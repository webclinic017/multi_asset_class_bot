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
# TA-Lib import with robust error handling and fallback
try:
    import talib
    TALIB_AVAILABLE = True
    print("TA-Lib loaded successfully")
except ImportError as e:
    print(f"Warning: TA-Lib not available: {e}")
    print("Using fallback implementations for technical indicators.")
    TALIB_AVAILABLE = False
    try:
        from utils.talib_fallback import TalibFallback
        talib = TalibFallback()
        print("Fallback TA-Lib implementations loaded successfully")
    except ImportError:
        print("Error: Could not load fallback implementations")
        # Create minimal dummy talib module
        class DummyTalib:
            @staticmethod
            def RSI(*args, **kwargs):
                return None
            @staticmethod
            def MACD(*args, **kwargs):
                return None, None, None
            @staticmethod
            def BBANDS(*args, **kwargs):
                return None, None, None
        talib = DummyTalib()

# Import sentiment analysis
try:
    from sentiment.news_analyzer import news_analyzer
    SENTIMENT_AVAILABLE = True
except ImportError:
    SENTIMENT_AVAILABLE = False

class EnhancedCryptoStrategy(bt.Strategy):
    """
    Advanced quantitative crypto trading strategy with:
    - Volatility regime detection
    - Multi-timeframe momentum analysis
    - Advanced mean reversion techniques
    - Dynamic position sizing with Kelly Criterion
    - Crypto-specific risk management
    - Market microstructure analysis
    - News sentiment analysis integration
    - Machine learning features
    - Sentiment-based trade filtering and exits
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
        
        # Sentiment Analysis Parameters
        ('use_sentiment_filter', True),
        ('sentiment_weight', 0.3),         # Weight of sentiment in decision
        ('sentiment_threshold', 0.25),     # Minimum sentiment strength
        ('news_lookback_hours', 8),        # Hours to look back for crypto news
        ('sentiment_boost_multiplier', 1.4), # Boost for aligned sentiment
        ('sentiment_veto_threshold', -0.7), # Strong negative sentiment veto
        ('min_sentiment_confidence', 0.25), # Minimum confidence required
        ('crypto_sentiment_decay', 0.9),   # Faster decay for crypto news
        
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
        ('max_position_size', 0.25),       # 25% max position
        ('pyramid_enabled', False),         # Pyramiding
        ('scale_out_enabled', True),       # Partial profit taking
        ('take_profit_percent', 0.10),
        ('stop_loss_percent', 0.05),
        ('take_profit_percent', 0.10),
        ('stop_loss_percent', 0.05),
        ('take_profit_percent', 0.10),
        ('stop_loss_percent', 0.05),
        ('take_profit_percent', 0.10),
        ('stop_loss_percent', 0.05),
        
        # Logging
        ('printlog', False)
    )

    def __init__(self):
        """Initialize enhanced crypto strategy"""
        self.logger = logging.getLogger(__name__)
        
        # Basic price data with safety checks
        try:
            self.dataclose = self.datas[0].close
            self.datahigh = self.datas[0].high
            self.datalow = self.datas[0].low
            self.datavolume = self.datas[0].volume
        except (IndexError, AttributeError) as e:
            self.logger.error(f"Error accessing data feeds: {e}")
            raise
        
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
        self.initial_capital = self.broker.get_cash()  # Store initial capital for profit/loss calculations
        self.daily_returns = []
        
        # Initialize portfolio value tracker for accurate portfolio tracking
        from execution.portfolio_value_tracker import get_portfolio_tracker
        self.portfolio_tracker = get_portfolio_tracker(10000.0)
        
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
        
        # Sentiment tracking
        self.last_sentiment_check = None
        self.current_sentiment = None
        self.sentiment_cache_duration = 180  # 3 minutes cache for crypto (faster than forex)
        self.sentiment_score = 0.0
        self.sentiment_momentum = 0.0
        
        if SENTIMENT_AVAILABLE and self.p.use_sentiment_filter:
            self.logger.info("Enhanced Crypto Strategy initialized with sentiment analysis and advanced quantitative features")
        else:
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
            # Calculate recent volatility with bounds checking
            recent_returns = []
            data_length = len(self.data)
            lookback = min(self.p.garch_lookback, data_length - 1)
            
            for i in range(1, lookback):
                try:
                    if (i < len(self.dataclose) and
                        i + 1 < len(self.dataclose) and
                        self.dataclose[-i-1] > 0):
                        ret = (self.dataclose[-i] - self.dataclose[-i-1]) / self.dataclose[-i-1]
                        recent_returns.append(ret)
                except (IndexError, ZeroDivisionError):
                    continue
                    
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
            # Short-term trend (EMA crossover) with bounds checking
            short_trend = 0
            if (len(self.ema_fast) > 0 and len(self.ema_slow) > 0):
                short_trend = 1 if self.ema_fast[0] > self.ema_slow[0] else -1
            
            # Medium-term trend (price vs KAMA) with bounds checking
            medium_trend = 0
            if (len(self.dataclose) > 0 and len(self.kama) > 0):
                medium_trend = 1 if self.dataclose[0] > self.kama[0] else -1
            
            # Long-term trend (ADX and Aroon) with bounds checking
            trend_strength = 0.5
            if len(self.adx) > 0:
                try:
                    trend_strength = self.adx[0] / 100
                except (IndexError, TypeError):
                    trend_strength = 0.5
            
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

    def get_sentiment_signal(self):
        """Get current sentiment signal with caching optimized for crypto"""
        if not SENTIMENT_AVAILABLE or not self.p.use_sentiment_filter:
            return {
                'signal_direction': 0.0,
                'signal_strength': 0.0,
                'confidence': 0.0,
                'recommendation': 'NEUTRAL'
            }
            
        try:
            current_time = datetime.now()
            
            # Check if we need to update sentiment (faster refresh for crypto)
            if (self.last_sentiment_check is None or
                (current_time - self.last_sentiment_check).total_seconds() > self.sentiment_cache_duration):
                
                # Get fresh sentiment data
                self.current_sentiment = news_analyzer.get_trading_signal(self.p.news_lookback_hours)
                self.last_sentiment_check = current_time
                
                # Update sentiment tracking
                if self.current_sentiment:
                    new_score = self.current_sentiment.get('signal_direction', 0.0)
                    self.sentiment_momentum = new_score - self.sentiment_score
                    self.sentiment_score = new_score
                
                self.log(f'CRYPTO SENTIMENT UPDATE - Direction: {self.current_sentiment["signal_direction"]:.3f}, '
                        f'Strength: {self.current_sentiment["signal_strength"]:.3f}, '
                        f'Momentum: {self.sentiment_momentum:.3f}')
                
            return self.current_sentiment
            
        except Exception as e:
            self.logger.error(f"Error getting crypto sentiment signal: {e}")
            return {
                'signal_direction': 0.0,
                'signal_strength': 0.0,
                'confidence': 0.0,
                'recommendation': 'NEUTRAL'
            }

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
            
            # Sentiment component
            sentiment_score = 0.0
            sentiment = self.get_sentiment_signal()
            
            if (self.p.use_sentiment_filter and
                sentiment['signal_strength'] >= self.p.sentiment_threshold and
                sentiment['confidence'] >= self.p.min_sentiment_confidence):
                
                # Crypto sentiment is more volatile, so we apply decay
                sentiment_direction = sentiment['signal_direction'] * self.p.crypto_sentiment_decay
                sentiment_strength = sentiment['signal_strength']
                
                # Sentiment momentum consideration
                if abs(self.sentiment_momentum) > 0.1:
                    momentum_boost = min(abs(self.sentiment_momentum) * 2, 0.5)
                    sentiment_strength *= (1 + momentum_boost)
                
                sentiment_score = sentiment_direction * sentiment_strength
                
            signals['components']['sentiment'] = sentiment_score
            
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
                
            # Calculate final scores with sentiment integration
            sentiment_component = signals['components']['sentiment']
            
            if trend_regime == 'bullish':
                buy_score = (
                    signals['components']['momentum'] * 0.35 +
                    signals['components']['trend'] * 0.35 +
                    max(0, signals['components']['reversion']) * 0.1 +
                    max(0, signals['components']['volume']) * 0.1 +
                    max(0, sentiment_component) * self.p.sentiment_weight
                ) * weight_adjustment
                
                sell_score = (max(0, -signals['components']['reversion']) * 0.2 +
                             max(0, -sentiment_component) * self.p.sentiment_weight * 0.5) * weight_adjustment
                
            elif trend_regime == 'bearish':
                sell_score = (
                    (1 - signals['components']['momentum']) * 0.35 +
                    (1 - signals['components']['trend']) * 0.35 +
                    max(0, -signals['components']['reversion']) * 0.1 +
                    max(0, signals['components']['volume']) * 0.1 +
                    max(0, -sentiment_component) * self.p.sentiment_weight
                ) * weight_adjustment
                
                buy_score = (max(0, signals['components']['reversion']) * 0.2 +
                            max(0, sentiment_component) * self.p.sentiment_weight * 0.5) * weight_adjustment
                
            else:  # neutral or ranging
                # Mean reversion strategy with sentiment overlay
                base_buy = max(0, signals['components']['reversion']) * 0.5
                base_sell = max(0, -signals['components']['reversion']) * 0.5
                
                buy_score = (base_buy + max(0, sentiment_component) * self.p.sentiment_weight) * weight_adjustment
                sell_score = (base_sell + max(0, -sentiment_component) * self.p.sentiment_weight) * weight_adjustment
            
            # Apply sentiment boost for strong alignment
            if (self.p.use_sentiment_filter and
                abs(sentiment_component) > 0.5 and
                sentiment['signal_strength'] > 0.6):
                
                if sentiment_component > 0 and buy_score > sell_score:
                    buy_score *= self.p.sentiment_boost_multiplier
                    self.log(f'CRYPTO SENTIMENT BOOST (BUY) - Score: {buy_score:.3f}')
                elif sentiment_component < 0 and sell_score > buy_score:
                    sell_score *= self.p.sentiment_boost_multiplier
                    self.log(f'CRYPTO SENTIMENT BOOST (SELL) - Score: {sell_score:.3f}')
                
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
        """Main strategy logic for crypto trading with sentiment analysis"""
        if self.order:
            return
        
        # Safety check for minimum data (increased for backtrader indicators)
        if len(self.data) < 60:
            return
            
        # Update regimes with error handling
        try:
            self.volatility_regime, vol_confidence = self.detect_volatility_regime()
            self.trend_regime, trend_confidence = self.detect_trend_regime()
        except Exception as e:
            self.logger.error(f"Error updating regimes: {e}")
            return
        
        # Get sentiment signal for veto check
        sentiment = self.get_sentiment_signal()
        
        # Check for sentiment veto (strong negative news can override technical signals)
        if (self.p.use_sentiment_filter and
            sentiment['signal_strength'] > 0.6 and
            sentiment['signal_direction'] < self.p.sentiment_veto_threshold):
            self.log(f'CRYPTO SENTIMENT VETO - Strong negative sentiment: {sentiment["signal_direction"]:.3f}')
            return
        
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
            if (signals['buy_score'] > min_signal_strength * 0.75 and  # Lowered threshold
                signals['confidence'] > min_confidence * 0.8 and
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
                
                sentiment_info = f"Sentiment: {sentiment['recommendation']} ({sentiment['signal_direction']:.3f})" if self.p.use_sentiment_filter else "No Sentiment"
                self.log(f'CRYPTO BUY - Score: {signals["buy_score"]:.3f}, '
                        f'Vol Regime: {self.volatility_regime}, Size: {position_size:.3f}, {sentiment_info}')
                
                self.order = self.buy(size=position_size)
                self.entry_bar = len(self)
                
                # Add portfolio value change and profit/loss information
                current_portfolio_value = self.broker.get_value()
                portfolio_change = current_portfolio_value - self.initial_capital
                portfolio_change_pct = (portfolio_change / self.initial_capital) * 100
                
                # Get portfolio summary from tracker
                portfolio_summary = self.portfolio_tracker.get_portfolio_summary()
                
                self.logger.info(f"*** ENHANCED CRYPTO PORTFOLIO VALUE AFTER BUY ORDER ***")
                self.logger.info(f"  Initial Capital: ${self.initial_capital:.2f}")
                self.logger.info(f"  Current Portfolio Value: ${current_portfolio_value:.2f}")
                self.logger.info(f"  Portfolio Change: ${portfolio_change:.2f} ({portfolio_change_pct:+.2f}%)")
                self.logger.info(f"  Realized P&L: ${portfolio_summary['realized_pnl']:.2f}")
                self.logger.info(f"  Unrealized P&L: ${portfolio_summary['unrealized_pnl']:.2f}")
                self.logger.info(f"  Net P&L: ${portfolio_summary['net_pnl']:.2f}")
                
                if portfolio_change > 0:
                    self.logger.info(f"*** ENHANCED CRYPTO PROFIT: ${portfolio_change:.2f} (+{portfolio_change_pct:.2f}%) ***")
                elif portfolio_change < 0:
                    self.logger.info(f"*** ENHANCED CRYPTO LOSS: ${portfolio_change:.2f} ({portfolio_change_pct:.2f}%) ***")
                else:
                    self.logger.info(f"*** ENHANCED CRYPTO BREAK EVEN: ${portfolio_change:.2f} (0.00%) ***")
                
            # Sell signal
            elif (signals['sell_score'] > min_signal_strength * 0.75 and
                  signals['confidence'] > min_confidence * 0.8 and
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
                
                sentiment_info = f"Sentiment: {sentiment['recommendation']} ({sentiment['signal_direction']:.3f})" if self.p.use_sentiment_filter else "No Sentiment"
                self.log(f'CRYPTO SELL - Score: {signals["sell_score"]:.3f}, '
                        f'Vol Regime: {self.volatility_regime}, Size: {position_size:.3f}, {sentiment_info}')
                
                self.order = self.sell(size=position_size)
                self.entry_bar = len(self)
                
                # Add portfolio value change and profit/loss information
                current_portfolio_value = self.broker.get_value()
                portfolio_change = current_portfolio_value - self.initial_capital
                portfolio_change_pct = (portfolio_change / self.initial_capital) * 100
                
                # Get portfolio summary from tracker
                portfolio_summary = self.portfolio_tracker.get_portfolio_summary()
                
                self.logger.info(f"*** ENHANCED CRYPTO PORTFOLIO VALUE AFTER SELL ORDER ***")
                self.logger.info(f"  Initial Capital: ${self.initial_capital:.2f}")
                self.logger.info(f"  Current Portfolio Value: ${current_portfolio_value:.2f}")
                self.logger.info(f"  Portfolio Change: ${portfolio_change:.2f} ({portfolio_change_pct:+.2f}%)")
                self.logger.info(f"  Realized P&L: ${portfolio_summary['realized_pnl']:.2f}")
                self.logger.info(f"  Unrealized P&L: ${portfolio_summary['unrealized_pnl']:.2f}")
                self.logger.info(f"  Net P&L: ${portfolio_summary['net_pnl']:.2f}")
                
                if portfolio_change > 0:
                    self.logger.info(f"*** ENHANCED CRYPTO PROFIT: ${portfolio_change:.2f} (+{portfolio_change_pct:.2f}%) ***")
                elif portfolio_change < 0:
                    self.logger.info(f"*** ENHANCED CRYPTO LOSS: ${portfolio_change:.2f} ({portfolio_change_pct:.2f}%) ***")
                else:
                    self.logger.info(f"*** ENHANCED CRYPTO BREAK EVEN: ${portfolio_change:.2f} (0.00%) ***")
                
        else:  # In position
            self._manage_crypto_position(current_vol, signals)

    def _manage_crypto_position(self, volatility: float, signals: Dict[str, Any]):
        """Advanced crypto position management with sentiment analysis"""
        current_price = self.dataclose[0]
        
        # Get current sentiment for exit decisions
        sentiment = self.get_sentiment_signal()
        
        # Dynamic stop loss based on volatility
        vol_multiplier = max(2.0, min(5.0, volatility * 100))  # 2x to 5x volatility
        dynamic_stop = self.p.base_stop_loss * vol_multiplier
        
        # Dynamic take profit
        dynamic_target = self.p.base_take_profit * vol_multiplier * 0.8  # Slightly tighter
        
        if self.position.size > 0:  # Long position
            stop_price = self.buyprice * (1 - dynamic_stop)
            target_price = self.buyprice * (1 + dynamic_target)
            
            # Sentiment-based early exit for long positions
            if (self.p.use_sentiment_filter and
                sentiment['signal_strength'] > 0.6 and
                sentiment['signal_direction'] < -0.5):
                self.log(f'CRYPTO SENTIMENT EXIT (LONG) - Negative sentiment: {sentiment["signal_direction"]:.3f}')
                self.close()
                return
            
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
                
    def notify_order(self, order):
        """Enhanced order notification with portfolio tracking"""
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            
            # Update portfolio tracker
            if order.isbuy():
                self.portfolio_tracker.update_cash(self.broker.get_cash())
                self.portfolio_tracker.add_position(
                    symbol="BTC_USD",  # Assuming BTC for crypto
                    size=order.executed.size,
                    entry_price=order.executed.price,
                    commission=order.executed.comm
                )
            else:
                self.portfolio_tracker.close_position(
                    symbol="BTC_USD",
                    exit_price=order.executed.price,
                    commission=order.executed.comm
                )
            
            # Calculate portfolio change since start
            current_portfolio_value = self.broker.get_value()
            portfolio_change = current_portfolio_value - self.initial_capital
            portfolio_change_pct = (portfolio_change / self.initial_capital) * 100
            
            # Get portfolio summary from tracker
            portfolio_summary = self.portfolio_tracker.get_portfolio_summary()
            
            self.logger.info(f"*** ENHANCED CRYPTO FINAL PORTFOLIO VALUE CHANGE AFTER ORDER EXECUTION ***")
            self.logger.info(f"  Initial Capital: ${self.initial_capital:.2f}")
            self.logger.info(f"  Current Portfolio Value: ${current_portfolio_value:.2f}")
            self.logger.info(f"  Portfolio Change: ${portfolio_change:.2f} ({portfolio_change_pct:+.2f}%)")
            self.logger.info(f"  Net P&L: ${portfolio_summary['net_pnl']:.2f}")
            
            if portfolio_change > 0:
                self.logger.info(f"*** ENHANCED CRYPTO FINAL RESULT: PROFIT ${portfolio_change:.2f} (+{portfolio_change_pct:.2f}%) ***")
            elif portfolio_change < 0:
                self.logger.info(f"*** ENHANCED CRYPTO FINAL RESULT: LOSS ${portfolio_change:.2f} ({portfolio_change_pct:.2f}%) ***")
            else:
                self.logger.info(f"*** ENHANCED CRYPTO FINAL RESULT: BREAK EVEN ${portfolio_change:.2f} (0.00%) ***")
            
            self.log(f'ENHANCED CRYPTO ORDER EXECUTED - {order.getstatusname()} at {order.executed.price:.4f}')
            self.order = None
            
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f'ENHANCED CRYPTO ORDER FAILED - {order.getstatusname()}')
            self.order = None

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
            
            # Sentiment-based early exit for short positions
            if (self.p.use_sentiment_filter and
                sentiment['signal_strength'] > 0.6 and
                sentiment['signal_direction'] > 0.5):
                self.log(f'CRYPTO SENTIMENT EXIT (SHORT) - Positive sentiment: {sentiment["signal_direction"]:.3f}')
                self.close()
                return
            
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
    print("Enhanced Crypto Strategy with Advanced Quantitative Features and Sentiment Analysis loaded successfully")
    print("Key features:")
    print("- Volatility regime detection with GARCH-like analysis")
    print("- Multi-timeframe trend analysis")
    print("- Kelly Criterion position sizing")
    print("- Dynamic risk management")
    print("- Crypto-specific indicators (VWAP, MFI, OBV)")
    print("- Machine learning features")
    print("- Advanced mean reversion techniques")
    print("- Partial profit taking and scaling")
    print("- News sentiment analysis integration")
    print("- Sentiment-based trade filtering and exits")
    print("- Sentiment momentum tracking")
    print("- Crypto-optimized sentiment parameters")