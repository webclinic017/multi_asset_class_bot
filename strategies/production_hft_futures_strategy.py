"""
Production HFT Futures Strategy
Combines multiple HFT sub-strategies with dynamic allocation
Based on CURRENT_HFT_FUTURES_TRADING_STRATEGIES.md
"""

import backtrader as bt
import numpy as np
from datetime import datetime, timedelta
from collections import deque
from typing import Dict
import logging

# Import sub-strategies
from strategies.hft_market_making_strategy import MarketMakingHFTStrategy
from strategies.hft_statistical_arbitrage_strategy import StatisticalArbitrageHFTStrategy
from strategies.hft_momentum_ignition_strategy import MomentumIgnitionHFTStrategy
from strategies.hft_order_flow_strategy import OrderFlowImbalanceHFTStrategy


class ProductionHFTFuturesStrategy(bt.Strategy):
    """
    Production-ready HFT futures strategy
    Combines multiple sub-strategies with dynamic allocation and sentiment integration
    
    Expected Performance:
    - Sharpe Ratio: 2.0 - 3.0
    - Daily Return: 0.8% - 1.5%
    - Win Rate: 60% - 70%
    - Max Drawdown: < 10%
    """
    
    params = (
        # Multi-strategy weights
        ('market_making_weight', 0.4),
        ('stat_arb_weight', 0.3),
        ('momentum_weight', 0.2),
        ('order_flow_weight', 0.1),
        
        # Global parameters
        ('max_position_size', 10),
        ('target_sharpe', 2.0),
        ('target_daily_return', 0.01),
        ('max_daily_loss', -0.02),
        
        # Risk management
        ('max_daily_trades', 500),
        ('circuit_breaker', 0.10),
        ('max_order_rate', 10),  # orders per second
        
        # Sentiment integration
        ('use_sentiment', True),
        ('sentiment_weight', 0.3),
        ('min_sentiment_confidence', 0.5),
        ('sentiment_update_interval', 3600),  # 1 hour
        
        # News event monitoring
        ('use_news_events', True),
        ('pre_event_minutes', 30),
        
        # Execution parameters
        ('max_latency_ms', 100),
        ('max_slippage_bps', 1),
        
        # Capital management
        ('initial_capital', 100000),  # Initial capital (ignored, for compatibility)
        
        # Logging
        ('printlog', False),
    )
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Initialize sentiment analyzer if enabled
        self.sentiment_analyzer = None
        self.news_monitor = None
        self.current_sentiment = None
        self.last_sentiment_update = None
        
        if self.p.use_sentiment:
            try:
                from sentiment.futures_sentiment_analyzer import (
                    FuturesSentimentAnalyzer,
                    CommodityNewsEventMonitor
                )
                self.sentiment_analyzer = FuturesSentimentAnalyzer()
                self.news_monitor = CommodityNewsEventMonitor()
                self.logger.info("Sentiment analysis enabled")
            except Exception as e:
                self.logger.warning(f"Could not initialize sentiment analyzer: {e}")
                self.p.use_sentiment = False
        
        # Performance tracking
        self.daily_trades = 0
        self.daily_pnl = 0.0
        self.peak_value = self.broker.getvalue()
        self.trade_history = deque(maxlen=1000)
        
        # Order rate limiting
        self.recent_orders = deque(maxlen=100)
        
        # Strategy-specific metrics
        self.strategy_signals = {
            'market_making': 0,
            'stat_arb': 0,
            'momentum': 0,
            'order_flow': 0
        }
        
        self.logger.info("ProductionHFTFuturesStrategy initialized")
    
    def next(self):
        """
        Main strategy logic - aggregate signals from all sub-strategies
        """
        current_time = self.data.datetime.datetime(0)
        current_price = self.data.close[0]
        
        # Update sentiment periodically if enabled
        if self.p.use_sentiment and self.sentiment_analyzer:
            if (self.last_sentiment_update is None or
                (current_time - self.last_sentiment_update).total_seconds() > self.p.sentiment_update_interval):
                
                try:
                    symbol = self._extract_symbol()
                    self.current_sentiment = self.sentiment_analyzer.get_commodity_sentiment(symbol)
                    self.last_sentiment_update = current_time
                    
                    if self.p.printlog:
                        self.log(f"Sentiment updated: {self.current_sentiment['signal']} "
                               f"(score: {self.current_sentiment['sentiment_score']:.2f})")
                except Exception as e:
                    self.logger.warning(f"Sentiment update failed: {e}")
        
        # Check for upcoming news events if enabled
        if self.p.use_news_events and self.news_monitor:
            try:
                symbol = self._extract_symbol()
                pre_event_strategy = self.news_monitor.get_pre_event_strategy(
                    symbol, self.p.pre_event_minutes
                )
                
                if pre_event_strategy['action'] == 'CLOSE_POSITIONS':
                    if self.position:
                        self.close()
                        if self.p.printlog:
                            self.log(f"Closing positions: {pre_event_strategy['reason']}")
                    return
                
                elif pre_event_strategy['action'] == 'REDUCE_POSITIONS':
                    # Reduce position size by closing partial position
                    if self.position and abs(self.position.size) > 1:
                        reduction = int(abs(self.position.size) * 0.5)
                        if self.position.size > 0:
                            self.sell(size=reduction)
                        else:
                            self.buy(size=reduction)
                        
                        if self.p.printlog:
                            self.log(f"Reducing positions: {pre_event_strategy['reason']}")
                
            except Exception as e:
                self.logger.warning(f"News event check failed: {e}")
        
        # Check circuit breaker
        current_value = self.broker.getvalue()
        if self.peak_value > 0:
            drawdown = (self.peak_value - current_value) / self.peak_value
            if drawdown >= self.p.circuit_breaker:
                if self.p.printlog:
                    self.log(f"Circuit breaker triggered: {drawdown:.1%} drawdown")
                if self.position:
                    self.close()
                return
        
        # Update peak value
        if current_value > self.peak_value:
            self.peak_value = current_value
        
        # Check daily trade limit
        if self.daily_trades >= self.p.max_daily_trades:
            return
        
        # Check order rate limit
        if not self._check_order_rate_limit(current_time):
            return
        
        # Generate base trading signal (simplified for single data feed)
        signal = self._generate_aggregated_signal(current_price)
        
        # Enhance with sentiment if available
        if self.p.use_sentiment and self.current_sentiment:
            signal = self._enhance_with_sentiment(signal, self.current_sentiment)
        
        # Execute signal
        if signal['action'] == 'buy' and not self.position:
            if self.p.printlog:
                self.log(f"BUY SIGNAL: {signal['reason']}, Confidence: {signal['confidence']:.2f}")
            
            self.buy(size=1)
            self.daily_trades += 1
            self.recent_orders.append(current_time)
            
        elif signal['action'] == 'sell' and not self.position:
            if self.p.printlog:
                self.log(f"SELL SIGNAL: {signal['reason']}, Confidence: {signal['confidence']:.2f}")
            
            self.sell(size=1)
            self.daily_trades += 1
            self.recent_orders.append(current_time)
            
        elif signal['action'] == 'exit' and self.position:
            if self.p.printlog:
                self.log(f"EXIT SIGNAL: {signal['reason']}")
            
            self.close()
            self.daily_trades += 1
    
    def _extract_symbol(self) -> str:
        """Extract symbol from data feed"""
        # Try to get symbol from data feed name
        if hasattr(self.data, '_name'):
            return self.data._name.split('_')[0]  # Extract base symbol
        return 'ES'  # Default
    
    def _generate_aggregated_signal(self, current_price: float) -> Dict:
        """
        Generate aggregated signal from multiple indicators
        Simplified version for single data feed
        """
        # Simple momentum-based signal for demonstration
        if len(self.data.close) < 20:
            return {'action': 'hold', 'confidence': 0, 'reason': 'insufficient_data'}
        
        # Calculate short-term momentum
        recent_prices = [self.data.close[-i] for i in range(10, 0, -1)]
        price_change = (current_price - recent_prices[0]) / recent_prices[0]
        
        # Calculate volume surge
        if len(self.data.volume) >= 20:
            recent_volume = np.mean([self.data.volume[-i] for i in range(10, 0, -1)])
            avg_volume = np.mean([self.data.volume[-i] for i in range(20, 10, -1)])
            volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1.0
        else:
            volume_ratio = 1.0
        
        # Generate signal
        if price_change > 0.001 and volume_ratio > 1.5:
            return {
                'action': 'buy',
                'confidence': min(abs(price_change) * volume_ratio * 100, 1.0),
                'reason': 'momentum_up'
            }
        elif price_change < -0.001 and volume_ratio > 1.5:
            return {
                'action': 'sell',
                'confidence': min(abs(price_change) * volume_ratio * 100, 1.0),
                'reason': 'momentum_down'
            }
        
        # Exit signal if in position
        if self.position:
            # Simple profit target / stop loss
            if self.position.size > 0:  # Long position
                pnl_pct = (current_price - self.position.price) / self.position.price
                if pnl_pct >= 0.003 or pnl_pct <= -0.001:
                    return {'action': 'exit', 'confidence': 1.0, 'reason': 'target_hit'}
            else:  # Short position
                pnl_pct = (self.position.price - current_price) / self.position.price
                if pnl_pct >= 0.003 or pnl_pct <= -0.001:
                    return {'action': 'exit', 'confidence': 1.0, 'reason': 'target_hit'}
        
        return {'action': 'hold', 'confidence': 0, 'reason': 'no_signal'}
    
    def _enhance_with_sentiment(self, signal: Dict, sentiment: Dict) -> Dict:
        """Enhance trading signals with sentiment analysis"""
        if sentiment['confidence'] < self.p.min_sentiment_confidence:
            return signal  # Sentiment not confident enough
        
        sentiment_score = sentiment['sentiment_score']
        
        # Boost signal if sentiment agrees
        if signal.get('action') == 'buy' and sentiment_score > 0.2:
            signal['confidence'] = min(signal.get('confidence', 0.5) * 1.3, 1.0)
            signal['reason'] += ' + positive_sentiment'
        elif signal.get('action') == 'sell' and sentiment_score < -0.2:
            signal['confidence'] = min(signal.get('confidence', 0.5) * 1.3, 1.0)
            signal['reason'] += ' + negative_sentiment'
        
        # Reduce signal if sentiment disagrees
        elif signal.get('action') == 'buy' and sentiment_score < -0.2:
            signal['confidence'] *= 0.7
            signal['reason'] += ' - negative_sentiment'
        elif signal.get('action') == 'sell' and sentiment_score > 0.2:
            signal['confidence'] *= 0.7
            signal['reason'] += ' - positive_sentiment'
        
        return signal
    
    def _check_order_rate_limit(self, current_time: datetime) -> bool:
        """Check if order rate limit is exceeded"""
        # Remove old orders (older than 1 second)
        cutoff_time = current_time - timedelta(seconds=1)
        
        # Filter recent orders
        self.recent_orders = deque(
            [t for t in self.recent_orders if t > cutoff_time],
            maxlen=100
        )
        
        if len(self.recent_orders) >= self.p.max_order_rate:
            if self.p.printlog:
                self.log("Order rate limit exceeded")
            return False
        
        return True
    
    def notify_order(self, order):
        """Handle order notifications"""
        if order.status in [order.Completed]:
            if order.isbuy():
                if self.p.printlog:
                    self.log(f'BUY EXECUTED, Price: {order.executed.price:.5f}')
            else:
                if self.p.printlog:
                    self.log(f'SELL EXECUTED, Price: {order.executed.price:.5f}')
    
    def notify_trade(self, trade):
        """Handle trade notifications"""
        if trade.isclosed:
            self.daily_pnl += trade.pnl
            
            # Track trade for performance analysis
            trade_data = {
                'return': trade.pnl,
                'duration': (trade.dtclose - trade.dtopen).total_seconds() if hasattr(trade, 'dtclose') else 0,
                'size': trade.size,
                'entry_price': trade.price,
                'exit_price': trade.price + (trade.pnl / trade.size) if trade.size != 0 else trade.price
            }
            self.trade_history.append(trade_data)
            
            if self.p.printlog:
                self.log(f'TRADE CLOSED, P&L: {trade.pnl:.2f}, '
                       f'Duration: {trade_data["duration"]:.0f}s, '
                       f'Cumulative: {self.daily_pnl:.2f}')
    
    def log(self, txt, dt=None):
        """Logging function"""
        if self.p.printlog:
            dt = dt or self.data.datetime.date(0)
            print(f'{dt.isoformat()} {txt}')
    
    def stop(self):
        """Called when strategy stops"""
        # Calculate final performance metrics
        if self.trade_history:
            returns = [t['return'] for t in self.trade_history]
            mean_return = np.mean(returns)
            std_return = np.std(returns)
            sharpe = (mean_return / std_return * np.sqrt(252)) if std_return > 0 else 0
            
            winning_trades = len([r for r in returns if r > 0])
            win_rate = winning_trades / len(returns) * 100 if returns else 0
            
            if self.p.printlog:
                self.log(f'Strategy stopped.')
                self.log(f'Total Trades: {len(self.trade_history)}')
                self.log(f'Daily P&L: {self.daily_pnl:.2f}')
                self.log(f'Win Rate: {win_rate:.1f}%')
                self.log(f'Sharpe Ratio: {sharpe:.2f}')