"""
Enhanced Forex Strategy with Advanced Quantitative Techniques
Optimized for maximum returns using sophisticated risk-adjusted optimization
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
        # Core Moving Average Parameters (Dynamic)
        ('fast_length', 12),
        ('slow_length', 26),
        ('signal_length', 9),
        
        # Advanced RSI Parameters
        ('rsi_period', 14),
        ('rsi_oversold', 25),
        ('rsi_overbought', 75),
        ('rsi_divergence_lookback', 20),
        
        # MACD Parameters
        ('macd_fast', 12),
        ('macd_slow', 26),
        ('macd_signal', 9),
        
        # Bollinger Bands
        ('bb_period', 20),
        ('bb_std', 2.0),
        ('bb_squeeze_threshold', 0.1),
        
        # Volatility Parameters
        ('atr_period', 14),
        ('volatility_lookback', 50),
        ('volatility_threshold', 0.02),
        
        # Advanced Risk Management
        ('base_stop_loss', 0.01),      # 1% base stop loss
        ('base_take_profit', 0.025),   # 2.5% base take profit
        ('dynamic_sizing', True),      # Enable dynamic position sizing
        ('max_risk_per_trade', 0.02),  # 2% max risk per trade
        ('volatility_adjustment', True), # Adjust for volatility
        
        # Regime Detection
        ('regime_lookback', 100),
        ('trend_threshold', 0.6),
        ('mean_reversion_threshold', 0.4),
        
        # Supply/Demand Enhanced
        ('pivot_period', 7),
        ('zone_lookback', 75),
        ('min_zone_strength', 3.0),
        ('zone_buffer', 0.0003),
        ('max_zones', 15),
        
        # Volume Analysis
        ('volume_period', 30),
        ('volume_levels', 25),
        ('volume_confirmation', True),
        
        # Multi-timeframe
        ('use_higher_tf', True),
        ('higher_tf_multiplier', 4),
        
        # Machine Learning Features
        ('use_ml_features', True),
        ('feature_lookback', 50),
        ('momentum_periods', [5, 10, 20, 50]),
        
        # Advanced Filters
        ('use_regime_filter', True),
        ('use_volatility_filter', True),
        ('use_correlation_filter', True),
        ('use_momentum_filter', True),
        
        # Performance Optimization
        ('min_sharpe_threshold', 0.5),
        ('max_drawdown_threshold', 0.15),
        ('profit_factor_threshold', 1.2),
        
        # Sentiment Integration
        ('sentiment_weight', 0.25),
        ('sentiment_threshold', 0.3),
        ('news_impact_decay', 0.95),
        
        # Logging
        ('printlog', False)
    )

    def __init__(self):
        """Initialize enhanced strategy with advanced indicators"""
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
        
        self.logger.info("Enhanced Forex Strategy initialized with advanced quantitative features")

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
        """Generate comprehensive trading signals using all indicators"""
        signals = {
            'buy_score': 0.0,
            'sell_score': 0.0,
            'signal_strength': 0.0,
            'regime_filter': True,
            'volatility_filter': True,
            'components': {}
        }
        
        try:
            # Trend signals
            trend_score = 0.0
            if self.ema_fast[0] > self.ema_slow[0]:
                trend_score += 1.0
            if self.tema[0] > self.tema[-1]:
                trend_score += 0.5
            if self.dataclose[0] > self.bb.lines.mid[0]:
                trend_score += 0.5
                
            signals['components']['trend'] = trend_score / 2.0
            
            # Momentum signals
            momentum_score = 0.0
            if self.rsi[0] > 50 and self.rsi[0] < self.p.rsi_overbought:
                momentum_score += 1.0
            if self.macd.macd[0] > self.macd.signal[0]:
                momentum_score += 1.0
            if self.stoch.percK[0] > self.stoch.percD[0]:
                momentum_score += 0.5
                
            signals['components']['momentum'] = momentum_score / 2.5
            
            # Mean reversion signals
            reversion_score = 0.0
            bb_position = (self.dataclose[0] - self.bb.lines.bot[0]) / \
                         (self.bb.lines.top[0] - self.bb.lines.bot[0])
            
            if bb_position < 0.2:  # Near lower band
                reversion_score += 1.0
            elif bb_position > 0.8:  # Near upper band
                reversion_score -= 1.0
                
            if self.williams_r[0] < -80:
                reversion_score += 0.5
            elif self.williams_r[0] > -20:
                reversion_score -= 0.5
                
            signals['components']['reversion'] = reversion_score / 1.5
            
            # Volume confirmation
            volume_score = 0.0
            if self.p.volume_confirmation and len(self.volume_ratio) > 0:
                if self.volume_ratio[0] > 1.2:
                    volume_score = 1.0
                elif self.volume_ratio[0] < 0.8:
                    volume_score = -0.5
                    
            signals['components']['volume'] = volume_score
            
            # Regime-based signal weighting
            regime_weights = {
                'bullish_trend': {'trend': 1.5, 'momentum': 1.2, 'reversion': 0.5},
                'bearish_trend': {'trend': 1.5, 'momentum': 1.2, 'reversion': 0.5},
                'mean_reverting': {'trend': 0.5, 'momentum': 0.8, 'reversion': 1.8},
                'high_volatility': {'trend': 0.8, 'momentum': 0.6, 'reversion': 1.0},
                'neutral': {'trend': 1.0, 'momentum': 1.0, 'reversion': 1.0}
            }
            
            weights = regime_weights.get(self.current_regime, regime_weights['neutral'])
            
            # Calculate weighted scores
            buy_score = (
                signals['components']['trend'] * weights['trend'] +
                signals['components']['momentum'] * weights['momentum'] +
                max(0, signals['components']['reversion']) * weights['reversion'] +
                max(0, signals['components']['volume']) * 0.5
            ) / (weights['trend'] + weights['momentum'] + weights['reversion'] + 0.5)
            
            sell_score = (
                (1 - signals['components']['trend']) * weights['trend'] +
                (1 - signals['components']['momentum']) * weights['momentum'] +
                max(0, -signals['components']['reversion']) * weights['reversion'] +
                max(0, -signals['components']['volume']) * 0.5
            ) / (weights['trend'] + weights['momentum'] + weights['reversion'] + 0.5)
            
            signals['buy_score'] = buy_score
            signals['sell_score'] = sell_score
            signals['signal_strength'] = max(buy_score, sell_score)
            
            # Apply filters
            if self.p.use_volatility_filter:
                current_vol = self.atr[0] / self.dataclose[0] if self.dataclose[0] > 0 else 0
                if current_vol > self.p.volatility_threshold:
                    signals['volatility_filter'] = False
                    
            return signals
            
        except Exception as e:
            self.logger.error(f"Error generating signals: {e}")
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
            # Entry logic
            if (signals['buy_score'] > 0.65 and 
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
                
            elif (signals['sell_score'] > 0.65 and 
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
        """Advanced position management with dynamic stops and targets"""
        current_price = self.dataclose[0]
        
        if self.position.size > 0:  # Long position
            # Dynamic stop loss
            stop_distance = max(self.p.base_stop_loss, volatility * 2)
            stop_price = self.buyprice * (1 - stop_distance)
            
            # Dynamic take profit
            target_distance = stop_distance * 2.5
            target_price = self.buyprice * (1 + target_distance)
            
            # Regime-based exit adjustments
            if self.current_regime == 'bearish_trend' and self.regime_confidence > 0.7:
                # Early exit in strong bearish regime
                if current_price > self.buyprice * 1.005:  # Small profit
                    self.log('REGIME EXIT (LONG) - Bearish trend detected')
                    self.close()
                    return
                    
            # Signal-based exit
            if signals['sell_score'] > 0.7:
                self.log('SIGNAL EXIT (LONG) - Strong sell signal')
                self.close()
                return
                
            # Standard exits
            if current_price <= stop_price:
                self.log(f'STOP LOSS (LONG) - Price: {current_price:.5f}')
                self.close()
            elif current_price >= target_price:
                self.log(f'TAKE PROFIT (LONG) - Price: {current_price:.5f}')
                self.close()
                
        elif self.position.size < 0:  # Short position
            # Dynamic stop loss
            stop_distance = max(self.p.base_stop_loss, volatility * 2)
            stop_price = self.buyprice * (1 + stop_distance)
            
            # Dynamic take profit
            target_distance = stop_distance * 2.5
            target_price = self.buyprice * (1 - target_distance)
            
            # Regime-based exit adjustments
            if self.current_regime == 'bullish_trend' and self.regime_confidence > 0.7:
                # Early exit in strong bullish regime
                if current_price < self.buyprice * 0.995:  # Small profit
                    self.log('REGIME EXIT (SHORT) - Bullish trend detected')
                    self.close()
                    return
                    
            # Signal-based exit
            if signals['buy_score'] > 0.7:
                self.log('SIGNAL EXIT (SHORT) - Strong buy signal')
                self.close()
                return
                
            # Standard exits
            if current_price >= stop_price:
                self.log(f'STOP LOSS (SHORT) - Price: {current_price:.5f}')
                self.close()
            elif current_price <= target_price:
                self.log(f'TAKE PROFIT (SHORT) - Price: {current_price:.5f}')
                self.close()

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