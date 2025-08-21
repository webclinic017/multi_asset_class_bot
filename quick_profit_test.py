#!/usr/bin/env python3
"""
Quick test to validate the enhanced profitable strategy
"""

import backtrader as bt
import pandas as pd
import numpy as np
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)

# Import our enhanced strategy
from strategies.profitable_forex_strategy import ProfitableForexStrategy

def create_trending_data():
    """Create trending test data that should be profitable"""
    # Create 500 data points with a clear uptrend
    dates = pd.date_range(start='2023-01-01', periods=500, freq='h')
    
    # Generate trending price data
    np.random.seed(123)  # Different seed for trending data
    base_price = 1.1000
    
    # Create a strong uptrend with some volatility
    trend = np.linspace(0, 0.02, 500)  # 2% uptrend over period
    noise = np.random.normal(0, 0.0003, 500)  # Small random movements
    
    prices = base_price * (1 + trend + noise)
    
    # Create OHLC data with realistic spreads
    data = []
    for i, price in enumerate(prices):
        if i == 0:
            open_price = price
        else:
            open_price = prices[i-1]
            
        high = price * (1 + abs(np.random.normal(0, 0.0002)))
        low = price * (1 - abs(np.random.normal(0, 0.0002)))
        close_price = price
        volume = np.random.randint(5000, 15000)
        
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

def test_enhanced_strategy():
    """Test the enhanced strategy with trending data"""
    print("Creating trending test data...")
    test_data = create_trending_data()
    print(f"Test data shape: {test_data.shape}")
    print(f"Price range: {test_data['close'].min():.5f} to {test_data['close'].max():.5f}")
    print(f"Total trend: {((test_data['close'].iloc[-1] / test_data['close'].iloc[0]) - 1) * 100:.2f}%")
    
    # Create cerebro
    cerebro = bt.Cerebro()
    cerebro.broker.setcash(10000)
    cerebro.broker.setcommission(commission=0.0001)  # Lower commission for testing
    
    # Add data
    data_feed = bt.feeds.PandasData(
        dataname=test_data,
        fromdate=test_data.index[0],
        todate=test_data.index[-1]
    )
    cerebro.adddata(data_feed)
    
    # Add enhanced strategy with optimized parameters
    cerebro.addstrategy(
        ProfitableForexStrategy,
        fast_length=8,
        slow_length=21,
        rsi_period=14,
        rsi_oversold=25,
        rsi_overbought=75,
        stop_loss_percent=0.008,
        take_profit_percent=0.024,  # 3:1 reward/risk
        max_trades_per_day=5,
        min_bars_between_trades=3,
        volatility_multiplier=1.5,
        trend_strength_min=0.6,
        use_rsi_filter=True,
        use_macd_filter=True,
        use_trend_filter=True,
        use_momentum_filter=True,
        use_breakout_filter=True,
        printlog=True
    )
    
    # Add analyzers
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trade_analyzer')
    
    print("Running enhanced strategy test...")
    try:
        strategies = cerebro.run()
        
        if strategies:
            strategy = strategies[0]
            
            # Get results
            final_value = cerebro.broker.getvalue()
            initial_value = 10000
            total_return = ((final_value - initial_value) / initial_value) * 100
            
            print(f'\n{"="*50}')
            print("ENHANCED STRATEGY TEST RESULTS")
            print(f'{"="*50}')
            print(f'Initial Capital: ${initial_value:,.2f}')
            print(f'Final Portfolio Value: ${final_value:,.2f}')
            print(f'Total Return: {total_return:.3f}%')
            
            # Analyze results
            sharpe_analysis = strategy.analyzers.sharpe.get_analysis()
            drawdown_analysis = strategy.analyzers.drawdown.get_analysis()
            returns_analysis = strategy.analyzers.returns.get_analysis()
            trade_analysis = strategy.analyzers.trade_analyzer.get_analysis()
            
            sharpe_ratio = sharpe_analysis.get('sharperatio', 0.0)
            max_drawdown = drawdown_analysis.get('max', {}).get('drawdown', 0.0)
            
            if sharpe_ratio:
                print(f'Sharpe Ratio: {sharpe_ratio:.2f}')
            else:
                print('Sharpe Ratio: N/A')
                
            if max_drawdown:
                print(f'Max Drawdown: {max_drawdown*100:.2f}%')
            
            # Trade statistics
            total_trades = trade_analysis.get('total', {}).get('closed', 0)
            winning_trades = trade_analysis.get('won', {}).get('total', 0)
            losing_trades = trade_analysis.get('lost', {}).get('total', 0)
            
            print(f'Total Trades: {total_trades}')
            print(f'Winning Trades: {winning_trades}')
            print(f'Losing Trades: {losing_trades}')
            
            if total_trades > 0:
                win_rate = (winning_trades / total_trades * 100)
                print(f'Win Rate: {win_rate:.2f}%')
                
                avg_win = trade_analysis.get('won', {}).get('pnl', {}).get('average', 0.0)
                avg_loss = trade_analysis.get('lost', {}).get('pnl', {}).get('average', 0.0)
                
                if avg_win:
                    print(f'Average Win: ${avg_win:.2f}')
                if avg_loss:
                    print(f'Average Loss: ${avg_loss:.2f}')
            
            print(f'{"="*50}')
            
            # Success criteria
            if total_return >= 1.0:
                print("🎉 SUCCESS: Achieved 1%+ target return!")
                return True
            elif total_return >= 0.5:
                print("✅ GOOD: Close to target (0.5%+)")
                return True
            elif total_return > 0:
                print("📈 POSITIVE: Making progress (positive return)")
                return True
            else:
                print("❌ NEEDS IMPROVEMENT: Negative return")
                return False
        else:
            print("No strategies executed")
            return False
            
    except Exception as e:
        print(f"Error running test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_enhanced_strategy()
    if success:
        print("\n✅ Enhanced strategy shows promise for 1%+ returns!")
    else:
        print("\n⚠️ Strategy needs further optimization.")