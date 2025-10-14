"""
Futures Data Loader - One-time data retrieval and persistence
Fetches futures market data from free sources and stores in SQLite database
Includes FRED and EIA data for fundamental analysis
"""

import yfinance as yf
import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import sys
import os
import requests

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database_manager import DatabaseManager

# Try to import FRED API (optional)
try:
    from fredapi import Fred
    FRED_AVAILABLE = True
except ImportError:
    FRED_AVAILABLE = False
    logging.warning("fredapi not installed. Install with: pip install fredapi")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FuturesDataLoader:
    """
    Loads futures market data from free sources and persists to SQLite
    Based on CURRENT_HFT_FUTURES_TRADING_STRATEGIES.md recommendations
    """
    
    # Futures symbols mapping (Yahoo Finance format)
    FUTURES_SYMBOLS = {
        # Tier 1: High Liquidity Futures (Best for HFT)
        'ES': {'yahoo': 'ES=F', 'name': 'E-mini S&P 500', 'category': 'indices', 'tier': 1},
        'NQ': {'yahoo': 'NQ=F', 'name': 'E-mini NASDAQ', 'category': 'indices', 'tier': 1},
        'CL': {'yahoo': 'CL=F', 'name': 'Crude Oil', 'category': 'energy', 'tier': 1},
        'GC': {'yahoo': 'GC=F', 'name': 'Gold', 'category': 'metals', 'tier': 1},
        
        # Tier 2: Medium Liquidity Futures
        'NG': {'yahoo': 'NG=F', 'name': 'Natural Gas', 'category': 'energy', 'tier': 2},
        'SI': {'yahoo': 'SI=F', 'name': 'Silver', 'category': 'metals', 'tier': 2},
        'HG': {'yahoo': 'HG=F', 'name': 'Copper', 'category': 'metals', 'tier': 2},
        'ZN': {'yahoo': 'ZN=F', 'name': '10-Year T-Note', 'category': 'financial', 'tier': 2},
        
        # Tier 3: Specialized Futures
        'ZC': {'yahoo': 'ZC=F', 'name': 'Corn', 'category': 'agriculture', 'tier': 3},
        'ZS': {'yahoo': 'ZS=F', 'name': 'Soybeans', 'category': 'agriculture', 'tier': 3},
        'ZW': {'yahoo': 'ZW=F', 'name': 'Wheat', 'category': 'agriculture', 'tier': 3},
        'YM': {'yahoo': 'YM=F', 'name': 'E-mini Dow', 'category': 'indices', 'tier': 1},
        'RB': {'yahoo': 'RB=F', 'name': 'RBOB Gasoline', 'category': 'energy', 'tier': 2},
        'HO': {'yahoo': 'HO=F', 'name': 'Heating Oil', 'category': 'energy', 'tier': 2},
    }
    
    def __init__(self, db_path: str = "trading_bot.db", fred_api_key: str = None,
                 eia_api_key: str = None, usda_api_key: str = None):
        """
        Initialize futures data loader
        
        Args:
            db_path: Path to SQLite database
            fred_api_key: FRED API key (from config/config.yaml)
            eia_api_key: EIA API key (from config/config.yaml)
            usda_api_key: USDA API key (from config/config.yaml)
        """
        self.db_manager = DatabaseManager(db_path)
        self.logger = logging.getLogger(__name__)
        
        # Initialize FRED API if available
        self.fred = None
        if FRED_AVAILABLE and fred_api_key:
            try:
                self.fred = Fred(api_key=fred_api_key)
                self.logger.info("FRED API initialized successfully")
            except Exception as e:
                self.logger.warning(f"Could not initialize FRED API: {e}")
        
        # Store EIA API key
        self.eia_api_key = eia_api_key
        if eia_api_key:
            self.logger.info("EIA API key configured")
        
        # Store USDA API key
        self.usda_api_key = usda_api_key
        if usda_api_key:
            self.logger.info("USDA API key configured")
        
    def fetch_futures_data(self, symbol: str, start_date: str, end_date: str, 
                          interval: str = '1h') -> Optional[pd.DataFrame]:
        """
        Fetch futures data from Yahoo Finance
        
        Args:
            symbol: Futures symbol (e.g., 'ES', 'CL', 'GC')
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date in 'YYYY-MM-DD' format
            interval: Data interval ('1m', '5m', '15m', '1h', '1d')
            
        Returns:
            DataFrame with OHLCV data or None if failed
        """
        try:
            if symbol not in self.FUTURES_SYMBOLS:
                self.logger.error(f"Unknown futures symbol: {symbol}")
                return None
            
            yahoo_symbol = self.FUTURES_SYMBOLS[symbol]['yahoo']
            name = self.FUTURES_SYMBOLS[symbol]['name']
            
            self.logger.info(f"Fetching {name} ({yahoo_symbol}) data from {start_date} to {end_date}")
            
            # Download data from Yahoo Finance
            ticker = yf.Ticker(yahoo_symbol)
            df = ticker.history(start=start_date, end=end_date, interval=interval)
            
            if df.empty:
                self.logger.warning(f"No data retrieved for {symbol}")
                return None
            
            # Standardize column names
            df.columns = df.columns.str.lower()
            
            # Ensure required columns exist
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            if not all(col in df.columns for col in required_cols):
                self.logger.error(f"Missing required columns for {symbol}")
                return None
            
            # Keep only required columns
            df = df[required_cols]
            
            # Remove any NaN values
            df = df.dropna()
            
            self.logger.info(f"Successfully fetched {len(df)} records for {symbol}")
            return df
            
        except Exception as e:
            self.logger.error(f"Error fetching data for {symbol}: {e}")
            return None
    
    def fetch_fred_data(self, symbol: str) -> Optional[Dict]:
        """
        Fetch fundamental data from FRED API
        
        Args:
            symbol: Futures symbol
            
        Returns:
            Dictionary with FRED data series
        """
        if not self.fred:
            return None
        
        try:
            # Map symbols to FRED series
            fred_series_map = {
                'CL': {
                    'crude_oil_price': 'DCOILWTICO',  # WTI Crude Oil Price
                    'crude_inventory': 'WCRSTUS1',     # Crude Oil Stocks
                },
                'NG': {
                    'natural_gas_price': 'DHHNGSP',    # Natural Gas Price
                },
                'GC': {
                    'gold_price': 'GOLDAMGBD228NLBM',  # Gold Price
                    'real_interest_rate': 'REAINTRATREARAT10Y',  # Real Interest Rate
                    'dollar_index': 'DTWEXBGS',        # Dollar Index
                },
                'SI': {
                    'silver_price': 'SLVPRUSD',        # Silver Price
                },
                'HG': {
                    'copper_price': 'PCOPPUSDM',       # Copper Price
                },
                'ES': {
                    'vix': 'VIXCLS',                   # VIX Volatility Index
                    'sp500': 'SP500',                  # S&P 500 Index
                },
                'ZN': {
                    'treasury_10y': 'DGS10',           # 10-Year Treasury Rate
                    'fed_funds': 'DFF',                # Fed Funds Rate
                }
            }
            
            series_ids = fred_series_map.get(symbol, {})
            if not series_ids:
                return None
            
            fred_data = {}
            for series_name, series_id in series_ids.items():
                try:
                    data = self.fred.get_series(series_id, limit=365)  # Last year
                    fred_data[series_name] = data
                    self.logger.info(f"Fetched FRED data: {series_name} ({len(data)} points)")
                except Exception as e:
                    self.logger.warning(f"Could not fetch FRED series {series_id}: {e}")
            
            return fred_data if fred_data else None
            
        except Exception as e:
            self.logger.error(f"Error fetching FRED data for {symbol}: {e}")
            return None
    
    def fetch_eia_data(self, symbol: str) -> Optional[Dict]:
        """
        Fetch energy data from EIA API
        
        Args:
            symbol: Futures symbol (energy commodities only)
            
        Returns:
            Dictionary with EIA data
        """
        if not self.eia_api_key:
            return None
        
        # Only for energy commodities
        if symbol not in ['CL', 'NG', 'RB', 'HO']:
            return None
        
        try:
            eia_data = {}
            
            if symbol == 'CL':
                # Crude oil inventory
                url = "https://api.eia.gov/v2/petroleum/stoc/wstk/data/"
                params = {
                    'api_key': self.eia_api_key,
                    'frequency': 'weekly',
                    'data[0]': 'value',
                    'facets[product][]': 'WCRSTUS1',
                    'sort[0][column]': 'period',
                    'sort[0][direction]': 'desc',
                    'length': 52
                }
                
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    eia_data['crude_inventory'] = data
                    self.logger.info(f"Fetched EIA crude inventory data")
            
            elif symbol == 'NG':
                # Natural gas storage
                url = "https://api.eia.gov/v2/natural-gas/stor/wkly/data/"
                params = {
                    'api_key': self.eia_api_key,
                    'frequency': 'weekly',
                    'data[0]': 'value',
                    'sort[0][column]': 'period',
                    'sort[0][direction]': 'desc',
                    'length': 52
                }
                
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    eia_data['gas_storage'] = data
                    self.logger.info(f"Fetched EIA natural gas storage data")
            
            return eia_data if eia_data else None
            
        except Exception as e:
            self.logger.error(f"Error fetching EIA data for {symbol}: {e}")
            return None
    
    def fetch_usda_data(self, symbol: str) -> Optional[Dict]:
        """
        Fetch agricultural data from USDA NASS API
        
        Args:
            symbol: Futures symbol (agriculture commodities only)
            
        Returns:
            Dictionary with USDA data
        """
        if not self.usda_api_key:
            return None
        
        # Only for agricultural commodities
        if symbol not in ['ZC', 'ZS', 'ZW']:
            return None
        
        try:
            usda_data = {}
            
            # Map symbols to commodity names
            commodity_map = {
                'ZC': 'CORN',
                'ZS': 'SOYBEANS',
                'ZW': 'WHEAT'
            }
            
            commodity = commodity_map.get(symbol)
            if not commodity:
                return None
            
            # Fetch production data
            url = "https://quickstats.nass.usda.gov/api/api_GET/"
            params = {
                'key': self.usda_api_key,
                'commodity_desc': commodity,
                'statisticcat_desc': 'PRODUCTION',
                'format': 'JSON',
                'year__GE': '2023'  # Last 2 years
            }
            
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                if 'data' in data:
                    usda_data['production'] = data['data']
                    self.logger.info(f"Fetched USDA production data for {commodity}")
            
            # Fetch planted acres
            params['statisticcat_desc'] = 'AREA PLANTED'
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                if 'data' in data:
                    usda_data['planted_acres'] = data['data']
                    self.logger.info(f"Fetched USDA planted acres for {commodity}")
            
            # Fetch yield data
            params['statisticcat_desc'] = 'YIELD'
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                if 'data' in data:
                    usda_data['yield'] = data['data']
                    self.logger.info(f"Fetched USDA yield data for {commodity}")
            
            return usda_data if usda_data else None
            
        except Exception as e:
            self.logger.error(f"Error fetching USDA data for {symbol}: {e}")
            return None
    
    def store_futures_data(self, symbol: str, timeframe: str, data: pd.DataFrame) -> bool:
        """
        Store futures data in SQLite database
        
        Args:
            symbol: Futures symbol
            timeframe: Timeframe (e.g., '1h', '1d')
            data: DataFrame with OHLCV data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"Storing {len(data)} records for {symbol} {timeframe}")
            self.db_manager.store_market_data(symbol, timeframe, data)
            self.logger.info(f"Successfully stored data for {symbol} {timeframe}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error storing data for {symbol}: {e}")
            return False
    
    def load_all_futures_data(self, start_date: str = None, end_date: str = None,
                             intervals: List[str] = None, tier_filter: int = None,
                             include_fundamentals: bool = True) -> Dict[str, int]:
        """
        Load data for all futures symbols including fundamentals
        
        Args:
            start_date: Start date (default: 1 year ago)
            end_date: End date (default: today)
            intervals: List of intervals to fetch (default: ['1h', '1d'])
            tier_filter: Only load symbols from specific tier (1, 2, or 3)
            include_fundamentals: Whether to fetch FRED/EIA fundamental data
            
        Returns:
            Dictionary with symbol: records_count
        """
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        if intervals is None:
            intervals = ['1h', '1d']
        
        results = {}
        
        # Filter symbols by tier if specified
        symbols_to_load = {
            k: v for k, v in self.FUTURES_SYMBOLS.items()
            if tier_filter is None or v['tier'] == tier_filter
        }
        
        self.logger.info(f"Loading data for {len(symbols_to_load)} futures symbols")
        self.logger.info(f"Date range: {start_date} to {end_date}")
        self.logger.info(f"Intervals: {intervals}")
        
        for symbol, info in symbols_to_load.items():
            self.logger.info(f"\n{'='*60}")
            self.logger.info(f"Processing {symbol} - {info['name']} (Tier {info['tier']})")
            self.logger.info(f"{'='*60}")
            
            for interval in intervals:
                # Fetch price data
                df = self.fetch_futures_data(symbol, start_date, end_date, interval)
                
                if df is not None and not df.empty:
                    # Store in database
                    success = self.store_futures_data(symbol, interval, df)
                    
                    if success:
                        key = f"{symbol}_{interval}"
                        results[key] = len(df)
                        self.logger.info(f"✓ {symbol} {interval}: {len(df)} records stored")
                    else:
                        self.logger.error(f"✗ {symbol} {interval}: Failed to store")
                else:
                    self.logger.warning(f"✗ {symbol} {interval}: No data available")
            
            # Fetch fundamental data if enabled
            if include_fundamentals:
                self.logger.info(f"\nFetching fundamental data for {symbol}...")
                
                # Fetch FRED data
                fred_data = self.fetch_fred_data(symbol)
                if fred_data:
                    self.logger.info(f"✓ FRED data: {len(fred_data)} series fetched")
                    # Store as metadata (could be stored in separate table if needed)
                    results[f"{symbol}_FRED"] = len(fred_data)
                
                # Fetch EIA data (for energy commodities)
                eia_data = self.fetch_eia_data(symbol)
                if eia_data:
                    self.logger.info(f"✓ EIA data: {len(eia_data)} series fetched")
                    results[f"{symbol}_EIA"] = len(eia_data)
                else:
                    self.logger.debug(f"  No EIA data available for {symbol}")
                
                # Fetch USDA data (for agricultural commodities)
                usda_data = self.fetch_usda_data(symbol)
                if usda_data:
                    self.logger.info(f"✓ USDA data: {len(usda_data)} series fetched")
                    results[f"{symbol}_USDA"] = len(usda_data)
                else:
                    self.logger.debug(f"  No USDA data available for {symbol}")
        
        return results
    
    def verify_data(self, symbol: str, timeframe: str) -> Dict:
        """
        Verify stored data for a symbol
        
        Args:
            symbol: Futures symbol
            timeframe: Timeframe
            
        Returns:
            Dictionary with verification results
        """
        try:
            df = self.db_manager.get_market_data(
                symbol, timeframe, 
                start_time=None, end_time=None, 
                limit=10000
            )
            
            if df.empty:
                return {
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'status': 'NO_DATA',
                    'records': 0
                }
            
            return {
                'symbol': symbol,
                'timeframe': timeframe,
                'status': 'OK',
                'records': len(df),
                'date_range': f"{df.index.min()} to {df.index.max()}",
                'columns': list(df.columns)
            }
            
        except Exception as e:
            return {
                'symbol': symbol,
                'timeframe': timeframe,
                'status': 'ERROR',
                'error': str(e)
            }
    
    def generate_report(self, results: Dict[str, int]) -> str:
        """Generate summary report of data loading"""
        report = [
            "\n" + "="*80,
            "FUTURES DATA LOADING REPORT",
            "="*80,
            f"Total symbols processed: {len(set(k.split('_')[0] for k in results.keys()))}",
            f"Total datasets: {len(results)}",
            f"Total records: {sum(results.values())}",
            "\nDetails by symbol:",
            "-"*80
        ]
        
        # Group by symbol
        by_symbol = {}
        for key, count in results.items():
            symbol, interval = key.rsplit('_', 1)
            if symbol not in by_symbol:
                by_symbol[symbol] = {}
            by_symbol[symbol][interval] = count
        
        for symbol in sorted(by_symbol.keys()):
            info = self.FUTURES_SYMBOLS.get(symbol, {})
            name = info.get('name', symbol)
            tier = info.get('tier', '?')
            
            report.append(f"\n{symbol} - {name} (Tier {tier}):")
            for interval, count in sorted(by_symbol[symbol].items()):
                report.append(f"  {interval}: {count:,} records")
        
        report.append("\n" + "="*80)
        return "\n".join(report)


def main():
    """Main execution function"""
    logger.info("Starting Futures Data Loader")
    logger.info("="*80)
    
    # Initialize loader
    loader = FuturesDataLoader()
    
    # Load data for all tiers
    # Tier 1: High liquidity (recommended for HFT)
    logger.info("\n### LOADING TIER 1 FUTURES (HIGH LIQUIDITY) ###")
    results_tier1 = loader.load_all_futures_data(
        start_date='2024-01-01',
        end_date=datetime.now().strftime('%Y-%m-%d'),
        intervals=['1h', '1d'],
        tier_filter=1
    )
    
    # Tier 2: Medium liquidity
    logger.info("\n### LOADING TIER 2 FUTURES (MEDIUM LIQUIDITY) ###")
    results_tier2 = loader.load_all_futures_data(
        start_date='2024-01-01',
        end_date=datetime.now().strftime('%Y-%m-%d'),
        intervals=['1h', '1d'],
        tier_filter=2
    )
    
    # Tier 3: Specialized
    logger.info("\n### LOADING TIER 3 FUTURES (SPECIALIZED) ###")
    results_tier3 = loader.load_all_futures_data(
        start_date='2024-01-01',
        end_date=datetime.now().strftime('%Y-%m-%d'),
        intervals=['1d'],  # Only daily for tier 3
        tier_filter=3
    )
    
    # Combine results
    all_results = {**results_tier1, **results_tier2, **results_tier3}
    
    # Generate and print report
    report = loader.generate_report(all_results)
    logger.info(report)
    
    # Verify a few samples
    logger.info("\n### VERIFICATION SAMPLES ###")
    samples = [('ES', '1h'), ('CL', '1h'), ('GC', '1d')]
    for symbol, timeframe in samples:
        verification = loader.verify_data(symbol, timeframe)
        logger.info(f"\n{symbol} {timeframe}:")
        for key, value in verification.items():
            logger.info(f"  {key}: {value}")
    
    logger.info("\n" + "="*80)
    logger.info("Futures Data Loading Complete!")
    logger.info("="*80)


if __name__ == "__main__":
    main()