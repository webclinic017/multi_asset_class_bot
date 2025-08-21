"""
Simplified Profitable Forex Strategy
Focus on actual profitability with simpler, more reliable signals
"""

import backtrader as bt
import logging
import numpy as np

class ProfitableForexStrategy(bt.Strategy):
    """
    Simplified forex strategy focused on profitability:
    1. Moving average crossover for trend direction
    2. RSI for momentum confirmation
    3. Proper risk management with better risk/reward ratios
    4. Less restrictive entry conditions
    """
    params = (
        # Moving Average Parameters
        ('fast_length', 10),
        ('slow_length', 30),
        
        # RSI Parameters
        ('rsi_period', 14),
        ('rsi_oversold', 30),
        ('rsi_overbought', 70),
        
        # MACD Parameters (optional)
        ('macd_fast', 12),
        ('macd_slow', 26),
        ('macd_signal', 9),
        
        # Risk Management - Better ratios
        ('stop_loss_percent', 0.01),    # 1% stop loss
        ('take_profit_percent', 0.02),  # 2% take profit (2:1 reward/risk)
        
        # Strategy Filters - Simplified
        ('use_rsi_filter', True),
        ('use_macd_filter', False),     # Disable complex filters initially
        ('use_trend_filter', True),     # Simple trend following
        
        # Trade Management
        ('max_trades_per_day', 3),      # Limit overtrading
        ('min_bars_between_trades', 5), # Prevent rapid fire trades
        
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
        self.last_trade_bar = 0
        self.trades_today = 0
        self.current_day = None

        # Simple Technical Indicators
        self.sma_fast = bt.indicators.SMA(self.datas[0], period=self.p.fast_length)
        self.sma_slow = bt.indicators.SMA(self.datas[0], period=self.p.slow_length)
        self.crossover = bt.indicators.CrossOver(self.sma_fast, self.sma_slow)
        
        # RSI for momentum
        self.rsi = bt.indicators.RSI(self.datas[0], period=self.p.rsi_period)
        
        # MACD (optional)
        if self.p.use_macd_filter:
            self.macd = bt.indicators.MACD(
                self.datas[0],
                period_me1=self.p.macd_fast,
                period_me2=self.p.macd_slow,
                period_signal=self.p.macd_signal
            )

        self.logger = logging.getLogger(__name__)
        self.logger.info("ProfitableForexStrategy initialized")

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED, Price: {order.executed.price:.5f}, Cost: {order.executed.value:.2f}')
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            elif order.issell():
                self.log(f'SELL EXECUTED, Price: {order.executed.price:.5f}, Cost: {order.executed.value:.2f}')
                self.buyprice = order.executed.price  # Store entry price for both long and short
                self.buycomm = order.executed.comm

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        
        self.log(f'TRADE CLOSED - P&L: {trade.pnlcomm:.2f}, Return: {(trade.pnlcomm/10000)*100:.3f}%')

    def next(self):
        # Track daily trades
        current_date = self.datas[0].datetime.date(0)
        if self.current_day != current_date:
            self.current_day = current_date
            self.trades_today = 0

        if self.order:
            return

        # Prevent overtrading
        if self.trades_today >= self.p.max_trades_per_day:
            return
            
        if len(self) - self.last_trade_bar < self.p.min_bars_between_trades:
            return

        current_price = self.dataclose[0]

        if not self.position:  # Not in market
            # Simple trend following with RSI confirmation
            
            # Long signal: MA crossover up + RSI not overbought
            if (self.crossover > 0 and 
                self.p.use_rsi_filter and self.rsi[0] < self.p.rsi_overbought and self.rsi[0] > 40):
                
                # Additional MACD confirmation if enabled
                macd_ok = True
                if self.p.use_macd_filter:
                    macd_ok = self.macd.macd[0] > self.macd.signal[0]
                
                if macd_ok:
                    self.log(f'BUY SIGNAL - Price: {current_price:.5f}, RSI: {self.rsi[0]:.1f}')
                    self.order = self.buy()
                    self.last_trade_bar = len(self)
                    self.trades_today += 1
            
            # Short signal: MA crossover down + RSI not oversold
            elif (self.crossover < 0 and 
                  self.p.use_rsi_filter and self.rsi[0] > self.p.rsi_oversold and self.rsi[0] < 60):
                
                # Additional MACD confirmation if enabled
                macd_ok = True
                if self.p.use_macd_filter:
                    macd_ok = self.macd.macd[0] < self.macd.signal[0]
                
                if macd_ok:
                    self.log(f'SELL SIGNAL - Price: {current_price:.5f}, RSI: {self.rsi[0]:.1f}')
                    self.order = self.sell()
                    self.last_trade_bar = len(self)
                    self.trades_today += 1
                    
            # Alternative: Simple trend following without crossover
            elif self.p.use_trend_filter:
                # Long: Fast MA above Slow MA + RSI rising
                if (self.sma_fast[0] > self.sma_slow[0] and 
                    self.rsi[0] > self.rsi[-1] and 
                    self.rsi[0] > 45 and self.rsi[0] < 75):
                    
                    self.log(f'TREND BUY - Price: {current_price:.5f}, RSI: {self.rsi[0]:.1f}')
                    self.order = self.buy()
                    self.last_trade_bar = len(self)
                    self.trades_today += 1
                
                # Short: Fast MA below Slow MA + RSI falling
                elif (self.sma_fast[0] < self.sma_slow[0] and 
                      self.rsi[0] < self.rsi[-1] and 
                      self.rsi[0] < 55 and self.rsi[0] > 25):
                    
                    self.log(f'TREND SELL - Price: {current_price:.5f}, RSI: {self.rsi[0]:.1f}')
                    self.order = self.sell()
                    self.last_trade_bar = len(self)
                    self.trades_today += 1

        else:  # In position - manage exits
            self._manage_position()

    def _manage_position(self):
        """Simple but effective position management"""
        current_price = self.dataclose[0]
        
        # Safety check for entry price
        if self.buyprice is None:
            self.log('Warning: No entry price recorded, closing position')
            self.close()
            return
        
        if self.position.size > 0:  # Long position
            stop_loss = self.buyprice * (1 - self.p.stop_loss_percent)
            take_profit = self.buyprice * (1 + self.p.take_profit_percent)
            
            if current_price <= stop_loss:
                self.log(f'STOP LOSS (LONG) - Entry: {self.buyprice:.5f}, Exit: {current_price:.5f}')
                self.close()
            elif current_price >= take_profit:
                self.log(f'TAKE PROFIT (LONG) - Entry: {self.buyprice:.5f}, Exit: {current_price:.5f}')
                self.close()
            # Trailing stop for big winners
            elif current_price > self.buyprice * 1.015:  # 1.5% profit
                trailing_stop = current_price * (1 - self.p.stop_loss_percent * 0.5)
                if trailing_stop > stop_loss:
                    self.log(f'TRAILING STOP UPDATE: {trailing_stop:.5f}')
                    
        elif self.position.size < 0:  # Short position
            stop_loss = self.buyprice * (1 + self.p.stop_loss_percent)
            take_profit = self.buyprice * (1 - self.p.take_profit_percent)
            
            if current_price >= stop_loss:
                self.log(f'STOP LOSS (SHORT) - Entry: {self.buyprice:.5f}, Exit: {current_price:.5f}')
                self.close()
            elif current_price <= take_profit:
                self.log(f'TAKE PROFIT (SHORT) - Entry: {self.buyprice:.5f}, Exit: {current_price:.5f}')
                self.close()
            # Trailing stop for big winners
            elif current_price < self.buyprice * 0.985:  # 1.5% profit
                trailing_stop = current_price * (1 + self.p.stop_loss_percent * 0.5)
                if trailing_stop < stop_loss:
                    self.log(f'TRAILING STOP UPDATE: {trailing_stop:.5f}')