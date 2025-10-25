import sys
import os
import json
from datetime import datetime, timedelta

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database_manager import DatabaseManager
from backtesting.realtime_backtest_engine import create_realtime_backtest_engine

def test_strategy_orders():
    """Test if the Market Making HFT strategy is placing orders"""
    print("Testing Market Making HFT strategy order placement...")
    
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
    
    # Create a test configuration
    config = {
        'backtesting': {
            'initial_capital': 100000.0,
            'commission': 0.001,
            'slippage': 0.0005,
            'start_date': '2025-08-12',
            'end_date': '2025-09-12',
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
            
        print(f"Data range: {loaded_data.index.min()} to {loaded_data.index.max()}")
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
    
    # Add a custom analyzer to track orders
    print("Adding order tracking analyzer...")
    try:
        from backtrader import Analyzer
        
        class OrderTracker(Analyzer):
            def __init__(self):
                super().__init__()
                self.orders = []
                self.trades = []
                
            def notify_order(self, order):
                if order.status in [order.Completed]:
                    self.orders.append({
                        'type': 'buy' if order.isbuy() else 'sell',
                        'price': order.executed.price,
                        'size': order.executed.size,
                        'datetime': self.strategy.data.datetime.datetime(0)
                    })
                    
            def notify_trade(self, trade):
                if trade.isclosed:
                    self.trades.append({
                        'pnl': trade.pnl,
                        'pnlcomm': trade.pnlcomm,
                        'datetime': self.strategy.data.datetime.datetime(0)
                    })
                    
            def get_analysis(self):
                return {
                    'orders': self.orders,
                    'trades': self.trades
                }
        
        backtest_engine.cerebro.addanalyzer(OrderTracker, _name='order_tracker')
        print("Order tracker analyzer added")
        
    except Exception as e:
        print(f"ERROR adding order tracker: {e}")
    
    # Run the backtest
    print("Running backtest with order tracking...")
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
            
            # Check order tracking results
            if 'strategies' in results and len(results['strategies']) > 0:
                strategy = results['strategies'][0]
                if hasattr(strategy, 'analyzers'):
                    for analyzer in strategy.analyzers:
                        if hasattr(analyzer, '_name') and analyzer._name == 'order_tracker':
                            analysis = analyzer.get_analysis()
                            print(f"\n=== ORDER TRACKING ===")
                            print(f"Total orders tracked: {len(analysis.get('orders', []))}")
                            print(f"Total trades tracked: {len(analysis.get('trades', []))}")
                            
                            if analysis.get('orders'):
                                print("Sample orders:")
                                for i, order in enumerate(analysis['orders'][:5]):  # Show first 5 orders
                                    print(f"  {i+1}. {order['type']} {order['size']} @ {order['price']:.2f} on {order['datetime']}")
                            
                            if analysis.get('trades'):
                                print("Sample trades:")
                                for i, trade in enumerate(analysis['trades'][:5]):  # Show first 5 trades
                                    print(f"  {i+1}. P&L: {trade['pnl']:.2f} on {trade['datetime']}")
        else:
            print("No results returned from backtest")
            
    except Exception as e:
        print(f"ERROR running backtest: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_strategy_orders()