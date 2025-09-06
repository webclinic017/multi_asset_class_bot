import sqlite3

conn = sqlite3.connect('database/trading_bot.db')
cursor = conn.cursor()

# Check recent sessions
cursor.execute('''
    SELECT id, session_type, symbol, initial_capital, final_capital, 
           total_return, total_trades, winning_trades, losing_trades, status 
    FROM trading_sessions 
    ORDER BY id DESC LIMIT 5
''')

rows = cursor.fetchall()
print('Recent sessions:')
for row in rows:
    print(f'ID: {row[0]}, Type: {row[1]}, Symbol: {row[2]}, Initial: {row[3]}, Final: {row[4]}, Return: {row[5]}, Trades: {row[6]}, Wins: {row[7]}, Losses: {row[8]}, Status: {row[9]}')

conn.close()