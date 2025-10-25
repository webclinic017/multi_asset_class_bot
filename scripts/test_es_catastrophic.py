"""
Test script to reproduce the ES futures -99.9% catastrophic loss
"""
import sys
import os
import logging
from datetime import datetime

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.database_manager import DatabaseManager
from backtesting.realtime_backtest_engine import create_realtime_backtest_engine

def test_es_catastrophic_loss():
    """Test ES futures to reproduce the -99.9% catastrophic loss"""
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    
    # Initialize database manager
    db_manager = DatabaseManager()
    
    # Create a test strategy similar to what might be used in frontend
    strategy_id = db_manager.create_strategy(
        name="ES Futures Test Strategy",
        description="Test strategy to reproduce ES futures catastrophic loss",
        strategy_type="hft",
        asset_class="futures",
        timeframe="1h",
        parameters={
            'spread_width': 0.25,
            'max_inventory': 10,
            'inventory_rebalance_threshold': 0.8,
            'quote_refresh_time': 5,
            'min_spread': 0.25,
            'max_spread': 2.0,
            'volatility_lookback': 20,
            'risk_limit': 0.02,
            'max_orders_per_side': 3,
            'order_size': 1,
            'adaptive_spread': True,
            'printlog': True
        }
    )
    
    # Create session
    session_id = db_manager.create_trading_session(
        session_type="backtest",
        strategy_id=strategy_id,
        symbol="ES",  # E-mini S&P 500 - the problematic symbol
        initial_capital=100000.0
    )
    
    # Configuration for backtest engine
    config = {
        'backtesting': {
            'initial_capital': 100000.0,
            'commission': 0.001,
            'slippage': 0.0005,
            'start_date': '2024-01-01',
            'end_date': '2024-03-01',
            'asset_class': 'futures'
        },
        'oanda': {
            'account_id': 'test',
            'access_token': 'test',
            'practice': True
        },
        'ibkr': {
            'host': '127.0.0.1',
            'port': 7497,
            'client_id': 1
        }
    }
    
    # Create backtest engine
    backtest_engine = create_realtime_backtest_engine(
        config=config,
        session_id=session_id
    )
    
    logger.info("Loading ES futures data...")
    loaded_data = backtest_engine.load_data('ES', 'futures', '1h')
    
    if loaded_data is None or loaded_data.empty:
        logger.error("Failed to load ES data")
        return None
    
    logger.info(f"Successfully loaded {len(loaded_data)} ES data points")
    logger.info(f"ES data range: {loaded_data.index.min()} to {loaded_data.index.max()}")
    logger.info(f"ES price range: ${loaded_data['close'].min():.2f} to ${loaded_data['close'].max():.2f}")
    
    # Add strategy to engine
    backtest_engine.add_strategy('MarketMakingHFTStrategy', 
                                spread_width=0.25,
                                max_inventory=10,
                                inventory_rebalance_threshold=0.8,
                                quote_refresh_time=5,
                                min_spread=0.25,
                                max_spread=2.0,
                                volatility_lookback=20,
                                risk_limit=0.02,
                                max_orders_per_side=3,
                                order_size=1,
                                adaptive_spread=True,
                                printlog=True)
    
    # Run backtest
    logger.info("Starting ES futures backtest...")
    result = backtest_engine.run_with_realtime_updates()
    
    if result and isinstance(result, dict):
        logger.info("ES backtest completed")
        
        # Extract key metrics
        final_value = result.get('final_value', 100000.0)
        total_return = result.get('total_return', 0.0)
        max_drawdown = result.get('max_drawdown', 0.0)
        total_trades = result.get('total_trades', 0)
        
        logger.info(f"ES Results:")
        logger.info(f"  Final Value: ${final_value:.2f}")
        logger.info(f"  Total Return: {total_return:.2f}%")
        logger.info(f"  Max Drawdown: {max_drawdown:.2f}%")
        logger.info(f"  Total Trades: {total_trades}")
        
        # Check if this is the catastrophic loss
        if total_return < -50:  # Catastrophic loss threshold
            logger.error(f"🚨 CATASTROPHIC LOSS DETECTED: {total_return:.2f}% 🚨")
            logger.error(f"Final value: ${final_value:.2f} (lost ${100000 - final_value:.2f})")
            
            # Get detailed trade information
            trades = result.get('trades', [])
            if trades:
                logger.error("Detailed trade analysis:")
                for i, trade in enumerate(trades):
                    logger.error(f"  Trade {i+1}: {trade}")
        
        return result
    else:
        logger.error("ES backtest failed")
        return None

if __name__ == "__main__":
    print("Testing ES futures to reproduce catastrophic loss...")
    result = test_es_catastrophic_loss()
    
    if result:
        print(f"\nFinal result: {result.get('total_return', 0):.2f}% return")
    else:
        print("Test failed")