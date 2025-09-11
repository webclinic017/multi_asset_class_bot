"""
Enhanced Real-time Scalping Strategy for 1-minute timeframe
Integrated with comprehensive signal logging and broker activity tracking
"""

import backtrader as bt
import logging
import numpy as np
from typing import Dict, Any, Tuple
from scipy import stats
from datetime import datetime

# Import our real-time logging components
from utils.realtime_signal_logger import get_signal_logger, SignalSource, SignalPriority
from backtesting.enhanced_realtime_broker import SignalType

class EnhancedRealtimeScalping1MStrategy(bt.Strategy):
    """Enhanced real-time compatible 1-minute scalping strategy with comprehensive logging"""
    
    params = (
        ('fast_length', 5),
        ('slow_length', 13),
        ('signal_length', 3),
        ('rsi_period', 7),
        ('rsi_oversold', 25),
        ('rsi_overbought', 75),
        ('macd_fast', 5),
        ('macd_slow', 13),
        ('macd_signal', 3),
        ('bb_period', 10),
        ('bb_std', 1.5),
        ('atr_period', 7),
        ('base_stop_loss', 0.003),
        ('base_take_profit', 0.009),
        ('dynamic_sizing', True),
        ('max_risk_per_trade', 0.015),
        ('volatility_adjustment', True),
        ('stop_loss_percent', 0.003),
        ('take_profit_percent', 0.009),
        ('position_size_percent', 0.02),
        ('regime_lookback', 50),
        ('trend_threshold', 0.4),
        ('mean_reversion_threshold', 0.3),
        ('volume_period', 15),
        ('volume_confirmation', True),
        ('use_regime_filter', True),
        ('use_volatility_filter', True),
        ('momentum_acceleration', 1.6),
        ('trend_following_boost', 1.4),
        ('breakout_multiplier', 1.8),
        ('mean_reversion_factor', 0.7),
        ('volatility_expansion_threshold', 1.3),
        ('max_trades_per_hour', 15),
        ('min_time_between_trades', 30),
        ('quick_exit_threshold', 0.002),
        ('signal_strength_threshold', 0.1),
        ('high_confidence_threshold', 0.7),
        ('printlog', False)
    )

    def __init__(self):
        """Initialize enhanced 1M scalping strategy with real-time logging"""
        self.logger = logging.getLogger(__name__)
        
        # Initialize signal logger
        self.signal_logger = get_signal_logger()
        
        # Portfolio tracker
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
        self.current_signal_id = None
        
        # Performance tracking
        self.trade_count = 0
        self.winning_trades = 0
        self.total_pnl = 0.0
        self.peak_value = self.broker.get_cash()
        
        # Scalping specific tracking
        self.last_trade_time = None
        self.trades_this_hour = 0
        self.last_hour = None
        self.quick_exits = 0
        self.signal_count = 0
        
        # Session tracking
        self.session_id = getattr(self, 'session_id', 1)  # Will be set externally
        
        # Initialize indicators
        self._init_core_indicators()
        
        # Market regime tracking
        self.current_regime = 'neutral'
        self.regime_confidence = 0.0
        
        # Set broker reference for signal logging
        if hasattr(self.broker, 'set_current_strategy'):
            self.broker.set_current_strategy(self)
        
        self.logger.info("Enhanced Realtime 1M Scalping Strategy initialized with comprehensive logging")

    def _init_core_indicators(self):
        """Initialize core technical indicators"""
        self.ema_fast = bt.indicators.EMA(period=self.p.fast_length)
        self.ema_slow = bt.indicators.EMA(period=self.p.slow_length)
        self.rsi = bt.indicators.RSI(period=self.p.rsi_period)
        self.macd = bt.indicators.MACD(
            period_me1=self.p.macd_fast,
            period_me2=self.p.macd_slow,
            period_signal=self.p.macd_signal
        )
        self.bb = bt.indicators.BollingerBands(
            period=self.p.bb_period,
            devfactor=self.p.bb_std
        )
        self.atr = bt.indicators.ATR(period=self.p.atr_period)
        self.stoch = bt.indicators.Stochastic(period=5, period_dfast=3)
        self.williams_r = bt.indicators.WilliamsR(period=8)
        self.volume_sma = bt.indicators.SMA(self.datavolume, period=self.p.volume_period)
        self.volume_ratio = self.datavolume / bt.indicators.Max(self.volume_sma, 1e-8)

    def detect_market_regime(self) -> Tuple[str, float]:
        """Detect market regime with enhanced logging"""
        current_data_length = len(self.data)
        
        if current_data_length < 15:
            return 'neutral', 0.0
            
        try:
            lookback_period = min(current_data_length - 1, self.p.regime_lookback)
            lookback_period = max(lookback_period, 15)
            
            recent_closes = np.array([self.dataclose[-i] for i in range(lookback_period, 0, -1)])
            recent_returns = np.diff(np.log(recent_closes))
            
            x = np.arange(len(recent_closes))
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, recent_closes)
            
            trend_strength = abs(r_value)
            
            if trend_strength > self.p.trend_threshold and slope > 0:
                return 'bullish_trend', min(trend_strength, 0.95)
            elif trend_strength > self.p.trend_threshold and slope < 0:
                return 'bearish_trend', min(trend_strength, 0.95)
            elif trend_strength < self.p.mean_reversion_threshold:
                return 'mean_reverting', 0.8
            else:
                return 'neutral', 0.3
                
        except Exception as e:
            self.logger.error(f"Error in regime detection: {e}")
            return 'neutral', 0.0

    def calculate_dynamic_position_size(self, signal_strength: float, volatility: float) -> float:
        """Calculate position size with enhanced risk management"""
        if not self.p.dynamic_sizing:
            return 0.01
            
        try:
            base_size = self.p.position_size_percent
            signal_adjustment = signal_strength * 1.2
            vol_adjustment = 1.0 / (1.0 + volatility * 15)
            
            final_size = base_size * signal_adjustment * vol_adjustment
            return max(final_size, 0.005)
            
        except Exception as e:
            self.logger.error(f"Error calculating position size: {e}")
            return 0.01

    def generate_enhanced_scalping_signals(self) -> Dict[str, Any]:
        """Generate enhanced scalping signals with comprehensive logging"""
        signals = {
            'buy_score': 0.0,
            'sell_score': 0.0,
            'signal_strength': 0.0,
            'regime_filter': True,
            'volatility_filter': True,
            'components': {},
            'indicators': {},
            'market_conditions': {},
            'risk_metrics': {}
        }
        
        try:
            current_price = self.dataclose[0]
            current_rsi = self.rsi[0]
            
            # Collect all indicator values for logging
            signals['indicators'] = {
                'ema_fast': float(self.ema_fast[0]),
                'ema_slow': float(self.ema_slow[0]),
                'rsi': float(current_rsi),
                'macd': float(self.macd.macd[0]),
                'macd_signal': float(self.macd.signal[0]),
                'bb_upper': float(self.bb.lines.top[0]),
                'bb_middle': float(self.bb.lines.mid[0]),
                'bb_lower': float(self.bb.lines.bot[0]),
                'atr': float(self.atr[0]),
                'stoch_k': float(self.stoch.percK[0]),
                'stoch_d': float(self.stoch.percD[0]),
                'williams_r': float(self.williams_r[0]),
                'volume_ratio': float(self.volume_ratio[0]) if len(self.volume_ratio) > 0 else 1.0
            }
            
            # Enhanced signal generation
            buy_score = 0.0
            sell_score = 0.0
            
            # Trend signals
            if self.ema_fast[0] > self.ema_slow[0]:
                buy_score += 0.4
                signals['components']['trend_bullish'] = True
            else:
                sell_score += 0.4
                signals['components']['trend_bearish'] = True
            
            # RSI signals
            if current_rsi < self.p.rsi_oversold:
                buy_score += 0.3
                signals['components']['rsi_oversold'] = True
            elif current_rsi > self.p.rsi_overbought:
                sell_score += 0.3
                signals['components']['rsi_overbought'] = True
            
            # MACD signals
            if self.macd.macd[0] > self.macd.signal[0]:
                buy_score += 0.2
                signals['components']['macd_bullish'] = True
            else:
                sell_score += 0.2
                signals['components']['macd_bearish'] = True
            
            # Volume confirmation
            if self.p.volume_confirmation and len(self.volume_ratio) > 0:
                if self.volume_ratio[0] > 1.5:
                    buy_score += 0.1
                    sell_score += 0.1
                    signals['components']['high_volume'] = True
            
            # Bollinger Bands
            bb_position = (current_price - self.bb.lines.bot[0]) / (self.bb.lines.top[0] - self.bb.lines.bot[0])
            if bb_position < 0.2:
                buy_score += 0.2
                signals['components']['bb_oversold'] = True
            elif bb_position > 0.8:
                sell_score += 0.2
                signals['components']['bb_overbought'] = True
            
            signals['buy_score'] = buy_score
            signals['sell_score'] = sell_score
            signals['signal_strength'] = max(buy_score, sell_score)
            
            # Market conditions
            current_vol = self.atr[0] / current_price if current_price > 0 else 0
            signals['market_conditions'] = {
                'price': float(current_price),
                'volatility': float(current_vol),
                'regime': self.current_regime,
                'regime_confidence': float(self.regime_confidence),
                'bb_position': float(bb_position),
                'trend_strength': float(abs(self.ema_fast[0] - self.ema_slow[0]) / current_price) if current_price > 0 else 0
            }
            
            # Risk metrics
            signals['risk_metrics'] = {
                'atr_percent': float(current_vol),
                'position_size': self.calculate_dynamic_position_size(signals['signal_strength'], current_vol),
                'max_risk': float(self.p.max_risk_per_trade),
                'trades_this_hour': self.trades_this_hour,
                'max_trades_per_hour': self.p.max_trades_per_hour
            }
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error generating signals: {e}")
            return signals

    def check_scalping_filters(self) -> bool:
        """Check scalping filters with logging"""
        try:
            current_time = self.datas[0].datetime.datetime(0)
            current_hour = current_time.hour
            
            if self.last_hour != current_hour:
                self.trades_this_hour = 0
                self.last_hour = current_hour
            
            if self.trades_this_hour >= self.p.max_trades_per_hour:
                self.logger.info(f"Max trades per hour reached: {self.trades_this_hour}/{self.p.max_trades_per_hour}")
                return False
            
            if self.last_trade_time:
                time_diff = (current_time - self.last_trade_time).total_seconds()
                if time_diff < self.p.min_time_between_trades:
                    self.logger.debug(f"Min time between trades not met: {time_diff}s < {self.p.min_time_between_trades}s")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error in scalping filters: {e}")
            return False

    def next(self):
        """Main scalping logic with enhanced real-time logging"""
        if self.order:
            return
        
        if not self.check_scalping_filters():
            return
        
        basic_min_data = max(self.p.slow_length, self.p.bb_period, self.p.atr_period)
        if len(self.data) < basic_min_data:
            return
        
        # Update market regime
        self.current_regime, self.regime_confidence = self.detect_market_regime()
        
        # Generate signals with comprehensive data
        signals = self.generate_enhanced_scalping_signals()
        
        current_price = self.dataclose[0]
        current_vol = self.atr[0] / current_price if current_price > 0 else 0
        
        if not self.position:
            # Check for buy signals
            if (signals['buy_score'] > self.p.signal_strength_threshold and 
                signals['regime_filter'] and signals['volatility_filter']):
                
                self.signal_count += 1
                
                # Determine signal priority
                priority = SignalPriority.HIGH if signals['signal_strength'] > self.p.high_confidence_threshold else SignalPriority.MEDIUM
                
                # Log the signal with comprehensive data
                signal_id = self.signal_logger.log_signal(
                    session_id=self.session_id,
                    symbol="EUR_USD",
                    timeframe="1m",
                    signal_type="BUY",
                    signal_strength=signals['signal_strength'],
                    confidence=signals['buy_score'],
                    price=current_price,
                    strategy_name=self.__class__.__name__,
                    indicators=signals['indicators'],
                    market_conditions=signals['market_conditions'],
                    risk_metrics=signals['risk_metrics'],
                    execution_context={
                        'components': signals['components'],
                        'regime': self.current_regime,
                        'regime_confidence': self.regime_confidence,
                        'bar_number': len(self),
                        'timestamp': self.datas[0].datetime.datetime(0).isoformat()
                    },
                    source=SignalSource.STRATEGY,
                    priority=priority
                )
                
                self.current_signal_id = signal_id
                
                # Log to broker if it supports signal logging
                if hasattr(self.broker, 'log_trading_signal'):
                    self.broker.log_trading_signal(
                        SignalType.BUY,
                        signals['signal_strength'],
                        signals['buy_score'],
                        current_price,
                        signals['indicators']
                    )
                
                # Calculate position size
                position_size = self.calculate_dynamic_position_size(signals['signal_strength'], current_vol)
                
                self.log(f'1M SCALPING BUY SIGNAL - Score: {signals["buy_score"]:.3f}, Size: {position_size:.3f}')
                
                try:
                    self.order = self.buy(size=position_size, exectype=bt.Order.Market)
                    self.entry_bar = len(self)
                    self.last_trade_time = self.datas[0].datetime.datetime(0)
                    self.trades_this_hour += 1
                except Exception as e:
                    self.logger.error(f"Buy order failed: {e}")
                
            # Check for sell signals
            elif (signals['sell_score'] > self.p.signal_strength_threshold and 
                  signals['regime_filter'] and signals['volatility_filter']):
                
                self.signal_count += 1
                
                # Determine signal priority
                priority = SignalPriority.HIGH if signals['signal_strength'] > self.p.high_confidence_threshold else SignalPriority.MEDIUM
                
                # Log the signal with comprehensive data
                signal_id = self.signal_logger.log_signal(
                    session_id=self.session_id,
                    symbol="EUR_USD",
                    timeframe="1m",
                    signal_type="SELL",
                    signal_strength=signals['signal_strength'],
                    confidence=signals['sell_score'],
                    price=current_price,
                    strategy_name=self.__class__.__name__,
                    indicators=signals['indicators'],
                    market_conditions=signals['market_conditions'],
                    risk_metrics=signals['risk_metrics'],
                    execution_context={
                        'components': signals['components'],
                        'regime': self.current_regime,
                        'regime_confidence': self.regime_confidence,
                        'bar_number': len(self),
                        'timestamp': self.datas[0].datetime.datetime(0).isoformat()
                    },
                    source=SignalSource.STRATEGY,
                    priority=priority
                )
                
                self.current_signal_id = signal_id
                
                # Log to broker if it supports signal logging
                if hasattr(self.broker, 'log_trading_signal'):
                    self.broker.log_trading_signal(
                        SignalType.SELL,
                        signals['signal_strength'],
                        signals['sell_score'],
                        current_price,
                        signals['indicators']
                    )
                
                # Calculate position size
                position_size = self.calculate_dynamic_position_size(signals['signal_strength'], current_vol)
                
                self.log(f'1M SCALPING SELL SIGNAL - Score: {signals["sell_score"]:.3f}, Size: {position_size:.3f}')
                
                try:
                    self.order = self.sell(size=position_size, exectype=bt.Order.Market)
                    self.entry_bar = len(self)
                    self.last_trade_time = self.datas[0].datetime.datetime(0)
                    self.trades_this_hour += 1
                except Exception as e:
                    self.logger.error(f"Sell order failed: {e}")
                    
        else:
            self._manage_position(current_vol, signals)

    def _manage_position(self, volatility: float, signals: Dict[str, Any]):
        """Enhanced position management with logging"""
        current_price = self.dataclose[0]
        
        if self.position.size > 0:  # Long position
            base_stop_distance = max(self.p.base_stop_loss, volatility * 1.0)
            stop_price = self.buyprice * (1 - base_stop_distance)
            target_price = self.buyprice * (1 + base_stop_distance * 3.0)
            quick_exit_price = self.buyprice * (1 + self.p.quick_exit_threshold)
            
            if current_price >= quick_exit_price:
                self.log(f'1M SCALPING QUICK EXIT (LONG) - Price: {current_price:.5f}')
                self.close()
                self.quick_exits += 1
            elif current_price <= stop_price:
                self.log(f'1M SCALPING STOP LOSS (LONG) - Price: {current_price:.5f}')
                self.close()
            elif current_price >= target_price:
                self.log(f'1M SCALPING TAKE PROFIT (LONG) - Price: {current_price:.5f}')
                self.close()
                
        elif self.position.size < 0:  # Short position
            base_stop_distance = max(self.p.base_stop_loss, volatility * 1.0)
            stop_price = self.buyprice * (1 + base_stop_distance)
            target_price = self.buyprice * (1 - base_stop_distance * 3.0)
            quick_exit_price = self.buyprice * (1 - self.p.quick_exit_threshold)
            
            if current_price <= quick_exit_price:
                self.log(f'1M SCALPING QUICK EXIT (SHORT) - Price: {current_price:.5f}')
                self.close()
                self.quick_exits += 1
            elif current_price >= stop_price:
                self.log(f'1M SCALPING STOP LOSS (SHORT) - Price: {current_price:.5f}')
                self.close()
            elif current_price <= target_price:
                self.log(f'1M SCALPING TAKE PROFIT (SHORT) - Price: {current_price:.5f}')
                self.close()

    def notify_order(self, order):
        """Enhanced order notification with signal execution tracking"""
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            
            # Mark signal as executed if we have a current signal
            if self.current_signal_id:
                self.signal_logger.mark_signal_executed(
                    self.current_signal_id,
                    datetime.utcnow(),
                    order.executed.price,
                    order.ref
                )
                self.current_signal_id = None
            
            # Update portfolio tracker
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
            
            self.log(f'1M SCALPING ORDER EXECUTED - {order.getstatusname()} at {order.executed.price:.5f}')
            self.order = None
            
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f'1M SCALPING ORDER FAILED - {order.getstatusname()}')
            self.order = None
            self.current_signal_id = None

    def log(self, txt, dt=None):
        """Enhanced logging"""
        if self.p.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            time = self.datas[0].datetime.time(0)
            current_value = self.broker.get_value()
            self.logger.info(f'{dt} {time} {txt} | Value: {current_value:.2f}')

    def notify_trade(self, trade):
        """Enhanced trade notification with comprehensive logging"""
        if trade.isclosed:
            self.trade_count += 1
            self.total_pnl += trade.pnl
            
            if trade.pnl > 0:
                self.winning_trades += 1
                
            win_rate = (self.winning_trades / self.trade_count) * 100 if self.trade_count > 0 else 0
            
            # Log comprehensive trade information
            self.logger.info(f"=== TRADE CLOSED ===")
            self.logger.info(f"Trade ID: {trade.ref}")
            self.logger.info(f"P&L: {trade.pnl:.2f}")
            self.logger.info(f"Win Rate: {win_rate:.1f}%")
            self.logger.info(f"Total Trades: {self.trade_count}")
            self.logger.info(f"Quick Exits: {self.quick_exits}")
            self.logger.info(f"Signals Generated: {self.signal_count}")
            
            self.log(f'1M SCALPING TRADE CLOSED - PnL: {trade.pnl:.2f} | Win Rate: {win_rate:.1f}%')

if __name__ == '__main__':
    print("Enhanced Realtime 1M Scalping Strategy with comprehensive logging loaded successfully")