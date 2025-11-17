"""
Social Sentiment Analyzer - Track Reddit/Twitter buzz
Detect trending stocks before they explode
Uses Reddit API (PRAW) and basic Twitter scraping
"""

import os
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
from collections import Counter

try:
    import praw
    PRAW_AVAILABLE = True
except ImportError:
    PRAW_AVAILABLE = False

class SocialSentimentAnalyzer:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Reddit API setup (requires credentials)
        self.reddit_client_id = os.environ.get('REDDIT_CLIENT_ID', '')
        self.reddit_client_secret = os.environ.get('REDDIT_CLIENT_SECRET', '')
        self.reddit_user_agent = 'Dai Trader Bot 1.0'
        
        self.reddit = None
        if PRAW_AVAILABLE and self.reddit_client_id and self.reddit_client_secret:
            try:
                self.reddit = praw.Reddit(
                    client_id=self.reddit_client_id,
                    client_secret=self.reddit_client_secret,
                    user_agent=self.reddit_user_agent
                )
            except Exception as e:
                self.logger.warning(f"Reddit API not configured: {e}")
        
        self.cache = {}
        self.cache_duration = 900  # 15 minutes (social data changes fast)
        
        # Sentiment keywords
        self.bullish_keywords = {
            'moon', 'rocket', 'bullish', 'calls', 'buy', 'long', 'squeeze',
            'breakout', 'rally', 'pump', 'bull', 'green', 'tendies', 'gains',
            'to the moon', '🚀', '📈', 'undervalued', 'cheap', 'dip'
        }
        
        self.bearish_keywords = {
            'bearish', 'puts', 'sell', 'short', 'crash', 'dump', 'bubble',
            'overvalued', 'red', 'falling', 'drop', 'plunge', '📉', 'rip',
            'bag holder', 'dead', 'tanking'
        }
    
    def get_social_sentiment(self, symbol: str, hours: int = 24) -> Dict:
        """
        Analyze social media sentiment for a symbol
        Combines Reddit mentions, sentiment, and trend detection
        """
        cache_key = f"social_{symbol}_{hours}"
        now = datetime.now()
        
        # Check cache
        if cache_key in self.cache:
            cached_time, cached_data = self.cache[cache_key]
            if (now - cached_time).total_seconds() < self.cache_duration:
                return cached_data
        
        try:
            # Get Reddit sentiment
            reddit_data = self._analyze_reddit(symbol, hours)
            
            # Combine all sources
            analysis = self._calculate_sentiment(symbol, reddit_data)
            
            # Cache result
            self.cache[cache_key] = (now, analysis)
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing social sentiment for {symbol}: {e}")
            return self._empty_response()
    
    def _analyze_reddit(self, symbol: str, hours: int) -> Dict:
        """Analyze Reddit mentions and sentiment"""
        if not self.reddit:
            return {
                'mentions': 0,
                'sentiment_score': 0,
                'top_posts': [],
                'subreddits': []
            }
        
        try:
            # Search relevant subreddits
            subreddits = ['wallstreetbets', 'stocks', 'investing', 'StockMarket']
            all_posts = []
            mention_count = 0
            bullish_count = 0
            bearish_count = 0
            
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            for sub_name in subreddits:
                try:
                    subreddit = self.reddit.subreddit(sub_name)
                    
                    # Search for symbol mentions
                    for post in subreddit.search(f'${symbol}', time_filter='day', limit=50):
                        post_time = datetime.fromtimestamp(post.created_utc)
                        
                        if post_time < cutoff_time:
                            continue
                        
                        mention_count += 1
                        text = f"{post.title} {post.selftext}".lower()
                        
                        # Count sentiment keywords
                        post_bullish = sum(1 for word in self.bullish_keywords if word in text)
                        post_bearish = sum(1 for word in self.bearish_keywords if word in text)
                        
                        bullish_count += post_bullish
                        bearish_count += post_bearish
                        
                        all_posts.append({
                            'title': post.title,
                            'score': post.score,
                            'num_comments': post.num_comments,
                            'subreddit': sub_name,
                            'url': f"https://reddit.com{post.permalink}",
                            'sentiment': 'bullish' if post_bullish > post_bearish else 'bearish' if post_bearish > post_bullish else 'neutral'
                        })
                except Exception as e:
                    self.logger.debug(f"Error searching r/{sub_name}: {e}")
                    continue
            
            # Calculate sentiment score (-1 to +1)
            total_sentiment_words = bullish_count + bearish_count
            if total_sentiment_words > 0:
                sentiment_score = (bullish_count - bearish_count) / total_sentiment_words
            else:
                sentiment_score = 0
            
            # Sort posts by engagement
            top_posts = sorted(all_posts, key=lambda x: x['score'] + x['num_comments'], reverse=True)[:5]
            
            return {
                'mentions': mention_count,
                'sentiment_score': sentiment_score,
                'bullish_count': bullish_count,
                'bearish_count': bearish_count,
                'top_posts': top_posts,
                'subreddits': subreddits
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing Reddit: {e}")
            return {
                'mentions': 0,
                'sentiment_score': 0,
                'top_posts': [],
                'subreddits': []
            }
    
    def _calculate_sentiment(self, symbol: str, reddit_data: Dict) -> Dict:
        """
        Calculate overall social sentiment score
        """
        mentions = reddit_data['mentions']
        sentiment_score = reddit_data['sentiment_score']
        
        # Determine signal
        signal = "NEUTRAL"
        confidence = 0
        reasons = []
        
        if mentions == 0:
            return self._empty_response()
        
        # High mention volume
        if mentions >= 20:
            confidence += 30
            reasons.append(f"{mentions} Reddit mentions (trending)")
        elif mentions >= 10:
            confidence += 20
            reasons.append(f"{mentions} Reddit mentions")
        elif mentions >= 5:
            confidence += 10
            reasons.append(f"{mentions} Reddit mentions")
        
        # Sentiment direction
        if sentiment_score > 0.3:
            signal = "BULLISH"
            confidence += 40
            reasons.append(f"Positive sentiment ({sentiment_score:.2f})")
        elif sentiment_score > 0.1:
            signal = "BULLISH"
            confidence += 20
            reasons.append(f"Slightly positive sentiment ({sentiment_score:.2f})")
        elif sentiment_score < -0.3:
            signal = "BEARISH"
            confidence += 40
            reasons.append(f"Negative sentiment ({sentiment_score:.2f})")
        elif sentiment_score < -0.1:
            signal = "BEARISH"
            confidence += 20
            reasons.append(f"Slightly negative sentiment ({sentiment_score:.2f})")
        
        # Engagement on top posts
        if reddit_data['top_posts']:
            top_post = reddit_data['top_posts'][0]
            if top_post['score'] > 500 or top_post['num_comments'] > 100:
                confidence += 15
                reasons.append(f"Viral post ({top_post['score']} upvotes)")
        
        # Determine action
        action = "HOLD"
        if signal == "BULLISH" and confidence > 60:
            action = "BUY"
        elif signal == "BEARISH" and confidence > 60:
            action = "AVOID"
        
        return {
            'signal': signal,
            'confidence': min(100, int(confidence)),
            'action': action,
            'mentions': mentions,
            'sentiment_score': round(sentiment_score, 2),
            'bullish_count': reddit_data.get('bullish_count', 0),
            'bearish_count': reddit_data.get('bearish_count', 0),
            'top_posts': reddit_data['top_posts'][:3],
            'reasons': reasons,
            'timestamp': datetime.now().isoformat()
        }
    
    def _empty_response(self) -> Dict:
        """Return empty response when no data available"""
        return {
            'signal': 'NEUTRAL',
            'confidence': 0,
            'action': 'HOLD',
            'mentions': 0,
            'sentiment_score': 0,
            'bullish_count': 0,
            'bearish_count': 0,
            'top_posts': [],
            'reasons': ['No social media data available'],
            'timestamp': datetime.now().isoformat()
        }
    
    def is_trending(self, symbol: str) -> Tuple[bool, str]:
        """
        Check if stock is trending on social media
        Returns: (is_trending, reason)
        """
        analysis = self.get_social_sentiment(symbol)
        
        # High mention volume = trending
        if analysis['mentions'] >= 15:
            return True, f"Trending on Reddit ({analysis['mentions']} mentions)"
        
        # Viral post
        if analysis['top_posts'] and analysis['top_posts'][0]['score'] > 1000:
            return True, f"Viral Reddit post ({analysis['top_posts'][0]['score']} upvotes)"
        
        return False, "Not trending"
    
    def should_trade_on_social(self, symbol: str) -> Tuple[bool, str]:
        """
        Determine if social sentiment supports trading
        Returns: (should_trade, reason)
        """
        analysis = self.get_social_sentiment(symbol)
        
        # Strong positive buzz
        if analysis['signal'] == 'BULLISH' and analysis['confidence'] > 65:
            return True, f"Strong social buzz ({analysis['confidence']}% conf, {analysis['mentions']} mentions)"
        
        # Negative sentiment
        if analysis['signal'] == 'BEARISH' and analysis['confidence'] > 65:
            return False, f"Negative social sentiment ({analysis['confidence']}% conf)"
        
        return True, "Social sentiment neutral"
    
    def get_social_boost(self, symbol: str) -> float:
        """
        Calculate position size multiplier based on social sentiment
        Returns: 0.6 to 1.6 multiplier
        """
        analysis = self.get_social_sentiment(symbol)
        
        if analysis['confidence'] < 50:
            return 1.0
        
        if analysis['signal'] == 'BULLISH':
            # Trending with positive sentiment
            if analysis['mentions'] > 20 and analysis['confidence'] > 75:
                return 1.6  # Viral stock = bigger position
            elif analysis['confidence'] > 70:
                return 1.3
            else:
                return 1.1
        
        elif analysis['signal'] == 'BEARISH':
            # Negative buzz = reduce
            return 0.6
        
        return 1.0
    
    def get_summary(self, symbols: List[str]) -> Dict:
        """Get social sentiment summary for multiple symbols"""
        summary = {
            'trending': [],
            'bullish_buzz': [],
            'bearish_buzz': [],
            'viral_posts': [],
            'timestamp': datetime.now().isoformat()
        }
        
        for symbol in symbols:
            analysis = self.get_social_sentiment(symbol)
            
            # Trending stocks
            if analysis['mentions'] >= 10:
                summary['trending'].append({
                    'symbol': symbol,
                    'mentions': analysis['mentions'],
                    'sentiment': analysis['signal']
                })
            
            # Bullish buzz
            if analysis['signal'] == 'BULLISH' and analysis['confidence'] > 60:
                summary['bullish_buzz'].append({
                    'symbol': symbol,
                    'confidence': analysis['confidence'],
                    'mentions': analysis['mentions']
                })
            
            # Bearish buzz
            if analysis['signal'] == 'BEARISH' and analysis['confidence'] > 60:
                summary['bearish_buzz'].append({
                    'symbol': symbol,
                    'confidence': analysis['confidence']
                })
            
            # Viral posts
            if analysis['top_posts']:
                for post in analysis['top_posts']:
                    if post['score'] > 500:
                        summary['viral_posts'].append({
                            'symbol': symbol,
                            'title': post['title'],
                            'score': post['score'],
                            'url': post['url']
                        })
        
        return summary


if __name__ == "__main__":
    # Test the analyzer
    logging.basicConfig(level=logging.INFO)
    analyzer = SocialSentimentAnalyzer()
    
    test_symbols = ['TSLA', 'GME', 'NVDA']
    for symbol in test_symbols:
        print(f"\n{symbol} Social Sentiment:")
        result = analyzer.get_social_sentiment(symbol)
        print(json.dumps(result, indent=2))
