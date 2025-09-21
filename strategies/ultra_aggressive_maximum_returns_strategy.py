"""
ULTRA-AGGRESSIVE MAXIMUM RETURNS STRATEGY
Designed for 2-3% daily returns through ultra-high-frequency scalping
"""

import backtrader as bt
import logging
import numpy as np
from typing import Dict, Any, Tuple
from scipy import stats
from datetime import datetime

from indicators.price_action_analyzer import PriceActionAnalyzer

class UltraAggressiveMaximumReturnsStrategy(bt.Strategy):
    """
    ULTRA-AGGRESSIVE STRATEGY FOR MAXIMUM RETURNS
    - 2-3% daily returns target
    - Ultra-high-frequency scalping (every 30 seconds)
    - 80% position size per trade
    - 0.1% take profit, 0.05% stop loss
    - 500+ trades per day
    """

    params = (
        ('initial_capital', 100000.0),
        ('fast_length', 3),   # Ultra-fast for scalping
        ('slow_length', 8),   # Ultra-fast for scalping
        ('rsi_period', 5),    # Ultra-fast RSI
        ('rsi_oversold', 15), # Ultra-aggressive oversold
        ('rsi_overbought', 85), # Ultra-aggressive overbought
        ('macd_fast', 3),     # Ultra-fast MACD
        ('macd_slow', 8),     # Ultra-fast MACD
        ('macd_signal', 2),   # Ultra-fast signal
        ('bb_period', 5),     # Ultra-fast Bollinger
        ('bb_std', 1.2),      # Tighter bands
        ('atr_period', 3),    # Ultra-fast ATR

        # ULTRA-ULTRA-AGGRESSIVE RISK MANAGEMENT
        ('base_stop_loss', 0.0005),    # 0.05% stop loss
        ('base_take_profit', 0.001),   # 0.1% take profit (200:1 ratio)
        ('dynamic_sizing', True),
        ('max_risk_per_trade', 0.30),  # 30% risk per trade
        ('position_size_percent', 0.80), # 80% of capital per trade
        ('max_position_size', 1.0),     # 100% maximum position size

        # ULTRA-HIGH-FREQUENCY TRADING
        ('max_trades_per_hour', 1000),   # 1000 trades per hour
        ('min_time_between_trades', 3),  # 3 seconds between trades
        ('quick_exit_threshold', 0.0008), # 0.08% quick exit

        # ULTRA-LENIENT SIGNAL THRESHOLDS
        ('signal_strength_threshold', 0.001), # Any signal triggers trade
        ('high_confidence_threshold', 0.001), # Any confidence triggers trade
        ('price_action_weight', 0.6),
        ('technical_weight', 0.4),

        # DISABLE ALL FILTERS FOR MAXIMUM TRADING
        ('use_regime_filter', False),
        ('use_volatility_filter', False),
        ('use_correlation_filter', False),
        ('use_momentum_filter', False),

        ('printlog', False)
    )

    def __init__(self):
        """Initialize ultra-aggressive maximum returns strategy"""
        self.logger = logging.getLogger(__name__)

        # Portfolio tracker
        from execution.portfolio_value_tracker import get_portfolio_tracker
        self.portfolio_tracker = get_portfolio_tracker(self.p.initial_capital)

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
        self.peak_value = self.broker.get_cash()
        self.initial_capital = self.broker.get_cash()
        self.last_completed_portfolio_value = self.broker.get_cash()

        # Ultra-high-frequency tracking
        self.last_trade_time = None
        self.trades_this_hour = 0
        self.last_hour = None
        self.quick_exits = 0
        self.signal_count = 0

        # Initialize indicators
        self._init_ultra_fast_indicators()

        # Price Action Analyzer
        self.price_action_analyzer = PriceActionAnalyzer(self)
        self.logger.info("Ultra-Aggressive Maximum Returns Strategy initialized")

    def _init_ultra_fast_indicators(self):
        """Initialize ultra-fast indicators for scalping"""
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

    def calculate_ultra_aggressive_position_size(self, signal_strength: float, volatility: float,
                                               price_action_confidence: float = 0.5,
                                               technical_confidence: float = 0.5) -> float:
        """Ultra-aggressive position sizing for maximum returns"""
        try:
            base_size = self.p.position_size_percent  # 80% of capital

            # Ultra-aggressive multipliers
            signal_multiplier = signal_strength * 20.0  # 20x signal strength
            vol_adjustment = 1.0 / (1.0 + volatility * 0.5)  # Minimal volatility penalty

            # Price action bonus
            if price_action_confidence > 0.2:
                pa_bonus = 10.0  # 10x bonus for any decent price action
            else:
                pa_bonus = 5.0   # 5x bonus even for poor price action

            # Confidence adjustment
            combined_confidence = (price_action_confidence * 0.6) + (technical_confidence * 0.4)
            confidence_adjustment = 5.0 + (combined_confidence * 10.0)  # 5.0 to 15.0

            final_size = base_size * signal_multiplier * vol_adjustment * confidence_adjustment * pa_bonus

            # Ultra-high risk limits
            max_size = self.p.max_risk_per_trade * 4.0  # 120% risk limit
            final_size = min(final_size, max_size)

            self.logger.info(f"ULTRA-AGGRESSIVE Position Sizing:")
            self.logger.info(f"  Base Size (80%): {base_size:.4f}")
            self.logger.info(f"  Signal Multiplier: {signal_multiplier:.3f}")
            self.logger.info(f"  PA Bonus: {pa_bonus:.3f}")
            self.logger.info(f"  Final Size: {final_size:.6f}")

            return max(final_size, 0.05)  # Minimum 5%

        except Exception as e:
            self.logger.error(f"Error calculating ultra-aggressive position size: {e}")
            return 0.05

    def generate_ultra_aggressive_signals(self) -> Dict[str, Any]:
        """Generate ultra-aggressive signals for maximum trading frequency"""
        signals = {
            'buy_score': 0.0,
            'sell_score': 0.0,
            'signal_strength': 0.0,
            'confidence': 0.0,
            'regime_filter': True,  # Always pass
            'volatility_filter': True,  # Always pass
            'price_action_score': 0.0,
            'technical_score': 0.0,
            'components': {}
        }

        try:
            current_price = self.dataclose[0]

            # === ULTRA-FAST PRICE ACTION ANALYSIS ===
            price_action_data = self.price_action_analyzer.calculate_price_action_score(lookback=5)  # Ultra-short

            pa_bullish = price_action_data['bullish_score']
            pa_bearish = price_action_data['bearish_score']
            pa_confidence = price_action_data['confidence']

            # === ULTRA-FAST TECHNICAL ANALYSIS ===
            tech_bullish = 0.0
            tech_bearish = 0.0

            # RSI Analysis (ultra-aggressive)
            current_rsi = float(self.rsi[0])
            if current_rsi < self.p.rsi_oversold:
                rsi_score = 1.0  # Strong bullish
            elif current_rsi > self.p.rsi_overbought:
                rsi_score = -1.0  # Strong bearish
            elif current_rsi < 50:
                rsi_score = 0.5  # Mild bullish
            elif current_rsi > 50:
                rsi_score = -0.5  # Mild bearish
            else:
                rsi_score = 0.0

            # MACD Analysis (ultra-fast)
            macd_line = float(self.macd.macd[0])
            macd_signal = float(self.macd.signal[0])
            if macd_line > macd_signal:
                macd_score = 0.8
            else:
                macd_score = -0.8

            # EMA Analysis (ultra-fast)
            ema_fast = float(self.ema_fast[0])
            ema_slow = float(self.ema_slow[0])
            if ema_fast > ema_slow:
                ema_score = 0.6
            else:
                ema_score = -0.6

            # Bollinger Bands (ultra-tight)
            bb_position = (current_price - self.bb.lines.bot[0]) / (self.bb.lines.top[0] - self.bb.lines.bot[0])
            if bb_position < 0.1:
                bb_score = 0.7  # Near lower band
            elif bb_position > 0.9:
                bb_score = -0.7  # Near upper band
            else:
                bb_score = 0.0

            # Calculate technical scores
            if rsi_score > 0 or macd_score > 0 or ema_score > 0 or bb_score > 0:
                tech_bullish = max(0, rsi_score) + max(0, macd_score) + max(0, ema_score) + max(0, bb_score)
            else:
                tech_bullish = 0.0

            if rsi_score < 0 or macd_score < 0 or ema_score < 0 or bb_score < 0:
                tech_bearish = abs(min(0, rsi_score)) + abs(min(0, macd_score)) + abs(min(0, ema_score)) + abs(min(0, bb_score))
            else:
                tech_bearish = 0.0

            # === ULTRA-AGGRESSIVE HYBRID CALCULATION ===
            price_action_weight = self.p.price_action_weight
            technical_weight = self.p.technical_weight

            weighted_pa_bullish = pa_bullish * price_action_weight
            weighted_pa_bearish = pa_bearish * price_action_weight
            weighted_tech_bullish = tech_bullish * technical_weight
            weighted_tech_bearish = tech_bearish * technical_weight

            final_bullish = weighted_pa_bullish + weighted_tech_bullish
            final_bearish = weighted_pa_bearish + weighted_tech_bearish

            signals['buy_score'] = final_bullish
            signals['sell_score'] = final_bearish
            signals['signal_strength'] = max(final_bullish, final_bearish)
            signals['price_action_score'] = pa_bullish + pa_bearish
            signals['technical_score'] = tech_bullish + tech_bearish

            # Ultra-high confidence for any signal
            combined_confidence = (pa_confidence * price_action_weight) + ((tech_bullish + tech_bearish) * technical_weight)
            signals['confidence'] = min(combined_confidence, 1.0)

            return signals

        except Exception as e:
            self.logger.error(f"Error generating ultra-aggressive signals: {e}")
            return signals

    def check_ultra_high_frequency_filters(self) -> bool:
        """Check ultra-high-frequency trading filters"""
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
            self.logger.error(f"Error in ultra-high-frequency filters: {e}")
            return False

    def next(self):
        """Ultra-aggressive next() logic for maximum returns"""
        # Update reference capital
        current_portfolio_value = self.broker.get_value()
        if abs(current_portfolio_value - self.last_completed_portfolio_value) > 1.0:
            self.last_completed_portfolio_value = current_portfolio_value

        if self.order:
            return

        if not self.check_ultra_high_frequency_filters():
            return

        if len(self.data) < 10:  # Ultra-short data requirement
            return

        # Generate ultra-aggressive signals
        signals = self.generate_ultra_aggressive_signals()

        current_price = self.dataclose[0]
        current_vol = self.atr[0] / current_price if current_price > 0 else 0

        if not self.position:
            # ULTRA-AGGRESSIVE ENTRY LOGIC
            buy_score = signals['buy_score']
            sell_score = signals['sell_score']

            # Any signal triggers trade (ultra-lenient thresholds)
            if buy_score > self.p.signal_strength_threshold:
                self.signal_count += 1

                position_size = self.calculate_ultra_aggressive_position_size(
                    buy_score, current_vol,
                    signals.get('price_action_details', {}).get('confidence', 0.5),
                    signals['confidence']
                )

                self.log(f'ULTRA-AGGRESSIVE BUY - Score: {buy_score:.3f}, Size: {position_size:.3f}')

                try:
                    self.order = self.buy(size=position_size, exectype=bt.Order.Market)
                    self.entry_bar = len(self)
                    self.last_trade_time = self.datas[0].datetime.datetime(0)
                    self.trades_this_hour += 1
                except Exception as e:
                    self.logger.error(f"Buy order failed: {e}")

            elif sell_score > self.p.signal_strength_threshold:
                self.signal_count += 1

                position_size = self.calculate_ultra_aggressive_position_size(
                    sell_score, current_vol,
                    signals.get('price_action_details', {}).get('confidence', 0.5),
                    signals['confidence']
                )

                self.log(f'ULTRA-AGGRESSIVE SELL - Score: {sell_score:.3f}, Size: {position_size:.3f}')

                try:
                    self.order = self.sell(size=position_size, exectype=bt.Order.Market)
                    self.entry_bar = len(self)
                    self.last_trade_time = self.datas[0].datetime.datetime(0)
                    self.trades_this_hour += 1
                except Exception as e:
                    self.logger.error(f"Sell order failed: {e}")

        else:
            # ULTRA-AGGRESSIVE EXIT LOGIC
            self._ultra_aggressive_position_management(current_vol, signals)

    def _ultra_aggressive_position_management(self, volatility: float, signals: Dict[str, Any]):
        """Ultra-aggressive position management for maximum returns"""
        current_price = self.dataclose[0]

        if self.position.size > 0:  # Long position
            # Ultra-tight stops and targets
            stop_price = self.buyprice * (1 - self.p.base_stop_loss)  # 0.05% stop
            target_price = self.buyprice * (1 + self.p.base_take_profit)  # 0.1% target
            quick_exit_price = self.buyprice * (1 + self.p.quick_exit_threshold)  # 0.08% quick exit

            # Ultra-aggressive exits
            if current_price >= quick_exit_price:
                self.log('ULTRA-QUICK EXIT (LONG)')
                self.close()
                self.quick_exits += 1
            elif current_price <= stop_price:
                self.log('ULTRA-STOP LOSS (LONG)')
                self.close()
            elif current_price >= target_price:
                self.log('ULTRA-TAKE PROFIT (LONG)')
                self.close()

        elif self.position.size < 0:  # Short position
            # Ultra-tight stops and targets for short
            stop_price = self.buyprice * (1 + self.p.base_stop_loss)  # 0.05% stop
            target_price = self.buyprice * (1 - self.p.base_take_profit)  # 0.1% target
            quick_exit_price = self.buyprice * (1 - self.p.quick_exit_threshold)  # 0.08% quick exit

            # Ultra-aggressive exits
            if current_price <= quick_exit_price:
                self.log('ULTRA-QUICK EXIT (SHORT)')
                self.close()
                self.quick_exits += 1
            elif current_price >= stop_price:
                self.log('ULTRA-STOP LOSS (SHORT)')
                self.close()
            elif current_price <= target_price:
                self.log('ULTRA-TAKE PROFIT (SHORT)')
                self.close()

    def notify_order(self, order):
        """Ultra-aggressive order notification"""
        if order.status in [order.Completed]:
            if order.isbuy():
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm

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

            # Update reference capital
            current_portfolio_value = self.broker.get_value()
            portfolio_summary = self.portfolio_tracker.get_portfolio_summary()
            portfolio_change = current_portfolio_value - self.last_completed_portfolio_value

            if portfolio_change > 0:
                self.logger.info(f'*** PROFIT: ${portfolio_change:.2f} ***')
            elif portfolio_change < 0:
                self.logger.info(f'*** LOSS: ${portfolio_change:.2f} ***')

            self.last_completed_portfolio_value = current_portfolio_value
            self.log(f'ULTRA-TRADE EXECUTED at {order.executed.price:.5f}')
            self.order = None

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f'ULTRA-ORDER FAILED - {order.getstatusname()}')
            self.order = None

    def log(self, txt, dt=None):
        """Enhanced logging"""
        if self.p.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            time = self.datas[0].datetime.time(0)
            current_value = self.broker.get_value()
            self.logger.info(f'{dt} {time} {txt} | Value: {current_value:.2f}')

    def notify_trade(self, trade):
        """Ultra-aggressive trade notification"""
        if trade.isclosed:
            self.trade_count += 1
            self.total_pnl += trade.pnl

            if trade.pnl > 0:
                self.winning_trades += 1

            win_rate = (self.winning_trades / self.trade_count) * 100 if self.trade_count > 0 else 0

            self.log(f'ULTRA-TRADE CLOSED - PnL: {trade.pnl:.2f} | Win Rate: {win_rate:.1f}% | Trades: {self.trade_count}')

if __name__ == '__main__':
    print("Ultra-Aggressive Maximum Returns Strategy loaded successfully")