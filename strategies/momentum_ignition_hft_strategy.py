"""
Momentum Ignition HFT Strategy for Futures Trading
High-frequency momentum ignition strategy that creates artificial momentum
"""

import backtrader as bt
import logging
import numpy as np
from typing import Dict, Any, Tuple, List
from datetime import datetime, timedelta
from collections import deque

class MomentumIgnitionHFTStrategy(bt.Strategy):
    """
    High-Frequency Trading Momentum Ignition Strategy for Futures

    This controversial strategy creates artificial momentum by placing rapid,
    small trades to influence other market participants' behavior, then profits
    from the resulting price movement.

    WARNING: This strategy involves market manipulation techniques and may be
    illegal or heavily regulated in many jurisdictions.
    """

    params = (
        ('ignition_volume', 50),     # Number of ignition trades
        ('trade_interval', 0.1),     # Seconds between ignition trades
        ('momentum_threshold', 0.001), # Price movement to trigger momentum (0.1%)
        ('profit_target', 0.005),    # Profit target after ignition (0.5%)
        ('stop_loss', 0.002),        # Stop loss after ignition (0.2%)
        ('max_ignition_trades', 10), # Maximum ignition trades per sequence
        ('cooldown_period', 300),    # Cooldown between ignition sequences (5 minutes)
        ('volume_multiplier', 2.0),  # Volume multiplier for ignition trades
        ('adaptive_ignition', True), # Use adaptive ignition parameters
        ('risk_limit', 0.01),        # Maximum risk per ignition sequence (1%)
        ('min_market_volume', 1000), # Minimum market volume required
        ('printlog', False)
    )

    def __init__(self):
        """Initialize momentum ignition strategy"""
        self.logger = logging.getLogger(__name__)

        # Basic data feeds
        self.dataclose = self.datas[0].close
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low
        self.datavolume = self.datas[0].volume

        # Momentum ignition state
        self.ignition_active = False
        self.ignition_start_price = None
        self.ignition_start_time = None
        self.ignition_trades_placed = 0
        self.ignition_direction = 0  # 1 for bullish, -1 for bearish
        self.last_ignition_time = None

        # Position tracking
        self.main_position = 0
        self.ignition_positions = []

        # Market state tracking
        self.price_history = deque(maxlen=100)
        self.volume_history = deque(maxlen=100)
        self.momentum_score = 0.0

        # Performance tracking
        self.total_ignitions = 0
        self.successful_ignitions = 0
        self.total_pnl = 0.0
        self.ignition_cost = 0.0
        self.profit_captured = 0.0

        # Risk management
        self.daily_loss_limit = self.broker.get_cash() * 0.05  # 5% daily loss limit
        self.daily_pnl = 0.0
        self.consecutive_failures = 0

        self.logger.info("Momentum Ignition HFT Strategy initialized - USE WITH EXTREME CAUTION")

    def calculate_momentum_score(self) -> float:
        """Calculate current market momentum score"""
        try:
            if len(self.price_history) < 20:
                return 0.0

            # Calculate price momentum
            recent_prices = list(self.price_history)[-20:]
            price_momentum = (recent_prices[-1] - recent_prices[0]) / recent_prices[0]

            # Calculate volume momentum
            recent_volumes = list(self.volume_history)[-20:]
            volume_momentum = (recent_volumes[-1] - np.mean(recent_volumes[:-1])) / np.mean(recent_volumes[:-1]) if np.mean(recent_volumes[:-1]) > 0 else 0

            # Calculate rate of change
            roc = np.polyfit(range(len(recent_prices)), recent_prices, 1)[0]

            # Combine metrics
            momentum_score = (price_momentum * 0.5 + volume_momentum * 0.3 + roc * 0.2)

            return momentum_score

        except Exception as e:
            self.logger.error(f"Error calculating momentum score: {e}")
            return 0.0

    def should_start_ignition(self) -> Tuple[bool, int]:
        """Determine if ignition should be started and in which direction"""
        try:
            # Check cooldown period
            if self.last_ignition_time:
                time_since_last = (datetime.now() - self.last_ignition_time).total_seconds()
                if time_since_last < self.p.cooldown_period:
                    return False, 0

            # Check market conditions
            current_volume = self.datavolume[0]
            if current_volume < self.p.min_market_volume:
                return False, 0

            # Check daily risk limits
            if self.daily_pnl < -self.daily_loss_limit:
                return False, 0

            # Calculate momentum and market state
            self.momentum_score = self.calculate_momentum_score()

            # Determine ignition direction based on market conditions
            current_price = self.dataclose[0]

            # Check for consolidation (low volatility) - good for ignition
            if len(self.price_history) >= 10:
                recent_prices = list(self.price_history)[-10:]
                price_range = max(recent_prices) - min(recent_prices)
                avg_price = np.mean(recent_prices)
                volatility = price_range / avg_price if avg_price > 0 else 0

                # Low volatility indicates potential for ignition
                if volatility < 0.005:  # Less than 0.5% range
                    # Determine direction based on slight bias
                    if len(recent_prices) >= 5:
                        short_trend = (recent_prices[-1] - recent_prices[-5]) / recent_prices[-5]
                        if abs(short_trend) < 0.001:  # Very little recent movement
                            # Random direction for truly range-bound markets
                            direction = 1 if np.random.random() > 0.5 else -1
                            return True, direction
                        else:
                            # Follow slight trend
                            direction = 1 if short_trend > 0 else -1
                            return True, direction

            return False, 0

        except Exception as e:
            self.logger.error(f"Error determining ignition start: {e}")
            return False, 0

    def execute_ignition_sequence(self, direction: int):
        """Execute a sequence of small trades to create momentum"""
        try:
            if self.ignition_active:
                return

            self.ignition_active = True
            self.ignition_start_price = self.dataclose[0]
            self.ignition_start_time = datetime.now()
            self.ignition_trades_placed = 0
            self.ignition_direction = direction

            # Calculate ignition parameters
            base_volume = self.p.ignition_volume
            if self.p.adaptive_ignition:
                # Adjust volume based on market conditions
                market_volatility = np.std(list(self.price_history)[-20:]) / np.mean(list(self.price_history)[-20:]) if len(self.price_history) >= 20 else 0.01
                base_volume = int(base_volume * (1 + market_volatility * 10))

            # Place initial ignition trades
            self.place_ignition_trades(direction, base_volume)

            self.total_ignitions += 1
            self.last_ignition_time = datetime.now()

            self.logger.warning(f"STARTED MOMENTUM IGNITION - Direction: {'BULLISH' if direction > 0 else 'BEARISH'}, "
                              f"Volume: {base_volume}, Start Price: {self.ignition_start_price:.5f}")

        except Exception as e:
            self.logger.error(f"Error executing ignition sequence: {e}")
            self.ignition_active = False

    def place_ignition_trades(self, direction: int, total_volume: int):
        """Place small ignition trades to create momentum"""
        try:
            # Calculate trade size - spread volume across multiple small trades
            trade_size = max(1, total_volume // self.p.max_ignition_trades)
            num_trades = min(self.p.max_ignition_trades, total_volume // trade_size)

            current_price = self.dataclose[0]

            for i in range(num_trades):
                if direction > 0:  # Bullish ignition
                    # Buy small amounts to push price up
                    order = self.buy(size=trade_size, exectype=bt.Order.Market)
                else:  # Bearish ignition
                    # Sell small amounts to push price down
                    order = self.sell(size=trade_size, exectype=bt.Order.Market)

                self.ignition_positions.append({
                    'order': order,
                    'size': trade_size,
                    'direction': direction,
                    'price': current_price,
                    'timestamp': datetime.now()
                })

                self.ignition_trades_placed += 1
                self.ignition_cost += trade_size * current_price * 0.0001  # Estimated commission

                # Small delay between trades (in real HFT this would be microseconds)
                # In backtrader, we can't simulate microsecond delays, so we'll place all at once

            self.logger.info(f"Placed {num_trades} ignition trades of size {trade_size} each")

        except Exception as e:
            self.logger.error(f"Error placing ignition trades: {e}")

    def monitor_ignition_progress(self):
        """Monitor the progress of active ignition and decide when to profit"""
        try:
            if not self.ignition_active:
                return

            current_price = self.dataclose[0]
            price_change = (current_price - self.ignition_start_price) / self.ignition_start_price
            time_elapsed = (datetime.now() - self.ignition_start_time).total_seconds()

            # Check if momentum has been created
            momentum_created = False
            if self.ignition_direction > 0:  # Bullish ignition
                momentum_created = price_change >= self.p.momentum_threshold
            else:  # Bearish ignition
                momentum_created = price_change <= -self.p.momentum_threshold

            # Check profit targets and stop losses
            if momentum_created:
                # Momentum created - place main position to profit
                main_position_size = self.calculate_main_position_size()

                if self.ignition_direction > 0:
                    # Go long to profit from bullish momentum
                    main_order = self.buy(size=main_position_size, exectype=bt.Order.Market)
                else:
                    # Go short to profit from bearish momentum
                    main_order = self.sell(size=main_position_size, exectype=bt.Order.Market)

                self.main_position = main_position_size if self.ignition_direction > 0 else -main_position_size

                self.logger.warning(f"MOMENTUM CREATED - Entering main position: "
                                  f"{'LONG' if self.ignition_direction > 0 else 'SHORT'} "
                                  f"Size: {main_position_size}, Price: {current_price:.5f}")

                # Set profit target and stop loss
                self.profit_target_price = current_price * (1 + self.p.profit_target) if self.ignition_direction > 0 else current_price * (1 - self.p.profit_target)
                self.stop_loss_price = current_price * (1 - self.p.stop_loss) if self.ignition_direction > 0 else current_price * (1 + self.p.stop_loss)

            elif time_elapsed >= 30:  # 30 seconds timeout
                # Ignition failed - close any positions
                self.close_ignition_sequence("timeout")
                self.consecutive_failures += 1

        except Exception as e:
            self.logger.error(f"Error monitoring ignition progress: {e}")

    def calculate_main_position_size(self) -> float:
        """Calculate the size of the main position to profit from created momentum"""
        try:
            portfolio_value = self.broker.get_cash()
            risk_amount = portfolio_value * self.p.risk_limit

            # Base size on risk and expected move
            expected_move = self.p.profit_target
            position_size = risk_amount / (expected_move * self.dataclose[0])

            # Limit position size
            max_size = portfolio_value * 0.05  # Max 5% of portfolio
            position_size = min(position_size, max_size)

            return max(1, int(position_size))

        except Exception as e:
            self.logger.error(f"Error calculating main position size: {e}")
            return 1

    def close_ignition_sequence(self, reason: str):
        """Close the ignition sequence and any open positions"""
        try:
            if not self.ignition_active:
                return

            # Close main position if exists
            if self.main_position != 0:
                if self.main_position > 0:
                    self.sell(size=self.main_position, exectype=bt.Order.Market)
                else:
                    self.buy(size=abs(self.main_position), exectype=bt.Order.Market)

            # Calculate P&L
            end_price = self.dataclose[0]
            price_change = (end_price - self.ignition_start_price) / self.ignition_start_price

            if self.main_position > 0:
                pnl = self.main_position * (end_price - self.ignition_start_price)
            elif self.main_position < 0:
                pnl = abs(self.main_position) * (self.ignition_start_price - end_price)
            else:
                pnl = -self.ignition_cost  # Just ignition costs if no main position

            self.total_pnl += pnl
            self.daily_pnl += pnl

            if pnl > 0:
                self.successful_ignitions += 1

            # Reset ignition state
            self.ignition_active = False
            self.ignition_positions.clear()
            self.main_position = 0

            success = "SUCCESS" if pnl > 0 else "FAILED"
            self.logger.warning(f"IGNITION SEQUENCE CLOSED - {success}, Reason: {reason}, "
                              f"P&L: ${pnl:.2f}, Price Change: {price_change:.4f}")

        except Exception as e:
            self.logger.error(f"Error closing ignition sequence: {e}")

    def manage_open_positions(self):
        """Manage open main positions with profit targets and stop losses"""
        try:
            if self.main_position == 0:
                return

            current_price = self.dataclose[0]

            # Check profit target and stop loss
            if self.ignition_direction > 0:  # Long position
                if current_price >= self.profit_target_price:
                    self.close_ignition_sequence("profit_target")
                elif current_price <= self.stop_loss_price:
                    self.close_ignition_sequence("stop_loss")
            else:  # Short position
                if current_price <= self.profit_target_price:
                    self.close_ignition_sequence("profit_target")
                elif current_price >= self.stop_loss_price:
                    self.close_ignition_sequence("stop_loss")

        except Exception as e:
            self.logger.error(f"Error managing open positions: {e}")

    def next(self):
        """Main momentum ignition logic"""
        try:
            # Update price and volume history
            self.price_history.append(self.dataclose[0])
            self.volume_history.append(self.datavolume[0])

            # Check if we should start ignition
            if not self.ignition_active:
                should_start, direction = self.should_start_ignition()
                if should_start:
                    self.execute_ignition_sequence(direction)

            # Monitor active ignition
            if self.ignition_active:
                self.monitor_ignition_progress()

            # Manage open positions
            self.manage_open_positions()

        except Exception as e:
            self.logger.error(f"Error in next(): {e}")

    def notify_order(self, order):
        """Handle order notifications"""
        try:
            if order.status == order.Completed:
                self.log(f"Order executed: {'BUY' if order.isbuy() else 'SELL'} "
                        f"{order.executed.size} @ {order.executed.price:.5f}")

            elif order.status in [order.Canceled, order.Rejected]:
                self.log(f"Order {'canceled' if order.status == order.Canceled else 'rejected'}: "
                        f"{'BUY' if order.isbuy() else 'SELL'} @ {order.price:.5f}")

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
        success_rate = (self.successful_ignitions / self.total_ignitions) * 100 if self.total_ignitions > 0 else 0

        self.logger.info("=== MOMENTUM IGNITION HFT STRATEGY RESULTS ===")
        self.logger.info(f"Total Ignition Sequences: {self.total_ignitions}")
        self.logger.info(f"Successful Ignitions: {self.successful_ignitions}")
        self.logger.info(f"Success Rate: {success_rate:.1f}%")
        self.logger.info(f"Total P&L: ${self.total_pnl:.2f}")
        self.logger.info(f"Ignition Costs: ${self.ignition_cost:.2f}")
        self.logger.info(f"Profit Captured: ${self.profit_captured:.2f}")
        self.logger.info(f"Daily P&L: ${self.daily_pnl:.2f}")
        self.logger.info(f"Consecutive Failures: {self.consecutive_failures}")
        self.logger.info(f"Final Portfolio Value: ${self.broker.get_value():.2f}")
        self.logger.warning("WARNING: Momentum ignition strategies may be illegal in many jurisdictions")

if __name__ == '__main__':
    print("Momentum Ignition HFT Strategy loaded successfully - USE WITH EXTREME CAUTION")