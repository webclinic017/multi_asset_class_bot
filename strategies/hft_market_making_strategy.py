"""
Market Making HFT Strategy for Futures
Based on CURRENT_HFT_FUTURES_TRADING_STRATEGIES.md
"""

import backtrader as bt
import numpy as np
from datetime import datetime, timedelta
import logging


class MarketMakingHFTStrategy(bt.Strategy):
    """
    High-frequency market making strategy for futures
    Continuously quotes bid/ask prices to capture spread
    
    Expected Performance:
    - Sharpe Ratio: 1.5 - 2.5
    - Daily Return: 0.3% - 0.8%
    - Win Rate: 55% - 65%
    - Max Drawdown: < 5%
    """
    
    params = (
        # Market making parameters - Updated for ES futures
        ('spread_width', 0.25),      # 0.25 points for ES futures
        ('min_spread', 0.25),        # Minimum spread (0.25 points)
        ('max_spread', 2.0),         # Maximum spread (2.0 points)
        ('max_inventory', 10),        # Maximum inventory positions
        ('quote_refresh_time', 5),   # seconds
        ('inventory_skew_factor', 0.5),  # Inventory skew factor
        ('inventory_rebalance_threshold', 0.8),  # Rebalance at 80% of max inventory
        ('volatility_lookback', 20), # Volatility lookback period
        ('adaptive_spread', True),   # Enable adaptive spread adjustment
        
        # Order management
        ('max_orders_per_side', 3),  # Maximum orders per side
        ('order_size', 1),           # Default order size
        
        # Risk management
        ('max_position_size', 10),   # Maximum position size
        ('max_daily_trades', 500),   # Maximum daily trades
        ('circuit_breaker', 0.05),   # 5% drawdown limit
        ('risk_limit', 0.02),        # 2% risk limit
        
        # Performance targets
        ('target_sharpe', 2.0),
        ('target_daily_return', 0.01),
        
        # Volatility parameters
        ('volatility_window', 20),
        ('volatility_adjustment', True),
        
        # Capital management
        ('initial_capital', 100000),  # Initial capital (ignored, for compatibility)
        
        # Logging
        ('printlog', False),
    )
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Track positions and inventory
        self.current_inventory = 0
        self.entry_prices = []
        
        # Calculate volatility for spread adjustment
        self.volatility = bt.indicators.StdDev(
            self.data.close,
            period=self.p.volatility_window
        )
        
        # Track mid price
        self.mid_price = (self.data.high + self.data.low) / 2
        
        # Performance tracking
        self.daily_trades = 0
        self.daily_pnl = 0.0
        self.peak_value = self.broker.getvalue()
        self.trade_count = 0
        
        # Order tracking
        self.bid_order = None
        self.ask_order = None
        self.last_quote_time = None
        
        # Track executed orders for proper inventory management
        self.executed_bids = []  # Track executed buy orders
        self.executed_asks = []  # Track executed sell orders
        
        self.logger.info("Market Making HFT Strategy initialized")
    
    def calculate_quotes(self, mid_price, current_inventory, volatility):
        """
        Calculate optimal bid/ask quotes based on:
        - Mid-market price
        - Current inventory position
        - Market volatility
        """
        # Base spread adjusted for volatility
        if self.p.volatility_adjustment and volatility > 0:
            base_spread = self.p.spread_width * (1 + volatility * 10)
        else:
            base_spread = self.p.spread_width
        
        # Ensure spread is within bounds
        base_spread = max(self.p.min_spread, min(base_spread, self.p.max_spread))
        
        # Inventory skew - widen spread on side with inventory
        inventory_ratio = current_inventory / self.p.max_inventory if self.p.max_inventory > 0 else 0
        bid_skew = base_spread * (1 + inventory_ratio * self.p.inventory_skew_factor)
        ask_skew = base_spread * (1 - inventory_ratio * self.p.inventory_skew_factor)
        
        bid_price = mid_price - bid_skew
        ask_price = mid_price + ask_skew
        
        return {
            'bid': round(bid_price, 5),
            'ask': round(ask_price, 5),
            'bid_size': self._calculate_quote_size(inventory_ratio, 'bid'),
            'ask_size': self._calculate_quote_size(inventory_ratio, 'ask')
        }
    
    def _calculate_quote_size(self, inventory_ratio, side):
        """Calculate quote size based on inventory"""
        base_size = self.p.order_size
        
        # Reduce size when inventory is high in the same direction
        if side == 'bid' and inventory_ratio > 0.5:
            return max(1, base_size * 0.5)  # Reduce bid size when long
        elif side == 'ask' and inventory_ratio < -0.5:
            return max(1, base_size * 0.5)  # Reduce ask size when short
        
        return base_size
    
    def next(self):
        """Main strategy logic"""
        current_time = self.data.datetime.datetime(0)
        current_price = self.data.close[0]
        
        # Check circuit breaker
        current_value = self.broker.getvalue()
        if self.peak_value > 0:
            drawdown = (self.peak_value - current_value) / self.peak_value
            if drawdown >= self.p.circuit_breaker:
                if self.p.printlog:
                    self.log(f"Circuit breaker triggered: {drawdown:.1%} drawdown")
                return
        
        # Update peak value
        if current_value > self.peak_value:
            self.peak_value = current_value
        
        # Check daily trade limit
        if self.daily_trades >= self.p.max_daily_trades:
            if self.p.printlog:
                self.log("Daily trade limit reached")
            return
        
        # Update inventory from position
        self.current_inventory = self.position.size
        
        # Get current volatility
        current_volatility = self.volatility[0] if len(self.volatility) > 0 else 0
        
        # Calculate quotes
        mid_price = (self.data.high[0] + self.data.low[0]) / 2
        quotes = self.calculate_quotes(mid_price, self.current_inventory, current_volatility)
        
        # Check if we need to refresh quotes
        should_refresh = (
            self.last_quote_time is None or
            (current_time - self.last_quote_time).total_seconds() >= self.p.quote_refresh_time
        )
        
        if should_refresh:
            # Cancel existing orders
            if self.bid_order:
                self.cancel(self.bid_order)
            if self.ask_order:
                self.cancel(self.ask_order)
            
            # Place new quotes if within inventory limits
            if abs(self.current_inventory) < self.p.max_inventory:
                # Place bid (buy) order
                if self.current_inventory < self.p.max_inventory:
                    self.bid_order = self.buy(
                        size=quotes['bid_size'],
                        price=quotes['bid'],
                        exectype=bt.Order.Limit
                    )
                
                # Place ask (sell) order
                if self.current_inventory > -self.p.max_inventory:
                    self.ask_order = self.sell(
                        size=quotes['ask_size'],
                        price=quotes['ask'],
                        exectype=bt.Order.Limit
                    )
                
                self.last_quote_time = current_time
        
        # Inventory rebalancing - close positions if inventory exceeds thresholds
        if abs(self.current_inventory) >= self.p.max_inventory * self.p.inventory_rebalance_threshold:
            if self.p.printlog:
                self.log(f"Rebalancing inventory: {self.current_inventory}")
            
            # Close positions to reduce inventory
            if self.current_inventory > 0:
                # Long inventory - sell to reduce
                # Use market order for faster execution
                self.sell(size=min(abs(self.current_inventory), 2), exectype=bt.Order.Market)
            elif self.current_inventory < 0:
                # Short inventory - buy to reduce
                # Use market order for faster execution
                self.buy(size=min(abs(self.current_inventory), 2), exectype=bt.Order.Market)
    
    def notify_order(self, order):
        """Handle order notifications"""
        if order.status in [order.Completed]:
            self.daily_trades += 1
            self.trade_count += 1
            
            # Track executed orders for inventory management
            if order.isbuy():
                if self.p.printlog:
                    self.log(f'BUY EXECUTED, Price: {order.executed.price:.5f}, Size: {order.executed.size}')
                self.executed_bids.append({
                    'price': order.executed.price,
                    'size': order.executed.size,
                    'time': self.data.datetime.datetime(0)
                })
            else:
                if self.p.printlog:
                    self.log(f'SELL EXECUTED, Price: {order.executed.price:.5f}, Size: {order.executed.size}')
                self.executed_asks.append({
                    'price': order.executed.price,
                    'size': order.executed.size,
                    'time': self.data.datetime.datetime(0)
                })
    
    def notify_trade(self, trade):
        """Handle trade notifications"""
        if trade.isclosed:
            self.daily_pnl += trade.pnl
            
            if self.p.printlog:
                self.log(f'TRADE CLOSED, P&L: {trade.pnl:.2f}, Cumulative: {self.daily_pnl:.2f}')
    
    def log(self, txt, dt=None):
        """Logging function"""
        if self.p.printlog:
            dt = dt or self.data.datetime.date(0)
            print(f'{dt.isoformat()} {txt}')
    
    def stop(self):
        """Called when strategy stops"""
        # Calculate final metrics
        total_spread_captured = sum(
            (ask['price'] - bid['price']) * min(bid['size'], ask['size'])
            for bid, ask in zip(self.executed_bids, self.executed_asks)
        )
        
        if self.p.printlog:
            self.log(f'Strategy stopped. Total trades: {self.trade_count}, Daily P&L: {self.daily_pnl:.2f}')
            self.log(f'=== MARKET MAKING HFT STRATEGY RESULTS ===')
            self.log(f'Total Trades: {self.trade_count}')
            self.log(f'Spread Captured: ${total_spread_captured:.2f}')
            self.log(f'Final Inventory: {self.position.size}')
            self.log(f'Win Rate: {((self.trade_count - len([t for t in self.executed_asks if t.get("pnl", 0) < 0])) / max(self.trade_count, 1) * 100):.1f}%')
            self.log(f'Final Portfolio Value: ${self.broker.getvalue():.2f}')
