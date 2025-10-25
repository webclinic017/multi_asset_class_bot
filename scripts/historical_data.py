"""
Historical Data Collection Script
Collects forex and crypto data using yfinance and saves to database
Supports 1M, 5M, 1H timeframes for all major pairs from 2018
"""

import yfinance as yf
import pandas as pd
import numpy as np
import os
import logging
import zipfile
from datetime import datetime, timedelta
from typing import List, Dict
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.database_manager import DatabaseManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/historical_data.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class HistoricalDataCollector:
    """Collects and manages historical market data"""
    
    def __init__(self):
        """Initialize the historical data collector"""
        self.db_manager = DatabaseManager()
        
        # Create data directory (use forex_hist_csv as requested)
        self.data_dir = 'forex_hist_csv'
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs('logs', exist_ok=True)
        
        # Major forex pairs (yfinance format)
        self.forex_pairs = [
            'EURUSD=X', 'GBPUSD=X', 'USDJPY=X', 'AUDUSD=X', 
            'USDCAD=X', 'USDCHF=X', 'NZDUSD=X', 'EURGBP=X',
            'EURJPY=X', 'GBPJPY=X', 'AUDJPY=X', 'CHFJPY=X'
        ]
        
        # Major crypto pairs
        self.crypto_pairs = [
            'BTC-USD', 'ETH-USD', 'SOL-USD', 'ADA-USD',
            'DOT-USD', 'AVAX-USD', 'MATIC-USD', 'LINK-USD'
        ]
        
        # Timeframes to collect (adjusted for yfinance limitations)
        self.timeframes = ['1d']  # Daily data can go back to 2018
        self.hourly_timeframes = ['1h']  # Hourly data limited to 730 days (2 years)
        self.minute_timeframes = ['1m', '5m']  # Minute data limited to 8 days
        
        # Start dates for different timeframes based on yfinance limitations
        self.daily_start_date = '2018-01-01'  # Daily data from 2018
        self.hourly_start_date = (datetime.now() - timedelta(days=720)).strftime('%Y-%m-%d')  # Last 2 years for hourly
        self.minute_start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')  # Last 7 days for minute

        # Set default start date for general use
        self.start_date = self.daily_start_date

        logger.info("Historical Data Collector initialized")
    
    def download_forex_data(self, symbol: str, timeframe: str, start_date: str, end_date: str = None) -> pd.DataFrame:
        """
        Download forex data using yfinance
        
        Args:
            symbol: Forex pair symbol (e.g., 'EURUSD=X')
            timeframe: Timeframe ('1m', '5m', '1h', '1d')
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD), defaults to today
            
        Returns:
            DataFrame with OHLCV data
        """
        try:
            if end_date is None:
                end_date = datetime.now().strftime('%Y-%m-%d')
            
            logger.info(f"Downloading {symbol} {timeframe} data from {start_date} to {end_date}")
            
            # Create yfinance ticker
            ticker = yf.Ticker(symbol)
            
            # Download data with specified interval
            interval_map = {
                '1m': '1m',
                '5m': '5m', 
                '15m': '15m',
                '30m': '30m',
                '1h': '1h',
                '1d': '1d'
            }
            
            interval = interval_map.get(timeframe, '1h')
            
            # For minute data, yfinance only allows 8 days maximum
            if interval in ['1m', '5m']:
                # Limit to last 7 days for minute data
                end_dt = pd.to_datetime(end_date)
                start_dt = max(pd.to_datetime(start_date), end_dt - timedelta(days=7))
                
                logger.info(f"Minute data limited to last 7 days: {start_dt.date()} to {end_dt.date()}")
                
                all_data = []
                current_date = start_dt
                
                while current_date < end_dt:
                    chunk_end = min(current_date + timedelta(days=1), end_dt)  # Daily chunks for minute data
                    
                    try:
                        chunk_data = ticker.history(
                            start=current_date.strftime('%Y-%m-%d'),
                            end=chunk_end.strftime('%Y-%m-%d'),
                            interval=interval,
                            auto_adjust=True,
                            prepost=False
                        )
                        
                        if not chunk_data.empty:
                            all_data.append(chunk_data)
                            logger.info(f"Downloaded {len(chunk_data)} {timeframe} candles for {symbol} from {current_date.date()} to {chunk_end.date()}")
                        
                    except Exception as e:
                        logger.warning(f"Failed to download chunk for {symbol} from {current_date.date()}: {e}")
                    
                    current_date = chunk_end
                
                if all_data:
                    df = pd.concat(all_data)
                    df = df.drop_duplicates()
                    df = df.sort_index()
                else:
                    df = pd.DataFrame()
            else:
                # Download all at once for hourly and daily data
                df = ticker.history(
                    start=start_date,
                    end=end_date,
                    interval=interval,
                    auto_adjust=True,
                    prepost=False
                )
            
            if not df.empty:
                # Handle different column structures from yfinance
                try:
                    # yfinance typically returns: Open, High, Low, Close, Volume, Dividends, Stock Splits
                    # We only need OHLCV
                    if len(df.columns) >= 5:
                        # Keep only first 5 columns (OHLCV)
                        df = df.iloc[:, :5]
                        df.columns = ['open', 'high', 'low', 'close', 'volume']
                    else:
                        # If less than 5 columns, add missing volume column
                        df.columns = ['open', 'high', 'low', 'close']
                        df['volume'] = 0  # Add zero volume if missing
                        df = df[['open', 'high', 'low', 'close', 'volume']]
                    
                    logger.info(f"Successfully downloaded {len(df)} {timeframe} candles for {symbol}")
                except Exception as col_error:
                    logger.error(f"Error standardizing columns for {symbol}: {col_error}")
                    return pd.DataFrame()
            else:
                logger.warning(f"No data downloaded for {symbol} {timeframe}")
            
            return df
            
        except Exception as e:
            logger.error(f"Error downloading {symbol} {timeframe} data: {e}")
            return pd.DataFrame()
    
    def download_crypto_data(self, symbol: str, timeframe: str, start_date: str, end_date: str = None) -> pd.DataFrame:
        """
        Download crypto data using yfinance
        
        Args:
            symbol: Crypto pair symbol (e.g., 'BTC-USD')
            timeframe: Timeframe ('1m', '5m', '1h', '1d')
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD), defaults to today
            
        Returns:
            DataFrame with OHLCV data
        """
        try:
            if end_date is None:
                end_date = datetime.now().strftime('%Y-%m-%d')
            
            logger.info(f"Downloading {symbol} {timeframe} data from {start_date} to {end_date}")
            
            # Create yfinance ticker
            ticker = yf.Ticker(symbol)
            
            # Download data
            interval_map = {
                '1m': '1m',
                '5m': '5m',
                '15m': '15m',
                '30m': '30m',
                '1h': '1h',
                '1d': '1d'
            }
            
            interval = interval_map.get(timeframe, '1h')
            
            # For minute data, download in smaller chunks
            if interval in ['1m', '5m']:
                all_data = []
                current_date = pd.to_datetime(start_date)
                end_dt = pd.to_datetime(end_date)
                
                while current_date < end_dt:
                    chunk_end = min(current_date + timedelta(days=7), end_dt)  # Weekly chunks for crypto
                    
                    try:
                        chunk_data = ticker.history(
                            start=current_date.strftime('%Y-%m-%d'),
                            end=chunk_end.strftime('%Y-%m-%d'),
                            interval=interval,
                            auto_adjust=True,
                            prepost=False
                        )
                        
                        if not chunk_data.empty:
                            all_data.append(chunk_data)
                            logger.info(f"Downloaded {len(chunk_data)} {timeframe} candles for {symbol} from {current_date.date()} to {chunk_end.date()}")
                        
                    except Exception as e:
                        logger.warning(f"Failed to download chunk for {symbol} from {current_date.date()}: {e}")
                    
                    current_date = chunk_end
                
                if all_data:
                    df = pd.concat(all_data)
                    df = df.drop_duplicates()
                    df = df.sort_index()
                else:
                    df = pd.DataFrame()
            else:
                # Download all at once for hourly and daily data
                df = ticker.history(
                    start=start_date,
                    end=end_date,
                    interval=interval,
                    auto_adjust=True,
                    prepost=False
                )
            
            if not df.empty:
                # Standardize column names
                df.columns = ['open', 'high', 'low', 'close', 'volume']
                logger.info(f"Successfully downloaded {len(df)} {timeframe} candles for {symbol}")
            else:
                logger.warning(f"No data downloaded for {symbol} {timeframe}")
            
            return df
            
        except Exception as e:
            logger.error(f"Error downloading {symbol} {timeframe} data: {e}")
            return pd.DataFrame()
    
    def save_to_csv_zip(self, df: pd.DataFrame, symbol: str, timeframe: str) -> str:
        """
        Save DataFrame to CSV and ZIP file
        
        Args:
            df: DataFrame with market data
            symbol: Symbol name
            timeframe: Timeframe
            
        Returns:
            Path to saved ZIP file
        """
        try:
            # Clean symbol name for filename
            clean_symbol = symbol.replace('=X', '').replace('-', '_')
            
            # Create filename
            csv_filename = f"{clean_symbol}_{timeframe}_{self.start_date}_to_{datetime.now().strftime('%Y-%m-%d')}.csv"
            zip_filename = f"{clean_symbol}_{timeframe}.zip"
            
            csv_path = os.path.join(self.data_dir, csv_filename)
            zip_path = os.path.join(self.data_dir, zip_filename)
            
            # Save to CSV
            df.to_csv(csv_path)
            logger.info(f"Saved {len(df)} rows to {csv_path}")
            
            # Create ZIP file
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(csv_path, csv_filename)
            
            # Remove CSV file (keep only ZIP)
            os.remove(csv_path)
            
            logger.info(f"Created ZIP file: {zip_path}")
            return zip_path
            
        except Exception as e:
            logger.error(f"Error saving data to ZIP: {e}")
            return None
    
    def load_to_database(self, df: pd.DataFrame, symbol: str, timeframe: str):
        """
        Load DataFrame data into SQLite database
        
        Args:
            df: DataFrame with market data
            symbol: Symbol name
            timeframe: Timeframe
        """
        try:
            if df.empty:
                logger.warning(f"No data to load for {symbol} {timeframe}")
                return
            
            # Clean symbol name for database
            clean_symbol = symbol.replace('=X', '').replace('-', '_')
            
            # Store in database
            self.db_manager.store_market_data(clean_symbol, timeframe, df)
            logger.info(f"Loaded {len(df)} {timeframe} candles for {clean_symbol} into database")
            
        except Exception as e:
            logger.error(f"Error loading {symbol} {timeframe} data to database: {e}")
    
    def collect_all_data(self):
        """Collect all historical data for forex and crypto pairs"""
        logger.info("Starting historical data collection...")
        
        total_pairs = len(self.forex_pairs) + len(self.crypto_pairs)
        total_combinations = total_pairs * len(self.timeframes)
        current_count = 0
        
        # Collect forex data
        logger.info("Collecting forex data...")
        for symbol in self.forex_pairs:
            for timeframe in self.timeframes:
                current_count += 1
                logger.info(f"Progress: {current_count}/{total_combinations} - {symbol} {timeframe}")
                
                try:
                    # Download data
                    df = self.download_forex_data(symbol, timeframe, self.start_date)
                    
                    if not df.empty:
                        # Save to ZIP file
                        zip_path = self.save_to_csv_zip(df, symbol, timeframe)
                        
                        # Load to database
                        self.load_to_database(df, symbol, timeframe)
                        
                        logger.info(f"[OK] Completed {symbol} {timeframe}: {len(df)} candles")
                    else:
                        logger.warning(f"[ERROR] No data for {symbol} {timeframe}")
                        
                except Exception as e:
                    logger.error(f"[ERROR] Failed {symbol} {timeframe}: {e}")
        
        # Collect crypto data
        logger.info("Collecting crypto data...")
        for symbol in self.crypto_pairs:
            for timeframe in self.timeframes:
                current_count += 1
                logger.info(f"Progress: {current_count}/{total_combinations} - {symbol} {timeframe}")
                
                try:
                    # Download data
                    df = self.download_crypto_data(symbol, timeframe, self.start_date)
                    
                    if not df.empty:
                        # Save to ZIP file
                        zip_path = self.save_to_csv_zip(df, symbol, timeframe)
                        
                        # Load to database
                        self.load_to_database(df, symbol, timeframe)
                        
                        logger.info(f"[OK] Completed {symbol} {timeframe}: {len(df)} candles")
                    else:
                        logger.warning(f"[ERROR] No data for {symbol} {timeframe}")
                        
                except Exception as e:
                    logger.error(f"[ERROR] Failed {symbol} {timeframe}: {e}")
        
        logger.info("Historical data collection completed!")
    
    def update_recent_data(self, days_back: int = 7):
        """Update database with recent data for all pairs"""
        logger.info(f"Updating recent data (last {days_back} days)...")
        
        start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        
        all_symbols = self.forex_pairs + self.crypto_pairs
        
        for symbol in all_symbols:
            for timeframe in self.timeframes:
                try:
                    if symbol in self.forex_pairs:
                        df = self.download_forex_data(symbol, timeframe, start_date)
                    else:
                        df = self.download_crypto_data(symbol, timeframe, start_date)
                    
                    if not df.empty:
                        self.load_to_database(df, symbol, timeframe)
                        logger.info(f"Updated {symbol} {timeframe}: {len(df)} recent candles")
                    
                except Exception as e:
                    logger.error(f"Failed to update {symbol} {timeframe}: {e}")
        
        logger.info("Recent data update completed!")
    
    def get_data_summary(self):
        """Get summary of data in database"""
        logger.info("Generating data summary...")
        
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get data summary
                cursor.execute("""
                    SELECT symbol, timeframe, COUNT(*) as candle_count,
                           MIN(timestamp) as earliest_date,
                           MAX(timestamp) as latest_date
                    FROM market_data
                    GROUP BY symbol, timeframe
                    ORDER BY symbol, timeframe
                """)
                
                results = cursor.fetchall()
                
                print("\n" + "="*80)
                print("HISTORICAL DATA SUMMARY")
                print("="*80)
                print(f"{'Symbol':<12} {'Timeframe':<10} {'Candles':<10} {'From':<12} {'To':<12}")
                print("-"*80)
                
                total_candles = 0
                for row in results:
                    symbol, timeframe, count, earliest, latest = row
                    earliest_date = earliest[:10] if earliest else 'N/A'
                    latest_date = latest[:10] if latest else 'N/A'
                    print(f"{symbol:<12} {timeframe:<10} {count:<10} {earliest_date:<12} {latest_date:<12}")
                    total_candles += count
                
                print("-"*80)
                print(f"Total candles in database: {total_candles:,}")
                print("="*80)
                
        except Exception as e:
            logger.error(f"Error generating data summary: {e}")

