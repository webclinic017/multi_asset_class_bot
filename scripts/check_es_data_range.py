from database.database_manager import DatabaseManager
from datetime import datetime

def check_es_data_range():
    db = DatabaseManager()
    
    # Check what date range we have for ES data
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT MIN(timestamp), MAX(timestamp), COUNT(*) as count 
            FROM market_data 
            WHERE symbol = 'ES' AND timeframe = '1h'
        """)
        result = cursor.fetchone()
        
        if result:
            min_date, max_date, count = result
            print(f"ES data range: {min_date} to {max_date}")
            print(f"Total records: {count}")
            
            # Try to load more data with a wider date range
            print("\nTrying to load data with wider date range...")
            try:
                # Load data from beginning to end
                es_data = db.get_market_data('ES', '1h')
                print(f"Full dataset shape: {es_data.shape}")
                print(f"Date range: {es_data.index.min()} to {es_data.index.max()}")
                
                # Check if we have enough data
                if len(es_data) >= 200:
                    print("SUCCESS: Have enough data for backtesting")
                else:
                    print(f"WARNING: Only {len(es_data)} records, need at least 200")
                    
            except Exception as e:
                print(f"Error loading full dataset: {e}")

if __name__ == "__main__":
    check_es_data_range()