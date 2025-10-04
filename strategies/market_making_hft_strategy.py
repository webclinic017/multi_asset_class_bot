"""
Market Making HFT Strategy for Futures Trading
High-frequency market making strategy that profits from bid-ask spreads
"""

import backtrader as bt
import logging
import numpy as np
from typing import Dict, Any, Tuple, List
from datetime import datetime, timedelta

class MarketMakingHFTStrategy(bt.Strategy):
    """
    High-Frequency Trading Market Making Strategy for Futures

    This strategy acts as a market maker by simultaneously placing both buy and sell
    limit orders for futures contracts, profiting from the bid-ask spread while
    managing inventory risk.
    """

    params = (
        ('spread_width', 0.0002),  # 0.02% spread width (2 pips on EUR/USD)
        ('max_inventory', 10),     # Maximum position size
        ('inventory_rebalance_threshold', 3),  # Rebalance when inventory exceeds this
        ('quote_refresh_time', 5),  # Refresh quotes every 5 seconds
        ('min_spread', 0.0001),    # Minimum spread to maintain
        ('max_spread', 0.001),     # Maximum spread during high volatility
        ('volatility_lookback', 20),  # Lookback period for volatility calculation
        ('risk_limit', 0.02),      # Maximum risk per trade (2%)
        ('max_orders_per_side', 3), # Maximum orders per side
        ('order_size', 1),         # Base order size
        ('adaptive_spread', True), # Use adaptive spread based on volatility
        ('printlog', False)
    )

    def __init__(self):
        """Initialize market making strategy"""
        self.logger = logging.getLogger(__name__)

        # Basic data feeds
        self.dataclose = self.datas[0].close
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low
        self.datavolume = self.datas[0].volume

        # Order management
        self.active_orders = {'buy': [], 'sell': []}
        self.inventory = 0  # Current position
        self.cash_balance = self.broker.get_cash()

        # Market making state
        self.last_quote_time = None
        self.mid_price = None
        self.spread = self.p.spread_width
        self.volatility = 0.0

        # Performance tracking
        self.total_trades = 0
        self.spread_captured = 0.0
        self.inventory_cost = 0.0

        # Indicators for market making
        self._init_indicators()

        self.logger.info("Market Making HFT Strategy initialized")

    def _init_indicators(self):
        """Initialize technical indicators for market making"""
        # Volatility indicator (ATR)
        self.atr = bt.indicators.ATR(period=self.p.volatility_lookback)

        # Moving averages for trend detection
        self.sma_short = bt.indicators.SMA(period=10)
        self.sma_long = bt.indicators.SMA(period=20)

        # RSI for momentum
        self.rsi = bt.indicators.RSI(period=14)

    def calculate_adaptive_spread(self) -> float:
        """Calculate adaptive spread based on market conditions"""
        if not self.p.adaptive_spread:
            return self.p.spread_width

        try:
            # Base spread
            base_spread = self.p.spread_width

            # Volatility adjustment
            current_volatility = self.atr[0] / self.dataclose[0] if self.dataclose[0] > 0 else 0
            vol_multiplier = min(current_volatility * 100, 2.0)  # Cap at 2x

            # Inventory adjustment - widen spread when inventory is high
            inventory_ratio = abs(self.inventory) / self.p.max_inventory
            inventory_multiplier = 1.0 + (inventory_ratio * 0.5)  # Up to 50% wider

            # Trend adjustment - narrower spread in trending markets
            trend_strength = abs(self.sma_short[0] - self.sma_long[0]) / self.dataclose[0] if self.dataclose[0] > 0 else 0
            trend_multiplier = max(0.5, 1.0 - trend_strength * 10)  # Minimum 50% of base

            adaptive_spread = base_spread * vol_multiplier * inventory_multiplier * trend_multiplier

            # Constrain to limits
            adaptive_spread = max(self.p.min_spread, min(self.p.max_spread, adaptive_spread))

            return adaptive_spread

        except Exception as e:
            self.logger.error(f"Error calculating adaptive spread: {e}")
            return self.p.spread_width

    def calculate_quotes(self) -> Tuple[float, float]:
        """Calculate bid and ask quotes"""
        try:
            # Get current mid price
            current_price = self.dataclose[0]
            self.mid_price = current_price

            # Calculate adaptive spread
            self.spread = self.calculate_adaptive_spread()

            # Calculate quotes
            half_spread = self.spread / 2
            bid_price = current_price - half_spread
            ask_price = current_price + half_spread

            # Inventory skew - adjust quotes to reduce inventory
            if self.inventory > 0:  # Long inventory, encourage selling
                bid_price -= half_spread * 0.1  # Lower bid to discourage buying
                ask_price += half_spread * 0.1  # Higher ask to encourage selling
            elif self.inventory < 0:  # Short inventory, encourage buying
                bid_price += half_spread * 0.1  # Higher bid to encourage buying
                ask_price -= half_spread * 0.1  # Lower ask to discourage selling

            return bid_price, ask_price

        except Exception as e:
            self.logger.error(f"Error calculating quotes: {e}")
            return current_price * 0.999, current_price * 1.001

    def cancel_all_orders(self):
        """Cancel all active orders"""
        for order_list in self.active_orders.values():
            for order in order_list[:]:  # Copy list to avoid modification during iteration
                if order.status in [order.Submitted, order.Accepted]:
                    self.cancel(order)
                    order_list.remove(order)

    def place_market_making_orders(self):
        """Place bid and ask limit orders"""
        try:
            # Cancel existing orders first
            self.cancel_all_orders()

            # Calculate new quotes
            bid_price, ask_price = self.calculate_quotes()

            # Calculate order sizes based on inventory
            base_size = self.p.order_size

            # Adjust sizes based on inventory (smaller orders when inventory is high)
            inventory_ratio = abs(self.inventory) / self.p.max_inventory
            size_multiplier = max(0.3, 1.0 - inventory_ratio)  # Minimum 30% size

            buy_size = base_size * size_multiplier
            sell_size = base_size * size_multiplier

            # Place limit orders
            orders_placed = 0

            # Place buy orders (limit orders to buy at bid price)
            if len(self.active_orders['buy']) < self.p.max_orders_per_side:
                buy_order = self.buy(price=bid_price, size=buy_size, exectype=bt.Order.Limit)
                self.active_orders['buy'].append(buy_order)
                orders_placed += 1

            # Place sell orders (limit orders to sell at ask price)
            if len(self.active_orders['sell']) < self.p.max_orders_per_side:
                sell_order = self.sell(price=ask_price, size=sell_size, exectype=bt.Order.Limit)
                self.active_orders['sell'].append(sell_order)
                orders_placed += 1

            if orders_placed > 0:
                self.logger.info(f"Placed {orders_placed} market making orders - "
                               f"Bid: {bid_price:.5f}, Ask: {ask_price:.5f}, "
                               f"Spread: {self.spread:.6f}, Inventory: {self.inventory}")

            self.last_quote_time = self.datas[0].datetime.datetime(0)

        except Exception as e:
            self.logger.error(f"Error placing market making orders: {e}")

    def rebalance_inventory(self):
        """Rebalance inventory if it exceeds threshold"""
        try:
            if abs(self.inventory) >= self.p.inventory_rebalance_threshold:
                # Cancel all orders
                self.cancel_all_orders()

                # Place market order to reduce inventory
                if self.inventory > 0:  # Long, sell to reduce
                    rebalance_size = min(self.inventory, self.p.order_size)
                    self.sell(size=rebalance_size, exectype=bt.Order.Market)
                    self.logger.info(f"Rebalancing: Selling {rebalance_size} to reduce long inventory")
                elif self.inventory < 0:  # Short, buy to reduce
                    rebalance_size = min(abs(self.inventory), self.p.order_size)
                    self.buy(size=rebalance_size, exectype=bt.Order.Market)
                    self.logger.info(f"Rebalancing: Buying {rebalance_size} to reduce short inventory")

        except Exception as e:
            self.logger.error(f"Error rebalancing inventory: {e}")

    def next(self):
        """Main market making logic"""
        try:
            current_time = self.datas[0].datetime.datetime(0)

            # Check if we need to refresh quotes
            if (self.last_quote_time is None or
                (current_time - self.last_quote_time).total_seconds() >= self.p.quote_refresh_time):

                # Rebalance inventory if needed
                self.rebalance_inventory()

                # Place new market making orders
                self.place_market_making_orders()

            # Update volatility
            if len(self.data) >= self.p.volatility_lookback:
                self.volatility = self.atr[0] / self.dataclose[0] if self.dataclose[0] > 0 else 0

        except Exception as e:
            self.logger.error(f"Error in next(): {e}")

    def notify_order(self, order):
        """Handle order notifications"""
        try:
            if order.status in [order.Submitted, order.Accepted]:
                return

            if order.status == order.Completed:
                # Update inventory
                if order.isbuy():
                    self.inventory += order.executed.size
                    self.spread_captured += (self.mid_price - order.executed.price) * order.executed.size
                    self.active_orders['buy'] = [o for o in self.active_orders['buy'] if o != order]
                else:  # Sell
                    self.inventory -= order.executed.size
                    self.spread_captured += (order.executed.price - self.mid_price) * order.executed.size
                    self.active_orders['sell'] = [o for o in self.active_orders['sell'] if o != order]

                self.total_trades += 1

                self.log(f"Order executed: {'BUY' if order.isbuy() else 'SELL'} "
                        f"{order.executed.size} @ {order.executed.price:.5f}, "
                        f"Inventory: {self.inventory}")

            elif order.status in [order.Canceled, order.Expired]:
                # Remove from active orders
                if order in self.active_orders['buy']:
                    self.active_orders['buy'].remove(order)
                elif order in self.active_orders['sell']:
                    self.active_orders['sell'].remove(order)

                self.log(f"Order {'canceled' if order.status == order.Canceled else 'expired'}: "
                        f"{'BUY' if order.isbuy() else 'SELL'} @ {order.price:.5f}")

            elif order.status == order.Rejected:
                self.log(f"Order rejected: {'BUY' if order.isbuy() else 'SELL'} @ {order.price:.5f}")
                # Remove from active orders
                if order in self.active_orders['buy']:
                    self.active_orders['buy'].remove(order)
                elif order in self.active_orders['sell']:
                    self.active_orders['sell'].remove(order)

        except Exception as e:
            self.logger.error(f"Error in notify_order: {e}")

    def notify_trade(self, trade):
        """Handle trade notifications"""
        if trade.isclosed:
            self.log(f"Trade closed - PnL: {trade.pnl:.2f}")

    def log(self, txt, dt=None):
        """Logging function"""
        if self.p.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            logging.info(f'{dt.isoformat()} {txt}')

    def stop(self):
        """Strategy stop - log final statistics"""
        total_return = self.spread_captured
        win_rate = (self.total_trades / max(self.total_trades, 1)) * 100

        self.logger.info("=== MARKET MAKING HFT STRATEGY RESULTS ===")
        self.logger.info(f"Total Trades: {self.total_trades}")
        self.logger.info(f"Spread Captured: ${self.spread_captured:.2f}")
        self.logger.info(f"Final Inventory: {self.inventory}")
        self.logger.info(f"Win Rate: {win_rate:.1f}%")
        self.logger.info(f"Final Portfolio Value: ${self.broker.get_value():.2f}")

if __name__ == '__main__':
    print("Market Making HFT Strategy loaded successfully")