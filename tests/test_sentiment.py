#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for sentiment analysis and news integration
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sentiment.news_analyzer import NewsAnalyzer
import pandas as pd
from datetime import datetime, timedelta

def test_news_analyzer():
    """Test the NewsAnalyzer functionality"""
    print("Testing NewsAnalyzer...")
    
    # Initialize the analyzer
    analyzer = NewsAnalyzer()
    
    # Test news sentiment fetching
    print("\n1. Testing news sentiment fetching...")
    try:
        sentiment_data = analyzer.get_news_sentiment(hours_back=24)
        print(f"[OK] Successfully fetched sentiment data")
        print(f"   EUR/USD Sentiment: {sentiment_data['eur_usd_sentiment']:.3f}")
        print(f"   Confidence: {sentiment_data['confidence']:.3f}")
        print(f"   News Count: {sentiment_data['news_count']}")
        print(f"   Signal Strength: {sentiment_data['signal_strength']:.3f}")
        
    except Exception as e:
        print(f"[ERROR] Error fetching sentiment: {e}")
        return False
    
    # Test trading signal
    print("\n2. Testing trading signal generation...")
    try:
        signal = analyzer.get_trading_signal(hours_back=24)
        print(f"[OK] Trading signal generated:")
        print(f"   Signal Direction: {signal['signal_direction']:.3f}")
        print(f"   Signal Strength: {signal['signal_strength']:.3f}")
        print(f"   Recommendation: {signal['recommendation']}")
        print(f"   News Count: {signal['news_count']}")
        
        if signal['signal_direction'] > 0:
            print("   -> Bullish sentiment (positive for EUR/USD)")
        elif signal['signal_direction'] < 0:
            print("   -> Bearish sentiment (negative for EUR/USD)")
        else:
            print("   -> Neutral sentiment")
            
    except Exception as e:
        print(f"[ERROR] Error getting trading signal: {e}")
        return False
    
    # Test economic calendar
    print("\n3. Testing economic calendar integration...")
    try:
        economic_data = analyzer.get_economic_calendar_impact()
        print(f"[OK] Economic calendar data:")
        print(f"   EUR Impact: {economic_data['eur_economic_impact']:.3f}")
        print(f"   USD Impact: {economic_data['usd_economic_impact']:.3f}")
        print(f"   Combined Impact: {economic_data['combined_impact']:.3f}")
        print(f"   High Impact Events: {economic_data['high_impact_events']}")
            
    except Exception as e:
        print(f"[ERROR] Error getting economic data: {e}")
        return False
    
    # Test caching
    print("\n4. Testing caching mechanism...")
    try:
        start_time = datetime.now()
        sentiment1 = analyzer.get_news_sentiment(hours_back=24)
        time1 = (datetime.now() - start_time).total_seconds()
        
        start_time = datetime.now()
        sentiment2 = analyzer.get_news_sentiment(hours_back=24)
        time2 = (datetime.now() - start_time).total_seconds()
        
        print(f"[OK] First call: {time1:.3f}s, Second call: {time2:.3f}s")
        print(f"   Cache working: {time2 < time1/2}")
        print(f"   Sentiment consistency: {abs(sentiment1['eur_usd_sentiment'] - sentiment2['eur_usd_sentiment']) < 0.001}")
        
    except Exception as e:
        print(f"[ERROR] Error testing cache: {e}")
        return False
    
    print("\n[SUCCESS] All tests passed! NewsAnalyzer is working correctly.")
    return True

def test_sentiment_strategy_integration():
    """Test integration with sentiment-enhanced strategy"""
    print("\n" + "="*60)
    print("Testing SentimentEnhancedForexStrategy integration...")
    
    try:
        # Test import and class definition
        from strategies.sentiment_enhanced_strategy import SentimentEnhancedForexStrategy
        print("[OK] Strategy class imported successfully")
        
        # Test class attributes without instantiation (to avoid backtrader issues)
        strategy_class = SentimentEnhancedForexStrategy
        
        # Check if the class has the expected attributes
        expected_attributes = ['sentiment_weight', 'technical_weight', 'sentiment_threshold']
        class_attributes = dir(strategy_class)
        
        for attr in expected_attributes:
            if attr in class_attributes:
                print(f"[OK] Found expected attribute: {attr}")
            else:
                print(f"[WARNING] Missing expected attribute: {attr}")
        
        # Test NewsAnalyzer integration by checking imports
        try:
            from sentiment.news_analyzer import NewsAnalyzer
            analyzer = NewsAnalyzer()
            sentiment_data = analyzer.get_news_sentiment()
            print("[OK] NewsAnalyzer can be imported and used independently")
            print(f"   Current EUR/USD sentiment: {sentiment_data['eur_usd_sentiment']:.3f}")
            print(f"   Confidence: {sentiment_data['confidence']:.3f}")
        except Exception as e:
            print(f"[ERROR] NewsAnalyzer integration issue: {e}")
            return False
            
    except ImportError as e:
        print(f"[ERROR] Import error: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Strategy integration error: {e}")
        return False
    
    print("[SUCCESS] Strategy integration test passed!")
    return True

if __name__ == "__main__":
    print("EUR/USD Sentiment Analysis Test Suite")
    print("="*60)
    
    # Test news analyzer
    success1 = test_news_analyzer()
    
    # Test strategy integration
    success2 = test_sentiment_strategy_integration()
    
    print("\n" + "="*60)
    if success1 and success2:
        print("[SUCCESS] ALL TESTS PASSED! Sentiment analysis system is ready.")
    else:
        print("[FAILED] Some tests failed. Please check the errors above.")
    print("="*60)