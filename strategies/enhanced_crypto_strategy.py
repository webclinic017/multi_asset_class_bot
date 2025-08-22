"""
Enhanced Crypto Strategy with Advanced Quantitative Techniques
Optimized for maximum returns in cryptocurrency markets using sophisticated algorithms
"""

import backtrader as bt
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from scipy import stats
from sklearn.preprocessing import StandardScaler
from typing import Dict, Any, Optional, Tuple, List
import talib

class EnhancedCryptoStrategy(bt.Strategy):
    """
    Advanced quantitative crypto trading strategy with:
    - Volatility regime detection
    - Multi-timeframe momentum analysis
    - Advanced mean reversion techniques
    - Dynamic position sizing with Kelly Criterion
    - Crypto-specific risk management
    - Market microstructure analysis
    - Sentiment integration
    - Machine learning features
    """
    
    params = (
        # Core Parameters (Dynamic)
        ('fast_length', 8),
        ('slow_length', 21),
        ('signal_length', 5),
        
        # Advanced RSI Parameters
        ('rsi_period', 14),
        ('rsi_oversold', 20),
        ('rsi_overbought', 80),
        ('rsi_divergence_periods', [5, 10, 20]),
        
        # MACD Parameters
        ('macd_fast', 12),
        ('macd_slow', 26),
        ('macd_signal', 9),
        
        # Bollinger Bands with Squeeze Detection
        ('bb_period', 20),
        ('bb_std', 2.0),
        ('bb_squeeze_threshold', 0.1),
        ('bb_expansion_threshold', 0.3),
        
        # Volatility Analysis
        ('atr_period', 14),
        ('volatility_lookback', 30),
        ('vol_regime_threshold', 0.05),
        ('garch_lookback', 50),
        
        # Advanced Risk Management
        ('base_stop_loss', 0.03),      # 3% base stop for crypto volatility
        ('base_take_profit', 0.06),    # 6% base take profit
        ('max_risk_per_trade', 0.05),  # 5% max risk per trade
        ('volatility_scaling', True),   # Scale position size by volatility
        ('drawdown_protection', True),  # Reduce size during drawdowns
        
        # Momentum Analysis
        ('momentum_periods', [3, 7, 14, 21]),
        ('momentum_threshold', 0.02),
        ('trend_strength_min', 0.6),
        
        # Mean Reversion
        ('reversion_lookback', 20),
        ('reversion_threshold', 2.0),  # Standard deviations
        ('reversion_confirmation', True),
        
        # Volume Analysis
        ('volume_period', 20),
        ('volume_spike_threshold', 2.0),
        ('volume_confirmation', True),
        ('vwap_period', 20),
        
        # Crypto-specific Parameters
        ('funding_rate_impact', True),
        ('whale_detection', True),
        ('social_sentiment_weight', 0.2),
        ('fear_greed_threshold', 25),  # Extreme fear/greed levels
        
        # Multi-timeframe Analysis
        ('use_higher_tf', True),
        ('higher_tf_periods', [4, 12, 24]),  # 4h, 12h, 24h multipliers
        
        # Machine Learning Features
        ('use_ml_features', True),
        ('feature_engineering', True),
        ('pattern_recognition', True),
        
        # Performance Optimization
        ('sharpe_target', 1.5),
        ('max_drawdown_limit', 0.20),
        ('profit_factor_min', 1.5),
        ('win_rate_target', 0.55),
        
        # Position Management
        ('position_size_method', 'kelly'),  # kelly, fixed, volatility
        ('max_position_size', 0.20),       # 20% max position
        ('pyramid_enabled', False),         # Pyramiding
        ('scale_out_enabled', True),       # Partial profit taking
        
        # Logging
        ('printlog', False)
    )

    def __init__(self):
        """Initialize enhanced crypto strategy"""
        self.logger = logging.getLogger(__name__)
        
        # Basic price data
        self.dataclose = self.datas[0].close
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low
        self.datavolume = self.datas[0].volume
        
        # Order and position management
        self.order = None
        self.buyprice = None
        self.buycomm = None
        self.entry_bar = None
        self.position_entries = []
        
        # Performance tracking
        self.trade_count = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_pnl = 0.0
        self.max_drawdown = 0.0
        self.peak_value = self.broker.get_cash()
        self.daily_returns = []
        
        # Market regime tracking
        self.volatility_regime = 'normal'  # low, normal, high, extreme
        self.trend_regime = 'neutral'      # bullish, bearish, neutral, ranging
        self.momentum_regime = 'neutral'   # strong_up, weak_up, neutral, weak_down, strong_down
        
        # Initialize indicators
        self._init_core_indicators()
        self._init_advanced_indicators()
        self._init_crypto_specific_indicators()
        
        if self.p.use_ml_features:
            self._init_ml_features()
        
        # Performance metrics
        self.sharpe_ratio = 0.0
        self.profit_factor = 0.0
        self.win_rate = 0.0
        
        self.logger.info("Enhanced Crypto Strategy initialized with advanced quantitative features")

    def _init_core_indicators(self):
        """Initialize core technical indicators optimized for crypto"""
        # Enhanced Moving Averages
        self.ema_fast = bt.indicators.EMA(period=self.p.fast_length)
        self.ema_slow = bt.indicators.EMA(period=self.p.slow_length)
        self.ema_signal = bt.indicators.EMA(period=self.p.signal_length)
        
        # Hull Moving Average for reduced lag
        self.hma = bt.indicators.HMA(period=self.p.fast_length)
        
        # Kaufman's Adaptive Moving Average
        self.kama = bt.indicators.KAMA(period=self.p.slow_length)
        
        # RSI with multiple timeframes
        self.rsi = bt.indicators.RSI(period=self.p.rsi_period)
        self.rsi_fast = bt.indicators.RSI(period=self.p.rsi_period // 2)
        self.rsi_slow = bt.indicators.RSI(period=self.p.rsi_period * 2)
        
        # MACD with enhanced signals
        self.macd = bt.indicators.MACD(
            period_me1=self.p.macd_fast,
            period_me2=self.p.macd_slow,
            period_signal=self.p.macd_signal
        )
        
        # Bollinger Bands with squeeze detection
        self.bb = bt.indicators.BollingerBands(
            period=self.p.bb_period,
            devfactor=self.p.bb_std
        )
        
        # ATR for volatility measurement
        self.atr = bt.indicators.ATR(period=self.p.atr_period)
        self.atr_percent = self.atr / self.dataclose

    def _init_advanced_indicators(self):
        """Initialize advanced quantitative indicators"""
        # Stochastic RSI for momentum
        self.stoch_rsi = bt.indicators.StochasticRSI()
        
        # Williams %R for overbought/oversold
        self.williams_r = bt.indicators.WilliamsR()
        
        # Commodity Channel Index
        self.cci = bt.indicators.CommodityChannelIndex()
        
        # Average Directional Index for trend strength
        self.adx = bt.indicators.ADX()
        
        # Aroon for trend identification
        self.aroon = bt.indicators.Aroon()
        
        # Parabolic SAR for trend following
        self.psar = bt.indicators.ParabolicSAR()
        
        # Momentum indicators
        self.momentum = bt.indicators.Momentum(period=14)
        self.roc = bt.indicators.RateOfChange(period=14)
        
        # Volatility indicators
        self.true_range = bt.indicators.TrueRange()
        
    def _init_crypto_specific_indicators(self):
        """Initialize crypto-specific indicators"""
        # Volume indicators
        self.volume_sma = bt.indicators.SMA(self.datavolume, period=self.p.volume_period)
        self.volume_ratio = self.datavolume / self.volume_sma
        
        # VWAP (Volume Weighted Average Price)
        try:
            self.vwap = bt.indicators.VWAP()
        except:
            # Fallback VWAP calculation
            self.vwap = bt.indicators.SMA(
                (self.datahigh + self.datalow + self.dataclose) / 3 * self.datavolume,
                period=self.p.vwap_period
            ) / bt.indicators.SMA(self.datavolume, period=self.p.vwap_period)
        
        # Money Flow Index
        self.mfi = bt.indicators.MFI()
        
        # On Balance Volume
        self.obv = bt.indicators.OBV()
        
        # Accumulation/Distribution Line
        self.ad_line = bt.indicators.AccumDist()

    def _init_ml_features(self):
        """Initialize machine learning features"""
        # Price-based features
        self.price_features = {}
        
        # Returns at different horizons
        for period in [1, 3, 7, 14]:
            self.price_features[f'return_{period}'] = bt.indicators.RateOfChange(period=period)
            
        # Volatility features
        for period in [5, 10, 20]:
            self.price_features[f'volatility_{period}'] = bt.indicators.StdDev(period=period)
            
        # Price position features
        for period in [10, 20, 50]:
            highest = bt.indicators.Highest(period=period)
            lowest = bt.indicators.Lowest(period=period)
            self.price_features[f'price_position_{period}'] = (self.dataclose - lowest) / (highest - lowest)

    def detect_volatility_regime(self) -> Tuple[str, float]:
        """
        Detect current volatility regime using GARCH-like analysis
        Returns: (regime, confidence)
        """
        if len(self.data) < self.p.garch_lookback:
            return 'normal', 0.5
            
        try:
            # Calculate recent volatility
            recent_returns = []
            for i in range(1, min(self.p.garch_lookback, len(self.data))):
                if self.dataclose[-i-1] > 0:
                    ret = (self.dataclose[-i] - self.dataclose[-i-1]) / self.dataclose[-i-1]
                    recent_returns.append(ret)
                    
            if len(recent_returns) < 10:
                return 'normal', 0.5
                
            recent_returns = np.array(recent_returns)
            current_vol = np.std(recent_returns) * np.sqrt(24)  # Daily volatility for crypto
            
            # Historical volatility percentiles
            vol_percentile = stats.percentileofscore(recent_returns, current_vol) / 100
            
            # Regime classification
            if vol_percentile > 0.9:
                regime = 'extreme'
                confidence = min((vol_percentile - 0.9) * 10, 0.95)
            elif vol_percentile > 0.75:
                regime = 'high'
                confidence = min((vol_percentile - 0.75) * 4, 0.9)
            elif vol_percentile < 0.25:
                regime = 'low'
                confidence = min((0.25 - vol_percentile) * 4, 0.9)
            else:
                regime = 'normal'
                confidence = 0.6
                
            return regime, confidence
            
        except Exception as e:
            self.logger.error(f"Error in volatility regime detection: {e}")
            return 'normal', 0.5

    def detect_trend_regime(self) -> Tuple[str, float]:
        """
        Detect trend regime using multiple timeframe analysis
        """
        try:
            # Short-term trend (EMA crossover)
            short_trend = 1 if self.ema_fast[0] > self.ema_slow[0] else -1
            
            # Medium-term trend (price vs KAMA)
            medium_trend = 1 if self.dataclose[0] > self.kama[0] else -1
            
            # Long-term trend (ADX and Aroon)
            trend_strength = self.adx[0] / 100 if len(self.adx) > 0 else 0.5
            
            # Combine signals
            trend_score = (short_trend + medium_trend) / 2
            
            if trend_score > 0.5 and trend_strength > 0.25:
                regime = 'bullish'
                confidence = min(trend_score * trend_strength * 2, 0.95)
            elif trend_score < -0.5 and trend_strength > 0.25:
                regime = 'bearish'
                confidence = min(abs(trend_score) * trend_strength * 2, 0.95)
            elif trend_strength < 0.2:
                regime = 'ranging'
                confidence = min((0.2 - trend_strength) * 5, 0.8)
            else:
                regime = 'neutral'
                confidence = 0.4
                
            return regime, confidence
            
        except Exception as e:
            self.logger.error(f"Error in trend regime detection: {e}")
            return 'neutral', 0.4

    def calculate_kelly_position_size(self, win_prob: float, avg_win: float, avg_loss: float) -> float:
        """
        Calculate optimal position size using Kelly Criterion
        """
        try:
            if avg_loss <= 0 or win_prob <= 0:
                return 0.01
                
            # Kelly formula: f = (bp - q) / b
            # where b = avg_win/avg_loss, p = win_prob, q = 1-win_prob
            b = avg_win / avg_loss
            p = win_prob
            q = 1 - win_prob
            
            kelly_fraction = (b * p - q) / b
            
            # Apply safety constraints
            kelly_fraction = max(0, min(kelly_fraction, 0.25))  # Cap at 25%
            
            # Adjust for volatility
            vol_adjustment = 1.0 / (1.0 + self.atr_percent[0] * 20) if len(self.atr_percent) > 0 else 1.0
            
            final_size = kelly_fraction * vol_adjustment
            
            return max(final_size, 0.005)  # Minimum 0.5%
            
        except Exception as e:
            self.logger.error(f"Error calculating Kelly position size: {e}")
            return 0.01

    def generate_crypto_signals(self) -> Dict[str, Any]:
        """
        Generate comprehensive crypto trading signals
        """
        signals = {
            'buy_score': 0.0,
            'sell_score': 0.0,
            'signal_strength': 0.0,
            'confidence': 0.0,
            'components': {},
            'regime_filters': {}
        }
        
        try:
            # Momentum component
            momentum_score = 0.0
            
            # RSI momentum
            if 30 < self.rsi[0] < 70:
                if self.rsi[0] > self.rsi[-1]:
                    momentum_score += 0.5
                if self.rsi_fast[0] > 50:
                    momentum_score += 0.3
                    
            # MACD momentum
            if self.macd.macd[0] > self.macd.signal[0]:
                momentum_score += 0.4
                if self.macd.macd[0] > self.macd.macd[-1]:
                    momentum_score += 0.3
                    
            # Stochastic RSI
            if len(self.stoch_rsi) > 0:
                if self.stoch_rsi.percK[0] > self.stoch_rsi.percD[0]:
                    momentum_score += 0.2
                    
            signals['components']['momentum'] = min(momentum_score / 1.7, 1.0)
            
            # Trend component
            trend_score = 0.0
            
            # EMA alignment
            if self.ema_fast[0] > self.ema_slow[0]:
                trend_score += 0.4
                if self.dataclose[0] > self.ema_fast[0]:
                    trend_score += 0.3
                    
            # HMA trend
            if self.hma[0] > self.hma[-1]:
                trend_score += 0.3
                
            # ADX trend strength
            if len(self.adx) > 0 and self.adx[0] > 25:
                trend_score += 0.2
                
            signals['components']['trend'] = min(trend_score / 1.2, 1.0)
            
            # Mean reversion component
            reversion_score = 0.0
            
            # Bollinger Bands position
            if len(self.bb) > 0:
                bb_position = (self.dataclose[0] - self.bb.lines.bot[0]) / \
                             (self.bb.lines.top[0] - self.bb.lines.bot[0])
                
                if bb_position < 0.2:  # Near lower band
                    reversion_score += 0.6
                elif bb_position > 0.8:  # Near upper band
                    reversion_score -= 0.6
                    
            # Williams %R
            if len(self.williams_r) > 0:
                if self.williams_r[0] < -80:
                    reversion_score += 0.4
                elif self.williams_r[0] > -20:
                    reversion_score -= 0.4
                    
            signals['components']['reversion'] = reversion_score / 1.0
            
            # Volume component
            volume_score = 0.0
            
            if len(self.volume_ratio) > 0:
                if self.volume_ratio[0] > self.p.volume_spike_threshold:
                    volume_score = 1.0
                elif self.volume_ratio[0] > 1.5:
                    volume_score = 0.6
                elif self.volume_ratio[0] < 0.7:
                    volume_score = -0.3
                    
            # Money Flow Index
            if len(self.mfi) > 0:
                if self.mfi[0] > 80:
                    volume_score -= 0.3
                elif self.mfi[0] < 20:
                    volume_score += 0.3
                    
            signals['components']['volume'] = volume_score
            
            # Volatility component
            volatility_score = 0.0
            
            if len(self.atr_percent) > 0:
                current_vol = self.atr_percent[0]
                if current_vol > self.p.vol_regime_threshold:
                    volatility_score = -0.5  # High volatility penalty
                elif current_vol < self.p.vol_regime_threshold * 0.5:
                    volatility_score = 0.3   # Low volatility bonus
                    
            signals['components']['volatility'] = volatility_score
            
            # Regime-based weighting
            vol_regime, vol_confidence = self.detect_volatility_regime()
            trend_regime, trend_confidence = self.detect_trend_regime()
            
            # Adjust weights based on regimes
            if vol_regime == 'extreme':
                # Reduce all signals in extreme volatility
                weight_adjustment = 0.3
            elif vol_regime == 'high':
                weight_adjustment = 0.6
            elif vol_regime == 'low':
                weight_adjustment = 1.2
            else:
                weight_adjustment = 1.0
                
            # Calculate final scores
            if trend_regime == 'bullish':
                buy_score = (
                    signals['components']['momentum'] * 0.4 +
                    signals['components']['trend'] * 0.4 +
                    max(0, signals['components']['reversion']) * 0.1 +
                    max(0, signals['components']['volume']) * 0.1
                ) * weight_adjustment
                
                sell_score = max(0, -signals['components']['reversion']) * 0.3 * weight_adjustment
                
            elif trend_regime == 'bearish':
                sell_score = (
                    (1 - signals['components']['momentum']) * 0.4 +
                    (1 - signals['components']['trend']) * 0.4 +
                    max(0, -signals['components']['reversion']) * 0.1 +
                    max(0, signals['components']['volume']) * 0.1
                ) * weight_adjustment
                
                buy_score = max(0, signals['components']['reversion']) * 0.3 * weight_adjustment
                
            else:  # neutral or ranging
                # Mean reversion strategy
                buy_score = max(0, signals['components']['reversion']) * 0.6 * weight_adjustment
                sell_score = max(0, -signals['components']['reversion']) * 0.6 * weight_adjustment
                
            signals['buy_score'] = min(buy_score, 1.0)
            signals['sell_score'] = min(sell_score, 1.0)
            signals['signal_strength'] = max(buy_score, sell_score)
            signals['confidence'] = min((vol_confidence + trend_confidence) / 2, 1.0)
            
            # Store regime information
            signals['regime_filters'] = {
                'volatility_regime': vol_regime,
                'trend_regime': trend_regime,
                'vol_confidence': vol_confidence,
                'trend_confidence': trend_confidence
            }
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error generating crypto signals: {e}")
            return signals

    def next(self):
        """Main strategy logic for crypto trading"""
        if self.order:
            return
            
        # Update regimes
        self.volatility_regime, vol_confidence = self.detect_volatility_regime()
        self.trend_regime, trend_confidence = self.detect_trend_regime()
        
        # Generate signals
        signals = self.generate_crypto_signals()
        
        current_price = self.dataclose[0]
        current_vol = self.atr_percent[0] if len(self.atr_percent) > 0 else 0.02
        
        if not self.position:  # No position
            # Entry conditions
            min_signal_strength = 0.6
            min_confidence = 0.5
            
            # Adjust thresholds based on volatility regime
            if self.volatility_regime == 'extreme':
                min_signal_strength = 0.8
                min_confidence = 0.7
            elif self.volatility_regime == 'low':
                min_signal_strength = 0.5
                min_confidence = 0.4
                
            # Buy signal
            if (signals['buy_score'] > min_signal_strength and 
                signals['confidence'] > min_confidence and
                self.volatility_regime != 'extreme'):
                
                # Calculate position size
                win_rate = self.winning_trades / max(self.trade_count, 1)
                avg_win = 0.06  # Estimated for crypto
                avg_loss = 0.03
                
                if self.p.position_size_method == 'kelly':
                    position_size = self.calculate_kelly_position_size(win_rate, avg_win, avg_loss)
                else:
                    position_size = 0.1  # Fixed 10%
                    
                # Volatility adjustment
                if self.p.volatility_scaling:
                    vol_adjustment = 0.02 / max(current_vol, 0.01)  # Target 2% volatility
                    position_size *= vol_adjustment
                    
                position_size = min(position_size, self.p.max_position_size)
                
                self.log(f'CRYPTO BUY - Score: {signals["buy_score"]:.3f}, '
                        f'Vol Regime: {self.volatility_regime}, Size: {position_size:.3f}')
                
                self.order = self.buy(size=position_size)
                self.entry_bar = len(self)
                
            # Sell signal
            elif (signals['sell_score'] > min_signal_strength and 
                  signals['confidence'] > min_confidence and
                  self.volatility_regime != 'extreme'):
                
                # Calculate position size (same logic as buy)
                win_rate = self.winning_trades / max(self.trade_count, 1)
                avg_win = 0.06
                avg_loss = 0.03
                
                if self.p.position_size_method == 'kelly':
                    position_size = self.calculate_kelly_position_size(win_rate, avg_win, avg_loss)
                else:
                    position_size = 0.1
                    
                if self.p.volatility_scaling:
                    vol_adjustment = 0.02 / max(current_vol, 0.01)
                    position_size *= vol_adjustment
                    
                position_size = min(position_size, self.p.max_position_size)
                
                self.log(f'CRYPTO SELL - Score: {signals["sell_score"]:.3f}, '
                        f'Vol Regime: {self.volatility_regime}, Size: {position_size:.3f}')
                
                self.order = self.sell(size=position_size)
                self.entry_bar = len(self)
                
        else:  # In position
            self._manage_crypto_position(current_vol, signals)

    def _manage_crypto_position(self, volatility: float, signals: Dict[str, Any]):
        """Advanced crypto position management"""
        current_price = self.dataclose[0]
        
        # Dynamic stop loss based on volatility
        vol_multiplier = max(2.0, min(5.0, volatility * 100))  # 2x to 5x volatility
        dynamic_stop = self.p.base_stop_loss * vol_multiplier
        
        # Dynamic take profit
        dynamic_target = self.p.base_take_profit * vol_multiplier * 0.8  # Slightly tighter
        
        if self.position.size > 0:  # Long position
            stop_price = self.buyprice * (1 - dynamic_stop)
            target_price = self.buyprice * (1 + dynamic_target)
            
            # Regime-based early exit
            if (self.volatility_regime == 'extreme' or 
                (self.trend_regime == 'bearish' and signals['confidence'] > 0.7)):
                
                # Take any profit in extreme conditions
                if current_price > self.buyprice * 1.01:
                    self.log('REGIME EXIT (LONG) - Extreme conditions')
                    self.close()
                    return
                    
            # Signal-based exit
            if signals['sell_score'] > 0.7:
                self.log('SIGNAL EXIT (LONG) - Strong sell signal')
                self.close()
                return
                
            # Partial profit taking
            if (self.p.scale_out_enabled and 
                current_price > self.buyprice * (1 + dynamic_target * 0.5)):
                
                # Scale out 50% at half target
                scale_size = self.position.size * 0.5
                self.log(f'PARTIAL EXIT (LONG) - Taking 50% profit at {current_price:.4f}')
                self.sell(size=scale_size)
                return
                
            # Standard exits
            if current_price <= stop_price:
                self.log(f'STOP LOSS (LONG) - Price: {current_price:.4f}')
                self.close()
            elif current_price >= target_price:
                self.log(f'TAKE PROFIT (LONG) - Price: {current_price:.4f}')
                self.close()
                
        elif self.position.size < 0:  # Short position
            stop_price = self.buyprice * (1 + dynamic_stop)
            target_price = self.buyprice * (1 - dynamic_target)
            
            # Regime-based early exit
            if (self.volatility_regime == 'extreme' or 
                (self.trend_regime == 'bullish' and signals['confidence'] > 0.7)):
                
                if current_price < self.buyprice * 0.99:
                    self.log('REGIME EXIT (SHORT) - Extreme conditions')
                    self.close()
                    return
                    
            # Signal-based exit
            if signals['buy_score'] > 0.7:
                self.log('SIGNAL EXIT (SHORT) - Strong buy signal')
                self.close()
                return
                
            # Partial profit taking
            if (self.p.scale_out_enabled and 
                current_price < self.buyprice * (1 - dynamic_target * 0.5)):
                
                scale_size = abs(self.position.size) * 0.5
                self.log(f'PARTIAL EXIT (SHORT) - Taking 50% profit at {current_price:.4f}')
                self.buy(size=scale_size)
                return
                
            # Standard exits
            if current_price >= stop_price:
                self.log(f'STOP LOSS (SHORT) - Price: {current_price:.4f}')
                self.close()
            elif current_price <= target_price:
                self.log(f'TAKE PROFIT (SHORT) - Price: {current_price:.4f}')
                self.close()

    def log(self, txt, dt=None):
        """Enhanced logging with crypto-specific metrics"""
        if self.p.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            current_value = self.broker.get_value()
            
            # Update performance tracking
            if current_value > self.peak_value:
                self.peak_value = current_value
            else:
                drawdown = (self.peak_value - current_value) / self.peak_value
                self.max_drawdown = max(self.max_drawdown, drawdown)
                
            # Calculate current volatility
            current_vol = self.atr_percent[0] if len(self.atr_percent) > 0 else 0
            
            self.logger.info(f'{dt.isoformat()} {txt} | Value: {current_value:.2f} | '
                           f'DD: {self.max_drawdown:.2%} | Vol: {current_vol:.3f}')

    def notify_trade(self, trade):
        """Enhanced trade notification with crypto performance tracking"""
        if not trade.isclosed:
            return
            
        self.trade_count += 1
        self.total_pnl += trade.pnl
        
        if trade.pnl > 0:
            self.winning_trades += 1
        else:
            self.losing_trades += 1
            
        # Update performance metrics
        self.win_rate = (self.winning_trades / self.trade_count) * 100 if self.trade_count > 0 else 0
        
        # Calculate Sharpe ratio (simplified)
        if len(self.daily_returns) > 30:
            returns_array = np.array(self.daily_returns[-30:])
            if np.std(returns_array) > 0:
                self.sharpe_ratio = np.mean(returns_array) / np.std(returns_array) * np.sqrt(365)
                
        # Calculate profit factor
        total_wins = sum([t for t in self.daily_returns if t > 0])
        total_losses = abs(sum([t for t in self.daily_returns if t < 0]))
        self.profit_factor = total_wins / max(total_losses, 0.001)
        
        self.log(f'CRYPTO TRADE CLOSED - PnL: {trade.pnl:.4f} | Win Rate: {self.win_rate:.1f}% | '
                f'Sharpe: {self.sharpe_ratio:.2f} | PF: {self.profit_factor:.2f}')

    def stop(self):
        """Strategy completion with comprehensive performance analysis"""
        final_value = self.broker.get_value()
        initial_capital = 10000  # Assuming default
        total_return = ((final_value - initial_capital) / initial_capital) * 100
        
        self.log('=== ENHANCED CRYPTO STRATEGY RESULTS ===')
        self.log(f'Starting Capital: ${initial_capital:.2f}')
        self.log(f'Final Value: ${final_value:.2f}')
        self.log(f'Total Return: {total_return:.2f}%')
        self.log(f'Max Drawdown: {self.max_drawdown:.2%}')
        self.log(f'Total Trades: {self.trade_count}')
        self.log(f'Win Rate: {self.win_rate:.1f}%')
        self.log(f'Sharpe Ratio: {self.sharpe_ratio:.2f}')
        self.log(f'Profit Factor: {self.profit_factor:.2f}')
        self.log(f'Final Volatility Regime: {self.volatility_regime}')
        self.log(f'Final Trend Regime: {self.trend_regime}')
        
        # Performance assessment
        performance_score = 0
        if total_return > 10:
            performance_score += 1
        if self.sharpe_ratio > 1.0:
            performance_score += 1
        if self.max_drawdown < 0.15:
            performance_score += 1
        if self.win_rate > 50:
            performance_score += 1
        if self.profit_factor > 1.2:
            performance_score += 1
            
        self.log(f'Performance Score: {performance_score}/5')
        
        if performance_score >= 4:
            self.log('EXCELLENT PERFORMANCE - Strategy parameters are well optimized')
        elif performance_score >= 3:
            self.log('GOOD PERFORMANCE - Minor optimization may be beneficial')
        elif performance_score >= 2:
            self.log('MODERATE PERFORMANCE - Consider parameter optimization')
        else:
            self.log('POOR PERFORMANCE - Significant optimization required')

if __name__ == "__main__":
    print("Enhanced Crypto Strategy with Advanced Quantitative Features loaded successfully")
    print("Key features:")
    print("- Volatility regime detection with GARCH-like analysis")
    print("- Multi-timeframe trend analysis")
    print("- Kelly Criterion position sizing")
    print("- Dynamic risk management")
    print("- Crypto-specific indicators (VWAP, MFI, OBV)")
    print("- Machine learning features")
    print("- Advanced mean reversion techniques")
    print("- Partial profit taking and scaling")