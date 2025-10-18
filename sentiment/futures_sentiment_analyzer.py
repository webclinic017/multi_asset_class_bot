"""
Futures Sentiment Analyzer
Free sentiment analysis for futures trading using RSS feeds and TextBlob
Based on CURRENT_HFT_FUTURES_TRADING_STRATEGIES.md
"""

import feedparser
from textblob import TextBlob
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional
import requests


class FuturesSentimentAnalyzer:
    """
    Free sentiment analysis for futures trading
    Uses RSS feeds and TextBlob for zero-cost sentiment analysis
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Free news sources by commodity category
        self.commodity_news_sources = {
            'energy': {
                'reuters': 'https://feeds.reuters.com/reuters/businessNews',
                'oilprice': 'https://oilprice.com/rss/main',
                'eia': 'https://www.eia.gov/rss/todayinenergy.xml'
            },
            'metals': {
                'reuters': 'https://feeds.reuters.com/reuters/UKMetalsNews',
                'kitco': 'https://www.kitco.com/rss/KitcoNews.xml',
                'mining': 'https://www.mining.com/feed/'
            },
            'agriculture': {
                'reuters': 'https://feeds.reuters.com/reuters/UKAgricultureNews',
                'agweb': 'https://www.agweb.com/rss.xml',
                'usda': 'https://www.usda.gov/rss/latest-releases.xml'
            },
            'indices': {
                'reuters': 'https://feeds.reuters.com/reuters/businessNews',
                'marketwatch': 'http://feeds.marketwatch.com/marketwatch/marketpulse/',
                'cnbc': 'https://www.cnbc.com/id/100003114/device/rss/rss.html'
            },
            'financial': {
                'reuters': 'https://feeds.reuters.com/reuters/businessNews',
                'marketwatch': 'http://feeds.marketwatch.com/marketwatch/marketpulse/',
                'fed': 'https://www.federalreserve.gov/feeds/press_all.xml'
            }
        }
        
        # Commodity-specific keywords for filtering
        self.commodity_keywords = {
            'CL': ['crude', 'oil', 'wti', 'brent', 'opec', 'petroleum', 'energy'],
            'NG': ['natural gas', 'lng', 'gas storage', 'heating', 'weather'],
            'GC': ['gold', 'precious metals', 'safe haven', 'inflation hedge'],
            'SI': ['silver', 'precious metals', 'industrial demand'],
            'HG': ['copper', 'industrial metals', 'manufacturing'],
            'ES': ['s&p', 'stocks', 'equity', 'market', 'dow', 'nasdaq'],
            'NQ': ['nasdaq', 'tech stocks', 'technology', 'growth stocks'],
            'YM': ['dow', 'dow jones', 'industrial average'],
            'ZC': ['corn', 'grain', 'crop', 'harvest', 'planting'],
            'ZS': ['soybean', 'oilseed', 'crush', 'export'],
            'ZW': ['wheat', 'grain', 'crop', 'harvest'],
            'ZN': ['treasury', 'bond', 'yield', 'interest rate', 'fed'],
            'RB': ['gasoline', 'rbob', 'refining', 'fuel'],
            'HO': ['heating oil', 'distillate', 'diesel']
        }
    
    def get_commodity_sentiment(self, symbol: str, hours_back: int = 24) -> Dict:
        """
        Get sentiment for specific commodity futures contract
        
        Args:
            symbol: Futures symbol (e.g., 'CL', 'GC', 'ES')
            hours_back: How many hours of news to analyze
            
        Returns:
            Dictionary with sentiment analysis results
        """
        # Determine commodity category
        category = self._get_commodity_category(symbol)
        
        # Fetch news from relevant sources
        all_news = []
        for source_name, source_url in self.commodity_news_sources.get(category, {}).items():
            try:
                news_items = self._fetch_rss_news(source_url, hours_back)
                all_news.extend(news_items)
                self.logger.debug(f"Fetched {len(news_items)} items from {source_name}")
            except Exception as e:
                self.logger.warning(f"Failed to fetch from {source_name}: {e}")
        
        # Filter for commodity-specific news
        relevant_news = self._filter_commodity_news(all_news, symbol)
        
        # Analyze sentiment
        sentiment_score = self._calculate_sentiment_score(relevant_news)
        
        return {
            'symbol': symbol,
            'sentiment_score': sentiment_score,  # -1 to 1
            'news_count': len(relevant_news),
            'confidence': min(len(relevant_news) / 10.0, 1.0),
            'signal': self._get_sentiment_signal(sentiment_score),
            'timestamp': datetime.now(),
            'category': category
        }
    
    def _get_commodity_category(self, symbol: str) -> str:
        """Map symbol to commodity category"""
        categories = {
            'CL': 'energy', 'NG': 'energy', 'RB': 'energy', 'HO': 'energy',
            'GC': 'metals', 'SI': 'metals', 'HG': 'metals', 'PL': 'metals',
            'ZC': 'agriculture', 'ZS': 'agriculture', 'ZW': 'agriculture',
            'ES': 'indices', 'NQ': 'indices', 'YM': 'indices',
            'ZN': 'financial', '6E': 'financial', '6J': 'financial'
        }
        return categories.get(symbol, 'energy')
    
    def _fetch_rss_news(self, url: str, hours_back: int) -> List[Dict]:
        """Fetch news from RSS feed"""
        try:
            feed = feedparser.parse(url)
            news_items = []
            cutoff_time = datetime.now() - timedelta(hours=hours_back)
            
            for entry in feed.entries[:50]:
                try:
                    pub_date = None
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        pub_date = datetime(*entry.published_parsed[:6])
                    
                    if pub_date and pub_date < cutoff_time:
                        continue
                    
                    title = getattr(entry, 'title', '')
                    summary = getattr(entry, 'summary', '')
                    
                    news_items.append({
                        'title': title,
                        'content': f"{title} {summary}",
                        'published': pub_date or datetime.now(),
                        'url': getattr(entry, 'link', '')
                    })
                except:
                    continue
            
            return news_items
            
        except Exception as e:
            self.logger.error(f"Error fetching RSS feed {url}: {e}")
            return []
    
    def _filter_commodity_news(self, news_items: List[Dict], symbol: str) -> List[Dict]:
        """Filter news relevant to specific commodity"""
        keywords = self.commodity_keywords.get(symbol, [])
        relevant_news = []
        
        for item in news_items:
            content_lower = item['content'].lower()
            keyword_matches = sum(1 for kw in keywords if kw in content_lower)
            
            if keyword_matches > 0:
                item['relevance_score'] = keyword_matches
                relevant_news.append(item)
        
        return sorted(relevant_news, key=lambda x: x['relevance_score'], reverse=True)
    
    def _calculate_sentiment_score(self, news_items: List[Dict]) -> float:
        """Calculate aggregate sentiment score"""
        if not news_items:
            return 0.0
        
        sentiments = []
        for item in news_items:
            try:
                blob = TextBlob(item['content'])
                sentiment = blob.sentiment.polarity
                
                # Weight by relevance and recency
                relevance_weight = min(item.get('relevance_score', 1) / 3.0, 1.0)
                time_weight = self._calculate_time_weight(item.get('published'))
                
                weighted_sentiment = sentiment * relevance_weight * time_weight
                sentiments.append(weighted_sentiment)
                
            except Exception as e:
                self.logger.debug(f"Error calculating sentiment: {e}")
        
        return sum(sentiments) / len(sentiments) if sentiments else 0.0
    
    def _calculate_time_weight(self, pub_date: Optional[datetime]) -> float:
        """Calculate time decay weight"""
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
    
    def _get_sentiment_signal(self, sentiment_score: float) -> str:
        """Convert sentiment score to trading signal"""
        if sentiment_score > 0.3:
            return 'BULLISH'
        elif sentiment_score < -0.3:
            return 'BEARISH'
        else:
            return 'NEUTRAL'


class CommodityNewsEventMonitor:
    """
    Monitor critical news events for commodity futures
    Based on CURRENT_HFT_FUTURES_TRADING_STRATEGIES.md
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Economic calendar of high-impact events
        self.event_calendar = {
            'energy': {
                'eia_crude_inventory': {
                    'schedule': 'Wednesday 10:30 AM ET',
                    'frequency': 'weekly',
                    'impact': 'HIGH',
                    'affected_symbols': ['CL', 'RB', 'HO']
                },
                'eia_gas_storage': {
                    'schedule': 'Thursday 10:30 AM ET',
                    'frequency': 'weekly',
                    'impact': 'HIGH',
                    'affected_symbols': ['NG']
                },
                'opec_meeting': {
                    'schedule': 'Variable',
                    'frequency': 'monthly',
                    'impact': 'VERY_HIGH',
                    'affected_symbols': ['CL', 'RB', 'HO']
                }
            },
            'metals': {
                'fomc_meeting': {
                    'schedule': 'Variable (8x/year)',
                    'frequency': 'irregular',
                    'impact': 'VERY_HIGH',
                    'affected_symbols': ['GC', 'SI']
                },
                'cpi_report': {
                    'schedule': 'Monthly ~13th, 8:30 AM ET',
                    'frequency': 'monthly',
                    'impact': 'HIGH',
                    'affected_symbols': ['GC', 'SI', 'HG']
                },
                'nonfarm_payrolls': {
                    'schedule': 'First Friday, 8:30 AM ET',
                    'frequency': 'monthly',
                    'impact': 'HIGH',
                    'affected_symbols': ['GC', 'SI']
                }
            },
            'agriculture': {
                'usda_wasde': {
                    'schedule': 'Monthly ~12th, 12:00 PM ET',
                    'frequency': 'monthly',
                    'impact': 'VERY_HIGH',
                    'affected_symbols': ['ZC', 'ZS', 'ZW']
                },
                'weekly_export_sales': {
                    'schedule': 'Thursday 8:30 AM ET',
                    'frequency': 'weekly',
                    'impact': 'MEDIUM',
                    'affected_symbols': ['ZC', 'ZS', 'ZW']
                },
                'crop_progress': {
                    'schedule': 'Monday 4:00 PM ET',
                    'frequency': 'weekly_seasonal',
                    'impact': 'MEDIUM',
                    'affected_symbols': ['ZC', 'ZS', 'ZW']
                }
            }
        }
    
    def check_upcoming_events(self, symbol: str, minutes_ahead: int = 60) -> List[Dict]:
        """
        Check for upcoming high-impact events
        
        Args:
            symbol: Futures symbol
            minutes_ahead: How many minutes ahead to check
            
        Returns:
            List of upcoming events
        """
        upcoming_events = []
        current_time = datetime.now()
        
        # Get category for symbol
        category = self._get_category_for_symbol(symbol)
        
        if not category:
            return upcoming_events
        
        # Check events for this category
        for event_name, event_info in self.event_calendar.get(category, {}).items():
            if symbol in event_info['affected_symbols']:
                # Calculate next event time (simplified - in production use actual calendar)
                event_time = self._get_next_event_time(event_info)
                
                if event_time:
                    minutes_until = (event_time - current_time).total_seconds() / 60
                    
                    if 0 <= minutes_until <= minutes_ahead:
                        upcoming_events.append({
                            'event': event_name,
                            'time': event_time,
                            'minutes_until': minutes_until,
                            'impact': event_info['impact'],
                            'action': self._get_pre_event_action(minutes_until, event_info['impact'])
                        })
        
        return sorted(upcoming_events, key=lambda x: x['minutes_until'])
    
    def _get_category_for_symbol(self, symbol: str) -> Optional[str]:
        """Get category for a symbol"""
        for category, events in self.event_calendar.items():
            for event_info in events.values():
                if symbol in event_info['affected_symbols']:
                    return category
        return None
    
    def _get_next_event_time(self, event_info: Dict) -> Optional[datetime]:
        """
        Calculate next event time based on schedule
        Simplified version - in production, use actual economic calendar API
        """
        schedule = event_info['schedule']
        current_time = datetime.now()
        
        # Parse schedule (simplified)
        if 'Wednesday' in schedule and '10:30' in schedule:
            # EIA crude inventory - every Wednesday at 10:30 AM ET
            days_ahead = (2 - current_time.weekday()) % 7  # Wednesday is 2
            next_event = current_time + timedelta(days=days_ahead)
            next_event = next_event.replace(hour=10, minute=30, second=0, microsecond=0)
            
            if next_event < current_time:
                next_event += timedelta(days=7)
            
            return next_event
        
        elif 'Thursday' in schedule and '10:30' in schedule:
            # EIA gas storage - every Thursday at 10:30 AM ET
            days_ahead = (3 - current_time.weekday()) % 7  # Thursday is 3
            next_event = current_time + timedelta(days=days_ahead)
            next_event = next_event.replace(hour=10, minute=30, second=0, microsecond=0)
            
            if next_event < current_time:
                next_event += timedelta(days=7)
            
            return next_event
        
        # Add more schedule parsers as needed
        return None
    
    def _get_pre_event_action(self, minutes_until: float, impact: str) -> str:
        """Determine action to take before event"""
        if minutes_until < 5:
            return 'CLOSE_POSITIONS'
        elif minutes_until < 15:
            return 'REDUCE_POSITIONS'
        elif minutes_until < 30:
            return 'TIGHTEN_STOPS'
        else:
            return 'PREPARE'
    
    def get_pre_event_strategy(self, symbol: str, minutes_before_event: int = 30) -> Dict:
        """
        Get trading strategy before major news event
        
        Args:
            symbol: Futures symbol
            minutes_before_event: Minutes before event to start adjusting
            
        Returns:
            Dictionary with recommended actions
        """
        upcoming_events = self.check_upcoming_events(symbol, minutes_before_event)
        
        if not upcoming_events:
            return {'action': 'NORMAL_TRADING'}
        
        # Find nearest high-impact event
        nearest_event = upcoming_events[0]
        
        if nearest_event['minutes_until'] < 5:
            # Very close to event - close positions
            return {
                'action': 'CLOSE_POSITIONS',
                'reason': f"{nearest_event['event']} in {nearest_event['minutes_until']:.0f} minutes",
                'urgency': 'CRITICAL'
            }
        elif nearest_event['minutes_until'] < 15:
            # Close to event - reduce positions
            return {
                'action': 'REDUCE_POSITIONS',
                'reduction_factor': 0.5,
                'reason': f"{nearest_event['event']} approaching",
                'urgency': 'HIGH'
            }
        elif nearest_event['minutes_until'] < 30:
            # Event approaching - tighten stops
            return {
                'action': 'TIGHTEN_STOPS',
                'stop_multiplier': 0.7,
                'reason': f"{nearest_event['event']} in {nearest_event['minutes_until']:.0f} minutes",
                'urgency': 'MEDIUM'
            }
        
        return {'action': 'NORMAL_TRADING'}


