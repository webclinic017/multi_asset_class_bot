from database.database_manager import DatabaseManager

db = DatabaseManager()
with db.get_connection() as conn:
    conn.row_factory = None  # Get tuples instead of Row objects
    cursor = conn.cursor()
    
    # Get session info
    cursor.execute('SELECT id, strategy_id, symbol, initial_capital, final_capital, total_return FROM trading_sessions WHERE id = 69')
    session = cursor.fetchone()
    print(f"Session 69:")
    print(f"  ID: {session[0]}, Strategy: {session[1]}, Symbol: {session[2]}")
    print(f"  Initial: ${session[3]:.2f}, Final: ${session[4]:.2f}")
    actual_return = ((session[4] - session[3]) / session[3]) * 100
    print(f"  Actual Return: {actual_return:.2f}%")
    print(f"  Stored Return: {session[5]*100 if session[5] else 0:.2f}%")
    
    # Get trades with all columns
    cursor.execute('''SELECT id, session_id, symbol, side, entry_time, exit_time,
                      entry_price, exit_price, quantity, pnl, pnl_pips, status, exit_reason
                      FROM trades WHERE session_id = 69''')
    trades = cursor.fetchall()
    print(f"\nTrades for session 69 ({len(trades)} trades):")
    for trade in trades:
        print(f"\n  Trade ID: {trade[0]}")
        print(f"    Symbol: {trade[2]}, Side: {trade[3]}")
        print(f"    Entry: {trade[4]}, Exit: {trade[5]}")
        print(f"    Entry Price: {trade[6]}, Exit Price: {trade[7]}, Quantity: {trade[8]}")
        print(f"    P&L: {trade[9]}, Status: {trade[11]}, Exit Reason: {trade[12]}")
        
        # Calculate what the loss should be
        if trade[6] and trade[7] and trade[8]:
            price_diff = trade[7] - trade[6] if trade[3] == 'BUY' else trade[6] - trade[7]
            expected_pnl = price_diff * trade[8]
            print(f"    Expected P&L: {expected_pnl:.2f}")
        
    # Get portfolio snapshots
    cursor.execute('SELECT timestamp, total_value, cash_balance, unrealized_pnl FROM portfolio_snapshots WHERE session_id = 69 ORDER BY timestamp')
    snapshots = cursor.fetchall()
    print(f"\nPortfolio snapshots ({len(snapshots)} snapshots):")
    for i, snap in enumerate(snapshots):
        print(f"  {i+1}. Time: {snap[0]}, Value: ${snap[1]:.2f}, Cash: ${snap[2]:.2f}, Unrealized: ${snap[3]:.2f}")