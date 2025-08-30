"""
Improved Forex Strategy Module for Trading Bot

This module defines a simplified but robust forex trading strategy focusing on:
- Moving average crossover signals with proper trend filtering
- RSI for momentum confirmation
- MACD for trend strength
- Proper risk management with dynamic position sizing
"""

import backtrader as bt
import logging
import numpy as np

class ImprovedForexStrategy(bt.Strategy):
    """
    Improved forex trading strategy with focus on reliability and positive Sharpe ratio.
    
    Strategy Logic:
    1. Use EMA crossover for trend direction (more responsive than SMA)
    2. RSI for momentum confirmation and overbought/oversold levels
    3. MACD for trend strength confirmation
    4. Dynamic position sizing based on volatility
    5. Proper risk management with trailing stops
    """
    params = (
        # Moving Average Parameters - Optimized for better performance
        ('fast_length', 8),            # More responsive EMA period
        ('slow_length', 21),           # More responsive EMA period
        
        # Technical Indicator Parameters
        ('rsi_period', 14),            # RSI period
        ('rsi_oversold', 25),          # More relaxed RSI oversold level
        ('rsi_overbought', 75),        # More relaxed RSI overbought level
        ('macd_fast', 12),             # MACD fast EMA
        ('macd_slow', 26),             # MACD slow EMA
        ('macd_signal', 9),            # MACD signal line
        
        # Risk Management - More aggressive for profit maximization
        ('stop_loss_percent', 0.005),  # Tighter stop loss
        ('take_profit_percent', 0.035), # Larger take profit (7:1 R/R)
        ('trailing_stop_percent', 0.002), # Tighter trailing stop
        
        # Position Sizing - More aggressive
        ('position_size_percent', 0.05), # 5% of capital per trade
        ('max_position_size', 0.10),     # Maximum 10% of capital
        
        # Strategy Filters - More relaxed to allow more trades
        ('min_volatility', 0.00005),   # Lower minimum volatility
        ('max_volatility', 0.02),      # Higher maximum volatility
        ('trend_strength_threshold', 0.3), # Lower trend strength threshold
        
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
        self.datavolume = self.datas[0].volume
        
        self.order = None
        self.buyprice = None
        self.buycomm = None
        self.entry_bar = None
        self.highest_profit = 0.0
        self.lowest_profit = 0.0

        # Use EMA instead of SMA for better responsiveness
        self.ema_fast = bt.indicators.EMA(self.datas[0], period=self.p.fast_length)
        self.ema_slow = bt.indicators.EMA(self.datas[0], period=self.p.slow_length)
        self.crossover = bt.indicators.CrossOver(self.ema_fast, self.ema_slow)
        
        # RSI for momentum
        self.rsi = bt.indicators.RSI(self.datas[0], period=self.p.rsi_period)
        
        # MACD for trend confirmation
        self.macd = bt.indicators.MACD(
            self.datas[0],
            period_me1=self.p.macd_fast,
            period_me2=self.p.macd_slow,
            period_signal=self.p.macd_signal
        )
        
        # ATR for volatility measurement
        self.atr = bt.indicators.ATR(self.datas[0], period=14)
        
        # Bollinger Bands for volatility and mean reversion
        self.bollinger = bt.indicators.BollingerBands(self.datas[0], period=20)
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("ImprovedForexStrategy initialized with optimized parameters")

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    'BUY EXECUTED, Price: %.5f, Cost: %.2f, Comm %.2f' %
                    (order.executed.price,
                     order.executed.value,
                     order.executed.comm))

                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
                self.highest_profit = 0.0
                self.lowest_profit = 0.0
            elif order.issell():
                self.log('SELL EXECUTED, Price: %.5f, Cost: %.2f, Comm %.2f' %
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

    def calculate_position_size(self):
        """Calculate position size based on volatility and risk management"""
        current_price = self.dataclose[0]
        account_value = self.broker.getvalue()
        
        # Base position size as percentage of account
        base_size = account_value * self.p.position_size_percent
        
        # Adjust for volatility (lower volatility = larger position)
        volatility = self.atr[0] / current_price if current_price > 0 else 0.01
        volatility = max(self.p.min_volatility, min(volatility, self.p.max_volatility))
        
        # Volatility adjustment factor (inverse relationship)
        volatility_factor = self.p.min_volatility / volatility
        volatility_factor = min(volatility_factor, 2.0)  # Cap at 2x
        
        adjusted_size = base_size * volatility_factor
        
        # Apply maximum position size limit
        max_size = account_value * self.p.max_position_size
        final_size = min(adjusted_size, max_size)
        
        # Convert to number of units
        units = int(final_size / current_price) if current_price > 0 else 0
        
        return max(units, 1)  # Minimum 1 unit

    def get_trend_strength(self):
        """Calculate trend strength based on EMA separation and MACD"""
        if len(self.ema_fast) < 2 or len(self.ema_slow) < 2:
            return 0.0
            
        # Check for None values
        if (self.ema_fast[0] is None or self.ema_slow[0] is None or
            self.ema_slow[0] == 0):
            return 0.0
            
        # EMA separation as percentage
        ema_separation = abs(self.ema_fast[0] - self.ema_slow[0]) / self.ema_slow[0]
        
        # MACD histogram strength - check for None values
        macd_histogram = 0.0
        if (self.macd.macd[0] is not None and self.macd.signal[0] is not None):
            macd_histogram = abs(self.macd.macd[0] - self.macd.signal[0])
        
        # Combine both measures
        trend_strength = min(ema_separation * 100 + macd_histogram * 10, 1.0)
        
        return trend_strength

    def next(self):
        self.log('Close, %.5f' % self.dataclose[0])

        if self.order:
            return

        current_price = self.dataclose[0]
        
        # Skip if not enough data
        if len(self.data) < max(self.p.fast_length, self.p.slow_length, self.p.rsi_period):
            return
            
        # Check for None values in critical indicators
        if (current_price is None or self.rsi[0] is None or
            self.atr[0] is None or self.bollinger.mid[0] is None):
            return

        if not self.position:  # Not in the market
            # Calculate trend strength
            trend_strength = self.get_trend_strength()
            
            # Only trade if trend is strong enough
            if trend_strength < self.p.trend_strength_threshold:
                return
            
            # Check volatility conditions
            volatility = self.atr[0] / current_price if current_price > 0 else 0.01
            if volatility < self.p.min_volatility or volatility > self.p.max_volatility:
                return
            
            # Buy conditions - with None checks
            buy_signal = (
                self.crossover > 0 and  # EMA crossover bullish
                self.rsi[0] > self.p.rsi_oversold and  # Not oversold
                self.rsi[0] < self.p.rsi_overbought and  # Not too overbought
                self.rsi[0] > self.rsi[-1] and  # RSI rising
                self.macd.macd[0] is not None and self.macd.signal[0] is not None and
                self.macd.macd[0] > self.macd.signal[0] and  # MACD bullish
                current_price > self.bollinger.mid[0]  # Above middle BB
            )
            
            # Sell conditions - with None checks
            sell_signal = (
                self.crossover < 0 and  # EMA crossover bearish
                self.rsi[0] < self.p.rsi_overbought and  # Not overbought
                self.rsi[0] > self.p.rsi_oversold and  # Not too oversold
                self.rsi[0] < self.rsi[-1] and  # RSI falling
                self.macd.macd[0] is not None and self.macd.signal[0] is not None and
                self.macd.macd[0] < self.macd.signal[0] and  # MACD bearish
                current_price < self.bollinger.mid[0]  # Below middle BB
            )
            
            if buy_signal:
                position_size = self.calculate_position_size()
                self.log(f'BUY CREATE - Price: {current_price:.5f}, Size: {position_size}, Trend: {trend_strength:.3f}')
                self.order = self.buy(size=position_size)
                self.entry_bar = len(self)
                
            elif sell_signal:
                position_size = self.calculate_position_size()
                self.log(f'SELL CREATE - Price: {current_price:.5f}, Size: {position_size}, Trend: {trend_strength:.3f}')
                self.order = self.sell(size=position_size)
                self.entry_bar = len(self)
                
        else:  # Already in the market - manage position
            self._manage_position()

    def _manage_position(self):
        """Advanced position management with trailing stops"""
        current_price = self.dataclose[0]
        
        # Check for None values
        if current_price is None or self.buyprice is None or self.atr[0] is None or self.atr[0] == 0:
            return
        
        current_atr = self.atr[0]
        
        if self.position.size > 0:  # Long position
            # Calculate current profit/loss
            current_profit = (current_price - self.buyprice) / self.buyprice
            self.highest_profit = max(self.highest_profit, current_profit)
            
            # Fixed stop loss and take profit
            stop_loss_price = self.buyprice * (1 - self.p.stop_loss_percent)
            take_profit_price = self.buyprice * (1 + self.p.take_profit_percent)
            
            # Trailing stop logic
            trailing_stop_price = current_price * (1 - self.p.trailing_stop_percent)
            
            # Use trailing stop if we're in profit
            if current_profit > self.p.trailing_stop_percent:
                effective_stop = max(stop_loss_price, trailing_stop_price)
            else:
                effective_stop = stop_loss_price
            
            # Exit conditions
            if current_price <= effective_stop:
                self.log(f'STOP LOSS HIT (LONG), Price: {current_price:.5f}, Profit: {current_profit:.3f}')
                self.close()
            elif current_price >= take_profit_price:
                self.log(f'TAKE PROFIT HIT (LONG), Price: {current_price:.5f}, Profit: {current_profit:.3f}')
                self.close()
            # Exit on trend reversal if in small profit - with None checks
            elif (current_profit > 0.002 and  # Small profit
                  self.crossover < 0 and  # Trend reversal
                  self.rsi[0] is not None and self.rsi[0] > 70):  # Overbought
                self.log(f'TREND REVERSAL EXIT (LONG), Price: {current_price:.5f}, Profit: {current_profit:.3f}')
                self.close()
                
        elif self.position.size < 0:  # Short position
            # Calculate current profit/loss
            current_profit = (self.buyprice - current_price) / self.buyprice
            self.lowest_profit = min(self.lowest_profit, current_profit)
            
            # Fixed stop loss and take profit
            stop_loss_price = self.buyprice * (1 + self.p.stop_loss_percent)
            take_profit_price = self.buyprice * (1 - self.p.take_profit_percent)
            
            # Trailing stop logic
            trailing_stop_price = current_price * (1 + self.p.trailing_stop_percent)
            
            # Use trailing stop if we're in profit
            if current_profit > self.p.trailing_stop_percent:
                effective_stop = min(stop_loss_price, trailing_stop_price)
            else:
                effective_stop = stop_loss_price
            
            # Exit conditions
            if current_price >= effective_stop:
                self.log(f'STOP LOSS HIT (SHORT), Price: {current_price:.5f}, Profit: {current_profit:.3f}')
                self.close()
            elif current_price <= take_profit_price:
                self.log(f'TAKE PROFIT HIT (SHORT), Price: {current_price:.5f}, Profit: {current_profit:.3f}')
                self.close()
            # Exit on trend reversal if in small profit - with None checks
            elif (current_profit > 0.002 and  # Small profit
                  self.crossover > 0 and  # Trend reversal
                  self.rsi[0] is not None and self.rsi[0] < 30):  # Oversold
                self.log(f'TREND REVERSAL EXIT (SHORT), Price: {current_price:.5f}, Profit: {current_profit:.3f}')
                self.close()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    print("ImprovedForexStrategy module loaded. Run backtest_engine.py or main.py to use.")