import sqlite3

conn = sqlite3.connect('database/trading_bot.db')
cursor = conn.cursor()

# Check available market data
cursor.execute('''
    SELECT symbol, timeframe, COUNT(*) as count, 
           MIN(timestamp) as start_date, MAX(timestamp) as end_date 
    FROM market_data 
    GROUP BY symbol, timeframe 
    ORDER BY count DESC 
    LIMIT 10
''')

rows = cursor.fetchall()
print('Available market data:')
for row in rows:
    print(f'Symbol: {row[0]}, Timeframe: {row[1]}, Records: {row[2]}, From: {row[3]}, To: {row[4]}')

print('\nTotal market data records:', cursor.execute('SELECT COUNT(*) FROM market_data').fetchone()[0])

conn.close()