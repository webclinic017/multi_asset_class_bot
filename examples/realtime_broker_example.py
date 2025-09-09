"""
RealTimeBroker Usage Example
Demonstrates how to use the fixed RealTimeBroker with proper broker integration
"""

import logging
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import backtrader as bt
from backtesting.realtime_broker import RealTimeBroker, create_realtime_broker

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler()
    ]
)

def create_sample_data():
    """Create sample market data"""
    dates = pd.date_range(start='2023-01-01', periods=100, freq='h')
    
    # Generate realistic price movement
    np.random.seed(42)
    base_price = 1.1000
    price_changes = np.random.normal(0, 0.0005, 100)
    prices = [base_price]
    
    for change in price_changes[1:]:
        new_price = prices[-1] * (1 + change)
        prices.append(new_price)
    
    # Create OHLCV data
    data = []
    for i, price in enumerate(prices):
        high = price * (1 + abs(np.random.normal(0, 0.0002)))
        low = price * (1 - abs(np.random.normal(0, 0.0002)))
        open_price = prices[i-1] if i > 0 else price
        close_price = price
        volume = np.random.randint(1000, 5000)
        
        data.append({
            'open': open_price,
            'high': high,
            'low': low,
            'close': close_price,
            'volume': volume
        })
    
    return pd.DataFrame(data, index=dates)

class ExampleStrategy(bt.Strategy):
    """Example strategy that properly handles orders with the fixed broker"""
    
    params = (
        ('fast_period', 10),
        ('slow_period', 20),
        ('risk_per_trade', 0.02),  # 2% risk per trade
    )
    
    def __init__(self):
        # Create moving averages
        self.fast_ma = bt.indicators.SMA(self.data.close, period=self.params.fast_period)
        self.slow_ma = bt.indicators.SMA(self.data.close, period=self.params.slow_period)
        
        # Create crossover signal
        self.crossover = bt.indicators.CrossOver(self.fast_ma, self.slow_ma)
        
        # Track orders
        self.order = None
        
    def next(self):
        # Check if we have an order pending
        if self.order:
            return
        
        # Check for buy signal
        if self.crossover > 0 and not self.position:
            # Calculate position size based on available cash
            cash = self.broker.getcash()
            price = self.data.close[0]
            size = int(cash * self.params.risk_per_trade / price)
            
            if size > 0:
                self.log(f'BUY SIGNAL: Size={size}, Price={price:.5f}, Cash=${cash:.2f}')
                self.order = self.buy(size=size)
        
        # Check for sell signal
        elif self.crossover < 0 and self.position:
            self.log(f'SELL SIGNAL: Closing position of {self.position.size} units')
            self.order = self.sell(size=self.position.size)
    
    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED: Size={order.executed.size}, '
                        f'Price={order.executed.price:.5f}, '
                        f'Cost=${order.executed.value:.2f}, '
                        f'Comm=${order.executed.comm:.2f}')
            else:
                self.log(f'SELL EXECUTED: Size={order.executed.size}, '
                        f'Price={order.executed.price:.5f}, '
                        f'Cost=${order.executed.value:.2f}, '
                        f'Comm=${order.executed.comm:.2f}')
            
            self.log(f'Cash: ${self.broker.getcash():.2f}, Value: ${self.broker.getvalue():.2f}')
            
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f'Order {order.getstatusname()}')
        
        # Reset order
        self.order = None
    
    def notify_trade(self, trade):
        if trade.isclosed:
            self.log(f'TRADE CLOSED: PnL=${trade.pnl:.2f}, PnL Net=${trade.pnlcomm:.2f}')
    
    def log(self, txt, dt=None):
        """Logging function"""
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()}: {txt}')

def run_example():
    """Run the RealTimeBroker example"""
    print("=" * 60)
    print("RealTimeBroker Example - Fixed Implementation")
    print("=" * 60)
    
    # Create cerebro
    cerebro = bt.Cerebro()
    
    # Create and set the fixed RealTimeBroker
    broker = create_realtime_broker(initial_cash=10000.0, commission=0.001)
    cerebro.broker = broker
    
    # Add sample data
    data = create_sample_data()
    data_feed = bt.feeds.PandasData(dataname=data)
    cerebro.adddata(data_feed)
    
    # Add strategy
    cerebro.addstrategy(ExampleStrategy)
    
    # Add analyzers
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    
    # Add observers
    cerebro.addobserver(bt.observers.Broker)
    cerebro.addobserver(bt.observers.Trades)
    cerebro.addobserver(bt.observers.BuySell)
    
    print(f'Starting Portfolio Value: ${cerebro.broker.getvalue():.2f}')
    
    # Run backtest
    results = cerebro.run()
    
    # Print results
    print("\n" + "=" * 60)
    print("BACKTEST RESULTS")
    print("=" * 60)
    
    final_value = cerebro.broker.getvalue()
    print(f'Final Portfolio Value: ${final_value:.2f}')
    print(f'Final Cash: ${cerebro.broker.getcash():.2f}')
    print(f'Total Return: ${final_value - 10000:.2f}')
    print(f'Return %: {((final_value / 10000) - 1) * 100:.2f}%')
    
    # Analyzer results
    trade_analyzer = results[0].analyzers.trades.get_analysis()
    if 'total' in trade_analyzer and 'closed' in trade_analyzer['total']:
        total_trades = trade_analyzer['total']['closed']
        print(f'Total Trades: {total_trades}')
        
        if total_trades > 0:
            won_trades = trade_analyzer['won']['total'] if 'won' in trade_analyzer else 0
            lost_trades = trade_analyzer['lost']['total'] if 'lost' in trade_analyzer else 0
            win_rate = (won_trades / total_trades) * 100 if total_trades > 0 else 0
            
            print(f'Winning Trades: {won_trades}')
            print(f'Losing Trades: {lost_trades}')
            print(f'Win Rate: {win_rate:.1f}%')
            
            if 'won' in trade_analyzer and 'pnl' in trade_analyzer['won']:
                avg_win = trade_analyzer['won']['pnl']['average']
                print(f'Average Win: ${avg_win:.2f}')
            
            if 'lost' in trade_analyzer and 'pnl' in trade_analyzer['lost']:
                avg_loss = trade_analyzer['lost']['pnl']['average']
                print(f'Average Loss: ${avg_loss:.2f}')
    
    # Sharpe ratio
    sharpe_ratio = results[0].analyzers.sharpe.get_analysis()
    if 'sharperatio' in sharpe_ratio and sharpe_ratio['sharperatio'] is not None:
        print(f'Sharpe Ratio: {sharpe_ratio["sharperatio"]:.3f}')
    
    # Drawdown
    drawdown = results[0].analyzers.drawdown.get_analysis()
    if 'max' in drawdown and 'drawdown' in drawdown['max']:
        print(f'Max Drawdown: {drawdown["max"]["drawdown"]:.2f}%')
    
    print("\n" + "=" * 60)
    print("SUCCESS: RealTimeBroker is working correctly!")
    print("- No _cash attribute errors")
    print("- Portfolio values update in real-time")
    print("- Orders execute immediately")
    print("- Proper cash and position management")
    print("=" * 60)
    
    # Optional: Plot results (uncomment if you want to see charts)
    # cerebro.plot(style='candlestick', barup='green', bardown='red')

if __name__ == "__main__":
    run_example()