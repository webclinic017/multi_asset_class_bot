import sqlite3

conn = sqlite3.connect('database/trading_bot.db')
cursor = conn.cursor()

# Get column names for trading_sessions table
cursor.execute("PRAGMA table_info(trading_sessions)")
columns = cursor.fetchall()

print("trading_sessions table columns:")
for col in columns:
    print(f"  {col[0]}: {col[1]} ({col[2]})")

# Get session 89 data with column names
cursor.execute("SELECT * FROM trading_sessions WHERE id = 89")
row = cursor.fetchone()

print(f"\nSession 89 raw data:")
for i, col in enumerate(columns):
    col_name = col[1]
    value = row[i] if i < len(row) else None
    print(f"  {col_name}: {value}")

conn.close()