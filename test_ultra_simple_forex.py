"""
Ultra simple forex strategy test that will definitely execute trades
"""

import logging
import pandas as pd
import numpy as np
import backtrader as bt
from datetime import datetime
import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class UltraSimpleForexStrategy(bt.Strategy):
    """Ultra simple strategy that will definitely trade"""
    
    params = (
        ('fast_period', 3),
        ('slow_period', 7),
        ('printlog', True)
    )
    
    def log(self, txt, dt=None):
        if self.p.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            logging.info(f'{dt.isoformat()} {txt}')
    
    def __init__(self):
        self.dataclose = self.datas[0].close
        self.order = None
        self.bar_executed = 0
        
        # Very simple moving averages
        self.sma_fast = bt.indicators.SMA(self.datas[0], period=self.p.fast_period)
        self.sma_slow = bt.indicators.SMA(self.datas[0], period=self.p.slow_period)
        self.crossover = bt.indicators.CrossOver(self.sma_fast, self.sma_slow)
        
        self.trade_count = 0
        
    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED: Price {order.executed.price:.5f}')
            else:
                self.log(f'SELL EXECUTED: Price {order.executed.price:.5f}')
            self.bar_executed = len(self)
        self.order = None
    
    def next(self):
        if self.order:
            return
            
        # Skip first few bars to let indicators initialize
        if len(self.data) < self.p.slow_period + 1:
            return
            
        current_price = self.dataclose[0]
        self.log(f'Close: {current_price:.5f}, Fast SMA: {self.sma_fast[0]:.5f}, Slow SMA: {self.sma_slow[0]:.5f}')
        
        if not self.position:
            # Simple crossover strategy
            if self.crossover > 0:  # Fast MA crosses above slow MA
                self.log(f'BUY SIGNAL - Fast MA crossed above Slow MA')
                self.order = self.buy(size=1000)  # Fixed size
                self.trade_count += 1
                
            elif self.crossover < 0:  # Fast MA crosses below slow MA
                self.log(f'SELL SIGNAL - Fast MA crossed below Slow MA')
                self.order = self.sell(size=1000)  # Fixed size
                self.trade_count += 1
        else:
            # Simple exit after 10 bars
            if len(self) - self.bar_executed >= 10:
                self.log(f'EXIT SIGNAL - Time-based exit')
                self.close()
    
    def notify_trade(self, trade):
        if trade.isclosed:
            self.log(f'TRADE CLOSED: PnL {trade.pnl:.2f}')

def create_zigzag_data(periods=200):
    """Create zigzag data that will definitely trigger crossovers"""
    
    timestamps = pd.date_range(start='2023-01-01', periods=periods, freq='h')
    
    # Create alternating up and down segments
    segment_length = 20
    price = 1.1000
    prices = []
    
    for i in range(periods):
        segment = i // segment_length
        position_in_segment = i % segment_length
        
        if segment % 2 == 0:  # Up segment
            price_change = 0.001 * position_in_segment
        else:  # Down segment
            price_change = -0.001 * position_in_segment
            
        current_price = 1.1000 + price_change + np.random.normal(0, 0.0001)
        prices.append(current_price)
    
    # Create OHLC data
    data = []
    for i, price in enumerate(prices):
        spread = 0.0001
        data.append({
            'datetime': timestamps[i],
            'open': price,
            'high': price + spread,
            'low': price - spread,
            'close': price,
            'volume': 1000
        })
    
    df = pd.DataFrame(data)
    df.set_index('datetime', inplace=True)
    return df

def test_ultra_simple():
    """Test ultra simple strategy"""
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    logger.info("=== ULTRA SIMPLE FOREX TEST ===")
    
    # Create zigzag data
    forex_data = create_zigzag_data(periods=100)
    logger.info(f"Generated {len(forex_data)} data points")
    
    # Create cerebro
    cerebro = bt.Cerebro()
    cerebro.broker.setcash(10000)
    cerebro.broker.setcommission(commission=0.0001)
    
    # Add data
    data_feed = bt.feeds.PandasData(dataname=forex_data)
    cerebro.adddata(data_feed)
    
    # Add strategy
    cerebro.addstrategy(UltraSimpleForexStrategy, printlog=True)
    
    # Add analyzers
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    
    # Run
    logger.info("Running backtest...")
    strategies = cerebro.run()
    strategy = strategies[0]
    
    # Results
    final_value = cerebro.broker.getvalue()
    
    sharpe_analysis = strategy.analyzers.sharpe.get_analysis()
    trade_analysis = strategy.analyzers.trades.get_analysis()
    
    sharpe_ratio = sharpe_analysis.get('sharperatio', 0.0) or 0.0
    total_trades = trade_analysis.get('total', {}).get('closed', 0) or 0
    
    logger.info(f"\n=== RESULTS ===")
    logger.info(f"Final Value: ${final_value:.2f}")
    logger.info(f"Total Return: {((final_value - 10000) / 10000) * 100:.2f}%")
    logger.info(f"Sharpe Ratio: {sharpe_ratio:.4f}")
    logger.info(f"Total Trades: {total_trades}")
    logger.info(f"Strategy Trade Count: {strategy.trade_count}")
    
    if total_trades > 0:
        logger.info("✅ SUCCESS: Trades were executed!")
        return True
    else:
        logger.info("❌ FAILURE: No trades executed")
        return False

if __name__ == "__main__":
    success = test_ultra_simple()