"""
Real-time Scalping Strategy for 1-minute timeframe
Compatible with real-time broker logic like EnhancedForexStrategy
"""

import backtrader as bt
import logging
import numpy as np
from typing import Dict, Any, Tuple
from scipy import stats

class RealtimeScalping1MStrategy(bt.Strategy):
    """Real-time compatible 1-minute scalping strategy"""
    
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
        ('printlog', False)
    )

    def __init__(self):
        """Initialize 1M scalping strategy"""
        self.logger = logging.getLogger(__name__)
        
        from execution.portfolio_value_tracker import get_portfolio_tracker
        self.portfolio_tracker = get_portfolio_tracker(10000.0)
        
        self.dataclose = self.datas[0].close
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low
        self.datavolume = self.datas[0].volume
        
        self.order = None
        self.buyprice = None
        self.buycomm = None
        self.entry_bar = None
        
        self.trade_count = 0
        self.winning_trades = 0
        self.total_pnl = 0.0
        self.peak_value = self.broker.get_cash()
        
        self.last_trade_time = None
        self.trades_this_hour = 0
        self.last_hour = None
        self.quick_exits = 0
        
        self._init_core_indicators()
        
        self.current_regime = 'neutral'
        self.regime_confidence = 0.0
        
        self.logger.info("Realtime 1M Scalping Strategy initialized")

    def _init_core_indicators(self):
        """Initialize indicators"""
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
        """Detect market regime"""
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
        """Calculate position size"""
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

    def generate_scalping_signals(self) -> Dict[str, Any]:
        """Generate scalping signals"""
        signals = {
            'buy_score': 0.0,
            'sell_score': 0.0,
            'signal_strength': 0.0,
            'regime_filter': True,
            'volatility_filter': True
        }
        
        try:
            current_price = self.dataclose[0]
            current_rsi = self.rsi[0]
            
            # Simple but effective scalping signals
            buy_score = 0.0
            sell_score = 0.0
            
            # Trend signals
            if self.ema_fast[0] > self.ema_slow[0]:
                buy_score += 0.4
            else:
                sell_score += 0.4
            
            # RSI signals
            if current_rsi < self.p.rsi_oversold:
                buy_score += 0.3
            elif current_rsi > self.p.rsi_overbought:
                sell_score += 0.3
            
            # MACD signals
            if self.macd.macd[0] > self.macd.signal[0]:
                buy_score += 0.2
            else:
                sell_score += 0.2
            
            # Volume confirmation
            if self.p.volume_confirmation and len(self.volume_ratio) > 0:
                if self.volume_ratio[0] > 1.5:
                    buy_score += 0.1
                    sell_score += 0.1
            
            signals['buy_score'] = buy_score
            signals['sell_score'] = sell_score
            signals['signal_strength'] = max(buy_score, sell_score)
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error generating signals: {e}")
            return signals

    def check_scalping_filters(self) -> bool:
        """Check scalping filters"""
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
        """Main scalping logic"""
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
            if signals['buy_score'] > 0.1 and signals['regime_filter'] and signals['volatility_filter']:
                position_size = self.calculate_dynamic_position_size(signals['signal_strength'], current_vol)
                
                self.log(f'1M SCALPING BUY - Score: {signals["buy_score"]:.3f}, Size: {position_size:.3f}')
                
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
                    
                    self.logger.info(f"*** 1M REALTIME SCALPING PORTFOLIO VALUE AFTER BUY ORDER ***")
                    self.logger.info(f"  Initial Capital: ${self.initial_capital:.2f}")
                    self.logger.info(f"  Current Portfolio Value: ${current_portfolio_value:.2f}")
                    self.logger.info(f"  Portfolio Change: ${portfolio_change:.2f} ({portfolio_change_pct:+.2f}%)")
                    self.logger.info(f"  Realized P&L: ${portfolio_summary['realized_pnl']:.2f}")
                    self.logger.info(f"  Unrealized P&L: ${portfolio_summary['unrealized_pnl']:.2f}")
                    self.logger.info(f"  Net P&L: ${portfolio_summary['net_pnl']:.2f}")
                    
                    if portfolio_change > 0:
                        self.logger.info(f"*** 1M REALTIME SCALPING PROFIT: ${portfolio_change:.2f} (+{portfolio_change_pct:.2f}%) ***")
                    elif portfolio_change < 0:
                        self.logger.info(f"*** 1M REALTIME SCALPING LOSS: ${portfolio_change:.2f} ({portfolio_change_pct:.2f}%) ***")
                    else:
                        self.logger.info(f"*** 1M REALTIME SCALPING BREAK EVEN: ${portfolio_change:.2f} (0.00%) ***")
                        
                except Exception as e:
                    self.logger.error(f"Buy order failed: {e}")
                
            elif signals['sell_score'] > 0.1 and signals['regime_filter'] and signals['volatility_filter']:
                position_size = self.calculate_dynamic_position_size(signals['signal_strength'], current_vol)
                
                self.log(f'1M SCALPING SELL - Score: {signals["sell_score"]:.3f}, Size: {position_size:.3f}')
                
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
                    
                    self.logger.info(f"*** 1M REALTIME SCALPING PORTFOLIO VALUE AFTER SELL ORDER ***")
                    self.logger.info(f"  Initial Capital: ${self.initial_capital:.2f}")
                    self.logger.info(f"  Current Portfolio Value: ${current_portfolio_value:.2f}")
                    self.logger.info(f"  Portfolio Change: ${portfolio_change:.2f} ({portfolio_change_pct:+.2f}%)")
                    self.logger.info(f"  Realized P&L: ${portfolio_summary['realized_pnl']:.2f}")
                    self.logger.info(f"  Unrealized P&L: ${portfolio_summary['unrealized_pnl']:.2f}")
                    self.logger.info(f"  Net P&L: ${portfolio_summary['net_pnl']:.2f}")
                    
                    if portfolio_change > 0:
                        self.logger.info(f"*** 1M REALTIME SCALPING PROFIT: ${portfolio_change:.2f} (+{portfolio_change_pct:.2f}%) ***")
                    elif portfolio_change < 0:
                        self.logger.info(f"*** 1M REALTIME SCALPING LOSS: ${portfolio_change:.2f} ({portfolio_change_pct:.2f}%) ***")
                    else:
                        self.logger.info(f"*** 1M REALTIME SCALPING BREAK EVEN: ${portfolio_change:.2f} (0.00%) ***")
                        
                except Exception as e:
                    self.logger.error(f"Sell order failed: {e}")
                    
        else:
            self._manage_position(current_vol, signals)

    def _manage_position(self, volatility: float, signals: Dict[str, Any]):
        """Position management"""
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
        """Order notification"""
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
            
            self.logger.info(f"*** 1M REALTIME SCALPING FINAL PORTFOLIO VALUE CHANGE AFTER ORDER EXECUTION ***")
            self.logger.info(f"  Previous Reference Capital: ${self.initial_capital:.2f}")
            self.logger.info(f"  Current Portfolio Value: ${current_portfolio_value:.2f}")
            self.logger.info(f"  Trade P&L: ${portfolio_change:.2f} ({portfolio_change_pct:+.2f}%)")
            self.logger.info(f"  Net P&L: ${portfolio_summary['net_pnl']:.2f}")
            
            if portfolio_change > 0:
                self.logger.info(f"*** 1M REALTIME SCALPING TRADE RESULT: PROFIT ${portfolio_change:.2f} (+{portfolio_change_pct:.2f}%) ***")
            elif portfolio_change < 0:
                self.logger.info(f"*** 1M REALTIME SCALPING TRADE RESULT: LOSS ${portfolio_change:.2f} ({portfolio_change_pct:.2f}%) ***")
            else:
                self.logger.info(f"*** 1M REALTIME SCALPING TRADE RESULT: BREAK EVEN ${portfolio_change:.2f} (0.00%) ***")
            
            # Update reference capital for next trade
            self.initial_capital = current_portfolio_value
            self.logger.info(f"*** UPDATED REFERENCE CAPITAL FOR NEXT TRADE: ${self.initial_capital:.2f} ***")
            
            self.log(f'1M SCALPING ORDER EXECUTED - {order.getstatusname()} at {order.executed.price:.5f}')
            self.order = None
            
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f'1M SCALPING ORDER FAILED - {order.getstatusname()}')
            self.order = None

    def log(self, txt, dt=None):
        """Logging"""
        if self.p.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            time = self.datas[0].datetime.time(0)
            current_value = self.broker.get_value()
            self.logger.info(f'{dt} {time} {txt} | Value: {current_value:.2f}')

    def notify_trade(self, trade):
        """Trade notification"""
        if trade.isclosed:
            self.trade_count += 1
            self.total_pnl += trade.pnl
            
            if trade.pnl > 0:
                self.winning_trades += 1
                
            win_rate = (self.winning_trades / self.trade_count) * 100 if self.trade_count > 0 else 0
            self.log(f'1M SCALPING TRADE CLOSED - PnL: {trade.pnl:.2f} | Win Rate: {win_rate:.1f}%')

if __name__ == '__main__':
    print("Realtime 1M Scalping Strategy loaded successfully")
