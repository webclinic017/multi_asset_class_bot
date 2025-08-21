"""
Crypto Strategy Module for Trading Bot

This module defines a crypto-specific trading strategy, e.g., a breakout strategy.
It integrates with the data feed and provides signals for execution.
"""

import backtrader as bt
import logging
import yaml
import os

class CryptoStrategy(bt.Strategy):
    """
    A simple crypto trading strategy based on a breakout of Bollinger Bands.
    """
    params = (
        ('bb_period', 20),
        ('bb_dev', 2),
        ('stop_loss_percent', 0.01), # 1% stop loss
        ('take_profit_percent', 0.03), # 3% take profit
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

        # Bollinger Bands
        self.bb = bt.indicators.BollingerBands(
            self.datas[0],
            period=self.p.bb_period,
            devfactor=self.p.bb_dev
        )
        
        self.upper_band = self.bb.lines.top
        self.lower_band = self.bb.lines.bot

        self.logger = logging.getLogger(__name__)
        self.logger.info("CryptoStrategy initialized")

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

        self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' %
                 (trade.pnl, trade.pnlcomm))

    def next(self):
        self.log('Close, %.2f' % self.dataclose[0])

        if self.order:
            return

        if not self.position:  # Not in the market
            # Buy signal: Close price breaks above upper Bollinger Band
            if self.dataclose[0] > self.upper_band[0]:
                self.log('BUY CREATE (Breakout), %.2f' % self.dataclose[0])
                self.order = self.buy()
            # Sell signal: Close price breaks below lower Bollinger Band
            elif self.dataclose[0] < self.lower_band[0]:
                self.log('SELL CREATE (Breakdown), %.2f' % self.dataclose[0])
                self.order = self.sell()
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
    
    print("Crypto Strategy module loaded. Run backtest_engine.py or main.py to use.")