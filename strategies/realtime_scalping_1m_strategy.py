
"""
Real-time Scalping Strategy for 1-minute timeframe
Compatible with real-time broker logic like EnhancedForexStrategy
Optimized for ultra-fast scalping with immediate execution
"""

import backtrader as bt
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Tuple
from scipy import stats
from sklearn.preprocessing import StandardScaler

# GPU acceleration imports
try:
    import torch
    GPU_AVAILABLE = torch.cuda.is_available()
    if GPU_AVAILABLE:
        print(f"GPU Available for 1M Scalping Strategy: {torch.cuda.get_device_name(0)}")
except ImportError:
    GPU_AVAILABLE = False
    torch = None

class RealtimeScalping1MStrategy(bt.Strategy):
    """
    Real-time compatible 1-minute scalping strategy with enhanced broker integration
    Uses the same parameter structure as EnhancedForexStrategy for compatibility
    """
    
    params = (
        # Core Moving Average Parameters (compatible with EnhancedForexStrategy)
        ('fast_length', 5),           # Ultra-fast EMA for 1M scalping
        ('slow_length', 13),          # Fibonacci-based slow EMA
        ('signal_length', 3),         # Ultra-fast signal line
        
        # Enhanced RSI Parameters
        ('rsi_period', 7),            # Fast RSI for scalping
        ('rsi_oversold', 25),         # Scalping oversold level
        ('rsi_overbought', 75),       # Scalping overbought level
        ('rsi_divergence_lookback', 10), # Shorter lookback for 1M
        
        # MACD Parameters
        ('macd_fast', 5),             # Ultra-fast MACD for 1M
        ('macd_slow', 13),            # Fast slow line
        ('macd_signal', 3),           # Very fast signal
        
        # Bollinger Bands for Scalping
        ('bb_period', 10),            # Short period for quick reactions
        ('bb_std', 1.5),              # Tighter bands for scalping
        ('bb_squeeze_threshold', 0.05), # Tight squeeze detection
        
        # Volatility and ATR
        ('atr_period', 7),            # Fast ATR for scalping
        ('volatility_lookback', 20),  # Short lookback
        ('volatility_threshold', 0.008), # Volatility threshold
        
        # Risk Management (compatible with enhanced strategy)
        ('base_stop_loss', 0.003),    # Very tight stop loss for 1M (0.3%)
        ('base_take_profit', 0.009),  # 3:1 risk/reward ratio
        ('dynamic_sizing', True),     # Enable dynamic position sizing
        ('max_risk_per_trade', 0.015), # 1.5% risk per trade
        ('volatility_adjustment', True), # Adjust for volatility
        ('stop_loss_percent', 0.003), # Tight stop loss
        ('take_profit_percent', 0.009), # Take profit
        ('trailing_stop_percent', 0.002), # Tight trailing stop
        ('position_size_percent', 0.02), # 2% position size
        ('max_position_size', 0.05),  # Maximum position size
        ('min_volatility', 0.00005),  # Minimum volatility
        ('max_volatility', 0.01),     # Maximum volatility
        ('trend_strength_threshold', 0.3), # Lower threshold for more trades
        
        # Regime Detection (adapted for 1M)
        ('regime_lookback', 50),      # Shorter lookback for 1M
        ('trend_threshold', 0.4),     # Lower threshold for trend detection
        ('mean_reversion_threshold', 0.3), # Lower threshold for mean reversion
        
        # Supply/Demand (adapted for 1M)
        ('pivot_period', 3),          # Very fast pivot detection for 1M
        ('zone_lookback', 30),        # Shorter zone lookback
        ('min_zone_strength', 2),     # Lower minimum strength
        ('zone_buffer', 0.0001),      # Tighter zone buffer for 1M
        ('max_zones', 15),            # More zones for better coverage
        
        # Volume Analysis
        ('volume_period', 15),        # Shorter volume period for 1M
        ('volume_levels', 25),        # More volume levels
        ('volume_confirmation', True), # Keep volume confirmation
        
        # Multi-timeframe (disabled for pure 1M scalping)
        ('use_higher_tf', False),
        ('higher_tf_multiplier', 5),  # 5M for higher timeframe
        
        # Machine Learning Features
        ('use_ml_features', True),
        ('feature_lookback', 25),     # Shorter feature lookback for 1M
        ('momentum_periods', [2, 5, 8, 13]), # Fibonacci-based periods for 1M
        
        # Filters
        ('use_regime_filter', True),
        ('use_volatility_filter', True),
        ('use_correlation_filter', False),
        ('use_momentum_filter', True),
        
        # Performance Optimization for 1M data
        ('min_sharpe_threshold', 0.05), # Very low threshold for 1M data
        ('max_drawdown_threshold', 0.4), # Allow higher drawdown for 1M data
        ('profit_factor_threshold', 0.6), # Lower threshold for more trades
        
        # Sentiment Integration (reduced weight for scalping)
        ('sentiment_weight', 0.2),    # Lower sentiment weight for scalping
        ('sentiment_threshold', 0.3), # Lower threshold
        ('news_impact_decay', 0.95),  # Faster decay for scalping
        
        # Advanced Scalping Features
        ('momentum_acceleration', 1.6), # Higher acceleration for 1M
        ('trend_following_boost', 1.4), # Trend following boost
        ('breakout_multiplier', 1.8),   # Higher breakout multiplier for 1M
        ('mean_reversion_factor', 0.7), # Mean reversion strength
        ('volatility_expansion_threshold', 1.3), # Volatility expansion detection
        
        # Scalping-specific parameters
        ('scalping_mode', True),      # Enable scalping mode
        ('max_trades_per_hour', 15),  # Higher trade frequency for 1M
        ('min_time_between_trades', 30), # 30 seconds minimum between trades
        ('quick_exit_threshold', 0.002), # Quick exit at 0.2% profit
        ('momentum_exit_threshold', 0.001), # Exit on momentum loss
        
        # GPU Acceleration
        ('use_gpu', True),            # Enable GPU acceleration
        ('gpu_batch_size', 32),       # GPU batch processing size
        ('gpu_lookback', 100),        # GPU data buffer size
        
        # Logging
        ('printlog', False)
    )

    def __init__(self):
        """Initialize 1M scalping strategy with real-time broker compatibility"""
        self.logger = logging.getLogger(__name__)
        
        # === COMPREHENSIVE INITIALIZATION LOGGING ===
        self.logger.info("=== REALTIME 1M SCALPING STRATEGY INITIALIZATION ===")
        self.logger.info(f"Strategy parameters received: {dict(self.params._getitems())}")
        
        # Initialize portfolio value tracker for accurate portfolio tracking
        from execution.portfolio_value_tracker import get_portfolio_tracker
        self.portfolio_tracker = get_portfolio_tracker(10000.0)
        self.logger.info("Portfolio value tracker initialized")
        
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
        
        # Scalping-specific tracking
        self.last_trade_time = None
        self.trades_this_hour = 0
        self.last_hour = None
        self.quick_exits = 0
        self.momentum_exits = 0
        
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
        self.logger.info(f"Realtime 1M Scalping Strategy initialized {gpu_status}")
        if self.use_gpu:
            self.logger.info(f"GPU Device: {torch.cuda.get_device_name(0)}")
        
        self.logger.info("=== 1M SCALPING STRATEGY INITIALIZATION COMPLETE ===")

    def _init_core_indicators(self):
        """Initialize core technical indicators for 1M scalping"""
        # Ultra-fast EMAs for scalping
        self.ema_fast = bt.indicators.EMA(period=self.p.fast_length)
        self.ema_slow = bt.indicators.EMA(period=self.p.slow_length)
        self.sma_signal = bt.indicators.SMA(period=self.p.signal_length)
        
        # Triple EMA for trend strength
        self.tema = bt.indicators.TEMA(period=self.p.fast_length)
        
        # RSI with divergence detection
        self.rsi = bt.indicators.RSI(period=self.p.rsi_period)
        self.rsi_ema = bt.indicators.EMA(self.rsi, period=3)
        
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
        """Initialize advanced quantitative indicators for 1M scalping"""
        # Stochastic for momentum
        self.stoch = bt.indicators.Stochastic(period=5, period_dfast=3)
        
        # Williams %R
        self.williams_r = bt.indicators.WilliamsR(period=10)
        
        # Commodity Channel Index
        self.cci = bt.indicators.CommodityChannelIndex(period=15)
        
        # Average Directional Index
        self.adx = bt.indicators.ADX(period=10)
        
        # Volume indicators
        self.volume_sma = bt.indicators.SMA(self.datavolume, period=self.p.volume_period)
        # Safe volume ratio calculation
        self.volume_ratio = self.datavolume / bt.indicators.Max(self.volume_sma, 1e-8)
        
    def _init_ml_features(self):
        """Initialize machine learning features for 1M scalping"""
        # Momentum features
        self.momentum_features = {}
        for period in self.p.momentum_periods:
            self.momentum_features[f'mom_{period}'] = bt.indicators.Momentum(period=period)
            
        # Rate of change features
        self.roc_3 = bt.indicators.RateOfChange(period=3)
        self.roc_5 = bt.indicators.RateOfChange(period=5)
        self.roc_8 = bt.indicators.RateOfChange(period=8)
        
        # Price position in range
        self.highest_10 = bt.indicators.Highest(self.datahigh, period=10)
        self.lowest_10 = bt.indicators.Lowest(self.datalow, period=10)

    def detect_market_regime(self) -> Tuple[str, float]:
        """Detect current market regime for 1M scalping"""
        current_data_length = len(self.data)
        
        # Use available data, but with minimum requirements for 1M
        min_regime_data = 15  # Minimum for basic regime detection on 1M
        if current_data_length < min_regime_data:
            return 'neutral', 0.0
            
        try:
            # Use available data up to regime_lookback
            lookback_period = min(current_data_length - 1, self.p.regime_lookback)
            lookback_period = max(lookback_period, min_regime_data)
            
            # Get recent price data
            recent_closes = np.array([self.dataclose[-i] for i in range(lookback_period, 0, -1)])
            recent_returns = np.diff(np.log(recent_closes))
            
            # Trend detection using linear regression
            x = np.arange(len(recent_closes))
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, recent_closes)
            
            # Volatility clustering detection (adapted for 1M)
            volatility = np.std(recent_returns) * np.sqrt(1440)  # Annualized for 1M data
            
            # Adaptive volatility calculation
            vol_window = min(8, len(recent_returns) // 2)
            if vol_window >= 3:
                vol_segments = [np.std(recent_returns[i:i+vol_window])
                               for i in range(0, len(recent_returns)-vol_window+1, max(1, vol_window//2))]
                vol_ma = np.mean(vol_segments) if vol_segments else volatility
            else:
                vol_ma = volatility
                
            vol_ratio = volatility / max(vol_ma, 1e-8) if vol_ma > 0 else 1.0
            
            # Regime classification with confidence adjustment
            trend_strength = abs(r_value)
            data_confidence_factor = min(1.0, lookback_period / self.p.regime_lookback)
            
            if trend_strength > self.p.trend_threshold and slope > 0:
                regime = 'bullish_trend'
                confidence = min(trend_strength * data_confidence_factor, 0.95)
            elif trend_strength > self.p.trend_threshold and slope < 0:
                regime = 'bearish_trend'
                confidence = min(trend_strength * data_confidence_factor, 0.95)
            elif vol_ratio > 1.8:  # Higher threshold for 1M
                regime = 'high_volatility'
                confidence = min((vol_ratio / 2.5) * data_confidence_factor, 0.9)
            elif trend_strength < self.p.mean_reversion_threshold:
                regime = 'mean_reverting'
                confidence = min((self.p.mean_reversion_threshold - trend_strength) * 2 * data_confidence_factor, 0.8)
            else:
                regime = 'neutral'
                confidence = 0.3 * data_confidence_factor
                
            return regime, confidence
            
        except Exception as e:
            self.logger.error(f"Error in regime detection: {e}")
            return 'neutral', 0.0

    def calculate_dynamic_position_size(self, signal_strength: float, volatility: float) -> float:
        """Calculate position size for 1M scalping with enhanced risk management"""
        if not self.p.dynamic_sizing:
            return 0.01  # Small default size for scalping
            
        try:
            # Base Kelly Criterion calculation
            win_rate = self.winning_trades / max(self.trade_count, 1)
            avg_win = 0.008  # Estimated average win for 1M scalping
            avg_loss = 0.003  # Estimated average loss for 1M scalping
            
            if win_rate > 0 and avg_loss > 0:
                kelly_fraction = (win_rate * avg_win - (1 - win_rate) * avg_loss) / max(avg_win, 1e-8)
                kelly_fraction = max(0, min(kelly_fraction, 0.15))  # Cap at 15% for scalping
            else:
                kelly_fraction = 0.01  # Default 1% for scalping
                
            # Adjust for signal strength
            signal_adjustment = signal_strength * 1.2
            
            # Adjust for volatility (more conservative in high vol)
            vol_adjustment = 1.0 / (1.0 + volatility * 15)
            
            # Adjust for regime
            regime_adjustment = 1.0
            if self.current_regime == 'high_volatility':
                regime_adjustment = 0.4  # Very conservative in high vol
            elif self.current_regime in ['bullish_trend', 'bearish_trend']:
                regime_adjustment = 1.3
                
            final_size = kelly_fraction * signal_adjustment * vol_adjustment * regime_adjustment
            
            # Ensure within risk limits for scalping
            max_size = self.p.max_risk_per_trade / max(volatility, 0.002)
            final_size = min(final_size, max_size)
            
            return max(final_size, 0.005)  # Minimum 0.5%
            
        except Exception as e:
            self.logger.error(f"Error calculating position size: {e}")
            return 0.01

    def generate_scalping_signals(self) -> Dict[str, Any]:
        """Generate ultra-fast scalping signals for 1M timeframe"""
        signals = {
            'buy_score': 0.0,
            'sell_score': 0.0,
            'signal_strength': 0.0,
            'regime_filter': True,
            'volatility_filter': True,
            'components': {}
        }
        
        try:
            self.logger.info("=== 1M SCALPING SIGNAL GENERATION ===")
            
            # Current values
            current_price = self.dataclose[0]
            current_rsi = self.rsi[0]
            current_atr = self.atr[0]
            
            # Ultra-fast trend signals
            trend_score = 0.0
            ema_condition = self.ema_fast[0] > self.ema_slow[0]
            if ema_condition:
                trend_score += 1.5  # Higher weight for scalping
            
            tema_condition = self.tema[0] > self.tema[-1] if len(self.tema) > 1 else False
            if tema_condition:
                trend_score += 1.0
            
            bb_condition = current_price > self.bb.lines.mid[0]
            if bb_condition:
                trend_score += 0.8
            
            # Add momentum acceleration for 1M
            if len(self.ema_fast) > 2:
                fast_acceleration = (self.ema_fast[0] - self.ema_fast[-1]) - (self.ema_fast[-1] - self.ema_fast[-2])
                if fast_acceleration > 0:
                    trend_score *= self.p.trend_following_boost
                    
            trend_component = min(trend_score / 3.3, 1.0)
            signals['components']['trend'] = trend_component
            
            # Ultra-fast momentum signals
            momentum_score = 0.0
            
            # RSI with tighter ranges for scalping
            rsi_condition1 = 40 < current_rsi < self.p.rsi_overbought
            rsi_condition2 = current_rsi < self.p.rsi_oversold
            
            if rsi_condition1:
                momentum_score += 1.4
            elif rsi_condition2:
                momentum_score += 1.8  # Higher weight for oversold in scalping
            
            # MACD with histogram analysis
            macd_condition = self.macd.macd[0] > self.macd.signal[0]
            if macd_condition:
                momentum_score += 1.2
                
                # Add histogram momentum
                if hasattr(self.macd, 'histo') and len(self.macd.histo) > 1:
                    histo_condition = self.macd.histo[0] > self.macd.histo[-1]
                    if histo_condition:
                        momentum_score *= self.p.momentum_acceleration
            
            # Stochastic with enhanced weighting for scalping
            stoch_condition = self.stoch.percK[0] > self.stoch.percD[0] and self.stoch.percK[0] < 75
            if stoch_condition:
                momentum_score += 1.0
                
            momentum_component = min(momentum_score / 4.2, 1.0)
            signals['components']['momentum'] = momentum_component
            
            # Mean reversion with volatility expansion for scalping
            reversion_score = 0.0
            bb_position = (current_price - self.bb.lines.bot[0]) / \
                         (self.bb.lines.top[0] - self.bb.lines.bot[0])
            
            # More aggressive BB analysis for scalping
            if bb_position < 0.1:  # Very aggressive lower band
                reversion_score += 1.5
            elif bb_position > 0.9:  # Very aggressive upper band
                reversion_score -= 1.5
            elif bb_position < 0.25:
                reversion_score += 0.8
            elif bb_position > 0.75:
                reversion_score -= 0.8
            
            # Williams %R with enhanced sensitivity for scalping
            williams_low = self.williams_r[0] < -80
            williams_high = self.williams_r[0] > -20
            
            if williams_low:
                reversion_score += 1.0
            elif williams_high:
                reversion_score -= 1.0
            
            # Apply mean reversion factor
            reversion_score *= self.p.mean_reversion_factor
            reversion_component = max(-1.0, min(reversion_score / 2.5, 1.0))
            signals['components']['reversion'] = reversion_component
            
            # Volume confirmation with breakout detection for scalping
            volume_score = 0.0
            if self.p.volume_confirmation and len(self.volume_ratio) > 0:
                volume_ratio_val = self.volume_ratio[0]
                
                if volume_ratio_val > 2.0:  # Very strong volume breakout for 1M
                    volume_score = 1.5 * self.p.breakout_multiplier
                elif volume_ratio_val > 1.5:
                    volume_score = 1.0
                elif volume_ratio_val < 0.6:
                    volume_score = -0.8
                    
            volume_component = max(-1.0, min(volume_score, 1.0))
            signals['components']['volume'] = volume_component
            
            # Volatility expansion signal for scalping
            volatility_score = 0.0
            if hasattr(self, 'atr') and len(self.atr) > 3:
                current_atr = self.atr[0]
                avg_atr = np.mean([self.atr[-i] for i in range(1, 4)])
                expansion_threshold = avg_atr * self.p.volatility_expansion_threshold
                
                if current_atr > expansion_threshold:
                    volatility_score = 0.6  # Volatility expansion signal
                    
            signals['components']['volatility_expansion'] = volatility_score
            
            # Enhanced regime-based signal weighting for scalping
            regime_weights = {
                'bullish_trend': {'trend': 2.0, 'momentum': 1.6, 'reversion': 0.3, 'volume': 1.4},
                'bearish_trend': {'trend': 2.0, 'momentum': 1.6, 'reversion': 0.3, 'volume': 1.4},
                'mean_reverting': {'trend': 0.3, 'momentum': 0.8, 'reversion': 2.2, 'volume': 0.9},
                'high_volatility': {'trend': 1.2, 'momentum': 0.6, 'reversion': 1.5, 'volume': 1.8},
                'neutral': {'trend': 1.4, 'momentum': 1.2, 'reversion': 1.1, 'volume': 1.1}
            }
            
            weights = regime_weights.get(self.current_regime, regime_weights['neutral'])
            
            # Calculate enhanced weighted scores
            buy_numerator = (
                signals['components']['trend'] * weights['trend'] +
                signals['components']['momentum'] * weights['momentum'] +
                max(0, signals['components']['reversion']) * weights['reversion'] +
                max(0, signals['components']['volume']) * weights['volume'] +
                signals['components']['volatility_expansion'] * 0.6
            )
            buy_denominator = (weights['trend'] + weights['momentum'] + weights['reversion'] + weights['volume'] + 0.6)
            buy_score = buy_numerator / buy_denominator
            
            sell_numerator = (
                (1 - signals['components']['trend']) * weights['trend'] +
                (1 - signals['components']['momentum']) * weights['momentum'] +
                max(0, -signals['components']['reversion']) * weights['reversion'] +
                max(0, -signals['components']['volume']) * weights['volume'] +
                signals['components']['volatility_expansion'] * 0.4
            )
            sell_denominator = (weights['trend'] + weights['momentum'] + weights['reversion'] + weights['volume'] + 0.4)
            sell_score = sell_numerator / sell_denominator
            
            signals['buy_score'] = buy_score
            signals['sell_score'] = sell_score
            signals['signal_strength'] = max(buy_score, sell_score)
            
            # Enhanced filters for 1M scalping
            if self.p.use_volatility_filter:
                current_vol = current_atr / current_price if current_price > 0 else 0
                vol_threshold = self.p.volatility_threshold * 2.0  # More lenient for 1M
                vol_filter_pass = current_vol <= vol_threshold
                
                if not vol_filter_pass:
                    signals['volatility_filter'] = False
                    
            return signals
            
        except Exception as e:
            import traceback
            self.logger.error(f"Error generating scalping signals: {str(e)}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return signals

    def check_scalping_filters(self) -> bool:
        """Check scalping-specific filters"""
        try:
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
            self.logger.error(f"Error in scalping filters: {e}")
            return False

    def next(self):
        """Main 1M scalping logic with real-time broker compatibility"""
        self.next_call_count += 1
        
        if self.order:
            return
        
        # Check scalping filters
        if not self.check_scalping_filters():
            return
        
        # Data availability check (progressive for 1M)
        basic_min_data = max(self.p.slow_length, self.p.bb_period, self.p.atr_period)
        current_data_length = len(self.data)
        
        if current_data_length < basic_min_data:
            return
        
        # Update market regime
        self.current_regime, self.regime_confidence = self.detect_market_regime()
        
        # Generate signals
        self.signal_generation_count += 1
        signals = self.generate_scalping_signals()
        
        # Current market conditions
        current_price = self.dataclose[0]
        current_vol = self.atr[0] / current_price if current_price > 0 else 0
        
        if not self.position:  # No position
            # Check buy conditions (lower threshold for 1M scalping)
            buy_score_ok = signals['buy_score'] > 0.12
            buy_vol_filter_ok = signals['volatility_filter']
            buy_regime_filter_ok = signals['regime_filter']
            
            # Check sell conditions
