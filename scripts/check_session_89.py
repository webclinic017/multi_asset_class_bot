import sqlite3

conn = sqlite3.connect('database/trading_bot.db')
cursor = conn.cursor()

# Check portfolio snapshots for session 89
cursor.execute("""
    SELECT total_value, timestamp
    FROM portfolio_snapshots
    WHERE session_id = 89
    ORDER BY timestamp ASC
""")

snapshots = cursor.fetchall()
print(f"Session 89 has {len(snapshots)} portfolio snapshots:")
for i, (value, timestamp) in enumerate(snapshots):
    print(f"  {i+1}. ${value:.2f} at {timestamp}")

# Calculate value changes
if len(snapshots) > 1:
    print(f"\nValue changes:")
    for i in range(1, len(snapshots)):
        prev_value = snapshots[i-1][0]
        curr_value = snapshots[i][0]
        change = curr_value - prev_value
        print(f"  Change {i}: ${change:.2f} ({'WIN' if change > 0 else 'LOSS'})")

# Check session details
cursor.execute("SELECT * FROM trading_sessions WHERE id = 89")
session = cursor.fetchone()
print(f"\nSession 89 details:")
print(f"  Total trades: {session[7] if len(session) > 7 else 'N/A'}")
print(f"  Winning trades: {session[8] if len(session) > 8 else 'N/A'}")
print(f"  Losing trades: {session[9] if len(session) > 9 else 'N/A'}")
print(f"  Final capital: {session[6] if len(session) > 6 else 'N/A'}")

conn.close()