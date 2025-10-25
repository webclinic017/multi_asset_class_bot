import sys
import os
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database_manager import DatabaseManager

def update_all_strategy_parameters():
    """Update all Market Making HFT strategy parameters in the database"""
    print("Updating all Market Making HFT strategy parameters in database...")
    
    # Initialize database manager
    db = DatabaseManager()
    
    # Get all Market Making HFT strategies directly from database
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, parameters, created_at 
            FROM strategies 
            WHERE name LIKE '%Market Making HFT%' 
            ORDER BY id DESC
        """)
        
        rows = cursor.fetchall()
        
        print(f"Found {len(rows)} Market Making HFT strategy entries:")
        
        # Define the correct parameters
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
        
        updated_count = 0
        
        for row in rows:
            strategy_id, name, parameters, created_at = row
            print(f"\nStrategy ID: {strategy_id}")
            print(f"Name: {name}")
            print(f"Created at: {created_at}")
            
            # Parse parameters
            try:
                params = json.loads(parameters) if isinstance(parameters, str) else parameters
                
                # Check if this needs to be updated
                if params.get('inventory_rebalance_threshold') != 0.8:
                    print("  *** Updating this strategy ***")
                    
                    # Update the strategy in the database
                    cursor.execute("""
                        UPDATE strategies 
                        SET parameters = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (json.dumps(updated_parameters), strategy_id))
                    conn.commit()
                    
                    updated_count += 1
                    print("  *** Successfully updated ***")
                else:
                    print("  *** Already updated ***")
                    
            except Exception as e:
                print(f"Error processing strategy {strategy_id}: {e}")
        
        print(f"\nSuccessfully updated {updated_count} strategy entries!")

if __name__ == "__main__":
    update_all_strategy_parameters()