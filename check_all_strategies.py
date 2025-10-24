import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database_manager import DatabaseManager
import json

def check_all_strategies():
    """Check all strategy entries in the database"""
    print("Checking all strategy entries in database...")
    
    # Initialize database manager
    db = DatabaseManager()
    
    # Get all strategies
    strategies = db.get_strategies()
    
    # Filter for Market Making HFT strategies
    hft_strategies = [s for s in strategies if s['name'] == 'Market Making HFT']
    
    print(f"Found {len(hft_strategies)} Market Making HFT strategy entries:")
    
    for strategy in hft_strategies:
        print(f"\nStrategy ID: {strategy['id']}")
        print(f"Created at: {strategy['created_at']}")
        print(f"Parameters: {strategy['parameters']}")
        
        # Check if this is the one we updated
        if strategy['parameters'].get('inventory_rebalance_threshold') == 0.8:
            print("  *** This is the updated strategy ***")
        elif strategy['parameters'].get('inventory_rebalance_threshold') == 3:
            print("  *** This has the old parameters ***")

if __name__ == "__main__":
    check_all_strategies()