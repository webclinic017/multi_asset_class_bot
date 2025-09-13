import sqlite3

conn = sqlite3.connect('database/trading_bot.db')
cursor = conn.cursor()

# Check trades for recent sessions
print("Checking trades for recent sessions:")
for session_id in [44, 43, 40]:
    cursor.execute('''
        SELECT *
        FROM trades 
        --WHERE session_id = ? AND status = 'closed'
    ''', (session_id,))
    
    result = cursor.fetchall()
    if result and result[0] > 0:
        #print(f"Session {session_id}: {result[0]} trades, {result[1]} wins, {result[2]} losses, Total P&L: ${result[3]:.2f}, Avg P&L: ${result[4]:.2f}")
        print(result)
    else:
        print(f"Session {session_id}: No closed trades found")

conn.close()