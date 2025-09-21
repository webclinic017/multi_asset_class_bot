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
from typing import Dict, Any, Optional, Tuple, List

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
from indicators.price_action_analyzer import PriceActionAnalyzer

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
        # Initial Capital Parameter
        ('initial_capital', 100000.0),  # Explicit initial capital parameter

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
        
        # Aggressive Risk Management for Maximum Returns
        ('base_stop_loss', 0.025),     # Aggressive 2.5% stop loss for higher returns
        ('base_take_profit', 0.08),    # Aggressive 8% take profit (3.2:1 ratio)
        ('dynamic_sizing', True),      # Enable dynamic position sizing
        ('max_risk_per_trade', 0.05),  # Higher risk per trade for maximum returns
        ('volatility_adjustment', True), # Adjust for volatility
        ('stop_loss_percent', 0.025),  # Aggressive stop loss
        ('take_profit_percent', 0.08), # Aggressive take profit
        ('trailing_stop_percent', 0.015), # Looser trailing stop for profit capture
        ('position_size_percent', 0.03), # 3% per trade for 2-3% daily target
        ('max_position_size', 0.15),   # Higher maximum position size
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
        
        # Aggressive Filters for Maximum Trade Frequency
        ('use_regime_filter', True),      # Keep regime filter for trend alignment
        ('use_volatility_filter', False), # Disable for more trades in all conditions
        ('use_correlation_filter', False), # Disable for more trades
        ('use_momentum_filter', False),   # Disable for higher frequency
        
        # Maximum Returns Performance Optimization
        ('min_sharpe_threshold', -0.5), # Much lower threshold for maximum returns focus
        ('max_drawdown_threshold', 0.25), # Allow 25% drawdown for higher returns
        ('profit_factor_threshold', 0.5), # Lower threshold for more aggressive trading
        
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
        
        # Hybrid Signal Parameters
        ('signal_strength_threshold', 0.15),  # Minimum signal strength for entry
        ('high_confidence_threshold', 0.7),   # High confidence threshold
        ('price_action_weight', 0.6),         # Price action weight in hybrid system
        ('technical_weight', 0.4),            # Technical indicator weight
        
        # High-Frequency Trading Parameters for Maximum Returns
        ('max_trades_per_hour', 20),          # Increased trades per hour for higher returns
        ('min_time_between_trades', 180),     # Reduced time between trades (3 minutes)
        ('quick_exit_threshold', 0.01),      # Higher quick exit threshold for faster profits
        
        # Logging
        ('printlog', False)
    )

    def __init__(self):
        """Initialize enhanced strategy with hybrid price action + technical indicator system"""
        self.logger = logging.getLogger(__name__)
        
        # === COMPREHENSIVE INITIALIZATION LOGGING ===
        self.logger.info("=== ENHANCED FOREX STRATEGY INITIALIZATION (HYBRID SYSTEM) ===")
        self.logger.info(f"Strategy parameters received: {dict(self.params._getitems())}")
        
        # Initialize portfolio value tracker for accurate portfolio tracking
        from execution.portfolio_value_tracker import PortfolioValueTracker
        # Use the same initial capital as the strategy parameter
        self.portfolio_tracker = PortfolioValueTracker(self.p.initial_capital)
        self.logger.info(f"Portfolio value tracker initialized with ${self.portfolio_tracker.initial_capital:,.2f}")
        
        # Basic price data
        self.dataclose = self.datas[0].close
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low
        self.datavolume = self.datas[0].volume
        
        self.logger.info(f"Data feeds initialized: close={type(self.dataclose)}, high={type(self.datahigh)}, low={type(self.datalow)}, volume={type(self.datavolume)}")
        
        # Initialize Price Action Analyzer (60% weight)
        self.price_action_analyzer = PriceActionAnalyzer(self)
        self.logger.info("Price Action Analyzer initialized for 60% signal weighting")
        
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
        self.peak_value = self.p.initial_capital
        self.initial_capital = self.p.initial_capital  # Use parameter for consistent reference
        self.last_completed_portfolio_value = self.p.initial_capital  # Initialize reference capital
        
        self.logger.info(f"Initial broker cash: {self.peak_value}")
        self.logger.info(f"Initial capital stored: {self.initial_capital}")
        
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
        self.logger.info(f"Enhanced Forex Strategy initialized with hybrid price action (60%) + technical indicators (40%) {gpu_status}")
        if self.use_gpu:
            self.logger.info(f"GPU Device: {torch.cuda.get_device_name(0)}")
        
        self.logger.info("=== HYBRID STRATEGY INITIALIZATION COMPLETE ===")

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
        Detect current market regime using advanced statistical methods with progressive data handling
        Returns: (regime_type, confidence_score)
        """
        current_data_length = len(self.data)
        
        # Use available data, but with minimum requirements
        min_regime_data = 20  # Minimum for basic regime detection
        if current_data_length < min_regime_data:
            return 'neutral', 0.0
            
        try:
            # Use available data up to regime_lookback, but at least min_regime_data
            lookback_period = min(current_data_length - 1, self.p.regime_lookback)
            lookback_period = max(lookback_period, min_regime_data)
            
            # Get recent price data with available lookback
            recent_closes = np.array([self.dataclose[-i] for i in range(lookback_period, 0, -1)])
            recent_returns = np.diff(np.log(recent_closes))
            
            # Trend detection using linear regression
            x = np.arange(len(recent_closes))
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, recent_closes)
            
            # Volatility clustering detection (adapted for shorter periods)
            volatility = np.std(recent_returns) * np.sqrt(252)  # Annualized
            
            # Adaptive volatility calculation based on available data
            vol_window = min(10, len(recent_returns) // 2)
            if vol_window >= 3:
                vol_segments = [np.std(recent_returns[i:i+vol_window])
                               for i in range(0, len(recent_returns)-vol_window+1, max(1, vol_window//2))]
                vol_ma = np.mean(vol_segments) if vol_segments else volatility
            else:
                vol_ma = volatility
                
            vol_ratio = volatility / max(vol_ma, 1e-8) if vol_ma > 0 else 1.0
            
            # Regime classification with confidence adjustment for data length
            trend_strength = abs(r_value)
            data_confidence_factor = min(1.0, lookback_period / self.p.regime_lookback)
            
            if trend_strength > self.p.trend_threshold and slope > 0:
                regime = 'bullish_trend'
                confidence = min(trend_strength * data_confidence_factor, 0.95)
            elif trend_strength > self.p.trend_threshold and slope < 0:
                regime = 'bearish_trend'
                confidence = min(trend_strength * data_confidence_factor, 0.95)
            elif vol_ratio > 1.5:
                regime = 'high_volatility'
                confidence = min((vol_ratio / 2.0) * data_confidence_factor, 0.9)
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

    def calculate_portfolio_optimized_position_size(self, signal_strength, volatility, regime):
        """Portfolio-aware position sizing for maximum returns"""

        # 1. Dynamic Kelly based on recent performance
        recent_win_rate = self._calculate_recent_win_rate(window=20)
        recent_avg_win = self._calculate_recent_avg_win(window=20)
        recent_avg_loss = self._calculate_recent_avg_loss(window=20)

        # 2. Portfolio health adjustment
        portfolio_health = self._calculate_portfolio_health_factor()
        health_multiplier = 0.5 + (portfolio_health * 0.5)  # 0.5 to 1.0

        # 3. Regime-based sizing
        regime_multiplier = {
            'bullish_trend': 1.4,    # Increase size in trends
            'bearish_trend': 1.4,
            'high_volatility': 0.7,  # Reduce in high vol
            'mean_reverting': 1.0,
            'neutral': 1.0
        }.get(self.current_regime, 1.0)

        # 4. Signal strength exponential scaling
        signal_multiplier = signal_strength ** 1.5  # Non-linear scaling

        # 5. Volatility-adjusted sizing
        vol_adjustment = min(2.0, 1.0 / (volatility * 5))  # More aggressive in low vol

        # 6. Portfolio concentration limits
        current_exposure = self._calculate_current_portfolio_exposure()
        concentration_limit = min(0.15, 0.05 + (portfolio_health * 0.1))  # Dynamic limits

        # Calculate final size
        base_kelly = self._calculate_adaptive_kelly(recent_win_rate, recent_avg_win, recent_avg_loss)
        final_size = (base_kelly * health_multiplier * regime_multiplier *
                     signal_multiplier * vol_adjustment)

        # Apply concentration limits
        final_size = min(final_size, concentration_limit - current_exposure)

        return max(final_size, 0.005)  # Minimum 0.5%

    def _calculate_recent_win_rate(self, window=20):
        """Calculate win rate over recent trades"""
        if self.trade_count < window:
            return self.winning_trades / max(self.trade_count, 1)
        # In a real implementation, you'd track recent trades
        return self.winning_trades / max(self.trade_count, 1)

    def _calculate_recent_avg_win(self, window=20):
        """Calculate average win over recent trades"""
        # Simplified - in practice, track individual trade P&Ls
        return 0.025  # Estimated

    def _calculate_recent_avg_loss(self, window=20):
        """Calculate average loss over recent trades"""
        # Simplified - in practice, track individual trade P&Ls
        return 0.015  # Estimated

    def _calculate_portfolio_health_factor(self):
        """Calculate portfolio health factor (0-1)"""
        if self.trade_count == 0:
            return 0.5  # Neutral starting point

        win_rate = self.winning_trades / max(self.trade_count, 1)
        profit_factor = self._calculate_profit_factor()

        # Health based on win rate and profit factor
        health = (win_rate * 0.6) + (min(profit_factor / 2.0, 1.0) * 0.4)
        return max(0.1, min(health, 1.0))

    def _calculate_current_portfolio_exposure(self):
        """Calculate current portfolio exposure as percentage"""
        if not self.position:
            return 0.0

        position_value = abs(self.position.size) * self.dataclose[0]
        portfolio_value = self.broker.get_value()
        return position_value / max(portfolio_value, 1e-8)

    def _calculate_adaptive_kelly(self, win_rate, avg_win, avg_loss):
        """Calculate adaptive Kelly fraction"""
        if win_rate <= 0 or avg_loss <= 0:
            return 0.02  # Conservative default

        kelly = (win_rate * avg_win - (1 - win_rate) * avg_loss) / max(avg_win, 1e-8)
        return max(0, min(kelly, 0.25))  # Cap at 25%

    def _calculate_profit_factor(self):
        """Calculate profit factor"""
        if self.trade_count == 0:
            return 1.0

        # Simplified - in practice, track gross profits vs losses
        if self.total_pnl > 0:
            return 1.5  # Assume 1.5 profit factor for positive P&L
        else:
            return 0.7  # Assume 0.7 profit factor for negative P&L

    def optimize_portfolio_exposure(self):
        """Portfolio-level optimization for maximum total returns"""

        # 1. Calculate current portfolio metrics
        total_exposure = self._calculate_total_portfolio_exposure()
        portfolio_volatility = self._calculate_portfolio_volatility()
        portfolio_correlation = self._calculate_portfolio_correlation()

        # 2. Determine optimal portfolio allocation
        max_exposure = self._calculate_optimal_max_exposure(portfolio_volatility)

        # 3. Adjust individual position sizes based on portfolio needs
        if total_exposure > max_exposure:
            # Reduce position sizes proportionally
            reduction_factor = max_exposure / total_exposure
            self._adjust_all_position_sizes(reduction_factor)

        # 4. Implement portfolio rebalancing
        self._rebalance_portfolio_for_max_returns()

        return max_exposure

    def _calculate_total_portfolio_exposure(self):
        """Calculate total portfolio exposure across all positions"""
        if not self.position:
            return 0.0

        position_value = abs(self.position.size) * self.dataclose[0]
        portfolio_value = self.broker.get_value()
        return position_value / max(portfolio_value, 1e-8)

    def _calculate_portfolio_volatility(self):
        """Calculate portfolio volatility"""
        # Simplified - in practice, calculate based on position volatilities
        return 0.15  # Assume 15% annualized volatility

    def _calculate_portfolio_correlation(self):
        """Calculate portfolio correlation"""
        # Simplified - in practice, calculate correlation matrix
        return 0.3  # Assume 0.3 average correlation

    def _calculate_optimal_max_exposure(self, portfolio_volatility):
        """Calculate optimal maximum exposure based on portfolio risk"""

        # Base exposure limits
        base_max_exposure = 0.30  # 30% max exposure

        # Adjust based on volatility
        if portfolio_volatility < 0.15:  # Low volatility
            max_exposure = min(0.40, base_max_exposure * 1.3)
        elif portfolio_volatility > 0.25:  # High volatility
            max_exposure = max(0.15, base_max_exposure * 0.7)
        else:
            max_exposure = base_max_exposure

        # Adjust based on recent performance
        recent_returns = self._calculate_recent_portfolio_returns(window=20)
        if recent_returns > 0.05:  # Good recent performance
            max_exposure *= 1.1  # Increase exposure
        elif recent_returns < -0.05:  # Poor recent performance
            max_exposure *= 0.8  # Decrease exposure

        return max_exposure

    def _calculate_recent_portfolio_returns(self, window=20):
        """Calculate recent portfolio returns"""
        # Simplified - in practice, track portfolio value over time
        if self.trade_count > 0:
            return self.total_pnl / self.initial_capital
        return 0.0

    def calculate_momentum_acceleration(self):
        """Calculate momentum acceleration for entry timing"""
        # Multi-timeframe momentum
        mom_1m = self.momentum_features.get('mom_3', bt.indicators.Momentum(period=3))[0] if 'mom_3' in self.momentum_features else 0
        mom_5m = self.momentum_features.get('mom_8', bt.indicators.Momentum(period=8))[0] if 'mom_8' in self.momentum_features else 0
        mom_15m = self.momentum_features.get('mom_13', bt.indicators.Momentum(period=13))[0] if 'mom_13' in self.momentum_features else 0

        # Acceleration detection
        acceleration = (mom_1m - mom_5m) + (mom_5m - mom_15m)

        # Boost signals in acceleration periods
        if acceleration > 0.001:  # Positive acceleration threshold
            return self.p.momentum_acceleration  # 1.4x signal strength
        elif acceleration < -0.001:  # Negative acceleration
            return 0.7  # Reduce signal strength
        else:
            return 1.0  # No acceleration boost

    def detect_breakout_signals(self):
        """Enhanced breakout detection for maximum returns"""
        # Volume + price breakout
        volume_breakout = self.volume_ratio[0] > 2.0 if len(self.volume_ratio) > 0 else False
        price_breakout = self.dataclose[0] > self.bb.lines.top[0] if len(self.bb.lines.top) > 0 else False

        # Consolidation breakout
        consolidation_period = 20  # bars
        if len(self.data) > consolidation_period:
            recent_highs = [self.datahigh[-i] for i in range(1, consolidation_period + 1)]
            recent_lows = [self.datalow[-i] for i in range(1, consolidation_period + 1)]
            consolidation_range = (max(recent_highs) - min(recent_lows)) / self.dataclose[0]
            consolidation_breakout = consolidation_range < 0.005  # Tight consolidation
        else:
            consolidation_breakout = False

        if volume_breakout and price_breakout and consolidation_breakout:
            return self.p.breakout_multiplier  # 1.5x signal strength
        elif volume_breakout or price_breakout:
            return 1.2  # Moderate breakout boost
        else:
            return 1.0  # No breakout

    def _adjust_all_position_sizes(self, reduction_factor):
        """Adjust all position sizes proportionally"""
        if self.position and reduction_factor < 1.0:
            current_size = self.position.size
            target_size = current_size * reduction_factor

            # Close partial position to reduce size
            if abs(target_size) < abs(current_size):
                self.close(size=abs(current_size - target_size))
                self.logger.info(f"Reduced position size by {1-reduction_factor:.2%} for portfolio optimization")

    def _rebalance_portfolio_for_max_returns(self):
        """Rebalance portfolio for maximum returns"""
        # This would implement portfolio rebalancing logic
        # For now, just ensure exposure limits are respected
        current_exposure = self._calculate_total_portfolio_exposure()
        max_exposure = self._calculate_optimal_max_exposure(self._calculate_portfolio_volatility())

        if current_exposure > max_exposure:
            self._adjust_all_position_sizes(max_exposure / current_exposure)

    def optimize_order_execution(self, signal, position_size):
        """Advanced order execution for maximum fill quality and minimal slippage"""

        # 1. Determine optimal order type based on market conditions
        order_type = self._select_optimal_order_type(signal, position_size)

        # 2. Calculate optimal execution price
        execution_price = self._calculate_optimal_execution_price(signal, order_type)

        # 3. Implement smart order routing
        if order_type == 'limit':
            # Place limit orders at optimal prices
            limit_price = self._calculate_limit_price(signal, execution_price)
            order = self.buy(size=position_size, price=limit_price, exectype=bt.Order.Limit)
        else:
            # Use market orders with timing optimization
            order = self._execute_timed_market_order(signal, position_size)

        # 4. Implement post-order management
        self._setup_order_management(order, signal)

        return order

    def _select_optimal_order_type(self, signal, position_size):
        """Select optimal order type based on market conditions and position size"""

        # Large positions in illiquid conditions -> Limit orders
        if position_size > 0.05 and self._detect_low_liquidity():
            return 'limit'

        # Strong signals in trending markets -> Market orders for speed
        if signal['strength'] > 0.8 and self._is_strong_trend():
            return 'market'

        # Default to market for most conditions
        return 'market'

    def _detect_low_liquidity(self):
        """Detect low liquidity conditions"""
        # Simplified - check volume and spread
        current_volume = self.datavolume[0] if len(self.datavolume) > 0 else 0
        avg_volume = np.mean([self.datavolume[-i] for i in range(1, min(21, len(self.datavolume)))]) if len(self.datavolume) > 1 else current_volume

        return current_volume < (avg_volume * 0.5) if avg_volume > 0 else False

    def _is_strong_trend(self):
        """Check if market is in strong trend"""
        return self.current_regime in ['bullish_trend', 'bearish_trend'] and self.regime_confidence > 0.7

    def _calculate_optimal_execution_price(self, signal, order_type):
        """Calculate optimal execution price"""
        current_price = self.dataclose[0]

        if order_type == 'limit':
            # For limit orders, calculate based on signal direction
            if signal.get('buy_score', 0) > signal.get('sell_score', 0):
                # Buying - place slightly below current price
                return current_price * 0.9995  # 0.05% below
            else:
                # Selling - place slightly above current price
                return current_price * 1.0005  # 0.05% above

        return current_price

    def _calculate_limit_price(self, signal, execution_price):
        """Calculate limit price for order"""
        return execution_price

    def _execute_timed_market_order(self, signal, position_size):
        """Execute market orders at optimal timing"""

        # Wait for favorable price action before executing
        if self._wait_for_favorable_entry(signal, timeout=5):  # Wait up to 5 bars
            order = self.buy(size=position_size, exectype=bt.Order.Market)
            return order
        else:
            # Timeout - execute anyway but with smaller size
            adjusted_size = position_size * 0.7
            order = self.buy(size=adjusted_size, exectype=bt.Order.Market)
            return order

    def _wait_for_favorable_entry(self, signal, timeout=5):
        """Wait for favorable entry conditions"""
        # Simplified - in practice, this would monitor price action
        return True  # For now, always proceed

    def _setup_order_management(self, order, signal):
        """Setup post-order management"""
        # This would setup order monitoring and adjustment logic
        self.logger.info(f"Order management setup for order {order.ref if order else 'None'}")

    def implement_performance_adaptation(self):
        """Continuous performance monitoring and parameter adaptation"""

        # 1. Real-time performance metrics
        self.performance_metrics = self._calculate_real_time_performance()

        # 2. Parameter optimization based on performance
        if self.performance_metrics['sharpe_ratio'] < 0.5:
            self._adjust_parameters_for_better_risk_adjusted_returns()

        if self.performance_metrics['win_rate'] < 0.45:
            self._optimize_entry_filters()

        if self.performance_metrics['avg_profit'] < self.performance_metrics['avg_loss'] * 1.5:
            self._improve_risk_reward_ratios()

        # 3. Market regime adaptation
        self._adapt_to_regime_changes()

        # 4. Portfolio health monitoring
        if self._detect_portfolio_stress():
            self._implement_defensive_measures()

    def _calculate_real_time_performance(self):
        """Calculate comprehensive real-time performance metrics"""

        metrics = {
            'total_return': self._calculate_total_return(),
            'sharpe_ratio': self._calculate_sharpe_ratio(),
            'win_rate': self.winning_trades / max(self.trade_count, 1),
            'avg_profit': self._calculate_avg_profit(),
            'avg_loss': self._calculate_avg_loss(),
            'max_drawdown': self.max_drawdown,
            'profit_factor': self._calculate_profit_factor(),
            'recovery_factor': self._calculate_recovery_factor(),
            'portfolio_volatility': self._calculate_portfolio_volatility(),
            'risk_adjusted_return': self._calculate_risk_adjusted_return()
        }

        return metrics

    def _calculate_total_return(self):
        """Calculate total return"""
        current_value = self.broker.get_value()
        return (current_value - self.initial_capital) / self.initial_capital

    def _calculate_sharpe_ratio(self):
        """Calculate Sharpe ratio"""
        # Simplified - in practice, calculate based on returns and volatility
        total_return = self._calculate_total_return()
        volatility = self._calculate_portfolio_volatility()
        return total_return / max(volatility, 0.01)

    def _calculate_avg_profit(self):
        """Calculate average profit per trade"""
        if self.winning_trades == 0:
            return 0.0
        return self.total_pnl / self.winning_trades

    def _calculate_avg_loss(self):
        """Calculate average loss per trade"""
        losing_trades = self.trade_count - self.winning_trades
        if losing_trades == 0:
            return 0.0
        return self.total_pnl / losing_trades  # Since total_pnl includes losses

    def _calculate_recovery_factor(self):
        """Calculate recovery factor"""
        if self.max_drawdown == 0:
            return float('inf')
        total_return = self._calculate_total_return()
        return total_return / self.max_drawdown

    def _calculate_risk_adjusted_return(self):
        """Calculate risk-adjusted return"""
        total_return = self._calculate_total_return()
        volatility = self._calculate_portfolio_volatility()
        return total_return / max(volatility, 0.01)

    def _adjust_parameters_for_better_risk_adjusted_returns(self):
        """Adjust parameters for better risk-adjusted returns"""
        self.logger.info("Adjusting parameters for better risk-adjusted returns")
        # This would modify strategy parameters based on performance

    def _optimize_entry_filters(self):
        """Optimize entry filters based on performance"""
        self.logger.info("Optimizing entry filters")
        # This would adjust signal thresholds and filters

    def _improve_risk_reward_ratios(self):
        """Improve risk/reward ratios"""
        self.logger.info("Improving risk/reward ratios")
        # This would adjust stop loss and take profit levels

    def _adapt_to_regime_changes(self):
        """Adapt to market regime changes"""
        self.logger.info(f"Adapting to regime: {self.current_regime}")
        # This would adjust parameters based on current regime

    def _detect_portfolio_stress(self):
        """Detect portfolio stress conditions"""
        current_drawdown = (self.peak_value - self.broker.get_value()) / self.peak_value
        return current_drawdown > 0.1  # 10% drawdown threshold

    def _implement_defensive_measures(self):
        """Implement defensive measures during stress"""
        self.logger.info("Implementing defensive measures")
        # This would reduce position sizes, tighten stops, etc.

    def calculate_dynamic_position_size(self, signal_strength: float, volatility: float,
                                       price_action_confidence: float = 0.5,
                                       technical_confidence: float = 0.5) -> float:
        """
        Enhanced position size calculation using portfolio-optimized sizing
        """
        if not self.p.dynamic_sizing:
            return 1.0

        try:
            # Use the new portfolio-aware sizing system
            final_size = self.calculate_portfolio_optimized_position_size(
                signal_strength, volatility, self.current_regime
            )

            # Apply additional confidence adjustments
            combined_confidence = (price_action_confidence * 0.6) + (technical_confidence * 0.4)
            confidence_adjustment = 0.8 + (combined_confidence * 0.4)  # Range: 0.8 to 1.2

            final_size *= confidence_adjustment

            # Ensure within risk limits
            max_size = self.p.max_risk_per_trade / max(volatility, 0.005)
            final_size = min(final_size, max_size)

            self.logger.info(f"Portfolio-Optimized Position Sizing:")
            self.logger.info(f"  Base Size: {final_size/confidence_adjustment:.6f}")
            self.logger.info(f"  Confidence Adjustment: {confidence_adjustment:.4f}")
            self.logger.info(f"  Final Size: {final_size:.6f}")
            self.logger.info(f"  Portfolio Health: {self._calculate_portfolio_health_factor():.4f}")
            self.logger.info(f"  Current Exposure: {self._calculate_current_portfolio_exposure():.4f}")

            return max(final_size, 0.005)  # Minimum 0.5%

        except Exception as e:
            self.logger.error(f"Error calculating portfolio-optimized position size: {e}")
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
            
            # Enhanced Trend signals with acceleration and momentum boost
            self.logger.info("=== TREND ANALYSIS WITH MOMENTUM ACCELERATION ===")
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

            # Apply momentum acceleration boost
            momentum_boost = self.calculate_momentum_acceleration()
            self.logger.info(f"Momentum acceleration boost: {momentum_boost:.3f}")
            if momentum_boost > 1.0:
                old_trend_score = trend_score
                trend_score *= momentum_boost
                self.logger.info(f"  Applied momentum boost: {old_trend_score:.3f} * {momentum_boost:.3f} = {trend_score:.3f}")

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
            self.logger.info("=== VOLUME ANALYSIS WITH BREAKOUT DETECTION ===")
            volume_score = 0.0
            breakout_boost = self.detect_breakout_signals()
            self.logger.info(f"Breakout detection boost: {breakout_boost:.3f}")

            if self.p.volume_confirmation and len(self.volume_ratio) > 0:
                volume_ratio_val = self.volume_ratio[0]
                self.logger.info(f"Volume ratio: {volume_ratio_val:.3f}")
                self.logger.info(f"Current volume: {self.datavolume[0]}")
                self.logger.info(f"Volume SMA: {self.volume_sma[0]}")

                if volume_ratio_val > 1.5:  # Strong volume breakout
                    volume_score = 1.2 * breakout_boost  # Apply breakout boost
                    self.logger.info(f"  Strong volume breakout with boost: 1.2 * {breakout_boost:.3f} = {volume_score:.3f}")
                elif volume_ratio_val > 1.2:
                    volume_score = 0.8 * breakout_boost  # Apply breakout boost
                    self.logger.info(f"  Moderate volume with boost: 0.8 * {breakout_boost:.3f} = {volume_score:.3f}")
                elif volume_ratio_val < 0.7:
                    volume_score = -0.6
                    self.logger.info("  Subtracted 0.6 to volume_score (low volume)")
            else:
                self.logger.info("Volume confirmation disabled or no volume data")

            volume_component = max(-1.0, min(volume_score, 1.0))
            signals['components']['volume'] = volume_component
            signals['components']['breakout_boost'] = breakout_boost
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

    def calculate_dynamic_signal_weights(self):
        """Dynamically adjust signal weights based on market conditions and performance"""

        # 1. Performance-based weight adjustment
        pa_recent_accuracy = self._calculate_signal_accuracy('price_action', window=50)
        tech_recent_accuracy = self._calculate_signal_accuracy('technical', window=50)

        # 2. Regime-based weight optimization
        regime_weights = {
            'bullish_trend': {'price_action': 0.7, 'technical': 0.3},  # Favor momentum
            'bearish_trend': {'price_action': 0.7, 'technical': 0.3},
            'high_volatility': {'price_action': 0.5, 'technical': 0.5},  # Balanced
            'mean_reverting': {'price_action': 0.4, 'technical': 0.6},  # Favor technical
            'neutral': {'price_action': 0.6, 'technical': 0.4}
        }

        base_weights = regime_weights.get(self.current_regime, {'price_action': 0.6, 'technical': 0.4})

        # 3. Performance adjustment (±20% based on accuracy)
        performance_adjustment = (pa_recent_accuracy - tech_recent_accuracy) * 0.2

        final_weights = {
            'price_action': base_weights['price_action'] + performance_adjustment,
            'technical': base_weights['technical'] - performance_adjustment
        }

        # Ensure weights stay within bounds
        final_weights['price_action'] = max(0.3, min(0.8, final_weights['price_action']))
        final_weights['technical'] = max(0.2, min(0.7, final_weights['technical']))

        return final_weights

    def optimize_signal_thresholds(self):
        """Dynamically adjust signal thresholds for maximum profitability"""

        # Calculate optimal thresholds based on recent performance
        profitable_signals = self._analyze_profitable_signal_patterns(window=100)

        # Adjust thresholds to capture more profitable setups
        if profitable_signals['avg_profit'] > 0.002:  # High-profit signals
            min_threshold = max(0.05, profitable_signals['threshold'] * 0.8)  # Lower threshold
        else:
            min_threshold = min(0.25, profitable_signals['threshold'] * 1.2)  # Higher threshold

        return min_threshold

    def _calculate_signal_accuracy(self, signal_type, window=50):
        """Calculate accuracy of signal type over recent trades"""
        # Simplified implementation - in practice, track signal performance
        if signal_type == 'price_action':
            return 0.65  # Assume 65% accuracy for price action
        else:
            return 0.60  # Assume 60% accuracy for technical

    def _analyze_profitable_signal_patterns(self, window=100):
        """Analyze patterns of profitable signals"""
        # Simplified implementation
        return {
            'avg_profit': 0.0025,  # Assume positive average profit
            'threshold': 0.15  # Current threshold
        }

    def generate_hybrid_signals(self) -> Dict[str, Any]:
        """
        Generate hybrid trading signals with dynamic weighting: adaptive price action + technical indicators
        Combines candlestick patterns, S/R levels, trend lines with traditional indicators
        """
        signals = {
            'buy_score': 0.0,
            'sell_score': 0.0,
            'signal_strength': 0.0,
            'confidence': 0.0,
            'regime_filter': True,
            'volatility_filter': True,
            'price_action_score': 0.0,
            'technical_score': 0.0,
            'components': {},
            'price_action_details': {},
            'technical_details': {}
        }
        
        try:
            self.logger.info("=== HYBRID SIGNAL GENERATION (60% Price Action + 40% Technical) ===")
            
            # === PRICE ACTION ANALYSIS (60% WEIGHT) ===
            self.logger.info("=== PRICE ACTION ANALYSIS (60% WEIGHT) ===")
            
            price_action_data = self.price_action_analyzer.calculate_price_action_score(lookback=30)
            
            # Extract price action scores
            pa_bullish = price_action_data['bullish_score']
            pa_bearish = price_action_data['bearish_score']
            pa_confidence = price_action_data['confidence']
            
            self.logger.info(f"Price Action Scores:")
            self.logger.info(f"  Bullish: {pa_bullish:.4f}")
            self.logger.info(f"  Bearish: {pa_bearish:.4f}")
            self.logger.info(f"  Confidence: {pa_confidence:.4f}")
            self.logger.info(f"  Patterns: {price_action_data.get('patterns_detected', [])}")
            
            # Log price action components
            if 'components' in price_action_data:
                self.logger.info("Price Action Components:")
                for component, value in price_action_data['components'].items():
                    self.logger.info(f"  {component}: {value:.4f}")
            
            signals['price_action_details'] = price_action_data
            
            # === TECHNICAL INDICATOR ANALYSIS (40% WEIGHT) ===
            self.logger.info("=== TECHNICAL INDICATOR ANALYSIS (40% WEIGHT) ===")
            
            tech_bullish = 0.0
            tech_bearish = 0.0
            tech_components = {}
            
            # RSI Analysis (10% of total signal)
            rsi_score = 0.0
            current_rsi = float(self.rsi[0])
            self.logger.info(f"RSI Analysis: {current_rsi:.2f}")
            
            if current_rsi < self.p.rsi_oversold:
                rsi_score = 0.4  # Strong bullish
                self.logger.info(f"  RSI Oversold: +0.4 bullish")
            elif current_rsi > self.p.rsi_overbought:
                rsi_score = -0.4  # Strong bearish
                self.logger.info(f"  RSI Overbought: +0.4 bearish")
            elif current_rsi < 45:
                rsi_score = 0.2  # Mild bullish
                self.logger.info(f"  RSI Below 45: +0.2 bullish")
            elif current_rsi > 55:
                rsi_score = -0.2  # Mild bearish
                self.logger.info(f"  RSI Above 55: +0.2 bearish")
            
            tech_components['rsi'] = rsi_score
            
            # MACD Analysis (10% of total signal)
            macd_score = 0.0
            macd_line = float(self.macd.macd[0])
            macd_signal = float(self.macd.signal[0])
            self.logger.info(f"MACD Analysis: Line={macd_line:.6f}, Signal={macd_signal:.6f}")
            
            if macd_line > macd_signal:
                macd_score = 0.3
                self.logger.info(f"  MACD Bullish: +0.3")
                
                # Check for histogram momentum
                if hasattr(self.macd, 'histo') and len(self.macd.histo) > 1:
                    if self.macd.histo[0] > self.macd.histo[-1]:
                        macd_score += 0.1
                        self.logger.info(f"  MACD Histogram Momentum: +0.1")
            else:
                macd_score = -0.3
                self.logger.info(f"  MACD Bearish: +0.3 bearish")
                
                if hasattr(self.macd, 'histo') and len(self.macd.histo) > 1:
                    if self.macd.histo[0] < self.macd.histo[-1]:
                        macd_score -= 0.1
                        self.logger.info(f"  MACD Histogram Momentum: +0.1 bearish")
            
            tech_components['macd'] = macd_score
            
            # Moving Average Analysis (10% of total signal)
            ma_score = 0.0
            ema_fast = float(self.ema_fast[0])
            ema_slow = float(self.ema_slow[0])
            current_price = float(self.dataclose[0])
            
            self.logger.info(f"Moving Average Analysis:")
            self.logger.info(f"  EMA Fast: {ema_fast:.5f}")
            self.logger.info(f"  EMA Slow: {ema_slow:.5f}")
            self.logger.info(f"  Current Price: {current_price:.5f}")
            
            if ema_fast > ema_slow:
                ma_score = 0.3
                self.logger.info(f"  EMA Fast > Slow: +0.3 bullish")
                
                # Price above both EMAs
                if current_price > ema_fast:
                    ma_score += 0.1
                    self.logger.info(f"  Price > EMA Fast: +0.1 bullish")
            else:
                ma_score = -0.3
                self.logger.info(f"  EMA Fast < Slow: +0.3 bearish")
                
                # Price below both EMAs
                if current_price < ema_fast:
                    ma_score -= 0.1
                    self.logger.info(f"  Price < EMA Fast: +0.1 bearish")
            
            tech_components['moving_averages'] = ma_score
            
            # Bollinger Bands Analysis (10% of total signal)
            bb_score = 0.0
            bb_upper = float(self.bb.lines.top[0])
            bb_middle = float(self.bb.lines.mid[0])
            bb_lower = float(self.bb.lines.bot[0])
            
            bb_position = (current_price - bb_lower) / (bb_upper - bb_lower) if bb_upper != bb_lower else 0.5
            
            self.logger.info(f"Bollinger Bands Analysis:")
            self.logger.info(f"  BB Position: {bb_position:.4f}")
            self.logger.info(f"  Price: {current_price:.5f}")
            self.logger.info(f"  BB Upper: {bb_upper:.5f}")
            self.logger.info(f"  BB Middle: {bb_middle:.5f}")
            self.logger.info(f"  BB Lower: {bb_lower:.5f}")
            
            if bb_position < 0.2:
                bb_score = 0.3  # Near lower band - bullish
                self.logger.info(f"  Near Lower Band: +0.3 bullish")
            elif bb_position > 0.8:
                bb_score = -0.3  # Near upper band - bearish
                self.logger.info(f"  Near Upper Band: +0.3 bearish")
            elif bb_position < 0.4:
                bb_score = 0.1  # Below middle - mild bullish
                self.logger.info(f"  Below Middle: +0.1 bullish")
            elif bb_position > 0.6:
                bb_score = -0.1  # Above middle - mild bearish
                self.logger.info(f"  Above Middle: +0.1 bearish")
            
            tech_components['bollinger_bands'] = bb_score
            
            # Calculate technical indicator totals
            if rsi_score > 0 or macd_score > 0 or ma_score > 0 or bb_score > 0:
                tech_bullish = max(0, rsi_score) + max(0, macd_score) + max(0, ma_score) + max(0, bb_score)
            else:
                tech_bullish = 0.0
                
            if rsi_score < 0 or macd_score < 0 or ma_score < 0 or bb_score < 0:
                tech_bearish = abs(min(0, rsi_score)) + abs(min(0, macd_score)) + abs(min(0, ma_score)) + abs(min(0, bb_score))
            else:
                tech_bearish = 0.0
            
            self.logger.info(f"Technical Indicator Totals:")
            self.logger.info(f"  Technical Bullish: {tech_bullish:.4f}")
            self.logger.info(f"  Technical Bearish: {tech_bearish:.4f}")
            
            signals['technical_details'] = {
                'bullish_score': tech_bullish,
                'bearish_score': tech_bearish,
                'components': tech_components,
                'rsi': current_rsi,
                'macd_line': macd_line,
                'macd_signal': macd_signal,
                'ema_fast': ema_fast,
                'ema_slow': ema_slow,
                'bb_position': bb_position
            }
            
            # === HYBRID SIGNAL CALCULATION WITH DYNAMIC WEIGHTS ===
            self.logger.info("=== HYBRID SIGNAL CALCULATION WITH DYNAMIC WEIGHTS ===")

            # Get dynamic weights based on performance and regime
            dynamic_weights = self.calculate_dynamic_signal_weights()
            price_action_weight = dynamic_weights['price_action']
            technical_weight = dynamic_weights['technical']

            self.logger.info(f"Dynamic Weights - Price Action: {price_action_weight:.3f}, Technical: {technical_weight:.3f}")
            
            # Calculate weighted scores
            weighted_pa_bullish = pa_bullish * price_action_weight
            weighted_pa_bearish = pa_bearish * price_action_weight
            weighted_tech_bullish = tech_bullish * technical_weight
            weighted_tech_bearish = tech_bearish * technical_weight
            
            self.logger.info(f"Weighted Scores:")
            self.logger.info(f"  Price Action Bullish (60%): {pa_bullish:.4f} * 0.6 = {weighted_pa_bullish:.4f}")
            self.logger.info(f"  Price Action Bearish (60%): {pa_bearish:.4f} * 0.6 = {weighted_pa_bearish:.4f}")
            self.logger.info(f"  Technical Bullish (40%): {tech_bullish:.4f} * 0.4 = {weighted_tech_bullish:.4f}")
            self.logger.info(f"  Technical Bearish (40%): {tech_bearish:.4f} * 0.4 = {weighted_tech_bearish:.4f}")
            
            # Final hybrid scores
            final_bullish = weighted_pa_bullish + weighted_tech_bullish
            final_bearish = weighted_pa_bearish + weighted_tech_bearish
            
            signals['buy_score'] = final_bullish
            signals['sell_score'] = final_bearish
            signals['signal_strength'] = max(final_bullish, final_bearish)
            signals['price_action_score'] = pa_bullish + pa_bearish
            signals['technical_score'] = tech_bullish + tech_bearish
            
            # Calculate combined confidence
            pa_weight_in_confidence = 0.6
            tech_weight_in_confidence = 0.4
            
            # Technical confidence based on indicator agreement
            tech_confidence = min(abs(tech_bullish - tech_bearish) / max(tech_bullish + tech_bearish, 0.1), 1.0)
            
            combined_confidence = (pa_confidence * pa_weight_in_confidence) + (tech_confidence * tech_weight_in_confidence)
            signals['confidence'] = combined_confidence
            
            self.logger.info(f"Final Hybrid Scores:")
            self.logger.info(f"  Buy Score: {signals['buy_score']:.4f}")
            self.logger.info(f"  Sell Score: {signals['sell_score']:.4f}")
            self.logger.info(f"  Signal Strength: {signals['signal_strength']:.4f}")
            self.logger.info(f"  Combined Confidence: {signals['confidence']:.4f}")
            self.logger.info(f"  Price Action Contribution: {signals['price_action_score']:.4f}")
            self.logger.info(f"  Technical Contribution: {signals['technical_score']:.4f}")
            
            # Enhanced filters
            self.logger.info("=== FILTER EVALUATION ===")
            
            # Volatility filter
            if self.p.use_volatility_filter:
                current_vol = self.atr[0] / self.dataclose[0] if self.dataclose[0] > 0 else 0
                vol_threshold = self.p.volatility_threshold * 3.0
                vol_filter_pass = current_vol <= vol_threshold
                
                self.logger.info(f"Volatility filter:")
                self.logger.info(f"  Current vol: {current_vol:.6f}")
                self.logger.info(f"  Threshold: {vol_threshold:.6f}")
                self.logger.info(f"  Filter pass: {vol_filter_pass}")
                
                signals['volatility_filter'] = vol_filter_pass
                if not vol_filter_pass:
                    self.logger.info("  VOLATILITY FILTER FAILED")
            
            # Regime filter
            if self.p.use_regime_filter:
                regime_filter_pass = self.regime_confidence > 0.3
                signals['regime_filter'] = regime_filter_pass
                self.logger.info(f"Regime filter: {regime_filter_pass} (confidence: {self.regime_confidence:.3f})")
            
            # Store component details for analysis
            signals['components'] = {
                'price_action_bullish': weighted_pa_bullish,
                'price_action_bearish': weighted_pa_bearish,
                'technical_bullish': weighted_tech_bullish,
                'technical_bearish': weighted_tech_bearish,
                'price_action_confidence': pa_confidence,
                'technical_confidence': tech_confidence,
                **tech_components
            }
            
            self.logger.info(f"Hybrid Signal Summary:")
            self.logger.info(f"  Final Decision: {'BUY' if final_bullish > final_bearish else 'SELL'}")
            self.logger.info(f"  Signal Strength: {signals['signal_strength']:.4f}")
            self.logger.info(f"  Confidence: {signals['confidence']:.4f}")
            self.logger.info(f"  Price Action Weight: 60%")
            self.logger.info(f"  Technical Weight: 40%")
            
            return signals
            
        except Exception as e:
            import traceback
            self.logger.error(f"Error generating hybrid signals: {str(e)}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return signals

    def next(self):
        """Main strategy logic with advanced quantitative analysis"""
        self.next_call_count += 1
        
        # Update reference capital if portfolio value has changed significantly
        current_portfolio_value = self.broker.get_value()
        if abs(current_portfolio_value - self.last_completed_portfolio_value) > 1.0:  # $1 threshold
            old_reference = self.last_completed_portfolio_value
            self.last_completed_portfolio_value = current_portfolio_value
            self.logger.info(f"*** REAL-TIME REFERENCE CAPITAL UPDATE ***")
            self.logger.info(f"  Old Reference: ${old_reference:.2f}")
            self.logger.info(f"  New Reference: ${self.last_completed_portfolio_value:.2f}")
            self.logger.info(f"  Portfolio Change: ${self.last_completed_portfolio_value - old_reference:.2f}")
        
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
        
        # Enhanced pending order management
        if self.order:
            if self.next_call_count <= 10 or self.next_call_count % 100 == 0:
                self.logger.info("Pending order exists - checking status")
                
            # Check for stuck orders and implement timeout
            if hasattr(self, 'order_submitted_bar'):
                bars_since_submission = len(self) - self.order_submitted_bar
                
                # Log order status periodically
                if bars_since_submission % 10 == 0:
                    self.logger.warning(f"Order pending for {bars_since_submission} bars")
                    self.logger.warning(f"Order status: {self.order.getstatusname()}")
                    self.logger.warning(f"Order alive: {self.order.alive()}")
                
                # Cancel stuck orders after reasonable timeout
                if bars_since_submission > 20:  # Cancel after 20 bars
                    self.logger.error(f"*** CANCELING STUCK ORDER ***")
                    self.logger.error(f"Order {self.order.ref} stuck for {bars_since_submission} bars")
                    try:
                        self.cancel(self.order)
                        self.logger.error(f"Cancellation request sent for order {self.order.ref}")
                    except Exception as cancel_error:
                        self.logger.error(f"Failed to cancel order: {cancel_error}")
                    
                    # Force clear the order reference to prevent infinite blocking
                    self.order = None
                    if hasattr(self, 'order_submitted_bar'):
                        delattr(self, 'order_submitted_bar')
                    self.logger.error("Order reference cleared - strategy can continue")
                    
            return
        
        # === DATA AVAILABILITY CHECK ===
        try:
            # Progressive data requirement - start with minimum needed for basic indicators
            basic_min_data = max(self.p.slow_length, self.p.bb_period, self.p.atr_period)  # ~21 bars
            advanced_min_data = self.p.regime_lookback  # 75 bars
            
            current_data_length = len(self.data)
            
            # Allow strategy to run with basic indicators if we have at least basic_min_data
            if current_data_length < basic_min_data:
                if self.next_call_count <= 10:
                    self.logger.info(f"Insufficient data for basic indicators: {current_data_length} < {basic_min_data} required")
                return
            
            # Log data availability status
            if current_data_length < advanced_min_data:
                if self.next_call_count <= 5:
                    self.logger.info(f"Running with limited data: {current_data_length}/{advanced_min_data} bars (regime detection disabled)")
            
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
        
        # Generate hybrid signals (60% price action + 40% technical indicators)
        self.logger.info("Generating hybrid trading signals...")
        self.signal_generation_count += 1
        signals = self.generate_hybrid_signals()

        # Implement performance monitoring and adaptation
        if self.next_call_count % 50 == 0:  # Adapt every 50 bars
            self.implement_performance_adaptation()
        
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
            
            # Check signal strength and direction with dynamic thresholds
            buy_score = signals['buy_score']
            sell_score = signals['sell_score']
            min_threshold = self.optimize_signal_thresholds()  # Dynamic threshold optimization
            
            # CRITICAL FIX: Only trigger the stronger signal and ensure minimum threshold
            signal_direction = None
            signal_strength = 0.0
            
            self.logger.info(f"Signal Direction Analysis:")
            self.logger.info(f"  Buy Score: {buy_score:.4f}")
            self.logger.info(f"  Sell Score: {sell_score:.4f}")
            self.logger.info(f"  Min Threshold: {min_threshold:.4f}")
            self.logger.info(f"  Volatility Filter: {signals['volatility_filter']}")
            self.logger.info(f"  Regime Filter: {signals['regime_filter']}")
            
            # Determine signal direction based on stronger score
            if buy_score > sell_score and buy_score > min_threshold:
                signal_direction = 'BUY'
                signal_strength = buy_score
                self.logger.info(f"  DIRECTION: BUY (stronger score: {buy_score:.4f} > {sell_score:.4f})")
            elif sell_score > buy_score and sell_score > min_threshold:
                signal_direction = 'SELL'
                signal_strength = sell_score
                self.logger.info(f"  DIRECTION: SELL (stronger score: {sell_score:.4f} > {buy_score:.4f})")
            else:
                signal_direction = None
                self.logger.info(f"  DIRECTION: NONE (insufficient signal strength or tie)")
                self.logger.info(f"    Buy vs Sell: {buy_score:.4f} vs {sell_score:.4f}")
                self.logger.info(f"    Max score: {max(buy_score, sell_score):.4f}")
                self.logger.info(f"    Threshold: {min_threshold:.4f}")
            
            # Apply filters only if we have a valid signal direction
            filters_pass = signals['volatility_filter'] and signals['regime_filter']
            
            # Entry logic with corrected signal direction logic
            if (signal_direction == 'BUY' and filters_pass):
                
                self.buy_signal_count += 1
                self.logger.info(f"BUY SIGNAL TRIGGERED #{self.buy_signal_count}")
                
                # Calculate position size with hybrid confidence
                pa_confidence = signals.get('price_action_details', {}).get('confidence', 0.5)
                tech_confidence = signals.get('confidence', 0.5)
                position_size = self.calculate_dynamic_position_size(
                    signal_strength, current_vol, pa_confidence, tech_confidence
                )
                
                # Calculate stops and targets
                stop_distance = max(self.p.base_stop_loss, current_vol * 2)
                target_distance = stop_distance * 2.5  # 2.5:1 R/R minimum
                
                self.logger.info(f"Position sizing:")
                self.logger.info(f"  Size: {position_size:.6f}")
                self.logger.info(f"  Stop distance: {stop_distance:.6f}")
                self.logger.info(f"  Target distance: {target_distance:.6f}")
                
                self.log(f'BUY SIGNAL - Buy: {buy_score:.3f}, Sell: {sell_score:.3f}, '
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
                    
                    # CRITICAL FIX: Use Market order with immediate execution
                    self.order = self.buy(size=position_size, exectype=bt.Order.Market)
                    self.entry_bar = len(self)
                    self.order_submitted_bar = len(self)  # Track when order was submitted
                    
                    self.logger.info(f"*** BUY ORDER SUBMITTED ***")
                    self.logger.info(f"  Order reference: {self.order.ref if self.order else 'None'}")
                    self.logger.info(f"  Order object: {self.order}")
                    
                    # Add portfolio value change and profit/loss information
                    current_portfolio_value = self.broker.get_value()
                    
                    # Use the most recent reference capital (updated after last completed order)
                    reference_capital = self.last_completed_portfolio_value
                    portfolio_change = current_portfolio_value - reference_capital
                    portfolio_change_pct = (portfolio_change / reference_capital) * 100 if reference_capital > 0 else 0
                    
                    # Get portfolio summary from tracker
                    portfolio_summary = self.portfolio_tracker.get_portfolio_summary()
                    
                    self.logger.info(f"*** PORTFOLIO VALUE AFTER BUY ORDER ***")
                    self.logger.info(f"  Reference Capital (Last Trade): ${reference_capital:.2f}")
                    self.logger.info(f"  Current Portfolio Value: ${current_portfolio_value:.2f}")
                    self.logger.info(f"  Expected Trade P&L: ${portfolio_change:.2f} ({portfolio_change_pct:+.2f}%)")
                    self.logger.info(f"  Realized P&L: ${portfolio_summary['realized_pnl']:.2f}")
                    self.logger.info(f"  Unrealized P&L: ${portfolio_summary['unrealized_pnl']:.2f}")
                    self.logger.info(f"  Net P&L: ${portfolio_summary['net_pnl']:.2f}")
                    
                    if portfolio_change > 0:
                        self.logger.info(f"*** EXPECTED PROFIT: ${portfolio_change:.2f} (+{portfolio_change_pct:.2f}%) ***")
                    elif portfolio_change < 0:
                        self.logger.info(f"*** EXPECTED LOSS: ${portfolio_change:.2f} ({portfolio_change_pct:.2f}%) ***")
                    else:
                        self.logger.info(f"*** EXPECTED BREAK EVEN: ${portfolio_change:.2f} (0.00%) ***")
                    
                    # CRITICAL: Check if notify_order callback will be triggered
                    self.logger.info(f"*** CHECKING ORDER PROCESSING ***")
                    self.logger.info(f"  Strategy has notify_order method: {hasattr(self, 'notify_order')}")
                    self.logger.info(f"  Broker type: {type(self.broker)}")
                    self.logger.info(f"  Broker has _orders: {hasattr(self.broker, '_orders')}")
                    
                    if hasattr(self.broker, '_orders'):
                        pending_orders = [o for o in self.broker._orders if o.alive()]
                        self.logger.info(f"  Broker pending orders count: {len(pending_orders)}")
                        for i, pending_order in enumerate(pending_orders):
                            self.logger.info(f"    Pending order {i}: {pending_order.ref} - {pending_order.getstatusname()}")
                    
                except Exception as e:
                    self.logger.error(f"*** BUY ORDER PLACEMENT FAILED ***")
                    self.logger.error(f"  Error: {e}")
                    import traceback
                    self.logger.error(f"  Traceback: {traceback.format_exc()}")
                
            elif (signal_direction == 'SELL' and filters_pass):
                
                self.sell_signal_count += 1
                self.logger.info(f"SELL SIGNAL TRIGGERED #{self.sell_signal_count}")
                
                # Calculate position size with hybrid confidence
                pa_confidence = signals.get('price_action_details', {}).get('confidence', 0.5)
                tech_confidence = signals.get('confidence', 0.5)
                position_size = self.calculate_dynamic_position_size(
                    signal_strength, current_vol, pa_confidence, tech_confidence
                )
                
                self.logger.info(f"Position sizing:")
                self.logger.info(f"  Size: {position_size:.6f}")
                
                self.log(f'SELL SIGNAL - Buy: {buy_score:.3f}, Sell: {sell_score:.3f}, '
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
                    
                    # CRITICAL FIX: Use Market order with immediate execution
                    self.order = self.sell(size=position_size, exectype=bt.Order.Market)
                    self.entry_bar = len(self)
                    self.order_submitted_bar = len(self)  # Track when order was submitted
                    
                    self.logger.info(f"*** SELL ORDER SUBMITTED ***")
                    self.logger.info(f"  Order reference: {self.order.ref if self.order else 'None'}")
                    self.logger.info(f"  Order object: {self.order}")
                    
                    # Add portfolio value change and profit/loss information
                    current_portfolio_value = self.broker.get_value()
                    
                    # Use the most recent reference capital (updated after last completed order)
                    reference_capital = self.last_completed_portfolio_value
                    portfolio_change = current_portfolio_value - reference_capital
                    portfolio_change_pct = (portfolio_change / reference_capital) * 100 if reference_capital > 0 else 0
                    
                    # Get portfolio summary from tracker
                    portfolio_summary = self.portfolio_tracker.get_portfolio_summary()
                    
                    self.logger.info(f"*** PORTFOLIO VALUE AFTER SELL ORDER ***")
                    self.logger.info(f"  Reference Capital (Last Trade): ${reference_capital:.2f}")
                    self.logger.info(f"  Current Portfolio Value: ${current_portfolio_value:.2f}")
                    self.logger.info(f"  Expected Trade P&L: ${portfolio_change:.2f} ({portfolio_change_pct:+.2f}%)")
                    self.logger.info(f"  Realized P&L: ${portfolio_summary['realized_pnl']:.2f}")
                    self.logger.info(f"  Unrealized P&L: ${portfolio_summary['unrealized_pnl']:.2f}")
                    self.logger.info(f"  Net P&L: ${portfolio_summary['net_pnl']:.2f}")
                    
                    if portfolio_change > 0:
                        self.logger.info(f"*** EXPECTED PROFIT: ${portfolio_change:.2f} (+{portfolio_change_pct:.2f}%) ***")
                    elif portfolio_change < 0:
                        self.logger.info(f"*** EXPECTED LOSS: ${portfolio_change:.2f} ({portfolio_change_pct:.2f}%) ***")
                    else:
                        self.logger.info(f"*** EXPECTED BREAK EVEN: ${portfolio_change:.2f} (0.00%) ***")
                    
                    # CRITICAL: Check if notify_order callback will be triggered
                    self.logger.info(f"*** CHECKING ORDER PROCESSING ***")
                    self.logger.info(f"  Strategy has notify_order method: {hasattr(self, 'notify_order')}")
                    self.logger.info(f"  Broker type: {type(self.broker)}")
                    self.logger.info(f"  Broker has _orders: {hasattr(self.broker, '_orders')}")
                    
                    if hasattr(self.broker, '_orders'):
                        pending_orders = [o for o in self.broker._orders if o.alive()]
                        self.logger.info(f"  Broker pending orders count: {len(pending_orders)}")
                        for i, pending_order in enumerate(pending_orders):
                            self.logger.info(f"    Pending order {i}: {pending_order.ref} - {pending_order.getstatusname()}")
                    
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
                    self.logger.info(f"  Buy score: {buy_score:.4f}, Sell score: {sell_score:.4f}")
                    self.logger.info(f"  Signal direction: {signal_direction}")
                    self.logger.info(f"  Filters pass: {filters_pass}")
                    if not signals['volatility_filter']:
                        self.logger.info(f"  Volatility filter failed: current_vol={current_vol:.6f}")
                    if not signals['regime_filter']:
                        self.logger.info(f"  Regime filter failed: regime={self.current_regime}")
                
        else:  # In position
            if self.next_call_count <= 10 or self.next_call_count % 100 == 0:
                self.logger.info(f"=== POSITION MANAGEMENT ===")
                self.logger.info(f"Current position size: {self.position.size}")
                self.logger.info(f"Entry price: {self.buyprice}")
                self.logger.info(f"Current P&L: {(current_price - self.buyprice) * self.position.size if self.buyprice else 0:.2f}")
            
            self._manage_position_advanced(current_vol, signals)

    def calculate_dynamic_risk_reward(self, signal_strength, volatility, regime):
        """Dynamic risk/reward optimization for maximum portfolio growth"""

        # 1. Base risk per trade (portfolio-based)
        portfolio_risk_limit = self._calculate_portfolio_risk_limit()
        base_risk = min(portfolio_risk_limit, 0.02)  # Max 2% per trade

        # 2. Dynamic reward multiplier based on signal quality
        reward_multiplier = 2.0 + (signal_strength * 3.0)  # 2.0 to 5.0 range

        # 3. Regime-based adjustments
        regime_adjustments = {
            'bullish_trend': {'risk': 1.2, 'reward': 1.5},    # Higher risk/reward in trends
            'bearish_trend': {'risk': 1.2, 'reward': 1.5},
            'high_volatility': {'risk': 0.8, 'reward': 1.2},  # Conservative in high vol
            'mean_reverting': {'risk': 1.0, 'reward': 2.0},   # Higher reward in ranging
            'neutral': {'risk': 1.0, 'reward': 1.8}
        }

        adjustments = regime_adjustments.get(self.current_regime, {'risk': 1.0, 'reward': 1.8})

        # 4. Volatility adjustments
        vol_risk_multiplier = max(0.5, 1.0 - (volatility * 2))    # Reduce risk in high vol
        vol_reward_multiplier = min(2.0, 1.0 + (volatility * 1))  # Increase reward in high vol

        # 5. Calculate final stop and target distances
        adjusted_risk = base_risk * adjustments['risk'] * vol_risk_multiplier
        adjusted_reward = reward_multiplier * adjustments['reward'] * vol_reward_multiplier

        stop_distance = adjusted_risk
        target_distance = stop_distance * adjusted_reward

        # 6. Implement partial profit taking for large moves
        if adjusted_reward > 3.0:
            self._setup_partial_profit_taking(target_distance, stop_distance)

        return stop_distance, target_distance

    def optimize_trailing_stops(self, position_type, entry_price, current_price):
        """Advanced trailing stop system for maximum profit capture"""

        # 1. Profit-based trailing activation
        profit_pct = abs(current_price - entry_price) / entry_price

        if profit_pct < 0.005:  # Less than 0.5% profit
            return None  # No trailing stop yet

        # 2. Dynamic trailing distance based on profit level
        if profit_pct < 0.01:  # 0.5% to 1% profit
            trail_pct = 0.003  # Tight trailing
        elif profit_pct < 0.02:  # 1% to 2% profit
            trail_pct = 0.005  # Moderate trailing
        elif profit_pct < 0.05:  # 2% to 5% profit
            trail_pct = 0.008  # Looser trailing
        else:  # Over 5% profit
            trail_pct = 0.012  # Very loose trailing

        # 3. Calculate trailing stop price
        if position_type == 'long':
            trail_price = current_price * (1 - trail_pct)
        else:  # short
            trail_price = current_price * (1 + trail_pct)

        return trail_price

    def _calculate_portfolio_risk_limit(self):
        """Calculate portfolio-based risk limit per trade"""
        portfolio_value = self.broker.get_value()
        return min(0.02, 1000 / portfolio_value)  # Max $1000 risk or 2%

    def _setup_partial_profit_taking(self, target_distance, stop_distance):
        """Setup partial profit taking for large moves"""
        # This would implement scaling out of positions
        # For now, just log the setup
        self.logger.info(f"Partial profit taking setup: target={target_distance:.6f}, stop={stop_distance:.6f}")

    def _manage_position_advanced(self, volatility: float, signals: Dict[str, Any]):
        """Enhanced position management with dynamic risk/reward optimization"""
        current_price = self.dataclose[0]

        # Get dynamic risk/reward parameters
        signal_strength = max(signals['buy_score'], signals['sell_score'])
        stop_distance, target_distance = self.calculate_dynamic_risk_reward(
            signal_strength, volatility, self.current_regime
        )

        if self.position.size > 0:  # Long position
            # Dynamic stop loss
            stop_price = self.buyprice * (1 - stop_distance)
            target_price = self.buyprice * (1 + target_distance)

            # Advanced trailing stop
            trailing_stop_price = self.optimize_trailing_stops('long', self.buyprice, current_price)

            # Profit-based position scaling
            current_profit_pct = (current_price - self.buyprice) / self.buyprice

            # Enhanced regime-based exit adjustments
            if self.current_regime == 'bearish_trend' and self.regime_confidence > 0.6:
                if current_profit_pct > 0.003:
                    self.log('REGIME EXIT (LONG) - Bearish trend detected')
                    self.close()
                    return

            # Enhanced signal-based exit
            if signals['sell_score'] > 0.6:
                self.log('SIGNAL EXIT (LONG) - Strong sell signal')
                self.close()
                return

            # Dynamic exits with trailing stop
            if current_price <= stop_price:
                self.log(f'STOP LOSS (LONG) - Price: {current_price:.5f}')
                self.close()
            elif current_price >= target_price:
                self.log(f'TAKE PROFIT (LONG) - Price: {current_price:.5f}')
                self.close()
            elif trailing_stop_price and current_price <= trailing_stop_price:
                self.log(f'ADVANCED TRAILING STOP (LONG) - Price: {current_price:.5f}')
                self.close()

        elif self.position.size < 0:  # Short position
            # Dynamic stop loss for short
            stop_price = self.buyprice * (1 + stop_distance)
            target_price = self.buyprice * (1 - target_distance)

            # Advanced trailing stop for short
            trailing_stop_price = self.optimize_trailing_stops('short', self.buyprice, current_price)

            # Profit calculation for short
            current_profit_pct = (self.buyprice - current_price) / self.buyprice

            # Enhanced regime-based exit adjustments
            if self.current_regime == 'bullish_trend' and self.regime_confidence > 0.6:
                if current_profit_pct > 0.003:
                    self.log('REGIME EXIT (SHORT) - Bullish trend detected')
                    self.close()
                    return

            # Enhanced signal-based exit
            if signals['buy_score'] > 0.6:
                self.log('SIGNAL EXIT (SHORT) - Strong buy signal')
                self.close()
                return

            # Dynamic exits with trailing stop
            if current_price >= stop_price:
                self.log(f'STOP LOSS (SHORT) - Price: {current_price:.5f}')
                self.close()
            elif current_price <= target_price:
                self.log(f'TAKE PROFIT (SHORT) - Price: {current_price:.5f}')
                self.close()
            elif trailing_stop_price and current_price >= trailing_stop_price:
                self.log(f'ADVANCED TRAILING STOP (SHORT) - Price: {current_price:.5f}')
                self.close()

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
        
        # Enhanced broker state logging with portfolio debugging
        self.logger.info(f"=== BROKER STATE ANALYSIS ===")
        broker_cash = self.broker.get_cash()
        broker_value = self.broker.get_value()
        self.logger.info(f"Broker cash: {broker_cash:.2f}")
        self.logger.info(f"Broker value: {broker_value:.2f}")
        
        # Debug portfolio calculation
        if self.position:
            position_value = self.position.size * self.dataclose[0]
            total_calculated = broker_cash + position_value
            self.logger.info(f"Position size: {self.position.size}")
            self.logger.info(f"Position price: {self.position.price:.5f}")
            self.logger.info(f"Current market price: {self.dataclose[0]:.5f}")
            self.logger.info(f"Position market value: {position_value:.2f}")
            self.logger.info(f"Calculated total (cash + position): {total_calculated:.2f}")
            self.logger.info(f"Broker reported value: {broker_value:.2f}")
            self.logger.info(f"Value discrepancy: {abs(total_calculated - broker_value):.2f}")
        else:
            self.logger.info(f"No position - cash should equal value")
            self.logger.info(f"Cash vs Value discrepancy: {abs(broker_cash - broker_value):.2f}")
        
        if order.status in [order.Submitted, order.Accepted]:
            self.logger.info(f"*** ORDER {order.getstatusname().upper()}: {order}")
            self.logger.info(f"*** Order is alive: {order.alive()}")
            self.logger.info(f"*** Waiting for execution...")
            
            # Enhanced diagnostics for accepted orders that don't execute
            if order.status == order.Accepted:
                self.logger.warning(f"*** ORDER ACCEPTED BUT NOT EXECUTING ***")
                self.logger.warning(f"  Order ref: {order.ref}")
                self.logger.warning(f"  Order size: {order.size}")
                self.logger.warning(f"  Order type: {order.ordtype}")
                self.logger.warning(f"  Current price: {self.dataclose[0]:.5f}")
                self.logger.warning(f"  Order price: {order.price if order.price else 'Market'}")
                
                # Check broker state for execution issues
                self.logger.warning(f"  Broker cash: {self.broker.get_cash():.2f}")
                self.logger.warning(f"  Required cash: {order.size * self.dataclose[0]:.2f}")
                self.logger.warning(f"  Cash sufficient: {self.broker.get_cash() >= order.size * self.dataclose[0]}")
                
                # Check if this is a market data issue
                try:
                    current_bar_time = self.datas[0].datetime.datetime(0)
                    self.logger.warning(f"  Current bar time: {current_bar_time}")
                    self.logger.warning(f"  Data available: {len(self.data)} bars")
                    self.logger.warning(f"  Price data valid: {self.dataclose[0] > 0}")
                except Exception as time_error:
                    self.logger.error(f"  Time/data error: {time_error}")
                
                # Check for broker execution issues
                if hasattr(self.broker, '_orders'):
                    pending_orders = len([o for o in self.broker._orders if o.alive()])
                    self.logger.warning(f"  Broker pending orders: {pending_orders}")
                
                # Log order execution requirements
                self.logger.warning(f"*** POTENTIAL EXECUTION BLOCKERS ***")
                self.logger.warning(f"  1. Insufficient liquidity at current price")
                self.logger.warning(f"  2. Market closed or no trading session")
                self.logger.warning(f"  3. Broker execution engine not processing orders")
                self.logger.warning(f"  4. Order size too small for execution")
                self.logger.warning(f"  5. Data feed synchronization issues")
            
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
                
            # Enhanced portfolio impact analysis with FORCED VALUE CORRECTION
            self.logger.info(f"*** POST-EXECUTION PORTFOLIO STATE ***")
            new_cash = self.broker.get_cash()
            new_value = self.broker.get_value()
            self.logger.info(f"  New broker cash: {new_cash:.2f}")
            self.logger.info(f"  New broker value: {new_value:.2f}")
            self.logger.info(f"  New position size: {self.position.size}")
            
            # Update portfolio tracker with execution details
            if order.isbuy():
                self.portfolio_tracker.update_cash(new_cash)
                self.portfolio_tracker.add_position(
                    symbol="EUR_USD",  # Assuming EUR_USD for forex
                    size=order.executed.size,
                    entry_price=order.executed.price,
                    commission=order.executed.comm
                )
            else:  # sell order
                self.portfolio_tracker.close_position(
                    symbol="EUR_USD",
                    exit_price=order.executed.price,
                    commission=order.executed.comm
                )
            
            # Get correct portfolio value from tracker
            correct_portfolio_value = self.portfolio_tracker.get_total_portfolio_value()
            portfolio_summary = self.portfolio_tracker.get_portfolio_summary()
            
            # Calculate portfolio change since last completed trade
            reference_capital = self.last_completed_portfolio_value
            portfolio_change = correct_portfolio_value - reference_capital
            portfolio_change_pct = (portfolio_change / reference_capital) * 100 if reference_capital > 0 else 0
            
            self.logger.info(f"*** PORTFOLIO VALUE TRACKER RESULTS ***")
            self.logger.info(f"  Tracker portfolio value: ${correct_portfolio_value:.2f}")
            self.logger.info(f"  Tracker total return: {portfolio_summary['total_return']:.2f}%")
            self.logger.info(f"  Tracker unrealized P&L: ${portfolio_summary['unrealized_pnl']:.2f}")
            self.logger.info(f"  Tracker realized P&L: ${portfolio_summary['realized_pnl']:.2f}")
            
            self.logger.info(f"*** FINAL PORTFOLIO VALUE CHANGE AFTER ORDER EXECUTION ***")
            self.logger.info(f"  Previous Reference Capital: ${reference_capital:.2f}")
            self.logger.info(f"  Current Portfolio Value: ${correct_portfolio_value:.2f}")
            self.logger.info(f"  Trade P&L: ${portfolio_change:.2f} ({portfolio_change_pct:+.2f}%)")
            self.logger.info(f"  Net P&L: ${portfolio_summary['net_pnl']:.2f}")
            
            if portfolio_change > 0:
                self.logger.info(f"*** TRADE RESULT: PROFIT ${portfolio_change:.2f} (+{portfolio_change_pct:.2f}%) ***")
            elif portfolio_change < 0:
                self.logger.info(f"*** TRADE RESULT: LOSS ${portfolio_change:.2f} ({portfolio_change_pct:.2f}%) ***")
            else:
                self.logger.info(f"*** TRADE RESULT: BREAK EVEN ${portfolio_change:.2f} (0.00%) ***")
            
            # Update reference capital for next trade
            old_reference = self.last_completed_portfolio_value
            self.last_completed_portfolio_value = correct_portfolio_value
            self.logger.info(f"*** REFERENCE CAPITAL UPDATE ***")
            self.logger.info(f"  Old Reference: ${old_reference:.2f}")
            self.logger.info(f"  New Reference: ${self.last_completed_portfolio_value:.2f}")
            self.logger.info(f"  Change: ${self.last_completed_portfolio_value - old_reference:.2f}")
            self.logger.info(f"*** UPDATED REFERENCE CAPITAL FOR NEXT TRADE: ${self.last_completed_portfolio_value:.2f} ***")
            
            # Force broker value correction if there's a discrepancy
            if abs(correct_portfolio_value - new_value) > 0.01:
                self.logger.error(f"*** BROKER VALUE DISCREPANCY DETECTED ***")
                self.logger.error(f"  Broker reported: ${new_value:.2f}")
                self.logger.error(f"  Correct value: ${correct_portfolio_value:.2f}")
                self.logger.error(f"  Discrepancy: ${abs(correct_portfolio_value - new_value):.2f}")
                
                # Force correct value
                success = self.portfolio_tracker.force_broker_value_update(self.broker)
                if success:
                    updated_value = self.broker.get_value()
                    self.logger.info(f"*** BROKER VALUE CORRECTED: ${updated_value:.2f} ***")
                else:
                    self.logger.error("*** FAILED TO CORRECT BROKER VALUE ***")
            else:
                self.logger.info(f"*** PORTFOLIO VALUES MATCH - NO CORRECTION NEEDED ***")
                
            self.log(f'ORDER EXECUTED - {order.getstatusname()} at {order.executed.price:.5f}')
            # Clear order reference after execution
            self.order = None
            if hasattr(self, 'order_submitted_bar'):
                delattr(self, 'order_submitted_bar')
            
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