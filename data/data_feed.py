"""
Data Feed Module for Trading Bot

This module handles data retrieval for forex, crypto, and futures markets
from various sources including OANDA, CCXT, and Interactive Brokers.
"""

import pandas as pd
import ccxt
import oandapyV20
import oandapyV20.endpoints.instruments as instruments
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
import logging
from datetime import datetime, timedelta
import yaml
import os
import pytz # Import pytz


class DataFeed:
    """Base class for data feed functionality"""
    
    def __init__(self, config: dict):
        """
        Initialize data feed with configuration
        
        Args:
            config (dict): Configuration dictionary
        """
        self.config = config
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing DataFeed")
    
    def get_forex_data(self, symbol, timeframe, start_date, end_date):
        """
        Retrieve forex data from OANDA
        
        Args:
            symbol (str): Currency pair (e.g., 'EUR_USD')
            timeframe (str): Timeframe (e.g., 'M1', 'M5', 'H1')
            start_date (str): Start date in 'YYYY-MM-DD' format
            end_date (str): End date in 'YYYY-MM-DD' format
            
        Returns:
            pd.DataFrame: Historical price data
        """
        raise NotImplementedError("Subclasses must implement get_forex_data")
    
    def get_crypto_data(self, symbol, timeframe, start_date, end_date):
        """
        Retrieve crypto data from CCXT
        
        Args:
            symbol (str): Trading pair (e.g., 'BTC/USDT')
            timeframe (str): Timeframe (e.g., '1m', '5m', '1h')
            start_date (str): Start date in 'YYYY-MM-DD' format
            end_date (str): End date in 'YYYY-MM-DD' format
            
        Returns:
            pd.DataFrame: Historical price data
        """
        raise NotImplementedError("Subclasses must implement get_crypto_data")
    
    def get_futures_data(self, symbol, timeframe, start_date, end_date):
        """
        Retrieve futures data from Interactive Brokers
        
        Args:
            symbol (str): Futures contract (e.g., 'ESZ23')
            timeframe (str): Timeframe (e.g., '1 min', '5 mins', '1 hour')
            start_date (str): Start date in 'YYYY-MM-DD' format
            end_date (str): End date in 'YYYY-MM-DD' format
            
        Returns:
            pd.DataFrame: Historical price data
        """
        raise NotImplementedError("Subclasses must implement get_futures_data")


