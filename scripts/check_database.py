import sqlite3
import pandas as pd
from database.database_manager import DatabaseManager

# Check database connection and data
db = DatabaseManager()
print('=== DATABASE CHECK ===')

# Check strategies
strategies = db.get_strategies()
print(f'Strategies count: {len(strategies)}')
if strategies:
    print('Sample strategies:')
    for s in strategies[:3]:
        print(f'  - {s["name"]} (ID: {s["id"]})')

# Check trading sessions
sessions = db.get_trading_sessions(limit=10)
print(f'\nTrading sessions count: {len(sessions)}')
if sessions:
    print('Sample sessions:')
    for s in sessions[:3]:
        print(f'  - ID: {s["id"]}, Type: {s["session_type"]}, Status: {s["status"]}, Trades: {s.get("total_trades", 0)}')

# Check trades
trades = db.get_trades(limit=5)
print(f'\nTrades count: {len(trades)}')
if trades:
    print('Sample trades:')
    for t in trades[:3]:
        print(f'  - ID: {t["id"]}, Session: {t["session_id"]}, P&L: {t.get("pnl", "N/A")}')

# Check market data
print('\nMarket data symbols:')
with db.get_connection() as conn:
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT symbol FROM market_data LIMIT 10')
    symbols = cursor.fetchall()
    print([s[0] for s in symbols])