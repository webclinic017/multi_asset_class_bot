from database.database_manager import DatabaseManager

def check_market_data():
    db = DatabaseManager()
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT symbol, timeframe, COUNT(*) as count FROM market_data GROUP BY symbol, timeframe ORDER BY count DESC")
        results = cursor.fetchall()
        print("Market data summary:")
        for row in results[:10]:
            print(f"Symbol: {row[0]}, Timeframe: {row[1]}, Count: {row[2]}")

if __name__ == "__main__":
    check_market_data()