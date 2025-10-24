"""
Script to load test data for futures backtesting
"""
import sys
import os
import logging
from datetime import datetime, timedelta

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.futures_data_loader import FuturesDataLoader

def load_test_data():
    """Load test data for futures backtesting"""
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Initialize data loader
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database", "trading_bot.db")
    loader = FuturesDataLoader(db_path=db_path)
    
    # Load data for a few symbols
    symbols = ['ES', 'CL', 'GC']  # E-mini S&P 500, Crude Oil, Gold
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    end_date = datetime.now().strftime('%Y-%m-%d')
    intervals = ['1h']
    
    logger.info(f"Loading test data from {start_date} to {end_date}")
    
    for symbol in symbols:
        logger.info(f"\nLoading data for {symbol}...")
        
        # Clear existing data
        loader.clear_existing_data(symbol, '1h')
        
        # Fetch fresh data
        df = loader.fetch_futures_data(symbol, start_date, end_date, '1h')
        
        if df is not None and not df.empty:
            # Store in database
            success = loader.store_futures_data(symbol, '1h', df)
            
            if success:
                logger.info(f"✓ {symbol}: {len(df)} records stored")
                
                # Verify data
                verification = loader.verify_data(symbol, '1h')
                logger.info(f"  Verification: {verification}")
            else:
                logger.error(f"✗ {symbol}: Failed to store")
        else:
            logger.warning(f"✗ {symbol}: No data available")

if __name__ == "__main__":
    load_test_data()