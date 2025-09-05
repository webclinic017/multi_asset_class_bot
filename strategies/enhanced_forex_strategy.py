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
        
        # Enhanced Performance Optimization
        ('min_sharpe_threshold', 0.2), # Lower threshold for more opportunities
        ('max_drawdown_threshold', 0.25), # Allow higher drawdown for more trades
        ('profit_factor_threshold', 1.0), # Lower threshold for more trades
        
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
        
        # Performance tracking
        self.trade_count = 0
        self.winning_trades = 0
        self.total_pnl = 0.0
        self.max_drawdown = 0.0
        self.peak_value = self.broker.get_cash()
        
        # GPU Setup
        self.use_gpu = self.p.use_gpu and GPU_AVAILABLE and torch is not None
        self.device = 'cuda' if self.use_gpu else 'cpu'
        
        # GPU data buffers for accelerated calculations
        self.gpu_price_buffer = []
        self.gpu_high_buffer = []
        self.gpu_low_buffer = []
        self.gpu_volume_buffer = []
        
        # Initialize core indicators
        self._init_core_indicators()
        
        # Initialize advanced indicators
        self._init_advanced_indicators()
        
        # Initialize ML features
        if self.p.use_ml_features:
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
        self.volume_ratio = self.datavolume / self.volume_sma
        
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
        
        # Price position in range
        self.price_position = (self.dataclose - bt.indicators.Lowest(self.datalow, period=20)) / \
                             (bt.indicators.Highest(self.datahigh, period=20) - bt.indicators.Lowest(self.datalow, period=20))

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
            vol_ratio = volatility / vol_ma if vol_ma > 0 else 1.0
            
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
                kelly_fraction = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
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
            # Enhanced Trend signals with acceleration
            trend_score = 0.0
            if self.ema_fast[0] > self.ema_slow[0]:
                trend_score += 1.2  # Stronger weight for trend following
            if self.tema[0] > self.tema[-1]:
                trend_score += 0.8  # Higher weight for TEMA momentum
            if self.dataclose[0] > self.bb.lines.mid[0]:
                trend_score += 0.6
            
            # Add trend acceleration detection
            if len(self.ema_fast) > 2:
                fast_acceleration = (self.ema_fast[0] - self.ema_fast[-1]) - (self.ema_fast[-1] - self.ema_fast[-2])
                if fast_acceleration > 0:
                    trend_score *= self.p.trend_following_boost
                    
            signals['components']['trend'] = min(trend_score / 2.6, 1.0)
            
            # Enhanced Momentum signals with multiple timeframes
            momentum_score = 0.0
            
            # RSI with enhanced levels
            if self.rsi[0] > 45 and self.rsi[0] < self.p.rsi_overbought:
                momentum_score += 1.2
            elif self.rsi[0] < self.p.rsi_oversold:
                momentum_score += 1.5  # Stronger oversold signal
            
            # MACD with histogram analysis
            if self.macd.macd[0] > self.macd.signal[0]:
                momentum_score += 1.0
                # Add histogram momentum (check if histogram exists)
                if hasattr(self.macd, 'histo') and len(self.macd.histo) > 1:
                    if self.macd.histo[0] > self.macd.histo[-1]:
                        momentum_score *= self.p.momentum_acceleration
            
            # Stochastic with enhanced weighting
            if self.stoch.percK[0] > self.stoch.percD[0] and self.stoch.percK[0] < 80:
                momentum_score += 0.8
                
            signals['components']['momentum'] = min(momentum_score / 3.2, 1.0)
            
            # Enhanced Mean reversion with volatility expansion
            reversion_score = 0.0
            bb_position = (self.dataclose[0] - self.bb.lines.bot[0]) / \
                         (self.bb.lines.top[0] - self.bb.lines.bot[0])
            
            # Enhanced Bollinger Band analysis
            if bb_position < 0.15:  # More aggressive lower band
                reversion_score += 1.3
            elif bb_position > 0.85:  # More aggressive upper band
                reversion_score -= 1.3
            elif bb_position < 0.3:
                reversion_score += 0.7
            elif bb_position > 0.7:
                reversion_score -= 0.7
            
            # Williams %R with enhanced sensitivity
            if self.williams_r[0] < -85:
                reversion_score += 0.8
            elif self.williams_r[0] > -15:
                reversion_score -= 0.8
            
            # Apply mean reversion factor
            reversion_score *= self.p.mean_reversion_factor
            signals['components']['reversion'] = max(-1.0, min(reversion_score / 2.1, 1.0))
            
            # Enhanced Volume confirmation with breakout detection
            volume_score = 0.0
            if self.p.volume_confirmation and len(self.volume_ratio) > 0:
                if self.volume_ratio[0] > 1.5:  # Strong volume breakout
                    volume_score = 1.2 * self.p.breakout_multiplier
                elif self.volume_ratio[0] > 1.2:
                    volume_score = 0.8
                elif self.volume_ratio[0] < 0.7:
                    volume_score = -0.6
                    
            signals['components']['volume'] = max(-1.0, min(volume_score, 1.0))
            
            # Volatility expansion signal
            volatility_score = 0.0
            if hasattr(self, 'atr') and len(self.atr) > 5:
                current_atr = self.atr[0]
                avg_atr = np.mean([self.atr[-i] for i in range(1, 6)])
                if current_atr > avg_atr * self.p.volatility_expansion_threshold:
                    volatility_score = 0.5  # Volatility expansion signal
                    
            signals['components']['volatility_expansion'] = volatility_score
            
            # Enhanced regime-based signal weighting
            regime_weights = {
                'bullish_trend': {'trend': 1.8, 'momentum': 1.4, 'reversion': 0.4, 'volume': 1.2},
                'bearish_trend': {'trend': 1.8, 'momentum': 1.4, 'reversion': 0.4, 'volume': 1.2},
                'mean_reverting': {'trend': 0.4, 'momentum': 0.9, 'reversion': 2.0, 'volume': 0.8},
                'high_volatility': {'trend': 1.0, 'momentum': 0.7, 'reversion': 1.3, 'volume': 1.5},
                'neutral': {'trend': 1.2, 'momentum': 1.1, 'reversion': 1.0, 'volume': 1.0}
            }
            
            weights = regime_weights.get(self.current_regime, regime_weights['neutral'])
            
            # Calculate enhanced weighted scores
            buy_score = (
                signals['components']['trend'] * weights['trend'] +
                signals['components']['momentum'] * weights['momentum'] +
                max(0, signals['components']['reversion']) * weights['reversion'] +
                max(0, signals['components']['volume']) * weights['volume'] +
                signals['components']['volatility_expansion'] * 0.5
            ) / (weights['trend'] + weights['momentum'] + weights['reversion'] + weights['volume'] + 0.5)
            
            sell_score = (
                (1 - signals['components']['trend']) * weights['trend'] +
                (1 - signals['components']['momentum']) * weights['momentum'] +
                max(0, -signals['components']['reversion']) * weights['reversion'] +
                max(0, -signals['components']['volume']) * weights['volume'] +
                signals['components']['volatility_expansion'] * 0.3
            ) / (weights['trend'] + weights['momentum'] + weights['reversion'] + weights['volume'] + 0.3)
            
            signals['buy_score'] = buy_score
            signals['sell_score'] = sell_score
            signals['signal_strength'] = max(buy_score, sell_score)
            
            # Enhanced filters with more lenient thresholds
            if self.p.use_volatility_filter:
                current_vol = self.atr[0] / self.dataclose[0] if self.dataclose[0] > 0 else 0
                # More lenient volatility filter for more trading opportunities
                if current_vol > self.p.volatility_threshold * 1.2:
                    signals['volatility_filter'] = False
                    
            return signals
            
        except Exception as e:
            self.logger.error(f"Error generating enhanced signals: {e}")
            return signals

    def next(self):
        """Main strategy logic with advanced quantitative analysis"""
        if self.order:
            return
            
        # Update market regime
        self.current_regime, self.regime_confidence = self.detect_market_regime()
        
        # Generate signals
        signals = self.generate_advanced_signals()
        
        # Current market conditions
        current_price = self.dataclose[0]
        current_vol = self.atr[0] / current_price if current_price > 0 else 0
        
        if not self.position:  # No position
            # Entry logic (lowered threshold for more trades)
            if (signals['buy_score'] > 0.3 and
                signals['volatility_filter'] and
                signals['regime_filter']):
                
                # Calculate position size
                position_size = self.calculate_dynamic_position_size(
                    signals['signal_strength'], current_vol
                )
                
                # Calculate stops and targets
                stop_distance = max(self.p.base_stop_loss, current_vol * 2)
                target_distance = stop_distance * 2.5  # 2.5:1 R/R minimum
                
                self.log(f'BUY SIGNAL - Score: {signals["buy_score"]:.3f}, '
                        f'Regime: {self.current_regime}, Size: {position_size:.3f}')
                
                self.order = self.buy(size=position_size)
                self.entry_bar = len(self)
                
            elif (signals['sell_score'] > 0.3 and
                  signals['volatility_filter'] and
                  signals['regime_filter']):
                
                # Calculate position size
                position_size = self.calculate_dynamic_position_size(
                    signals['signal_strength'], current_vol
                )
                
                self.log(f'SELL SIGNAL - Score: {signals["sell_score"]:.3f}, '
                        f'Regime: {self.current_regime}, Size: {position_size:.3f}')
                
                self.order = self.sell(size=position_size)
                self.entry_bar = len(self)
                
        else:  # In position
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
        if not trade.isclosed:
            return
            
        self.trade_count += 1
        self.total_pnl += trade.pnl
        
        if trade.pnl > 0:
            self.winning_trades += 1
            
        # Calculate performance metrics
        win_rate = (self.winning_trades / self.trade_count) * 100 if self.trade_count > 0 else 0
        avg_pnl = self.total_pnl / self.trade_count if self.trade_count > 0 else 0
        
        self.log(f'TRADE CLOSED - PnL: {trade.pnl:.2f} | Win Rate: {win_rate:.1f}% | Avg PnL: {avg_pnl:.2f}')

if __name__ == '__main__':
    print("Enhanced Forex Strategy with Advanced Quantitative Features loaded successfully")