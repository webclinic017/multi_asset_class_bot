"""
Sentiment-Enhanced Forex Strategy
Combines technical analysis with news sentiment and fundamental analysis
"""

import backtrader as bt
import logging
import numpy as np
import sys
import os

# Add the parent directory to the path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sentiment.news_analyzer import news_analyzer

class SentimentEnhancedForexStrategy(bt.Strategy):
    """
    Advanced forex strategy that combines:
    1. Technical analysis (MA, RSI, MACD, etc.)
    2. News sentiment analysis
    3. Fundamental analysis signals
    4. Enhanced risk management
    """
    params = (
        # Technical Analysis Parameters
        ('fast_length', 8),
        ('slow_length', 21),
        ('rsi_period', 14),
        ('rsi_oversold', 25),
        ('rsi_overbought', 75),
        ('macd_fast', 12),
        ('macd_slow', 26),
        ('macd_signal', 9),
        
        # Risk Management - Enhanced
        ('stop_loss_percent', 0.008),    # 0.8% stop loss
        ('take_profit_percent', 0.024),  # 2.4% take profit (3:1 ratio)
        
        # Sentiment Analysis Parameters
        ('use_sentiment_filter', True),
        ('sentiment_threshold', 0.3),     # Minimum sentiment strength
        ('sentiment_weight', 0.4),        # Weight of sentiment in decision
        ('news_lookback_hours', 12),      # Hours to look back for news
        
        # Strategy Filters
        ('use_rsi_filter', True),
        ('use_macd_filter', True),
        ('use_trend_filter', True),
        ('use_momentum_filter', True),
        ('use_breakout_filter', True),
        
        # Trade Management
        ('max_trades_per_day', 4),
        ('min_bars_between_trades', 3),
        
        # Enhanced Features
        ('volatility_multiplier', 1.5),
        ('trend_strength_min', 0.6),
        
        # Sentiment-specific parameters
        ('sentiment_boost_multiplier', 1.2),  # Boost position size with strong sentiment
        ('news_veto_threshold', -0.7),        # Strong negative news can veto trades
        
        # Logging
        ('printlog', False)
    )

    def log(self, txt, dt=None):
        """Logging function for this strategy"""
        if self.p.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            logging.info(f'{dt.isoformat()} {txt}')

    def __init__(self):
        self.dataclose = self.datas[0].close
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low
        
        self.order = None
        self.buyprice = None
        self.buycomm = None
        self.last_trade_bar = 0
        self.trades_today = 0
        self.current_day = None

        # Technical Indicators
        self.sma_fast = bt.indicators.SMA(self.datas[0], period=self.p.fast_length)
        self.sma_slow = bt.indicators.SMA(self.datas[0], period=self.p.slow_length)
        self.crossover = bt.indicators.CrossOver(self.sma_fast, self.sma_slow)
        
        # RSI for momentum
        self.rsi = bt.indicators.RSI(self.datas[0], period=self.p.rsi_period)
        
        # MACD for trend confirmation
        self.macd = bt.indicators.MACD(
            self.datas[0],
            period_me1=self.p.macd_fast,
            period_me2=self.p.macd_slow,
            period_signal=self.p.macd_signal
        )
        
        # Additional indicators
        self.ema_fast = bt.indicators.EMA(self.datas[0], period=self.p.fast_length)
        self.ema_slow = bt.indicators.EMA(self.datas[0], period=self.p.slow_length)
        
        # Volatility indicators
        self.atr = bt.indicators.ATR(self.datas[0], period=14)
        self.bb = bt.indicators.BollingerBands(self.datas[0], period=20)
        
        # Momentum indicators
        self.momentum = bt.indicators.Momentum(self.datas[0], period=10)
        self.roc = bt.indicators.RateOfChange(self.datas[0], period=12)
        
        # Trend strength
        self.adx = bt.indicators.DirectionalMovementIndex(self.datas[0], period=14)
        
        # Sentiment tracking
        self.last_sentiment_check = None
        self.current_sentiment = None
        self.sentiment_cache_duration = 300  # 5 minutes cache
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("SentimentEnhancedForexStrategy initialized")

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED, Price: {order.executed.price:.5f}, Cost: {order.executed.value:.2f}')
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            elif order.issell():
                self.log(f'SELL EXECUTED, Price: {order.executed.price:.5f}, Cost: {order.executed.value:.2f}')
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        
        self.log(f'TRADE CLOSED - P&L: {trade.pnlcomm:.2f}, Return: {(trade.pnlcomm/10000)*100:.3f}%')

    def get_sentiment_signal(self):
        """Get current sentiment signal with caching"""
        try:
            current_time = self.datas[0].datetime.datetime(0)
            
            # Check if we need to update sentiment
            if (self.last_sentiment_check is None or 
                (current_time - self.last_sentiment_check).total_seconds() > self.sentiment_cache_duration):
                
                # Get fresh sentiment data
                self.current_sentiment = news_analyzer.get_trading_signal(self.p.news_lookback_hours)
                self.last_sentiment_check = current_time
                
                self.log(f'SENTIMENT UPDATE - Direction: {self.current_sentiment["signal_direction"]:.3f}, '
                        f'Strength: {self.current_sentiment["signal_strength"]:.3f}, '
                        f'Recommendation: {self.current_sentiment["recommendation"]}')
            
            return self.current_sentiment
            
        except Exception as e:
            self.logger.error(f"Error getting sentiment signal: {e}")
            return {
                'signal_direction': 0.0,
                'signal_strength': 0.0,
                'recommendation': 'NEUTRAL'
            }

    def next(self):
        # Track daily trades
        current_date = self.datas[0].datetime.date(0)
        if self.current_day != current_date:
            self.current_day = current_date
            self.trades_today = 0

        if self.order:
            return

        # Prevent overtrading
        if self.trades_today >= self.p.max_trades_per_day:
            return
            
        if len(self) - self.last_trade_bar < self.p.min_bars_between_trades:
            return

        current_price = self.dataclose[0]

        if not self.position:  # Not in market
            # Get sentiment signal
            sentiment = self.get_sentiment_signal()
            
            # Check for sentiment veto (strong negative news)
            if (self.p.use_sentiment_filter and 
                sentiment['signal_strength'] > 0.5 and 
                sentiment['signal_direction'] < self.p.news_veto_threshold):
                self.log(f'SENTIMENT VETO - Strong negative sentiment: {sentiment["signal_direction"]:.3f}')
                return
            
            # Enhanced multi-factor signal generation
            technical_signals = self._get_technical_signals(current_price)
            
            # Combine technical and sentiment signals
            combined_signals = self._combine_signals(technical_signals, sentiment)
            
            # Execute trades based on combined signals
            if combined_signals['action'] == 'BUY' and combined_signals['strength'] > 0.6:
                position_size = self._calculate_position_size(combined_signals, sentiment)
                self.log(f'SENTIMENT-ENHANCED BUY - Technical: {len(technical_signals["long_signals"])}, '
                        f'Sentiment: {sentiment["recommendation"]}, Strength: {combined_signals["strength"]:.3f}')
                self.order = self.buy(size=position_size)
                self.last_trade_bar = len(self)
                self.trades_today += 1
                
            elif combined_signals['action'] == 'SELL' and combined_signals['strength'] > 0.6:
                position_size = self._calculate_position_size(combined_signals, sentiment)
                self.log(f'SENTIMENT-ENHANCED SELL - Technical: {len(technical_signals["short_signals"])}, '
                        f'Sentiment: {sentiment["recommendation"]}, Strength: {combined_signals["strength"]:.3f}')
                self.order = self.sell(size=position_size)
                self.last_trade_bar = len(self)
                self.trades_today += 1

        else:  # In position - manage exits
            self._manage_position()

    def _get_technical_signals(self, current_price):
        """Get technical analysis signals"""
        long_signals = []
        short_signals = []
        
        # Check trend strength
        trend_strong = True
        if hasattr(self, 'adx') and len(self.adx) > 0:
            trend_strong = self.adx.adx[0] > (self.p.trend_strength_min * 100)
        
        # LONG SIGNALS
        if self.crossover > 0:
            long_signals.append('ma_cross')
        
        if self.ema_fast[0] > self.ema_slow[0] and self.ema_fast[0] > self.ema_fast[-1]:
            long_signals.append('ema_trend')
        
        if (self.rsi[0] > self.p.rsi_oversold + 10 and 
            self.rsi[0] < self.p.rsi_overbought - 5 and 
            self.rsi[0] > self.rsi[-1]):
            long_signals.append('rsi_momentum')
        
        if (self.macd.macd[0] > self.macd.signal[0] and 
            self.macd.macd[0] > self.macd.macd[-1]):
            long_signals.append('macd_bull')
        
        if (self.p.use_breakout_filter and 
            current_price > self.bb.top[0] and 
            self.momentum[0] > 0):
            long_signals.append('breakout')
        
        if (self.p.use_trend_filter and trend_strong and
            self.sma_fast[0] > self.sma_slow[0] and
            current_price > self.sma_fast[0]):
            long_signals.append('strong_trend')
        
        # SHORT SIGNALS
        if self.crossover < 0:
            short_signals.append('ma_cross')
        
        if self.ema_fast[0] < self.ema_slow[0] and self.ema_fast[0] < self.ema_fast[-1]:
            short_signals.append('ema_trend')
        
        if (self.rsi[0] < self.p.rsi_overbought - 10 and 
            self.rsi[0] > self.p.rsi_oversold + 5 and 
            self.rsi[0] < self.rsi[-1]):
            short_signals.append('rsi_momentum')
        
        if (self.macd.macd[0] < self.macd.signal[0] and 
            self.macd.macd[0] < self.macd.macd[-1]):
            short_signals.append('macd_bear')
        
        if (self.p.use_breakout_filter and 
            current_price < self.bb.bot[0] and 
            self.momentum[0] < 0):
            short_signals.append('breakdown')
        
        if (self.p.use_trend_filter and trend_strong and
            self.sma_fast[0] < self.sma_slow[0] and
            current_price < self.sma_fast[0]):
            short_signals.append('strong_trend')
        
        return {
            'long_signals': long_signals,
            'short_signals': short_signals,
            'trend_strong': trend_strong
        }

    def _combine_signals(self, technical_signals, sentiment):
        """Combine technical and sentiment signals"""
        tech_long_strength = len(technical_signals['long_signals']) / 6.0  # Max 6 signals
        tech_short_strength = len(technical_signals['short_signals']) / 6.0
        
        # Sentiment contribution
        sentiment_strength = sentiment['signal_strength'] if self.p.use_sentiment_filter else 0
        sentiment_direction = sentiment['signal_direction'] if self.p.use_sentiment_filter else 0
        
        # Combine signals with weights
        tech_weight = 1.0 - self.p.sentiment_weight
        sentiment_weight = self.p.sentiment_weight
        
        # Calculate combined strength for long
        long_combined = (tech_long_strength * tech_weight + 
                        max(0, sentiment_direction) * sentiment_strength * sentiment_weight)
        
        # Calculate combined strength for short
        short_combined = (tech_short_strength * tech_weight + 
                         max(0, -sentiment_direction) * sentiment_strength * sentiment_weight)
        
        # Determine action
        if long_combined > short_combined and long_combined > 0.5:
            action = 'BUY'
            strength = long_combined
        elif short_combined > long_combined and short_combined > 0.5:
            action = 'SELL'
            strength = short_combined
        else:
            action = 'NEUTRAL'
            strength = 0.0
        
        # Sentiment boost for strong alignment
        if (self.p.use_sentiment_filter and 
            sentiment_strength > 0.6 and 
            ((action == 'BUY' and sentiment_direction > 0.4) or 
             (action == 'SELL' and sentiment_direction < -0.4))):
            strength *= self.p.sentiment_boost_multiplier
            self.log(f'SENTIMENT BOOST APPLIED - New strength: {strength:.3f}')
        
        return {
            'action': action,
            'strength': min(strength, 1.0),  # Cap at 1.0
            'technical_component': max(tech_long_strength, tech_short_strength),
            'sentiment_component': sentiment_strength,
            'sentiment_direction': sentiment_direction
        }

    def _calculate_position_size(self, combined_signals, sentiment):
        """Calculate position size based on signal strength and sentiment"""
        base_size = None  # Use default size
        
        # Increase size for very strong signals
        if combined_signals['strength'] > 0.8:
            base_size = 1.2  # 20% larger position
        elif combined_signals['strength'] > 0.9:
            base_size = 1.5  # 50% larger position
        
        return base_size

    def _manage_position(self):
        """Enhanced position management with sentiment consideration"""
        current_price = self.dataclose[0]
        
        # Safety check for entry price
        if self.buyprice is None:
            self.log('Warning: No entry price recorded, closing position')
            self.close()
            return
        
        # Get current sentiment for exit decisions
        sentiment = self.get_sentiment_signal()
        
        # Dynamic stop loss and take profit based on volatility
        volatility_adj = 1.0
        if hasattr(self, 'atr') and len(self.atr) > 0:
            volatility_adj = max(0.5, min(2.0, self.atr[0] / (current_price * 0.001)))
        
        if self.position.size > 0:  # Long position
            stop_loss = self.buyprice * (1 - self.p.stop_loss_percent * volatility_adj)
            take_profit = self.buyprice * (1 + self.p.take_profit_percent * volatility_adj)
            
            # Enhanced exit conditions
            if current_price <= stop_loss:
                self.log(f'STOP LOSS (LONG) - Entry: {self.buyprice:.5f}, Exit: {current_price:.5f}')
                self.close()
            elif current_price >= take_profit:
                self.log(f'TAKE PROFIT (LONG) - Entry: {self.buyprice:.5f}, Exit: {current_price:.5f}')
                self.close()
            # Sentiment-based early exit
            elif (self.p.use_sentiment_filter and 
                  sentiment['signal_strength'] > 0.6 and 
                  sentiment['signal_direction'] < -0.5):
                self.log(f'SENTIMENT EXIT (LONG) - Negative sentiment: {sentiment["signal_direction"]:.3f}')
                self.close()
            # Technical reversal exit
            elif (hasattr(self, 'macd') and 
                  self.macd.macd[0] < self.macd.signal[0] and 
                  self.rsi[0] > 70):
                self.log(f'TECHNICAL REVERSAL EXIT (LONG)')
                self.close()
                
        elif self.position.size < 0:  # Short position
            stop_loss = self.buyprice * (1 + self.p.stop_loss_percent * volatility_adj)
            take_profit = self.buyprice * (1 - self.p.take_profit_percent * volatility_adj)
            
            # Enhanced exit conditions
            if current_price >= stop_loss:
                self.log(f'STOP LOSS (SHORT) - Entry: {self.buyprice:.5f}, Exit: {current_price:.5f}')
                self.close()
            elif current_price <= take_profit:
                self.log(f'TAKE PROFIT (SHORT) - Entry: {self.buyprice:.5f}, Exit: {current_price:.5f}')
                self.close()
            # Sentiment-based early exit
            elif (self.p.use_sentiment_filter and 
                  sentiment['signal_strength'] > 0.6 and 
                  sentiment['signal_direction'] > 0.5):
                self.log(f'SENTIMENT EXIT (SHORT) - Positive sentiment: {sentiment["signal_direction"]:.3f}')
                self.close()
            # Technical reversal exit
            elif (hasattr(self, 'macd') and 
                  self.macd.macd[0] > self.macd.signal[0] and 
                  self.rsi[0] < 30):
                self.log(f'TECHNICAL REVERSAL EXIT (SHORT)')
                self.close()