class OANDADataFeed(DataFeed):
    """OANDA data feed implementation"""
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.account_id = self.config['oanda']['account_id']
        self.access_token = self.config['oanda']['access_token']
        self.practice = self.config['oanda']['practice']
        
        # Initialize OANDA client
        self.client = oandapyV20.API(
            access_token=self.access_token,
            environment='practice' if self.practice else 'live'
        )
        
        self.logger.info("OANDADataFeed initialized")
    
    def get_forex_data(self, symbol, timeframe, start_date, end_date):
        """
        Retrieve forex data from OANDA
        
        Args:
            symbol (str): Currency pair (e.g., 'EUR_USD')
            timeframe (str): Timeframe (e.g., 'M1', 'M5', 'H1')
            start_date (str): Start date in 'YYYY-MM-DD' format
            end_date (str): End date in 'YYYY-MM-DD' format
            
        Returns:
            pd.DataFrame: Historical price data
        """
        try:
            # Map user-friendly timeframes to OANDA granularity
            timeframe_mapping = {
                "1s": "S5", # Smallest OANDA granularity is 5 seconds
                "5s": "S5",
                "10s": "S10",
                "15s": "S15",
                "30s": "S30",
                "1m": "M1",
                "2m": "M2",
                "3m": "M3",
                "5m": "M5",
                "10m": "M10",
                "15m": "M15",
                "30m": "M30",
                "1h": "H1",
                "2h": "H2",
                "3h": "H3",
                "4h": "H4",
                "6h": "H6",
                "8h": "H8",
                "12h": "H12",
                "1d": "D",
                "1w": "W",
                "1M": "M",
                "h1": "H1", # Add explicit mapping for "H1" if it comes from config
                "h2": "H2",
                "h3": "H3",
                "h4": "H4",
                "h6": "H6",
                "h8": "H8",
                "h12": "H12",
                "d": "D",
                "w": "W",
                "m": "M"
            }
            
            oanda_timeframe = timeframe_mapping.get(timeframe.lower())
            if not oanda_timeframe:
                raise ValueError(f"Unsupported timeframe for OANDA: {timeframe}")
            
            # Convert start_date and end_date to timezone-aware UTC datetime objects
            # OANDA API expects ISO 8601 format with 'Z' for UTC
            start_dt = datetime.strptime(start_date, '%Y-%m-%d').replace(tzinfo=pytz.UTC)
            end_dt = datetime.strptime(end_date, '%Y-%m-%d').replace(tzinfo=pytz.UTC)
            
            # Limit date range to avoid API restrictions (max 1 year for practice accounts)
            max_days = 365
            if (end_dt - start_dt).days > max_days:
                self.logger.warning(f"Date range too large ({(end_dt - start_dt).days} days), limiting to {max_days} days")
                start_dt = end_dt - timedelta(days=max_days)
            
            # Ensure we don't request future data
            now = datetime.now(pytz.UTC)
            if end_dt > now:
                end_dt = now
                self.logger.info(f"Adjusted end date to current time: {end_dt}")
            
            self.logger.info(f"Requesting OANDA data for {symbol} from {start_dt} to {end_dt} (practice account)")
            
            all_candles = []
            current_from_dt = start_dt
            
            # OANDA's max candles per request when using 'from' and 'to' is 5000.
            # We will fetch in chunks of 5000 candles.
            max_candles_per_request = 5000
            
            # Determine the interval in seconds for the given timeframe
            if oanda_timeframe.startswith('S'):
                interval_seconds = int(oanda_timeframe[1:])
            elif oanda_timeframe.startswith('M'):
                interval_seconds = int(oanda_timeframe[1:]) * 60
            elif oanda_timeframe.startswith('H'):
                interval_seconds = int(oanda_timeframe[1:]) * 3600
            elif oanda_timeframe == 'D':
                interval_seconds = 24 * 3600
            elif oanda_timeframe == 'W':
                interval_seconds = 7 * 24 * 3600
            elif oanda_timeframe == 'M':
                interval_seconds = 30 * 24 * 3600 # Approximate for month
            else:
                raise ValueError(f"Cannot determine interval for timeframe: {oanda_timeframe}")
 
            while current_from_dt < end_dt:
                # Calculate 'to' date for the current chunk
                # Request up to max_candles_per_request candles from current_from_dt
                chunk_to_dt = current_from_dt + timedelta(seconds=max_candles_per_request * interval_seconds)
                
                # Ensure we don't go past the overall end_dt
                if chunk_to_dt > end_dt:
                    chunk_to_dt = end_dt
 
                params = {
                    "from": current_from_dt.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                    "to": chunk_to_dt.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                    "granularity": oanda_timeframe,
                    "price": "MBA"
                }
                
                request = instruments.InstrumentsCandles(
                    instrument=symbol,
                    params=params
                )
                
                try:
                    response = self.client.request(request)
                    candles = response.get('candles', [])
                    
                    if not candles:
                        self.logger.info(f"No more candles for {symbol} from {current_from_dt} to {chunk_to_dt}. Total collected: {len(all_candles)}")
                        break # No more data in this range, stop fetching
                    
                    self.logger.info(f"Retrieved {len(candles)} candles for {symbol} from {current_from_dt} to {chunk_to_dt}. Total collected so far: {len(all_candles) + len(candles)}")
                    all_candles.extend(candles)
                    
                    # Set next current_from_dt to the timestamp of the last candle + 1 interval
                    last_candle_time = pd.to_datetime(candles[-1]['time'], utc=True)
                    current_from_dt = last_candle_time + timedelta(seconds=interval_seconds)
                    
                    # If the last candle's time is already past or at the overall end_dt, break
                    if last_candle_time >= end_dt:
                        self.logger.info(f"Reached or passed end_dt ({end_dt}). Stopping data retrieval.")
                        break
 
                except Exception as e:
                    self.logger.error(f"Error retrieving OANDA data for {symbol} from {current_from_dt} to {chunk_to_dt}: {str(e)}")
                    break # Break on error to prevent infinite loops


            data = []
            for candle in all_candles:
                if candle['complete']:
                    # Ensure timestamp is timezone-aware UTC
                    timestamp = pd.to_datetime(candle['time'], utc=True)
                    data.append({
                        'timestamp': timestamp,
                        'open': float(candle['mid']['o']),
                        'high': float(candle['mid']['h']),
                        'low': float(candle['mid']['l']),
                        'close': float(candle['mid']['c']),
                        'volume': float(candle['volume'])
                    })
            
            df = pd.DataFrame(data)
            if not df.empty:
                df.set_index('timestamp', inplace=True)
                # Remove duplicate timestamps that might occur at chunk boundaries
                df = df.loc[~df.index.duplicated(keep='first')]
                self.logger.info(f"Retrieved {len(df)} candles for {symbol}")
            else:
                self.logger.warning(f"No data retrieved for {symbol} in the specified range.")
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error retrieving OANDA data for {symbol}: {str(e)}")
            raise


