#!/usr/bin/env python3
"""
Scale past backtest results from $10k to $100k initial capital
This updates the database to reflect the impact of $100k initial capital on all past tests
"""

import sqlite3
import json
from datetime import datetime

def scale_backtest_results():
    """Scale all $10k backtest results to $100k equivalent"""

    # Connect to database
    conn = sqlite3.connect('database/trading_bot.db')
    cursor = conn.cursor()

    print("Scaling past backtest results from $10k to $100k initial capital...")

    # Get all backtest sessions with $10k initial capital
    cursor.execute("""
        SELECT id, initial_capital, final_capital, total_return, max_drawdown
        FROM trading_sessions
        WHERE session_type = 'backtest' AND initial_capital = 10000.0
    """)

    sessions_to_scale = cursor.fetchall()
    print(f"Found {len(sessions_to_scale)} sessions with $10k initial capital to scale")

    scaling_factor = 10.0  # 10x scaling from $10k to $100k

    for session_id, initial_capital, final_capital, total_return, max_drawdown in sessions_to_scale:
        # Scale the final capital
        new_final_capital = final_capital * scaling_factor if final_capital else None

        # Total return remains the same (it's a percentage)
        # Max drawdown remains the same (it's a percentage)

        # Update the session
        cursor.execute("""
            UPDATE trading_sessions
            SET initial_capital = ?, final_capital = ?
            WHERE id = ?
        """, (100000.0, new_final_capital, session_id))

        print(f"[OK] Scaled session {session_id}: ${initial_capital:,.0f} -> $100,000.00, Final: ${final_capital or 0:,.0f} -> ${new_final_capital or 0:,.0f}")

    # Also scale any portfolio snapshots for these sessions
    for session_id, _, _, _, _ in sessions_to_scale:
        cursor.execute("""
            UPDATE portfolio_snapshots
            SET total_value = total_value * ?, cash_balance = cash_balance * ?
            WHERE session_id = ?
        """, (scaling_factor, scaling_factor, session_id))

        print(f"[DATA] Scaled portfolio snapshots for session {session_id}")

    # Scale trade P&L values for these sessions
    for session_id, _, _, _, _ in sessions_to_scale:
        cursor.execute("""
            UPDATE trades
            SET pnl = pnl * ?, pnl_pips = pnl_pips * ?
            WHERE session_id = ?
        """, (scaling_factor, scaling_factor, session_id))

        print(f"[PNL] Scaled trade P&L for session {session_id}")

    # Commit changes
    conn.commit()

    # Get updated counts
    cursor.execute("""
        SELECT COUNT(*) FROM trading_sessions
        WHERE session_type = 'backtest' AND initial_capital = 100000.0
    """)

    total_100k_sessions = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) FROM trading_sessions
        WHERE session_type = 'backtest' AND initial_capital = 10000.0
    """)

    remaining_10k_sessions = cursor.fetchone()[0]

    conn.close()

    print("\n=== SCALING COMPLETE ===")
    print(f"Total $100k backtest sessions: {total_100k_sessions}")
    print(f"Remaining $10k backtest sessions: {remaining_10k_sessions}")
    print("\nAll past backtest data now reflects $100k initial capital impact!")
    print("New backtests will automatically use $100k initial capital.")

if __name__ == "__main__":
    scale_backtest_results()