import sys
import os
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database_manager import DatabaseManager

def update_strategy_parameters():
    """Update strategy parameters in the database to match the strategy file"""
    print("Updating strategy parameters in database...")
    
    # Initialize database manager
    db = DatabaseManager()
    
    # Get the Market Making HFT strategy
    strategies = db.get_strategies()
    hft_strategies = [s for s in strategies if s['name'] == 'Market Making HFT']
    
    if not hft_strategies:
        print("ERROR: Market Making HFT strategy not found in database")
        return
    
    # Use the most recent strategy entry
    hft_strategy = hft_strategies[0]  # They're ordered by created_at DESC
    strategy_id = hft_strategy['id']
    
    print(f"Found strategy: {hft_strategy['name']} (ID: {strategy_id})")
    print(f"Current parameters: {hft_strategy['parameters']}")
    
    # Update parameters to match the strategy file
    updated_parameters = {
        'spread_width': 0.25,
        'max_inventory': 10,
        'inventory_rebalance_threshold': 0.8,  # Changed from 3 to 0.8
        'quote_refresh_time': 5,
        'min_spread': 0.25,
        'max_spread': 2.0,
        'volatility_lookback': 20,
        'risk_limit': 0.02,
        'max_orders_per_side': 3,
        'order_size': 1,
        'adaptive_spread': True,
        'printlog': False
    }
    
    print(f"Updating parameters to: {updated_parameters}")
    
    # Update the strategy in the database using direct SQL
    print("Using direct SQL update...")
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE strategies 
                SET parameters = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (json.dumps(updated_parameters), strategy_id))
            conn.commit()
        
        print("Successfully updated strategy parameters in database")
        
        # Verify the update
        updated_strategy = db.get_strategy(strategy_id)
        print(f"Updated parameters: {updated_strategy['parameters']}")
    except Exception as e:
        print(f"ERROR updating strategy parameters: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    update_strategy_parameters()