import sqlite3

conn = sqlite3.connect('database/trading_bot.db')
cursor = conn.cursor()

# Fix final capital for sessions with real trades
print("Fixing final capital calculations...")

cursor.execute('''
    SELECT ts.id, ts.initial_capital, 
           COALESCE(SUM(t.pnl), 0) as total_pnl,
           COUNT(t.id) as trade_count
    FROM trading_sessions ts
    LEFT JOIN trades t ON ts.id = t.session_id AND t.status = 'closed'
    WHERE ts.status = 'completed' AND ts.session_type = 'backtest'
    GROUP BY ts.id, ts.initial_capital
    HAVING trade_count > 0
''')

sessions_to_fix = cursor.fetchall()

for session_id, initial_capital, total_pnl, trade_count in sessions_to_fix:
    correct_final_capital = initial_capital + total_pnl
    correct_total_return = total_pnl / initial_capital
    
    print(f"Session {session_id}: Initial: ${initial_capital}, P&L: ${total_pnl:.2f}, Correct Final: ${correct_final_capital:.2f}")
    
    # Update the session with correct final capital
    cursor.execute('''
        UPDATE trading_sessions 
        SET final_capital = ?, total_return = ?
        WHERE id = ?
    ''', (correct_final_capital, correct_total_return, session_id))

conn.commit()
print(f"Fixed {len(sessions_to_fix)} sessions with correct final capital calculations")
conn.close()