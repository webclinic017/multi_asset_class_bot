"""
Statistical Arbitrage HFT Strategy for Futures Trading
High-frequency statistical arbitrage strategy that exploits mean-reverting relationships
"""

import backtrader as bt
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple, List
from datetime import datetime, timedelta
from scipy import stats
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler

class StatisticalArbitrageHFTStrategy(bt.Strategy):
    """
    High-Frequency Trading Statistical Arbitrage Strategy for Futures

    This strategy uses statistical models to identify and exploit temporary deviations
    from normal relationships between related futures contracts, profiting from
    mean-reverting behavior.
    """

    params = (
        ('lookback_period', 100),   # Lookback period for statistical analysis
        ('entry_threshold', 2.0),   # Standard deviations for entry signal
        ('exit_threshold', 0.5),    # Standard deviations for exit signal
        ('max_holding_time', 300),  # Maximum holding time in seconds
        ('min_relationship_strength', 0.7),  # Minimum correlation for pairs
        ('max_position_size', 5),   # Maximum position size per leg
        ('risk_limit', 0.01),       # Maximum risk per trade (1%)
        ('cointegration_test_period', 50),  # Period for cointegration test
        ('zscore_smoothing', 5),    # Smoothing period for z-score
        ('adaptive_threshold', True),  # Use adaptive entry/exit thresholds
        ('pairs_update_interval', 3600),  # Update pairs every hour
        ('printlog', False)
    )

    def __init__(self, initial_capital=None):
        """Initialize statistical arbitrage strategy
        
        Args:
            initial_capital: Optional initial capital (ignored, kept for compatibility)
        """
        self.logger = logging.getLogger(__name__)

        # For futures trading, we need multiple data feeds
        # This strategy assumes we have at least 2 related futures contracts
        if len(self.datas) < 2:
            raise ValueError("Statistical arbitrage requires at least 2 data feeds")

        # Data feeds
        self.data1 = self.datas[0]  # Primary futures contract
        self.data2 = self.datas[1]  # Related futures contract

        # Statistical analysis state
        self.price_history_1 = []
        self.price_history_2 = []
        self.spread_history = []
        self.zscore_history = []

        # Current positions and signals
        self.position_size = 0
        self.entry_time = None
        self.current_zscore = 0.0
        self.spread_mean = 0.0
        self.spread_std = 1.0

        # Pairs trading parameters
        self.hedge_ratio = 1.0  # Initially 1:1 ratio
        self.correlation = 0.0
        self.cointegrated = False

        # Performance tracking
        self.total_trades = 0
        self.winning_trades = 0
        self.total_pnl = 0.0

        # Timing
        self.last_pairs_update = None

        # Initialize statistical models
        self._init_statistical_models()

        self.logger.info("Statistical Arbitrage HFT Strategy initialized")

    def _init_statistical_models(self):
        """Initialize statistical models for pairs analysis"""
        # Linear regression for hedge ratio calculation
        self.regression_model = LinearRegression()

        # Standard scaler for normalization
        self.scaler = StandardScaler()

    def update_statistical_relationship(self):
        """Update the statistical relationship between the two assets"""
        try:
            if len(self.price_history_1) < self.p.lookback_period:
                return

            # Convert to numpy arrays
            prices_1 = np.array(self.price_history_1[-self.p.lookback_period:])
            prices_2 = np.array(self.price_history_2[-self.p.lookback_period:])

            # Calculate hedge ratio using linear regression
            X = prices_1.reshape(-1, 1)
            y = prices_2
            self.regression_model.fit(X, y)
            self.hedge_ratio = self.regression_model.coef_[0]

            # Calculate spread
            spread = prices_2 - self.hedge_ratio * prices_1
            self.spread_history = spread.tolist()

            # Calculate spread statistics
            self.spread_mean = np.mean(spread)
            self.spread_std = np.std(spread)

            # Calculate z-score
            if self.spread_std > 0:
                current_spread = prices_2[-1] - self.hedge_ratio * prices_1[-1]
                self.current_zscore = (current_spread - self.spread_mean) / self.spread_std

                # Smooth z-score
                self.zscore_history.append(self.current_zscore)
                if len(self.zscore_history) > self.p.zscore_smoothing:
                    self.zscore_history = self.zscore_history[-self.p.zscore_smoothing:]

                self.current_zscore = np.mean(self.zscore_history)

            # Calculate correlation
            correlation_matrix = np.corrcoef(prices_1, prices_2)
            self.correlation = correlation_matrix[0, 1]

            # Test for cointegration (simplified)
            self.cointegrated = abs(self.correlation) > self.p.min_relationship_strength

            self.logger.info(f"Updated statistical relationship - "
                           f"Hedge Ratio: {self.hedge_ratio:.4f}, "
                           f"Correlation: {self.correlation:.4f}, "
                           f"Z-Score: {self.current_zscore:.2f}, "
                           f"Cointegrated: {self.cointegrated}")

        except Exception as e:
            self.logger.error(f"Error updating statistical relationship: {e}")

    def calculate_adaptive_thresholds(self) -> Tuple[float, float]:
        """Calculate adaptive entry and exit thresholds based on market conditions"""
        if not self.p.adaptive_threshold:
            return self.p.entry_threshold, self.p.exit_threshold

        try:
            # Base thresholds
            entry_threshold = self.p.entry_threshold
            exit_threshold = self.p.exit_threshold

            # Adjust based on volatility
            volatility_adjustment = min(self.spread_std / abs(self.spread_mean), 2.0) if self.spread_mean != 0 else 1.0

            # Adjust based on correlation strength
            correlation_adjustment = 1.0 + (1.0 - abs(self.correlation)) * 0.5

            # Adjust based on recent performance
            if len(self.zscore_history) > 10:
                recent_volatility = np.std(self.zscore_history[-10:])
                performance_adjustment = 1.0 + recent_volatility * 0.2
            else:
                performance_adjustment = 1.0

            adaptive_entry = entry_threshold * volatility_adjustment * correlation_adjustment * performance_adjustment
            adaptive_exit = exit_threshold * volatility_adjustment

            return adaptive_entry, adaptive_exit

        except Exception as e:
            self.logger.error(f"Error calculating adaptive thresholds: {e}")
            return self.p.entry_threshold, self.p.exit_threshold

    def generate_arbitrage_signals(self) -> Dict[str, Any]:
        """Generate statistical arbitrage signals"""
        signals = {
            'action': 'hold',
            'size_1': 0,
            'size_2': 0,
            'reason': '',
            'zscore': self.current_zscore,
            'confidence': 0.0
        }

        try:
            if not self.cointegrated or len(self.price_history_1) < self.p.lookback_period:
                signals['reason'] = 'Insufficient data or no cointegration'
                return signals

            entry_threshold, exit_threshold = self.calculate_adaptive_thresholds()

            # Check for entry signals
            if abs(self.current_zscore) > entry_threshold and self.position_size == 0:
                # Enter position
                if self.current_zscore > entry_threshold:
                    # Asset 2 is overvalued relative to Asset 1, sell Asset 2 and buy Asset 1
                    signals['action'] = 'enter'
                    signals['size_1'] = self.p.max_position_size  # Buy Asset 1
                    signals['size_2'] = -self.p.max_position_size * self.hedge_ratio  # Sell Asset 2
                    signals['reason'] = f'Asset 2 overvalued (Z={self.current_zscore:.2f})'
                elif self.current_zscore < -entry_threshold:
                    # Asset 1 is overvalued relative to Asset 2, sell Asset 1 and buy Asset 2
                    signals['action'] = 'enter'
                    signals['size_1'] = -self.p.max_position_size  # Sell Asset 1
                    signals['size_2'] = self.p.max_position_size * self.hedge_ratio  # Buy Asset 2
                    signals['reason'] = f'Asset 1 overvalued (Z={self.current_zscore:.2f})'

                signals['confidence'] = min(abs(self.current_zscore) / entry_threshold, 1.0)

            # Check for exit signals
            elif self.position_size != 0:
                if abs(self.current_zscore) < exit_threshold:
                    # Exit position - spread has reverted to mean
                    signals['action'] = 'exit'
                    signals['size_1'] = -self.position_size  # Close position in Asset 1
                    signals['size_2'] = -self.position_size * self.hedge_ratio  # Close position in Asset 2
                    signals['reason'] = f'Spread reverted to mean (Z={self.current_zscore:.2f})'
                    signals['confidence'] = 1.0 - (abs(self.current_zscore) / exit_threshold)

                elif self.entry_time and (datetime.now() - self.entry_time).total_seconds() > self.p.max_holding_time:
                    # Exit due to time limit
                    signals['action'] = 'exit'
                    signals['size_1'] = -self.position_size
                    signals['size_2'] = -self.position_size * self.hedge_ratio
                    signals['reason'] = 'Maximum holding time exceeded'
                    signals['confidence'] = 0.5

            return signals

        except Exception as e:
            self.logger.error(f"Error generating arbitrage signals: {e}")
            return signals

    def execute_arbitrage_trade(self, signals: Dict[str, Any]):
        """Execute arbitrage trade"""
        try:
            if signals['action'] == 'enter':
                # Place orders for both legs simultaneously
                order1 = self.buy(size=signals['size_1'], exectype=bt.Order.Market) if signals['size_1'] > 0 else \
                        self.sell(size=abs(signals['size_1']), exectype=bt.Order.Market)

                order2 = self.buy(size=signals['size_2'], exectype=bt.Order.Market) if signals['size_2'] > 0 else \
                        self.sell(size=abs(signals['size_2']), exectype=bt.Order.Market)

                self.position_size = signals['size_1']
                self.entry_time = datetime.now()

                self.logger.info(f"Entered arbitrage position - "
                               f"Asset1: {signals['size_1']:+.1f}, "
                               f"Asset2: {signals['size_2']:+.1f}, "
                               f"Z-Score: {signals['zscore']:.2f}")

            elif signals['action'] == 'exit':
                # Close positions
                order1 = self.sell(size=abs(self.position_size), exectype=bt.Order.Market) if self.position_size > 0 else \
                        self.buy(size=abs(self.position_size), exectype=bt.Order.Market)

                order2 = self.sell(size=abs(signals['size_2']), exectype=bt.Order.Market) if signals['size_2'] > 0 else \
                        self.buy(size=abs(signals['size_2']), exectype=bt.Order.Market)

                self.position_size = 0
                self.entry_time = None

                self.logger.info(f"Exited arbitrage position - "
                               f"Z-Score: {signals['zscore']:.2f}")

        except Exception as e:
            self.logger.error(f"Error executing arbitrage trade: {e}")

    def next(self):
        """Main statistical arbitrage logic"""
        try:
            # Update price histories
            self.price_history_1.append(self.data1.close[0])
            self.price_history_2.append(self.data2.close[0])

            # Maintain history length
            max_history = max(self.p.lookback_period, self.p.cointegration_test_period) * 2
            if len(self.price_history_1) > max_history:
                self.price_history_1 = self.price_history_1[-max_history:]
                self.price_history_2 = self.price_history_2[-max_history:]

            # Update statistical relationship periodically
            current_time = self.datas[0].datetime.datetime(0)
            if (self.last_pairs_update is None or
                (current_time - self.last_pairs_update).total_seconds() >= self.p.pairs_update_interval):
                self.update_statistical_relationship()
                self.last_pairs_update = current_time

            # Generate and execute signals
            if len(self.price_history_1) >= self.p.lookback_period:
                signals = self.generate_arbitrage_signals()

                if signals['action'] != 'hold':
                    self.execute_arbitrage_trade(signals)

        except Exception as e:
            self.logger.error(f"Error in next(): {e}")

    def notify_order(self, order):
        """Handle order notifications"""
        try:
            if order.status == order.Completed:
                self.total_trades += 1
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

        self.logger.info("=== STATISTICAL ARBITRAGE HFT STRATEGY RESULTS ===")
        self.logger.info(f"Total Trades: {self.total_trades}")
        self.logger.info(f"Winning Trades: {self.winning_trades}")
        self.logger.info(f"Win Rate: {win_rate:.1f}%")
        self.logger.info(f"Total P&L: ${self.total_pnl:.2f}")
        self.logger.info(f"Final Portfolio Value: ${self.broker.get_value():.2f}")
        self.logger.info(f"Final Correlation: {self.correlation:.4f}")
        self.logger.info(f"Cointegrated: {self.cointegrated}")

if __name__ == '__main__':
    print("Statistical Arbitrage HFT Strategy loaded successfully")