class SocialSentimentAnalyzer:
    """
    Analyze social media sentiment from free sources
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.reddit_base = "https://www.reddit.com"
    
    def get_reddit_sentiment(self, subreddit: str = 'wallstreetbets', 
                           keyword: str = 'oil') -> Dict:
        """
        Get sentiment from Reddit discussions
        
        Args:
            subreddit: Subreddit to search
            keyword: Keyword to search for
            
        Returns:
            Dictionary with sentiment results
        """
        try:
            # Use Reddit's JSON API (no authentication needed)
            url = f"{self.reddit_base}/r/{subreddit}/search.json"
            params = {
                'q': keyword,
                'sort': 'new',
                'limit': 100,
                't': 'day'
            }
            
            headers = {'User-Agent': 'TradingBot/1.0'}
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code != 200:
                return {'sentiment': 0, 'post_count': 0, 'source': 'reddit'}
            
            data = response.json()
            posts = data.get('data', {}).get('children', [])
            
            sentiments = []
            for post in posts:
                try:
                    post_data = post.get('data', {})
                    title = post_data.get('title', '')
                    selftext = post_data.get('selftext', '')
                    content = f"{title} {selftext}"
                    
                    blob = TextBlob(content)
                    sentiments.append(blob.sentiment.polarity)
                except:
                    continue
            
            avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0
            
            return {
                'sentiment': avg_sentiment,
                'post_count': len(posts),
                'source': 'reddit',
                'keyword': keyword
            }
            
        except Exception as e:
            self.logger.error(f"Reddit sentiment error: {e}")
            return {'sentiment': 0, 'post_count': 0, 'source': 'reddit'}