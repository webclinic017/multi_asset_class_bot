#!/usr/bin/env python3
"""
Debug script to test the ProfitableForexStrategy in isolation
"""

import backtrader as bt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)

# Import our strategy
from strategies.profitable_forex_strategy import ProfitableForexStrategy

def create_test_data():
    """Create simple test data for debugging"""
    # Create 1000 data points
    dates = pd.date_range(start='2023-01-01', periods=1000, freq='H')
    
    # Generate realistic forex price data
    np.random.seed(42)
    base_price = 1.1000
    
    # Generate price movements
    returns = np.random.normal(0, 0.0005, 1000)  # Small random movements
    prices = [base_price]
    
    for ret in returns[1:]:
        prices.append(prices[-1] * (1 + ret))
    
    # Create OHLC data
    data = []
    for i, price in enumerate(prices):
        high = price * (1 + abs(np.random.normal(0, 0.0002)))
        low = price * (1 - abs(np.random.normal(0, 0.0002)))
        open_price = prices[i-1] if i > 0 else price
        close_price = price
        volume = np.random.randint(1000, 10000)
        
        data.append({
            'datetime': dates[i],
            'open': open_price,
            'high': max(open_price, high, close_price),
            'low': min(open_price, low, close_price),
            'close': close_price,
            'volume': volume
        })
    
    df = pd.DataFrame(data)
    df.set_index('datetime', inplace=True)
    return df

def test_strategy():
    """Test the strategy with simple data"""
    print("Creating test data...")
    test_data = create_test_data()
    print(f"Test data shape: {test_data.shape}")
    print(f"Test data head:\n{test_data.head()}")
    
    # Create cerebro
    cerebro = bt.Cerebro()
    cerebro.broker.setcash(10000)
    cerebro.broker.setcommission(commission=0.001)
    
    # Add data
    data_feed = bt.feeds.PandasData(
        dataname=test_data,
        fromdate=test_data.index[0],
        todate=test_data.index[-1]
    )
    cerebro.adddata(data_feed)
    
    # Add strategy with simple parameters
    cerebro.addstrategy(
        ProfitableForexStrategy,
        fast_length=10,
        slow_length=30,
        rsi_period=14,
        rsi_oversold=30,
        rsi_overbought=70,
        stop_loss_percent=0.01,
        take_profit_percent=0.02,
        max_trades_per_day=3,
        min_bars_between_trades=5,
        printlog=True
    )
    
    # Add analyzers
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trade_analyzer')
    
    print("Running backtest...")
    try:
        strategies = cerebro.run()
        
        if strategies:
            strategy = strategies[0]
            
            # Get results
            final_value = cerebro.broker.getvalue()
            print(f'Final Portfolio Value: {final_value:.2f}')
            
            # Analyze results
            sharpe_analysis = strategy.analyzers.sharpe.get_analysis()
            drawdown_analysis = strategy.analyzers.drawdown.get_analysis()
            returns_analysis = strategy.analyzers.returns.get_analysis()
            trade_analysis = strategy.analyzers.trade_analyzer.get_analysis()
            
            print(f"Sharpe analysis: {sharpe_analysis}")
            print(f"Drawdown analysis: {drawdown_analysis}")
            print(f"Returns analysis: {returns_analysis}")
            print(f"Trade analysis: {trade_analysis}")
            
            # Extract metrics safely
            sharpe_ratio = sharpe_analysis.get('sharperatio', 0.0)
            max_drawdown = drawdown_analysis.get('max', {}).get('drawdown', 0.0)
            total_return = returns_analysis.get('rtot', 0.0)
            
            print(f"Sharpe Ratio: {sharpe_ratio}")
            print(f"Max Drawdown: {max_drawdown}")
            print(f"Total Return: {total_return}")
            
            # Trade statistics
            total_trades = trade_analysis.get('total', {}).get('closed', 0)
            winning_trades = trade_analysis.get('won', {}).get('total', 0)
            losing_trades = trade_analysis.get('lost', {}).get('total', 0)
            
            print(f"Total Trades: {total_trades}")
            print(f"Winning Trades: {winning_trades}")
            print(f"Losing Trades: {losing_trades}")
            
            if total_trades > 0:
                win_rate = (winning_trades / total_trades * 100)
                print(f"Win Rate: {win_rate:.2f}%")
            
            return {
                'final_value': final_value,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown * 100 if max_drawdown else 0.0,
                'total_return': total_return * 100 if total_return else 0.0,
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
            }
        else:
            print("No strategies executed")
            return None
            
    except Exception as e:
        print(f"Error running backtest: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    results = test_strategy()
    if results:
        print("\n" + "="*50)
        print("STRATEGY TEST RESULTS")
        print("="*50)
        for key, value in results.items():
            print(f"{key}: {value}")
    else:
        print("Strategy test failed!")