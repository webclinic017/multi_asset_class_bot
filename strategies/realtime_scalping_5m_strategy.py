"""
Real-time Scalping Strategy for 5-minute timeframe
Compatible with real-time broker logic like EnhancedForexStrategy
Optimized for medium-frequency scalping with immediate execution
"""

import backtrader as bt
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Tuple
from scipy import stats

class RealtimeScalping5MStrategy(bt.Strategy):
    """
    Real-time compatible 5-minute scalping strategy with enhanced broker integration
    Uses the same parameter structure as EnhancedForexStrategy for compatibility
    """
    
    params = (
        # Core Moving Average Parameters (compatible with EnhancedForexStrategy)
        ('fast_length', 8),           # Fast EMA for 5M scalping
        ('slow_length', 21),          # Fibonacci-based slow EMA
        ('signal_length', 5),         # Signal line
        
        # Enhanced RSI Parameters
        ('rsi_period', 14),           # Standard RSI for 5M
        ('rsi_oversold', 30),         # Scalping oversold level
        ('rsi_overbought', 70),       # Scalping overbought level
        ('rsi_divergence_lookback', 15), # Lookback for 5M
        
        # MACD Parameters
        ('macd_fast', 8),             # Fast MACD for 5M
        ('macd_slow', 21),            # Slow line
        ('macd_signal', 5),           # Signal line
        
        # Bollinger Bands for Scalping
        ('bb_period', 20),            # Period for 5M reactions
        ('bb_std', 2.0),              # Standard bands for scalping
        ('bb_squeeze_threshold', 0.1), # Squeeze detection
        
        # Volatility and ATR
        ('atr_period', 14),           # ATR for 5M scalping
        ('volatility_lookback', 30),  # Lookback
        ('volatility_threshold', 0.01), # Volatility threshold
        
        # Risk Management (compatible with enhanced strategy)
        ('base_stop_loss', 0.005),    # Stop loss for 5M (0.5%)
        ('base_take_profit', 0.015),  # 3:1 risk/reward ratio
        ('dynamic_sizing', True),     # Enable dynamic position sizing
        ('max_risk_per_trade', 0.02), # 2% risk per trade
        ('volatility_adjustment', True), # Adjust for volatility
        ('stop_loss_percent', 0.005), # Stop loss
        ('take_profit_percent', 0.015), # Take profit
        ('trailing_stop_percent', 0.003), # Trailing stop
        ('position_size_percent', 0.03), # 3% position size
        ('max_position_size', 0.06),  # Maximum position size
        ('min_volatility', 0.0001),   # Minimum volatility
        ('max_volatility', 0.015),    # Maximum volatility
        ('trend_strength_threshold', 0.4), # Threshold for more trades
        
        # Regime Detection (adapted for 5M)
        ('regime_lookback', 100),     # Lookback for 5M
        ('trend_threshold', 0.5),     # Threshold for trend detection
        ('mean_reversion_threshold', 0.4), # Threshold for mean reversion
        
        # Volume Analysis
        ('volume_period', 20),        # Volume period for 5M
        ('volume_levels', 30),        # Volume levels
        ('volume_confirmation', True), # Keep volume confirmation
        
        # Machine Learning Features
        ('use_ml_features', True),
        ('feature_lookback', 50),     # Feature lookback for 5M
        ('momentum_periods', [5, 10, 20, 34]), # Periods for 5M
        
        # Filters
        ('use_regime_filter', True),
        ('use_volatility_filter', True),
        ('use_correlation_filter', False),
        ('use_momentum_filter', True),
        
        # Performance Optimization for 5M data
        ('min_sharpe_threshold', 0.1), # Threshold for 5M data
        ('max_drawdown_threshold', 0.3), # Allow drawdown for 5M data
        ('profit_factor_threshold', 0.8), # Threshold for more trades
        
        # Advanced Scalping Features
        ('momentum_acceleration', 1.4), # Acceleration for 5M
        ('trend_following_boost', 1.3), # Trend following boost
        ('breakout_multiplier', 1.6),   # Breakout multiplier for 5M
        ('mean_reversion_factor', 0.8), # Mean reversion strength
        ('volatility_expansion_threshold', 1.2), # Volatility expansion detection
        
        # Scalping-specific parameters
        ('scalping_mode', True),      # Enable scalping mode
        ('max_trades_per_hour', 8),   # Trade frequency for 5M
        ('min_time_between_trades', 120), # 2 minutes minimum between trades
        ('quick_exit_threshold', 0.003), # Quick exit at 0.3% profit
        ('momentum_exit_threshold', 0.002), # Exit on momentum loss
        
        # Logging
        ('printlog', False)
    )

    def __init__(self):
        """Initialize 5M scalping strategy with real-time broker compatibility"""
        self.logger = logging.getLogger(__name__)
        
        # Initialize portfolio value tracker for accurate portfolio tracking
        from execution.portfolio_value_tracker import get_portfolio_tracker
        self.portfolio_tracker = get_portfolio_tracker(10000.0)
        
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
        self.initial_capital = self.broker.get_cash()  # Store initial capital for profit/loss calculations
        self.last_completed_portfolio_value = self.broker.get_cash()  # Initialize reference capital
        
        # Scalping-specific tracking
        self.last_trade_time = None
        self.trades_this_hour = 0
        self.last_hour = None
        self.quick_exits = 0
        
        # Initialize core indicators
        self._init_core_indicators()
        
        # Market regime tracking
        self.current_regime = 'neutral'
        self.regime_confidence = 0.0
        
        self.logger.info(f"Realtime 5M Scalping Strategy initialized")

    def _init_core_indicators(self):
        """Initialize core technical indicators for 5M scalping"""
        # EMAs for scalping
        self.ema_fast = bt.indicators.EMA(period=self.p.fast_length)
        self.ema_slow = bt.indicators.EMA(period=self.p.slow_length)
        self.sma_signal = bt.indicators.SMA(period=self.p.signal_length)
        
        # RSI
        self.rsi = bt.indicators.RSI(period=self.p.rsi_period)
        
        # MACD
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
        
        # Stochastic for momentum
        self.stoch = bt.indicators.Stochastic(period=14, period_dfast=3)
        
        # Volume indicators
        self.volume_sma = bt.indicators.SMA(self.datavolume, period=self.p.volume_period)
        self.volume_ratio = self.datavolume / bt.indicators.Max(self.volume_sma, 1e-8)

    def detect_market_regime(self) -> Tuple[str, float]:
        """Detect current market regime for 5M scalping"""
        current_data_length = len(self.data)
        
        min_regime_data = 30  # Minimum for basic regime detection on 5M
        if current_data_length < min_regime_data:
            return 'neutral', 0.0
            
        try:
            lookback_period = min(current_data_length - 1, self.p.regime_lookback)
            lookback_period = max(lookback_period, min_regime_data)
            
            recent_closes = np.array([self.dataclose[-i] for i in range(lookback_period, 0, -1)])
            recent_returns = np.diff(np.log(recent_closes))
            
            x = np.arange(len(recent_closes))
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, recent_closes)
            
            volatility = np.std(recent_returns) * np.sqrt(288)  # Annualized for 5M data
            
            vol_window = min(15, len(recent_returns) // 2)
            if vol_window >= 5:
                vol_segments = [np.std(recent_returns[i:i+vol_window])
                               for i in range(0, len(recent_returns)-vol_window+1, max(1, vol_window//2))]
                vol_ma = np.mean(vol_segments) if vol_segments else volatility
            else:
                vol_ma = volatility
                
            vol_ratio = volatility / max(vol_ma, 1e-8) if vol_ma > 0 else 1.0
            
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
                confidence = 0.4 * data_confidence_factor
                
            return regime, confidence
            
        except Exception as e:
            self.logger.error(f"Error in regime detection: {e}")
            return 'neutral', 0.0

    def calculate_dynamic_position_size(self, signal_strength: float, volatility: float) -> float:
        """Calculate position size for 5M scalping"""
        if not self.p.dynamic_sizing:
            return 0.02  # Default size for 5M scalping
            
        try:
            win_rate = self.winning_trades / max(self.trade_count, 1)
            avg_win = 0.012  # Estimated average win for 5M scalping
            avg_loss = 0.005  # Estimated average loss for 5M scalping
            
            if win_rate > 0 and avg_loss > 0:
                kelly_fraction = (win_rate * avg_win - (1 - win_rate) * avg_loss) / max(avg_win, 1e-8)
                kelly_fraction = max(0, min(kelly_fraction, 0.2))  # Cap at 20% for 5M scalping
            else:
                kelly_fraction = 0.02  # Default 2% for 5M scalping
                
            signal_adjustment = signal_strength * 1.1
            vol_adjustment = 1.0 / (1.0 + volatility * 10)
            
            regime_adjustment = 1.0
            if self.current_regime == 'high_volatility':
                regime_adjustment = 0.6
            elif self.current_regime in ['bullish_trend', 'bearish_trend']:
                regime_adjustment = 1.2
                
            final_size = kelly_fraction * signal_adjustment * vol_adjustment * regime_adjustment
            max_size = self.p.max_risk_per_trade / max(volatility, 0.003)
            final_size = min(final_size, max_size)
            
            return max(final_size, 0.01)  # Minimum 1%
            
        except Exception as e:
            self.logger.error(f"Error calculating position size: {e}")
            return 0.02

    def generate_scalping_signals(self) -> Dict[str, Any]:
        """Generate scalping signals for 5M timeframe"""
        signals = {
            'buy_score': 0.0,
            'sell_score': 0.0,
            'signal_strength': 0.0,
            'regime_filter': True,
            'volatility_filter': True,
            'components': {}
        }
        
        try:
            current_price = self.dataclose[0]
            current_rsi = self.rsi[0]
            current_atr = self.atr[0]
            
            # Trend signals
            trend_score = 0.0
            if self.ema_fast[0] > self.ema_slow[0]:
                trend_score += 1.2
            
            if len(self.ema_fast) > 1 and self.ema_fast[0] > self.ema_fast[-1]:
                trend_score += 0.8
            
            if current_price > self.bb.lines.mid[0]:
                trend_score += 0.6
                
            trend_component = min(trend_score / 2.6, 1.0)
            signals['components']['trend'] = trend_component
            
            # Momentum signals
            momentum_score = 0.0
            
            if 35 < current_rsi < self.p.rsi_overbought:
                momentum_score += 1.2
            elif current_rsi < self.p.rsi_oversold:
                momentum_score += 1.5
            
            if self.macd.macd[0] > self.macd.signal[0]:
                momentum_score += 1.0
            
            if self.stoch.percK[0] > self.stoch.percD[0] and self.stoch.percK[0] < 80:
                momentum_score += 0.8
                
            momentum_component = min(momentum_score / 3.5, 1.0)
            signals['components']['momentum'] = momentum_component
            
            # Mean reversion
            reversion_score = 0.0
            bb_position = (current_price - self.bb.lines.bot[0]) / \
                         (self.bb.lines.top[0] - self.bb.lines.bot[0])
            
            if bb_position < 0.2:
                reversion_score += 1.2
            elif bb_position > 0.8:
                reversion_score -= 1.2
            elif bb_position < 0.35:
                reversion_score += 0.6
            elif bb_position > 0.65:
                reversion_score -= 0.6
            
            reversion_score *= self.p.mean_reversion_factor
            reversion_component = max(-1.0, min(reversion_score / 1.2, 1.0))
            signals['components']['reversion'] = reversion_component
            
            # Volume confirmation
            volume_score = 0.0
            if self.p.volume_confirmation and len(self.volume_ratio) > 0:
                volume_ratio_val = self.volume_ratio[0]
                
                if volume_ratio_val > 1.5:
                    volume_score = 1.2 * self.p.breakout_multiplier
                elif volume_ratio_val > 1.2:
                    volume_score = 0.8
                elif volume_ratio_val < 0.8:
                    volume_score = -0.5
                    
            volume_component = max(-1.0, min(volume_score, 1.0))
            signals['components']['volume'] = volume_component
            
            # Calculate weighted scores
            regime_weights = {
                'bullish_trend': {'trend': 1.8, 'momentum': 1.4, 'reversion': 0.4, 'volume': 1.2},
                'bearish_trend': {'trend': 1.8, 'momentum': 1.4, 'reversion': 0.4, 'volume': 1.2},
                'mean_reverting': {'trend': 0.4, 'momentum': 0.9, 'reversion': 2.0, 'volume': 0.8},
                'high_volatility': {'trend': 1.0, 'momentum': 0.7, 'reversion': 1.3, 'volume': 1.5},
                'neutral': {'trend': 1.2, 'momentum': 1.1, 'reversion': 1.0, 'volume': 1.0}
            }
            
            weights = regime_weights.get(self.current_regime, regime_weights['neutral'])
            
            buy_numerator = (
                signals['components']['trend'] * weights['trend'] +
                signals['components']['momentum'] * weights['momentum'] +
                max(0, signals['components']['reversion']) * weights['reversion'] +
                max(0, signals['components']['volume']) * weights['volume']
            )
            buy_denominator = (weights['trend'] + weights['momentum'] + weights['reversion'] + weights['volume'])
            buy_score = buy_numerator / buy_denominator
            
            sell_numerator = (
                (1 - signals['components']['trend']) * weights['trend'] +
                (1 - signals['components']['momentum']) * weights['momentum'] +
                max(0, -signals['components']['reversion']) * weights['reversion'] +
                max(0, -signals['components']['volume']) * weights['volume']
            )
            sell_denominator = buy_denominator
            sell_score = sell_numerator / sell_denominator
            
            signals['buy_score'] = buy_score
            signals['sell_score'] = sell_score
            signals['signal_strength'] = max(buy_score, sell_score)
            
            # Volatility filter
            if self.p.use_volatility_filter:
                current_vol = current_atr / current_price if current_price > 0 else 0
                vol_threshold = self.p.volatility_threshold * 1.5
                if current_vol > vol_threshold:
                    signals['volatility_filter'] = False
                    
            return signals
            
        except Exception as e:
            self.logger.error(f"Error generating scalping signals: {str(e)}")
            return signals

    def check_scalping_filters(self) -> bool:
        """Check scalping-specific filters for 5M"""
        try:
            current_time = self.datas[0].datetime.datetime(0)
            current_hour = current_time.hour
            
            if self.last_hour != current_hour:
                self.trades_this_hour = 0
                self.last_hour = current_hour
            
            if self.trades_this_hour >= self.p.max_trades_per_hour:
                return False
            
            if self.last_trade_time:
                time_diff = (current_time - self.last_trade_time).total_seconds()
                if time_diff < self.p.min_time_between_trades:
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error in scalping filters: {e}")
            return False

    def next(self):
        """Main 5M scalping logic with real-time broker compatibility"""
        if self.order:
            return
        
        if not self.check_scalping_filters():
            return
        
        basic_min_data = max(self.p.slow_length, self.p.bb_period, self.p.atr_period)
        if len(self.data) < basic_min_data:
            return
        
        self.current_regime, self.regime_confidence = self.detect_market_regime()
        signals = self.generate_scalping_signals()
        
        current_price = self.dataclose[0]
        current_vol = self.atr[0] / current_price if current_price > 0 else 0
        
        if not self.position:
            buy_score_ok = signals['buy_score'] > 0.15
            buy_vol_filter_ok = signals['volatility_filter']
            buy_regime_filter_ok = signals['regime_filter']
            
            sell_score_ok = signals['sell_score'] > 0.15
            sell_vol_filter_ok = signals['volatility_filter']
            sell_regime_filter_ok = signals['regime_filter']
            
            if (buy_score_ok and buy_vol_filter_ok and buy_regime_filter_ok):
                position_size = self.calculate_dynamic_position_size(
                    signals['signal_strength'], current_vol
                )
                
                self.log(f'5M SCALPING BUY - Score: {signals["buy_score"]:.3f}, '
                        f'Regime: {self.current_regime}, Size: {position_size:.3f}')
                
                try:
                    self.order = self.buy(size=position_size, exectype=bt.Order.Market)
                    self.entry_bar = len(self)
                    self.last_trade_time = self.datas[0].datetime.datetime(0)
                    self.trades_this_hour += 1
                    
                    # Add portfolio value change and profit/loss information
                    current_portfolio_value = self.broker.get_value()
                    portfolio_change = current_portfolio_value - self.initial_capital
                    portfolio_change_pct = (portfolio_change / self.initial_capital) * 100
                    
                    # Get portfolio summary from tracker
                    portfolio_summary = self.portfolio_tracker.get_portfolio_summary()
                    
                    self.logger.info(f"*** 5M REALTIME SCALPING PORTFOLIO VALUE AFTER BUY ORDER ***")
                    self.logger.info(f"  Initial Capital: ${self.initial_capital:.2f}")
                    self.logger.info(f"  Current Portfolio Value: ${current_portfolio_value:.2f}")
                    self.logger.info(f"  Portfolio Change: ${portfolio_change:.2f} ({portfolio_change_pct:+.2f}%)")
                    self.logger.info(f"  Realized P&L: ${portfolio_summary['realized_pnl']:.2f}")
                    self.logger.info(f"  Unrealized P&L: ${portfolio_summary['unrealized_pnl']:.2f}")
                    self.logger.info(f"  Net P&L: ${portfolio_summary['net_pnl']:.2f}")
                    
                    if portfolio_change > 0:
                        self.logger.info(f"*** 5M REALTIME SCALPING PROFIT: ${portfolio_change:.2f} (+{portfolio_change_pct:.2f}%) ***")
                    elif portfolio_change < 0:
                        self.logger.info(f"*** 5M REALTIME SCALPING LOSS: ${portfolio_change:.2f} ({portfolio_change_pct:.2f}%) ***")
                    else:
                        self.logger.info(f"*** 5M REALTIME SCALPING BREAK EVEN: ${portfolio_change:.2f} (0.00%) ***")
                    
                except Exception as e:
                    self.logger.error(f"5M scalping buy order failed: {e}")
                
            elif (sell_score_ok and sell_vol_filter_ok and sell_regime_filter_ok):
                position_size = self.calculate_dynamic_position_size(
                    signals['signal_strength'], current_vol
                )
                
                self.log(f'5M SCALPING SELL - Score: {signals["sell_score"]:.3f}, '
                        f'Regime: {self.current_regime}, Size: {position_size:.3f}')
                
                try:
                    self.order = self.sell(size=position_size, exectype=bt.Order.Market)
                    self.entry_bar = len(self)
                    self.last_trade_time = self.datas[0].datetime.datetime(0)
                    self.trades_this_hour += 1
                    
                    # Add portfolio value change and profit/loss information
                    current_portfolio_value = self.broker.get_value()
                    portfolio_change = current_portfolio_value - self.initial_capital
                    portfolio_change_pct = (portfolio_change / self.initial_capital) * 100
                    
                    # Get portfolio summary from tracker
                    portfolio_summary = self.portfolio_tracker.get_portfolio_summary()
                    
                    self.logger.info(f"*** 5M REALTIME SCALPING PORTFOLIO VALUE AFTER SELL ORDER ***")
                    self.logger.info(f"  Initial Capital: ${self.initial_capital:.2f}")
                    self.logger.info(f"  Current Portfolio Value: ${current_portfolio_value:.2f}")
                    self.logger.info(f"  Portfolio Change: ${portfolio_change:.2f} ({portfolio_change_pct:+.2f}%)")
                    self.logger.info(f"  Realized P&L: ${portfolio_summary['realized_pnl']:.2f}")
                    self.logger.info(f"  Unrealized P&L: ${portfolio_summary['unrealized_pnl']:.2f}")
                    self.logger.info(f"  Net P&L: ${portfolio_summary['net_pnl']:.2f}")
                    
                    if portfolio_change > 0:
                        self.logger.info(f"*** 5M REALTIME SCALPING PROFIT: ${portfolio_change:.2f} (+{portfolio_change_pct:.2f}%) ***")
                    elif portfolio_change < 0:
                        self.logger.info(f"*** 5M REALTIME SCALPING LOSS: ${portfolio_change:.2f} ({portfolio_change_pct:.2f}%) ***")
                    else:
                        self.logger.info(f"*** 5M REALTIME SCALPING BREAK EVEN: ${portfolio_change:.2f} (0.00%) ***")
                    
                except Exception as e:
                    self.logger.error(f"5M scalping sell order failed: {e}")
                    
        else:
            self._manage_scalping_position(current_vol, signals)

    def _manage_scalping_position(self, volatility: float, signals: Dict[str, Any]):
        """Position management for 5M scalping"""
        current_price = self.dataclose[0]
        
        if self.position.size > 0:  # Long position
            base_stop_distance = max(self.p.base_stop_loss, volatility * 1.5)
            stop_price = self.buyprice * (1 - base_stop_distance)
            target_distance = base_stop_distance * 3.0
            target_price = self.buyprice * (1 + target_distance)
            quick_exit_price = self.buyprice * (1 + self.p.quick_exit_threshold)
            
            current_profit_pct = (current_price - self.buyprice) / self.buyprice
            
            if self.current_regime == 'bearish_trend' and self.regime_confidence > 0.6:
                if current_profit_pct > 0.002:
                    self.log('5M SCALPING REGIME EXIT (LONG)')
                    self.close()
                    return
            
            if signals['sell_score'] > 0.6:
                self.log('5M SCALPING SIGNAL EXIT (LONG)')
                self.close()
                return
            
            if current_price >= quick_exit_price:
                self.log(f'5M SCALPING QUICK EXIT (LONG) - Price: {current_price:.5f}')
                self.close()
                self.quick_exits += 1
            elif current_price <= stop_price:
                self.log(f'5M SCALPING STOP LOSS (LONG) - Price: {current_price:.5f}')
                self.close()
            elif current_price >= target_price:
                self.log(f'5M SCALPING TAKE PROFIT (LONG) - Price: {current_price:.5f}')
                self.close()
                
        elif self.position.size < 0:  # Short position
            base_stop_distance = max(self.p.base_stop_loss, volatility * 1.5)
            stop_price = self.buyprice * (1 + base_stop_distance)
            target_distance = base_stop_distance * 3.0
            target_price = self.buyprice * (1 - target_distance)
            quick_exit_price = self.buyprice * (1 - self.p.quick_exit_threshold)
            
            current_profit_pct = (self.buyprice - current_price) / self.buyprice
            
            if self.current_regime == 'bullish_trend' and self.regime_confidence > 0.6:
                if current_profit_pct > 0.002:
                    self.log('5M SCALPING REGIME EXIT (SHORT)')
                    self.close()
                    return
                    
            if signals['buy_score'] > 0.6:
                self.log('5M SCALPING SIGNAL EXIT (SHORT)')
                self.close()
                return
            
            if current_price <= quick_exit_price:
                self.log(f'5M SCALPING QUICK EXIT (SHORT) - Price: {current_price:.5f}')
                self.close()
                self.quick_exits += 1
            elif current_price >= stop_price:
                self.log(f'5M SCALPING STOP LOSS (SHORT) - Price: {current_price:.5f}')
                self.close()
            elif current_price <= target_price:
                self.log(f'5M SCALPING TAKE PROFIT (SHORT) - Price: {current_price:.5f}')
                self.close()

    def notify_order(self, order):
        """Order notification for 5M scalping"""
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            
            if order.isbuy():
                self.portfolio_tracker.update_cash(self.broker.get_cash())
                self.portfolio_tracker.add_position(
                    symbol="EUR_USD",
                    size=order.executed.size,
                    entry_price=order.executed.price,
                    commission=order.executed.comm
                )
            else:
                self.portfolio_tracker.close_position(
                    symbol="EUR_USD",
                    exit_price=order.executed.price,
                    commission=order.executed.comm
                )
            
            # Calculate portfolio change since start
            current_portfolio_value = self.broker.get_value()
            portfolio_change = current_portfolio_value - self.initial_capital
            portfolio_change_pct = (portfolio_change / self.initial_capital) * 100
            
            # Get portfolio summary from tracker
            portfolio_summary = self.portfolio_tracker.get_portfolio_summary()
            
            self.logger.info(f"*** 5M REALTIME SCALPING FINAL PORTFOLIO VALUE CHANGE AFTER ORDER EXECUTION ***")
            self.logger.info(f"  Previous Reference Capital: ${self.initial_capital:.2f}")
            self.logger.info(f"  Current Portfolio Value: ${current_portfolio_value:.2f}")
            self.logger.info(f"  Trade P&L: ${portfolio_change:.2f} ({portfolio_change_pct:+.2f}%)")
            self.logger.info(f"  Net P&L: ${portfolio_summary['net_pnl']:.2f}")
            
            if portfolio_change > 0:
                self.logger.info(f"*** 5M REALTIME SCALPING TRADE RESULT: PROFIT ${portfolio_change:.2f} (+{portfolio_change_pct:.2f}%) ***")
            elif portfolio_change < 0:
                self.logger.info(f"*** 5M REALTIME SCALPING TRADE RESULT: LOSS ${portfolio_change:.2f} ({portfolio_change_pct:.2f}%) ***")
            else:
                self.logger.info(f"*** 5M REALTIME SCALPING TRADE RESULT: BREAK EVEN ${portfolio_change:.2f} (0.00%) ***")
            
            # Update reference capital for next trade
            self.initial_capital = current_portfolio_value
            self.logger.info(f"*** UPDATED REFERENCE CAPITAL FOR NEXT TRADE: ${self.initial_capital:.2f} ***")
            
            self.log(f'5M SCALPING ORDER EXECUTED - {order.getstatusname()} at {order.executed.price:.5f}')
            self.order = None
            
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f'5M SCALPING ORDER FAILED - {order.getstatusname()}')
            self.order = None

    def log(self, txt, dt=None):
        """Logging for 5M scalping"""
        if self.p.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            time = self.datas[0].datetime.time(0)
            current_value = self.broker.get_value()
            self.logger.info(f'{dt} {time} {txt} | Value: {current_value:.2f}')

    def notify_trade(self, trade):
        """Trade notification for 5M scalping"""
        if trade.isclosed:
            self.trade_count += 1
            self.total_pnl += trade.pnl
            
            if trade.pnl > 0:
                self.winning_trades += 1
                
            win_rate = (self.winning_trades / self.trade_count) * 100 if self.trade_count > 0 else 0
            avg_pnl = self.total_pnl / self.trade_count if self.trade_count > 0 else 0
            
            self.log(f'5M SCALPING TRADE CLOSED - PnL: {trade.pnl:.2f} | Win Rate: {win_rate:.1f}%')

if __name__ == '__main__':
    print("Realtime 5M Scalping Strategy loaded successfully")