def main():
    """Main function to run historical data collection"""
    print("Historical Data Collection Script")
    print("=" * 50)
    
    collector = HistoricalDataCollector()
    
    try:
        # Ask user what to do
        print("\nOptions:")
        print("1. Collect all historical data (2018 to present)")
        print("2. Update recent data (last 7 days)")
        print("3. Show data summary")
        print("4. Collect specific symbol and timeframe")
        
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == '1':
            print("\n[PROGRESS] Starting full historical data collection...")
            print("This may take a while. Please be patient.")
            collector.collect_all_data()
            
        elif choice == '2':
            print("\n[PROGRESS] Updating recent data...")
            collector.update_recent_data()
            
        elif choice == '3':
            print("\n[SUMMARY] Data Summary:")
            collector.get_data_summary()
            
        elif choice == '4':
            print("\nAvailable symbols:")
            print("Forex:", ', '.join([s.replace('=X', '') for s in collector.forex_pairs]))
            print("Crypto:", ', '.join([s.replace('-USD', '') for s in collector.crypto_pairs]))
            
            symbol = input("Enter symbol (e.g., EURUSD, BTC): ").strip().upper()
            timeframe = input("Enter timeframe (1m, 5m, 1h): ").strip().lower()
            
            # Convert to yfinance format
            if symbol in [s.replace('=X', '') for s in collector.forex_pairs]:
                yf_symbol = f"{symbol}=X"
                df = collector.download_forex_data(yf_symbol, timeframe, collector.start_date)
            elif symbol in [s.replace('-USD', '') for s in collector.crypto_pairs]:
                yf_symbol = f"{symbol}-USD"
                df = collector.download_crypto_data(yf_symbol, timeframe, collector.start_date)
            else:
                print(f"Unknown symbol: {symbol}")
                return
            
            if not df.empty:
                collector.save_to_csv_zip(df, yf_symbol, timeframe)
                collector.load_to_database(df, yf_symbol, timeframe)
                print(f"[OK] Collected {len(df)} candles for {symbol} {timeframe}")
            else:
                print(f"[ERROR] No data collected for {symbol} {timeframe}")
        
        else:
            print("Invalid choice. Exiting.")
            return
        
        # Show final summary
        print("\n[SUMMARY] Final Data Summary:")
        collector.get_data_summary()
        
        print("\n[OK] Historical data collection completed!")
        print("[INFO] Data is now available in the database for backtesting.")
        
    except KeyboardInterrupt:
        print("\n[WARN] Collection interrupted by user")
    except Exception as e:
        logger.error(f"Error in main: {e}")
        print(f"[ERROR] Error: {e}")

if __name__ == "__main__":
    main()