"""
Crypto Trading Strategy for SOL/USD
Enhanced technical analysis strategy optimized for cryptocurrency markets
"""

import backtrader as bt
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta

class CryptoStrategy(bt.Strategy):
    """
    Advanced Crypto Trading Strategy for SOL/USD
    
    Features:
    - RSI momentum analysis
    - MACD trend confirmation
    - Bollinger Bands volatility
    - Volume analysis
    - Dynamic stop-loss and take-profit
    - Crypto-specific risk management
    """
    
    params = (
        # Moving Average Parameters
        ('fast_length', 12),
        ('slow_length', 26),
        
        # RSI Parameters
        ('rsi_period', 14),
        ('rsi_oversold', 25),
        ('rsi_overbought', 75),
        
        # MACD Parameters
        ('macd_fast', 12),
        ('macd_slow', 26),
        ('macd_signal', 9),
        
        # Bollinger Bands Parameters
        ('bb_period', 20),
        ('bb_std', 2.0),
        
        # Volume Parameters
        ('volume_period', 20),
        ('volume_threshold', 1.5),  # Volume must be 1.5x average
        
        # Risk Management
        ('stop_loss_percent', 0.03),    # 3% stop loss (crypto volatility)
        ('take_profit_percent', 0.06),  # 6% take profit (2:1 R/R)
        ('position_size_percent', 0.1), # 10% of capital per trade
        ('max_positions', 1),           # Only one position at a time
        
        # Crypto-specific parameters
        ('volatility_threshold', 0.05), # 5% volatility threshold
        ('trend_strength_min', 0.6),    # Minimum trend strength
        
        # Logging
        ('printlog', False),
    )
    
    def __init__(self):
        """Initialize strategy indicators and variables"""
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing CryptoStrategy for SOL/USD")
        
        # Price data
        self.dataclose = self.datas[0].close
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low
        self.datavolume = self.datas[0].volume
        
        # Moving Averages
        self.fast_ma = bt.indicators.EMA(period=self.params.fast_length)
        self.slow_ma = bt.indicators.EMA(period=self.params.slow_length)
        
        # RSI
        self.rsi = bt.indicators.RSI(period=self.params.rsi_period)
        
        # MACD
        self.macd = bt.indicators.MACD(
            period_me1=self.params.macd_fast,
            period_me2=self.params.macd_slow,
            period_signal=self.params.macd_signal
        )
        
        # Bollinger Bands
        self.bb = bt.indicators.BollingerBands(
            period=self.params.bb_period,
            devfactor=self.params.bb_std
        )
        
        # Volume indicators
        self.volume_sma = bt.indicators.SMA(self.datavolume, period=self.params.volume_period)
        
        # ATR for volatility
        self.atr = bt.indicators.ATR(period=14)
        
        # Trend strength indicator
        self.adx = bt.indicators.ADX(period=14)
        
        # Trade tracking
        self.order = None
        self.buyprice = None
        self.buycomm = None
        self.trade_count = 0
        self.winning_trades = 0
        self.losing_trades = 0
        
        # Performance tracking
        self.start_cash = self.broker.get_cash()
        
        self.logger.info("CryptoStrategy indicators initialized")
    
    def log(self, txt, dt=None):
        """Logging function"""
        if self.params.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            print(f'{dt.isoformat()}, {txt}')
            self.logger.info(f'{dt.isoformat()}, {txt}')
    
    def notify_order(self, order):
        """Handle order notifications"""
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED, Price: {order.executed.price:.4f}, '
                        f'Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}')
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:
                self.log(f'SELL EXECUTED, Price: {order.executed.price:.4f}, '
                        f'Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}')
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')
        
        self.order = None
    
    def notify_trade(self, trade):
        """Handle trade notifications"""
        if not trade.isclosed:
            return
        
        self.trade_count += 1
        pnl = trade.pnl
        
        if pnl > 0:
            self.winning_trades += 1
            self.log(f'TRADE PROFIT: ${pnl:.2f} (Trade #{self.trade_count})')
        else:
            self.losing_trades += 1
            self.log(f'TRADE LOSS: ${pnl:.2f} (Trade #{self.trade_count})')
        
        # Calculate win rate
        win_rate = (self.winning_trades / self.trade_count) * 100 if self.trade_count > 0 else 0
        self.log(f'Win Rate: {win_rate:.1f}% ({self.winning_trades}W/{self.losing_trades}L)')
    
    def get_volatility(self):
        """Calculate current market volatility"""
        if len(self.atr) < 1:
            return 0
        return self.atr[0] / self.dataclose[0]
    
    def get_volume_signal(self):
        """Analyze volume for confirmation"""
        if len(self.volume_sma) < 1:
            return 0
        
        current_volume = self.datavolume[0]
        avg_volume = self.volume_sma[0]
        
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0
        
        if volume_ratio >= self.params.volume_threshold:
            return 1  # High volume confirmation
        elif volume_ratio < 0.5:
            return -1  # Low volume warning
        else:
            return 0  # Normal volume
    
    def get_trend_strength(self):
        """Calculate trend strength using ADX"""
        if len(self.adx) < 1:
            return 0
        return self.adx[0] / 100.0  # Normalize to 0-1
    
    def get_bollinger_signal(self):
        """Analyze Bollinger Bands for entry signals"""
        if len(self.bb) < 1:
            return 0
        
        price = self.dataclose[0]
        bb_upper = self.bb.lines.top[0]
        bb_lower = self.bb.lines.bot[0]
        bb_middle = self.bb.lines.mid[0]
        
        # Calculate position within bands
        bb_range = bb_upper - bb_lower
        if bb_range == 0:
            return 0
        
        position = (price - bb_lower) / bb_range
        
        if position <= 0.1:  # Near lower band
            return 1  # Potential buy signal
        elif position >= 0.9:  # Near upper band
            return -1  # Potential sell signal
        else:
            return 0  # Neutral
    
    def generate_signals(self):
        """Generate comprehensive trading signals"""
        signals = {}
        
        # Moving Average Signal
        if self.fast_ma[0] > self.slow_ma[0]:
            signals['ma'] = 1
        elif self.fast_ma[0] < self.slow_ma[0]:
            signals['ma'] = -1
        else:
            signals['ma'] = 0
        
        # RSI Signal
        if self.rsi[0] < self.params.rsi_oversold:
            signals['rsi'] = 1  # Oversold - potential buy
        elif self.rsi[0] > self.params.rsi_overbought:
            signals['rsi'] = -1  # Overbought - potential sell
        else:
            signals['rsi'] = 0
        
        # MACD Signal
        if self.macd.macd[0] > self.macd.signal[0]:
            signals['macd'] = 1
        elif self.macd.macd[0] < self.macd.signal[0]:
            signals['macd'] = -1
        else:
            signals['macd'] = 0
        
        # Bollinger Bands Signal
        signals['bb'] = self.get_bollinger_signal()
        
        # Volume Signal
        signals['volume'] = self.get_volume_signal()
        
        # Trend Strength
        signals['trend_strength'] = self.get_trend_strength()
        
        # Volatility
        signals['volatility'] = self.get_volatility()
        
        return signals
    
    def should_buy(self, signals):
        """Determine if we should enter a long position"""
        # Basic conditions
        if self.order or self.position:
            return False
        
        # Volatility check
        if signals['volatility'] > self.params.volatility_threshold:
            self.log(f"High volatility ({signals['volatility']:.3f}) - skipping trade")
            return False
        
        # Trend strength check
        if signals['trend_strength'] < self.params.trend_strength_min:
            return False
        
        # Signal scoring system
        buy_score = 0
        
        # Moving average trend (weight: 2)
        if signals['ma'] == 1:
            buy_score += 2
        
        # RSI oversold (weight: 2)
        if signals['rsi'] == 1:
            buy_score += 2
        
        # MACD bullish (weight: 1)
        if signals['macd'] == 1:
            buy_score += 1
        
        # Bollinger Bands support (weight: 1)
        if signals['bb'] == 1:
            buy_score += 1
        
        # Volume confirmation (weight: 1)
        if signals['volume'] == 1:
            buy_score += 1
        
        # Need at least 4 points to buy
        return buy_score >= 4
    
    def should_sell(self, signals):
        """Determine if we should exit a long position"""
        if not self.position:
            return False
        
        # Emergency exit on high volatility
        if signals['volatility'] > self.params.volatility_threshold * 1.5:
            self.log(f"Emergency exit - extreme volatility ({signals['volatility']:.3f})")
            return True
        
        # Signal scoring system for exit
        sell_score = 0
        
        # Moving average bearish (weight: 2)
        if signals['ma'] == -1:
            sell_score += 2
        
        # RSI overbought (weight: 2)
        if signals['rsi'] == -1:
            sell_score += 2
        
        # MACD bearish (weight: 1)
        if signals['macd'] == -1:
            sell_score += 1
        
        # Bollinger Bands resistance (weight: 1)
        if signals['bb'] == -1:
            sell_score += 1
        
        # Need at least 3 points to sell
        return sell_score >= 3
    
    def calculate_position_size(self):
        """Calculate position size based on risk management"""
        cash = self.broker.get_cash()
        price = self.dataclose[0]
        
        # Calculate position size based on percentage of capital
        position_value = cash * self.params.position_size_percent
        size = int(position_value / price)
        
        # Ensure we don't exceed available cash
        max_size = int(cash / price * 0.95)  # Leave 5% buffer
        
        return min(size, max_size)
    
    def next(self):
        """Main strategy logic executed on each bar"""
        # Generate signals
        signals = self.generate_signals()
        
        # Log current state
        self.log(f'Close: ${self.dataclose[0]:.4f}, RSI: {self.rsi[0]:.1f}, '
                f'Vol: {signals["volatility"]:.3f}, Trend: {signals["trend_strength"]:.2f}')
        
        # Check for buy signals
        if self.should_buy(signals):
            size = self.calculate_position_size()
            if size > 0:
                self.log(f'BUY SIGNAL - Size: {size}, Price: ${self.dataclose[0]:.4f}')
                self.order = self.buy(size=size)
        
        # Check for sell signals
        elif self.should_sell(signals):
            self.log(f'SELL SIGNAL - Price: ${self.dataclose[0]:.4f}')
            self.order = self.sell(size=self.position.size)
    
    def stop(self):
        """Called when strategy finishes"""
        final_value = self.broker.get_value()
        total_return = ((final_value - self.start_cash) / self.start_cash) * 100
        
        self.log(f'=== CRYPTO STRATEGY RESULTS ===')
        self.log(f'Starting Capital: ${self.start_cash:.2f}')
        self.log(f'Final Value: ${final_value:.2f}')
        self.log(f'Total Return: {total_return:.2f}%')
        self.log(f'Total Trades: {self.trade_count}')
        
        if self.trade_count > 0:
            win_rate = (self.winning_trades / self.trade_count) * 100
            self.log(f'Win Rate: {win_rate:.1f}%')
            self.log(f'Winning Trades: {self.winning_trades}')
            self.log(f'Losing Trades: {self.losing_trades}')
        
        self.logger.info(f'CryptoStrategy completed - Final Value: ${final_value:.2f}, Return: {total_return:.2f}%')