class CCXTDataFeed(DataFeed):
    """CCXT data feed implementation"""
    
    def __init__(self, config: dict):
        super().__init__(config)
        
        # Initialize CCXT exchanges
        self.exchanges = {}
        
        # Get CCXT config with safe defaults for backtesting
        ccxt_config = self.config.get('ccxt', {})
        api_key = ccxt_config.get('api_key', '')
        secret = ccxt_config.get('secret', '')
        password = ccxt_config.get('password', '')
        
        # For backtesting, we can use exchanges without credentials for public data
        try:
            # Add common exchanges
            self.exchanges['binance'] = ccxt.binance({
                'apiKey': api_key if api_key else '',
                'secret': secret if secret else '',
                'password': password if password else '',
                'enableRateLimit': True,
                'sandbox': False,
            })
            self.logger.info("Binance exchange initialized for CCXT data feed")
        except Exception as e:
            self.logger.warning(f"Failed to initialize Binance exchange: {e}")
        
        # Add Kraken exchange for crypto data (krakenx)
        try:
            self.exchanges['kraken'] = ccxt.kraken({
                'apiKey': api_key if api_key else '',
                'secret': secret if secret else '',
                'password': password if password else '',
                'enableRateLimit': True,
                'sandbox': False,  # Kraken doesn't have sandbox, use live API for public data
            })
            self.logger.info("Kraken exchange initialized for CCXT data feed")
        except Exception as e:
            self.logger.warning(f"Failed to initialize Kraken exchange: {e}")
        
        # If no exchanges were initialized successfully, log warning but don't fail
        if not self.exchanges:
            self.logger.warning("No CCXT exchanges initialized successfully. Historical data fetching may fail.")
        
        self.logger.info("CCXTDataFeed initialized")
    
    def get_crypto_data(self, symbol, timeframe, start_date, end_date):
        """
        Retrieve crypto data from CCXT
        
        Args:
            symbol (str): Trading pair (e.g., 'BTC/USDT')
            timeframe (str): Timeframe (e.g., '1m', '5m', '1h')
            start_date (str): Start date in 'YYYY-MM-DD' format
            end_date (str): End date in 'YYYY-MM-DD' format
            
        Returns:
            pd.DataFrame: Historical price data
        """
        try:
            exchange_name = 'kraken' # Use Kraken for crypto data (krakenx)
            exchange = self.exchanges.get(exchange_name)
            
            if not exchange:
                raise ValueError(f"Exchange {exchange_name} not supported or configured.")
            
            # Convert dates to milliseconds timestamp
            since = exchange.parse8601(start_date + 'T00:00:00Z')
            until = exchange.parse8601(end_date + 'T23:59:59Z')
            
            all_ohlcv = []
            while since < until:
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since)
                if not ohlcv:
                    break
                all_ohlcv.extend(ohlcv)
                since = ohlcv[-1][0] + exchange.parse_timeframe(timeframe)
            
            df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            self.logger.info(f"Retrieved {len(df)} candles for {symbol} from {exchange_name}")
            return df
            
        except Exception as e:
            self.logger.error(f"Error retrieving CCXT data for {symbol}: {str(e)}")
            raise


