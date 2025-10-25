"""
Test script for running a backtest with the corrected Market Making HFT strategy
"""
import sys
import os
import logging
from datetime import datetime

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.database_manager import DatabaseManager
from backtesting.realtime_backtest_engine import create_realtime_backtest_engine

def test_hft_strategy():
    """Test the Market Making HFT strategy with corrected parameters"""
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Initialize database manager
    db_manager = DatabaseManager()
    
    # Create a test strategy with corrected parameters
    strategy_id = db_manager.create_strategy(
        name="Market Making HFT",
        description="Test Market Making HFT strategy with corrected parameters",
        strategy_type="hft",
        asset_class="futures",
        timeframe="1h",  # Changed to 1h to match available data
        parameters={
            'spread_width': 0.25,
            'max_inventory': 10,
            'inventory_rebalance_threshold': 0.8,  # Corrected parameter
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
    
    logger.info(f"Created test strategy with ID: {strategy_id}")
    
    # Create a test session
    session_id = db_manager.create_trading_session(
        session_type="backtest",
        strategy_id=strategy_id,
        symbol="CL",  # Changed to CL (Crude Oil) which we know has data
        initial_capital=100000.0
    )
    
    logger.info(f"Created test session with ID: {session_id}")
    
    # Configuration for backtest engine - use dates that match available data
    config = {
        'backtesting': {
            'initial_capital': 100000.0,
            'commission': 0.001,
            'slippage': 0.0005,
            'start_date': '2024-01-01',  # Use full available data range
            'end_date': '2024-03-01',    # Extended period for better analysis
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
    
    logger.info("Backtest engine created successfully")
    
    # Load data for the backtest
    asset_type = 'futures'
    symbol = 'CL'
    timeframe = '1h'
    
    logger.info(f"Loading data for {symbol} ({asset_type}, {timeframe})...")
    loaded_data = backtest_engine.load_data(symbol, asset_type, timeframe)
    
    if loaded_data is None or loaded_data.empty:
        logger.error(f"Failed to load data for {symbol}")
        return None
    
    logger.info(f"Successfully loaded {len(loaded_data)} data points")
    logger.info(f"Data date range: {loaded_data.index.min()} to {loaded_data.index.max()}")
    
    # Add strategy to engine with parameters
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
    
    # Run backtest with real-time updates
    logger.info("Starting backtest...")
    results = backtest_engine.run_with_realtime_updates()
    
    logger.info("Backtest completed")
    logger.info(f"Results: {results}")
    
    return results

if __name__ == "__main__":
    test_hft_strategy()