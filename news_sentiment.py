"""
News and Sentiment Analysis Module
Analyzes market news and sentiment to inform trading decisions
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List
from alpaca.data.historical import NewsClient
from alpaca.data.requests import NewsRequest
from config import Config

logger = logging.getLogger(__name__)

class NewsSentimentAnalyzer:
    """Analyzes news sentiment for stocks."""
    
    def __init__(self):
        """Initialize news client."""
        try:
            self.news_client = NewsClient(
                api_key=Config.ALPACA_API_KEY,
                secret_key=Config.ALPACA_SECRET_KEY
            )
            self.sentiment_cache = {}  # Cache recent sentiment
            logger.info("News sentiment analyzer initialized")
        except Exception as e:
            logger.error(f"Failed to initialize news client: {e}")
            self.news_client = None
    
    def get_news_sentiment(self, symbol: str, hours: int = 24) -> Dict:
        """
        Get news sentiment for a symbol over the past N hours.
        
        Returns:
            Dict with sentiment score, article count, and summary
        """
        if not self.news_client:
            return self._get_default_sentiment()
        
        try:
            # Check cache first (valid for 30 minutes)
            cache_key = f"{symbol}_{hours}"
            if cache_key in self.sentiment_cache:
                cached = self.sentiment_cache[cache_key]
                if (datetime.now() - cached['timestamp']).seconds < 1800:
                    return cached['data']
            
            # Fetch news from Alpaca
            start_time = datetime.now() - timedelta(hours=hours)
            
            request = NewsRequest(
                symbols=[symbol],
                start=start_time,
                limit=50
            )
            
            news = self.news_client.get_news(request)
            
            if not news or len(news.data) == 0:
                return self._get_default_sentiment()
            
            # Analyze sentiment from news articles
            sentiment_scores = []
            positive_count = 0
            negative_count = 0
            neutral_count = 0
            headlines = []
            
            for article in news.data:
                # Alpaca provides sentiment in the article metadata
                headline = article.headline
                headlines.append(headline)
                
                # Simple sentiment analysis based on keywords
                sentiment = self._analyze_headline_sentiment(headline)
                sentiment_scores.append(sentiment)
                
                if sentiment > 0.1:
                    positive_count += 1
                elif sentiment < -0.1:
                    negative_count += 1
                else:
                    neutral_count += 1
            
            # Calculate overall sentiment
            avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
            
            # Determine sentiment category
            if avg_sentiment > 0.2:
                sentiment_label = "BULLISH"
            elif avg_sentiment < -0.2:
                sentiment_label = "BEARISH"
            else:
                sentiment_label = "NEUTRAL"
            
            # Calculate confidence based on article count and agreement
            article_count = len(news.data)
            agreement = max(positive_count, negative_count, neutral_count) / article_count if article_count > 0 else 0
            confidence = min(agreement * 100, 95)
            
            result = {
                'sentiment_score': avg_sentiment,  # -1 to +1
                'sentiment_label': sentiment_label,
                'confidence': confidence,
                'article_count': article_count,
                'positive_articles': positive_count,
                'negative_articles': negative_count,
                'neutral_articles': neutral_count,
                'top_headlines': headlines[:5],
                'has_major_news': article_count > 10,  # High news volume
                'timestamp': datetime.now()
            }
            
            # Cache the result
            self.sentiment_cache[cache_key] = {
                'data': result,
                'timestamp': datetime.now()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error fetching news sentiment for {symbol}: {e}")
            return self._get_default_sentiment()
    
    def _analyze_headline_sentiment(self, headline: str) -> float:
        """
        Analyze sentiment of a headline using keyword matching.
        Returns score from -1 (very negative) to +1 (very positive)
        """
        headline_lower = headline.lower()
        
        # Positive keywords
        positive_words = [
            'surge', 'soar', 'jump', 'rally', 'gain', 'profit', 'beat', 'exceed',
            'record', 'high', 'growth', 'upgrade', 'buy', 'bullish', 'strong',
            'rise', 'boost', 'advance', 'outperform', 'success', 'positive',
            'breakthrough', 'innovation', 'expansion', 'partnership', 'deal',
            'acquisition', 'revenue', 'earnings beat'
        ]
        
        # Negative keywords
        negative_words = [
            'plunge', 'crash', 'fall', 'drop', 'decline', 'loss', 'miss', 'weak',
            'concern', 'worry', 'risk', 'downgrade', 'sell', 'bearish', 'poor',
            'lawsuit', 'investigation', 'scandal', 'layoff', 'cut', 'bankruptcy',
            'debt', 'warning', 'volatile', 'uncertain', 'fear', 'crisis',
            'delay', 'postpone', 'cancel', 'disappoint'
        ]
        
        # Very strong positive
        very_positive = ['record profit', 'blowout earnings', 'major breakthrough']
        
        # Very strong negative
        very_negative = ['bankruptcy', 'fraud', 'recall', 'criminal']
        
        score = 0.0
        
        # Check very strong signals first
        for phrase in very_positive:
            if phrase in headline_lower:
                score += 0.5
        
        for phrase in very_negative:
            if phrase in headline_lower:
                score -= 0.5
        
        # Count positive and negative words
        positive_count = sum(1 for word in positive_words if word in headline_lower)
        negative_count = sum(1 for word in negative_words if word in headline_lower)
        
        # Calculate sentiment score
        score += (positive_count * 0.15) - (negative_count * 0.15)
        
        # Clamp to -1 to +1 range
        return max(-1.0, min(1.0, score))
    
    def _get_default_sentiment(self) -> Dict:
        """Return neutral sentiment when data is unavailable."""
        return {
            'sentiment_score': 0.0,
            'sentiment_label': 'NEUTRAL',
            'confidence': 0,
            'article_count': 0,
            'positive_articles': 0,
            'negative_articles': 0,
            'neutral_articles': 0,
            'top_headlines': [],
            'has_major_news': False,
            'timestamp': datetime.now()
        }
    
    def should_avoid_trading(self, symbol: str) -> tuple[bool, str]:
        """
        Determine if trading should be avoided due to news.
        
        Returns:
            (should_avoid: bool, reason: str)
        """
        sentiment = self.get_news_sentiment(symbol, hours=4)  # Last 4 hours
        
        # Avoid trading during major negative news
        if sentiment['sentiment_label'] == 'BEARISH' and sentiment['confidence'] > 70:
            return True, f"Strong negative sentiment ({sentiment['confidence']:.0f}% conf): {sentiment['top_headlines'][0] if sentiment['top_headlines'] else 'Multiple bearish articles'}"
        
        # Avoid trading during high news volatility (too many articles = uncertain)
        if sentiment['has_major_news'] and sentiment['article_count'] > 20:
            return True, f"Excessive news volume ({sentiment['article_count']} articles in 4h) - high uncertainty"
        
        return False, ""
    
    def get_sentiment_boost(self, symbol: str) -> float:
        """
        Get sentiment boost/penalty for position sizing.
        
        Returns:
            Multiplier from 0.5 (very negative) to 1.5 (very positive)
        """
        sentiment = self.get_news_sentiment(symbol, hours=24)
        
        if sentiment['article_count'] < 3:
            return 1.0  # Not enough data, neutral
        
        score = sentiment['sentiment_score']
        confidence = sentiment['confidence'] / 100
        
        # Scale sentiment impact by confidence
        boost = 1.0 + (score * 0.5 * confidence)
        
        # Clamp to reasonable range
        return max(0.5, min(1.5, boost))
    
    def get_news_summary(self, symbols: List[str]) -> Dict:
        """Get news summary for multiple symbols."""
        summary = {
            'timestamp': datetime.now(),
            'total_symbols': len(symbols),
            'bullish_symbols': [],
            'bearish_symbols': [],
            'high_news_volume': [],
            'top_stories': []
        }
        
        for symbol in symbols:
            sentiment = self.get_news_sentiment(symbol, hours=24)
            
            if sentiment['sentiment_label'] == 'BULLISH' and sentiment['confidence'] > 60:
                summary['bullish_symbols'].append({
                    'symbol': symbol,
                    'confidence': sentiment['confidence'],
                    'headline': sentiment['top_headlines'][0] if sentiment['top_headlines'] else None
                })
            
            if sentiment['sentiment_label'] == 'BEARISH' and sentiment['confidence'] > 60:
                summary['bearish_symbols'].append({
                    'symbol': symbol,
                    'confidence': sentiment['confidence'],
                    'headline': sentiment['top_headlines'][0] if sentiment['top_headlines'] else None
                })
            
            if sentiment['has_major_news']:
                summary['high_news_volume'].append(symbol)
            
            # Collect top stories
            for headline in sentiment['top_headlines'][:2]:
                summary['top_stories'].append({
                    'symbol': symbol,
                    'headline': headline,
                    'sentiment': sentiment['sentiment_label']
                })
        
        return summary