class IBKRDataFeed(DataFeed, EWrapper):
    """Interactive Brokers data feed implementation"""

    def __init__(self, config: dict):
        super().__init__(config)
        EWrapper.__init__(self)

        self.host = self.config['ibkr']['host']
        self.port = self.config['ibkr']['port']
        self.client_id = self.config['ibkr']['client_id']

        self.client = EClient(self)
        self.data = {} # To store historical data
        self.req_id_counter = 0

        # Initialize database manager for caching
        from database.database_manager import DatabaseManager
        self.db_manager = DatabaseManager()

        self.logger.info("IBKRDataFeed initialized")
    
    def connect(self):
        """Connect to IBKR TWS/Gateway"""
        try:
            self.client.connect(self.host, self.port, self.client_id)
            self.logger.info(f"Connected to IBKR at {self.host}:{self.port}")
            # Start the socket in a different thread
            import threading
            thread = threading.Thread(target=self.client.run)
            thread.start()
            setattr(self.client, "thread", thread)
        except Exception as e:
            self.logger.error(f"Error connecting to IBKR: {str(e)}")
            raise
    
    def disconnect(self):
        """Disconnect from IBKR TWS/Gateway"""
        self.client.disconnect()
        self.logger.info("Disconnected from IBKR")
    
    def historicalData(self, reqId, bar):
        """Callback for historical data"""
        if reqId not in self.data:
            self.data[reqId] = []
        self.data[reqId].append({
            'timestamp': datetime.strptime(bar.date, '%Y%m%d %H:%M:%S'),
            'open': bar.open,
            'high': bar.high,
            'low': bar.low,
            'close': bar.close,
            'volume': bar.volume
        })
    
    def historicalDataEnd(self, reqId, start, end):
        """Callback for historical data end"""
        self.logger.info(f"Historical data request {reqId} finished. From {start} to {end}")
        # Signal that data retrieval is complete for this request
        self.data[reqId + '_complete'] = True
    
    def get_futures_data(self, symbol, timeframe, start_date, end_date):
        """
        Retrieve futures data from Interactive Brokers

        Args:
            symbol (str): Futures contract (e.g., 'ESZ23', 'NGZ4')
            timeframe (str): Timeframe (e.g., '1 min', '5 mins', '1 hour')
            start_date (str): Start date in 'YYYY-MM-DD' format
            end_date (str): End date in 'YYYY-MM-DD' format

        Returns:
            pd.DataFrame: Historical price data
        """
        try:
            # Validate symbol format
            if len(symbol) < 3:
                raise ValueError(f"Invalid futures symbol format: {symbol}. Use format like 'NGZ4' (Natural Gas Dec 2024)")

            # Parse symbol: last 2 chars should be month code + year
            month_year = symbol[-2:]
            if not (month_year[0].isalpha() and month_year[1].isdigit()):
                raise ValueError(f"Invalid futures symbol format: {symbol}. Last 2 chars should be month code + year (e.g., 'Z4' for Dec 2024)")

            self.connect()

            contract = Contract()
            contract.symbol = symbol[:-2] # e.g., NG from NGZ4
            contract.secType = "FUT"
            contract.exchange = "GLOBEX" # Natural Gas trades on GLOBEX
            contract.currency = "USD"
            contract.lastTradeDateOrContractMonth = "20" + symbol[-2:] # e.g., 2024 from NGZ4
            
            # Generate unique request ID
            req_id = self.req_id_counter
            self.req_id_counter += 1
            self.data[req_id] = []
            self.data[req_id + '_complete'] = False
            
            # Request historical data
            self.client.reqHistoricalData(
                req_id,
                contract,
                end_date + " 23:59:59 US/Eastern", # End date and time
                "1 Y", # Duration string (e.g., "1 Y", "6 M", "1 W", "1 D")
                timeframe, # Bar size (e.g., "1 min", "5 mins", "1 hour", "1 day")
                "TRADES", # What to show (TRADES, MIDPOINT, BID, ASK, BID_ASK)
                0, # RTH (regular trading hours)
                1, # Format date
                False, # Keep up to date
                []
            )
            
            # Wait for data to be received
            import time
            while not self.data.get(req_id + '_complete', False):
                time.sleep(0.1)
            
            df = pd.DataFrame(self.data[req_id])
            df.set_index('timestamp', inplace=True)

            # Save to database for future use
            if not df.empty:
                try:
                    self.db_manager.store_market_data(symbol, timeframe, df)
                    self.logger.info(f"Saved {len(df)} candles for {symbol} to database")
                except Exception as e:
                    self.logger.warning(f"Failed to save data to database: {e}")

            self.disconnect()

            self.logger.info(f"Retrieved {len(df)} candles for {symbol} from IBKR")
            return df
            
        except Exception as e:
            self.logger.error(f"Error retrieving IBKR data for {symbol}: {str(e)}")
            raise


