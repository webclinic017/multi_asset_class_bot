
"""
Enhanced Market Making HFT Strategy for Futures Trading
Optimized for maximum risk-adjusted returns with advanced inventory management
"""

import backtrader as bt
import logging
import numpy as np
from typing import Dict, Any, Tuple, List
from datetime import datetime, timedelta
import pandas as pd

class EnhancedMarketMakingHFTStrategy(bt.Strategy):
    """
    Enhanced High-Frequency Trading Market Making Strategy with:
    - Advanced inventory management
    - Dynamic spread optimization
    - Risk-adjusted position sizing
    - Market regime detection
    - Transaction cost optimization
    """

    params = (
        # Core Market Making Parameters
        ('spread_width', 0.0002),  # Base spread width (0.02%)
        ('max_inventory', 5),      # Reduced maximum position size
        ('inventory_rebalance_threshold', 2),  # Lower threshold for faster rebalancing
        ('quote_refresh_time', 3),  # Faster refresh (3 seconds)
        ('min_spread', 0.0001),    # Minimum spread
        ('max_spread', 0.0008),    # Reduced maximum spread
        ('volatility_lookback', 15),  # Shorter lookback for responsiveness
        ('risk_limit', 0.015),     # Reduced risk per trade (1.5%)
        ('max_orders_per_side', 2), # Reduced orders per side
        ('order_size', 1),         # Base order size
        ('adaptive_spread', True), # Enable adaptive spread
        
        # Enhanced Risk Management
        ('inventory_hedge_ratio', 0.3),  # Hedge ratio for inventory management
        ('max_drawdown_limit', 0.05),    # 5% maximum drawdown
        ('position_size_multiplier', 0.8), # Conservative position sizing
        ('stop_loss_buffer', 0.001),     # Stop loss buffer
        
        # Market Regime Detection
        ('use_regime_filter', True),
        ('trend_strength_threshold', 0.3),
        ('volatility_regime_threshold', 0.02),
        
        # Performance Optimization
        ('min_profit_threshold', 0.0005),  # Minimum profit per trade
        ('max_holding_time', 300),         # Maximum holding time (5 minutes)
        ('rebalance_frequency', 10),       # Rebalance every 10 bars
        
        # Transaction Cost Management
        ('commission_adjustment', True),
        ('slippage_buffer', 0.0001),       # Slippage buffer
        
        ('printlog', False)
    )

    def __init__(self, initial_capital=None):
        """Initialize enhanced market making strategy"""
        self.logger = logging.getLogger(__name__)

        # Basic data feeds
        self.dataclose = self.datas[0].close
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low
        self.datavolume = self.datas[0].volume

        # Order management
        self.active_orders = {'buy': [], 'sell': []}
        self.inventory = 0
        self.cash_balance = self.broker.get_cash()

        # Market making state
        self.last_quote_time = None
        self.mid_price = None
        self.spread = self.p.spread_width
        self.volatility = 0.0
        self.current_regime = 'neutral'

        # Performance tracking
        self.total_trades = 0
        self.spread_captured = 0.0
        self.inventory_cost = 0.0
        self.max_inventory_held = 0
        self.total_commissions = 0.0

        # Risk management
        self.peak_portfolio_value = self.broker.get_value()
        self.current_drawdown = 0.0
        self.holding_start_time = None

        # Indicators for market making
        self._init_indicators()

        self.logger.info("Enhanced Market Making HFT Strategy initialized")

    def _init_indicators(self):
        """Initialize technical indicators for enhanced market making"""
        # Volatility indicators
        self.atr = bt.indicators.ATR(period=self.p.volatility_lookback)
        self.atr_percent = bt.indicators.PercentChange(self.atr, period=1)
        
        # Trend detection
        self.ema_fast = bt.indicators.EMA(period=5)
        self.ema_slow = bt.indicators.EMA(period=15)
        self.trend_strength = bt.indicators.Momentum(period=10)
        
        # Volume analysis
        self.volume_sma = bt.indicators.SMA(self.datavolume, period=10)
        self.volume_ratio = self.datavolume / bt.indicators.Max(self.volume_sma, 1e-8)
        
        # Market regime detection
        self.rsi = bt.indicators.RSI(period=14)
        self.macd = bt.indicators.MACD()

    def detect_market_regime(self) -> str:
        """Detect current market regime for adaptive behavior"""
        try:
            # Volatility-based regime
            current_vol = self.atr[0] / self.dataclose[0] if self.dataclose[0] > 0 else 0
            
            if current_vol > self.p.volatility_regime_threshold:
                return 'high_volatility'
            elif current_vol < 0.005:
                return 'low_volatility'
            
            # Trend-based regime
            if len(self.data) >= 15:
                trend_score = (self.ema_fast[0] - self.ema_slow[0]) / self.dataclose[0]
                
                if abs(trend_score) > self.p.trend_strength_threshold:
                    return 'trending' if trend_score > 0 else 'downtrend'
            
            return 'neutral'
            
        except Exception as e:
            self.logger.error(f"Error detecting market regime: {e}")
            return 'neutral'

    def calculate_enhanced_spread(self) -> float:
        """Calculate enhanced adaptive spread based on multiple factors"""
        if not self.p.adaptive_spread:
            return self.p.spread_width

        try:
            # Base spread
            base_spread = self.p.spread_width
            
            # Volatility adjustment (more conservative)
            current_volatility = self.atr[0] / self.dataclose[0] if self.dataclose[0] > 0 else 0
            vol_multiplier = 1.0 + (current_volatility * 10)  # More conservative scaling
            
            # Inventory adjustment (enhanced)
            inventory_ratio = abs(self.inventory) / self.p.max_inventory
            inventory_multiplier = 1.0 + (inventory_ratio * 0.3)  # Reduced inventory impact
            
            # Market regime adjustment
            regime_multipliers = {
                'high_volatility': 1.5,
                'low_volatility': 0.8,
                'trending': 1.2,
                'downtrend': 1.3,
                'neutral': 1.0
            }
            regime_multiplier = regime_multipliers.get(self.current_regime, 1.0)
            
            # Volume adjustment
            if self.volume_ratio[0] > 2.0:
                volume_multiplier = 0.9  # Tighter spreads in high volume
            elif self.volume_ratio[0] < 0.5:
                volume_multiplier = 1.2  # Wider spreads in low volume
            else:
                volume_multiplier = 1.0
            
            # Calculate final spread
            adaptive_spread = (base_spread * vol_multiplier * inventory_multiplier * 
                             regime_multiplier * volume_multiplier)
            
            # Apply commission and slippage adjustment
            if self.p.commission_adjustment:
                commission_impact = self.p.slippage_buffer * 2  # Bid-ask impact
                adaptive_spread += commission_impact
            
            # Constrain to limits
            adaptive_spread = max(self.p.min_spread, min(self.p.max_spread, adaptive_spread))
            
            return adaptive_spread
            
        except Exception as e:
            self.logger.error(f"Error calculating enhanced spread: {e}")
            return self.p.spread_width

    def calculate_enhanced_quotes(self) -> Tuple[float, float]:
        """Calculate enhanced bid and ask quotes with better inventory management"""
        try:
            # Get current mid price
            current_price = self.dataclose[0]
            self.mid_price = current_price
            
            # Calculate enhanced adaptive spread
            self.spread = self.calculate_enhanced_spread()
            
            # Calculate base quotes
            half_spread = self.spread / 2
            bid_price = current_price - half_spread
            ask_price = current_price + half_spread
            
            # Enhanced inventory skew with risk management
            inventory_ratio = abs(self.inventory) / self.p.max_inventory
            
            if self.inventory > 0:  # Long inventory, encourage selling
                # More aggressive skew when inventory is high
                skew_factor = min(0.2, inventory_ratio * 0.5)
                bid_price -= half_spread * skew_factor  # Lower bid to discourage buying
                ask_price += half_spread * skew_factor  # Higher ask to encourage selling
                
            elif self.inventory < 0:  # Short inventory, encourage buying
                # More aggressive skew when short inventory is high
                skew_factor = min(0.2, inventory_ratio * 0.5)
                bid_price += half_spread * skew_factor  # Higher bid to encourage buying
                ask_price -= half_spread * skew_factor  # Lower ask to discourage selling
            
            # Apply risk management - avoid extreme quotes
            max_skew = self.p.spread_width * 0.5
            bid_price = max(current_price * (1 - max_skew), bid_price)
            ask_price = min(current_price * (1 + max_skew), ask_price)
            
            return bid_price, ask_price
            
        except Exception as e:
            self.logger.error(f"Error calculating enhanced quotes: {e}")
            return current_price * 0.999, current_price * 1.001

    def check_risk_limits(self) -> bool:
        """Check if we should continue trading based on risk limits"""
        try:
            current_value = self.broker.get_value()
            
            # Update peak value
            if current_value > self.peak_portfolio_value:
                self.peak_portfolio_value = current_value
            
            # Calculate drawdown
            self.current_drawdown = (self.peak_portfolio_value - current_value) / self.peak_portfolio_value
            
            # Check drawdown limit
            if self.current_drawdown > self.p.max_drawdown_limit:
                self.logger.warning(f"Max drawdown exceeded: {self.current_drawdown:.2%} > {self.p.max_drawdown_limit:.2%}")
                return False
            
            # Check inventory limits
            if abs(self.inventory) >= self.p.max_inventory:
                self.logger.warning(f"Max inventory exceeded: {abs(self.inventory)} >= {self.p.max_inventory}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking risk limits: {e}")
            return False

    def calculate_position_size(self, signal_strength: float = 1.0) -> float:
        """Calculate enhanced position size with risk management"""
        try:
            # Base size with risk management
            base_size = self.p.order_size * self.p.position_size_multiplier
            
            # Inventory-based sizing (smaller when inventory is high)
            inventory_ratio = abs(self.inventory) / self.p.max_inventory
            inventory_multiplier = max(0.3, 1.0 - inventory_ratio)  # Minimum 30% size
            
            # Volatility-based sizing
            current_vol = self.atr[0] / self.dataclose[0] if self.dataclose[0] > 0 else 0
            vol_multiplier = min(1.5, 1.0 / (1.0 + current_vol * 5))  # Reduce size in high vol
            
            # Regime-based sizing
            regime_multipliers = {
                'high_volatility': 0.7,
                'low_volatility': 1.2,
                'trending': 0.8,
                'downtrend': 0.6,
                'neutral': 1.0
            }
            regime_multiplier = regime_multipliers.get(self.current_regime, 1.0)
            
            # Calculate final size
            position_size = base_size * inventory_multiplier * vol_multiplier * regime_multiplier
            
            # Apply minimum size constraint
            position_size = max(position_size, 0.1)
            
            self.log(f'Enhanced Position Size: Base={base_size:.2f}, Inventory={inventory_multiplier:.2f}, '
                    f'Volatility={vol_multiplier:.2f}, Regime={regime_multiplier:.2f}, '
                    f'Final={position_size:.2f}')
            
            return position_size
            
        except Exception as e:
            self.logger.error(f"Error calculating enhanced position size: {e}")
            return self.p.order_size * 0.8  # Conservative fallback

    def enhanced_inventory_rebalance(self):
        """Enhanced inventory rebalancing with better timing and risk management"""
        try:
            # Check if rebalancing is needed
            if abs(self.inventory) < self.p.inventory_rebalance_threshold:
                return
            
            # Check if we're in a high-risk regime
            if self.current_regime in ['high_volatility', 'downtrend']:
                self.logger.info(f"Skipping rebalancing in {self.current_regime} regime")
                return
            
            # Cancel all orders first
            self.cancel_all_orders()
            
            # Calculate optimal rebalance size
            target_inventory = 0
            current_inventory = self.inventory
            
            # Use partial rebalancing to reduce market impact
            rebalance_ratio = min(0.7, abs(current_inventory) / self.p.max_inventory)
            rebalance_size = abs(current_inventory) * rebalance_ratio
            
            # Ensure minimum meaningful size
            rebalance_size = max(rebalance_size, 0.5)
            
            # Place market order with enhanced timing
            if current_inventory > 0:  # Long, sell to reduce
                self.sell(size=rebalance_size, exectype=bt.Order.Market)
                self.logger.info(f"Enhanced rebalancing: Selling {rebalance_size} to reduce long inventory "
                              f"(current: {current_inventory})")
            elif current_inventory < 0:  # Short, buy to reduce
                self.buy(size=rebalance_size, exectype=bt.Order.Market)
                self.logger.info(f"Enhanced rebalancing: Buying {rebalance_size} to reduce short inventory "
                              f"(current: {current_inventory})")
            
            # Track rebalancing time
            self.holding_start_time = self.datas[0].datetime.datetime(0)
            
        except Exception as e:
            self.logger.error(f"Error in enhanced inventory rebalancing: {e}")

    def place_enhanced_market_making_orders(self):
        """Place enhanced market making orders with better risk management"""
        try:
            # Check risk limits before placing orders
            if not self.check_risk_limits():
                self.logger.info("Risk limits exceeded, skipping order placement")
                return
            
            # Cancel existing orders first
            self.cancel_all_orders()
            
            # Calculate enhanced quotes
            bid_price, ask_price = self.calculate_enhanced_quotes()
            
            # Calculate enhanced position size
            bid_size = self.calculate_position_size(0.8)  # Slightly smaller for bids
            ask_size = self.calculate_position_size(1.0)  # Normal size for asks
            
            # Apply minimum profit threshold
            spread_profit = (ask_price - bid_price) / bid_price
            if spread_profit < self.p.min_profit_threshold:
                self.logger.info(f"Spread profit too low: {spread_profit:.6f} < {self.p.min_profit_threshold:.6f}")
                return
            
            # Check market conditions
            if self.current_regime == 'high_volatility' and spread_profit < self.p.min_profit_threshold * 2:
                self.logger.info("High volatility with insufficient spread, skipping orders")
                return
            
            # Place limit orders with enhanced validation
            orders_placed = 0
            
            # Enhanced buy order placement
            if (len(self.active_orders['buy']) < self.p.max_orders_per_side and 
                bid_price > 0 and bid_size > 0):
                
                # Validate order against current market
                if bid_price < self.dataclose[0] * 0.99:  # Sanity check
                    self.logger.warning(f"Bid price too low: {bid_price:.5f} vs market {self.dataclose[0]:.5f}")
                else:
                    buy_order = self.buy(price=bid_price, size=bid_size, exectype=bt.Order.Limit)
                    self.active_orders['buy'].append(buy_order)
                    orders_placed += 1
            
            # Enhanced sell order placement
            if (len(self.active_orders['sell']) < self.p.max_orders_per_side and 
                ask_price > 0 and ask_size > 0):
                
                # Validate order against current market
                if ask_price > self.dataclose[0] * 1.01:  # Sanity check
                    self.logger.warning(f"Ask price too high: {ask_price:.5f} vs market {self.dataclose[0]:.5f}")
                else:
                    sell_order = self.sell(price=ask_price, size=ask_size, exectype=bt.Order.Limit)
                    self.active_orders['sell'].append(sell_order)
                    orders_placed += 1
            
            if orders_placed > 0:
                self.logger.info(f"Placed {orders_placed} enhanced market making orders - "
                              f"Bid: {bid_price:.5f}, Ask: {ask_price:.5f}, "
                              f"Spread: {self.spread:.6f} ({spread_profit:.4%}), "
                              f"Inventory: {self.inventory}, Regime: {self.current_regime}")
            
            self.last_quote_time = self.datas[0].datetime.datetime(0)
            
        except Exception as e:
            self.logger.error(f"Error in place_enhanced_market_making_orders: {e}")