import sqlite3
import pandas as pd

conn = sqlite3.connect('trading_bot.db')
cursor = conn.cursor()

# Check trades for recent sessions
# print("Checking trades for recent sessions:")
# for session_id in [44, 43, 40]:
cursor.execute('''
    SELECT *
    FROM market_data
    --WHERE session_id = ? AND status = 'closed'
''')

rows= cursor.fetchall()
column_names = [description[0] for description in cursor.description]
df = pd.DataFrame(rows, columns=column_names)
if df is not None:
    #print(f"Session {session_id}: {result[0]} trades, {result[1]} wins, {result[2]} losses, Total P&L: ${result[3]:.2f}, Avg P&L: ${result[4]:.2f}")
    df.to_csv('data_in_sqlite.csv')
else:
    print(f"Session : No closed trades found")

conn.close()