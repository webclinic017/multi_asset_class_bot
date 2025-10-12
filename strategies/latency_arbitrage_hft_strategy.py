"""
Latency Arbitrage HFT Strategy for Futures Trading
High-frequency latency arbitrage strategy that exploits price discrepancies
"""

import backtrader as bt
import logging
import numpy as np
from typing import Dict, Any, Tuple, List
from datetime import datetime, timedelta

class LatencyArbitrageHFTStrategy(bt.Strategy):
    """
    High-Frequency Trading Latency Arbitrage Strategy for Futures

    This strategy exploits microsecond-level price discrepancies between
    different futures exchanges or market data feeds by acting faster
    than other market participants.
    """

    params = (
        ('max_position_size', 10),         # Maximum position size
        ('min_profit_threshold', 0.0001),  # Minimum profit target (0.01%)
        ('max_holding_time', 60),          # Maximum holding time in seconds
        ('latency_threshold', 0.5),        # Latency threshold in seconds
        ('price_tolerance', 0.0002),       # Price tolerance for arbitrage (0.02%)
        ('risk_limit', 0.005),             # Maximum risk per trade (0.5%)
        ('exchange_count', 2),             # Number of exchanges to monitor
        ('arbitrage_window', 5),           # Time window for arbitrage opportunity
        ('volume_threshold', 100),         # Minimum volume threshold
        ('spread_threshold', 0.001),       # Maximum acceptable spread (0.1%)
        ('adaptive_position_sizing', True), # Use adaptive position sizing
        ('order_refresh_time', 1),         # Order refresh interval in seconds
        ('exchange_comparison_window', 10), # Window for comparing exchange prices
        ('profit_taking_threshold', 0.0002), # Profit taking threshold (0.02%)
        ('stop_loss_multiplier', 2.0),     # Stop loss multiplier relative to profit target
        ('printlog', False)
    )

    def __init__(self, initial_capital=None):
        """Initialize latency arbitrage strategy
        
        Args:
            initial_capital: Optional initial capital (ignored, kept for compatibility)
        """
        self.logger = logging.getLogger(__name__)

        # For latency arbitrage, we need multiple data feeds from different exchanges
        # This strategy assumes we have at least 2 data feeds representing different exchanges
        if len(self.datas) < 2:
            raise ValueError("Latency arbitrage requires at least 2 data feeds from different exchanges")

        # Data feeds from different exchanges
        self.exchange1 = self.datas[0]  # Primary exchange
        self.exchange2 = self.datas[1]  # Secondary exchange

        # Price tracking
        self.exchange1_prices = []
        self.exchange2_prices = []
        self.price_discrepancies = []

        # Order management
        self.active_orders = []
        self.current_position = 0
        self.entry_time = None
        self.entry_price = 0.0

        # Performance tracking
        self.total_trades = 0
        self.winning_trades = 0
        self.total_pnl = 0.0

        # Latency tracking
        self.last_order_time = None
        self.execution_latencies = []

        self.logger.info("Latency Arbitrage HFT Strategy initialized")

    def calculate_price_discrepancy(self) -> Tuple[float, str]:
        """Calculate price discrepancy between exchanges"""
        try:
            current_price_1 = self.exchange1.close[0]
            current_price_2 = self.exchange2.close[0]

            if current_price_1 == 0 or current_price_2 == 0:
                return 0.0, 'neutral'

            # Calculate percentage difference
            price_diff = abs(current_price_1 - current_price_2)
            avg_price = (current_price_1 + current_price_2) / 2
            discrepancy_pct = price_diff / avg_price if avg_price > 0 else 0

            # Determine direction
            if current_price_1 > current_price_2:
                direction = 'exchange1_higher'
            elif current_price_2 > current_price_1:
                direction = 'exchange2_higher'
            else:
                direction = 'neutral'

            # Store discrepancy for analysis
            self.price_discrepancies.append(discrepancy_pct)
            if len(self.price_discrepancies) > 100:  # Keep last 100 discrepancies
                self.price_discrepancies = self.price_discrepancies[-100:]

            return discrepancy_pct, direction

        except Exception as e:
            self.logger.error(f"Error calculating price discrepancy: {e}")
            return 0.0, 'neutral'

    def should_enter_arbitrage(self, discrepancy: float, direction: str) -> bool:
        """Determine if arbitrage opportunity exists"""
        try:
            # Check if discrepancy exceeds threshold
            if discrepancy < self.p.latency_threshold:
                return False

            # Check if we have enough recent data for statistical significance
            if len(self.price_discrepancies) < 10:
                return False

            # Calculate mean and std of recent discrepancies
            recent_discrepancies = self.price_discrepancies[-20:]  # Last 20 observations
            mean_discrepancy = np.mean(recent_discrepancies)
            std_discrepancy = np.std(recent_discrepancies)

            # Check if current discrepancy is statistically significant (2+ standard deviations)
            if std_discrepancy > 0:
                z_score = (discrepancy - mean_discrepancy) / std_discrepancy
                if z_score < 2.0:
                    return False

            # Check if we have capacity for new position
            if abs(self.current_position) >= self.p.max_position_size:
                return False

            # Check timing constraints
            if self.last_order_time:
                time_since_last_order = (datetime.now() - self.last_order_time).total_seconds()
                if time_since_last_order < self.p.order_refresh_time:
                    return False

            return True

        except Exception as e:
            self.logger.error(f"Error checking arbitrage entry: {e}")
            return False

    def calculate_arbitrage_position(self, discrepancy: float, direction: str) -> Tuple[float, float]:
        """Calculate position sizes for arbitrage"""
        try:
            base_size = min(self.p.max_position_size - abs(self.current_position), 1.0)

            # Adjust size based on discrepancy magnitude
            size_multiplier = min(discrepancy / self.p.latency_threshold, 3.0)  # Max 3x base size
            position_size = base_size * size_multiplier

            # Determine buy/sell based on direction
            if direction == 'exchange1_higher':
                # Buy on exchange 2, sell on exchange 1
                size_exchange1 = -position_size  # Sell
                size_exchange2 = position_size   # Buy
            elif direction == 'exchange2_higher':
                # Buy on exchange 1, sell on exchange 2
                size_exchange1 = position_size   # Buy
                size_exchange2 = -position_size  # Sell
            else:
                return 0.0, 0.0

            return size_exchange1, size_exchange2

        except Exception as e:
            self.logger.error(f"Error calculating arbitrage position: {e}")
            return 0.0, 0.0

    def should_exit_arbitrage(self) -> bool:
        """Determine if arbitrage position should be closed"""
        try:
            if self.current_position == 0:
                return False

            # Check holding time
            if self.entry_time:
                holding_time = (datetime.now() - self.entry_time).total_seconds()
                if holding_time > self.p.max_holding_time:
                    self.logger.info(f"Exiting due to max holding time: {holding_time}s")
                    return True

            # Check profit/loss thresholds
            current_price_1 = self.exchange1.close[0]
            current_price_2 = self.exchange2.close[0]

            # Calculate current P&L
            if self.current_position > 0:  # Long exchange 1, short exchange 2
                pnl = (current_price_1 - self.entry_price) - (current_price_2 - self.entry_price)
            else:  # Short exchange 1, long exchange 2
                pnl = (self.entry_price - current_price_1) - (self.entry_price - current_price_2)

            # Check profit taking
            if pnl > self.p.profit_taking_threshold:
                self.logger.info(f"Exiting due to profit target: {pnl}")
                return True

            # Check stop loss
            stop_loss_level = -self.p.profit_taking_threshold * self.p.stop_loss_multiplier
            if pnl < stop_loss_level:
                self.logger.info(f"Exiting due to stop loss: {pnl}")
                return True

            # Check if discrepancy has converged
            discrepancy, _ = self.calculate_price_discrepancy()
            if discrepancy < self.p.min_profit_threshold:
                self.logger.info(f"Exiting due to discrepancy convergence: {discrepancy}")
                return True

            return False

        except Exception as e:
            self.logger.error(f"Error checking arbitrage exit: {e}")
            return True  # Exit on error

    def execute_arbitrage_trade(self, size_exchange1: float, size_exchange2: float):
        """Execute arbitrage trade on both exchanges"""
        try:
            # Place orders on both exchanges simultaneously
            if size_exchange1 != 0:
                order1 = self.buy(size=size_exchange1, exectype=bt.Order.Market) if size_exchange1 > 0 else \
                        self.sell(size=abs(size_exchange1), exectype=bt.Order.Market)

            if size_exchange2 != 0:
                order2 = self.buy(size=size_exchange2, exectype=bt.Order.Market) if size_exchange2 > 0 else \
                        self.sell(size=abs(size_exchange2), exectype=bt.Order.Market)

            # Update position tracking
            self.current_position += size_exchange1  # Track position on primary exchange
            self.entry_time = datetime.now()
            self.entry_price = self.exchange1.close[0]
            self.last_order_time = datetime.now()

            self.logger.info(f"Executed arbitrage trade - Exchange1: {size_exchange1:+.1f}, "
                           f"Exchange2: {size_exchange2:+.1f}, Total Position: {self.current_position}")

        except Exception as e:
            self.logger.error(f"Error executing arbitrage trade: {e}")

    def close_arbitrage_position(self):
        """Close arbitrage position"""
        try:
            # Get actual position from broker
            position = self.getposition(self.data)
            
            if position.size != 0:
                # Close the entire position to register as a complete trade
                if position.size > 0:
                    self.sell(size=position.size, exectype=bt.Order.Market)
                    self.logger.info(f"Closing long arbitrage position: {position.size} units")
                else:
                    self.buy(size=abs(position.size), exectype=bt.Order.Market)
                    self.logger.info(f"Closing short arbitrage position: {abs(position.size)} units")

            self.current_position = 0
            self.entry_time = None
            self.entry_price = 0.0

        except Exception as e:
            self.logger.error(f"Error closing arbitrage position: {e}")

    def next(self):
        """Main latency arbitrage logic"""
        try:
            # Update price histories
            self.exchange1_prices.append(self.exchange1.close[0])
            self.exchange2_prices.append(self.exchange2.close[0])

            # Maintain history length
            max_history = 1000
            if len(self.exchange1_prices) > max_history:
                self.exchange1_prices = self.exchange1_prices[-max_history:]
                self.exchange2_prices = self.exchange2_prices[-max_history:]

            # Calculate current price discrepancy
            discrepancy, direction = self.calculate_price_discrepancy()

            # Check for exit conditions first
            if self.should_exit_arbitrage():
                self.close_arbitrage_position()
                self.total_trades += 1

            # Check for entry conditions
            elif self.should_enter_arbitrage(discrepancy, direction):
                size_exchange1, size_exchange2 = self.calculate_arbitrage_position(discrepancy, direction)
                if size_exchange1 != 0 or size_exchange2 != 0:
                    self.execute_arbitrage_trade(size_exchange1, size_exchange2)

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
            self.total_pnl += trade.pnl
            if trade.pnl > 0:
                self.winning_trades += 1

            win_rate = (self.winning_trades / self.total_trades) * 100 if self.total_trades > 0 else 0

            self.log(f"Trade closed - PnL: {trade.pnl:.2f}, Win Rate: {win_rate:.1f}%")

    def log(self, txt, dt=None):
        """Logging function"""
        if self.p.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            logging.info(f'{dt.isoformat()} {txt}')

    def stop(self):
        """Strategy stop - close all positions and log final statistics"""
        # Close any remaining positions to register complete trades
        position = self.getposition(self.data)
        if position.size != 0:
            if position.size > 0:
                self.sell(size=position.size, exectype=bt.Order.Market)
                self.logger.info(f"Closing final long position: {position.size} units")
            else:
                self.buy(size=abs(position.size), exectype=bt.Order.Market)
                self.logger.info(f"Closing final short position: {abs(position.size)} units")
        
        win_rate = (self.winning_trades / self.total_trades) * 100 if self.total_trades > 0 else 0
        avg_latency = np.mean(self.execution_latencies) if self.execution_latencies else 0

        self.logger.info("=== LATENCY ARBITRAGE HFT STRATEGY RESULTS ===")
        self.logger.info(f"Total Trades: {self.total_trades}")
        self.logger.info(f"Winning Trades: {self.winning_trades}")
        self.logger.info(f"Win Rate: {win_rate:.1f}%")
        self.logger.info(f"Total P&L: ${self.total_pnl:.2f}")
        self.logger.info(f"Average Execution Latency: {avg_latency:.6f}s")
        self.logger.info(f"Final Portfolio Value: ${self.broker.get_value():.2f}")

if __name__ == '__main__':
    print("Latency Arbitrage HFT Strategy loaded successfully")