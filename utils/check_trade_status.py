import sqlite3

conn = sqlite3.connect('database/trading_bot.db')
cursor = conn.cursor()

# Check trade status for sessions with missing final capital
print("Checking trade status for sessions with missing final capital:")

for session_id in [44, 43]:
    print(f"\nSession {session_id}:")
    
    # Check all trades for this session
    cursor.execute('''
        SELECT status, COUNT(*) as count, SUM(pnl) as total_pnl
        FROM trades 
        WHERE session_id = ?
        GROUP BY status
    ''', (session_id,))
    
    trade_status = cursor.fetchall()
    for status, count, pnl in trade_status:
        print(f"  Status '{status}': {count} trades, Total P&L: ${pnl:.2f if pnl else 0}")
    
    # Get sample trades
    cursor.execute('''
        SELECT id, status, pnl, exit_time
        FROM trades 
        WHERE session_id = ?
        LIMIT 3
    ''', (session_id,))
    
    sample_trades = cursor.fetchall()
    print(f"  Sample trades:")
    for trade_id, status, pnl, exit_time in sample_trades:
        print(f"    Trade {trade_id}: Status='{status}', P&L=${pnl:.2f if pnl else 0}, Exit={exit_time}")

conn.close()