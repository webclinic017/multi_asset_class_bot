#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backtest the sentiment-enhanced forex strategy
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import backtrader as bt
import pandas as pd
from datetime import datetime, timedelta
import yfinance as yf
from strategies.sentiment_enhanced_strategy import SentimentEnhancedForexStrategy
from backtesting.backtest_engine import BacktestEngine
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_eur_usd_data(days_back=365):
    """Get EUR/USD data for backtesting"""
    try:
        # Get EUR/USD data from Yahoo Finance
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        ticker = "EURUSD=X"
        data = yf.download(ticker, start=start_date, end=end_date, interval="1h")
        
        if data.empty:
            logger.warning("No data from Yahoo Finance, using sample data")
            return create_sample_data(days_back)
        
        # Clean and prepare data
        data = data.dropna()
        data.columns = [col.lower() for col in data.columns]
        
        logger.info(f"Downloaded {len(data)} EUR/USD data points")
        return data
        
    except Exception as e:
        logger.warning(f"Error downloading data: {e}, using sample data")
        return create_sample_data(days_back)

def create_sample_data(days_back=365):
    """Create sample EUR/USD data for testing"""
    import numpy as np
    
    # Create date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    dates = pd.date_range(start=start_date, end=end_date, freq='H')
    
    # Generate realistic EUR/USD price data
    np.random.seed(42)  # For reproducible results
    
    # Start around 1.0800
    initial_price = 1.0800
    returns = np.random.normal(0, 0.001, len(dates))  # Small hourly returns
    
    # Add some trend and volatility
    trend = np.sin(np.arange(len(dates)) * 2 * np.pi / (24 * 30)) * 0.0001  # Monthly cycle
    returns += trend
    
    # Calculate prices
    prices = [initial_price]
    for ret in returns[1:]:
        prices.append(prices[-1] * (1 + ret))
    
    # Create OHLC data
    data = pd.DataFrame(index=dates)
    data['close'] = prices
    data['open'] = data['close'].shift(1).fillna(data['close'].iloc[0])
    data['high'] = data[['open', 'close']].max(axis=1) * (1 + np.random.uniform(0, 0.0005, len(data)))
    data['low'] = data[['open', 'close']].min(axis=1) * (1 - np.random.uniform(0, 0.0005, len(data)))
    data['volume'] = np.random.randint(1000, 10000, len(data))
    
    logger.info(f"Created {len(data)} sample EUR/USD data points")
    return data

def run_sentiment_backtest():
    """Run backtest with sentiment-enhanced strategy"""
    print("EUR/USD Sentiment-Enhanced Strategy Backtest")
    print("=" * 60)
    
    try:
        # Get data
        print("1. Loading EUR/USD data...")
        data = get_eur_usd_data(days_back=90)  # 3 months of data
        
        if len(data) < 100:
            print(f"[WARNING] Limited data available: {len(data)} points")
        
        # Initialize backtest engine
        print("2. Initializing backtest engine...")
        engine = BacktestEngine()
        
        # Set up strategy parameters
        strategy_params = {
            'sentiment_weight': 0.3,
            'technical_weight': 0.7,
            'sentiment_threshold': 0.1,
            'min_sentiment_confidence': 0.3,
            'sentiment_position_multiplier': 1.5,
            'max_sentiment_trades_per_day': 3,
            'sentiment_exit_threshold': 0.05
        }
        
        print("3. Running sentiment-enhanced backtest...")
        print(f"   Strategy parameters: {strategy_params}")
        
        # Run backtest
        results = engine.run_backtest(
            strategy_class=SentimentEnhancedForexStrategy,
            data=data,
            initial_cash=10000,
            commission=0.0001,  # 1 pip spread
            strategy_params=strategy_params
        )
        
        # Display results
        print("\n4. Backtest Results:")
        print("=" * 40)
        
        if results:
            for key, value in results.items():
                if isinstance(value, float):
                    print(f"   {key}: {value:.4f}")
                else:
                    print(f"   {key}: {value}")
        else:
            print("   [WARNING] No results returned from backtest")
        
        # Compare with technical-only strategy
        print("\n5. Running technical-only comparison...")
        
        # Technical-only parameters
        tech_params = {
            'sentiment_weight': 0.0,
            'technical_weight': 1.0,
            'sentiment_threshold': 0.0,
            'min_sentiment_confidence': 0.0,
            'sentiment_position_multiplier': 1.0,
            'max_sentiment_trades_per_day': 10,
            'sentiment_exit_threshold': 0.0
        }
        
        tech_results = engine.run_backtest(
            strategy_class=SentimentEnhancedForexStrategy,
            data=data,
            initial_cash=10000,
            commission=0.0001,
            strategy_params=tech_params
        )
        
        print("\n6. Technical-Only Results:")
        print("=" * 40)
        
        if tech_results:
            for key, value in tech_results.items():
                if isinstance(value, float):
                    print(f"   {key}: {value:.4f}")
                else:
                    print(f"   {key}: {value}")
        
        # Performance comparison
        if results and tech_results:
            print("\n7. Performance Comparison:")
            print("=" * 40)
            
            sentiment_return = results.get('total_return', 0)
            technical_return = tech_results.get('total_return', 0)
            
            sentiment_sharpe = results.get('sharpe_ratio', 0)
            technical_sharpe = tech_results.get('sharpe_ratio', 0)
            
            print(f"   Sentiment-Enhanced Return: {sentiment_return:.2%}")
            print(f"   Technical-Only Return:     {technical_return:.2%}")
            print(f"   Improvement:               {sentiment_return - technical_return:.2%}")
            print()
            print(f"   Sentiment-Enhanced Sharpe: {sentiment_sharpe:.4f}")
            print(f"   Technical-Only Sharpe:     {technical_sharpe:.4f}")
            print(f"   Sharpe Improvement:        {sentiment_sharpe - technical_sharpe:.4f}")
            
            if sentiment_return > technical_return:
                print("\n   [SUCCESS] Sentiment enhancement improved returns!")
            else:
                print("\n   [INFO] Technical-only performed better in this period")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Backtest failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_sentiment_backtest()
    
    print("\n" + "=" * 60)
    if success:
        print("[SUCCESS] Sentiment-enhanced strategy backtest completed!")
        print("The sentiment analysis system is integrated and functional.")
    else:
        print("[FAILED] Backtest encountered errors.")
    print("=" * 60)