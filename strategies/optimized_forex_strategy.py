"""
Optimized Forex Strategy Module for Trading Bot

This module defines a realistic and optimized forex trading strategy that:
- Uses proven technical indicators with realistic parameters
- Has achievable trading conditions that will execute trades
- Implements proper risk management for positive Sharpe ratio
- Focuses on consistent profitability over complexity
"""

import backtrader as bt
import logging
import numpy as np

class OptimizedForexStrategy(bt.Strategy):
    """
    Optimized forex trading strategy designed for positive Sharpe ratio.
    
    Strategy Logic:
    1. Simple but effective EMA crossover system
    2. RSI for momentum confirmation (relaxed levels)
    3. ATR-based position sizing and stops
    4. Realistic trading conditions that will execute
    5. Focus on risk-adjusted returns
    """
    params = (
        # Moving Average Parameters - Proven effective periods
        ('fast_ema', 8),               # Fast EMA period
        ('slow_ema', 21),              # Slow EMA period
        
        # Technical Indicator Parameters - Relaxed for more trades
        ('rsi_period', 14),            # RSI period
        ('rsi_oversold', 25),          # RSI oversold level (relaxed)
        ('rsi_overbought', 75),        # RSI overbought level (relaxed)
        ('atr_period', 14),            # ATR period
        
        # Risk Management - Conservative but achievable
        ('stop_loss_atr', 2.0),        # Stop loss as multiple of ATR
        ('take_profit_atr', 3.0),      # Take profit as multiple of ATR
        ('position_size_percent', 0.02), # 2% of capital per trade
        
        # Trading Filters - Realistic conditions
        ('min_atr', 0.0001),           # Minimum ATR to trade
        ('max_atr', 0.01),             # Maximum ATR to trade
        
        # Logging
        ('printlog', False)
    )

    def log(self, txt, dt=None):
        """Logging function for this strategy"""
        if self.p.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            logging.info(f'{dt.isoformat()} {txt}')

    def __init__(self):
        self.dataclose = self.datas[0].close
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low
        
        self.order = None
        self.buyprice = None
        self.buycomm = None
        self.bar_executed = 0
        
        # Technical Indicators - Simple and effective
        self.ema_fast = bt.indicators.EMA(self.datas[0], period=self.p.fast_ema)
        self.ema_slow = bt.indicators.EMA(self.datas[0], period=self.p.slow_ema)
        self.crossover = bt.indicators.CrossOver(self.ema_fast, self.ema_slow)
        
        # RSI for momentum confirmation
        self.rsi = bt.indicators.RSI(self.datas[0], period=self.p.rsi_period)
        
        # ATR for volatility and position sizing
        self.atr = bt.indicators.ATR(self.datas[0], period=self.p.atr_period)
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("OptimizedForexStrategy initialized with realistic parameters")

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED: Price {order.executed.price:.5f}, '
                        f'Cost {order.executed.value:.2f}, Comm {order.executed.comm:.2f}')
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            elif order.issell():
                self.log(f'SELL EXECUTED: Price {order.executed.price:.5f}, '
                        f'Cost {order.executed.value:.2f}, Comm {order.executed.comm:.2f}')
            
            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        self.log(f'TRADE CLOSED: PnL {trade.pnl:.2f}, Net PnL {trade.pnlcomm:.2f}')

    def calculate_position_size(self):
        """Calculate position size based on account value and risk percentage"""
        account_value = self.broker.getvalue()
        current_price = self.dataclose[0]
        
        # Calculate position size as percentage of account
        position_value = account_value * self.p.position_size_percent
        position_size = int(position_value / current_price) if current_price > 0 else 1
        
        return max(position_size, 1)  # Minimum 1 unit

    def next(self):
        current_price = self.dataclose[0]
        
        # Skip if not enough data for indicators
        if len(self.data) < max(self.p.fast_ema, self.p.slow_ema, self.p.rsi_period, self.p.atr_period):
            return
            
        # Check for None values
        if (current_price is None or self.rsi[0] is None or 
            self.atr[0] is None or self.ema_fast[0] is None or self.ema_slow[0] is None):
            return

        if self.order:
            return

        # Check ATR conditions - ensure we have enough volatility but not too much
        current_atr = self.atr[0]
        if current_atr < self.p.min_atr or current_atr > self.p.max_atr:
            return

        if not self.position:  # Not in the market
            
            # Long signal: EMA crossover + RSI not overbought
            long_signal = (
                self.crossover > 0 and  # Fast EMA crosses above slow EMA
                self.rsi[0] < self.p.rsi_overbought and  # Not overbought
                self.rsi[0] > 30  # Not too oversold either
            )
            
            # Short signal: EMA crossover + RSI not oversold
            short_signal = (
                self.crossover < 0 and  # Fast EMA crosses below slow EMA
                self.rsi[0] > self.p.rsi_oversold and  # Not oversold
                self.rsi[0] < 70  # Not too overbought either
            )
            
            if long_signal:
                position_size = self.calculate_position_size()
                self.log(f'BUY SIGNAL: Price {current_price:.5f}, RSI {self.rsi[0]:.1f}, ATR {current_atr:.5f}')
                self.order = self.buy(size=position_size)
                
            elif short_signal:
                position_size = self.calculate_position_size()
                self.log(f'SELL SIGNAL: Price {current_price:.5f}, RSI {self.rsi[0]:.1f}, ATR {current_atr:.5f}')
                self.order = self.sell(size=position_size)
                
        else:  # Already in position - manage exits
            self._manage_position()

    def _manage_position(self):
        """Manage existing positions with ATR-based stops and targets"""
        current_price = self.dataclose[0]
        current_atr = self.atr[0]
        
        if current_price is None or current_atr is None or self.buyprice is None:
            return
        
        if self.position.size > 0:  # Long position
            # ATR-based stop loss and take profit
            stop_loss_price = self.buyprice - (current_atr * self.p.stop_loss_atr)
            take_profit_price = self.buyprice + (current_atr * self.p.take_profit_atr)
            
            # Exit conditions
            if current_price <= stop_loss_price:
                self.log(f'LONG STOP LOSS: Price {current_price:.5f}, Stop {stop_loss_price:.5f}')
                self.close()
            elif current_price >= take_profit_price:
                self.log(f'LONG TAKE PROFIT: Price {current_price:.5f}, Target {take_profit_price:.5f}')
                self.close()
            # Exit on opposite signal
            elif self.crossover < 0 and self.rsi[0] > 70:
                self.log(f'LONG EXIT ON SIGNAL: Price {current_price:.5f}')
                self.close()
                
        elif self.position.size < 0:  # Short position
            # ATR-based stop loss and take profit
            stop_loss_price = self.buyprice + (current_atr * self.p.stop_loss_atr)
            take_profit_price = self.buyprice - (current_atr * self.p.take_profit_atr)
            
            # Exit conditions
            if current_price >= stop_loss_price:
                self.log(f'SHORT STOP LOSS: Price {current_price:.5f}, Stop {stop_loss_price:.5f}')
                self.close()
            elif current_price <= take_profit_price:
                self.log(f'SHORT TAKE PROFIT: Price {current_price:.5f}, Target {take_profit_price:.5f}')
                self.close()
            # Exit on opposite signal
            elif self.crossover > 0 and self.rsi[0] < 30:
                self.log(f'SHORT EXIT ON SIGNAL: Price {current_price:.5f}')
                self.close()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    print("OptimizedForexStrategy module loaded. This strategy is designed for realistic trading conditions and positive Sharpe ratio.")