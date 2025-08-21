"""
News and Sentiment Analysis Module for EUR/USD Trading
Integrates free news sources and sentiment analysis for enhanced trading signals
"""

import requests
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import time
import re
from textblob import TextBlob
import feedparser
# import yfinance as yf  # Not needed for RSS-based news analysis
from bs4 import BeautifulSoup
import pandas as pd

logger = logging.getLogger(__name__)

class NewsAnalyzer:
    """
    Comprehensive news and sentiment analyzer for EUR/USD trading
    Uses free news sources and sentiment analysis
    """
    
    def __init__(self):
        """Initialize the news analyzer with free sources"""
        self.news_sources = {
            'reuters_forex': 'https://feeds.reuters.com/reuters/UKforex',
            'reuters_europe': 'https://feeds.reuters.com/reuters/UKEuropeNews',
            'reuters_us': 'https://feeds.reuters.com/reuters/domesticNews',
            'bbc_business': 'http://feeds.bbci.co.uk/news/business/rss.xml',
            'cnbc_forex': 'https://www.cnbc.com/id/100727362/device/rss/rss.html',
            'marketwatch': 'http://feeds.marketwatch.com/marketwatch/marketpulse/',
            'yahoo_finance': 'https://feeds.finance.yahoo.com/rss/2.0/headline'
        }
        
        # EUR/USD relevant keywords for filtering
        self.eur_keywords = [
            'euro', 'eur', 'european central bank', 'ecb', 'eurozone', 'lagarde',
            'germany', 'france', 'italy', 'spain', 'inflation', 'gdp', 'unemployment',
            'brexit', 'eu', 'european union', 'draghi'
        ]
        
        self.usd_keywords = [
            'dollar', 'usd', 'federal reserve', 'fed', 'powell', 'fomc', 'interest rate',
            'united states', 'usa', 'america', 'treasury', 'yellen', 'inflation',
            'employment', 'nonfarm', 'gdp', 'cpi', 'ppi'
        ]
        
        # Economic indicators impact mapping
        self.economic_indicators = {
            'interest_rate': {'weight': 0.9, 'eur_impact': 1.0, 'usd_impact': -1.0},
            'inflation': {'weight': 0.8, 'eur_impact': 0.7, 'usd_impact': -0.7},
            'gdp': {'weight': 0.7, 'eur_impact': 0.8, 'usd_impact': -0.8},
            'employment': {'weight': 0.6, 'eur_impact': 0.6, 'usd_impact': -0.6},
            'trade': {'weight': 0.5, 'eur_impact': 0.5, 'usd_impact': -0.5}
        }
        
        self.sentiment_cache = {}
        self.news_cache = {}
        self.cache_duration = 3600  # 1 hour cache
        
        logger.info("NewsAnalyzer initialized with free news sources")
    
    def get_news_sentiment(self, hours_back: int = 24) -> Dict[str, float]:
        """
        Get comprehensive news sentiment for EUR/USD
        
        Args:
            hours_back: Hours to look back for news
            
        Returns:
            Dict with sentiment scores and analysis
        """
        try:
            # Check cache first
            cache_key = f"sentiment_{hours_back}"
            if self._is_cache_valid(cache_key):
                return self.sentiment_cache[cache_key]
            
            logger.info(f"Fetching news sentiment for last {hours_back} hours")
            
            # Collect news from all sources
            all_news = []
            for source_name, source_url in self.news_sources.items():
                try:
                    news_items = self._fetch_rss_news(source_url, hours_back)
                    for item in news_items:
                        item['source'] = source_name
                    all_news.extend(news_items)
                    time.sleep(0.5)  # Rate limiting
                except Exception as e:
                    logger.warning(f"Failed to fetch from {source_name}: {e}")
            
            # Filter EUR/USD relevant news
            relevant_news = self._filter_relevant_news(all_news)
            
            # Analyze sentiment
            sentiment_analysis = self._analyze_sentiment(relevant_news)
            
            # Cache results
            self.sentiment_cache[cache_key] = sentiment_analysis
            
            logger.info(f"Analyzed {len(relevant_news)} relevant news items")
            return sentiment_analysis
            
        except Exception as e:
            logger.error(f"Error getting news sentiment: {e}")
            return self._get_default_sentiment()
    
    def _fetch_rss_news(self, url: str, hours_back: int) -> List[Dict]:
        """Fetch news from RSS feed"""
        try:
            feed = feedparser.parse(url)
            news_items = []
            cutoff_time = datetime.now() - timedelta(hours=hours_back)
            
            for entry in feed.entries[:50]:  # Limit to recent entries
                try:
                    # Parse publication date
                    pub_date = None
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        pub_date = datetime(*entry.published_parsed[:6])
                    elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                        pub_date = datetime(*entry.updated_parsed[:6])
                    
                    # Skip old news
                    if pub_date and pub_date < cutoff_time:
                        continue
                    
                    # Extract content
                    title = getattr(entry, 'title', '')
                    summary = getattr(entry, 'summary', '')
                    content = f"{title} {summary}"
                    
                    if content.strip():
                        news_items.append({
                            'title': title,
                            'content': content,
                            'published': pub_date or datetime.now(),
                            'url': getattr(entry, 'link', '')
                        })
                        
                except Exception as e:
                    logger.debug(f"Error parsing news entry: {e}")
                    continue
            
            return news_items
            
        except Exception as e:
            logger.warning(f"Error fetching RSS from {url}: {e}")
            return []
    
    def _filter_relevant_news(self, news_items: List[Dict]) -> List[Dict]:
        """Filter news relevant to EUR/USD"""
        relevant_news = []
        
        for item in news_items:
            content_lower = item['content'].lower()
            
            # Check for EUR/USD relevance
            eur_score = sum(1 for keyword in self.eur_keywords if keyword in content_lower)
            usd_score = sum(1 for keyword in self.usd_keywords if keyword in content_lower)
            
            # Must have at least one EUR or USD keyword
            if eur_score > 0 or usd_score > 0:
                item['eur_relevance'] = eur_score
                item['usd_relevance'] = usd_score
                item['total_relevance'] = eur_score + usd_score
                relevant_news.append(item)
        
        # Sort by relevance and recency
        relevant_news.sort(key=lambda x: (x['total_relevance'], x['published']), reverse=True)
        
        return relevant_news[:100]  # Limit to top 100 most relevant
    
    def _analyze_sentiment(self, news_items: List[Dict]) -> Dict[str, float]:
        """Analyze sentiment of news items"""
        if not news_items:
            return self._get_default_sentiment()
        
        eur_sentiments = []
        usd_sentiments = []
        overall_sentiments = []
        
        for item in news_items:
            try:
                # Get sentiment using TextBlob
                blob = TextBlob(item['content'])
                sentiment_score = blob.sentiment.polarity  # -1 to 1
                
                # Weight by relevance and recency
                relevance_weight = min(item['total_relevance'] / 5.0, 1.0)
                time_weight = self._calculate_time_weight(item['published'])
                weighted_sentiment = sentiment_score * relevance_weight * time_weight
                
                overall_sentiments.append(weighted_sentiment)
                
                # Separate EUR and USD sentiment
                if item['eur_relevance'] > 0:
                    eur_weight = item['eur_relevance'] / item['total_relevance']
                    eur_sentiments.append(weighted_sentiment * eur_weight)
                
                if item['usd_relevance'] > 0:
                    usd_weight = item['usd_relevance'] / item['total_relevance']
                    usd_sentiments.append(weighted_sentiment * usd_weight)
                    
            except Exception as e:
                logger.debug(f"Error analyzing sentiment for item: {e}")
                continue
        
        # Calculate final sentiment scores
        overall_sentiment = sum(overall_sentiments) / len(overall_sentiments) if overall_sentiments else 0
        eur_sentiment = sum(eur_sentiments) / len(eur_sentiments) if eur_sentiments else 0
        usd_sentiment = sum(usd_sentiments) / len(usd_sentiments) if usd_sentiments else 0
        
        # EUR/USD sentiment (positive = EUR bullish, negative = USD bullish)
        eur_usd_sentiment = eur_sentiment - usd_sentiment
        
        # Confidence based on number of news items
        confidence = min(len(news_items) / 20.0, 1.0)  # Max confidence at 20+ news items
        
        return {
            'overall_sentiment': overall_sentiment,
            'eur_sentiment': eur_sentiment,
            'usd_sentiment': usd_sentiment,
            'eur_usd_sentiment': eur_usd_sentiment,
            'confidence': confidence,
            'news_count': len(news_items),
            'timestamp': datetime.now(),
            'signal_strength': abs(eur_usd_sentiment) * confidence
        }
    
    def _calculate_time_weight(self, pub_date: datetime) -> float:
        """Calculate time-based weight (more recent = higher weight)"""
        if not pub_date:
            return 0.5
        
        hours_ago = (datetime.now() - pub_date).total_seconds() / 3600
        
        if hours_ago <= 1:
            return 1.0
        elif hours_ago <= 6:
            return 0.8
        elif hours_ago <= 12:
            return 0.6
        elif hours_ago <= 24:
            return 0.4
        else:
            return 0.2
    
    def get_economic_calendar_impact(self) -> Dict[str, float]:
        """
        Get economic calendar impact for EUR/USD
        Uses free sources for economic data
        """
        try:
            # This would integrate with free economic calendar APIs
            # For now, return neutral impact
            return {
                'eur_economic_impact': 0.0,
                'usd_economic_impact': 0.0,
                'combined_impact': 0.0,
                'high_impact_events': 0
            }
        except Exception as e:
            logger.error(f"Error getting economic calendar: {e}")
            return {
                'eur_economic_impact': 0.0,
                'usd_economic_impact': 0.0,
                'combined_impact': 0.0,
                'high_impact_events': 0
            }
    
    def get_trading_signal(self, hours_back: int = 24) -> Dict[str, float]:
        """
        Get comprehensive trading signal based on news and sentiment
        
        Returns:
            Dict with signal strength and direction
        """
        try:
            # Get sentiment analysis
            sentiment = self.get_news_sentiment(hours_back)
            
            # Get economic calendar impact
            economic = self.get_economic_calendar_impact()
            
            # Combine signals
            sentiment_signal = sentiment['eur_usd_sentiment'] * sentiment['confidence']
            economic_signal = economic['combined_impact']
            
            # Weight the signals
            combined_signal = (sentiment_signal * 0.7) + (economic_signal * 0.3)
            
            # Signal strength (0 to 1)
            signal_strength = min(abs(combined_signal), 1.0)
            
            # Signal direction (-1 to 1)
            signal_direction = max(-1.0, min(1.0, combined_signal))
            
            return {
                'signal_direction': signal_direction,  # -1 (sell) to 1 (buy)
                'signal_strength': signal_strength,    # 0 to 1
                'sentiment_component': sentiment_signal,
                'economic_component': economic_signal,
                'confidence': sentiment['confidence'],
                'news_count': sentiment['news_count'],
                'recommendation': self._get_recommendation(signal_direction, signal_strength)
            }
            
        except Exception as e:
            logger.error(f"Error getting trading signal: {e}")
            return {
                'signal_direction': 0.0,
                'signal_strength': 0.0,
                'sentiment_component': 0.0,
                'economic_component': 0.0,
                'confidence': 0.0,
                'news_count': 0,
                'recommendation': 'NEUTRAL'
            }
    
    def _get_recommendation(self, direction: float, strength: float) -> str:
        """Get trading recommendation based on signal"""
        if strength < 0.3:
            return 'NEUTRAL'
        elif direction > 0.5 and strength > 0.6:
            return 'STRONG_BUY'
        elif direction > 0.2 and strength > 0.4:
            return 'BUY'
        elif direction < -0.5 and strength > 0.6:
            return 'STRONG_SELL'
        elif direction < -0.2 and strength > 0.4:
            return 'SELL'
        else:
            return 'NEUTRAL'
    
    def _get_default_sentiment(self) -> Dict[str, float]:
        """Return default neutral sentiment"""
        return {
            'overall_sentiment': 0.0,
            'eur_sentiment': 0.0,
            'usd_sentiment': 0.0,
            'eur_usd_sentiment': 0.0,
            'confidence': 0.0,
            'news_count': 0,
            'timestamp': datetime.now(),
            'signal_strength': 0.0
        }
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache is still valid"""
        if cache_key not in self.sentiment_cache:
            return False
        
        cache_time = self.sentiment_cache[cache_key].get('timestamp')
        if not cache_time:
            return False
        
        return (datetime.now() - cache_time).total_seconds() < self.cache_duration

# Singleton instance
news_analyzer = NewsAnalyzer()