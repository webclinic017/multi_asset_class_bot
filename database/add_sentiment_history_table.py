"""
Add sentiment_history table to store historical sentiment data for backtesting
This enables accurate sentiment analysis during historical backtests
"""

import sqlite3
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_sentiment_history_table():
    """Add sentiment_history table to the database"""
    
    db_path = "database/trading_bot.db"
    
    if not os.path.exists(db_path):
        logger.error(f"Database not found at {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create sentiment_history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sentiment_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol VARCHAR(20) NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                sentiment_score DECIMAL(10,6) NOT NULL,
                news_count INTEGER DEFAULT 0,
                confidence DECIMAL(10,6) DEFAULT 0,
                signal VARCHAR(20),
                category VARCHAR(50),
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, timestamp)
            )
        """)
        
        # Create index for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sentiment_symbol_timestamp 
            ON sentiment_history(symbol, timestamp)
        """)
        
        conn.commit()
        logger.info("✓ sentiment_history table created successfully")
        
        # Verify table was created
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='sentiment_history'
        """)
        
        if cursor.fetchone():
            logger.info("✓ Table verified in database")
            
            # Show table schema
            cursor.execute("PRAGMA table_info(sentiment_history)")
            columns = cursor.fetchall()
            
            logger.info("Table schema:")
            for col in columns:
                logger.info(f"  - {col[1]} ({col[2]})")
            
            return True
        else:
            logger.error("✗ Table creation failed")
            return False
            
    except Exception as e:
        logger.error(f"Error creating sentiment_history table: {e}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    logger.info("=" * 80)
    logger.info("Adding sentiment_history table to database")
    logger.info("=" * 80)
    
    success = add_sentiment_history_table()
    
    if success:
        logger.info("\n✓ sentiment_history table added successfully!")
        logger.info("\nNext steps:")
        logger.info("1. Run scripts/populate_sentiment_history.py to populate historical data")
        logger.info("2. Strategy will automatically use historical sentiment during backtests")
    else:
        logger.error("\n✗ Failed to add sentiment_history table")