"""
Simple Crypto Strategy - Backtrader Compatible
Simplified version with basic indicators that work reliably with limited data
"""

import backtrader as bt
import logging
from datetime import datetime

class SimpleCryptoStrategy(bt.Strategy):
    """
    Simplified crypto trading strategy with basic indicators
    Designed to work reliably with backtrader and limited data
    """
    
    params = (
        # Basic Parameters
        ('fast_length', 10),
        ('slow_length', 21),
        ('rsi_period', 14),
        ('rsi_oversold', 30),
        ('rsi_overbought', 70),
        
        # Risk Management
        ('stop_loss_percent', 0.04),
        ('take_profit_percent', 0.08),
        ('position_size_percent', 0.15),
        
        # Logging
        ('printlog', False)
    )

    def __init__(self):
        """Initialize simple crypto strategy"""
        self.logger = logging.getLogger(__name__)
        
        # Basic price data
        self.dataclose = self.datas[0].close
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low
        self.datavolume = self.datas[0].volume
        
        # Order management
        self.order = None
        self.buyprice = None
        self.buycomm = None
        
        # Performance tracking
        self.trade_count = 0
        self.winning_trades = 0
        self.losing_trades = 0
        
        # Initialize basic indicators only
        self.ema_fast = bt.indicators.EMA(period=self.p.fast_length)
        self.ema_slow = bt.indicators.EMA(period=self.p.slow_length)
        self.rsi = bt.indicators.RSI(period=self.p.rsi_period)
        
        # Simple volume indicator
        self.volume_sma = bt.indicators.SMA(self.datavolume, period=20)
        
        self.logger.info("Simple Crypto Strategy initialized with basic indicators")

    def next(self):
        """Main strategy logic"""
        if self.order:
            return
        
        # Safety check for minimum data
        if len(self.data) < max(self.p.slow_length, self.p.rsi_period) + 5:
            return
            
        # Simple signal generation
        current_price = self.dataclose[0]
        
        if not self.position:  # No position
            # Buy signal: EMA crossover + RSI oversold
            if (self.ema_fast[0] > self.ema_slow[0] and 
                self.ema_fast[-1] <= self.ema_slow[-1] and
                self.rsi[0] < 50):
                
                self.log(f'BUY CREATE - Price: {current_price:.4f}, RSI: {self.rsi[0]:.2f}')
                self.order = self.buy(size=self.p.position_size_percent)
                
            # Sell signal: EMA crossover down + RSI overbought
            elif (self.ema_fast[0] < self.ema_slow[0] and 
                  self.ema_fast[-1] >= self.ema_slow[-1] and
                  self.rsi[0] > 50):
                
                self.log(f'SELL CREATE - Price: {current_price:.4f}, RSI: {self.rsi[0]:.2f}')
                self.order = self.sell(size=self.p.position_size_percent)
                
        else:  # In position
            # Simple exit logic
            if self.position.size > 0:  # Long position
                stop_price = self.buyprice * (1 - self.p.stop_loss_percent)
                target_price = self.buyprice * (1 + self.p.take_profit_percent)
                
                if current_price <= stop_price:
                    self.log(f'STOP LOSS (LONG) - Price: {current_price:.4f}')
                    self.close()
                elif current_price >= target_price:
                    self.log(f'TAKE PROFIT (LONG) - Price: {current_price:.4f}')
                    self.close()
                    
            elif self.position.size < 0:  # Short position
                stop_price = self.buyprice * (1 + self.p.stop_loss_percent)
                target_price = self.buyprice * (1 - self.p.take_profit_percent)
                
                if current_price >= stop_price:
                    self.log(f'STOP LOSS (SHORT) - Price: {current_price:.4f}')
                    self.close()
                elif current_price <= target_price:
                    self.log(f'TAKE PROFIT (SHORT) - Price: {current_price:.4f}')
                    self.close()

    def log(self, txt, dt=None):
        """Logging function"""
        if self.p.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            self.logger.info(f'{dt.isoformat()} {txt}')

    def notify_order(self, order):
        """Order notification"""
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED - Price: {order.executed.price:.4f}')
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:
                self.log(f'SELL EXECUTED - Price: {order.executed.price:.4f}')

            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        self.order = None

    def notify_trade(self, trade):
        """Trade notification"""
        if not trade.isclosed:
            return

        self.trade_count += 1
        if trade.pnl > 0:
            self.winning_trades += 1
        else:
            self.losing_trades += 1

        self.log(f'TRADE CLOSED - PnL: {trade.pnl:.4f}')

    def stop(self):
        """Strategy completion"""
        final_value = self.broker.get_value()
        initial_capital = 10000
        total_return = ((final_value - initial_capital) / initial_capital) * 100
        win_rate = (self.winning_trades / max(self.trade_count, 1)) * 100
        
        self.log('=== SIMPLE CRYPTO STRATEGY RESULTS ===')
        self.log(f'Final Value: ${final_value:.2f}')
        self.log(f'Total Return: {total_return:.2f}%')
        self.log(f'Total Trades: {self.trade_count}')
        self.log(f'Win Rate: {win_rate:.1f}%')

if __name__ == "__main__":
    print("Simple Crypto Strategy loaded successfully")
    print("Features:")
    print("- Basic EMA crossover signals")
    print("- RSI momentum filter")
    print("- Simple stop loss and take profit")
    print("- Minimal data requirements")
    print("- Backtrader compatible")