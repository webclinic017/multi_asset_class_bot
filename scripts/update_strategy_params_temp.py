from database.database_manager import DatabaseManager
import json

db = DatabaseManager()

# More aggressive parameters to generate more trades
new_params = {
    'spread_width': 0.15,  # Reduced from 0.25 - tighter spread = more trades
    'max_inventory': 15,  # Increased from 10 - allow more positions
    'inventory_rebalance_threshold': 0.6,  # Reduced from 0.8 - rebalance more often
    'quote_refresh_time': 3,  # Reduced from 5 - update quotes more frequently
    'min_spread': 0.15,  # Reduced from 0.25 - tighter minimum spread
    'max_spread': 1.5,  # Reduced from 2.0 - tighter maximum spread
    'volatility_lookback': 15,  # Reduced from 20 - more responsive to volatility
    'risk_limit': 0.03,  # Increased from 0.02 - allow more risk per trade
    'max_orders_per_side': 5,  # Increased from 3 - more orders = more opportunities
    'order_size': 1,  # Keep same
    'adaptive_spread': True,  # Keep adaptive
    'printlog': False  # Disable verbose logging
}

# Update the strategy
with db.get_connection() as conn:
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE strategies SET parameters = ? WHERE id = 4675',
        (json.dumps(new_params),)
    )
    conn.commit()

print('Strategy 4675 (Original Market Making) updated with more aggressive parameters:')
print(json.dumps(new_params, indent=2))
print('\nKey changes to generate more trades:')
print('- Tighter spreads (0.25 -> 0.15) = more competitive quotes')
print('- More frequent quote updates (5s -> 3s) = more opportunities')
print('- Higher inventory limits (10 -> 15) = more positions')
print('- More orders per side (3 -> 5) = more market presence')
print('- Lower rebalance threshold (0.8 -> 0.6) = more active rebalancing')