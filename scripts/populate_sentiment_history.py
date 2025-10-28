"""
Populate Historical Sentiment Data
Stores current sentiment snapshots for future backtesting
Run this script daily to build historical sentiment database
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from datetime import datetime
from sentiment.futures_sentiment_analyzer import FuturesSentimentAnalyzer
from database.database_manager import DatabaseManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def populate_sentiment_for_symbol(symbol: str, analyzer: FuturesSentimentAnalyzer, db: DatabaseManager):
    """Populate sentiment data for a single symbol"""
    try:
        logger.info(f"Fetching sentiment for {symbol}...")
        
        # Get current sentiment
        sentiment_result = analyzer.get_commodity_sentiment(symbol, hours_back=24)
        
        # Store in database
        db.store_sentiment_data(
            symbol=symbol,
            timestamp=datetime.now(),
            sentiment_score=sentiment_result['sentiment_score'],
            news_count=sentiment_result['news_count'],
            confidence=sentiment_result['confidence'],
            signal=sentiment_result['signal'],
            category=sentiment_result['category']
        )
        
        logger.info(f"  ✓ Stored sentiment for {symbol}:")
        logger.info(f"    Score: {sentiment_result['sentiment_score']:.3f}")
        logger.info(f"    Signal: {sentiment_result['signal']}")
        logger.info(f"    News Count: {sentiment_result['news_count']}")
        logger.info(f"    Confidence: {sentiment_result['confidence']:.3f}")
        
        return True
        
    except Exception as e:
        logger.error(f"  ✗ Failed to populate sentiment for {symbol}: {e}")
        return False

def populate_all_symbols():
    """Populate sentiment data for all tracked symbols"""
    logger.info("=" * 80)
    logger.info("POPULATING HISTORICAL SENTIMENT DATA")
    logger.info("=" * 80)
    
    # Initialize analyzer and database
    try:
        analyzer = FuturesSentimentAnalyzer()
        db = DatabaseManager()
        logger.info("✓ Sentiment analyzer and database initialized")
    except Exception as e:
        logger.error(f"✗ Failed to initialize: {e}")
        return
    
    # Symbols to track
    symbols = {
        'Equity Indices': ['ES', 'NQ', 'YM', 'RTY'],
        'Energy': ['CL', 'NG', 'RB', 'HO'],
        'Metals': ['GC', 'SI', 'HG'],
        'Agriculture': ['ZC', 'ZS', 'ZW']
    }
    
    total_success = 0
    total_failed = 0
    
    for category, symbol_list in symbols.items():
        logger.info(f"\n{category}:")
        
        for symbol in symbol_list:
            if populate_sentiment_for_symbol(symbol, analyzer, db):
                total_success += 1
            else:
                total_failed += 1
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Total symbols processed: {total_success + total_failed}")
    logger.info(f"  ✓ Successful: {total_success}")
    logger.info(f"  ✗ Failed: {total_failed}")
    
    if total_success > 0:
        logger.info("\n✓ Sentiment history populated successfully!")
        logger.info("\nTo build historical database:")
        logger.info("1. Run this script daily (e.g., via cron job)")
        logger.info("2. After 30+ days, you'll have historical sentiment for backtesting")
        logger.info("3. Strategy will automatically use historical data in backtest mode")
    
    # Show current database stats
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sentiment_history")
        total_rows = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT symbol, COUNT(*) as count, MIN(timestamp), MAX(timestamp)
            FROM sentiment_history
            GROUP BY symbol
            ORDER BY count DESC
        """)
        
        symbol_stats = cursor.fetchall()
        
        logger.info(f"\nCurrent sentiment_history database:")
        logger.info(f"  Total records: {total_rows}")
        logger.info(f"  Symbols tracked: {len(symbol_stats)}")
        
        if symbol_stats:
            logger.info(f"\n  Top symbols:")
            for symbol, count, min_date, max_date in symbol_stats[:10]:
                logger.info(f"    {symbol}: {count} records ({min_date} to {max_date})")

if __name__ == "__main__":
    populate_all_symbols()