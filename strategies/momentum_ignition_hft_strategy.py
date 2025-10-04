"""
Momentum Ignition HFT Strategy for Futures Trading
High-frequency momentum ignition strategy that creates artificial momentum
"""

import backtrader as bt
import logging
import numpy as np
from typing import Dict, Any, Tuple, List
from datetime import datetime, timedelta

class MomentumIgnitionHFTStrategy(bt.Strategy):
    """
    High-Frequency Trading Momentum Ignition Strategy for Futures

    This controversial strategy creates artificial momentum by placing rapid,
    small trades to influence market psychology and profit from the resulting
    price movements as other market participants react.
    """

    params = (
        ('momentum_threshold', 0.001),    # Minimum momentum to ignite (0.1%)
        ('ignition_volume', 5),           # Number of ignition trades
        ('max_holding_time', 30),         # Maximum holding time in seconds
        ('profit_target', 0.0005),        # Profit target per trade (0.05%)
        ('stop_loss', 0.0002),            # Stop loss per trade (0.02%)
        ('volume_surge_threshold', 2.0),  # Volume surge multiplier
        ('momentum_decay_time', 15),      # Momentum decay time in seconds
        ('risk_limit', 0.01),             # Maximum risk per ignition sequence (1%)
        ('max_trades_per_minute', 10),    # Maximum trades per minute
        ('ignition_interval', 60),        # Minimum time between ignition sequences
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

        # Momentum tracking
        self.price_momentum = []
        self.volume_momentum = []
        self.momentum_start_time = None
        self.ignition_active = False

        # Order management
        self.active_orders = []
        self.ignition_sequence = []
        self.current_position = 0
        self.entry_price = 0.0

        # Performance tracking
        self.total_trades = 0
        self.ignition_sequences = 0
        self.successful_ignitions = 0
        self.total_pnl = 0.0

        # Timing controls
        self.last_trade_time = None
        self.last_ignition_time = None
        self.trades_this_minute = 0
        self.minute_start = None

        # Initialize indicators
        self._init_indicators()

        self.logger.info("Momentum Ignition HFT Strategy initialized")

    def _init_indicators(self):
        """Initialize technical indicators"""
        # Price momentum indicators
        self.sma_short = bt.indicators.SMA(period=5)
        self.sma_long = bt.indicators.SMA(period=20)
        self.rsi = bt.indicators.RSI(period=14)

        # Volume indicators
        self.volume_sma = bt.indicators.SMA(self.datavolume, period=10)
        self.volume_ratio = self.datavolume / bt.indicators.Max(self.volume_sma, 1e-8)

    def calculate_momentum_score(self) -> Tuple[float, str]:
        """Calculate current market momentum score"""
        try:
            # Price momentum calculation
            if len(self.data) < 20:
                return 0.0, 'neutral'

            # Calculate price change over different periods
            price_change_1m = (self.dataclose[0] - self.dataclose[-1]) / self.dataclose[-1] if self.dataclose[-1] != 0 else 0
            price_change_5m = (self.dataclose[0] - self.dataclose[-5]) / self.dataclose[-5] if len(self.data) > 5 and self.dataclose[-5] != 0 else 0

            # Volume momentum
            volume_ratio = float(self.volume_ratio[0]) if len(self.volume_ratio) > 0 else 1.0

            # RSI momentum
            rsi_current = float(self.rsi[0])
            rsi_change = rsi_current - 50  # Distance from neutral

            # Combine momentum factors
            price_momentum = (price_change_1m * 0.4) + (price_change_5m * 0.6)
            volume_momentum = volume_ratio - 1.0  # Deviation from average

            # Overall momentum score
            momentum_score = (price_momentum * 0.6) + (volume_momentum * 0.3) + (rsi_change / 100 * 0.1)

            # Determine direction
            if momentum_score > self.p.momentum_threshold:
                direction = 'bullish'
            elif momentum_score < -self.p.momentum_threshold:
                direction = 'bearish'
            else:
                direction = 'neutral'

            # Store momentum for trend analysis
            self.price_momentum.append(price_momentum)
            self.volume_momentum.append(volume_momentum)

            # Keep only recent momentum data
            max_momentum_history = 50
            if len(self.price_momentum) > max_momentum_history:
                self.price_momentum = self.price_momentum[-max_momentum_history:]
                self.volume_momentum = self.volume_momentum[-max_momentum_history:]

            return abs(momentum_score), direction

        except Exception as e:
            self.logger.error(f"Error calculating momentum score: {e}")
            return 0.0, 'neutral'

    def should_ignite_momentum(self, momentum_score: float, direction: str) -> bool:
        """Determine if momentum ignition should be triggered"""
        try:
            # Check momentum threshold
            if momentum_score < self.p.momentum_threshold:
                return False

            # Check timing constraints
            current_time = datetime.now()

            # Check trades per minute limit
            if self.minute_start and (current_time - self.minute_start).seconds >= 60:
                self.trades_this_minute = 0
                self.minute_start = current_time

            if self.trades_this_minute >= self.p.max_trades_per_minute:
                return False

            # Check minimum interval between ignition sequences
            if self.last_ignition_time:
                time_since_last_ignition = (current_time - self.last_ignition_time).total_seconds()
                if time_since_last_ignition < self.p.ignition_interval:
                    return False

            # Check if already in an active ignition sequence
            if self.ignition_active:
                return False

            # Check volume conditions - need sufficient liquidity
            volume_ratio = float(self.volume_ratio[0]) if len(self.volume_ratio) > 0 else 1.0
            if volume_ratio < self.p.volume_surge_threshold:
                return False

            # Check market volatility - avoid extremely volatile conditions
            if len(self.data) >= 10:
                recent_high = max(self.datahigh[i] for i in range(-10, 1) if i >= -len(self.data))
                recent_low = min(self.datalow[i] for i in range(-10, 1) if i >= -len(self.data))
                volatility = (recent_high - recent_low) / self.dataclose[0] if self.dataclose[0] > 0 else 0

                if volatility > 0.05:  # 5% volatility threshold
                    return False

            return True

        except Exception as e:
            self.logger.error(f"Error checking ignition conditions: {e}")
            return False

    def execute_momentum_ignition(self, direction: str):
        """Execute momentum ignition sequence"""
        try:
            self.ignition_active = True
            self.ignition_sequence = []
            self.momentum_start_time = datetime.now()
            self.last_ignition_time = datetime.now()
            self.ignition_sequences += 1

            # Calculate ignition trade size
            base_size = 0.5  # Small base size for ignition
            current_price = self.dataclose[0]

            # Execute rapid sequence of small trades
            for i in range(self.p.ignition_volume):
                if direction == 'bullish':
                    # Buy small amounts to create upward momentum
                    order = self.buy(size=base_size, exectype=bt.Order.Market)
                elif direction == 'bearish':
                    # Sell small amounts to create downward momentum
                    order = self.sell(size=base_size, exectype=bt.Order.Market)
                else:
                    break

                self.ignition_sequence.append(order)
                self.active_orders.append(order)
                self.trades_this_minute += 1

                # Small delay between trades (simulated)
                # In real HFT, this would be microsecond-level timing

            self.logger.info(f"Initiated momentum ignition sequence #{self.ignition_sequences} "
                           f"with {len(self.ignition_sequence)} trades in {direction} direction")

        except Exception as e:
            self.logger.error(f"Error executing momentum ignition: {e}")
            self.ignition_active = False

    def monitor_ignition_progress(self) -> bool:
        """Monitor the progress of momentum ignition and decide when to profit"""
        try:
            if not self.ignition_active or not self.momentum_start_time:
                return False

            current_time = datetime.now()
            ignition_duration = (current_time - self.momentum_start_time).total_seconds()

            # Check if ignition has timed out
            if ignition_duration > self.p.max_holding_time:
                self.logger.info("Momentum ignition timed out, closing positions")
                self.close_ignition_positions()
                return True

            # Check if momentum has been successfully ignited
            momentum_score, current_direction = self.calculate_momentum_score()

            # If momentum has increased significantly, take profit
            if momentum_score > self.p.momentum_threshold * 2:  # 2x threshold
                self.logger.info(f"Momentum successfully ignited (score: {momentum_score:.4f}), taking profit")
                self.take_ignition_profit(current_direction)
                return True

            # Check for adverse momentum (strategy failed)
            if len(self.price_momentum) >= 5:
                recent_momentum = np.mean(self.price_momentum[-5:])
                if abs(recent_momentum) < self.p.momentum_threshold * 0.3:  # Momentum decayed
                    self.logger.info("Momentum ignition failed, cutting losses")
                    self.close_ignition_positions()
                    return True

            return False

        except Exception as e:
            self.logger.error(f"Error monitoring ignition progress: {e}")
            self.close_ignition_positions()
            return True

    def take_ignition_profit(self, direction: str):
        """Take profit from successful momentum ignition"""
        try:
            # Calculate profit-taking position size
            profit_size = len(self.ignition_sequence) * 2  # 2x the ignition volume

            if direction == 'bullish':
                # Momentum went up, take short profit
                order = self.sell(size=profit_size, exectype=bt.Order.Market)
            elif direction == 'bearish':
                # Momentum went down, take long profit
                order = self.buy(size=profit_size, exectype=bt.Order.Market)
            else:
                self.close_ignition_positions()
                return

            self.active_orders.append(order)
            self.successful_ignitions += 1

            self.logger.info(f"Taking profit from successful ignition: {profit_size} {direction} position")

        except Exception as e:
            self.logger.error(f"Error taking ignition profit: {e}")

        finally:
            self.ignition_active = False
            self.ignition_sequence = []

    def close_ignition_positions(self):
        """Close all ignition-related positions"""
        try:
            # Calculate net position from ignition sequence
            net_position = 0
            for order in self.ignition_sequence:
                if hasattr(order, 'executed') and order.executed.size != 0:
                    if order.isbuy():
                        net_position += order.executed.size
                    else:
                        net_position -= order.executed.size

            # Close net position
            if net_position > 0:
                self.sell(size=net_position, exectype=bt.Order.Market)
            elif net_position < 0:
                self.buy(size=abs(net_position), exectype=bt.Order.Market)

            self.logger.info(f"Closed ignition positions, net position was: {net_position}")

        except Exception as e:
            self.logger.error(f"Error closing ignition positions: {e}")

        finally:
            self.ignition_active = False
            self.ignition_sequence = []

    def next(self):
        """Main momentum ignition logic"""
        try:
            # Update minute tracking
            current_time = datetime.now()
            if not self.minute_start or (current_time - self.minute_start).seconds >= 60:
                self.minute_start = current_time
                self.trades_this_minute = 0

            # Monitor active ignition sequence
            if self.ignition_active:
                if self.monitor_ignition_progress():
                    return

            # Check for new ignition opportunities
            momentum_score, direction = self.calculate_momentum_score()

            if self.should_ignite_momentum(momentum_score, direction):
                self.execute_momentum_ignition(direction)

        except Exception as e:
            self.logger.error(f"Error in next(): {e}")

    def notify_order(self, order):
        """Handle order notifications"""
        try:
            if order.status == order.Completed:
                self.total_trades += 1
                self.log(f"Order executed: {'BUY' if order.isbuy() else 'SELL'} "
                        f"{order.executed.size} @ {order.executed.price:.5f}")

                # Remove from active orders
                if order in self.active_orders:
                    self.active_orders.remove(order)

            elif order.status in [order.Canceled, order.Rejected]:
                self.log(f"Order {'canceled' if order.status == order.Canceled else 'rejected'}: "
                        f"{'BUY' if order.isbuy() else 'SELL'} @ {order.price:.5f}")

                # Remove from active orders
                if order in self.active_orders:
                    self.active_orders.remove(order)

        except Exception as e:
            self.logger.error(f"Error in notify_order: {e}")

    def notify_trade(self, trade):
        """Handle trade notifications"""
        if trade.isclosed:
            self.total_pnl += trade.pnl

            win_rate = (self.successful_ignitions / self.ignition_sequences) * 100 if self.ignition_sequences > 0 else 0

            self.log(f"Trade closed - PnL: {trade.pnl:.2f}, "
                    f"Ignition Success Rate: {win_rate:.1f}%")

    def log(self, txt, dt=None):
        """Logging function"""
        if self.p.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            logging.info(f'{dt.isoformat()} {txt}')

    def stop(self):
        """Strategy stop - log final statistics"""
        success_rate = (self.successful_ignitions / self.ignition_sequences) * 100 if self.ignition_sequences > 0 else 0

        self.logger.info("=== MOMENTUM IGNITION HFT STRATEGY RESULTS ===")
        self.logger.info(f"Total Trades: {self.total_trades}")
        self.logger.info(f"Ignition Sequences: {self.ignition_sequences}")
        self.logger.info(f"Successful Ignitions: {self.successful_ignitions}")
        self.logger.info(f"Success Rate: {success_rate:.1f}%")
        self.logger.info(f"Total P&L: ${self.total_pnl:.2f}")
        self.logger.info(f"Final Portfolio Value: ${self.broker.get_value():.2f}")

if __name__ == '__main__':
    print("Momentum Ignition HFT Strategy loaded successfully")