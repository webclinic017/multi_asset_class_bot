"""
Add fundamental_data table to existing database
Migration script for FRED/EIA/USDA data storage
"""

import sqlite3
import os
import sys

# Get database path - use the same path as DatabaseManager default
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trading_bot.db")

print(f"Database path: {db_path}")
print(f"Database exists: {os.path.exists(db_path)}")

# Connect to database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Create fundamental_data table
create_table_sql = """
CREATE TABLE IF NOT EXISTS fundamental_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol VARCHAR(20) NOT NULL,
    data_source VARCHAR(20) NOT NULL,
    series_name VARCHAR(100) NOT NULL,
    series_id VARCHAR(100),
    timestamp TIMESTAMP NOT NULL,
    value DECIMAL(15,6),
    metadata TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, data_source, series_name, timestamp)
);
"""

print("\nCreating fundamental_data table...")
cursor.execute(create_table_sql)

# Create indexes
print("Creating indexes...")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_fundamental_data_symbol ON fundamental_data(symbol);")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_fundamental_data_source ON fundamental_data(data_source);")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_fundamental_data_timestamp ON fundamental_data(timestamp);")

conn.commit()

# Verify table was created
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='fundamental_data'")
result = cursor.fetchone()

if result:
    print("✓ fundamental_data table created successfully!")
    
    # Check table structure
    cursor.execute("PRAGMA table_info(fundamental_data)")
    columns = cursor.fetchall()
    print("\nTable structure:")
    for col in columns:
        print(f"  - {col[1]} ({col[2]})")
else:
    print("✗ Failed to create fundamental_data table")

conn.close()
print("\nDone!")