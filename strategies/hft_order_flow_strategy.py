"""
Order Flow Imbalance HFT Strategy for Futures
Based on CURRENT_HFT_FUTURES_TRADING_STRATEGIES.md
"""

import backtrader as bt
import numpy as np
from datetime import datetime, timedelta
import logging


class OrderFlowImbalanceHFTStrategy(bt.Strategy):
    """
    Trade based on order book imbalances
    Predicts short-term price movements from order flow
    
    Expected Performance:
    - Sharpe Ratio: 1.5 - 2.2
    - Daily Return: 0.4% - 0.9%
    - Win Rate: 52% - 62%
    - Max Drawdown: < 6%
    """
    
    params = (
        # Order flow parameters
        ('imbalance_threshold', 0.3),  # 30% imbalance
        ('depth_levels', 5),
        ('min_liquidity', 100),
        ('hold_time', 30),  # seconds
        
        # Volume-based imbalance (since we don't have real order book)
        ('volume_window', 10),
        ('buy_sell_ratio_threshold', 1.5),
        
        # Risk management
        ('max_position_size', 10),
        ('max_daily_trades', 500),
        ('circuit_breaker', 0.06),  # 6% drawdown
        
        # Performance targets
        ('target_sharpe', 1.8),
        ('target_daily_return', 0.006),
        
        # Logging
        ('printlog', False),
    )
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Volume tracking for imbalance calculation
        self.volume_history = []
        self.price_changes = []
        
        # Position tracking
        self.in_position = False
        self.entry_time = None
        self.entry_price = 0.0
        self.position_direction = None
        
        # Imbalance metrics
        self.current_imbalance = 0.0
        self.buy_pressure = 0.0
        self.sell_pressure = 0.0
        
        # Performance tracking
        self.daily_trades = 0
        self.daily_pnl = 0.0
        self.peak_value = self.broker.getvalue()
        self.trade_count = 0
        
        self.logger.info("OrderFlowImbalanceHFTStrategy initialized")
    
    def calculate_order_flow_imbalance(self):
        """
        Calculate order flow imbalance from volume and price changes
        Since we don't have real order book data, we estimate from volume and price
        
        Returns: dict with imbalance metrics
        """
        if len(self.volume_history) < self.p.volume_window:
            return None
        
        recent_volumes = self.volume_history[-self.p.volume_window:]
        recent_price_changes = self.price_changes[-self.p.volume_window:]
        
        # Estimate buy/sell volume based on price changes
        buy_volume = sum(v for v, pc in zip(recent_volumes, recent_price_changes) if pc > 0)
        sell_volume = sum(v for v, pc in zip(recent_volumes, recent_price_changes) if pc < 0)
        
        total_volume = buy_volume + sell_volume
        
        if total_volume < self.p.min_liquidity:
            return None  # Insufficient liquidity
        
        # Calculate imbalance ratio
        imbalance = (buy_volume - sell_volume) / total_volume if total_volume > 0 else 0
        
        return {
            'imbalance': imbalance,
            'buy_volume': buy_volume,
            'sell_volume': sell_volume,
            'total_volume': total_volume,
            'buy_pressure': buy_volume / total_volume if total_volume > 0 else 0,
            'sell_pressure': sell_volume / total_volume if total_volume > 0 else 0
        }
    
    def next(self):
        """Main strategy logic"""
        current_time = self.data.datetime.datetime(0)
        current_price = self.data.close[0]
        current_volume = self.data.volume[0]
        
        # Calculate price change
        if len(self.volume_history) > 0:
            prev_price = self.data.close[-1] if len(self.data.close) > 1 else current_price
            price_change = current_price - prev_price
        else:
            price_change = 0
        
        # Update history
        self.volume_history.append(current_volume)
        self.price_changes.append(price_change)
        
        # Keep only necessary history
        max_length = self.p.volume_window + 50
        if len(self.volume_history) > max_length:
            self.volume_history = self.volume_history[-max_length:]
            self.price_changes = self.price_changes[-max_length:]
        
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
        
        # Calculate order flow imbalance
        imbalance_data = self.calculate_order_flow_imbalance()
        
        if imbalance_data is None:
            return
        
        self.current_imbalance = imbalance_data['imbalance']
        self.buy_pressure = imbalance_data['buy_pressure']
        self.sell_pressure = imbalance_data['sell_pressure']
        
        # Entry logic
        if not self.in_position:
            if self.current_imbalance > self.p.imbalance_threshold:
                # Strong buy pressure
                if self.p.printlog:
                    self.log(f"BUY SIGNAL: Imbalance={self.current_imbalance:.2f}, "
                           f"Buy Pressure={self.buy_pressure:.2f}")
                
                self.buy(size=1)
                self.in_position = True
                self.position_direction = 'long'
                self.entry_time = current_time
                self.entry_price = current_price
                self.daily_trades += 1
                
            elif self.current_imbalance < -self.p.imbalance_threshold:
                # Strong sell pressure
                if self.p.printlog:
                    self.log(f"SELL SIGNAL: Imbalance={self.current_imbalance:.2f}, "
                           f"Sell Pressure={self.sell_pressure:.2f}")
                
                self.sell(size=1)
                self.in_position = True
                self.position_direction = 'short'
                self.entry_time = current_time
                self.entry_price = current_price
                self.daily_trades += 1
        
        # Exit logic - time-based or imbalance reversal
        else:
            time_held = (current_time - self.entry_time).total_seconds()
            
            # Time-based exit
            if time_held >= self.p.hold_time:
                if self.p.printlog:
                    self.log(f"TIME EXIT: Held for {time_held:.0f}s, "
                           f"Imbalance={self.current_imbalance:.2f}")
                
                self.close()
                self.in_position = False
                self.daily_trades += 1
            
            # Imbalance normalization exit
            elif abs(self.current_imbalance) < 0.1:
                if self.p.printlog:
                    self.log(f"IMBALANCE NORMALIZED: {self.current_imbalance:.2f}")
                
                self.close()
                self.in_position = False
                self.daily_trades += 1
            
            # Reversal exit (imbalance flips significantly)
            elif (self.position_direction == 'long' and 
                  self.current_imbalance < -self.p.imbalance_threshold * 0.5):
                if self.p.printlog:
                    self.log(f"IMBALANCE REVERSAL (LONG): {self.current_imbalance:.2f}")
                
                self.close()
                self.in_position = False
                self.daily_trades += 1
            
            elif (self.position_direction == 'short' and 
                  self.current_imbalance > self.p.imbalance_threshold * 0.5):
                if self.p.printlog:
                    self.log(f"IMBALANCE REVERSAL (SHORT): {self.current_imbalance:.2f}")
                
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
                hold_time = (self.data.datetime.datetime(0) - self.entry_time).total_seconds()
                self.log(f'TRADE CLOSED, P&L: {trade.pnl:.2f}, '
                       f'Hold Time: {hold_time:.0f}s, '
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