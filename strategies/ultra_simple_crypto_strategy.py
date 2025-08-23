"""
Ultra Simple Crypto Strategy - Zero Indicators
Absolute minimal strategy with NO indicators to avoid backtrader array issues
"""

import backtrader as bt
import logging
from datetime import datetime

class UltraSimpleCryptoStrategy(bt.Strategy):
    """
    Ultra simplified crypto trading strategy with NO indicators
    Uses only raw price data to avoid any backtrader array index issues
    """
    
    params = (
        # Basic Parameters
        ('lookback_period', 5),  # How many bars to look back for price comparison
        ('price_change_threshold', 0.02),  # 2% price change threshold
        
        # Risk Management
        ('stop_loss_percent', 0.04),
        ('take_profit_percent', 0.08),
        ('position_size_percent', 0.15),
        
        # Logging
        ('printlog', False)
    )

    def __init__(self):
        """Initialize ultra simple crypto strategy with NO indicators"""
        self.logger = logging.getLogger(__name__)
        
        # Basic price data only - NO INDICATORS
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
        
        # NO INDICATORS AT ALL - this should eliminate ExponentialSmoothing issues
        self.logger.info("Ultra Simple Crypto Strategy initialized with ZERO indicators")

    def next(self):
        """Main strategy logic using only raw price data"""
        if self.order:
            return
        
        # Safety check for minimum data
        if len(self.data) < self.p.lookback_period + 1:
            return
            
        # Simple signal generation using only price data
        current_price = self.dataclose[0]
        previous_price = self.dataclose[-self.p.lookback_period]
        
        # Calculate price change percentage
        if previous_price > 0:
            price_change = (current_price - previous_price) / previous_price
        else:
            return  # Skip if invalid price data
        
        if not self.position:  # No position
            # Buy signal: Price increased significantly
            if price_change > self.p.price_change_threshold:
                self.log(f'BUY CREATE - Price: {current_price:.4f}, Change: {price_change*100:.2f}%')
                # Calculate position size based on available cash
                cash = self.broker.get_cash()
                size = int(cash * self.p.position_size_percent / current_price)
                if size > 0:
                    self.order = self.buy(size=size)
                
            # Sell signal: Price decreased significantly
            elif price_change < -self.p.price_change_threshold:
                self.log(f'SELL CREATE - Price: {current_price:.4f}, Change: {price_change*100:.2f}%')
                # Calculate position size based on available cash
                cash = self.broker.get_cash()
                size = int(cash * self.p.position_size_percent / current_price)
                if size > 0:
                    self.order = self.sell(size=size)
                
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
        
        self.log('=== ULTRA SIMPLE CRYPTO STRATEGY RESULTS ===')
        self.log(f'Final Value: ${final_value:.2f}')
        self.log(f'Total Return: {total_return:.2f}%')
        self.log(f'Total Trades: {self.trade_count}')
        self.log(f'Win Rate: {win_rate:.1f}%')

if __name__ == "__main__":
    print("Ultra Simple Crypto Strategy loaded successfully")
    print("Features:")
    print("- ZERO indicators (no EMA, RSI, SMA, etc.)")
    print("- Pure price action signals")
    print("- Simple momentum-based entries")
    print("- Basic stop loss and take profit")
    print("- Minimal data requirements (6 bars)")
    print("- Should eliminate ALL backtrader indicator issues")