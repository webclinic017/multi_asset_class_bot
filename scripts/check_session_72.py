from database.database_manager import DatabaseManager

db = DatabaseManager()
with db.get_connection() as conn:
    conn.row_factory = None
    cursor = conn.cursor()
    
    # Get session info
    cursor.execute('SELECT id, strategy_id, symbol, initial_capital, final_capital FROM trading_sessions WHERE id = 72')
    session = cursor.fetchone()
    print(f"Session 72:")
    print(f"  Symbol: {session[2]}")
    print(f"  Initial: ${session[3]:.2f}")
    print(f"  Final: ${session[4]:.2f}")
    print(f"  Loss: ${session[3] - session[4]:.2f}")
    print(f"  Loss %: {((session[4] - session[3]) / session[3]) * 100:.2f}%")
    
    # Get trades
    cursor.execute('SELECT id, side, entry_price, exit_price, quantity, pnl FROM trades WHERE session_id = 72')
    trades = cursor.fetchall()
    print(f"\nTrades: {len(trades)}")
    for t in trades:
        print(f"  Trade {t[0]}: {t[1]}, Entry={t[2]}, Exit={t[3]}, Qty={t[4]}, PnL={t[5]}")
        
        # Calculate expected loss
        if t[2] and t[3] and t[4]:
            price_diff = t[3] - t[2] if t[1] == 'BUY' else t[2] - t[3]
            expected_pnl = price_diff * t[4] * 50  # Assuming $50 multiplier
            print(f"    Price diff: {price_diff:.2f} points")
            print(f"    Expected PnL: ${expected_pnl:.2f}")