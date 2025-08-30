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
        self.last_request_time = 0
        self.rate_limit_seconds = 1.5  # Increased rate limit to be safer
    
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
            # Enforce rate limit
            elapsed_time = time.time() - self.last_request_time
            if elapsed_time < self.rate_limit_seconds:
                time.sleep(self.rate_limit_seconds - elapsed_time)
            
            if data:
                response = requests.post(url, headers=headers, data=data, timeout=30)
            else:
                response = requests.get(url, headers=headers, timeout=30)
            
            self.last_request_time = time.time()
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
    
    def get_trades_data(self, symbol='SOLUSD', since=None):
        """
        Get trades data from Kraken's public Trades endpoint.
        
        Args:
            symbol (str): Trading pair symbol.
            since (int): Return trade data since given timestamp (exclusive).
            
        Returns:
            pd.DataFrame: Trades data.
        """
        try:
            kraken_symbol = self.symbol_mapping.get(symbol, symbol)
            
            params = f'pair={kraken_symbol}'
            if since:
                params += f'&since={since}'

            response = self._kraken_request(f'/0/public/Trades?{params}')
            if response.get('error'):
                raise Exception(f"Kraken API error: {response['error']}")

            result = response['result']
            if not result:
                raise Exception(f"No trades data for {kraken_symbol}")

            pair_key = list(result.keys())[0]
            if pair_key == 'last':
                return pd.DataFrame(), None

            trades_data = result[pair_key]
            last_id = result['last']

            df_data = []
            for trade in trades_data:
                df_data.append({
                    'timestamp': pd.to_datetime(float(trade[2]), unit='s', utc=True),
                    'price': float(trade[0]),
                    'volume': float(trade[1]),
                    'side': trade[3],
                    'order_type': trade[4],
                    'misc': trade[5]
                })

            df = pd.DataFrame(df_data)
            if not df.empty:
                df.set_index('timestamp', inplace=True)
                df = df.sort_index()

            self.logger.info(f"Retrieved {len(df)} trades for {kraken_symbol}")
            return df, last_id

        except Exception as e:
            self.logger.error(f"Error getting trades data for {symbol}: {e}")
            return pd.DataFrame(), None

    def get_all_trades(self, symbol, start_date):
        """
        Get all historical trade data from a specific start date using pagination.
        """
        all_trades = []
        last_id = None
        
        start_dt = datetime.strptime(start_date, '%Y-%m-%d').replace(tzinfo=pytz.UTC)
        # Convert start_date to nanoseconds for the 'since' parameter
        since_nano = int(start_dt.timestamp() * 1e9)

        while True:
            # The 'since' parameter in the Trades endpoint is a nanosecond timestamp.
            df, last_id = self.get_trades_data(symbol, since=since_nano)
            if df.empty or last_id is None:
                break

            all_trades.append(df)
            since_nano = last_id # Update for the next iteration
            
            # Respect rate limits
            # Rate limiting is now handled in _kraken_request

        if not all_trades:
            return pd.DataFrame()

        combined_df = pd.concat(all_trades)
        combined_df = combined_df[~combined_df.index.duplicated(keep='first')]

        # Final filter to remove any trades before the start date
        combined_df = combined_df[combined_df.index >= start_dt]
        return combined_df.sort_index()
    
    def get_ohlc_from_trades(self, trades_df, timeframe):
        """
        Convert trade data to OHLC format.
        """
        if trades_df.empty:
            return pd.DataFrame()

        resample_period = f"{self.timeframe_mapping[timeframe]}min"
        
        ohlc = trades_df['price'].resample(resample_period).ohlc()
        ohlc['volume'] = trades_df['volume'].resample(resample_period).sum()
        
        # Ensure all expected columns are present
        ohlc.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}, inplace=True)
        
        return ohlc

    def get_crypto_data(self, symbol, timeframe, start_date, end_date):
        """
        Retrieve crypto data from Kraken using the Trades endpoint.
        """
        try:
            trades_df = self.get_all_trades(symbol, start_date)
            
            if trades_df.empty:
                self.logger.warning(f"No trade data retrieved for {symbol}")
                return pd.DataFrame()

            self.logger.info(f"Earliest trade data for {symbol}: {trades_df.index[0]}")
            
            ohlc_df = self.get_ohlc_from_trades(trades_df, timeframe)
            
            # Filter by date range
            start_dt = datetime.strptime(start_date, '%Y-%m-%d').replace(tzinfo=pytz.UTC)
            end_dt = datetime.strptime(end_date, '%Y-%m-%d').replace(tzinfo=pytz.UTC)
            ohlc_df = ohlc_df[(ohlc_df.index >= start_dt) & (ohlc_df.index <= end_dt)]

            self.logger.info(f"Resampled to {len(ohlc_df)} OHLC candles for {symbol}")
            return ohlc_df

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
    
    # Test get_all_trades directly
    print("\n=== Testing Trade Data Retrieval ===")
    trades_df = kraken_feed.get_all_trades('SOLUSD', start_date='2024-01-01')
    if not trades_df.empty:
        print(f"Retrieved {len(trades_df)} trades")
        print(f"Earliest trade: {trades_df.index.min()}")
        print(f"Latest trade: {trades_df.index.max()}")
        print(trades_df.head())