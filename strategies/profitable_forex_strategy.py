"""
Simplified Profitable Forex Strategy
Focus on actual profitability with proper position sizing and risk management
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
    5. Dynamic position sizing for meaningful returns
    """
    params = (
        # Moving Average Parameters - Optimized for trends
        ('fast_length', 8),
        ('slow_length', 21),
        
        # RSI Parameters - More aggressive
        ('rsi_period', 14),
        ('rsi_oversold', 25),
        ('rsi_overbought', 75),
        
        # MACD Parameters - Enhanced momentum
        ('macd_fast', 12),
        ('macd_slow', 26),
        ('macd_signal', 9),
        
        # Risk Management - Higher reward ratios
        ('stop_loss_percent', 0.008),    # 0.8% stop loss
        ('take_profit_percent', 0.024),  # 2.4% take profit (3:1 reward/risk)
        
        # Position Sizing - CRITICAL FIX: Add proper position sizing
        ('risk_per_trade', 0.02),        # 2% risk per trade
        ('position_size_percent', 0.04), # 4% position size per trade
        ('max_position_size', 0.10),     # Maximum 10% position size
        ('dynamic_sizing', True),         # Enable dynamic position sizing
        
        # Strategy Filters - Enhanced for profitability
        ('use_rsi_filter', True),
        ('use_macd_filter', True),       # Enable MACD for better signals
        ('use_trend_filter', True),      # Strong trend following
        ('use_momentum_filter', True),   # Add momentum confirmation
        
        # Trade Management - More aggressive
        ('max_trades_per_day', 5),       # Allow more profitable opportunities
        ('min_bars_between_trades', 3),  # Faster signal response
        
        # Enhanced Features
        ('use_breakout_filter', True),   # Catch breakout moves
        ('volatility_multiplier', 1.5), # Adjust for market volatility
        ('trend_strength_min', 0.6),    # Minimum trend strength
        
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

        # Enhanced Technical Indicators for Higher Profitability
        self.sma_fast = bt.indicators.SMA(self.datas[0], period=self.p.fast_length)
        self.sma_slow = bt.indicators.SMA(self.datas[0], period=self.p.slow_length)
        self.crossover = bt.indicators.CrossOver(self.sma_fast, self.sma_slow)
        
        # RSI for momentum
        self.rsi = bt.indicators.RSI(self.datas[0], period=self.p.rsi_period)
        
        # MACD for trend confirmation
        self.macd = bt.indicators.MACD(
            self.datas[0],
            period_me1=self.p.macd_fast,
            period_me2=self.p.macd_slow,
            period_signal=self.p.macd_signal
        )
        
        # Additional indicators for higher profitability
        self.ema_fast = bt.indicators.EMA(self.datas[0], period=self.p.fast_length)
        self.ema_slow = bt.indicators.EMA(self.datas[0], period=self.p.slow_length)
        
        # Volatility indicators
        self.atr = bt.indicators.ATR(self.datas[0], period=14)
        self.bb = bt.indicators.BollingerBands(self.datas[0], period=20)
        
        # Momentum indicators
        self.momentum = bt.indicators.Momentum(self.datas[0], period=10)
        self.roc = bt.indicators.RateOfChange(self.datas[0], period=12)
        
        # Trend strength
        self.adx = bt.indicators.DirectionalMovementIndex(self.datas[0], period=14)

        # Performance tracking
        self.trade_count = 0
        self.winning_trades = 0
        self.total_pnl = 0.0

        self.logger = logging.getLogger(__name__)
        self.logger.info("ProfitableForexStrategy initialized with dynamic position sizing")

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
        
        self.trade_count += 1
        if trade.pnlcomm > 0:
            self.winning_trades += 1
        self.total_pnl += trade.pnlcomm
        
        self.log(f'TRADE CLOSED - P&L: {trade.pnlcomm:.2f}, Return: {(trade.pnlcomm/10000)*100:.3f}%')

    def calculate_position_size(self, signal_strength: float = 1.0) -> float:
        """
        Calculate position size based on account value and risk parameters
        Uses dynamic sizing based on signal strength and volatility
        """
        if not self.p.dynamic_sizing:
            return self.p.position_size_percent
        
        try:
            # Base position size
            base_size = self.p.position_size_percent
            
            # Signal strength adjustment
            signal_multiplier = signal_strength * 2.0  # Scale with signal strength
            
            # Volatility adjustment
            volatility_factor = 1.0
            if hasattr(self, 'atr') and len(self.atr) > 0:
                volatility_factor = max(0.5, min(2.0, 1.0 / (self.atr[0] / self.dataclose[0])))
            
            # Performance-based adjustment
            performance_factor = 1.0
            if self.trade_count > 0:
                win_rate = self.winning_trades / self.trade_count
                if win_rate > 0.6:
                    performance_factor = 1.2  # Increase size for good performance
                elif win_rate < 0.4:
                    performance_factor = 0.8  # Decrease size for poor performance
            
            # Calculate final position size
            position_size = base_size * signal_multiplier * volatility_factor * performance_factor
            
            # Apply maximum position size limit
            position_size = min(position_size, self.p.max_position_size)
            
            # Ensure minimum position size
            position_size = max(position_size, 0.01)  # Minimum 1%
            
            self.log(f'Position Size Calculation: Base={base_size:.4f}, Signal={signal_multiplier:.2f}, '
                   f'Volatility={volatility_factor:.2f}, Performance={performance_factor:.2f}, '
                   f'Final={position_size:.4f}')
            
            return position_size
            
        except Exception as e:
            self.logger.error(f"Error calculating position size: {e}")
            return self.p.position_size_percent  # Fallback to base size

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
            # Enhanced multi-factor signal generation for higher profitability
            
            # Check trend strength
            trend_strong = True
            if hasattr(self, 'adx') and len(self.adx) > 0:
                trend_strong = self.adx.adx[0] > (self.p.trend_strength_min * 100)
            
            # Volatility adjustment
            volatility_factor = 1.0
            if hasattr(self, 'atr') and len(self.atr) > 0:
                volatility_factor = self.p.volatility_multiplier * (self.atr[0] / current_price)
            
            # LONG SIGNALS - Multiple confirmation system
            long_signals = []
            
            # 1. MA Crossover Signal
            if self.crossover > 0:
                long_signals.append('ma_cross')
            
            # 2. EMA Trend Signal
            if self.ema_fast[0] > self.ema_slow[0] and self.ema_fast[0] > self.ema_fast[-1]:
                long_signals.append('ema_trend')
            
            # 3. RSI Momentum Signal
            if (self.rsi[0] > self.p.rsi_oversold + 10 and
                self.rsi[0] < self.p.rsi_overbought - 5 and
                self.rsi[0] > self.rsi[-1]):
                long_signals.append('rsi_momentum')
            
            # 4. MACD Signal
            if (self.macd.macd[0] > self.macd.signal[0] and
                self.macd.macd[0] > self.macd.macd[-1]):
                long_signals.append('macd_bull')
            
            # 5. Breakout Signal
            if (self.p.use_breakout_filter and
                current_price > self.bb.top[0] and
                self.momentum[0] > 0):
                long_signals.append('breakout')
            
            # 6. Strong Trend Signal
            if (self.p.use_trend_filter and trend_strong and
                self.sma_fast[0] > self.sma_slow[0] and
                current_price > self.sma_fast[0]):
                long_signals.append('strong_trend')
            
            # Execute LONG if multiple signals align
            if len(long_signals) >= 3:  # Require at least 3 confirmations
                signal_strength = len(long_signals) / 6.0  # Normalize to 0-1
                position_size = self.calculate_position_size(signal_strength)
                self.log(f'STRONG BUY - Price: {current_price:.5f}, Signals: {long_signals}, '
                       f'RSI: {self.rsi[0]:.1f}, Position Size: {position_size:.4f}')
                self.order = self.buy(size=position_size)
                self.last_trade_bar = len(self)
                self.trades_today += 1
            
            # SHORT SIGNALS - Multiple confirmation system
            short_signals = []
            
            # 1. MA Crossover Signal
            if self.crossover < 0:
                short_signals.append('ma_cross')
            
            # 2. EMA Trend Signal
            if self.ema_fast[0] < self.ema_slow[0] and self.ema_fast[0] < self.ema_fast[-1]:
                short_signals.append('ema_trend')
            
            # 3. RSI Momentum Signal
            if (self.rsi[0] < self.p.rsi_overbought - 10 and
                self.rsi[0] > self.p.rsi_oversold + 5 and
                self.rsi[0] < self.rsi[-1]):
                short_signals.append('rsi_momentum')
            
            # 4. MACD Signal
            if (self.macd.macd[0] < self.macd.signal[0] and
                self.macd.macd[0] < self.macd.macd[-1]):
                short_signals.append('macd_bear')
            
            # 5. Breakout Signal
            if (self.p.use_breakout_filter and
                current_price < self.bb.bot[0] and
                self.momentum[0] < 0):
                short_signals.append('breakdown')
            
            # 6. Strong Trend Signal
            if (self.p.use_trend_filter and trend_strong and
                self.sma_fast[0] < self.sma_slow[0] and
                current_price < self.sma_fast[0]):
                short_signals.append('strong_trend')
            
            # Execute SHORT if multiple signals align
            if len(short_signals) >= 3:  # Require at least 3 confirmations
                signal_strength = len(short_signals) / 6.0  # Normalize to 0-1
                position_size = self.calculate_position_size(signal_strength)
                self.log(f'STRONG SELL - Price: {current_price:.5f}, Signals: {short_signals}, '
                       f'RSI: {self.rsi[0]:.1f}, Position Size: {position_size:.4f}')
                self.order = self.sell(size=position_size)
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
            # Dynamic stop loss and take profit based on volatility
            volatility_adj = 1.0
            if hasattr(self, 'atr') and len(self.atr) > 0:
                volatility_adj = max(0.5, min(2.0, self.atr[0] / (current_price * 0.001)))
            
            stop_loss = self.buyprice * (1 - self.p.stop_loss_percent * volatility_adj)
            take_profit = self.buyprice * (1 + self.p.take_profit_percent * volatility_adj)
            
            # Enhanced exit conditions
            if current_price <= stop_loss:
                self.log(f'STOP LOSS (LONG) - Entry: {self.buyprice:.5f}, Exit: {current_price:.5f}')
                self.close()
            elif current_price >= take_profit:
                self.log(f'TAKE PROFIT (LONG) - Entry: {self.buyprice:.5f}, Exit: {current_price:.5f}')
                self.close()
            # Aggressive trailing stop for maximum profits
            elif current_price > self.buyprice * 1.012:  # 1.2% profit
                trailing_stop = current_price * (1 - self.p.stop_loss_percent * 0.4)
                if trailing_stop > stop_loss:
                    self.log(f'TRAILING STOP UPDATE: {trailing_stop:.5f}')
            # Early exit on signal reversal
            elif (hasattr(self, 'macd') and
                  self.macd.macd[0] < self.macd.signal[0] and
                  self.rsi[0] > 70):
                self.log(f'SIGNAL REVERSAL EXIT (LONG) - Entry: {self.buyprice:.5f}, Exit: {current_price:.5f}')
                self.close()
                    
        elif self.position.size < 0:  # Short position
            # Dynamic stop loss and take profit based on volatility
            volatility_adj = 1.0
            if hasattr(self, 'atr') and len(self.atr) > 0:
                volatility_adj = max(0.5, min(2.0, self.atr[0] / (current_price * 0.001)))
            
            stop_loss = self.buyprice * (1 + self.p.stop_loss_percent * volatility_adj)
            take_profit = self.buyprice * (1 - self.p.take_profit_percent * volatility_adj)
            
            # Enhanced exit conditions
            if current_price >= stop_loss:
                self.log(f'STOP LOSS (SHORT) - Entry: {self.buyprice:.5f}, Exit: {current_price:.5f}')
                self.close()
            elif current_price <= take_profit:
                self.log(f'TAKE PROFIT (SHORT) - Entry: {self.buyprice:.5f}, Exit: {current_price:.5f}')
                self.close()
            # Aggressive trailing stop for maximum profits
            elif current_price < self.buyprice * 0.988:  # 1.2% profit
                trailing_stop = current_price * (1 + self.p.stop_loss_percent * 0.4)
                if trailing_stop < stop_loss:
                    self.log(f'TRAILING STOP UPDATE: {trailing_stop:.5f}')
            # Early exit on signal reversal
            elif (hasattr(self, 'macd') and
                  self.macd.macd[0] > self.macd.signal[0] and
                  self.rsi[0] < 30):
                self.log(f'SIGNAL REVERSAL EXIT (SHORT) - Entry: {self.buyprice:.5f}, Exit: {current_price:.5f}')
                self.close()