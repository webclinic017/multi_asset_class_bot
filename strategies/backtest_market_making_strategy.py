"""
Backtest-Optimized Market Making Strategy
Modified to use Market orders for reliable backtest execution
"""

import backtrader as bt
import logging
import numpy as np
from typing import Dict, Any, Tuple
from datetime import datetime, timedelta

class BacktestMarketMakingStrategy(bt.Strategy):
    """
    Market Making Strategy optimized for backtesting
    Uses Market orders instead of Limit orders for reliable execution
    """

    params = (
        ('spread_width', 0.15),  # Spread threshold for entry
        ('max_inventory', 15),
        ('inventory_rebalance_threshold', 0.6),
        ('quote_refresh_time', 3),
        ('min_spread', 0.15),
        ('max_spread', 1.5),
        ('volatility_lookback', 15),
        ('risk_limit', 0.03),
        ('max_orders_per_side', 5),
        ('order_size', 1),
        ('adaptive_spread', True),
        ('printlog', False),
        # New parameters for more aggressive trading
        ('rsi_oversold', 35),  # Enter long when RSI < 35
        ('rsi_overbought', 65),  # Enter short when RSI > 65
        ('min_bars_between_trades', 5),  # Minimum bars between trades
    )

    def __init__(self, initial_capital=None):
        self.logger = logging.getLogger(__name__)
        
        # Data feeds
        self.dataclose = self.datas[0].close
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low
        
        # Position tracking
        self.inventory = 0
        self.in_position = False
        self.bars_since_trade = 0
        
        # Indicators
        self.atr = bt.indicators.ATR(period=self.p.volatility_lookback)
        self.sma_fast = bt.indicators.SMA(period=10)
        self.sma_slow = bt.indicators.SMA(period=20)
        self.rsi = bt.indicators.RSI(period=14)
        self.ema_fast = bt.indicators.EMA(period=8)
        self.ema_slow = bt.indicators.EMA(period=21)
        
        # Bollinger Bands for mean reversion
        self.bbands = bt.indicators.BollingerBands(period=20, devfactor=2.0)
        
        # Performance tracking
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        
        self.logger.info("Backtest Market Making Strategy initialized")

    def next(self):
        """Main trading logic - uses Market orders for reliable execution"""
        try:
            # Increment bars counter
            self.bars_since_trade += 1
            
            # Get current position
            position = self.getposition(self.data)
            current_size = position.size
            
            # Update inventory
            self.inventory = current_size
            self.in_position = (current_size != 0)
            
            # Wait minimum bars between trades
            if self.bars_since_trade < self.p.min_bars_between_trades:
                return
            
            current_price = self.dataclose[0]
            
            # Calculate signals
            rsi_value = self.rsi[0]
            price_vs_sma = (current_price - self.sma_slow[0]) / self.sma_slow[0] * 100
            bb_position = (current_price - self.bbands.lines.mid[0]) / (self.bbands.lines.top[0] - self.bbands.lines.bot[0])
            
            # EMA crossover
            ema_bullish = self.ema_fast[0] > self.ema_slow[0]
            ema_bearish = self.ema_fast[0] < self.ema_slow[0]
            
            # ENTRY SIGNALS - Multiple conditions for more trades
            
            # Long entry conditions (any of these triggers a buy)
            long_signal = (
                (rsi_value < self.p.rsi_oversold) or  # Oversold
                (current_price < self.bbands.lines.bot[0]) or  # Below lower BB
                (ema_bullish and price_vs_sma < -0.5) or  # Bullish crossover with price below SMA
                (current_price < self.sma_fast[0] * 0.998)  # Price significantly below fast SMA
            )
            
            # Short entry conditions (any of these triggers a sell)
            short_signal = (
                (rsi_value > self.p.rsi_overbought) or  # Overbought
                (current_price > self.bbands.lines.top[0]) or  # Above upper BB
                (ema_bearish and price_vs_sma > 0.5) or  # Bearish crossover with price above SMA
                (current_price > self.sma_fast[0] * 1.002)  # Price significantly above fast SMA
            )
            
            # EXIT SIGNALS
            
            # Exit long position
            if current_size > 0:
                exit_long = (
                    (rsi_value > 60) or  # RSI back to neutral/overbought
                    (current_price > self.bbands.lines.mid[0]) or  # Price back above mid BB
                    (current_price > position.price * 1.005) or  # Take profit at 0.5%
                    (current_price < position.price * 0.995)  # Stop loss at 0.5%
                )
                
                if exit_long:
                    self.sell(size=current_size, exectype=bt.Order.Market)
                    self.bars_since_trade = 0
                    self.logger.info(f"EXIT LONG: Size={current_size}, Price={current_price:.5f}, RSI={rsi_value:.1f}")
                    return
            
            # Exit short position
            elif current_size < 0:
                exit_short = (
                    (rsi_value < 40) or  # RSI back to neutral/oversold
                    (current_price < self.bbands.lines.mid[0]) or  # Price back below mid BB
                    (current_price < position.price * 0.995) or  # Take profit at 0.5%
                    (current_price > position.price * 1.005)  # Stop loss at 0.5%
                )
                
                if exit_short:
                    self.buy(size=abs(current_size), exectype=bt.Order.Market)
                    self.bars_since_trade = 0
                    self.logger.info(f"EXIT SHORT: Size={abs(current_size)}, Price={current_price:.5f}, RSI={rsi_value:.1f}")
                    return
            
            # ENTER NEW POSITIONS (only if not in position)
            
            if not self.in_position:
                # Enter long
                if long_signal:
                    size = self.p.order_size
                    self.buy(size=size, exectype=bt.Order.Market)
                    self.bars_since_trade = 0
                    self.total_trades += 1
                    self.logger.info(f"ENTER LONG: Size={size}, Price={current_price:.5f}, RSI={rsi_value:.1f}, BB_pos={bb_position:.2f}")
                
                # Enter short
                elif short_signal:
                    size = self.p.order_size
                    self.sell(size=size, exectype=bt.Order.Market)
                    self.bars_since_trade = 0
                    self.total_trades += 1
                    self.logger.info(f"ENTER SHORT: Size={size}, Price={current_price:.5f}, RSI={rsi_value:.1f}, BB_pos={bb_position:.2f}")
            
        except Exception as e:
            self.logger.error(f"Error in next(): {e}")

    def notify_order(self, order):
        """Handle order notifications"""
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f"BUY EXECUTED: {order.executed.size} @ {order.executed.price:.5f}")
            else:
                self.log(f"SELL EXECUTED: {order.executed.size} @ {order.executed.price:.5f}")

    def notify_trade(self, trade):
        """Handle trade notifications"""
        if trade.isclosed:
            if trade.pnl > 0:
                self.winning_trades += 1
            else:
                self.losing_trades += 1
            self.log(f"Trade closed - PnL: {trade.pnl:.2f}, Total: W={self.winning_trades} L={self.losing_trades}")

    def log(self, txt, dt=None):
        """Logging function"""
        if self.p.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            self.logger.info(f'{dt.isoformat()} {txt}')

    def stop(self):
        """Strategy stop"""
        # Close any remaining positions
        position = self.getposition(self.data)
        if position.size != 0:
            if position.size > 0:
                self.sell(size=position.size, exectype=bt.Order.Market)
            else:
                self.buy(size=abs(position.size), exectype=bt.Order.Market)
        
        win_rate = (self.winning_trades / max(self.total_trades, 1)) * 100 if self.total_trades > 0 else 0
        
        self.logger.info("=== BACKTEST MARKET MAKING STRATEGY RESULTS ===")
        self.logger.info(f"Total Trades: {self.total_trades}")
        self.logger.info(f"Winning Trades: {self.winning_trades}")
        self.logger.info(f"Losing Trades: {self.losing_trades}")
        self.logger.info(f"Win Rate: {win_rate:.1f}%")
        self.logger.info(f"Final Portfolio Value: ${self.broker.get_value():.2f}")

if __name__ == '__main__':
    print("Backtest Market Making Strategy loaded successfully")