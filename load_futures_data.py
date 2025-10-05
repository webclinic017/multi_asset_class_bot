#!/usr/bin/env python3
"""
Load Real Futures Data to SQLite Database
Downloads real historical futures data from yfinance and stores it in SQLite
Includes major futures contracts: Oil, Gold, Gas, and other commodities
"""

import yfinance as yf
import pandas as pd
import os
import sys
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.database_manager import DatabaseManager

def download_and_store_futures_data():
    """Download real futures data and store in database"""
    print("Downloading real futures data and storing in SQLite database...")

    db = DatabaseManager()

    # Major futures contracts (yfinance format)
    futures_contracts = [
        # Energy
        ('CL=F', 'WTI_CRUDE_OIL', 'Crude Oil (WTI)'),
        ('BZ=F', 'BRENT_CRUDE_OIL', 'Brent Crude Oil'),
        ('NG=F', 'NATURAL_GAS', 'Natural Gas'),

        # Metals
        ('GC=F', 'GOLD', 'Gold'),
        ('SI=F', 'SILVER', 'Silver'),
        ('HG=F', 'COPPER', 'Copper'),
        ('PL=F', 'PLATINUM', 'Platinum'),
        ('PA=F', 'PALLADIUM', 'Palladium'),

        # Agriculture
        ('ZC=F', 'CORN', 'Corn'),
        ('ZW=F', 'WHEAT', 'Wheat'),
        ('ZS=F', 'SOYBEANS', 'Soybeans'),
        ('KC=F', 'COFFEE', 'Coffee'),
        ('CT=F', 'COTTON', 'Cotton'),
        ('SB=F', 'SUGAR', 'Sugar'),

        # Livestock
        ('LE=F', 'LIVE_CATTLE', 'Live Cattle'),
        ('GF=F', 'FEEDER_CATTLE', 'Feeder Cattle'),
        ('HE=F', 'LEAN_HOGS', 'Lean Hogs'),

        # Financial
        ('ES=F', 'E_MINI_S&P', 'E-mini S&P 500'),
        ('NQ=F', 'E_MINI_NASDAQ', 'E-mini Nasdaq-100'),
        ('RTY=F', 'E_MINI_RUSSELL', 'E-mini Russell 2000'),
        ('YM=F', 'E_MINI_DOW', 'E-mini Dow Jones'),
        ('ZB=F', 'T_BOND', '30-Year T-Bond'),
        ('ZN=F', 'T_NOTE', '10-Year T-Note'),
        ('ZF=F', 'FIVE_YEAR', '5-Year T-Note'),
        ('ZT=F', 'TWO_YEAR', '2-Year T-Note'),

        # Currencies (already have forex, but adding some futures)
        ('6E=F', 'EURO_FX', 'Euro FX'),
        ('6B=F', 'BRITISH_POUND', 'British Pound'),
        ('6J=F', 'JAPANESE_YEN', 'Japanese Yen'),
        ('6A=F', 'AUSTRALIAN_DOLLAR', 'Australian Dollar'),
        ('6C=F', 'CANADIAN_DOLLAR', 'Canadian Dollar'),
        ('6N=F', 'NEW_ZEALAND_DOLLAR', 'New Zealand Dollar'),
        ('6S=F', 'SWISS_FRANC', 'Swiss Franc'),
    ]

    # Timeframes with yfinance limitations
    timeframes = [
        ('1d', '2020-01-01'),  # Daily data from 2020
        ('1h', (datetime.now() - timedelta(days=700)).strftime('%Y-%m-%d'))  # Hourly last 700 days
    ]

    total_contracts = len(futures_contracts)
    total_timeframes = len(timeframes)
    current_count = 0

    for yf_symbol, db_symbol, description in futures_contracts:
        for timeframe, start_date in timeframes:
            current_count += 1

            print(f"Progress: {current_count}/{total_contracts * total_timeframes} - {description} ({db_symbol}) {timeframe}")

            try:
                # Download real data from yfinance
                ticker = yf.Ticker(yf_symbol)
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
                    db.store_market_data(db_symbol, timeframe, df_clean)

                    print(f"[OK] Stored {len(df_clean)} real {timeframe} candles for {description} ({db_symbol})")

                    # Save to CSV for backup
                    os.makedirs('futures_hist_csv', exist_ok=True)
                    csv_path = f'futures_hist_csv/{db_symbol}_{timeframe}_real.csv'
                    df.to_csv(csv_path)
                    print(f"   Saved backup CSV: {csv_path}")

                else:
                    print(f"[WARNING] No data downloaded for {description} ({db_symbol}) {timeframe}")

            except Exception as e:
                print(f"[ERROR] Failed {description} ({db_symbol}) {timeframe}: {e}")

    # Show final database summary
    print("\n" + "="*80)
    print("REAL FUTURES DATA LOADED TO DATABASE")
    print("="*80)

    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT symbol, timeframe, COUNT(*) as candle_count,
                       MIN(timestamp) as earliest_date,
                       MAX(timestamp) as latest_date
                FROM market_data
                WHERE symbol IN ('WTI_CRUDE_OIL', 'GOLD', 'NATURAL_GAS', 'BRENT_CRUDE_OIL', 'SILVER', 'COPPER',
                               'E_MINI_S&P', 'E_MINI_NASDAQ', 'T_BOND', 'T_NOTE', 'EURO_FX', 'BRITISH_POUND')
                GROUP BY symbol, timeframe
                ORDER BY symbol, timeframe
            """)

            results = cursor.fetchall()

            print(f"{'Symbol':<20} {'Timeframe':<10} {'Candles':<10} {'From':<12} {'To':<12}")
            print("-"*80)

            total_candles = 0
            for row in results:
                symbol, timeframe, count, earliest, latest = row
                earliest_date = earliest[:10] if earliest else 'N/A'
                latest_date = latest[:10] if latest else 'N/A'
                print(f"{symbol:<20} {timeframe:<10} {count:<10} {earliest_date:<12} {latest_date:<12}")
                total_candles += count

            print("-"*80)
            print(f"Total real futures candles in database: {total_candles:,}")
            print("="*80)

    except Exception as e:
        print(f"Error showing summary: {e}")

    print("\n[OK] Real futures data loaded to SQLite database!")
    print("[INFO] HFT strategies can now backtest against real futures data")
    print("[RESTART] Restart the server for backtests to use this futures data")

if __name__ == "__main__":
    download_and_store_futures_data()