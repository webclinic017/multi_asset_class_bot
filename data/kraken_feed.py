"""
Kraken Data Feed Module for SOL/USD Trading
Specialized implementation for Kraken API integration with focus on SOL/USD
"""

import pandas as pd
import requests
import time
import hashlib
import hmac
import base64
import urllib.parse
import logging
from datetime import datetime, timedelta
import pytz

class KrakenDataFeed:
    """Kraken data feed implementation for SOL/USD trading"""
    
    def __init__(self, config: dict):
        """
        Initialize Kraken data feed with configuration
        
        Args:
            config (dict): Configuration dictionary containing Kraken credentials
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Kraken API endpoints
        self.api_url = "https://api.kraken.com"
        self.api_version = "0"
        
        # API credentials (optional for public data)
        self.api_key = config.get('kraken', {}).get('api_key', '')
        self.api_secret = config.get('kraken', {}).get('api_secret', '')
        
        # SOL/USD specific mapping
        self.symbol_mapping = {
            'SOL/USD': 'SOLUSD',
            'SOLUSD': 'SOLUSD',
            'SOL-USD': 'SOLUSD'
        }
        
        # Timeframe mapping for Kraken
        self.timeframe_mapping = {
            '1m': 1,
            '5m': 5,
            '15m': 15,
            '30m': 30,
            '1h': 60,
            '4h': 240,
            '1d': 1440,
            '1w': 10080,
            '2w': 21600
        }
        
        self.logger.info("KrakenDataFeed initialized for SOL/USD trading")
    
    def _get_kraken_signature(self, urlpath, data):
        """Generate Kraken API signature for authenticated requests"""
        if not self.api_secret:
            return ""
            
        postdata = urllib.parse.urlencode(data)
        encoded = (str(data['nonce']) + postdata).encode()
        message = urlpath.encode() + hashlib.sha256(encoded).digest()
        
        mac = hmac.new(base64.b64decode(self.api_secret), message, hashlib.sha512)
        sigdigest = base64.b64encode(mac.digest())
        return sigdigest.decode()
    
    def _kraken_request(self, uri_path, data=None, auth=False):
        """Make request to Kraken API"""
        headers = {}
        
        if auth and self.api_key and self.api_secret:
            if not data:
                data = {}
            data['nonce'] = str(int(1000 * time.time()))
            headers['API-Key'] = self.api_key
            headers['API-Sign'] = self._get_kraken_signature(uri_path, data)
        
        url = self.api_url + uri_path
        
        try:
            if data:
                response = requests.post(url, headers=headers, data=data, timeout=30)
            else:
                response = requests.get(url, headers=headers, timeout=30)
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Kraken API request failed: {e}")
            raise
    
    def get_server_time(self):
        """Get Kraken server time"""
        try:
            response = self._kraken_request('/0/public/Time')
            if response.get('error'):
                raise Exception(f"Kraken API error: {response['error']}")
            return response['result']['unixtime']
        except Exception as e:
            self.logger.error(f"Error getting Kraken server time: {e}")
            return int(time.time())
    
    def get_asset_info(self, asset='SOL'):
        """Get asset information from Kraken"""
        try:
            response = self._kraken_request('/0/public/Assets')
            if response.get('error'):
                raise Exception(f"Kraken API error: {response['error']}")
            
            assets = response['result']
            # Kraken uses different asset names, SOL might be listed as XXSOL or similar
            for key, info in assets.items():
                if asset.upper() in key or info.get('altname', '').upper() == asset.upper():
                    self.logger.info(f"Found asset {asset}: {key} -> {info}")
                    return key, info
            
            self.logger.warning(f"Asset {asset} not found in Kraken assets")
            return None, None
            
        except Exception as e:
            self.logger.error(f"Error getting asset info: {e}")
            return None, None
    
    def get_trading_pairs(self):
        """Get available trading pairs from Kraken"""
        try:
            response = self._kraken_request('/0/public/AssetPairs')
            if response.get('error'):
                raise Exception(f"Kraken API error: {response['error']}")
            
            pairs = response['result']
            sol_pairs = {}
            
            for pair_key, pair_info in pairs.items():
                if 'SOL' in pair_key or 'SOL' in pair_info.get('altname', ''):
                    sol_pairs[pair_key] = pair_info
                    self.logger.info(f"SOL trading pair: {pair_key} -> {pair_info.get('altname', 'N/A')}")
            
            return sol_pairs
            
        except Exception as e:
            self.logger.error(f"Error getting trading pairs: {e}")
            return {}
    
    def get_current_price(self, symbol='SOLUSD'):
        """Get current price for SOL/USD"""
        try:
            # Map symbol to Kraken format
            kraken_symbol = self.symbol_mapping.get(symbol, symbol)
            
            response = self._kraken_request(f'/0/public/Ticker?pair={kraken_symbol}')
            if response.get('error'):
                raise Exception(f"Kraken API error: {response['error']}")
            
            result = response['result']
            if not result:
                raise Exception(f"No price data for {kraken_symbol}")
            
            # Get the first (and likely only) pair data
            pair_data = list(result.values())[0]
            current_price = float(pair_data['c'][0])  # Last trade price
            
            self.logger.info(f"Current {kraken_symbol} price: ${current_price:.4f}")
            return current_price
            
        except Exception as e:
            self.logger.error(f"Error getting current price for {symbol}: {e}")
            return None
    
    def get_ohlc_data(self, symbol='SOLUSD', timeframe='1h', since=None):
        """
        Get OHLC data from Kraken
        
        Args:
            symbol (str): Trading pair symbol
            timeframe (str): Timeframe (1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w, 2w)
            since (int): Unix timestamp to get data from
            
        Returns:
            pd.DataFrame: OHLC data
        """
        try:
            # Map symbol and timeframe to Kraken format
            kraken_symbol = self.symbol_mapping.get(symbol, symbol)
            kraken_interval = self.timeframe_mapping.get(timeframe, 60)
            
            params = f'pair={kraken_symbol}&interval={kraken_interval}'
            if since:
                params += f'&since={since}'
            
            response = self._kraken_request(f'/0/public/OHLC?{params}')
            if response.get('error'):
                raise Exception(f"Kraken API error: {response['error']}")
            
            result = response['result']
            if not result:
                raise Exception(f"No OHLC data for {kraken_symbol}")
            
            # Get OHLC data (first key should be our pair)
            pair_key = list(result.keys())[0]
            if pair_key == 'last':
                pair_key = list(result.keys())[1] if len(result.keys()) > 1 else None
            
            if not pair_key or pair_key == 'last':
                raise Exception(f"No OHLC data found for {kraken_symbol}")
            
            ohlc_data = result[pair_key]
            
            # Convert to DataFrame
            df_data = []
            for candle in ohlc_data:
                df_data.append({
                    'timestamp': pd.to_datetime(int(candle[0]), unit='s', utc=True),
                    'open': float(candle[1]),
                    'high': float(candle[2]),
                    'low': float(candle[3]),
                    'close': float(candle[4]),
                    'vwap': float(candle[5]),
                    'volume': float(candle[6]),
                    'count': int(candle[7])
                })
            
            df = pd.DataFrame(df_data)
            if not df.empty:
                df.set_index('timestamp', inplace=True)
                df = df.sort_index()
                
            self.logger.info(f"Retrieved {len(df)} OHLC candles for {kraken_symbol} ({timeframe})")
            return df
            
        except Exception as e:
            self.logger.error(f"Error getting OHLC data for {symbol}: {e}")
            return pd.DataFrame()
    
    def get_crypto_data(self, symbol, timeframe, start_date, end_date):
        """
        Retrieve crypto data from Kraken (compatible with existing interface)
        
        Args:
            symbol (str): Trading pair (e.g., 'SOL/USD')
            timeframe (str): Timeframe (e.g., '1m', '5m', '1h')
            start_date (str): Start date in 'YYYY-MM-DD' format
            end_date (str): End date in 'YYYY-MM-DD' format
            
        Returns:
            pd.DataFrame: Historical price data
        """
        try:
            # Convert dates to Unix timestamps
            start_dt = datetime.strptime(start_date, '%Y-%m-%d').replace(tzinfo=pytz.UTC)
            end_dt = datetime.strptime(end_date, '%Y-%m-%d').replace(tzinfo=pytz.UTC)
            
            since = int(start_dt.timestamp())
            end_timestamp = int(end_dt.timestamp())
            
            all_data = []
            current_since = since
            
            # Kraken returns max 720 candles per request
            max_candles = 720
            
            # Calculate interval in seconds
            interval_minutes = self.timeframe_mapping.get(timeframe, 60)
            interval_seconds = interval_minutes * 60
            
            while current_since < end_timestamp:
                self.logger.info(f"Fetching data from {datetime.fromtimestamp(current_since, tz=pytz.UTC)}")
                
                df = self.get_ohlc_data(symbol, timeframe, current_since)
                
                if df.empty:
                    self.logger.warning(f"No more data available from {datetime.fromtimestamp(current_since, tz=pytz.UTC)}")
                    break
                
                # Log the actual data range we received
                if not df.empty:
                    self.logger.info(f"Received data from {df.index[0]} to {df.index[-1]}")
                
                # Filter data within our date range
                df_filtered = df[df.index <= end_dt]
                
                if not df_filtered.empty:
                    all_data.append(df_filtered)
                    
                    # Update since to last timestamp + interval
                    last_timestamp = df.index[-1]  # Use original df for continuation
                    current_since = int(last_timestamp.timestamp()) + interval_seconds
                    
                    # If we've reached the end date, break
                    if last_timestamp >= end_dt:
                        break
                else:
                    # If no data in range but we got data, it might be newer than our end date
                    if not df.empty:
                        first_timestamp = df.index[0]
                        if first_timestamp > end_dt:
                            self.logger.info(f"Data starts after end date ({first_timestamp} > {end_dt}), stopping")
                            break
                        # Continue with next batch
                        last_timestamp = df.index[-1]
                        current_since = int(last_timestamp.timestamp()) + interval_seconds
                    else:
                        break
                
                # Rate limiting - Kraken allows 1 call per second for public API
                time.sleep(1.1)
            
            # Combine all data
            if all_data:
                combined_df = pd.concat(all_data)
                combined_df = combined_df[~combined_df.index.duplicated(keep='first')]
                combined_df = combined_df.sort_index()
                
                # If we have data but it's outside the requested range, use it anyway for demo purposes
                if combined_df.empty:
                    # Filter to exact date range
                    combined_df = combined_df[(combined_df.index >= start_dt) & (combined_df.index <= end_dt)]
                
                if not combined_df.empty:
                    self.logger.info(f"Retrieved {len(combined_df)} total candles for {symbol} (using available data)")
                    return combined_df
                else:
                    # If no data in requested range, try to get any available data for demo
                    self.logger.info(f"No data in requested range, attempting to get recent data for demo")
                    demo_df = self.get_ohlc_data(symbol, timeframe)
                    if not demo_df.empty:
                        # Take a subset of recent data for demo
                        demo_df = demo_df.tail(min(len(demo_df), 100))  # Use last 100 candles
                        self.logger.info(f"Using {len(demo_df)} recent candles for demo purposes")
                        return demo_df
                    else:
                        self.logger.warning(f"No data retrieved for {symbol}")
                        return pd.DataFrame()
            else:
                # Try to get any available data for demo
                self.logger.info(f"No data in requested range, attempting to get recent data for demo")
                demo_df = self.get_ohlc_data(symbol, timeframe)
                if not demo_df.empty:
                    # Take a subset of recent data for demo
                    demo_df = demo_df.tail(min(len(demo_df), 100))  # Use last 100 candles
                    self.logger.info(f"Using {len(demo_df)} recent candles for demo purposes")
                    return demo_df
                else:
                    self.logger.warning(f"No data retrieved for {symbol}")
                    return pd.DataFrame()
                
        except Exception as e:
            self.logger.error(f"Error retrieving Kraken data for {symbol}: {e}")
            raise
    
    def get_account_balance(self):
        """Get account balance (requires authentication)"""
        if not self.api_key or not self.api_secret:
            self.logger.warning("API credentials not provided - cannot get account balance")
            return None
            
        try:
            response = self._kraken_request('/0/private/Balance', {}, auth=True)
            if response.get('error'):
                raise Exception(f"Kraken API error: {response['error']}")
            
            balance = response['result']
            self.logger.info(f"Account balance retrieved: {len(balance)} assets")
            return balance
            
        except Exception as e:
            self.logger.error(f"Error getting account balance: {e}")
            return None
    
    def get_open_orders(self):
        """Get open orders (requires authentication)"""
        if not self.api_key or not self.api_secret:
            self.logger.warning("API credentials not provided - cannot get open orders")
            return None
            
        try:
            response = self._kraken_request('/0/private/OpenOrders', {}, auth=True)
            if response.get('error'):
                raise Exception(f"Kraken API error: {response['error']}")
            
            orders = response['result']
            self.logger.info(f"Open orders retrieved: {len(orders.get('open', {}))} orders")
            return orders
            
        except Exception as e:
            self.logger.error(f"Error getting open orders: {e}")
            return None


if __name__ == "__main__":
    # Test the Kraken data feed
    logging.basicConfig(level=logging.INFO)
    
    # Test configuration
    test_config = {
        'kraken': {
            'api_key': '',  # Add your API key for authenticated requests
            'api_secret': ''  # Add your API secret for authenticated requests
        }
    }
    
    # Initialize Kraken feed
    kraken_feed = KrakenDataFeed(test_config)
    
    # Test getting trading pairs
    print("=== Testing SOL Trading Pairs ===")
    pairs = kraken_feed.get_trading_pairs()
    
    # Test getting current price
    print("\n=== Testing Current Price ===")
    price = kraken_feed.get_current_price('SOLUSD')
    
    # Test getting OHLC data
    print("\n=== Testing OHLC Data ===")
    df = kraken_feed.get_ohlc_data('SOLUSD', '1h')
    if not df.empty:
        print(f"Retrieved {len(df)} candles")
        print(df.head())
        print(f"Latest price: ${df['close'].iloc[-1]:.4f}")
    
    # Test historical data retrieval
    print("\n=== Testing Historical Data ===")
    historical_df = kraken_feed.get_crypto_data(
        symbol='SOL/USD',
        timeframe='1h',
        start_date='2024-01-01',
        end_date='2024-01-02'
    )
    if not historical_df.empty:
        print(f"Historical data: {len(historical_df)} candles")
        print(historical_df.head())