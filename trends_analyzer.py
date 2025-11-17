"""
Google Trends Analyzer - Detect retail interest surges
Track when retail investors are searching for stocks
Uses pytrends library (unofficial Google Trends API)
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

try:
    from pytrends.request import TrendReq
    PYTRENDS_AVAILABLE = True
except ImportError:
    PYTRENDS_AVAILABLE = False

class GoogleTrendsAnalyzer:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        self.pytrends = None
        if PYTRENDS_AVAILABLE:
            try:
                self.pytrends = TrendReq(hl='en-US', tz=360)
            except Exception as e:
                self.logger.warning(f"Google Trends not available: {e}")
        
        self.cache = {}
        self.cache_duration = 1800  # 30 minutes
    
    def get_search_interest(self, symbol: str) -> Dict:
        """
        Analyze Google search interest for a stock
        Rising searches often precede price moves (retail FOMO)
        """
        cache_key = f"trends_{symbol}"
        now = datetime.now()
        
        # Check cache
        if cache_key in self.cache:
            cached_time, cached_data = self.cache[cache_key]
            if (now - cached_time).total_seconds() < self.cache_duration:
                return cached_data
        
        try:
            if not self.pytrends:
                return self._empty_response()
            
            # Build search query
            keywords = [f"{symbol} stock", symbol]
            
            # Get interest over time (last 7 days)
            self.pytrends.build_payload(keywords, timeframe='now 7-d', geo='US')
            interest_df = self.pytrends.interest_over_time()
            
            # Analyze trend
            analysis = self._analyze_search_trend(symbol, interest_df)
            
            # Cache result
            self.cache[cache_key] = (now, analysis)
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing trends for {symbol}: {e}")
            return self._empty_response()
    
    def _analyze_search_trend(self, symbol: str, interest_df) -> Dict:
        """Analyze search interest trends"""
        if interest_df is None or interest_df.empty:
            return self._empty_response()
        
        # Get the main keyword column
        keyword_col = f"{symbol} stock"
        if keyword_col not in interest_df.columns:
            keyword_col = symbol
        
        if keyword_col not in interest_df.columns:
            return self._empty_response()
        
        # Calculate metrics
        data = interest_df[keyword_col]
        current_interest = data.iloc[-1]
        avg_interest = data.mean()
        max_interest = data.max()
        
        # Calculate trend direction
        recent_3d = data.tail(3).mean()
        older_3d = data.head(3).mean()
        
        percent_change = ((recent_3d - older_3d) / older_3d * 100) if older_3d > 0 else 0
        
        # Determine signal
        signal = "NEUTRAL"
        confidence = 0
        reasons = []
        
        # Spike in interest
        if current_interest > avg_interest * 2:
            signal = "SURGING"
            confidence += 40
            reasons.append(f"Search interest spike ({int(current_interest)}% of peak)")
        elif current_interest > avg_interest * 1.5:
            signal = "RISING"
            confidence += 25
            reasons.append(f"Rising search interest ({int(current_interest)}%)")
        
        # Trend direction
        if percent_change > 50:
            if signal == "NEUTRAL":
                signal = "RISING"
            confidence += 30
            reasons.append(f"Search trend up {percent_change:.0f}%")
        elif percent_change > 20:
            confidence += 15
            reasons.append(f"Positive trend ({percent_change:.0f}%)")
        elif percent_change < -30:
            signal = "FALLING"
            confidence += 20
            reasons.append(f"Search interest falling ({percent_change:.0f}%)")
        
        # High absolute interest
        if current_interest > 75:
            confidence += 15
            reasons.append("Very high absolute interest")
        
        # Determine action
        action = "HOLD"
        if signal == "SURGING" and confidence > 65:
            action = "BUY"  # Retail FOMO incoming
        elif signal == "RISING" and confidence > 60:
            action = "WATCH"
        elif signal == "FALLING":
            action = "AVOID"  # Interest fading
        
        return {
            'signal': signal,
            'confidence': min(100, int(confidence)),
            'action': action,
            'current_interest': int(current_interest),
            'average_interest': int(avg_interest),
            'percent_change': round(percent_change, 1),
            'reasons': reasons,
            'timestamp': datetime.now().isoformat()
        }
    
    def _empty_response(self) -> Dict:
        """Return empty response when no data available"""
        return {
            'signal': 'NEUTRAL',
            'confidence': 0,
            'action': 'HOLD',
            'current_interest': 0,
            'average_interest': 0,
            'percent_change': 0,
            'reasons': ['Google Trends data not available'],
            'timestamp': datetime.now().isoformat()
        }
    
    def is_retail_fomo(self, symbol: str) -> bool:
        """
        Check if retail FOMO is building
        Returns: True if search interest spiking
        """
        analysis = self.get_search_interest(symbol)
        
        # Surging search interest = retail FOMO
        if analysis['signal'] == 'SURGING' and analysis['confidence'] > 60:
            return True
        
        return False
    
    def get_trends_boost(self, symbol: str) -> float:
        """
        Calculate position size multiplier based on search trends
        Returns: 0.8 to 1.4 multiplier
        """
        analysis = self.get_search_interest(symbol)
        
        if analysis['confidence'] < 50:
            return 1.0
        
        if analysis['signal'] == 'SURGING':
            # Retail FOMO can drive short-term pumps
            if analysis['confidence'] > 75:
                return 1.4
            elif analysis['confidence'] > 65:
                return 1.2
            else:
                return 1.1
        
        elif analysis['signal'] == 'RISING':
            return 1.05
        
        elif analysis['signal'] == 'FALLING':
            # Interest fading = avoid
            return 0.8
        
        return 1.0
    
    def get_summary(self, symbols: List[str]) -> Dict:
        """Get search trends summary for multiple symbols"""
        summary = {
            'surging_interest': [],
            'rising_interest': [],
            'falling_interest': [],
            'timestamp': datetime.now().isoformat()
        }
        
        for symbol in symbols:
            analysis = self.get_search_interest(symbol)
            
            if analysis['signal'] == 'SURGING':
                summary['surging_interest'].append({
                    'symbol': symbol,
                    'confidence': analysis['confidence'],
                    'interest': analysis['current_interest']
                })
            
            elif analysis['signal'] == 'RISING' and analysis['confidence'] > 60:
                summary['rising_interest'].append({
                    'symbol': symbol,
                    'interest': analysis['current_interest']
                })
            
            elif analysis['signal'] == 'FALLING':
                summary['falling_interest'].append({
                    'symbol': symbol
                })
        
        return summary


if __name__ == "__main__":
    # Test the analyzer
    logging.basicConfig(level=logging.INFO)
    analyzer = GoogleTrendsAnalyzer()
    
    test_symbols = ['TSLA', 'NVDA', 'AAPL']
    for symbol in test_symbols:
        print(f"\n{symbol} Search Trends:")
        result = analyzer.get_search_interest(symbol)
        print(json.dumps(result, indent=2))
