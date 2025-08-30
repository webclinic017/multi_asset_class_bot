"""
Test script to compare the original forex strategy with the optimized version
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

from strategies.optimized_forex_strategy import OptimizedForexStrategy
from strategies.forex_strategy import ForexStrategy

def create_realistic_forex_data(start_date, end_date, initial_price=1.1000):
    """Create realistic EUR/USD-like forex data with trends and volatility"""
    
    # Generate hourly timestamps
    timestamps = pd.date_range(start=start_date, end=end_date, freq='h')
    n_periods = len(timestamps)
    
    # Set random seed for reproducible results
    np.random.seed(42)
    
    # Create multiple trend phases
    trend_length = n_periods // 6  # 6 different trend phases
    prices = []
    current_price = initial_price
    
    for phase in range(6):
        start_idx = phase * trend_length
        end_idx = min((phase + 1) * trend_length, n_periods)
        phase_length = end_idx - start_idx
        
        # Alternate between trending and ranging markets
        if phase % 3 == 0:  # Strong uptrend
            trend_strength = 0.002
        elif phase % 3 == 1:  # Strong downtrend
            trend_strength = -0.0015
        else:  # Ranging/sideways
            trend_strength = 0.0002
        
        # Generate price movements for this phase
        for i in range(phase_length):
            # Trend component
            trend_move = trend_strength + np.random.normal(0, 0.0003)
            
            # Add some mean reversion
            if len(prices) > 20:
                recent_avg = np.mean(prices[-20:])
                mean_reversion = (recent_avg - current_price) * 0.01
                trend_move += mean_reversion
            
            # Apply the move
            current_price *= (1 + trend_move)
            prices.append(current_price)
    
    # Ensure we have exactly the right number of prices
    while len(prices) < n_periods:
        prices.append(prices[-1] * (1 + np.random.normal(0, 0.0001)))
    prices = prices[:n_periods]
    
    # Create OHLC data
    data = []
    for i, close_price in enumerate(prices):
        # Generate realistic intrabar volatility
        volatility = abs(np.random.normal(0, 0.0008))
        
        # Create OHLC
        if i == 0:
            open_price = close_price
        else:
            # Open close to previous close with small gap
            open_price = data[i-1]['close'] * (1 + np.random.normal(0, 0.0001))
        
        # High and low based on volatility
        high = max(open_price, close_price) * (1 + volatility)
        low = min(open_price, close_price) * (1 - volatility)
        
        # Ensure OHLC relationships are valid
        high = max(high, open_price, close_price)
        low = min(low, open_price, close_price)
        
        # Realistic volume
        volume = np.random.randint(8000, 25000)
        
        data.append({
            'datetime': timestamps[i],
            'open': open_price,
            'high': high,
            'low': low,
            'close': close_price,
            'volume': volume
        })
    
    df = pd.DataFrame(data)
    df.set_index('datetime', inplace=True)
    return df

def run_strategy_test():
    """Test and compare forex strategies"""
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    logger.info("=== OPTIMIZED FOREX STRATEGY COMPARISON ===")
    
    # Create realistic test data
    start_date = datetime(2023, 1, 1)
    end_date = datetime(2023, 6, 30)  # 6 months of data
    
    logger.info("Generating realistic EUR/USD data...")
    forex_data = create_realistic_forex_data(start_date, end_date)
    logger.info(f"Generated {len(forex_data)} data points")
    
    # Test parameters
    initial_capital = 10000
    commission = 0.0001
    
    strategies_to_test = [
        {
            'name': 'Original ForexStrategy',
            'class': ForexStrategy,
            'params': {
                'fast_length': 10,
                'slow_length': 30,
                'stop_loss_percent': 0.01,
                'take_profit_percent': 0.02,
                'printlog': False
            }
        },
        {
            'name': 'Optimized ForexStrategy',
            'class': OptimizedForexStrategy,
            'params': {
                'fast_ema': 8,
                'slow_ema': 21,
                'rsi_oversold': 25,
                'rsi_overbought': 75,
                'stop_loss_atr': 2.0,
                'take_profit_atr': 3.0,
                'position_size_percent': 0.02,
                'printlog': False
            }
        }
    ]
    
    results = {}
    
    for strategy_config in strategies_to_test:
        logger.info(f"\n--- Testing {strategy_config['name']} ---")
        
        try:
            # Create cerebro instance
            cerebro = bt.Cerebro()
            cerebro.broker.setcash(initial_capital)
            cerebro.broker.setcommission(commission=commission)
            
            # Add data
            data_feed = bt.feeds.PandasData(
                dataname=forex_data,
                fromdate=start_date,
                todate=end_date
            )
            cerebro.adddata(data_feed)
            
            # Add strategy
            cerebro.addstrategy(strategy_config['class'], **strategy_config['params'])
            
            # Add analyzers
            cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
            cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
            cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
            cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
            
            # Run backtest
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
            
            avg_win = trade_analysis.get('won', {}).get('pnl', {}).get('average', 0.0) or 0.0
            avg_loss = trade_analysis.get('lost', {}).get('pnl', {}).get('average', 0.0) or 0.0
            
            # Store results
            results[strategy_config['name']] = {
                'final_value': final_value,
                'total_return': total_return * 100,
                'sharpe_ratio': float(sharpe_ratio),
                'max_drawdown': max_drawdown * 100,
                'total_trades': total_trades,
                'win_rate': win_rate,
                'avg_win': avg_win,
                'avg_loss': avg_loss
            }
            
            # Log results
            logger.info(f"Final Value: ${final_value:.2f}")
            logger.info(f"Total Return: {total_return * 100:.2f}%")
            logger.info(f"Sharpe Ratio: {sharpe_ratio:.4f}")
            logger.info(f"Max Drawdown: {max_drawdown * 100:.2f}%")
            logger.info(f"Total Trades: {total_trades}")
            logger.info(f"Win Rate: {win_rate:.2f}%")
            logger.info(f"Avg Win: ${avg_win:.2f}")
            logger.info(f"Avg Loss: ${avg_loss:.2f}")
            
        except Exception as e:
            logger.error(f"Error testing {strategy_config['name']}: {e}")
            results[strategy_config['name']] = None
    
    # Compare results
    logger.info("\n=== STRATEGY COMPARISON SUMMARY ===")
    
    if all(results.values()):
        original = results['Original ForexStrategy']
        optimized = results['Optimized ForexStrategy']
        
        logger.info(f"{'Metric':<20} {'Original':<15} {'Optimized':<15} {'Improvement':<15}")
        logger.info("-" * 70)
        
        metrics = [
            ('Total Return (%)', 'total_return'),
            ('Sharpe Ratio', 'sharpe_ratio'),
            ('Max Drawdown (%)', 'max_drawdown'),
            ('Win Rate (%)', 'win_rate'),
            ('Total Trades', 'total_trades')
        ]
        
        for metric_name, metric_key in metrics:
            orig_val = original[metric_key]
            opt_val = optimized[metric_key]
            
            if metric_key == 'max_drawdown':
                # For drawdown, lower is better
                if orig_val != 0:
                    improvement = f"{((orig_val - opt_val) / orig_val * 100):.1f}%"
                else:
                    improvement = "N/A"
            else:
                # For other metrics, higher is better
                if orig_val != 0:
                    improvement = f"{((opt_val - orig_val) / orig_val * 100):.1f}%"
                else:
                    improvement = "N/A"
            
            logger.info(f"{metric_name:<20} {orig_val:<15.4f} {opt_val:<15.4f} {improvement:<15}")
        
        # Overall assessment
        logger.info("\n=== FINAL ASSESSMENT ===")
        
        improvements = []
        if optimized['sharpe_ratio'] > original['sharpe_ratio']:
            improvements.append("✅ BETTER SHARPE RATIO")
        if optimized['total_return'] > original['total_return']:
            improvements.append("✅ BETTER RETURNS")
        if optimized['total_trades'] > original['total_trades']:
            improvements.append("✅ MORE ACTIVE TRADING")
        if optimized['win_rate'] > original['win_rate']:
            improvements.append("✅ HIGHER WIN RATE")
        
        if improvements:
            logger.info("OPTIMIZED STRATEGY IMPROVEMENTS:")
            for improvement in improvements:
                logger.info(f"  {improvement}")
        else:
            logger.info("❌ No significant improvements detected")
        
        # Success criteria
        if optimized['sharpe_ratio'] > 0 and optimized['total_trades'] > 0:
            logger.info("\n🎉 SUCCESS: Optimized strategy achieves positive Sharpe ratio with active trading!")
        else:
            logger.info("\n⚠️  WARNING: Strategy needs further optimization")
    
    return results

if __name__ == "__main__":
    results = run_strategy_test()