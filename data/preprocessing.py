"""
Data Preprocessing Module for Trading Bot

This module handles data cleaning, feature engineering, and other
preprocessing steps for historical price data.
"""

import pandas as pd
import numpy as np
import logging

class DataPreprocessor:
    """
    Handles preprocessing of financial time series data.
    Includes methods for cleaning, feature engineering, and normalization.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.info("DataPreprocessor initialized")

    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Cleans the input DataFrame by handling missing values and duplicates.

        Args:
            df (pd.DataFrame): Input DataFrame with historical price data.

        Returns:
            pd.DataFrame: Cleaned DataFrame.
        """
        self.logger.info("Cleaning data...")
        if df.isnull().sum().sum() > 0:
            self.logger.warning("Missing values detected. Filling with forward fill then backward fill.")
            df.ffill(inplace=True)
            df.bfill(inplace=True)
        
        if df.duplicated().sum() > 0:
            self.logger.warning("Duplicate rows detected. Dropping duplicates.")
            df.drop_duplicates(inplace=True)
            
        self.logger.info("Data cleaning complete.")
        return df

    def add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Adds common technical indicators to the DataFrame.
        
        Args:
            df (pd.DataFrame): Input DataFrame with 'open', 'high', 'low', 'close', 'volume' columns.
            
        Returns:
            pd.DataFrame: DataFrame with added technical indicators.
        """
        self.logger.info("Adding technical indicators...")
        
        # Simple Moving Average (SMA)
        df['SMA_10'] = df['close'].rolling(window=10).mean()
        df['SMA_20'] = df['close'].rolling(window=20).mean()
        
        # Exponential Moving Average (EMA)
        df['EMA_12'] = df['close'].ewm(span=12, adjust=False).mean()
        df['EMA_26'] = df['close'].ewm(span=26, adjust=False).mean()
        
        # Moving Average Convergence Divergence (MACD)
        df['MACD'] = df['EMA_12'] - df['EMA_26']
        df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_Histogram'] = df['MACD'] - df['Signal_Line']
        
        # Relative Strength Index (RSI)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # Bollinger Bands
        df['BB_Middle'] = df['close'].rolling(window=20).mean()
        df['BB_Upper'] = df['BB_Middle'] + (df['close'].rolling(window=20).std() * 2)
        df['BB_Lower'] = df['BB_Middle'] - (df['close'].rolling(window=20).std() * 2)
        
        # Log Returns
        df['Log_Returns'] = np.log(df['close'] / df['close'].shift(1))
        
        # Volatility (Standard Deviation of Log Returns)
        df['Volatility'] = df['Log_Returns'].rolling(window=20).std() * np.sqrt(252) # Annualized
        
        self.logger.info("Technical indicators added.")
        return df # Do not dropna here, handle it in preprocess

    def normalize_features(self, df: pd.DataFrame, features: list = None) -> pd.DataFrame:
        """
        Normalizes specified features using Min-Max Scaling.

        Args:
            df (pd.DataFrame): Input DataFrame.
            features (list, optional): List of column names to normalize. If None, normalizes all numeric columns.

        Returns:
            pd.DataFrame: DataFrame with normalized features.
        """
        self.logger.info("Normalizing features...")
        df_normalized = df.copy()
        
        if features is None:
            features = df.select_dtypes(include=[np.number]).columns.tolist()
            # Exclude 'volume' if it's not intended for normalization with other indicators
            if 'volume' in features:
                features.remove('volume') 
        
        for feature in features:
            if feature in df_normalized.columns:
                min_val = df_normalized[feature].min()
                max_val = df_normalized[feature].max()
                if max_val - min_val != 0:
                    df_normalized[feature] = (df_normalized[feature] - min_val) / (max_val - min_val)
                else:
                    df_normalized[feature] = 0.0 # Handle case where all values are the same
            else:
                self.logger.warning(f"Feature '{feature}' not found in DataFrame for normalization.")
                
        self.logger.info("Feature normalization complete.")
        return df_normalized

    def preprocess(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Applies a full preprocessing pipeline to the data.

        Args:
            df (pd.DataFrame): Raw historical price data.

        Returns:
            pd.DataFrame: Preprocessed data ready for strategy.
        """
        self.logger.info("Starting full data preprocessing pipeline.")
        
        # Check minimum data requirements (increased for backtrader compatibility)
        if len(df) < 100:
            self.logger.error(f"Insufficient data for preprocessing: {len(df)} rows (minimum 100 required)")
            return pd.DataFrame()
        
        df = self.clean_data(df)
        
        # Ensure we still have enough data after cleaning
        if len(df) < 80:
            self.logger.error(f"Insufficient data after cleaning: {len(df)} rows (minimum 80 required)")
            return pd.DataFrame()
        
        df = self.add_technical_indicators(df)
        
        # Drop rows with NaN values introduced by rolling windows after all indicators are added
        initial_rows = len(df)
        df.dropna(inplace=True)
        
        # Check if we have enough data left after dropping NaN values (increased for backtrader)
        if len(df) < 60:
            self.logger.error(f"Insufficient data after dropping NaN values: {len(df)} rows (minimum 60 required)")
            return pd.DataFrame()
        
        if len(df) < initial_rows:
            self.logger.info(f"Dropped {initial_rows - len(df)} rows due to NaN values after indicator calculation.")

        # Ensure required columns exist
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            self.logger.error(f"Missing required columns after preprocessing: {missing_columns}")
            return pd.DataFrame()

        # Define features to normalize (excluding 'open', 'high', 'low', 'close', 'volume' if they are raw prices)
        features_to_normalize = [col for col in df.columns if col not in ['open', 'high', 'low', 'close', 'volume']]
        
        # Only normalize if we have features to normalize
        if features_to_normalize:
            df = self.normalize_features(df, features=features_to_normalize)
        
        self.logger.info(f"Full data preprocessing pipeline complete. Final shape: {df.shape}")
        return df

if __name__ == "__main__":
    # Example Usage
    logging.basicConfig(level=logging.INFO)

    # Create a sample DataFrame
    data = {
        'timestamp': pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03', '2023-01-04', '2023-01-05',
                                     '2023-01-06', '2023-01-07', '2023-01-08', '2023-01-09', '2023-01-10',
                                     '2023-01-11', '2023-01-12', '2023-01-13', '2023-01-14', '2023-01-15',
                                     '2023-01-16', '2023-01-17', '2023-01-18', '2023-01-19', '2023-01-20',
                                     '2023-01-21', '2023-01-22', '2023-01-23', '2023-01-24', '2023-01-25']),
        'open': np.random.rand(25) * 100 + 100,
        'high': np.random.rand(25) * 100 + 105,
        'low': np.random.rand(25) * 100 + 95,
        'close': np.random.rand(25) * 100 + 100,
        'volume': np.random.randint(1000, 5000, 25)
    }
    sample_df = pd.DataFrame(data).set_index('timestamp')
    
    # Introduce some missing values and duplicates for testing
    sample_df.loc['2023-01-05', 'close'] = np.nan
    sample_df = pd.concat([sample_df, sample_df.loc[['2023-01-10']]])

    preprocessor = DataPreprocessor()
    processed_df = preprocessor.preprocess(sample_df.copy())

    print("\nOriginal Sample Data Head:")
    print(sample_df.head())
    print("\nProcessed Data Head:")
    print(processed_df.head())
    print("\nProcessed Data Info:")
    processed_df.info()
    print("\nProcessed Data Description:")
    print(processed_df.describe())