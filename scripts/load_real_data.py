"""
Load Real yfinance Data to SQLite Database
Downloads real historical data from yfinance and persists it in SQLite
Run once, use forever for backtesting
"""

import yfinance as yf
import pandas as pd
import os
import sys
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.database_manager import DatabaseManager

def download_and_store_real_data():
    """Download real yfinance data and store in database"""
    print("Downloading real yfinance data and storing in SQLite database...")
    
    db = DatabaseManager()
    
    # Major forex pairs (yfinance format)
    forex_pairs = [
        'EURUSD=X', 'GBPUSD=X', 'USDJPY=X', 'AUDUSD=X', 
        'USDCAD=X', 'USDCHF=X', 'NZDUSD=X'
    ]
    
    # Timeframes with yfinance limitations
    timeframes = [
        ('1d', '2020-01-01'),  # Daily data from 2020
        ('1h', (datetime.now() - timedelta(days=700)).strftime('%Y-%m-%d'))  # Hourly last 700 days
    ]
    
    total_pairs = len(forex_pairs)
    total_timeframes = len(timeframes)
    current_count = 0
    
    for symbol in forex_pairs:
        for timeframe, start_date in timeframes:
            current_count += 1
            clean_symbol = symbol.replace('=X', '')  # EURUSD=X -> EURUSD
            
            print(f"Progress: {current_count}/{total_pairs * total_timeframes} - {clean_symbol} {timeframe}")
            
            try:
                # Download real data from yfinance
                ticker = yf.Ticker(symbol)
                df = ticker.history(
                    start=start_date,
                    end=datetime.now().strftime('%Y-%m-%d'),
                    interval=timeframe,
                    auto_adjust=True,
                    prepost=False
                )
                
                if not df.empty:
                    # Clean and prepare data
                    if len(df.columns) >= 5:
                        df = df.iloc[:, :5]  # Keep only OHLCV
                    
                    df.columns = ['open', 'high', 'low', 'close', 'volume']
                    
                    # Prepare for database storage
                    df_clean = df.copy()
                    df_clean.index = df_clean.index.strftime('%Y-%m-%d %H:%M:%S')
                    
                    # Ensure proper data types
                    for col in ['open', 'high', 'low', 'close', 'volume']:
                        if col in df_clean.columns:
                            df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce').astype(float)
                    
                    # Remove NaN values
                    df_clean = df_clean.dropna()
                    
                    # Store in database
                    db.store_market_data(clean_symbol, timeframe, df_clean)
                    
                    print(f"[OK] Stored {len(df_clean)} real {timeframe} candles for {clean_symbol}")
                    
                    # Save to CSV for backup
                    os.makedirs('forex_hist_csv', exist_ok=True)
                    csv_path = f'forex_hist_csv/{clean_symbol}_{timeframe}_real.csv'
                    df.to_csv(csv_path)
                    print(f"   Saved backup CSV: {csv_path}")
                    
                else:
                    print(f"[ERROR] No data downloaded for {clean_symbol} {timeframe}")
                    
            except Exception as e:
                print(f"[ERROR] Failed {clean_symbol} {timeframe}: {e}")
    
    # Show final database summary
    print("\n" + "="*60)
    print("REAL DATA LOADED TO DATABASE")
    print("="*60)
    
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT symbol, timeframe, COUNT(*) as candle_count,
                       MIN(timestamp) as earliest_date,
                       MAX(timestamp) as latest_date
                FROM market_data
                GROUP BY symbol, timeframe
                ORDER BY symbol, timeframe
            """)
            
            results = cursor.fetchall()
            
            print(f"{'Symbol':<10} {'Timeframe':<10} {'Candles':<10} {'From':<12} {'To':<12}")
            print("-"*60)
            
            total_candles = 0
            for row in results:
                symbol, timeframe, count, earliest, latest = row
                earliest_date = earliest[:10] if earliest else 'N/A'
                latest_date = latest[:10] if latest else 'N/A'
                print(f"{symbol:<10} {timeframe:<10} {count:<10} {earliest_date:<12} {latest_date:<12}")
                total_candles += count
            
            print("-"*60)
            print(f"Total real candles in database: {total_candles:,}")
            print("="*60)
            
    except Exception as e:
        print(f"Error showing summary: {e}")
    
    print("\n[OK] Real yfinance data loaded to SQLite database!")
    print("[INFO] Backtesting will now use real historical data from database")
    print("[RESTART] You can restart the server and backtests will use this data")

if __name__ == "__main__":
    download_and_store_real_data()