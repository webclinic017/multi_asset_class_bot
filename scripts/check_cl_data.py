"""
Script to check CL data in the database
"""
import sys
import os
import logging
from datetime import datetime

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.database_manager import DatabaseManager

def check_cl_data():
    """Check CL data in the database"""
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Initialize database manager
    db_manager = DatabaseManager()
    
    # Check data for CL symbol
    symbol = 'CL'
    timeframe = '1h'
    
    logger.info(f"Checking data for {symbol} {timeframe}...")
    
    # Get data from database
    df = db_manager.get_market_data(
        symbol=symbol,
        timeframe=timeframe,
        start_time=None,
        end_time=None,
        limit=10000
    )
    
    if df is None or df.empty:
        logger.info(f"No data found for {symbol} {timeframe}")
        return
    
    logger.info(f"Found {len(df)} records for {symbol} {timeframe}")
    logger.info(f"Date range: {df.index.min()} to {df.index.max()}")
    logger.info(f"Columns: {list(df.columns)}")
    
    # Show first few rows
    logger.info(f"First 5 rows:")
    logger.info(df.head())
    
    # Show last few rows
    logger.info(f"Last 5 rows:")
    logger.info(df.tail())

if __name__ == "__main__":
    check_cl_data()