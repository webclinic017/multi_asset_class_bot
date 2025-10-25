import sys
import os
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database_manager import DatabaseManager

def check_db_strategies():
    """Check all strategy entries in the database directly"""
    print("Checking all strategy entries in database...")
    
    # Initialize database manager
    db = DatabaseManager()
    
    # Get all strategies directly from database
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
        
        for row in rows:
            strategy_id, name, parameters, created_at = row
            print(f"\nStrategy ID: {strategy_id}")
            print(f"Name: {name}")
            print(f"Created at: {created_at}")
            
            # Parse parameters
            try:
                params = json.loads(parameters) if isinstance(parameters, str) else parameters
                print(f"Parameters: {params}")
                
                # Check if this is the one we updated
                if params.get('inventory_rebalance_threshold') == 0.8:
                    print("  *** This is the updated strategy ***")
                elif params.get('inventory_rebalance_threshold') == 3:
                    print("  *** This has the old parameters ***")
            except Exception as e:
                print(f"Error parsing parameters: {e}")
                print(f"Raw parameters: {parameters}")

if __name__ == "__main__":
    check_db_strategies()