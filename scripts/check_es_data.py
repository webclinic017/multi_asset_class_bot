from database.database_manager import DatabaseManager

def check_es_data():
    db = DatabaseManager()
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT symbol, timeframe, COUNT(*) as count FROM market_data WHERE symbol LIKE '%ES%' GROUP BY symbol, timeframe ORDER BY count DESC")
        results = cursor.fetchall()
        print("ES-related market data:")
        for row in results:
            print(f"Symbol: {row[0]}, Timeframe: {row[1]}, Count: {row[2]}")
        
        # Also check for any futures symbols
        cursor.execute("SELECT symbol, timeframe, COUNT(*) as count FROM market_data WHERE symbol LIKE '%CL%' OR symbol LIKE '%NG%' OR symbol LIKE '%GC%' GROUP BY symbol, timeframe ORDER BY count DESC")
        results = cursor.fetchall()
        print("\nOther futures market data:")
        for row in results:
            print(f"Symbol: {row[0]}, Timeframe: {row[1]}, Count: {row[2]}")

if __name__ == "__main__":
    check_es_data()