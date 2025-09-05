"""
Scalping Forex Strategy for EUR_USD
Optimized for 1M and 5M timeframes with high-frequency trading capabilities
"""

import backtrader as bt
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Tuple
from scipy import stats
from sklearn.preprocessing import StandardScaler

class ScalpingForexStrategy(bt.Strategy):
    """
    High-frequency scalping strategy optimized for EUR_USD on 1M/5M timeframes
    Features:
    - Ultra-fast signal generation
    - Tight risk management
    - High win rate focus
    - Momentum and mean reversion hybrid
    - Volume-based confirmation
    """
    
    params = (
        # Core Scalping Parameters
        ('fast_ema', 5),           # Very fast EMA for quick signals
        ('slow_ema', 13),          # Fibonacci-based slow EMA
        ('signal_ema', 3),         # Ultra-fast signal line
        
        # RSI Scalping Parameters
        ('rsi_period', 7),         # Fast RSI for scalping
        ('rsi_oversold', 25),      # Scalping oversold level
        ('rsi_overbought', 75),    # Scalping overbought level
        ('rsi_neutral_low', 45),   # Neutral zone low
        ('rsi_neutral_high', 55),  # Neutral zone high
        
        # MACD Scalping Parameters
        ('macd_fast', 5),          # Ultra-fast MACD
        ('macd_slow', 13),         # Fast slow line
        ('macd_signal', 3),        # Very fast signal
        
        # Bollinger Bands for Scalping
        ('bb_period', 10),         # Short period for quick reactions
        ('bb_std', 1.5),           # Tighter bands for scalping
        ('bb_squeeze_threshold', 0.05), # Tight squeeze detection
        
        # Volatility and ATR
        ('atr_period', 7),         # Fast ATR for scalping
        ('volatility_lookback', 20), # Short lookback
        ('min_volatility', 0.00005), # Minimum volatility for trading
        ('max_volatility', 0.008),   # Maximum volatility threshold
        
        # Scalping Risk Management
        ('stop_loss_pips', 3),     # Very tight stop loss (3 pips)
        ('take_profit_pips', 6),   # 2:1 risk/reward ratio
        ('trailing_stop_pips', 2), # Tight trailing stop
        ('max_risk_per_trade', 0.01), # 1% risk per trade
        ('position_size_percent', 0.02), # 2% position size
        
        # Entry Filters
        ('min_spread', 0.00008),   # Minimum spread for entry (0.8 pips)
        ('max_spread', 0.00025),   # Maximum spread allowed (2.5 pips)
        ('volume_threshold', 1.2), # Volume confirmation threshold
        
        # Time Filters (scalping hours)
        ('trade_start_hour', 7),   # Start trading at 7 AM UTC (London open)
        ('trade_end_hour', 17),    # Stop trading at 5 PM UTC (NY close)
        ('avoid_news_minutes', 30), # Avoid trading 30 min around news
        
        # Signal Confirmation
        ('min_signal_strength', 0.6), # Minimum signal strength
        ('confirmation_bars', 2),      # Bars for signal confirmation
        ('momentum_threshold', 0.0001), # Minimum momentum for entry
        
        # Advanced Scalping Features
        ('use_price_action', True),    # Use price action patterns
        ('use_order_flow', True),      # Use order flow analysis
        ('use_support_resistance', True), # Use S/R levels
        ('scalp_session_filter', True),   # Filter by trading session
        
        # Performance Optimization
        ('max_trades_per_hour', 10),   # Limit trades per hour
        ('min_time_between_trades', 60), # Minimum seconds between trades
        ('daily_profit_target', 0.02),   # 2% daily profit target
        ('daily_loss_limit', 0.01),     # 1% daily loss limit
        
        # Logging
        ('printlog', True)
    )

    def __init__(self):
        """Initialize scalping strategy with ultra-fast indicators"""
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
        self.entry_bar = None
        self.last_trade_time = None
        
        # Performance tracking
        self.trade_count = 0
        self.winning_trades = 0
        self.daily_pnl = 0.0
        self.trades_this_hour = 0
        self.last_hour = None
        
        # Initialize scalping indicators
        self._init_scalping_indicators()
        
        # Market microstructure tracking
        self.bid_ask_spread = 0.0
        self.order_flow_imbalance = 0.0
        self.support_levels = []
        self.resistance_levels = []
        
        # Signal tracking
        self.signal_history = []
        self.last_signal_time = None
        
        self.logger.info("Scalping Forex Strategy initialized for EUR_USD")

    def _init_scalping_indicators(self):
        """Initialize ultra-fast indicators for scalping"""
        # Ultra-fast EMAs
        self.ema_fast = bt.indicators.EMA(period=self.p.fast_ema)
        self.ema_slow = bt.indicators.EMA(period=self.p.slow_ema)
        self.ema_signal = bt.indicators.EMA(period=self.p.signal_ema)
        
        # Fast RSI
        self.rsi = bt.indicators.RSI(period=self.p.rsi_period)
        self.rsi_ema = bt.indicators.EMA(self.rsi, period=3)
        
        # Ultra-fast MACD
        self.macd = bt.indicators.MACD(
            period_me1=self.p.macd_fast,
            period_me2=self.p.macd_slow,
            period_signal=self.p.macd_signal
        )
        
        # Tight Bollinger Bands
        self.bb = bt.indicators.BollingerBands(
            period=self.p.bb_period,
            devfactor=self.p.bb_std
        )
        
        # Fast ATR
        self.atr = bt.indicators.ATR(period=self.p.atr_period)
        
        # Stochastic for momentum
        self.stoch = bt.indicators.Stochastic(period=5, period_dfast=3)
        
        # Volume indicators
        self.volume_sma = bt.indicators.SMA(self.datavolume, period=10)
        self.volume_ratio = self.datavolume / self.volume_sma
        
        # Price momentum
        self.momentum = bt.indicators.Momentum(period=3)
        self.roc = bt.indicators.RateOfChange(period=5)
        
        # Support/Resistance levels
        self.highest = bt.indicators.Highest(self.datahigh, period=20)
        self.lowest = bt.indicators.Lowest(self.datalow, period=20)

    def is_trading_session(self) -> bool:
        """Check if current time is within trading session"""
        if not self.p.scalp_session_filter:
            return True
            
        try:
            current_time = self.datas[0].datetime.time(0)
            current_hour = current_time.hour
            
            # Trade during London and NY overlap (most liquid)
            return self.p.trade_start_hour <= current_hour <= self.p.trade_end_hour
        except:
            return True

    def calculate_spread(self) -> float:
        """Estimate bid-ask spread (simplified for backtesting)"""
        # In live trading, this would come from broker
        # For backtesting, estimate based on volatility
        if len(self.atr) > 0:
            return max(self.p.min_spread, min(self.atr[0] * 0.3, self.p.max_spread))
        return self.p.min_spread

    def detect_price_action_pattern(self) -> Dict[str, Any]:
        """Detect scalping price action patterns"""
        if len(self.dataclose) < 5:
            return {'pattern': None, 'strength': 0.0}
        
        # Get recent price action
        recent_closes = [self.dataclose[-i] for i in range(4, -1, -1)]
        recent_highs = [self.datahigh[-i] for i in range(4, -1, -1)]
        recent_lows = [self.datalow[-i] for i in range(4, -1, -1)]
        
        patterns = {
            'bullish_engulfing': 0.0,
            'bearish_engulfing': 0.0,
            'hammer': 0.0,
            'shooting_star': 0.0,
            'inside_bar': 0.0,
            'outside_bar': 0.0
        }
        
        try:
            # Bullish engulfing
            if (recent_closes[-2] < recent_closes[-3] and 
                recent_closes[-1] > recent_closes[-2] and
                recent_closes[-1] > recent_highs[-2]):
                patterns['bullish_engulfing'] = 0.8
            
            # Bearish engulfing
            if (recent_closes[-2] > recent_closes[-3] and 
                recent_closes[-1] < recent_closes[-2] and
                recent_closes[-1] < recent_lows[-2]):
                patterns['bearish_engulfing'] = 0.8
            
            # Inside bar (consolidation)
            if (recent_highs[-1] < recent_highs[-2] and 
                recent_lows[-1] > recent_lows[-2]):
                patterns['inside_bar'] = 0.6
            
            # Outside bar (breakout)
            if (recent_highs[-1] > recent_highs[-2] and 
                recent_lows[-1] < recent_lows[-2]):
                patterns['outside_bar'] = 0.7
        
        except Exception as e:
            self.logger.warning(f"Error in price action detection: {e}")
        
        # Find strongest pattern
        strongest_pattern = max(patterns, key=patterns.get)
        strength = patterns[strongest_pattern]
        
        return {'pattern': strongest_pattern if strength > 0.5 else None, 'strength': strength}

    def generate_scalping_signals(self) -> Dict[str, Any]:
        """Generate ultra-fast scalping signals"""
        signals = {
            'buy_score': 0.0,
            'sell_score': 0.0,
            'signal_strength': 0.0,
            'entry_type': None,
            'confidence': 0.0
        }
        
        if len(self.dataclose) < max(self.p.slow_ema, self.p.rsi_period):
            return signals
        
        try:
            # Current values
            current_price = self.dataclose[0]
            current_rsi = self.rsi[0]
            current_atr = self.atr[0]
            
            # EMA signals (trend following)
            ema_bullish = self.ema_fast[0] > self.ema_slow[0]
            ema_bearish = self.ema_fast[0] < self.ema_slow[0]
            ema_momentum = abs(self.ema_fast[0] - self.ema_slow[0]) / current_price
            
            # RSI signals (mean reversion)
            rsi_oversold = current_rsi < self.p.rsi_oversold
            rsi_overbought = current_rsi > self.p.rsi_overbought
            rsi_neutral = self.p.rsi_neutral_low < current_rsi < self.p.rsi_neutral_high
            
            # MACD signals
            macd_bullish = self.macd.macd[0] > self.macd.signal[0]
            macd_bearish = self.macd.macd[0] < self.macd.signal[0]
            
            # Bollinger Bands signals
            bb_upper = self.bb.lines.top[0]
            bb_lower = self.bb.lines.bot[0]
            bb_middle = self.bb.lines.mid[0]
            bb_position = (current_price - bb_lower) / (bb_upper - bb_lower)
            
            # Volume confirmation
            volume_surge = self.volume_ratio[0] > self.p.volume_threshold
            
            # Stochastic signals
            stoch_oversold = self.stoch.percK[0] < 20
            stoch_overbought = self.stoch.percK[0] > 80
            
            # Price action patterns
            price_action = self.detect_price_action_pattern()
            
            # Momentum signals
            momentum_bullish = self.momentum[0] > self.p.momentum_threshold
            momentum_bearish = self.momentum[0] < -self.p.momentum_threshold
            
            # Calculate buy signals
            buy_score = 0.0
            
            # Trend following buy signals
            if ema_bullish and macd_bullish:
                buy_score += 0.3
            
            # Mean reversion buy signals
            if rsi_oversold and bb_position < 0.2:
                buy_score += 0.4
            
            # Momentum buy signals
            if momentum_bullish and volume_surge:
                buy_score += 0.2
            
            # Stochastic confirmation
            if stoch_oversold and self.stoch.percK[0] > self.stoch.percD[0]:
                buy_score += 0.1
            
            # Price action confirmation
            if price_action['pattern'] in ['bullish_engulfing', 'hammer']:
                buy_score += price_action['strength'] * 0.2
            
            # Calculate sell signals
            sell_score = 0.0
            
            # Trend following sell signals
            if ema_bearish and macd_bearish:
                sell_score += 0.3
            
            # Mean reversion sell signals
            if rsi_overbought and bb_position > 0.8:
                sell_score += 0.4
            
            # Momentum sell signals
            if momentum_bearish and volume_surge:
                sell_score += 0.2
            
            # Stochastic confirmation
            if stoch_overbought and self.stoch.percK[0] < self.stoch.percD[0]:
                sell_score += 0.1
            
            # Price action confirmation
            if price_action['pattern'] in ['bearish_engulfing', 'shooting_star']:
                sell_score += price_action['strength'] * 0.2
            
            # Determine entry type
            if buy_score > sell_score and buy_score > self.p.min_signal_strength:
                signals['entry_type'] = 'BUY'
                signals['signal_strength'] = buy_score
                signals['confidence'] = min(buy_score / 1.0, 0.95)
            elif sell_score > buy_score and sell_score > self.p.min_signal_strength:
                signals['entry_type'] = 'SELL'
                signals['signal_strength'] = sell_score
                signals['confidence'] = min(sell_score / 1.0, 0.95)
            
            signals['buy_score'] = buy_score
            signals['sell_score'] = sell_score
            
        except Exception as e:
            self.logger.error(f"Error generating scalping signals: {e}")
        
        return signals

    def check_risk_filters(self) -> bool:
        """Check all risk management filters"""
        try:
            # Check trading session
            if not self.is_trading_session():
                return False
            
            # Check spread
            current_spread = self.calculate_spread()
            if current_spread > self.p.max_spread:
                return False
            
            # Check volatility
            if len(self.atr) > 0:
                current_vol = self.atr[0] / self.dataclose[0]
                if current_vol < self.p.min_volatility or current_vol > self.p.max_volatility:
                    return False
            
            # Check daily limits
            if abs(self.daily_pnl) > self.p.daily_loss_limit:
                return False
            
            if self.daily_pnl > self.p.daily_profit_target:
                return False  # Stop trading after hitting daily target
            
            # Check trades per hour limit
            current_time = self.datas[0].datetime.datetime(0)
            current_hour = current_time.hour
            
            if self.last_hour != current_hour:
                self.trades_this_hour = 0
                self.last_hour = current_hour
            
            if self.trades_this_hour >= self.p.max_trades_per_hour:
                return False
            
            # Check minimum time between trades
            if self.last_trade_time:
                time_diff = (current_time - self.last_trade_time).total_seconds()
                if time_diff < self.p.min_time_between_trades:
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error in risk filters: {e}")
            return False

    def calculate_position_size(self, signal_strength: float) -> float:
        """Calculate position size for scalping"""
        try:
            base_size = self.p.position_size_percent
            
            # Adjust for signal strength
            size_multiplier = 0.5 + (signal_strength * 0.5)  # 0.5x to 1.0x
            
            # Adjust for volatility
            if len(self.atr) > 0:
                vol_adjustment = 1.0 / (1.0 + self.atr[0] * 1000)  # Reduce size in high vol
                size_multiplier *= vol_adjustment
            
            final_size = base_size * size_multiplier
            return max(0.005, min(final_size, 0.05))  # Between 0.5% and 5%
            
        except Exception as e:
            self.logger.error(f"Error calculating position size: {e}")
            return 0.01

    def next(self):
        """Main scalping logic"""
        if self.order:
            return
        
        # Check risk filters
        if not self.check_risk_filters():
            return
        
        # Generate signals
        signals = self.generate_scalping_signals()
        
        current_price = self.dataclose[0]
        
        if not self.position:  # No position
            if signals['entry_type'] == 'BUY':
                # Calculate position size
                position_size = self.calculate_position_size(signals['signal_strength'])
                
                # Calculate stops and targets in pips
                stop_loss_price = current_price - (self.p.stop_loss_pips * 0.0001)
                take_profit_price = current_price + (self.p.take_profit_pips * 0.0001)
                
                self.log(f'BUY SIGNAL - Price: {current_price:.5f}, '
                        f'Strength: {signals["signal_strength"]:.3f}, '
                        f'Size: {position_size:.3f}, '
                        f'SL: {stop_loss_price:.5f}, TP: {take_profit_price:.5f}')
                
                self.order = self.buy(size=position_size)
                self.entry_bar = len(self)
                self.last_trade_time = self.datas[0].datetime.datetime(0)
                self.trades_this_hour += 1
                
            elif signals['entry_type'] == 'SELL':
                # Calculate position size
                position_size = self.calculate_position_size(signals['signal_strength'])
                
                # Calculate stops and targets in pips
                stop_loss_price = current_price + (self.p.stop_loss_pips * 0.0001)
                take_profit_price = current_price - (self.p.take_profit_pips * 0.0001)
                
                self.log(f'SELL SIGNAL - Price: {current_price:.5f}, '
                        f'Strength: {signals["signal_strength"]:.3f}, '
                        f'Size: {position_size:.3f}, '
                        f'SL: {stop_loss_price:.5f}, TP: {take_profit_price:.5f}')
                
                self.order = self.sell(size=position_size)
                self.entry_bar = len(self)
                self.last_trade_time = self.datas[0].datetime.datetime(0)
                self.trades_this_hour += 1
                
        else:  # In position
            self._manage_scalping_position()

    def _manage_scalping_position(self):
        """Ultra-tight position management for scalping"""
        current_price = self.dataclose[0]
        
        if self.position.size > 0:  # Long position
            # Calculate stops and targets
            stop_loss_price = self.buyprice - (self.p.stop_loss_pips * 0.0001)
            take_profit_price = self.buyprice + (self.p.take_profit_pips * 0.0001)
            
            # Trailing stop
            if not hasattr(self, 'highest_price_long'):
                self.highest_price_long = current_price
            else:
                self.highest_price_long = max(self.highest_price_long, current_price)
            
            trailing_stop_price = self.highest_price_long - (self.p.trailing_stop_pips * 0.0001)
            
            # Exit conditions
            if current_price <= stop_loss_price:
                self.log(f'STOP LOSS (LONG) - Price: {current_price:.5f}')
                self.close()
                self.highest_price_long = None
            elif current_price >= take_profit_price:
                self.log(f'TAKE PROFIT (LONG) - Price: {current_price:.5f}')
                self.close()
                self.highest_price_long = None
            elif current_price <= trailing_stop_price and current_price > self.buyprice:
                self.log(f'TRAILING STOP (LONG) - Price: {current_price:.5f}')
                self.close()
                self.highest_price_long = None
                
        elif self.position.size < 0:  # Short position
            # Calculate stops and targets
            stop_loss_price = self.buyprice + (self.p.stop_loss_pips * 0.0001)
            take_profit_price = self.buyprice - (self.p.take_profit_pips * 0.0001)
            
            # Trailing stop
            if not hasattr(self, 'lowest_price_short'):
                self.lowest_price_short = current_price
            else:
                self.lowest_price_short = min(self.lowest_price_short, current_price)
            
            trailing_stop_price = self.lowest_price_short + (self.p.trailing_stop_pips * 0.0001)
            
            # Exit conditions
            if current_price >= stop_loss_price:
                self.log(f'STOP LOSS (SHORT) - Price: {current_price:.5f}')
                self.close()
                self.lowest_price_short = None
            elif current_price <= take_profit_price:
                self.log(f'TAKE PROFIT (SHORT) - Price: {current_price:.5f}')
                self.close()
                self.lowest_price_short = None
            elif current_price >= trailing_stop_price and current_price < self.buyprice:
                self.log(f'TRAILING STOP (SHORT) - Price: {current_price:.5f}')
                self.close()
                self.lowest_price_short = None

    def log(self, txt, dt=None):
        """Enhanced logging for scalping"""
        if self.p.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            time = self.datas[0].datetime.time(0)
            current_value = self.broker.get_value()
            
            self.logger.info(f'{dt} {time} {txt} | Value: {current_value:.2f} | Daily PnL: {self.daily_pnl:.2%}')

    def notify_trade(self, trade):
        """Track scalping trade performance"""
        if not trade.isclosed:
            return
            
        self.trade_count += 1
        trade_pnl = trade.pnl
        self.daily_pnl += trade_pnl / self.broker.get_cash()  # As percentage
        
        if trade_pnl > 0:
            self.winning_trades += 1
            
        # Calculate performance metrics
        win_rate = (self.winning_trades / self.trade_count) * 100 if self.trade_count > 0 else 0
        
        self.log(f'TRADE CLOSED - PnL: {trade_pnl:.2f} pips | '
                f'Win Rate: {win_rate:.1f}% | '
                f'Total Trades: {self.trade_count}')

if __name__ == '__main__':
    print("Scalping Forex Strategy for EUR_USD loaded successfully")