"""
CCXT Data Feed Module
Provides historical and real-time market data using the ccxt library.
"""

import ccxt
import pandas as pd
import logging
from datetime import datetime
import pytz

class CCXTDataFeed:
    """CCXT data feed for crypto data."""
    
    def __init__(self, config: dict):
        """
        Initialize CCXT data feed.
        
        Args:
            config (dict): Configuration dictionary.
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.exchange_name = 'kraken'  # Default to Kraken, can be made configurable
        
        try:
            self.exchange = getattr(ccxt, self.exchange_name)()
            self.exchange.load_markets()
            self.logger.info(f"CCXTDataFeed initialized for {self.exchange_name}")
        except Exception as e:
            self.logger.error(f"Error initializing CCXT exchange: {e}")
            raise

    def get_crypto_data(self, symbol, timeframe, start_date, end_date):
        """
        Retrieve crypto data from CCXT.
        
        Args:
            symbol (str): Trading pair (e.g., 'SOL/USD')
            timeframe (str): Timeframe (e.g., '1m', '5m', '1h')
            start_date (str): Start date in 'YYYY-MM-DD' format
            end_date (str): End date in 'YYYY-MM-DD' format
            
        Returns:
            pd.DataFrame: Historical price data
        """
        if not self.exchange.has['fetchOHLCV']:
            self.logger.error(f"{self.exchange_name} does not support fetching OHLCV data.")
            return pd.DataFrame()

        try:
            since = int(datetime.strptime(start_date, '%Y-%m-%d').replace(tzinfo=pytz.UTC).timestamp() * 1000)
            end_ts = int(datetime.strptime(end_date, '%Y-%m-%d').replace(tzinfo=pytz.UTC).timestamp() * 1000)
            
            all_ohlcv = self._fetch_all_ohlcv(symbol, timeframe, since, end_ts)

            if not all_ohlcv:
                self.logger.warning(f"No data retrieved for {symbol}")
                return pd.DataFrame()

            df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
            df.set_index('timestamp', inplace=True)
            
            self.logger.info(f"Retrieved {len(df)} OHLCV candles for {symbol}")
            return df

        except Exception as e:
            self.logger.error(f"Error retrieving CCXT data for {symbol}: {e}")
            raise

    def _fetch_all_ohlcv(self, symbol, timeframe, since, end_ts):
        """
        Fetch all OHLCV data from a given start time, handling pagination.
        """
        all_ohlcv = []
        while since < end_ts:
            try:
                ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, since)
                if not ohlcv:
                    break
                
                since = ohlcv[-1][0] + self.exchange.parse_timeframe(timeframe) * 1000
                all_ohlcv.extend(ohlcv)
                
            except Exception as e:
                self.logger.warning(f"Error fetching chunk of OHLCV data: {e}. Retrying...")
                time.sleep(self.exchange.rateLimit / 1000) # Respect rate limit

        return all_ohlcv