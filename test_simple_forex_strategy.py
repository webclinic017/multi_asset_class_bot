"""
Simple test for forex strategy with guaranteed trade execution
"""

import logging
import pandas as pd
import numpy as np
import backtrader as bt
from datetime import datetime, timedelta
import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from strategies.improved_forex_strategy import ImprovedForexStrategy

def create_simple_trending_data(periods=1000, initial_price=1.1000):
    """Create simple trending data that will definitely trigger trades"""
    
    timestamps = pd.date_range(start='2023-01-01', periods=periods, freq='h')
    
    # Create clear uptrend for first half, downtrend for second half
    half = periods // 2
    
    # Strong uptrend
    uptrend = np.linspace(initial_price, initial_price * 1.05, half)
    # Strong downtrend  
    downtrend = np.linspace(initial_price * 1.05, initial_price * 0.98, periods - half)
    
    prices = np.concatenate([uptrend, downtrend])
    
    # Add minimal noise
    noise = np.random.normal(0, 0.0001, periods)
    prices = prices + noise
    
    # Create OHLC data
    data = []
    for i, price in enumerate(prices):
        # Simple OHLC with small spreads
        spread = price * 0.0002
        
        high = price + spread
        low = price - spread
        open_price = prices[i-1] if i > 0 else price
        
        data.append({
            'datetime': timestamps[i],
            'open': open_price,
            'high': high,
            'low': low,
            'close': price,
            'volume': 10000
        })
    
    df = pd.DataFrame(data)
    df.set_index('datetime', inplace=True)
    return df

def test_simple_strategy():
    """Test the improved strategy with simple parameters"""
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    logger.info("=== SIMPLE FOREX STRATEGY TEST ===")
    
    # Create simple trending data
    forex_data = create_simple_trending_data(periods=500)
    logger.info(f"Generated {len(forex_data)} data points")
    
    # Create cerebro instance
    cerebro = bt.Cerebro()
    cerebro.broker.setcash(10000)
    cerebro.broker.setcommission(commission=0.0001)
    
    # Add data
    data_feed = bt.feeds.PandasData(dataname=forex_data)
    cerebro.adddata(data_feed)
    
    # Add strategy with relaxed parameters to ensure trades
    cerebro.addstrategy(
        ImprovedForexStrategy,
        fast_length=5,           # Very short periods
        slow_length=15,          # Short periods
        rsi_period=10,           # Short RSI
        rsi_oversold=20,         # More relaxed RSI levels
        rsi_overbought=80,
        stop_loss_percent=0.02,  # Wider stops
        take_profit_percent=0.04, # Wider targets
        position_size_percent=0.1, # Larger position size
        trend_strength_threshold=0.1, # Lower threshold
        min_volatility=0.00001,  # Very low minimum
        max_volatility=0.1,      # High maximum
        printlog=True            # Enable logging
    )
    
    # Add analyzers
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    
    # Run backtest
    logger.info("Running backtest...")
    strategies = cerebro.run()
    strategy = strategies[0]
    
    # Get results
    final_value = cerebro.broker.getvalue()
    
    # Extract metrics safely
    sharpe_analysis = strategy.analyzers.sharpe.get_analysis()
    drawdown_analysis = strategy.analyzers.drawdown.get_analysis()
    returns_analysis = strategy.analyzers.returns.get_analysis()
    trade_analysis = strategy.analyzers.trades.get_analysis()
    
    sharpe_ratio = sharpe_analysis.get('sharperatio', 0.0) or 0.0
    max_drawdown = drawdown_analysis.get('max', {}).get('drawdown', 0.0) or 0.0
    total_return = returns_analysis.get('rtot', 0.0) or 0.0
    
    total_trades = trade_analysis.get('total', {}).get('closed', 0) or 0
    winning_trades = trade_analysis.get('won', {}).get('total', 0) or 0
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
    
    # Log results
    logger.info(f"\n=== RESULTS ===")
    logger.info(f"Initial Capital: $10,000.00")
    logger.info(f"Final Value: ${final_value:.2f}")
    logger.info(f"Total Return: {total_return * 100:.2f}%")
    logger.info(f"Sharpe Ratio: {sharpe_ratio:.4f}")
    logger.info(f"Max Drawdown: {max_drawdown * 100:.2f}%")
    logger.info(f"Total Trades: {total_trades}")
    logger.info(f"Win Rate: {win_rate:.2f}%")
    
    if total_trades > 0:
        logger.info("✅ SUCCESS: Strategy executed trades!")
        if sharpe_ratio > 0:
            logger.info("✅ SUCCESS: Positive Sharpe ratio achieved!")
        else:
            logger.info("⚠️  WARNING: Sharpe ratio is not positive")
    else:
        logger.info("❌ FAILURE: No trades were executed")
    
    return {
        'final_value': final_value,
        'total_return': total_return,
        'sharpe_ratio': sharpe_ratio,
        'max_drawdown': max_drawdown,
        'total_trades': total_trades,
        'win_rate': win_rate
    }

if __name__ == "__main__":
    results = test_simple_strategy()