"""
Enhanced Forex Strategy with Advanced Quantitative Techniques
Optimized for maximum returns using sophisticated risk-adjusted optimization
Now with GPU acceleration support using PyTorch
"""

import backtrader as bt
import logging
import yaml
import os
import numpy as np
import pandas as pd
import sys
from scipy import stats
from sklearn.preprocessing import StandardScaler
from typing import Dict, Any, Optional, Tuple

# GPU acceleration imports
try:
    import torch
    GPU_AVAILABLE = torch.cuda.is_available()
    if GPU_AVAILABLE:
        print(f"GPU Available for Enhanced Forex Strategy: {torch.cuda.get_device_name(0)}")
except ImportError:
    GPU_AVAILABLE = False
    torch = None

# Import custom indicators
from indicators.custom_indicators import PivotHighLow, SupplyDemandZones, VolumeProfile

# Import sentiment analysis
try:
    from sentiment.news_analyzer import news_analyzer
    SENTIMENT_AVAILABLE = True
except ImportError:
    SENTIMENT_AVAILABLE = False

class EnhancedForexStrategy(bt.Strategy):
    """
    Advanced quantitative forex trading strategy with:
    - Multi-timeframe analysis
    - Regime detection
    - Dynamic position sizing
    - Advanced risk management
    - Machine learning features
    - Volatility clustering
    - Mean reversion detection
    """
    
    params = (
        # Optimized Core Moving Average Parameters
        ('fast_length', 8),   # Faster for quicker signals
        ('slow_length', 21),  # Fibonacci number for better market resonance
        ('signal_length', 5), # Faster signal line
        
        # Enhanced RSI Parameters
        ('rsi_period', 9),    # Faster RSI for more responsive signals
        ('rsi_oversold', 20), # More aggressive oversold level
        ('rsi_overbought', 80), # More aggressive overbought level
        ('rsi_divergence_lookback', 15), # Shorter lookback for faster divergence detection
        
        # Optimized MACD Parameters
        ('macd_fast', 8),     # Faster MACD
        ('macd_slow', 21),    # Fibonacci-based slow line
        ('macd_signal', 5),   # Faster signal line
        
        # Enhanced Bollinger Bands
        ('bb_period', 16),    # Shorter period for more responsive bands
        ('bb_std', 1.8),      # Tighter bands for more signals
        ('bb_squeeze_threshold', 0.08), # More sensitive squeeze detection
        
        # Optimized Volatility Parameters
        ('atr_period', 10),   # Faster ATR
        ('volatility_lookback', 35), # Shorter lookback
        ('volatility_threshold', 0.015), # More sensitive threshold
        
        # Enhanced Risk Management for Higher Returns
        ('base_stop_loss', 0.008),     # Tighter base stop loss
        ('base_take_profit', 0.035),   # Higher take profit target
        ('dynamic_sizing', True),      # Enable dynamic position sizing
        ('max_risk_per_trade', 0.025), # Slightly higher risk per trade
        ('volatility_adjustment', True), # Adjust for volatility
        ('stop_loss_percent', 0.008),  # Tighter stop loss
        ('take_profit_percent', 0.04), # Higher take profit
        ('trailing_stop_percent', 0.004), # Tighter trailing stop
        ('position_size_percent', 0.04), # Larger position size
        ('max_position_size', 0.08),   # Higher maximum position size
        ('min_volatility', 0.00008),   # Lower minimum volatility
        ('max_volatility', 0.012),     # Higher maximum volatility
        ('trend_strength_threshold', 0.4), # Lower threshold for more trades
        
        # Enhanced Regime Detection
        ('regime_lookback', 75),       # Shorter lookback for faster adaptation
        ('trend_threshold', 0.55),     # Lower threshold for trend detection
        ('mean_reversion_threshold', 0.35), # Lower threshold for mean reversion
        
        # Optimized Supply/Demand
        ('pivot_period', 5),           # Faster pivot detection
        ('zone_lookback', 50),         # Shorter zone lookback
        ('min_zone_strength', 2.5),    # Lower minimum strength
        ('zone_buffer', 0.0002),       # Tighter zone buffer
        ('max_zones', 20),             # More zones for better coverage
        
        # Enhanced Volume Analysis
        ('volume_period', 20),         # Shorter volume period
        ('volume_levels', 30),         # More volume levels
        ('volume_confirmation', True), # Keep volume confirmation
        
        # Multi-timeframe Optimization
        ('use_higher_tf', True),
        ('higher_tf_multiplier', 3),   # Closer timeframe relationship
        
        # Enhanced Machine Learning Features
        ('use_ml_features', True),
        ('feature_lookback', 35),      # Shorter feature lookback
        ('momentum_periods', [3, 8, 13, 34]), # Fibonacci-based periods
        
        # Optimized Filters
        ('use_regime_filter', True),
        ('use_volatility_filter', True),
        ('use_correlation_filter', False), # Disable for more trades
        ('use_momentum_filter', True),
        
        # Enhanced Performance Optimization for 1-hour data
        ('min_sharpe_threshold', 0.1), # Much lower threshold for 1-hour data
        ('max_drawdown_threshold', 0.35), # Allow higher drawdown for 1-hour data
        ('profit_factor_threshold', 0.8), # Lower threshold for more trades
        
        # Enhanced Sentiment Integration
        ('sentiment_weight', 0.35),    # Higher sentiment weight
        ('sentiment_threshold', 0.25), # Lower threshold for more signals
        ('news_impact_decay', 0.92),   # Faster decay for more responsive sentiment
        
        # Advanced Features for Maximum Returns
        ('momentum_acceleration', 1.4), # Momentum acceleration factor
        ('trend_following_boost', 1.3), # Trend following boost
        ('breakout_multiplier', 1.5),   # Breakout signal multiplier
        ('mean_reversion_factor', 0.8), # Mean reversion strength
        ('volatility_expansion_threshold', 1.2), # Volatility expansion detection
        
        # GPU Acceleration
        ('use_gpu', True),             # Enable GPU acceleration
        ('gpu_batch_size', 64),        # Larger batch for complex strategy
        ('gpu_lookback', 200),         # Larger buffer for advanced analysis
        
        # Logging
        ('printlog', False)
    )

    def __init__(self):
        """Initialize enhanced strategy with advanced indicators and GPU acceleration"""
        self.logger = logging.getLogger(__name__)
        
        # === COMPREHENSIVE INITIALIZATION LOGGING ===
        self.logger.info("=== ENHANCED FOREX STRATEGY INITIALIZATION ===")
        self.logger.info(f"Strategy parameters received: {dict(self.params._getitems())}")
        
        # Basic price data
        self.dataclose = self.datas[0].close
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low
        self.datavolume = self.datas[0].volume
        
        self.logger.info(f"Data feeds initialized: close={type(self.dataclose)}, high={type(self.datahigh)}, low={type(self.datalow)}, volume={type(self.datavolume)}")
        
        # Order management
        self.order = None
        self.buyprice = None
        self.buycomm = None
        self.entry_bar = None
        
        # Performance tracking
        self.trade_count = 0
        self.winning_trades = 0
        self.total_pnl = 0.0
        self.max_drawdown = 0.0
        self.peak_value = self.broker.get_cash()
        
        self.logger.info(f"Initial broker cash: {self.peak_value}")
        
        # GPU Setup
        self.use_gpu = self.p.use_gpu and GPU_AVAILABLE and torch is not None
        self.device = 'cuda' if self.use_gpu else 'cpu'
        
        self.logger.info(f"GPU setup: use_gpu={self.p.use_gpu}, GPU_AVAILABLE={GPU_AVAILABLE}, torch_available={torch is not None}, final_use_gpu={self.use_gpu}")
        
        # GPU data buffers for accelerated calculations
        self.gpu_price_buffer = []
        self.gpu_high_buffer = []
        self.gpu_low_buffer = []
        self.gpu_volume_buffer = []
        
        # Diagnostic counters
        self.next_call_count = 0
        self.signal_generation_count = 0
        self.buy_signal_count = 0
        self.sell_signal_count = 0
        self.filtered_signal_count = 0
        
        # Initialize core indicators
        self.logger.info("Initializing core indicators...")
        self._init_core_indicators()
        
        # Initialize advanced indicators
        self.logger.info("Initializing advanced indicators...")
        self._init_advanced_indicators()
        
        # Initialize ML features
        if self.p.use_ml_features:
            self.logger.info("Initializing ML features...")
            self._init_ml_features()
        
        # Market regime tracking
        self.current_regime = 'neutral'
        self.regime_confidence = 0.0
        
        # Volatility clustering
        self.volatility_regime = 'normal'
        self.vol_cluster_strength = 0.0
        
        # Sentiment tracking
        self.sentiment_score = 0.0
        self.sentiment_momentum = 0.0
        
        gpu_status = "with GPU acceleration" if self.use_gpu else "CPU mode"
        self.logger.info(f"Enhanced Forex Strategy initialized with advanced quantitative features {gpu_status}")
        if self.use_gpu:
            self.logger.info(f"GPU Device: {torch.cuda.get_device_name(0)}")
        
        self.logger.info("=== STRATEGY INITIALIZATION COMPLETE ===")

    def _init_core_indicators(self):
        """Initialize core technical indicators"""
        # Enhanced Moving Averages
        self.ema_fast = bt.indicators.EMA(period=self.p.fast_length)
        self.ema_slow = bt.indicators.EMA(period=self.p.slow_length)
        self.sma_signal = bt.indicators.SMA(period=self.p.signal_length)
        
        # Triple EMA for trend strength
        self.tema = bt.indicators.TEMA(period=self.p.fast_length)
        
        # RSI with divergence detection
        self.rsi = bt.indicators.RSI(period=self.p.rsi_period)
        self.rsi_ema = bt.indicators.EMA(self.rsi, period=5)
        
        # MACD with histogram
        self.macd = bt.indicators.MACD(
            period_me1=self.p.macd_fast,
            period_me2=self.p.macd_slow,
            period_signal=self.p.macd_signal
        )
        
        # Bollinger Bands
        self.bb = bt.indicators.BollingerBands(
            period=self.p.bb_period,
            devfactor=self.p.bb_std
        )
        
        # ATR for volatility
        self.atr = bt.indicators.ATR(period=self.p.atr_period)
        
    def _init_advanced_indicators(self):
        """Initialize advanced quantitative indicators"""
        # Stochastic for momentum
        self.stoch = bt.indicators.Stochastic()
        
        # Williams %R
        self.williams_r = bt.indicators.WilliamsR()
        
        # Commodity Channel Index
        self.cci = bt.indicators.CommodityChannelIndex()
        
        # Average Directional Index
        self.adx = bt.indicators.ADX()
        
        # Parabolic SAR
        self.psar = bt.indicators.ParabolicSAR()
        
        # Volume indicators
        self.volume_sma = bt.indicators.SMA(self.datavolume, period=self.p.volume_period)
        # Safe volume ratio calculation to prevent division by zero
        self.volume_ratio = self.datavolume / bt.indicators.Max(self.volume_sma, 1e-8)
        
        # Custom supply/demand zones
        if hasattr(self, 'p') and getattr(self.p, 'use_supply_demand', True):
            try:
                self.supply_demand = SupplyDemandZones(
                    pivot_period=self.p.pivot_period,
                    zone_lookback=self.p.zone_lookback,
                    min_zone_strength=self.p.min_zone_strength,
                    zone_buffer=self.p.zone_buffer,
                    max_zones=self.p.max_zones
                )
            except:
                self.logger.warning("Supply/Demand zones not available")
                
    def _init_ml_features(self):
        """Initialize machine learning features"""
        # Momentum features
        self.momentum_features = {}
        for period in self.p.momentum_periods:
            self.momentum_features[f'mom_{period}'] = bt.indicators.Momentum(period=period)
            
        # Rate of change features
        self.roc_5 = bt.indicators.RateOfChange(period=5)
        self.roc_10 = bt.indicators.RateOfChange(period=10)
        self.roc_20 = bt.indicators.RateOfChange(period=20)
        
        # Price position in range - will be calculated manually in next() to avoid division by zero
        self.highest_20 = bt.indicators.Highest(self.datahigh, period=20)
        self.lowest_20 = bt.indicators.Lowest(self.datalow, period=20)

    def detect_market_regime(self) -> Tuple[str, float]:
        """
        Detect current market regime using advanced statistical methods
        Returns: (regime_type, confidence_score)
        """
        if len(self.data) < self.p.regime_lookback:
            return 'neutral', 0.0
            
        try:
            # Get recent price data
            recent_closes = np.array([self.dataclose[-i] for i in range(self.p.regime_lookback, 0, -1)])
            recent_returns = np.diff(np.log(recent_closes))
            
            # Trend detection using linear regression
            x = np.arange(len(recent_closes))
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, recent_closes)
            
            # Volatility clustering detection
            volatility = np.std(recent_returns) * np.sqrt(252)  # Annualized
            vol_ma = np.mean([np.std(recent_returns[i:i+10]) for i in range(0, len(recent_returns)-10, 5)])
            vol_ratio = volatility / max(vol_ma, 1e-8) if vol_ma > 0 else 1.0
            
            # Regime classification
            trend_strength = abs(r_value)
            
            if trend_strength > self.p.trend_threshold and slope > 0:
                regime = 'bullish_trend'
                confidence = min(trend_strength, 0.95)
            elif trend_strength > self.p.trend_threshold and slope < 0:
                regime = 'bearish_trend'
                confidence = min(trend_strength, 0.95)
            elif vol_ratio > 1.5:
                regime = 'high_volatility'
                confidence = min(vol_ratio / 2.0, 0.9)
            elif trend_strength < self.p.mean_reversion_threshold:
                regime = 'mean_reverting'
                confidence = min((self.p.mean_reversion_threshold - trend_strength) * 2, 0.8)
            else:
                regime = 'neutral'
                confidence = 0.3
                
            return regime, confidence
            
        except Exception as e:
            self.logger.error(f"Error in regime detection: {e}")
            return 'neutral', 0.0

    def calculate_dynamic_position_size(self, signal_strength: float, volatility: float) -> float:
        """
        Calculate position size using Kelly Criterion and volatility adjustment
        """
        if not self.p.dynamic_sizing:
            return 1.0
            
        try:
            # Base Kelly Criterion calculation
            win_rate = self.winning_trades / max(self.trade_count, 1)
            avg_win = 0.025  # Estimated average win
            avg_loss = 0.015  # Estimated average loss
            
            if win_rate > 0 and avg_loss > 0:
                kelly_fraction = (win_rate * avg_win - (1 - win_rate) * avg_loss) / max(avg_win, 1e-8)
                kelly_fraction = max(0, min(kelly_fraction, 0.25))  # Cap at 25%
            else:
                kelly_fraction = 0.02  # Default 2%
                
            # Adjust for signal strength
            signal_adjustment = signal_strength * 1.5
            
            # Adjust for volatility
            vol_adjustment = 1.0 / (1.0 + volatility * 10)
            
            # Adjust for regime
            regime_adjustment = 1.0
            if self.current_regime == 'high_volatility':
                regime_adjustment = 0.5
            elif self.current_regime in ['bullish_trend', 'bearish_trend']:
                regime_adjustment = 1.2
                
            final_size = kelly_fraction * signal_adjustment * vol_adjustment * regime_adjustment
            
            # Ensure within risk limits
            max_size = self.p.max_risk_per_trade / max(volatility, 0.005)
            final_size = min(final_size, max_size)
            
            return max(final_size, 0.005)  # Minimum 0.5%
            
        except Exception as e:
            self.logger.error(f"Error calculating position size: {e}")
            return 0.01

    def generate_advanced_signals(self) -> Dict[str, Any]:
        """Generate enhanced trading signals with advanced quantitative methods for maximum returns"""
        signals = {
            'buy_score': 0.0,
            'sell_score': 0.0,
            'signal_strength': 0.0,
            'regime_filter': True,
            'volatility_filter': True,
            'components': {}
        }
        
        try:
            self.logger.info("=== SIGNAL GENERATION DETAILED ANALYSIS ===")
            
            # === INDICATOR VALUES LOGGING ===
            self.logger.info("Current indicator values:")
            try:
                self.logger.info(f"  EMA Fast: {float(self.ema_fast[0]):.5f}")
                self.logger.info(f"  EMA Slow: {float(self.ema_slow[0]):.5f}")
                self.logger.info(f"  TEMA: {float(self.tema[0]):.5f}")
                self.logger.info(f"  RSI: {float(self.rsi[0]):.2f}")
                self.logger.info(f"  MACD: {float(self.macd.macd[0]):.6f}")
                self.logger.info(f"  MACD Signal: {float(self.macd.signal[0]):.6f}")
                self.logger.info(f"  BB Mid: {float(self.bb.lines.mid[0]):.5f}")
                self.logger.info(f"  BB Top: {float(self.bb.lines.top[0]):.5f}")
                self.logger.info(f"  BB Bot: {float(self.bb.lines.bot[0]):.5f}")
                self.logger.info(f"  ATR: {float(self.atr[0]):.6f}")
                self.logger.info(f"  Current Price: {float(self.dataclose[0]):.5f}")
            except Exception as indicator_error:
                self.logger.error(f"Error logging indicator values: {indicator_error}")
                # Log raw values without formatting
                self.logger.info(f"  EMA Fast: {self.ema_fast[0]}")
                self.logger.info(f"  EMA Slow: {self.ema_slow[0]}")
                self.logger.info(f"  TEMA: {self.tema[0]}")
                self.logger.info(f"  RSI: {self.rsi[0]}")
                self.logger.info(f"  MACD: {self.macd.macd[0]}")
                self.logger.info(f"  MACD Signal: {self.macd.signal[0]}")
                self.logger.info(f"  BB Mid: {self.bb.lines.mid[0]}")
                self.logger.info(f"  BB Top: {self.bb.lines.top[0]}")
                self.logger.info(f"  BB Bot: {self.bb.lines.bot[0]}")
                self.logger.info(f"  ATR: {self.atr[0]}")
                self.logger.info(f"  Current Price: {self.dataclose[0]}")
            
            # Enhanced Trend signals with acceleration
            self.logger.info("=== TREND ANALYSIS ===")
            trend_score = 0.0
            
            ema_condition = self.ema_fast[0] > self.ema_slow[0]
            self.logger.info(f"EMA Fast > Slow: {ema_condition} ({self.ema_fast[0]:.5f} > {self.ema_slow[0]:.5f})")
            if ema_condition:
                trend_score += 1.2
                self.logger.info("  Added 1.2 to trend_score")
            
            tema_condition = self.tema[0] > self.tema[-1] if len(self.tema) > 1 else False
            # Safe formatting for TEMA momentum comparison
            if len(self.tema) > 1:
                tema_prev_str = f"{float(self.tema[-1]):.5f}"
            else:
                tema_prev_str = "N/A"
            self.logger.info(f"TEMA momentum: {tema_condition} ({float(self.tema[0]):.5f} > {tema_prev_str})")
            if tema_condition:
                trend_score += 0.8
                self.logger.info("  Added 0.8 to trend_score")
            
            bb_condition = self.dataclose[0] > self.bb.lines.mid[0]
            self.logger.info(f"Price > BB Mid: {bb_condition} ({self.dataclose[0]:.5f} > {self.bb.lines.mid[0]:.5f})")
            if bb_condition:
                trend_score += 0.6
                self.logger.info("  Added 0.6 to trend_score")
            
            # Add trend acceleration detection
            if len(self.ema_fast) > 2:
                fast_acceleration = (self.ema_fast[0] - self.ema_fast[-1]) - (self.ema_fast[-1] - self.ema_fast[-2])
                self.logger.info(f"EMA Fast acceleration: {fast_acceleration:.6f}")
                if fast_acceleration > 0:
                    old_trend_score = trend_score
                    trend_score *= self.p.trend_following_boost
                    self.logger.info(f"  Applied trend boost: {old_trend_score:.3f} * {self.p.trend_following_boost} = {trend_score:.3f}")
                    
            trend_component = min(trend_score / 2.6, 1.0)
            signals['components']['trend'] = trend_component
            self.logger.info(f"Final trend component: {trend_component:.4f} (raw: {trend_score:.3f})")
            
            # Enhanced Momentum signals with multiple timeframes
            self.logger.info("=== MOMENTUM ANALYSIS ===")
            momentum_score = 0.0
            
            # RSI with enhanced levels
            rsi_condition1 = self.rsi[0] > 45 and self.rsi[0] < self.p.rsi_overbought
            rsi_condition2 = self.rsi[0] < self.p.rsi_oversold
            self.logger.info(f"RSI value: {self.rsi[0]:.2f}")
            self.logger.info(f"RSI 45-{self.p.rsi_overbought} range: {rsi_condition1}")
            self.logger.info(f"RSI oversold (<{self.p.rsi_oversold}): {rsi_condition2}")
            
            if rsi_condition1:
                momentum_score += 1.2
                self.logger.info("  Added 1.2 to momentum_score (RSI range)")
            elif rsi_condition2:
                momentum_score += 1.5
                self.logger.info("  Added 1.5 to momentum_score (RSI oversold)")
            
            # MACD with histogram analysis
            macd_condition = self.macd.macd[0] > self.macd.signal[0]
            self.logger.info(f"MACD > Signal: {macd_condition} ({self.macd.macd[0]:.6f} > {self.macd.signal[0]:.6f})")
            if macd_condition:
                momentum_score += 1.0
                self.logger.info("  Added 1.0 to momentum_score (MACD)")
                
                # Add histogram momentum (check if histogram exists)
                if hasattr(self.macd, 'histo') and len(self.macd.histo) > 1:
                    histo_condition = self.macd.histo[0] > self.macd.histo[-1]
                    self.logger.info(f"MACD histogram momentum: {histo_condition} ({self.macd.histo[0]:.6f} > {self.macd.histo[-1]:.6f})")
                    if histo_condition:
                        old_momentum = momentum_score
                        momentum_score *= self.p.momentum_acceleration
                        self.logger.info(f"  Applied momentum acceleration: {old_momentum:.3f} * {self.p.momentum_acceleration} = {momentum_score:.3f}")
            
            # Stochastic with enhanced weighting
            stoch_condition = self.stoch.percK[0] > self.stoch.percD[0] and self.stoch.percK[0] < 80
            self.logger.info(f"Stochastic K: {self.stoch.percK[0]:.2f}, D: {self.stoch.percD[0]:.2f}")
            self.logger.info(f"Stoch K>D and K<80: {stoch_condition}")
            if stoch_condition:
                momentum_score += 0.8
                self.logger.info("  Added 0.8 to momentum_score (Stochastic)")
                
            momentum_component = min(momentum_score / 3.2, 1.0)
            signals['components']['momentum'] = momentum_component
            self.logger.info(f"Final momentum component: {momentum_component:.4f} (raw: {momentum_score:.3f})")
            
            # Enhanced Mean reversion with volatility expansion
            self.logger.info("=== MEAN REVERSION ANALYSIS ===")
            reversion_score = 0.0
            bb_position = (self.dataclose[0] - self.bb.lines.bot[0]) / \
                         (self.bb.lines.top[0] - self.bb.lines.bot[0])
            
            self.logger.info(f"Bollinger Band position: {bb_position:.4f}")
            self.logger.info(f"  Price: {self.dataclose[0]:.5f}")
            self.logger.info(f"  BB Top: {self.bb.lines.top[0]:.5f}")
            self.logger.info(f"  BB Mid: {self.bb.lines.mid[0]:.5f}")
            self.logger.info(f"  BB Bot: {self.bb.lines.bot[0]:.5f}")
            
            # Enhanced Bollinger Band analysis
            if bb_position < 0.15:  # More aggressive lower band
                reversion_score += 1.3
                self.logger.info("  Added 1.3 to reversion_score (BB < 0.15)")
            elif bb_position > 0.85:  # More aggressive upper band
                reversion_score -= 1.3
                self.logger.info("  Subtracted 1.3 from reversion_score (BB > 0.85)")
            elif bb_position < 0.3:
                reversion_score += 0.7
                self.logger.info("  Added 0.7 to reversion_score (BB < 0.3)")
            elif bb_position > 0.7:
                reversion_score -= 0.7
                self.logger.info("  Subtracted 0.7 from reversion_score (BB > 0.7)")
            
            # Williams %R with enhanced sensitivity
            williams_low = self.williams_r[0] < -85
            williams_high = self.williams_r[0] > -15
            self.logger.info(f"Williams %R: {self.williams_r[0]:.2f}")
            self.logger.info(f"  Williams < -85: {williams_low}")
            self.logger.info(f"  Williams > -15: {williams_high}")
            
            if williams_low:
                reversion_score += 0.8
                self.logger.info("  Added 0.8 to reversion_score (Williams oversold)")
            elif williams_high:
                reversion_score -= 0.8
                self.logger.info("  Subtracted 0.8 from reversion_score (Williams overbought)")
            
            # Apply mean reversion factor
            old_reversion = reversion_score
            reversion_score *= self.p.mean_reversion_factor
            self.logger.info(f"Applied mean reversion factor: {old_reversion:.3f} * {self.p.mean_reversion_factor} = {reversion_score:.3f}")
            
            reversion_component = max(-1.0, min(reversion_score / 2.1, 1.0))
            signals['components']['reversion'] = reversion_component
            self.logger.info(f"Final reversion component: {reversion_component:.4f} (raw: {reversion_score:.3f})")
            
            # Enhanced Volume confirmation with breakout detection
            self.logger.info("=== VOLUME ANALYSIS ===")
            volume_score = 0.0
            if self.p.volume_confirmation and len(self.volume_ratio) > 0:
                volume_ratio_val = self.volume_ratio[0]
                self.logger.info(f"Volume ratio: {volume_ratio_val:.3f}")
                self.logger.info(f"Current volume: {self.datavolume[0]}")
                self.logger.info(f"Volume SMA: {self.volume_sma[0]}")
                
                if volume_ratio_val > 1.5:  # Strong volume breakout
                    volume_score = 1.2 * self.p.breakout_multiplier
                    self.logger.info(f"  Strong volume breakout: 1.2 * {self.p.breakout_multiplier} = {volume_score:.3f}")
                elif volume_ratio_val > 1.2:
                    volume_score = 0.8
                    self.logger.info("  Added 0.8 to volume_score (moderate volume)")
                elif volume_ratio_val < 0.7:
                    volume_score = -0.6
                    self.logger.info("  Subtracted 0.6 from volume_score (low volume)")
            else:
                self.logger.info("Volume confirmation disabled or no volume data")
                    
            volume_component = max(-1.0, min(volume_score, 1.0))
            signals['components']['volume'] = volume_component
            self.logger.info(f"Final volume component: {volume_component:.4f} (raw: {volume_score:.3f})")
            
            # Volatility expansion signal
            self.logger.info("=== VOLATILITY EXPANSION ANALYSIS ===")
            volatility_score = 0.0
            if hasattr(self, 'atr') and len(self.atr) > 5:
                current_atr = self.atr[0]
                avg_atr = np.mean([self.atr[-i] for i in range(1, 6)])
                expansion_threshold = avg_atr * self.p.volatility_expansion_threshold
                
                self.logger.info(f"Current ATR: {current_atr:.6f}")
                self.logger.info(f"Average ATR (5 periods): {avg_atr:.6f}")
                self.logger.info(f"Expansion threshold: {expansion_threshold:.6f}")
                
                if current_atr > expansion_threshold:
                    volatility_score = 0.5  # Volatility expansion signal
                    self.logger.info("  Volatility expansion detected: added 0.5")
                else:
                    self.logger.info("  No volatility expansion")
            else:
                self.logger.info("Insufficient ATR data for volatility expansion analysis")
                    
            signals['components']['volatility_expansion'] = volatility_score
            self.logger.info(f"Final volatility expansion component: {volatility_score:.4f}")
            
            # Enhanced regime-based signal weighting
            self.logger.info("=== SIGNAL WEIGHTING AND FINAL CALCULATION ===")
            regime_weights = {
                'bullish_trend': {'trend': 1.8, 'momentum': 1.4, 'reversion': 0.4, 'volume': 1.2},
                'bearish_trend': {'trend': 1.8, 'momentum': 1.4, 'reversion': 0.4, 'volume': 1.2},
                'mean_reverting': {'trend': 0.4, 'momentum': 0.9, 'reversion': 2.0, 'volume': 0.8},
                'high_volatility': {'trend': 1.0, 'momentum': 0.7, 'reversion': 1.3, 'volume': 1.5},
                'neutral': {'trend': 1.2, 'momentum': 1.1, 'reversion': 1.0, 'volume': 1.0}
            }
            
            weights = regime_weights.get(self.current_regime, regime_weights['neutral'])
            self.logger.info(f"Using regime weights for '{self.current_regime}': {weights}")
            
            # Log all component values before weighting
            self.logger.info("Component values before weighting:")
            for component, value in signals['components'].items():
                self.logger.info(f"  {component}: {value:.4f}")
            
            # Calculate enhanced weighted scores
            buy_numerator = (
                signals['components']['trend'] * weights['trend'] +
                signals['components']['momentum'] * weights['momentum'] +
                max(0, signals['components']['reversion']) * weights['reversion'] +
                max(0, signals['components']['volume']) * weights['volume'] +
                signals['components']['volatility_expansion'] * 0.5
            )
            buy_denominator = (weights['trend'] + weights['momentum'] + weights['reversion'] + weights['volume'] + 0.5)
            buy_score = buy_numerator / buy_denominator
            
            self.logger.info(f"Buy score calculation:")
            self.logger.info(f"  Numerator: {buy_numerator:.4f}")
            self.logger.info(f"  Denominator: {buy_denominator:.4f}")
            self.logger.info(f"  Final buy score: {buy_score:.4f}")
            
            sell_numerator = (
                (1 - signals['components']['trend']) * weights['trend'] +
                (1 - signals['components']['momentum']) * weights['momentum'] +
                max(0, -signals['components']['reversion']) * weights['reversion'] +
                max(0, -signals['components']['volume']) * weights['volume'] +
                signals['components']['volatility_expansion'] * 0.3
            )
            sell_denominator = (weights['trend'] + weights['momentum'] + weights['reversion'] + weights['volume'] + 0.3)
            sell_score = sell_numerator / sell_denominator
            
            self.logger.info(f"Sell score calculation:")
            self.logger.info(f"  Numerator: {sell_numerator:.4f}")
            self.logger.info(f"  Denominator: {sell_denominator:.4f}")
            self.logger.info(f"  Final sell score: {sell_score:.4f}")
            
            signals['buy_score'] = buy_score
            signals['sell_score'] = sell_score
            signals['signal_strength'] = max(buy_score, sell_score)
            
            self.logger.info(f"Signal strength: {signals['signal_strength']:.4f}")
            
            # Enhanced filters with very lenient thresholds for 1-hour data
            self.logger.info("=== FILTER EVALUATION ===")
            if self.p.use_volatility_filter:
                current_vol = self.atr[0] / self.dataclose[0] if self.dataclose[0] > 0 else 0
                vol_threshold = self.p.volatility_threshold * 3.0
                vol_filter_pass = current_vol <= vol_threshold
                
                self.logger.info(f"Volatility filter:")
                self.logger.info(f"  Current vol: {current_vol:.6f}")
                self.logger.info(f"  Threshold: {vol_threshold:.6f}")
                self.logger.info(f"  Filter pass: {vol_filter_pass}")
                
                if not vol_filter_pass:
                    signals['volatility_filter'] = False
                    self.logger.info("  VOLATILITY FILTER FAILED")
                else:
                    self.logger.info("  Volatility filter passed")
            
            self.logger.info(f"Final signal summary:")
            self.logger.info(f"  Buy score: {signals['buy_score']:.4f}")
            self.logger.info(f"  Sell score: {signals['sell_score']:.4f}")
            self.logger.info(f"  Volatility filter: {signals['volatility_filter']}")
            self.logger.info(f"  Regime filter: {signals['regime_filter']}")
                    
            return signals
            
        except Exception as e:
            import traceback
            self.logger.error(f"Error generating enhanced signals: {str(e)}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return signals

    def next(self):
        """Main strategy logic with advanced quantitative analysis"""
        self.next_call_count += 1
        
        # === COMPREHENSIVE NEXT() METHOD LOGGING ===
        if self.next_call_count <= 10 or self.next_call_count % 100 == 0:
            self.logger.info(f"=== NEXT() CALL #{self.next_call_count} ===")
            self.logger.info(f"Current bar length: {len(self.data)}")
            self.logger.info(f"Current datetime: {self.datas[0].datetime.datetime(0)}")
            self.logger.info(f"Current price: {self.dataclose[0]:.5f}")
            self.logger.info(f"Current position: {self.position.size if self.position else 0}")
            self.logger.info(f"Pending order: {self.order is not None}")
            
            # === BROKER STATE MONITORING ===
            self.logger.info(f"=== BROKER STATE MONITORING ===")
            self.logger.info(f"Broker cash: {self.broker.get_cash():.2f}")
            self.logger.info(f"Broker value: {self.broker.get_value():.2f}")
            if self.position:
                self.logger.info(f"Position size: {self.position.size}")
                self.logger.info(f"Position price: {self.position.price:.5f}")
                self.logger.info(f"Position value: {self.position.size * self.dataclose[0]:.2f}")
                self.logger.info(f"Position P&L: {(self.dataclose[0] - self.position.price) * self.position.size:.2f}")
            else:
                self.logger.info(f"No open position")
                
            # Check for pending orders
            if self.order:
                self.logger.info(f"=== PENDING ORDER STATUS ===")
                self.logger.info(f"Order ref: {self.order.ref}")
                self.logger.info(f"Order status: {self.order.getstatusname()}")
                self.logger.info(f"Order alive: {self.order.alive()}")
                self.logger.info(f"Order size: {self.order.size}")
                self.logger.info(f"Order type: {self.order.ordtype}")
                
                # Check if order is stuck
                if hasattr(self, 'order_submitted_bar'):
                    bars_since_submission = len(self) - self.order_submitted_bar
                    if bars_since_submission > 5:  # Order stuck for more than 5 bars
                        self.logger.warning(f"*** ORDER POTENTIALLY STUCK ***")
                        self.logger.warning(f"  Bars since submission: {bars_since_submission}")
                        self.logger.warning(f"  Order status: {self.order.getstatusname()}")
        
        if self.order:
            if self.next_call_count <= 10 or self.next_call_count % 100 == 0:
                self.logger.info("Skipping next() - pending order exists")
            return
        
        # === DATA AVAILABILITY CHECK ===
        try:
            # Check if we have enough data for indicators
            min_data_required = max(self.p.slow_length, self.p.regime_lookback, self.p.bb_period, self.p.atr_period)
            if len(self.data) < min_data_required:
                if self.next_call_count <= 10:
                    self.logger.info(f"Insufficient data: {len(self.data)} < {min_data_required} required")
                return
            
            # Validate current data
            if self.dataclose[0] <= 0:
                self.logger.warning(f"Invalid price data: {self.dataclose[0]}")
                return
                
        except Exception as e:
            self.logger.error(f"Data validation error: {e}")
            return
            
        # Update market regime
        self.logger.info("Detecting market regime...")
        self.current_regime, self.regime_confidence = self.detect_market_regime()
        
        if self.next_call_count <= 10 or self.next_call_count % 100 == 0:
            self.logger.info(f"Market regime: {self.current_regime} (confidence: {self.regime_confidence:.3f})")
        
        # Generate signals
        self.logger.info("Generating trading signals...")
        self.signal_generation_count += 1
        signals = self.generate_advanced_signals()
        
        # === DETAILED SIGNAL ANALYSIS ===
        self.logger.info(f"=== SIGNAL ANALYSIS #{self.signal_generation_count} ===")
        self.logger.info(f"Buy score: {signals['buy_score']:.4f}")
        self.logger.info(f"Sell score: {signals['sell_score']:.4f}")
        self.logger.info(f"Signal strength: {signals['signal_strength']:.4f}")
        self.logger.info(f"Volatility filter: {signals['volatility_filter']}")
        self.logger.info(f"Regime filter: {signals['regime_filter']}")
        
        # Log signal components
        if 'components' in signals:
            self.logger.info("Signal components:")
            for component, value in signals['components'].items():
                self.logger.info(f"  {component}: {value:.4f}")
        
        # Current market conditions
        current_price = self.dataclose[0]
        current_vol = self.atr[0] / current_price if current_price > 0 else 0
        
        self.logger.info(f"Current market conditions:")
        self.logger.info(f"  Price: {current_price:.5f}")
        self.logger.info(f"  Volatility: {current_vol:.6f}")
        self.logger.info(f"  ATR: {self.atr[0]:.6f}")
        
        if not self.position:  # No position
            self.logger.info("=== ENTRY LOGIC EVALUATION ===")
            
            # Check buy conditions
            buy_score_ok = signals['buy_score'] > 0.15
            buy_vol_filter_ok = signals['volatility_filter']
            buy_regime_filter_ok = signals['regime_filter']
            
            self.logger.info(f"Buy conditions check:")
            self.logger.info(f"  Score > 0.15: {buy_score_ok} ({signals['buy_score']:.4f})")
            self.logger.info(f"  Volatility filter: {buy_vol_filter_ok}")
            self.logger.info(f"  Regime filter: {buy_regime_filter_ok}")
            
            # Check sell conditions
            sell_score_ok = signals['sell_score'] > 0.15
            sell_vol_filter_ok = signals['volatility_filter']
            sell_regime_filter_ok = signals['regime_filter']
            
            self.logger.info(f"Sell conditions check:")
            self.logger.info(f"  Score > 0.15: {sell_score_ok} ({signals['sell_score']:.4f})")
            self.logger.info(f"  Volatility filter: {sell_vol_filter_ok}")
            self.logger.info(f"  Regime filter: {sell_regime_filter_ok}")
            
            # Entry logic (much lower threshold for 1-hour data)
            if (buy_score_ok and buy_vol_filter_ok and buy_regime_filter_ok):
                
                self.buy_signal_count += 1
                self.logger.info(f"BUY SIGNAL TRIGGERED #{self.buy_signal_count}")
                
                # Calculate position size
                position_size = self.calculate_dynamic_position_size(
                    signals['signal_strength'], current_vol
                )
                
                # Calculate stops and targets
                stop_distance = max(self.p.base_stop_loss, current_vol * 2)
                target_distance = stop_distance * 2.5  # 2.5:1 R/R minimum
                
                self.logger.info(f"Position sizing:")
                self.logger.info(f"  Size: {position_size:.6f}")
                self.logger.info(f"  Stop distance: {stop_distance:.6f}")
                self.logger.info(f"  Target distance: {target_distance:.6f}")
                
                self.log(f'BUY SIGNAL - Score: {signals["buy_score"]:.3f}, '
                        f'Regime: {self.current_regime}, Size: {position_size:.3f}')
                
                try:
                    self.logger.info(f"*** PLACING BUY ORDER ***")
                    self.logger.info(f"  Pre-order broker cash: {self.broker.get_cash():.2f}")
                    self.logger.info(f"  Pre-order broker value: {self.broker.get_value():.2f}")
                    self.logger.info(f"  Order size: {position_size}")
                    self.logger.info(f"  Current price: {current_price:.5f}")
                    self.logger.info(f"  Required margin: {position_size * current_price:.2f}")
                    
                    # Check if we have enough cash
                    required_cash = position_size * current_price
                    available_cash = self.broker.get_cash()
                    self.logger.info(f"  Cash check: Required {required_cash:.2f}, Available {available_cash:.2f}")
                    
                    if required_cash > available_cash:
                        self.logger.error(f"*** INSUFFICIENT CASH FOR BUY ORDER ***")
                        self.logger.error(f"  Required: {required_cash:.2f}, Available: {available_cash:.2f}")
                        return
                    
                    self.order = self.buy(size=position_size)
                    self.entry_bar = len(self)
                    self.order_submitted_bar = len(self)  # Track when order was submitted
                    
                    self.logger.info(f"*** BUY ORDER SUBMITTED ***")
                    self.logger.info(f"  Order reference: {self.order.ref if self.order else 'None'}")
                    self.logger.info(f"  Order object: {self.order}")
                    self.logger.info(f"  Order status: {self.order.getstatusname() if self.order else 'None'}")
                    self.logger.info(f"  Order alive: {self.order.alive() if self.order else 'None'}")
                    self.logger.info(f"  Submitted at bar: {self.order_submitted_bar}")
                    
                except Exception as e:
                    self.logger.error(f"*** BUY ORDER PLACEMENT FAILED ***")
                    self.logger.error(f"  Error: {e}")
                    import traceback
                    self.logger.error(f"  Traceback: {traceback.format_exc()}")
                
            elif (sell_score_ok and sell_vol_filter_ok and sell_regime_filter_ok):
                
                self.sell_signal_count += 1
                self.logger.info(f"SELL SIGNAL TRIGGERED #{self.sell_signal_count}")
                
                # Calculate position size
                position_size = self.calculate_dynamic_position_size(
                    signals['signal_strength'], current_vol
                )
                
                self.logger.info(f"Position sizing:")
                self.logger.info(f"  Size: {position_size:.6f}")
                
                self.log(f'SELL SIGNAL - Score: {signals["sell_score"]:.3f}, '
                        f'Regime: {self.current_regime}, Size: {position_size:.3f}')
                
                try:
                    self.logger.info(f"*** PLACING SELL ORDER ***")
                    self.logger.info(f"  Pre-order broker cash: {self.broker.get_cash():.2f}")
                    self.logger.info(f"  Pre-order broker value: {self.broker.get_value():.2f}")
                    self.logger.info(f"  Order size: {position_size}")
                    self.logger.info(f"  Current price: {current_price:.5f}")
                    self.logger.info(f"  Required margin: {position_size * current_price:.2f}")
                    
                    # Check if we have enough cash for margin
                    required_cash = position_size * current_price
                    available_cash = self.broker.get_cash()
                    self.logger.info(f"  Cash check: Required {required_cash:.2f}, Available {available_cash:.2f}")
                    
                    if required_cash > available_cash:
                        self.logger.error(f"*** INSUFFICIENT CASH FOR SELL ORDER ***")
                        self.logger.error(f"  Required: {required_cash:.2f}, Available: {available_cash:.2f}")
                        return
                    
                    self.order = self.sell(size=position_size)
                    self.entry_bar = len(self)
                    self.order_submitted_bar = len(self)  # Track when order was submitted
                    
                    self.logger.info(f"*** SELL ORDER SUBMITTED ***")
                    self.logger.info(f"  Order reference: {self.order.ref if self.order else 'None'}")
                    self.logger.info(f"  Order object: {self.order}")
                    self.logger.info(f"  Order status: {self.order.getstatusname() if self.order else 'None'}")
                    self.logger.info(f"  Order alive: {self.order.alive() if self.order else 'None'}")
                    self.logger.info(f"  Submitted at bar: {self.order_submitted_bar}")
                    
                except Exception as e:
                    self.logger.error(f"*** SELL ORDER PLACEMENT FAILED ***")
                    self.logger.error(f"  Error: {e}")
                    import traceback
                    self.logger.error(f"  Traceback: {traceback.format_exc()}")
                    
            else:
                # Log why no signal was generated
                self.filtered_signal_count += 1
                if self.next_call_count <= 10 or self.filtered_signal_count % 50 == 0:
                    self.logger.info(f"NO SIGNAL #{self.filtered_signal_count} - Conditions not met")
                    if not buy_score_ok and not sell_score_ok:
                        self.logger.info(f"  Both scores too low: buy={signals['buy_score']:.4f}, sell={signals['sell_score']:.4f}")
                    if not signals['volatility_filter']:
                        self.logger.info(f"  Volatility filter failed: current_vol={current_vol:.6f}, threshold={self.p.volatility_threshold}")
                    if not signals['regime_filter']:
                        self.logger.info(f"  Regime filter failed: regime={self.current_regime}")
                
        else:  # In position
            if self.next_call_count <= 10 or self.next_call_count % 100 == 0:
                self.logger.info(f"=== POSITION MANAGEMENT ===")
                self.logger.info(f"Current position size: {self.position.size}")
                self.logger.info(f"Entry price: {self.buyprice}")
                self.logger.info(f"Current P&L: {(current_price - self.buyprice) * self.position.size if self.buyprice else 0:.2f}")
            
            self._manage_position_advanced(current_vol, signals)

    def _manage_position_advanced(self, volatility: float, signals: Dict[str, Any]):
        """Enhanced position management with advanced profit optimization"""
        current_price = self.dataclose[0]
        
        if self.position.size > 0:  # Long position
            # Enhanced dynamic stop loss with trailing
            base_stop_distance = max(self.p.base_stop_loss, volatility * 1.8)
            stop_price = self.buyprice * (1 - base_stop_distance)
            
            # Enhanced dynamic take profit with multiple targets
            target_distance = base_stop_distance * 3.0  # Better risk/reward ratio
            target_price = self.buyprice * (1 + target_distance)
            
            # Implement trailing stop logic
            if not hasattr(self, 'highest_price_long'):
                self.highest_price_long = current_price
            else:
                self.highest_price_long = max(self.highest_price_long, current_price)
            
            # Calculate trailing stop
            trailing_distance = base_stop_distance * 0.6  # Tighter trailing
            trailing_stop_price = self.highest_price_long * (1 - trailing_distance)
            
            # Profit-based position scaling
            current_profit_pct = (current_price - self.buyprice) / self.buyprice
            
            # Enhanced regime-based exit adjustments
            if self.current_regime == 'bearish_trend' and self.regime_confidence > 0.6:
                # More aggressive early exit
                if current_profit_pct > 0.003:  # Even smaller profit threshold
                    self.log('REGIME EXIT (LONG) - Bearish trend detected')
                    self.close()
                    self.highest_price_long = None
                    return
            
            # Enhanced signal-based exit with lower threshold
            if signals['sell_score'] > 0.6:  # Lower threshold for more exits
                self.log('SIGNAL EXIT (LONG) - Strong sell signal')
                self.close()
                self.highest_price_long = None
                return
            
            # Enhanced exits with trailing stop
            if current_price <= stop_price:
                self.log(f'STOP LOSS (LONG) - Price: {current_price:.5f}')
                self.close()
                self.highest_price_long = None
            elif current_price >= target_price:
                self.log(f'TAKE PROFIT (LONG) - Price: {current_price:.5f}')
                self.close()
                self.highest_price_long = None
            elif current_profit_pct > 0.01 and current_price <= trailing_stop_price:
                self.log(f'TRAILING STOP (LONG) - Price: {current_price:.5f}')
                self.close()
                self.highest_price_long = None
                
        elif self.position.size < 0:  # Short position
            # Enhanced dynamic stop loss with trailing
            base_stop_distance = max(self.p.base_stop_loss, volatility * 1.8)
            stop_price = self.buyprice * (1 + base_stop_distance)
            
            # Enhanced dynamic take profit
            target_distance = base_stop_distance * 3.0
            target_price = self.buyprice * (1 - target_distance)
            
            # Implement trailing stop logic for short
            if not hasattr(self, 'lowest_price_short'):
                self.lowest_price_short = current_price
            else:
                self.lowest_price_short = min(self.lowest_price_short, current_price)
            
            # Calculate trailing stop for short
            trailing_distance = base_stop_distance * 0.6
            trailing_stop_price = self.lowest_price_short * (1 + trailing_distance)
            
            # Profit calculation for short
            current_profit_pct = (self.buyprice - current_price) / self.buyprice
            
            # Enhanced regime-based exit adjustments
            if self.current_regime == 'bullish_trend' and self.regime_confidence > 0.6:
                # More aggressive early exit
                if current_profit_pct > 0.003:
                    self.log('REGIME EXIT (SHORT) - Bullish trend detected')
                    self.close()
                    self.lowest_price_short = None
                    return
                    
            # Enhanced signal-based exit
            if signals['buy_score'] > 0.6:
                self.log('SIGNAL EXIT (SHORT) - Strong buy signal')
                self.close()
                self.lowest_price_short = None
                return
                
            # Enhanced exits with trailing stop
            if current_price >= stop_price:
                self.log(f'STOP LOSS (SHORT) - Price: {current_price:.5f}')
                self.close()
                self.lowest_price_short = None
            elif current_price <= target_price:
                self.log(f'TAKE PROFIT (SHORT) - Price: {current_price:.5f}')
                self.close()
                self.lowest_price_short = None
            elif current_profit_pct > 0.01 and current_price >= trailing_stop_price:
                self.log(f'TRAILING STOP (SHORT) - Price: {current_price:.5f}')
                self.close()
                self.lowest_price_short = None

    def notify_order(self, order):
        """Enhanced order notification with detailed logging"""
        self.logger.info(f"=== ORDER NOTIFICATION ===")
        self.logger.info(f"Order ID: {order.ref}")
        self.logger.info(f"Order status: {order.getstatusname()}")
        self.logger.info(f"Order type: {order.ordtype}")
        self.logger.info(f"Order size: {order.size}")
        self.logger.info(f"Order price: {order.price if order.price else 'Market'}")
        self.logger.info(f"Order created: {order.created}")
        self.logger.info(f"Order alive: {order.alive()}")
        
        # Log broker state
        self.logger.info(f"Broker cash: {self.broker.get_cash():.2f}")
        self.logger.info(f"Broker value: {self.broker.get_value():.2f}")
        self.logger.info(f"Current position size: {self.position.size if self.position else 0}")
        
        if order.status in [order.Submitted, order.Accepted]:
            self.logger.info(f"*** ORDER {order.getstatusname().upper()}: {order}")
            self.logger.info(f"*** Order is alive: {order.alive()}")
            self.logger.info(f"*** Waiting for execution...")
            # Don't clear order reference yet - wait for execution
            
        elif order.status in [order.Completed]:
            if order.isbuy():
                self.logger.info(f"*** BUY ORDER EXECUTED ***")
                self.logger.info(f"  Executed price: {order.executed.price:.5f}")
                self.logger.info(f"  Executed size: {order.executed.size}")
                self.logger.info(f"  Executed value: {order.executed.value:.2f}")
                self.logger.info(f"  Commission: {order.executed.comm:.2f}")
                self.logger.info(f"  Execution time: {order.executed.dt}")
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:
                self.logger.info(f"*** SELL ORDER EXECUTED ***")
                self.logger.info(f"  Executed price: {order.executed.price:.5f}")
                self.logger.info(f"  Executed size: {order.executed.size}")
                self.logger.info(f"  Executed value: {order.executed.value:.2f}")
                self.logger.info(f"  Commission: {order.executed.comm:.2f}")
                self.logger.info(f"  Execution time: {order.executed.dt}")
                
            # Log portfolio impact
            self.logger.info(f"*** POST-EXECUTION PORTFOLIO STATE ***")
            self.logger.info(f"  New broker cash: {self.broker.get_cash():.2f}")
            self.logger.info(f"  New broker value: {self.broker.get_value():.2f}")
            self.logger.info(f"  New position size: {self.position.size}")
            self.logger.info(f"  Position value: {self.position.size * order.executed.price:.2f}")
                
            self.log(f'ORDER EXECUTED - {order.getstatusname()} at {order.executed.price:.5f}')
            # Clear order reference after execution
            self.order = None
            
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.logger.error(f"*** ORDER FAILED: {order.getstatusname()} ***")
            if hasattr(order, 'info'):
                self.logger.error(f"  Order info: {order.info}")
            self.logger.error(f"  Broker cash: {self.broker.get_cash():.2f}")
            self.logger.error(f"  Broker value: {self.broker.get_value():.2f}")
            self.log(f'ORDER FAILED - {order.getstatusname()}')
            # Clear order reference on failure
            self.order = None
            
        elif order.status in [order.Partial]:
            self.logger.info(f"*** ORDER PARTIALLY FILLED ***")
            self.logger.info(f"  Partial execution price: {order.executed.price:.5f}")
            self.logger.info(f"  Partial execution size: {order.executed.size}")
            self.logger.info(f"  Remaining size: {order.size - order.executed.size}")
            # Don't clear order reference - still active
            
        else:
            self.logger.warning(f"*** UNKNOWN ORDER STATUS: {order.status} ({order.getstatusname()}) ***")
            self.logger.warning(f"  Order details: {order}")

    def log(self, txt, dt=None):
        """Enhanced logging with performance metrics"""
        if self.p.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            current_value = self.broker.get_value()
            
            # Update performance tracking
            if current_value > self.peak_value:
                self.peak_value = current_value
            else:
                drawdown = (self.peak_value - current_value) / self.peak_value
                self.max_drawdown = max(self.max_drawdown, drawdown)
                
            self.logger.info(f'{dt.isoformat()} {txt} | Value: {current_value:.2f} | DD: {self.max_drawdown:.2%}')

    def notify_trade(self, trade):
        """Enhanced trade notification with performance tracking"""
        self.logger.info(f"=== TRADE NOTIFICATION ===")
        self.logger.info(f"Trade status: {'CLOSED' if trade.isclosed else 'OPEN'}")
        self.logger.info(f"Trade size: {trade.size}")
        self.logger.info(f"Entry price: {trade.price:.5f}")
        
        if trade.isclosed:
            self.logger.info(f"Exit price: {trade.price:.5f}")
            self.logger.info(f"Trade P&L: {trade.pnl:.2f}")
            self.logger.info(f"Trade P&L Net: {trade.pnlcomm:.2f}")
            
            self.trade_count += 1
            self.total_pnl += trade.pnl
            
            if trade.pnl > 0:
                self.winning_trades += 1
                self.logger.info("WINNING TRADE")
            else:
                self.logger.info("LOSING TRADE")
                
            # Calculate performance metrics
            win_rate = (self.winning_trades / self.trade_count) * 100 if self.trade_count > 0 else 0
            avg_pnl = self.total_pnl / self.trade_count if self.trade_count > 0 else 0
            
            self.logger.info(f"Updated performance:")
            self.logger.info(f"  Total trades: {self.trade_count}")
            self.logger.info(f"  Winning trades: {self.winning_trades}")
            self.logger.info(f"  Win rate: {win_rate:.1f}%")
            self.logger.info(f"  Average P&L: {avg_pnl:.2f}")
            self.logger.info(f"  Total P&L: {self.total_pnl:.2f}")
            
            self.log(f'TRADE CLOSED - PnL: {trade.pnl:.2f} | Win Rate: {win_rate:.1f}% | Avg PnL: {avg_pnl:.2f}')
        else:
            self.logger.info("Trade opened but not yet closed")

if __name__ == '__main__':
    print("Enhanced Forex Strategy with Advanced Quantitative Features loaded successfully")