"""
Momentum Ignition HFT Strategy for Futures
Based on CURRENT_HFT_FUTURES_TRADING_STRATEGIES.md
"""

import backtrader as bt
import numpy as np
import logging


class MomentumIgnitionHFTStrategy(bt.Strategy):
    """
    High-frequency momentum strategy
    Detects and trades rapid price movements
    
    Expected Performance:
    - Sharpe Ratio: 1.8 - 2.8
    - Daily Return: 0.8% - 1.5%
    - Win Rate: 50% - 60%
    - Max Drawdown: < 10%
    """
    
    params = (
        # Momentum parameters
        ('momentum_threshold', 0.001),  # 0.1% price change
        ('momentum_window', 10),  # ticks
        ('volume_threshold', 1.5),  # 1.5x average volume
        ('profit_target', 0.003),  # 0.3%
        ('stop_loss', 0.001),  # 0.1%
        ('ignition_volume', 50),  # Volume for ignition detection
        ('trade_interval', 0.1),  # Minimum interval between trades
        ('max_holding_time', 30),  # Maximum holding time in seconds
        
        # Volume analysis
        ('volume_lookback', 100),
        ('volume_surge_threshold', 2.0),  # Volume surge multiplier
        ('momentum_decay_time', 15),  # Momentum decay time in seconds
        ('min_market_volume', 1000),  # Minimum market volume threshold
        
        # Advanced parameters
        ('max_ignition_trades', 10),  # Maximum ignition trades per session
        ('cooldown_period', 300),  # Cooldown period in seconds
        ('volume_multiplier', 2.0),  # Volume multiplier for sizing
        ('adaptive_ignition', True),  # Enable adaptive ignition detection
        ('max_trades_per_minute', 10),  # Maximum trades per minute
        
        # Risk management
        ('max_position_size', 10),
        ('max_daily_trades', 500),
        ('circuit_breaker', 0.10),  # 10% drawdown
        ('risk_limit', 0.01),  # Risk limit as percentage
        
        # Performance targets
        ('target_sharpe', 2.3),
        ('target_daily_return', 0.012),
        
        # Capital management
        ('initial_capital', 100000),  # Initial capital (ignored, for compatibility)
        
        # Logging
        ('printlog', False),
    )
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Price and volume tracking
        self.price_history = []
        self.volume_history = []
        
        # Position tracking
        self.in_position = False
        self.entry_price = 0.0
        self.position_direction = None  # 'long' or 'short'
        self.stop_loss_price = 0.0
        self.take_profit_price = 0.0
        
        # Momentum indicators
        self.momentum_strength = 0.0
        self.volume_ratio = 0.0
        
        # Performance tracking
        self.daily_trades = 0
        self.daily_pnl = 0.0
        self.peak_value = self.broker.getvalue()
        self.trade_count = 0
        
        # Volume indicator
        self.volume_sma = bt.indicators.SimpleMovingAverage(
            self.data.volume,
            period=self.p.volume_lookback
        )
        
        self.logger.info("MomentumIgnitionHFTStrategy initialized")
    
    def detect_momentum(self):
        """
        Detect momentum ignition based on price and volume
        Returns: dict with momentum metrics
        """
        if len(self.price_history) < self.p.momentum_window:
            return None
        
        # Calculate recent price change
        recent_prices = self.price_history[-self.p.momentum_window:]
        price_change = (recent_prices[-1] - recent_prices[0]) / recent_prices[0]
        
        # Calculate volume surge
        if len(self.volume_history) >= self.p.momentum_window:
            recent_volume = self.volume_history[-self.p.momentum_window:]
            avg_recent_volume = np.mean(recent_volume)
            
            # Get average volume from indicator
            if len(self.volume_sma) > 0:
                avg_volume = self.volume_sma[0]
                volume_ratio = avg_recent_volume / avg_volume if avg_volume > 0 else 0
            else:
                volume_ratio = 1.0
        else:
            volume_ratio = 1.0
        
        # Calculate momentum strength
        momentum_strength = abs(price_change) * volume_ratio
        
        return {
            'price_change': price_change,
            'volume_ratio': volume_ratio,
            'momentum_strength': momentum_strength,
            'direction': 'up' if price_change > 0 else 'down'
        }
    
    def next(self):
        """Main strategy logic"""
        current_price = self.data.close[0]
        current_volume = self.data.volume[0]
        
        # Update price and volume history
        self.price_history.append(current_price)
        self.volume_history.append(current_volume)
        
        # Keep only necessary history
        max_length = max(self.p.momentum_window, self.p.volume_lookback) + 50
        if len(self.price_history) > max_length:
            self.price_history = self.price_history[-max_length:]
            self.volume_history = self.volume_history[-max_length:]
        
        # Check circuit breaker
        current_value = self.broker.getvalue()
        if self.peak_value > 0:
            drawdown = (self.peak_value - current_value) / self.peak_value
            if drawdown >= self.p.circuit_breaker:
                if self.p.printlog:
                    self.log(f"Circuit breaker triggered: {drawdown:.1%} drawdown")
                if self.in_position:
                    self.close()
                    self.in_position = False
                return
        
        # Update peak value
        if current_value > self.peak_value:
            self.peak_value = current_value
        
        # Check daily trade limit
        if self.daily_trades >= self.p.max_daily_trades:
            return
        
        # Detect momentum
        momentum_data = self.detect_momentum()
        
        if momentum_data is None:
            return
        
        self.momentum_strength = momentum_data['momentum_strength']
        self.volume_ratio = momentum_data['volume_ratio']
        
        # Entry logic
        if not self.in_position:
            # Check for momentum ignition
            if (self.momentum_strength > self.p.momentum_threshold and
                self.volume_ratio > self.p.volume_threshold):
                
                if momentum_data['direction'] == 'up':
                    # Buy on upward momentum
                    if self.p.printlog:
                        self.log(f"BUY SIGNAL: Momentum={self.momentum_strength:.4f}, "
                               f"Volume Ratio={self.volume_ratio:.2f}")
                    
                    self.buy(size=1)
                    self.in_position = True
                    self.position_direction = 'long'
                    self.entry_price = current_price
                    self.stop_loss_price = current_price * (1 - self.p.stop_loss)
                    self.take_profit_price = current_price * (1 + self.p.profit_target)
                    self.daily_trades += 1
                    
                elif momentum_data['direction'] == 'down':
                    # Sell on downward momentum
                    if self.p.printlog:
                        self.log(f"SELL SIGNAL: Momentum={self.momentum_strength:.4f}, "
                               f"Volume Ratio={self.volume_ratio:.2f}")
                    
                    self.sell(size=1)
                    self.in_position = True
                    self.position_direction = 'short'
                    self.entry_price = current_price
                    self.stop_loss_price = current_price * (1 + self.p.stop_loss)
                    self.take_profit_price = current_price * (1 - self.p.profit_target)
                    self.daily_trades += 1
        
        # Exit logic
        else:
            pnl_pct = (current_price - self.entry_price) / self.entry_price
            
            if self.position_direction == 'long':
                # Check stop loss or take profit for long position
                if current_price <= self.stop_loss_price:
                    if self.p.printlog:
                        self.log(f"STOP LOSS HIT (LONG): P&L={pnl_pct:.2%}")
                    self.close()
                    self.in_position = False
                    self.daily_trades += 1
                    
                elif current_price >= self.take_profit_price:
                    if self.p.printlog:
                        self.log(f"TAKE PROFIT HIT (LONG): P&L={pnl_pct:.2%}")
                    self.close()
                    self.in_position = False
                    self.daily_trades += 1
            
            elif self.position_direction == 'short':
                # Check stop loss or take profit for short position
                if current_price >= self.stop_loss_price:
                    if self.p.printlog:
                        self.log(f"STOP LOSS HIT (SHORT): P&L={-pnl_pct:.2%}")
                    self.close()
                    self.in_position = False
                    self.daily_trades += 1
                    
                elif current_price <= self.take_profit_price:
                    if self.p.printlog:
                        self.log(f"TAKE PROFIT HIT (SHORT): P&L={-pnl_pct:.2%}")
                    self.close()
                    self.in_position = False
                    self.daily_trades += 1
    
    def notify_order(self, order):
        """Handle order notifications"""
        if order.status in [order.Completed]:
            self.trade_count += 1
            
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
            
            if self.p.printlog:
                pnl_pct = (trade.pnl / self.entry_price) * 100 if self.entry_price > 0 else 0
                self.log(f'TRADE CLOSED, P&L: {trade.pnl:.2f} ({pnl_pct:.2f}%), '
                       f'Cumulative: {self.daily_pnl:.2f}')
    
    def log(self, txt, dt=None):
        """Logging function"""
        if self.p.printlog:
            dt = dt or self.data.datetime.date(0)
            print(f'{dt.isoformat()} {txt}')
    
    def stop(self):
        """Called when strategy stops"""
        if self.p.printlog:
            self.log(f'Strategy stopped. Total trades: {self.trade_count}, '
                   f'Daily P&L: {self.daily_pnl:.2f}')