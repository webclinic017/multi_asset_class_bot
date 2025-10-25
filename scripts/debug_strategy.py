import sys
import os
import json
from datetime import datetime, timedelta

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database_manager import DatabaseManager
from backtesting.realtime_backtest_engine import create_realtime_backtest_engine

def debug_strategy():
    """Debug the Market Making HFT strategy with detailed logging"""
    print("Debugging Market Making HFT strategy...")
    
    # Initialize database manager
    db = DatabaseManager()
    
    # Get the Market Making HFT strategy
    strategies = db.get_strategies()
    hft_strategy = None
    for strategy in strategies:
        if strategy['name'] == 'Market Making HFT':
            hft_strategy = strategy
            break
    
    if not hft_strategy:
        print("ERROR: Market Making HFT strategy not found in database")
        return
    
    print(f"Found strategy: {hft_strategy['name']}")
    
    # Create a test configuration with a date range that has more data
    config = {
        'backtesting': {
            'initial_capital': 100000.0,
            'commission': 0.001,
            'slippage': 0.0005,
            'start_date': '2025-08-12',  # Use date with more data
            'end_date': '2025-09-12',    # Wider range with enough data
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
    
    # Enable logging for the strategy
    strategy_params = hft_strategy['parameters'].copy()
    strategy_params['printlog'] = True
    
    # Create backtest engine
    print("Creating real-time backtest engine...")
    backtest_engine = create_realtime_backtest_engine(
        config=config,
        session_id=1,
        update_callback=None,
        websocket_manager=None
    )
    
    # Load ES data
    print("Loading ES futures data...")
    try:
        loaded_data = backtest_engine.load_data('ES', 'futures', '1h')
        print(f"Loaded data shape: {loaded_data.shape if loaded_data is not None else 'None'}")
        
        if loaded_data is None or loaded_data.empty:
            print("ERROR: Failed to load data")
            return
            
        print("First few rows of data:")
        print(loaded_data.head())
        print(f"\nData range: {loaded_data.index.min()} to {loaded_data.index.max()}")
        print(f"Total records: {len(loaded_data)}")
        
    except Exception as e:
        print(f"ERROR loading data: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Add the Market Making HFT strategy with logging enabled
    print("Adding Market Making HFT strategy with logging...")
    try:
        backtest_engine.add_strategy('MarketMakingHFTStrategy', **strategy_params)
        print("Strategy added successfully")
    except Exception as e:
        print(f"ERROR adding strategy: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Run the backtest
    print("Running backtest with detailed logging...")
    try:
        results = backtest_engine.run_with_realtime_updates()
        print("Backtest completed!")
        
        if results and isinstance(results, dict):
            print("\n=== BACKTEST RESULTS ===")
            print(f"Final portfolio value: ${results.get('final_value', 'N/A')}")
            print(f"Total return: {results.get('total_return', 'N/A')}")
            print(f"Total trades: {results.get('total_trades', 'N/A')}")
            print(f"Winning trades: {results.get('winning_trades', 'N/A')}")
            print(f"Losing trades: {results.get('losing_trades', 'N/A')}")
            print(f"Win rate: {results.get('win_rate', 'N/A')}")
            print(f"Sharpe ratio: {results.get('sharpe_ratio', 'N/A')}")
            print(f"Max drawdown: {results.get('max_drawdown', 'N/A')}")
            print(f"Portfolio snapshots: {len(results.get('portfolio_snapshots', []))}")
        else:
            print("No results returned from backtest")
            
    except Exception as e:
        print(f"ERROR running backtest: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_strategy()