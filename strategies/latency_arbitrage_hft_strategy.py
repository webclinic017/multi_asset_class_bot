"""
Latency Arbitrage HFT Strategy for Futures Trading
High-frequency latency arbitrage strategy that exploits price discrepancies across exchanges
"""

import backtrader as bt
import logging
import numpy as np
from typing import Dict, Any, Tuple, List
from datetime import datetime, timedelta
from collections import deque

class LatencyArbitrageHFTStrategy(bt.Strategy):
    """
    High-Frequency Trading Latency Arbitrage Strategy for Futures

    This strategy exploits minor price discrepancies for the same futures contract
    on different exchanges by acting on market data faster than other participants.
    Requires multiple exchange feeds with minimal latency differences.
    """

    params = (
        ('max_position_size', 10),   # Maximum position size
        ('min_profit_threshold', 0.0001),  # Minimum profit threshold (0.01%)
        ('max_holding_time', 60),    # Maximum holding time in seconds
        ('latency_threshold', 0.5),  # Maximum acceptable latency difference (seconds)
        ('price_tolerance', 0.0002), # Price tolerance for arbitrage (0.02%)
        ('risk_limit', 0.005),       # Maximum risk per trade (0.5%)
        ('exchange_count', 2),       # Number of exchanges to monitor
        ('arbitrage_window', 5),     # Time window for arbitrage opportunity (seconds)
        ('volume_threshold', 100),   # Minimum volume for valid arbitrage
        ('spread_threshold', 0.001), # Maximum bid-ask spread to consider
        ('adaptive_position_sizing', True),  # Use adaptive position sizing
        ('printlog', False)
    )

    def __init__(self):
        """Initialize latency arbitrage strategy"""
        self.logger = logging.getLogger(__name__)

        # Require multiple data feeds (different exchanges)
        if len(self.datas) < self.p.exchange_count:
            raise ValueError(f"Latency arbitrage requires at least {self.p.exchange_count} data feeds (exchanges)")

        # Exchange data feeds
        self.exchanges = []
        for i in range(self.p.exchange_count):
            exchange_data = {
                'data': self.datas[i],
                'name': f'Exchange_{i+1}',
                'last_price': None,
                'last_time': None,
                'bid': None,
                'ask': None,
                'latency': 0.0,
                'price_history': deque(maxlen=100),  # Keep last 100 prices
                'time_history': deque(maxlen=100)    # Keep last 100 timestamps
            }
            self.exchanges.append(exchange_data)

        # Arbitrage state
        self.active_arbitrages = []  # List of active arbitrage positions
        self.arbitrage_opportunities = 0
        self.successful_arbitrages = 0

        # Performance tracking
        self.total_trades = 0
        self.total_pnl = 0.0
        self.best_arbitrage = 0.0
        self.worst_arbitrage = 0.0

        # Risk management
        self.daily_loss_limit = self.broker.get_cash() * 0.05  # 5% daily loss limit
        self.daily_pnl = 0.0

        self.logger.info(f"Latency Arbitrage HFT Strategy initialized with {self.p.exchange_count} exchanges")

    def update_exchange_data(self):
        """Update price and timing data for all exchanges"""
        try:
            current_time = self.datas[0].datetime.datetime(0)

            for exchange in self.exchanges:
                current_price = exchange['data'].close[0]

                # Update price history
                exchange['price_history'].append(current_price)
                exchange['time_history'].append(current_time)

                # Calculate latency (simplified - in real HFT this would be measured)
                if exchange['last_time']:
                    time_diff = (current_time - exchange['last_time']).total_seconds()
                    exchange['latency'] = time_diff
                else:
                    exchange['latency'] = 0.0

                # Update last known data
                exchange['last_price'] = current_price
                exchange['last_time'] = current_time

                # Simulate bid/ask (in real implementation, this would come from order book data)
                spread = current_price * self.p.spread_threshold
                exchange['bid'] = current_price - spread / 2
                exchange['ask'] = current_price + spread / 2

        except Exception as e:
            self.logger.error(f"Error updating exchange data: {e}")

    def find_arbitrage_opportunities(self) -> List[Dict[str, Any]]:
        """Find arbitrage opportunities across exchanges"""
        opportunities = []

        try:
            # Compare each pair of exchanges
            for i in range(len(self.exchanges)):
                for j in range(i + 1, len(self.exchanges)):
                    exchange_a = self.exchanges[i]
                    exchange_b = self.exchanges[j]

                    # Check if both exchanges have recent data
                    if not exchange_a['last_price'] or not exchange_b['last_price']:
                        continue

                    # Check latency difference
                    latency_diff = abs(exchange_a['latency'] - exchange_b['latency'])
                    if latency_diff > self.p.latency_threshold:
                        continue

                    # Calculate price difference
                    price_diff = exchange_b['last_price'] - exchange_a['last_price']
                    price_diff_pct = abs(price_diff) / exchange_a['last_price']

                    # Check if price difference exceeds minimum threshold
                    if price_diff_pct < self.p.min_profit_threshold:
                        continue

                    # Determine arbitrage direction
                    if price_diff > 0:
                        # Exchange B is more expensive, buy from A and sell to B
                        buy_exchange = exchange_a
                        sell_exchange = exchange_b
                        expected_profit = price_diff
                    else:
                        # Exchange A is more expensive, buy from B and sell to A
                        buy_exchange = exchange_b
                        sell_exchange = exchange_a
                        expected_profit = abs(price_diff)

                    # Check volume and spread conditions
                    if (len(buy_exchange['price_history']) < 10 or
                        len(sell_exchange['price_history']) < 10):
                        continue

                    # Calculate position size based on expected profit and risk
                    position_size = self.calculate_position_size(expected_profit, price_diff_pct)

                    if position_size > 0:
                        opportunity = {
                            'buy_exchange': buy_exchange,
                            'sell_exchange': sell_exchange,
                            'expected_profit': expected_profit,
                            'profit_pct': price_diff_pct,
                            'position_size': position_size,
                            'timestamp': datetime.now(),
                            'time_window': self.p.arbitrage_window
                        }
                        opportunities.append(opportunity)

            self.arbitrage_opportunities += len(opportunities)
            return opportunities

        except Exception as e:
            self.logger.error(f"Error finding arbitrage opportunities: {e}")
            return []

    def calculate_position_size(self, expected_profit: float, profit_pct: float) -> float:
        """Calculate position size based on expected profit and risk parameters"""
        try:
            if not self.p.adaptive_position_sizing:
                return min(self.p.max_position_size, self.broker.get_cash() * 0.01)  # 1% of capital

            # Base position size on expected profit
            base_size = self.p.max_position_size

            # Adjust for profit percentage
            profit_multiplier = min(profit_pct / self.p.min_profit_threshold, 3.0)

            # Adjust for portfolio risk
            portfolio_value = self.broker.get_cash()
            risk_amount = portfolio_value * self.p.risk_limit
            risk_size = risk_amount / (profit_pct * portfolio_value) if profit_pct > 0 else 0

            # Adjust for daily P&L
            if self.daily_pnl < -self.daily_loss_limit:
                return 0  # Stop trading if daily loss limit reached

            daily_pnl_adjustment = max(0.1, 1.0 + (self.daily_pnl / self.daily_loss_limit))

            # Calculate final position size
            position_size = base_size * profit_multiplier * min(risk_size, 1.0) / daily_pnl_adjustment
            position_size = max(0.1, min(position_size, self.p.max_position_size))

            return position_size

        except Exception as e:
            self.logger.error(f"Error calculating position size: {e}")
            return 0.1

    def execute_arbitrage(self, opportunity: Dict[str, Any]):
        """Execute arbitrage trade across exchanges"""
        try:
            buy_exchange = opportunity['buy_exchange']
            sell_exchange = opportunity['sell_exchange']
            position_size = opportunity['position_size']

            # In a real implementation, this would place orders on different exchanges
            # For simulation, we'll use market orders on the primary data feed

            # Buy order (simulated)
            buy_order = self.buy(size=position_size, exectype=bt.Order.Market,
                                price=buy_exchange['ask'])

            # Sell order (simulated)
            sell_order = self.sell(size=position_size, exectype=bt.Order.Market,
                                 price=sell_exchange['bid'])

            # Track active arbitrage
            arbitrage_record = {
                'id': len(self.active_arbitrages),
                'buy_exchange': buy_exchange['name'],
                'sell_exchange': sell_exchange['name'],
                'position_size': position_size,
                'entry_time': datetime.now(),
                'expected_profit': opportunity['expected_profit'],
                'buy_order': buy_order,
                'sell_order': sell_order,
                'status': 'pending'
            }

            self.active_arbitrages.append(arbitrage_record)

            self.logger.info(f"Executed latency arbitrage - "
                           f"Buy: {buy_exchange['name']} @ {buy_exchange['ask']:.5f}, "
                           f"Sell: {sell_exchange['name']} @ {sell_exchange['bid']:.5f}, "
                           f"Size: {position_size:.1f}, "
                           f"Expected Profit: ${opportunity['expected_profit']:.4f}")

        except Exception as e:
            self.logger.error(f"Error executing arbitrage: {e}")

    def manage_active_arbitrages(self):
        """Manage and close active arbitrage positions"""
        try:
            current_time = datetime.now()
            completed_arbitrages = []

            for arbitrage in self.active_arbitrages:
                time_held = (current_time - arbitrage['entry_time']).total_seconds()

                # Check if arbitrage should be closed
                if time_held >= self.p.max_holding_time:
                    # Close position due to time limit
                    self.close_arbitrage(arbitrage, "time_limit")
                    completed_arbitrages.append(arbitrage)

                elif arbitrage['status'] == 'filled':
                    # Check if both orders are filled
                    if (arbitrage['buy_order'].status == bt.Order.Completed and
                        arbitrage['sell_order'].status == bt.Order.Completed):
                        self.close_arbitrage(arbitrage, "completed")
                        completed_arbitrages.append(arbitrage)

            # Remove completed arbitrages
            for completed in completed_arbitrages:
                self.active_arbitrages.remove(completed)

        except Exception as e:
            self.logger.error(f"Error managing active arbitrages: {e}")

    def close_arbitrage(self, arbitrage: Dict[str, Any], reason: str):
        """Close an arbitrage position"""
        try:
            # In a real implementation, this would close positions on both exchanges
            # For simulation, we'll just mark as completed

            arbitrage['status'] = 'closed'
            arbitrage['close_time'] = datetime.now()
            arbitrage['close_reason'] = reason

            # Calculate actual P&L (simplified)
            actual_pnl = arbitrage['expected_profit'] * arbitrage['position_size'] * 0.95  # 5% slippage
            self.total_pnl += actual_pnl
            self.daily_pnl += actual_pnl

            # Update statistics
            self.successful_arbitrages += 1
            self.best_arbitrage = max(self.best_arbitrage, actual_pnl)
            self.worst_arbitrage = min(self.worst_arbitrage, actual_pnl)

            self.logger.info(f"Closed arbitrage - Reason: {reason}, "
                           f"P&L: ${actual_pnl:.4f}, "
                           f"Time held: {(arbitrage['close_time'] - arbitrage['entry_time']).total_seconds():.1f}s")

        except Exception as e:
            self.logger.error(f"Error closing arbitrage: {e}")

    def next(self):
        """Main latency arbitrage logic"""
        try:
            # Update exchange data
            self.update_exchange_data()

            # Find arbitrage opportunities
            opportunities = self.find_arbitrage_opportunities()

            # Execute arbitrage trades
            for opportunity in opportunities[:3]:  # Limit to 3 simultaneous arbitrages
                self.execute_arbitrage(opportunity)

            # Manage active arbitrages
            self.manage_active_arbitrages()

        except Exception as e:
            self.logger.error(f"Error in next(): {e}")

    def notify_order(self, order):
        """Handle order notifications"""
        try:
            if order.status == order.Completed:
                self.total_trades += 1

                # Update arbitrage status
                for arbitrage in self.active_arbitrages:
                    if arbitrage['buy_order'] == order or arbitrage['sell_order'] == order:
                        arbitrage['status'] = 'filled'
                        break

                self.log(f"Order executed: {'BUY' if order.isbuy() else 'SELL'} "
                        f"{order.executed.size} @ {order.executed.price:.5f}")

            elif order.status in [order.Canceled, order.Rejected]:
                self.log(f"Order {'canceled' if order.status == order.Canceled else 'rejected'}: "
                        f"{'BUY' if order.isbuy() else 'SELL'} @ {order.price:.5f}")

                # Remove failed arbitrage
                for arbitrage in self.active_arbitrages[:]:
                    if arbitrage['buy_order'] == order or arbitrage['sell_order'] == order:
                        self.active_arbitrages.remove(arbitrage)
                        break

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
        success_rate = (self.successful_arbitrages / self.arbitrage_opportunities) * 100 if self.arbitrage_opportunities > 0 else 0

        self.logger.info("=== LATENCY ARBITRAGE HFT STRATEGY RESULTS ===")
        self.logger.info(f"Arbitrage Opportunities: {self.arbitrage_opportunities}")
        self.logger.info(f"Successful Arbitrages: {self.successful_arbitrages}")
        self.logger.info(f"Success Rate: {success_rate:.1f}%")
        self.logger.info(f"Total Trades: {self.total_trades}")
        self.logger.info(f"Total P&L: ${self.total_pnl:.2f}")
        self.logger.info(f"Best Arbitrage: ${self.best_arbitrage:.4f}")
        self.logger.info(f"Worst Arbitrage: ${self.worst_arbitrage:.4f}")
        self.logger.info(f"Daily P&L: ${self.daily_pnl:.2f}")
        self.logger.info(f"Final Portfolio Value: ${self.broker.get_value():.2f}")

if __name__ == '__main__':
    print("Latency Arbitrage HFT Strategy loaded successfully")