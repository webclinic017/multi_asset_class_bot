from database.database_manager import DatabaseManager
import json

db = DatabaseManager()

# Create new backtest-optimized strategy
strategy_params = {
    'spread_width': 0.15,
    'max_inventory': 15,
    'inventory_rebalance_threshold': 0.6,
    'quote_refresh_time': 3,
    'min_spread': 0.15,
    'max_spread': 1.5,
    'volatility_lookback': 15,
    'risk_limit': 0.03,
    'max_orders_per_side': 5,
    'order_size': 1,
    'adaptive_spread': True,
    'printlog': False,
    'rsi_oversold': 35,
    'rsi_overbought': 65,
    'min_bars_between_trades': 5
}

strategy_id = db.create_strategy(
    name="Backtest Market Making",
    description="Market making strategy optimized for backtesting with Market orders and multiple entry signals",
    strategy_type="market_making",
    asset_class="futures",
    timeframe="1m",
    parameters=strategy_params
)

print(f"Created new strategy with ID: {strategy_id}")
print(f"Strategy name: Backtest Market Making")
print(f"Parameters: {json.dumps(strategy_params, indent=2)}")
print("\nThis strategy uses:")
print("- Market orders for reliable execution")
print("- Multiple entry signals (RSI, Bollinger Bands, EMA crossovers)")
print("- Tight stop losses and take profits (0.5%)")
print("- Minimum 5 bars between trades")
print("\nExpected to generate 50-200+ trades per year")