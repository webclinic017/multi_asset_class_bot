"""
Advanced Quantitative Crypto Trading Strategy
Institutional-grade strategy with sophisticated quantitative techniques
"""

import backtrader as bt
import numpy as np
import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
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
            @staticmethod
            def ATR(*args, **kwargs):
                return None
            @staticmethod
            def STOCH(*args, **kwargs):
                return None, None
            @staticmethod
            def CCI(*args, **kwargs):
                return None
        talib = DummyTalib()
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import warnings
warnings.filterwarnings('ignore')

class AdvancedQuantCryptoStrategy(bt.Strategy):
    """
    Enhanced crypto trading strategy with:
    - Crypto-specific volatility regimes
    - On-chain metrics integration
    - Exchange flow analysis
    - Liquidity-based execution
    - Improved risk management for crypto
    """
    
    params = (
        # Enhanced Volatility Regime Detection
        ('vol_lookback', 14),  # Shorter lookback for crypto
        ('vol_threshold_low', 0.20),  # Higher thresholds for crypto
        ('vol_threshold_high', 0.40),
        
        # Crypto-Specific Momentum
        ('momentum_short', 3),  # Faster periods for crypto
        ('momentum_medium', 12),
        ('momentum_long', 36),
        ('momentum_threshold', 0.03),  # Higher threshold
        
        # Mean Reversion with Crypto Adjustments
        ('bb_period', 14),
        ('bb_std', 2.2),  # Wider bands for crypto
        ('rsi_period', 10),  # Shorter RSI
        ('rsi_oversold', 30),
        ('rsi_overbought', 70),
        
        # Enhanced Position Sizing
        ('kelly_lookback', 50),  # Shorter lookback
        ('max_kelly_fraction', 0.20),  # More conservative
        ('min_position_size', 0.02),
        ('max_position_size', 0.15),
        
        # Crypto Risk Management
        ('max_drawdown', 0.20),  # Higher tolerance
        ('var_confidence', 0.10),  # More conservative
        ('max_positions', 5),  # More positions allowed
        
        # Liquidity and Execution
        ('volume_ma_period', 14),
        ('liquidity_threshold', 0.0005),  # Tighter for crypto
        
        # On-Chain Metrics (placeholders)
        ('onchain_weight', 0.15),
        ('exchange_netflow_weight', 0.10),
        
        # Sentiment Analysis
        ('sentiment_weight', 0.25),
        ('sentiment_threshold', 0.15),
        
        # General
        ('printlog', True),
        ('debug_mode', False)
    )

    def __init__(self):
        """Initialize enhanced crypto strategy"""
        self.logger = logging.getLogger(__name__)
        
        # Basic price data
        self.dataclose = self.datas[0].close
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low
        self.dataopen = self.datas[0].open
        self.datavolume = self.datas[0].volume
        
        # Order and position management
        self.order = None
        self.position_entry_price = None
        self.position_entry_time = None
        
        # Performance tracking
        self.trade_count = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_pnl = 0.0
        self.max_drawdown_current = 0.0
        self.peak_value = 0.0
        
        # Volatility regime tracking
        self.current_regime = 'normal'
        self.regime_history = []
        
        # Momentum signals
        self.momentum_signals = {'short': 0, 'medium': 0, 'long': 0}
        
        # Kelly Criterion data
        self.trade_returns = []
        self.kelly_fraction = 0.1
        
        # Machine Learning
        self.ml_model = None
        self.ml_features = []
        self.ml_predictions = []
        self.bars_since_retrain = 0
        
        # Market microstructure
        self.volume_profile = []
        self.liquidity_zones = []
        
        # ML feature names (moved from _init_ml_features)
        self.feature_names = [
            'returns_1', 'returns_5', 'returns_20',
            'volatility', 'volume_ratio', 'rsi', 'macd_signal',
            'bb_position', 'momentum_short', 'momentum_long',
            'stoch_k', 'williams_r', 'cci', 'atr_ratio'
        ]
        
        # Track initialization state
        self.initialized = False
        self.required_bars = max(
            self.p.vol_lookback,
            self.p.momentum_long,
            self.p.bb_period,
            self.p.rsi_period,
            self.p.volume_ma_period,
            14  # MACD default period
        ) + 10
        
        self.logger.info(f"Strategy initialized - waiting for {self.required_bars} bars of data")

    def _init_indicators(self):
        """Initialize enhanced indicators with safety checks"""
        try:
            # Calculate max required period
            max_period = max(
                self.p.vol_lookback,
                self.p.momentum_long,
                self.p.bb_period,
                self.p.rsi_period,
                self.p.volume_ma_period,
                14  # MACD default period
            )
            
            # Wait until we have enough data
            required_bars = max_period + 10
            if len(self.data) < required_bars:
                self.logger.warning(f"Not enough data to initialize indicators (have {len(self.data)}, need {required_bars} bars)")
                # Don't disable strategy - just wait for more data
                return True
                
            # Volatility indicators
            self.atr = bt.indicators.ATR(period=self.p.vol_lookback)
            self.volatility = bt.indicators.StdDev(self.dataclose, period=self.p.vol_lookback)
            
            # Momentum indicators
            self.momentum_short = bt.indicators.Momentum(period=self.p.momentum_short)
            self.momentum_medium = bt.indicators.Momentum(period=self.p.momentum_medium)
            self.momentum_long = bt.indicators.Momentum(period=self.p.momentum_long)
            
            # Mean reversion indicators
            self.bollinger = bt.indicators.BollingerBands(period=self.p.bb_period, devfactor=self.p.bb_std)
            self.rsi = bt.indicators.RSI(period=self.p.rsi_period)
            
            # Volume and liquidity indicators
            self.volume_ma = bt.indicators.SMA(self.datavolume, period=self.p.volume_ma_period)
            self.volume_ratio = self.datavolume / self.volume_ma
            
            # Additional indicators
            self.macd = bt.indicators.MACD()
            self.stochastic = bt.indicators.Stochastic()
            self.cci = bt.indicators.CommodityChannelIndex()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Indicator initialization failed: {e}")
            return False

    def next(self):
        """Enhanced crypto trading logic with detailed logging"""
        # Skip if we don't have enough data yet
        if len(self.data) < self.required_bars:
            self.logger.info(f"Waiting for data - have {len(self.data)} bars, need {self.required_bars}")
            return
            
        # Initialize indicators if not done yet
        if not hasattr(self, 'initialized'):
            try:
                if self._init_indicators():
                    self.initialized = True
                    self.logger.info(f"Strategy initialized with {len(self.data)} bars")
                    # Detailed indicator validation
                    self.logger.info("Indicator Values:")
                    self.logger.info(f"Close: {self.dataclose[0]:.4f}")
                    self.logger.info(f"RSI: {self.rsi[0]:.2f} (Oversold: {self.p.rsi_oversold}, Overbought: {self.p.rsi_overbought})")
                    self.logger.info(f"MACD: {self.macd.macd[0]:.4f} Signal: {self.macd.signal[0]:.4f}")
                    self.logger.info(f"Bollinger: Upper {self.bollinger.top[0]:.4f} Lower {self.bollinger.bot[0]:.4f}")
                    self.logger.info(f"ATR: {self.atr[0]:.4f} Volatility: {self.volatility[0]:.4f}")
                else:
                    self.logger.error("Indicator initialization failed")
                    return
            except Exception as e:
                self.logger.error(f"Initialization error: {str(e)}", exc_info=True)
                return

        # Only proceed if fully initialized with valid indicators
        if not self.initialized or any(ind[0] is None for ind in [self.rsi, self.macd, self.bollinger]):
            self.logger.warning("Not initialized or invalid indicators")
            return
            
        # Log current market state
        self.logger.info(f"Current Market - Close: {self.dataclose[0]:.4f} Vol: {self.volatility[0]:.4f} Regime: {self.current_regime}")

        # Main trading logic
        try:
            # Update market state
            self._update_volatility_regime()
            self._update_momentum_signals()
            
            # Generate trading signal
            signal = self._generate_composite_signal()
            if signal is None:
                return
                
            # Calculate position size
            position_size = self._calculate_kelly_position_size()
            
            # Execute trade if signal is valid
            self._execute_trades(signal, position_size)
            
        except Exception as e:
            self.logger.error(f"Trading error: {str(e)}")

        # Main trading logic here
        try:
            self._update_volatility_regime()
            self._update_momentum_signals()
            self._update_kelly_criterion()
            
            if len(self.data) >= self.p.ml_lookback:
                if self.bars_since_retrain >= 30:
                    self._retrain_ml_model()
                    self.bars_since_retrain = 0
                else:
                    self.bars_since_retrain += 1
            
            ml_signal = self._get_ml_prediction()
            position_size = self._calculate_kelly_position_size()
            
            if not self._risk_management_check():
                return
                
            signal = self._generate_composite_signal(ml_signal)
            self._execute_trades(signal, position_size)
            self._update_performance_metrics()
            
        except Exception as e:
            self.logger.warning(f"Trading error: {e}")
            
        try:
            # Update all components
            self._update_volatility_regime()
            self._update_momentum_signals()
            self._update_kelly_criterion()
            
            # ML updates
            if len(self.data) >= self.p.ml_lookback:
                if self.bars_since_retrain >= 30:  # More frequent retraining
                    self._retrain_ml_model()
                    self.bars_since_retrain = 0
                else:
                    self.bars_since_retrain += 1
            
            # Generate signals
            ml_signal = self._get_ml_prediction()
            position_size = self._calculate_kelly_position_size()
            
            if not self._risk_management_check():
                return
                
            signal = self._generate_composite_signal(ml_signal)
            self._execute_trades(signal, position_size)
            self._update_performance_metrics()
            
        except Exception as e:
            self.logger.warning(f"Strategy error: {e}")

    def _update_volatility_regime(self):
        """Enhanced crypto volatility regime detection"""
        current_vol = self.volatility[0]
        
        if current_vol < self.p.vol_threshold_low:
            regime = 'low'
        elif current_vol > self.p.vol_threshold_high:
            regime = 'high'
        else:
            regime = 'normal'
        
        if regime != self.current_regime:
            self.log(f'Volatility regime change: {self.current_regime} -> {regime}')
            self.current_regime = regime
        
        self.regime_history.append(regime)
        if len(self.regime_history) > 50:  # Shorter memory for crypto
            self.regime_history.pop(0)

    def _execute_trades(self, signal, position_size):
        """Enhanced execution for crypto markets"""
        if self.order:
            return
            
        current_price = self.dataclose[0]
        cash = self.broker.get_cash()
        
        # Enhanced position sizing with min/max constraints
        position_size = max(self.p.min_position_size,
                          min(position_size, self.p.max_position_size))
        
        # Adjust position size based on liquidity and volatility
        liquidity_factor = min(1.0, self.volume_ratio[0] / 2.0)
        volatility_factor = 1.0 - min(0.5, self.volatility[0] / 0.1)  # Reduce size in high vol
        position_size *= liquidity_factor * volatility_factor
        
        if signal == 1 and not self.position:
            position_value = cash * position_size
            shares = int(position_value / current_price)
            
            if shares > 0:
                self.order = self.buy(size=shares)
                self.log(f'BUY CREATE - Size: {shares}, Vol Regime: {self.current_regime}')
                self.position_entry_price = current_price
                self.position_entry_time = len(self.data)
                
        elif signal == -1 and self.position:
            self.order = self.close()
            self.log('SELL CREATE - Signal')
            # Track trade performance
            self._update_trade_stats(current_price)
            
        # Crypto-specific stop logic
        elif self.position and self.position_entry_price:
            pnl_pct = (current_price - self.position_entry_price) / self.position_entry_price
            
            # Wider stops in high volatility
            if self.current_regime == 'high':
                stop_loss = -0.05
                take_profit = 0.10
            else:
                stop_loss = -0.03
                take_profit = 0.06
                
            if pnl_pct <= stop_loss:
                self.order = self.close()
                self.log(f'STOP LOSS at {pnl_pct:.2%}')
            elif pnl_pct >= take_profit:
                self.order = self.close()
                self.log(f'TAKE PROFIT at {pnl_pct:.2%}')

    def log(self, txt, dt=None):
        """Robust logging function that works even when data isn't available"""
        try:
            if self.p.printlog:
                dt = dt or (self.datas[0].datetime.date(0) if len(self.data) > 0 else datetime.now().date())
                self.logger.info(f'{dt.isoformat()} {txt}')
        except Exception:
            # Fallback to simple logging if date access fails
            self.logger.info(str(txt))

    def stop(self):
        """Enhanced performance reporting"""
        try:
            final_value = self.broker.get_value()
            initial_capital = 10000
            total_return = ((final_value - initial_capital) / initial_capital) * 100
            win_rate = (self.winning_trades / max(self.trade_count, 1)) * 100
            
            self.log('=== ENHANCED CRYPTO STRATEGY RESULTS ===')
            self.log(f'Final Value: ${final_value:.2f}')
            self.log(f'Total Return: {total_return:.2f}%')
            self.log(f'Win Rate: {win_rate:.1f}%')
            self.log(f'Final Vol Regime: {self.current_regime}')
            self.log(f'Final Kelly Fraction: {self.kelly_fraction:.3f}')
        except Exception as e:
            self.logger.error(f"Error generating final report: {e}")

# Keep all other existing methods unchanged
# [Previous implementation of other methods remains the same]