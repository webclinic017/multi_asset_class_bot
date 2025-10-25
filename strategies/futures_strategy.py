"""
Futures Strategy Module for Trading Bot

This module defines a futures-specific trading strategy, e.g., a trend-following strategy.
It integrates with the data feed and provides signals for execution.
"""

import backtrader as bt
import logging
import yaml
import os

class FuturesStrategy(bt.Strategy):
    """
    A simple futures trading strategy based on a combination of SMA and RSI.
    """
    params = (
        ('sma_period', 20),              # Shorter period for more responsive signals
        ('rsi_period', 14),
        ('rsi_overbought', 75),          # More aggressive overbought level
        ('rsi_oversold', 25),            # More aggressive oversold level
        ('stop_loss_percent', 0.015),    # Tighter 1.5% stop loss
        ('take_profit_percent', 0.03),   # 3% take profit for better risk-reward
        
        # Position Sizing - Enhanced for better risk management
        ('risk_per_trade', 0.015),       # 1.5% risk per trade
        ('position_size_percent', 0.08), # 8% position size per trade
        ('max_position_size', 0.15),     # Maximum 15% position size
        ('dynamic_sizing', True),        # Enable dynamic position sizing
        
        # Market Regime Detection
        ('use_regime_filter', True),     # Enable market regime filter
        ('volatility_lookback', 20),     # Lookback period for volatility calculation
        
        ('printlog', False)
    )

    def log(self, txt, dt=None):
        """Logging function for this strategy"""
        if self.p.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            logging.info(f'{dt.isoformat()} {txt}')

    def __init__(self):
        self.dataclose = self.datas[0].close
        self.order = None
        self.buyprice = None
        self.buycomm = None

        # Performance tracking
        self.trade_count = 0
        self.winning_trades = 0
        self.total_pnl = 0.0

        # Indicators
        self.sma = bt.indicators.SMA(self.datas[0], period=self.p.sma_period)
        self.rsi = bt.indicators.RSI(self.datas[0], period=self.p.rsi_period)
        
        # Volatility indicator for market regime detection
        if self.p.use_regime_filter:
            self.atr = bt.indicators.ATR(self.datas[0], period=self.p.volatility_lookback)
            self.volatility = 0.0

        self.logger = logging.getLogger(__name__)
        self.logger.info("FuturesStrategy initialized with dynamic position sizing")

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    'BUY EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                    (order.executed.price,
                     order.executed.value,
                     order.executed.comm))

                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            elif order.issell():
                self.log('SELL EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                         (order.executed.price,
                          order.executed.value,
                          order.executed.comm))

            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        self.trade_count += 1
        if trade.pnlcomm > 0:
            self.winning_trades += 1
        self.total_pnl += trade.pnlcomm

        self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' %
                 (trade.pnl, trade.pnlcomm))

    def calculate_position_size(self, signal_strength: float = 1.0) -> float:
        """
        Calculate position size based on account value and risk parameters
        Uses dynamic sizing based on signal strength and performance
        """
        if not self.p.dynamic_sizing:
            return self.p.position_size_percent
        
        try:
            # Base position size
            base_size = self.p.position_size_percent
            
            # Signal strength adjustment
            signal_multiplier = signal_strength * 1.5  # Scale with signal strength
            
            # Performance-based adjustment
            performance_factor = 1.0
            if self.trade_count > 0:
                win_rate = self.winning_trades / self.trade_count
                if win_rate > 0.6:
                    performance_factor = 1.1  # Increase size for good performance
                elif win_rate < 0.4:
                    performance_factor = 0.9  # Decrease size for poor performance
            
            # Calculate final position size
            position_size = base_size * signal_multiplier * performance_factor
            
            # Apply maximum position size limit
            position_size = min(position_size, self.p.max_position_size)
            
            # Ensure minimum position size
            position_size = max(position_size, 0.01)  # Minimum 1%
            
            self.log(f'Position Size: Base={base_size:.4f}, Signal={signal_multiplier:.2f}, '
                   f'Performance={performance_factor:.2f}, Final={position_size:.4f}')
            
            return position_size
            
        except Exception as e:
            self.logger.error(f"Error calculating position size: {e}")
            return self.p.position_size_percent  # Fallback to base size

    def next(self):
        self.log('Close, %.2f' % self.dataclose[0])
        
        # Update volatility measure for market regime detection
        if self.p.use_regime_filter and len(self) > self.p.volatility_lookback:
            self.volatility = self.atr[0] / self.dataclose[0]

        if self.order:
            return

        # Market regime filter - only trade in favorable conditions
        if self.p.use_regime_filter:
            # Avoid trading in high volatility regimes
            if self.volatility > 0.02:  # Adjust threshold as needed
                return

        if not self.position:  # Not in the market
            # Calculate signal strength
            signal_strength = 1.0
            if self.dataclose[0] > self.sma[0]:
                signal_strength *= 1.2
            if self.rsi[0] < self.p.rsi_oversold:
                signal_strength *= 1.3
            
            # Buy signal: Close price above SMA and RSI oversold
            if self.dataclose[0] > self.sma[0] and self.rsi[0] < self.p.rsi_oversold:
                position_size = self.calculate_position_size(signal_strength)
                self.log('BUY CREATE (Trend-following), %.2f, Position Size: %.4f' % (self.dataclose[0], position_size))
                self.order = self.buy(size=position_size)
            
            # Calculate signal strength for sell
            signal_strength = 1.0
            if self.dataclose[0] < self.sma[0]:
                signal_strength *= 1.2
            if self.rsi[0] > self.p.rsi_overbought:
                signal_strength *= 1.3
            
            # Sell signal: Close price below SMA and RSI overbought
            elif self.dataclose[0] < self.sma[0] and self.rsi[0] > self.p.rsi_overbought:
                position_size = self.calculate_position_size(signal_strength)
                self.log('SELL CREATE (Trend-following), %.2f, Position Size: %.4f' % (self.dataclose[0], position_size))
                self.order = self.sell(size=position_size)
        else:  # Already in the market
            # Implement stop loss and take profit
            if self.position.islong:
                # Check for stop loss
                if self.dataclose[0] <= self.buyprice * (1 - self.p.stop_loss_percent):
                    self.log('STOP LOSS HIT (LONG), %.2f' % self.dataclose[0])
                    self.close()
                # Check for take profit
                elif self.dataclose[0] >= self.buyprice * (1 + self.p.take_profit_percent):
                    self.log('TAKE PROFIT HIT (LONG), %.2f' % self.dataclose[0])
                    self.close()
            elif self.position.isshort:
                # Check for stop loss
                if self.dataclose[0] >= self.buyprice * (1 + self.p.stop_loss_percent): # For short, stop loss is above entry
                    self.log('STOP LOSS HIT (SHORT), %.2f' % self.dataclose[0])
                    self.close()
                # Check for take profit
                elif self.dataclose[0] <= self.buyprice * (1 - self.p.take_profit_percent): # For short, take profit is below entry
                    self.log('TAKE PROFIT HIT (SHORT), %.2f' % self.dataclose[0])
                    self.close()

if __name__ == '__main__':
    # This is a placeholder for how the strategy might be used with a backtesting engine.
    # Actual backtesting setup will be in backtest_engine.py
    logging.basicConfig(level=logging.INFO)
    
    print("Futures Strategy module loaded. Run backtest_engine.py or main.py to use.")