class DBDataFeed(DataFeed):
    """Database-backed data feed that uses IBKR as fallback for futures"""

    def __init__(self, config: dict):
        super().__init__(config)

        # Initialize database manager
        from database.database_manager import DatabaseManager
        self.db_manager = DatabaseManager()

        # Initialize IBKR feed as fallback
        self.ibkr_feed = IBKRDataFeed(config)

        self.logger.info("DBDataFeed initialized")

    def get_futures_data(self, symbol, timeframe, start_date, end_date):
        """
        Retrieve futures data from IBKR (bypassing cache for testing)

        Args:
            symbol (str): Futures contract (e.g., 'ESZ23', 'NGZ4')
            timeframe (str): Timeframe (e.g., '1 min', '5 mins', '1 hour')
            start_date (str): Start date in 'YYYY-MM-DD' format
            end_date (str): End date in 'YYYY-MM-DD' format

        Returns:
            pd.DataFrame: Historical price data
        """
        try:
            self.logger.info(f"Fetching fresh data for {symbol} from IBKR (cache bypassed)")
            self.logger.info(f"IBKR config: host={self.ibkr_feed.host}, port={self.ibkr_feed.port}, client_id={self.ibkr_feed.client_id}")

            # Always fetch from IBKR (bypassing database cache)
            df = self.ibkr_feed.get_futures_data(symbol, timeframe, start_date, end_date)

            # Still save to database for future use
            if not df.empty:
                try:
                    self.db_manager.store_market_data(symbol, timeframe, df)
                    self.logger.info(f"Saved {len(df)} candles for {symbol} to database")
                except Exception as e:
                    self.logger.warning(f"Failed to save data to database: {e}")

            return df

        except Exception as e:
            self.logger.error(f"Error retrieving futures data for {symbol}: {str(e)}")
            self.logger.error(f"Make sure IBKR TWS/Gateway is running and API is enabled")
            self.logger.error(f"For futures, use specific contract symbols like 'NGZ4' (Dec 2024 Natural Gas)")
            raise


if __name__ == "__main__":
    # Example Usage (for testing purposes)
    logging.basicConfig(level=logging.INFO)
    
    # To run this example, you would need a dummy config dictionary
    # or load it from a file as main.py does.
    dummy_config = {
        'oanda': {
            'account_id': 'YOUR_OANDA_ACCOUNT_ID',
            'access_token': 'YOUR_OANDA_ACCESS_TOKEN',
            'practice': True
        },
        'ccxt': {
            'api_key': 'YOUR_CCXT_API_KEY',
            'secret': 'YOUR_CCXT_SECRET',
            'password': 'YOUR_CCXT_PASSWORD'
        },
        'ibkr': {
            'host': '127.0.0.1',
            'port': 7497,
            'client_id': 1
        }
    }

    # OANDA Example
    try:
        oanda_feed = OANDADataFeed(config=dummy_config)
        # Note: This will likely fail without real OANDA credentials and a running TWS/Gateway
        # forex_data = oanda_feed.get_forex_data(
        #     symbol="EUR_USD",
        #     timeframe="H1",
        #     start_date="2023-01-01",
        #     end_date="2023-01-02"
        # )
        # print("\nOANDA EUR_USD H1 Data:")
        # print(forex_data.head())
    except Exception as e:
        print(f"OANDA Example Error: {e}")

    # CCXT Example
    try:
        ccxt_feed = CCXTDataFeed(config=dummy_config)
        # crypto_data = ccxt_feed.get_crypto_data(
        #     symbol="BTC/USDT",
        #     timeframe="1h",
        #     start_date="2023-01-01",
        #     end_date="2023-01-02"
        # )
        # print("\nCCXT BTC/USDT 1h Data:")
        # print(crypto_data.head())
    except Exception as e:
        print(f"CCXT Example Error: {e}")

    # IBKR Example (Requires TWS/Gateway running and connected)
    try:
        ibkr_feed = IBKRDataFeed(config=dummy_config)
        # futures_data = ibkr_feed.get_futures_data(
        #     symbol="ESZ23",
        #     timeframe="1 hour",
        #     start_date="2023-01-01",
        #     end_date="2023-01-02"
        # )
        # print("\nIBKR ESZ23 1 hour Data:")
        # print(futures_data.head())
    except Exception as e:
        print(f"IBKR Example Error: {e}")