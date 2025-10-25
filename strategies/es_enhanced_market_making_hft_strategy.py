"""
ES-Enhanced Market Making HFT Strategy for E-mini S&P 500 Futures
Optimized for high-priced index futures with price-adjusted position sizing
"""

import backtrader as bt
import logging
import numpy as np
from typing import Dict, Any, Tuple, List
from datetime import datetime, timedelta

class ESEnhancedMarketMakingHFTStrategy(bt.Strategy):
    """
    ES-Enhanced High-Frequency Trading Market Making Strategy specifically
    designed for high-priced index futures like E-mini S&P 500
    """

    params = (
        # Core Market Making Parameters (ES-optimized)
        ('spread_width', 0.0001),  # Reduced spread for ES (0.01%)
        ('max_inventory', 2),      # Much lower inventory for ES
        ('inventory_rebalance_threshold', 1),  # Tighter threshold
        ('quote_refresh_time', 3),  # Faster refresh
        ('min_spread', 0.00005),   # Minimum spread for ES
        ('max_spread', 0.0005),    # Maximum spread for ES
        ('volatility_lookback', 10),  # Shorter lookback for ES
        ('risk_limit', 0.005),     # Much lower risk per trade (0.5%)
        ('max_orders_per_side', 1), # Single order per side for ES
        ('order_size', 0.1),       # Much smaller base size for ES
        ('adaptive_spread', True), # Enable adaptive spread
        
        # ES-Specific Risk Management
        ('max_notional_exposure', 50000),  # Max $50k exposure
        ('price_adjusted_sizing', True),   # Enable price-adjusted sizing
        ('max_contracts', 10),             # Maximum 10 contracts
        ('notional_per_trade', 5000),      # $5k notional per trade
        
        # Market Regime Detection
        ('use_regime_filter', True),
        ('trend_strength_threshold', 0.2),
        ('volatility_regime_threshold', 0.015),
        
        # Performance Optimization
        ('min_profit_threshold', 0.0001),  # Lower profit threshold
        ('max_holding_time', 180),         # Shorter holding time (3 min)
        ('rebalance_frequency', 3),        # Faster rebalancing
        
        # Transaction Cost Management
        ('commission_adjustment', False),  # Disable for testing
        ('slippage_buffer', 0.00002),      # Lower slippage buffer
        
        ('printlog', False)
    )

    def __init__(self, initial_capital=None):
        """Initialize ES-enhanced market making strategy"""
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
        self.total_notional_traded = 0.0

        # Risk management
        self.peak_portfolio_value = self.broker.get_value()
        self.current_drawdown = 0.0
        self.holding_start_time = None

        # Indicators for market making
        self._init_indicators()

        self.logger.info("ES-Enhanced Market Making HFT Strategy initialized")

    def _init_indicators(self):
        """Initialize technical indicators for ES market making"""
        # Volatility indicators
        self.atr = bt.indicators.ATR(period=self.p.volatility_lookback)
        self.atr_percent = bt.indicators.PercentChange(self.atr, period=1)
        
        # Trend detection
        self.ema_fast = bt.indicators.EMA(period=3)
        self.ema_slow = bt.indicators.EMA(period=8)
        self.trend_strength = bt.indicators.Momentum(period=5)
        
        # Volume analysis
        self.volume_sma = bt.indicators.SMA(self.datavolume, period=5)
        self.volume_ratio = self.datavolume / bt.indicators.Max(self.volume_sma, 1e-8)
        
        # Market regime detection
        self.rsi = bt.indicators.RSI(period=10)
        self.macd = bt.indicators.MACD(period_me1=3, period_me2=8, period_signal=2)

    def calculate_es_adjusted_position_size(self) -> float:
        """Calculate ES-adjusted position size based on price and risk limits"""
        try:
            current_price = self.dataclose[0]
            if current_price <= 0:
                return 0.1
            
            # Base size with price adjustment
            base_notional = self.p.notional_per_trade
            base_size = base_notional / current_price
            
            # Apply maximum contract limit
            base_size = min(base_size, self.p.max_contracts)
            
            # Inventory-based sizing (much more conservative for ES)
            inventory_ratio = abs(self.inventory) / self.p.max_inventory
            inventory_multiplier = max(0.2, 1.0 - inventory_ratio * 0.8)  # More aggressive reduction
            
            # Volatility-based sizing for ES
            current_vol = self.atr[0] / current_price if current_price > 0 else 0
            vol_multiplier = min(2.0, 1.0 / (1.0 + current_vol * 3))  # More conservative
            
            # Notional exposure check
            current_notional = abs(self.inventory) * current_price
            exposure_ratio = current_notional / self.p.max_notional_exposure
            exposure_multiplier = max(0.1, 1.0 - exposure_ratio)  # Strong exposure reduction
            
            # Calculate final size
            position_size = (base_size * inventory_multiplier * vol_multiplier * 
                           exposure_multiplier * self.p.order_size)
            
            # Apply minimum size constraint
            position_size = max(position_size, 0.01)
            
            self.log(f'ES Position Size: Base={base_size:.3f}, Inventory={inventory_multiplier:.2f}, '
                    f'Volatility={vol_multiplier:.2f}, Exposure={exposure_multiplier:.2f}, '
                    f'Final={position_size:.3f}, Notional=${position_size * current_price:.0f}')
            
            return position_size
            
        except Exception as e:
            self.logger.error(f"Error calculating ES position size: {e}")
            return 0.01  # Very conservative fallback

    def detect_es_market_regime(self) -> str:
        """Detect market regime specifically for ES futures"""
        try:
            current_price = self.dataclose[0]
            if current_price <= 0:
                return 'neutral'
            
            # Volatility-based regime for ES
            current_vol = self.atr[0] / current_price if current_price > 0 else 0
            
            if current_vol > self.p.volatility_regime_threshold:
                return 'high_volatility'
            elif current_vol < 0.008:
                return 'low_volatility'
            
            # Trend-based regime for ES
            if len(self.data) >= 8:
                trend_score = (self.ema_fast[0] - self.ema_slow[0]) / current_price
                
                if abs(trend_score) > self.p.trend_strength_threshold:
                    return 'trending' if trend_score > 0 else 'downtrend'
            
            return 'neutral'
            
        except Exception as e:
            self.logger.error(f"Error detecting ES market regime: {e}")
            return 'neutral'

    def calculate_es_enhanced_spread(self) -> float:
        """Calculate ES-enhanced adaptive spread"""
        if not self.p.adaptive_spread:
            return self.p.spread_width

        try:
            current_price = self.dataclose[0]
            if current_price <= 0:
                return self.p.spread_width
            
            # Base spread (much tighter for ES)
            base_spread = self.p.spread_width
            
            # Volatility adjustment (more conservative for ES)
            current_volatility = self.atr[0] / current_price if current_price > 0 else 0
            vol_multiplier = 1.0 + (current_volatility * 5)  # More conservative scaling
            
            # Inventory adjustment (much more aggressive for ES)
            inventory_ratio = abs(self.inventory) / self.p.max_inventory
            inventory_multiplier = 1.0 + (inventory_ratio * 0.5)  # More aggressive widening
            
            # Market regime adjustment for ES
            regime_multipliers = {
                'high_volatility': 2.0,    # Wider in high vol
                'low_volatility': 0.7,     # Tighter in low vol
                'trending': 1.3,           # Wider in trending
                'downtrend': 1.5,          # Much wider in downtrend
                'neutral': 1.0
            }
            regime_multiplier = regime_multipliers.get(self.current_regime, 1.0)
            
            # Volume adjustment for ES
            if self.volume_ratio[0] > 2.0:
                volume_multiplier = 0.8  # Tighter in high volume
            elif self.volume_ratio[0] < 0.5:
                volume_multiplier = 1.3  # Wider in low volume
            else:
                volume_multiplier = 1.0
            
            # Calculate final spread
            adaptive_spread = (base_spread * vol_multiplier * inventory_multiplier * 
                             regime_multiplier * volume_multiplier)
            
            # Apply commission and slippage adjustment
            if self.p.commission_adjustment:
                commission_impact = self.p.slippage_buffer * 2
                adaptive_spread += commission_impact
            
            # Constrain to limits
            adaptive_spread = max(self.p.min_spread, min(self.p.max_spread, adaptive_spread))
            
            return adaptive_spread
            
        except Exception as e:
            self.logger.error(f"Error calculating ES enhanced spread: {e}")
            return self.p.spread_width

    def check_es_risk_limits(self) -> bool:
        """Check ES-specific risk limits"""
        try:
            current_value = self.broker.get_value()
            current_price = self.dataclose[0]

            if current_price <= 0:
                return False

            # Update peak value
            if current_value > self.peak_portfolio_value:
                self.peak_portfolio_value = current_value

            # Calculate drawdown
            self.current_drawdown = (self.peak_portfolio_value - current_value) / self.peak_portfolio_value

            # Check drawdown limit (default to 20% if not set)
            max_drawdown_limit = getattr(self.p, 'max_drawdown_limit', 0.20)
            if self.current_drawdown > max_drawdown_limit:
                self.logger.warning(f"ES Max drawdown exceeded: {self.current_drawdown:.2%} > {max_drawdown_limit:.2%}")
                return False

            # Check inventory limits
            if abs(self.inventory) >= self.p.max_inventory:
                self.logger.warning(f"ES Max inventory exceeded: {abs(self.inventory)} >= {self.p.max_inventory}")
                return False

            # Check notional exposure for ES
            current_notional = abs(self.inventory) * current_price
            if current_notional > self.p.max_notional_exposure:
                self.logger.warning(f"ES Max notional exposure exceeded: ${current_notional:.0f} > ${self.p.max_notional_exposure:.0f}")
                return False

            return True

        except Exception as e:
            self.logger.error(f"Error checking ES risk limits: {e}")
            return False

    def cancel_all_orders(self):
        """Cancel all active orders"""
        for order_list in self.active_orders.values():
            for order in order_list[:]:  # Copy list to avoid modification during iteration
                if order.status in [order.Submitted, order.Accepted]:
                    self.cancel(order)
                    order_list.remove(order)

    def place_es_enhanced_market_making_orders(self):
        """Place ES-enhanced market making orders with strict risk management"""
        try:
            # Check risk limits before placing orders
            if not self.check_es_risk_limits():
                self.logger.info("ES Risk limits exceeded, skipping order placement")
                return

            # Cancel existing orders first
            self.cancel_all_orders()

            # Update market regime
            self.current_regime = self.detect_es_market_regime()

            # Calculate enhanced quotes
            current_price = self.dataclose[0]
            if current_price <= 0:
                return

            self.spread = self.calculate_es_enhanced_spread()
            half_spread = self.spread / 2
            bid_price = current_price - half_spread
            ask_price = current_price + half_spread

            # Calculate ES-adjusted position size
            bid_size = self.calculate_es_adjusted_position_size()
            ask_size = self.calculate_es_adjusted_position_size()

            # Apply minimum profit threshold
            spread_profit = (ask_price - bid_price) / bid_price
            if spread_profit < self.p.min_profit_threshold:
                self.logger.info(f"ES Spread profit too low: {spread_profit:.6f} < {self.p.min_profit_threshold:.6f}")
                return

            # Check market conditions for ES
            if self.current_regime == 'high_volatility' and spread_profit < self.p.min_profit_threshold * 2:
                self.logger.info("ES High volatility with insufficient spread, skipping orders")
                return

            # Enhanced inventory skew for ES
            inventory_ratio = abs(self.inventory) / self.p.max_inventory

            if self.inventory > 0:  # Long inventory, encourage selling
                skew_factor = min(0.3, inventory_ratio * 0.8)  # More aggressive skew
                bid_price -= half_spread * skew_factor  # Lower bid to discourage buying
                ask_price += half_spread * skew_factor  # Higher ask to encourage selling

            elif self.inventory < 0:  # Short inventory, encourage buying
                skew_factor = min(0.3, inventory_ratio * 0.8)  # More aggressive skew
                bid_price += half_spread * skew_factor  # Higher bid to encourage buying
                ask_price -= half_spread * skew_factor  # Lower ask to discourage selling

            # Apply risk management - avoid extreme quotes
            max_skew = self.p.spread_width * 0.6
            bid_price = max(current_price * (1 - max_skew), bid_price)
            ask_price = min(current_price * (1 + max_skew), ask_price)

            # Validate prices
            if bid_price <= 0 or ask_price <= 0 or bid_price >= ask_price:
                self.logger.warning(f"ES Invalid quotes: Bid={bid_price:.2f}, Ask={ask_price:.2f}")
                return

            # Place limit orders with enhanced validation
            orders_placed = 0

            # Enhanced buy order placement for ES
            if (len(self.active_orders['buy']) < self.p.max_orders_per_side and
                bid_price > 0 and bid_size > 0):

                # Additional validation for ES
                if bid_price < current_price * 0.995:  # Stricter sanity check
                    self.logger.warning(f"ES Bid price too low: {bid_price:.2f} vs market {current_price:.2f}")
                else:
                    buy_order = self.buy(price=bid_price, size=bid_size, exectype=bt.Order.Limit)
                    self.active_orders['buy'].append(buy_order)
                    orders_placed += 1

            # Enhanced sell order placement for ES
            if (len(self.active_orders['sell']) < self.p.max_orders_per_side and
                ask_price > 0 and ask_size > 0):

                # Additional validation for ES
                if ask_price > current_price * 1.005:  # Stricter sanity check
                    self.logger.warning(f"ES Ask price too high: {ask_price:.2f} vs market {current_price:.2f}")
                else:
                    sell_order = self.sell(price=ask_price, size=ask_size, exectype=bt.Order.Limit)
                    self.active_orders['sell'].append(sell_order)
                    orders_placed += 1

            if orders_placed > 0:
                self.log(f"Placed {orders_placed} ES-enhanced market making orders - "
                        f"Bid: ${bid_price:.2f}, Ask: ${ask_price:.2f}, "
                        f"Spread: {self.spread:.6f} ({spread_profit:.4%}), "
                        f"Inventory: {self.inventory}, Regime: {self.current_regime}, "
                        f"Notional: ${bid_size * current_price:.0f}/${ask_size * current_price:.0f}")

            self.last_quote_time = self.datas[0].datetime.datetime(0)

        except Exception as e:
            self.logger.error(f"Error placing ES enhanced market making orders: {e}")

    def enhanced_es_inventory_rebalance(self):
        """Enhanced ES inventory rebalancing with immediate action"""
        try:
            # Check if rebalancing is needed
            if abs(self.inventory) < self.p.inventory_rebalance_threshold:
                return
            
            # Check if we're in a high-risk regime for ES
            if self.current_regime in ['high_volatility', 'downtrend']:
                self.logger.info(f"Skipping ES rebalancing in {self.current_regime} regime")
                return
            
            # Cancel all orders first
            self.cancel_all_orders()
            
            # Calculate optimal rebalance size for ES
            current_price = self.dataclose[0]
            if current_price <= 0:
                return
            
            current_inventory = self.inventory
            
            # Use aggressive partial rebalancing for ES
            rebalance_ratio = min(0.8, abs(current_inventory) / self.p.max_inventory)
            rebalance_size = abs(current_inventory) * rebalance_ratio
            
            # Ensure minimum meaningful size for ES
            rebalance_size = max(rebalance_size, 0.05)
            
            # Apply notional limit check
            rebalance_notional = rebalance_size * current_price
            if rebalance_notional > self.p.max_notional_exposure * 0.3:  # 30% of max
                rebalance_size = (self.p.max_notional_exposure * 0.3) / current_price
            
            # Place market order with enhanced timing for ES
            if current_inventory > 0:  # Long, sell to reduce
                self.sell(size=rebalance_size, exectype=bt.Order.Market)
                self.logger.info(f"ES Enhanced rebalancing: Selling {rebalance_size} to reduce long inventory "
                              f"(current: {current_inventory}, notional: ${rebalance_notional:.0f})")
            elif current_inventory < 0:  # Short, buy to reduce
                self.buy(size=rebalance_size, exectype=bt.Order.Market)
                self.logger.info(f"ES Enhanced rebalancing: Buying {rebalance_size} to reduce short inventory "
                              f"(current: {current_inventory}, notional: ${rebalance_notional:.0f})")
            
            # Track rebalancing time
            self.holding_start_time = self.datas[0].datetime.datetime(0)
            
        except Exception as e:
            self.logger.error(f"Error in ES enhanced inventory rebalancing: {e}")

    def next(self):
        """Main ES market making logic"""
        try:
            current_time = self.datas[0].datetime.datetime(0)
            
            # Update market regime
            self.current_regime = self.detect_es_market_regime()
            
            # Check if we need to refresh quotes
            if (self.last_quote_time is None or
                (current_time - self.last_quote_time).total_seconds() >= self.p.quote_refresh_time):
                
                # Enhanced inventory rebalancing if needed
                self.enhanced_es_inventory_rebalance()
                
                # Place new ES market making orders
                self.place_es_enhanced_market_making_orders()
            
            # Update volatility
            if len(self.data) >= self.p.volatility_lookback:
                self.volatility = self.atr[0] / self.dataclose[0] if self.dataclose[0] > 0 else 0
            
        except Exception as e:
            self.logger.error(f"Error in ES next(): {e}")

    def notify_order(self, order):
        """Handle order notifications for ES"""
        try:
            if order.status in [order.Submitted, order.Accepted]:
                return

            if order.status == order.Completed:
                # Update inventory
                if order.isbuy():
                    self.inventory += order.executed.size
                    self.spread_captured += (self.mid_price - order.executed.price) * order.executed.size
                    self.active_orders['buy'] = [o for o in self.active_orders['buy'] if o != order]
                    self.total_notional_traded += order.executed.price * order.executed.size
                else:  # Sell
                    self.inventory -= order.executed.size
                    self.spread_captured += (order.executed.price - self.mid_price) * order.executed.size
                    self.active_orders['sell'] = [o for o in self.active_orders['sell'] if o != order]
                    self.total_notional_traded += order.executed.price * order.executed.size

                self.total_trades += 1

                self.log(f"ES Order executed: {'BUY' if order.isbuy() else 'SELL'} "
                        f"{order.executed.size} @ ${order.executed.price:.2f}, "
                        f"Inventory: {self.inventory}, Notional: ${order.executed.price * order.executed.size:.0f}")

            elif order.status in [order.Canceled, order.Expired]:
                # Remove from active orders
                if order in self.active_orders['buy']:
                    self.active_orders['buy'].remove(order)
                elif order in self.active_orders['sell']:
                    self.active_orders['sell'].remove(order)

                self.log(f"ES Order {'canceled' if order.status == order.Canceled else 'expired'}: "
                        f"{'BUY' if order.isbuy() else 'SELL'} @ ${order.price:.2f}")

            elif order.status == order.Rejected:
                self.log(f"ES Order rejected: {'BUY' if order.isbuy() else 'SELL'} @ ${order.price:.2f}")
                # Remove from active orders
                if order in self.active_orders['buy']:
                    self.active_orders['buy'].remove(order)
                elif order in self.active_orders['sell']:
                    self.active_orders['sell'].remove(order)

        except Exception as e:
            self.logger.error(f"Error in ES notify_order: {e}")

    def notify_trade(self, trade):
        """Handle trade notifications for ES"""
        if trade.isclosed:
            self.log(f"ES Trade closed - PnL: ${trade.pnl:.2f}, Commission: ${trade.pnlcomm - trade.pnl:.2f}")

    def log(self, txt, dt=None):
        """Logging function for ES"""
        if self.p.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            logging.info(f'{dt.isoformat()} ES {txt}')

    def stop(self):
        """Strategy stop - close all positions and log final ES statistics"""
        # Close any remaining inventory to register complete trades
        position = self.getposition(self.data)
        if position.size != 0:
            current_price = self.dataclose[0]
            if current_price > 0:
                if position.size > 0:
                    self.sell(size=position.size, exectype=bt.Order.Market)
                    self.logger.info(f"ES Closing final long position: {position.size} units")
                else:
                    self.buy(size=abs(position.size), exectype=bt.Order.Market)
                    self.logger.info(f"ES Closing final short position: {abs(position.size)} units")
        
        total_return = self.spread_captured
        win_rate = (self.total_trades / max(self.total_trades, 1)) * 100
        final_value = self.broker.get_value()
        total_return_pct = (final_value - 100000) / 100000 * 100

        self.logger.info("=== ES-ENHANCED MARKET MAKING HFT STRATEGY RESULTS ===")
        self.logger.info(f"Total Trades: {self.total_trades}")
        self.logger.info(f"Spread Captured: ${self.spread_captured:.2f}")
        self.logger.info(f"Final Inventory: {self.inventory}")
        self.logger.info(f"Win Rate: {win_rate:.1f}%")
        self.logger.info(f"Total Notional Traded: ${self.total_notional_traded:.0f}")
        self.logger.info(f"Final Portfolio Value: ${final_value:.2f}")
        self.logger.info(f"Total Return: {total_return_pct:.2f}%")
        self.logger.info(f"Max Inventory Held: {self.max_inventory_held}")

if __name__ == '__main__':
    print("ES-Enhanced Market Making HFT Strategy loaded successfully")
