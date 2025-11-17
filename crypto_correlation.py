"""
Crypto Correlation Tracker - Detect when crypto leads stocks
Monitor Bitcoin/Ethereum for early signals on risk appetite
Uses FREE CoinGecko API
"""

import os
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

class CryptoCorrelationTracker:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # CoinGecko API (free, no key required)
        self.base_url = "https://api.coingecko.com/api/v3"
        
        self.cache = {}
        self.cache_duration = 600  # 10 minutes
        
        # Key crypto to track
        self.crypto_ids = {
            'bitcoin': 'BTC',
            'ethereum': 'ETH'
        }
    
    def get_crypto_sentiment(self) -> Dict:
        """
        Analyze crypto market sentiment
        Crypto often leads stock market moves (risk-on/risk-off)
        """
        cache_key = "crypto_sentiment"
        now = datetime.now()
        
        # Check cache
        if cache_key in self.cache:
            cached_time, cached_data = self.cache[cache_key]
            if (now - cached_time).total_seconds() < self.cache_duration:
                return cached_data
        
        try:
            # Get Bitcoin and Ethereum data
            btc_data = self._get_crypto_data('bitcoin')
            eth_data = self._get_crypto_data('ethereum')
            
            # Analyze sentiment
            analysis = self._analyze_crypto_trends(btc_data, eth_data)
            
            # Cache result
            self.cache[cache_key] = (now, analysis)
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing crypto sentiment: {e}")
            return self._empty_response()
    
    def _get_crypto_data(self, crypto_id: str) -> Optional[Dict]:
        """Fetch crypto data from CoinGecko"""
        try:
            url = f"{self.base_url}/coins/{crypto_id}"
            params = {
                'localization': 'false',
                'tickers': 'false',
                'market_data': 'true',
                'community_data': 'false',
                'developer_data': 'false'
            }
            
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                return resp.json()
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error fetching {crypto_id}: {e}")
            return None
    
    def _analyze_crypto_trends(self, btc_data: Optional[Dict], 
                               eth_data: Optional[Dict]) -> Dict:
        """
        Analyze crypto trends for stock market correlation
        
        Theory: When crypto rallies, risk appetite is high (bullish for stocks)
                When crypto dumps, risk-off (bearish for stocks)
        """
        signal = "NEUTRAL"
        confidence = 0
        reasons = []
        
        if not btc_data:
            return self._empty_response()
        
        # Extract market data
        btc_market = btc_data.get('market_data', {})
        btc_price_change_24h = btc_market.get('price_change_percentage_24h', 0)
        btc_price_change_7d = btc_market.get('price_change_percentage_7d', 0)
        
        eth_market = eth_data.get('market_data', {}) if eth_data else {}
        eth_price_change_24h = eth_market.get('price_change_percentage_24h', 0)
        
        # Bitcoin trend
        if btc_price_change_24h > 5:
            signal = "RISK_ON"
            confidence += 30
            reasons.append(f"Bitcoin up {btc_price_change_24h:.1f}% (24h)")
        elif btc_price_change_24h > 2:
            signal = "RISK_ON"
            confidence += 15
            reasons.append(f"Bitcoin rising ({btc_price_change_24h:.1f}%)")
        elif btc_price_change_24h < -5:
            signal = "RISK_OFF"
            confidence += 30
            reasons.append(f"Bitcoin down {btc_price_change_24h:.1f}% (24h)")
        elif btc_price_change_24h < -2:
            signal = "RISK_OFF"
            confidence += 15
            reasons.append(f"Bitcoin falling ({btc_price_change_24h:.1f}%)")
        
        # 7-day trend
        if btc_price_change_7d > 10:
            confidence += 20
            reasons.append(f"Strong 7-day rally ({btc_price_change_7d:.1f}%)")
        elif btc_price_change_7d < -10:
            confidence += 20
            reasons.append(f"Weak 7-day trend ({btc_price_change_7d:.1f}%)")
        
        # Ethereum confirmation
        if eth_price_change_24h:
            if (btc_price_change_24h > 0 and eth_price_change_24h > 0) or \
               (btc_price_change_24h < 0 and eth_price_change_24h < 0):
                confidence += 15
                reasons.append("BTC/ETH moving together")
        
        # Determine action
        action = "NORMAL"
        if signal == "RISK_ON" and confidence > 60:
            action = "INCREASE_EXPOSURE"
        elif signal == "RISK_OFF" and confidence > 60:
            action = "REDUCE_EXPOSURE"
        
        return {
            'signal': signal,
            'confidence': min(100, int(confidence)),
            'action': action,
            'btc_change_24h': round(btc_price_change_24h, 2),
            'btc_change_7d': round(btc_price_change_7d, 2),
            'eth_change_24h': round(eth_price_change_24h, 2),
            'reasons': reasons,
            'timestamp': datetime.now().isoformat()
        }
    
    def _empty_response(self) -> Dict:
        """Return empty response when no data available"""
        return {
            'signal': 'NEUTRAL',
            'confidence': 0,
            'action': 'NORMAL',
            'btc_change_24h': 0,
            'btc_change_7d': 0,
            'eth_change_24h': 0,
            'reasons': ['No crypto data available'],
            'timestamp': datetime.now().isoformat()
        }
    
    def get_crypto_risk_factor(self) -> float:
        """
        Calculate position size multiplier based on crypto sentiment
        Returns: 0.7 to 1.2 multiplier
        """
        analysis = self.get_crypto_sentiment()
        
        if analysis['confidence'] < 50:
            return 1.0
        
        if analysis['signal'] == 'RISK_ON':
            # Crypto rallying = risk appetite high
            if analysis['confidence'] > 75:
                return 1.2
            elif analysis['confidence'] > 60:
                return 1.1
            else:
                return 1.05
        
        elif analysis['signal'] == 'RISK_OFF':
            # Crypto dumping = risk off
            if analysis['confidence'] > 75:
                return 0.7
            elif analysis['confidence'] > 60:
                return 0.85
            else:
                return 0.95
        
        return 1.0
    
    def is_crypto_leading_stocks(self) -> bool:
        """
        Check if crypto is showing strong directional move
        Can indicate incoming stock market move
        """
        analysis = self.get_crypto_sentiment()
        
        # Strong crypto move with high confidence
        if analysis['confidence'] > 70:
            return True
        
        return False


if __name__ == "__main__":
    # Test the tracker
    logging.basicConfig(level=logging.INFO)
    tracker = CryptoCorrelationTracker()
    
    print("Crypto Sentiment Analysis:")
    result = tracker.get_crypto_sentiment()
    print(json.dumps(result, indent=2))