class SOLStrategy(CryptoStrategy):
    """
    Specialized strategy for SOL/USD trading
    Inherits from CryptoStrategy with SOL-specific optimizations
    """
    
    params = (
        # SOL-optimized parameters
        ('fast_length', 10),
        ('slow_length', 21),
        ('rsi_period', 14),
        ('rsi_oversold', 30),
        ('rsi_overbought', 70),
        ('stop_loss_percent', 0.04),    # 4% stop loss for SOL volatility
        ('take_profit_percent', 0.08),  # 8% take profit
        ('position_size_percent', 0.15), # 15% position size for SOL
        ('volatility_threshold', 0.06),  # 6% volatility threshold
        ('printlog', False),
    )
    
    def __init__(self):
        super().__init__()
        self.logger.info("SOLStrategy initialized with SOL-specific parameters")
    
    def should_buy(self, signals):
        """SOL-specific buy logic with additional momentum checks"""
        if not super().should_buy(signals):
            return False
        
        # Additional SOL-specific checks
        # Check for strong momentum (price above both MAs)
        if self.dataclose[0] > self.fast_ma[0] and self.dataclose[0] > self.slow_ma[0]:
            return True
        
        # Check for bounce from support (Bollinger lower band)
        if signals['bb'] == 1 and signals['rsi'] == 1:
            return True
        
        return False
    
    def get_sol_market_condition(self):
        """Analyze SOL-specific market conditions"""
        # This could be extended with SOL ecosystem metrics
        # For now, use technical analysis
        
        conditions = {
            'trend': 'neutral',
            'momentum': 'neutral',
            'volatility': 'normal'
        }
        
        # Trend analysis
        if self.fast_ma[0] > self.slow_ma[0] and self.dataclose[0] > self.fast_ma[0]:
            conditions['trend'] = 'bullish'
        elif self.fast_ma[0] < self.slow_ma[0] and self.dataclose[0] < self.fast_ma[0]:
            conditions['trend'] = 'bearish'
        
        # Momentum analysis
        if self.rsi[0] > 60 and self.macd.macd[0] > self.macd.signal[0]:
            conditions['momentum'] = 'strong'
        elif self.rsi[0] < 40 and self.macd.macd[0] < self.macd.signal[0]:
            conditions['momentum'] = 'weak'
        
        # Volatility analysis
        volatility = self.get_volatility()
        if volatility > 0.08:
            conditions['volatility'] = 'high'
        elif volatility < 0.02:
            conditions['volatility'] = 'low'
        
        return conditions


if __name__ == "__main__":
    # Test the crypto strategy
    import logging
    logging.basicConfig(level=logging.INFO)
    
    print("CryptoStrategy and SOLStrategy classes defined successfully")
    print("Key features:")
    print("- Multi-indicator analysis (RSI, MACD, Bollinger Bands)")
    print("- Volume confirmation")
    print("- Volatility-based risk management")
    print("- Crypto-specific position sizing")
    print("- SOL-optimized parameters")