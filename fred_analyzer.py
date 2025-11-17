"""
FRED Economic Data Analyzer - Monitor macro trends
Track interest rates, unemployment, GDP for market regime detection
Uses FREE Federal Reserve Economic Data API
"""

import os
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

class FREDAnalyzer:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # FRED API key (free from https://fred.stlouisfed.org/docs/api/api_key.html)
        self.api_key = os.environ.get('FRED_API_KEY', '')
        self.base_url = "https://api.stlouisfed.org/fred/series/observations"
        
        self.cache = {}
        self.cache_duration = 86400  # 24 hours (economic data updates slowly)
        
        # Key economic indicators
        self.indicators = {
            'DFF': 'Federal Funds Rate',
            'UNRATE': 'Unemployment Rate',
            'CPIAUCSL': 'CPI Inflation',
            'GDP': 'GDP',
            'T10Y2Y': '10Y-2Y Treasury Spread',
            'VIXCLS': 'VIX Fear Index',
            'DEXUSEU': 'Dollar Index'
        }
    
    def get_economic_regime(self) -> Dict:
        """
        Analyze current economic regime
        Returns: Bull/Bear market indicators
        """
        cache_key = "economic_regime"
        now = datetime.now()
        
        # Check cache
        if cache_key in self.cache:
            cached_time, cached_data = self.cache[cache_key]
            if (now - cached_time).total_seconds() < self.cache_duration:
                return cached_data
        
        try:
            if not self.api_key:
                return self._default_regime()
            
            # Fetch key indicators
            fed_funds = self._get_latest_value('DFF')
            unemployment = self._get_latest_value('UNRATE')
            treasury_spread = self._get_latest_value('T10Y2Y')
            vix = self._get_latest_value('VIXCLS')
            
            # Analyze regime
            analysis = self._analyze_regime(fed_funds, unemployment, treasury_spread, vix)
            
            # Cache result
            self.cache[cache_key] = (now, analysis)
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing economic regime: {e}")
            return self._default_regime()
    
    def _get_latest_value(self, series_id: str) -> Optional[float]:
        """Fetch latest value for a FRED series"""
        try:
            params = {
                'series_id': series_id,
                'api_key': self.api_key,
                'file_type': 'json',
                'sort_order': 'desc',
                'limit': 1
            }
            
            resp = requests.get(self.base_url, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                observations = data.get('observations', [])
                if observations and observations[0]['value'] != '.':
                    return float(observations[0]['value'])
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error fetching {series_id}: {e}")
            return None
    
    def _analyze_regime(self, fed_funds: Optional[float], unemployment: Optional[float],
                       treasury_spread: Optional[float], vix: Optional[float]) -> Dict:
        """
        Determine market regime based on economic indicators
        """
        regime = "NEUTRAL"
        confidence = 0
        reasons = []
        
        # Fed Funds Rate (higher = tighter policy = bearish)
        if fed_funds is not None:
            if fed_funds > 4.5:
                regime = "BEARISH"
                confidence += 25
                reasons.append(f"High interest rates ({fed_funds}%)")
            elif fed_funds < 2.0:
                regime = "BULLISH"
                confidence += 20
                reasons.append(f"Low interest rates ({fed_funds}%)")
        
        # Unemployment (rising = bearish, falling = bullish)
        if unemployment is not None:
            if unemployment < 4.0:
                if regime != "BEARISH":
                    regime = "BULLISH"
                confidence += 15
                reasons.append(f"Low unemployment ({unemployment}%)")
            elif unemployment > 6.0:
                regime = "BEARISH"
                confidence += 20
                reasons.append(f"High unemployment ({unemployment}%)")
        
        # Treasury Spread (inverted = recession warning)
        if treasury_spread is not None:
            if treasury_spread < 0:
                regime = "BEARISH"
                confidence += 30
                reasons.append(f"Inverted yield curve ({treasury_spread}%)")
            elif treasury_spread > 1.0:
                if regime != "BEARISH":
                    regime = "BULLISH"
                confidence += 10
                reasons.append("Healthy yield curve")
        
        # VIX (high = fear = bearish)
        if vix is not None:
            if vix > 25:
                regime = "BEARISH"
                confidence += 20
                reasons.append(f"High volatility/fear (VIX {vix})")
            elif vix < 15:
                if regime != "BEARISH":
                    regime = "BULLISH"
                confidence += 15
                reasons.append(f"Low volatility (VIX {vix})")
        
        # Determine action
        action = "NORMAL_TRADING"
        if regime == "BEARISH" and confidence > 70:
            action = "REDUCE_RISK"
        elif regime == "BULLISH" and confidence > 70:
            action = "INCREASE_RISK"
        
        return {
            'regime': regime,
            'confidence': min(100, int(confidence)),
            'action': action,
            'fed_funds_rate': fed_funds,
            'unemployment': unemployment,
            'treasury_spread': treasury_spread,
            'vix': vix,
            'reasons': reasons,
            'timestamp': datetime.now().isoformat()
        }
    
    def _default_regime(self) -> Dict:
        """Return default regime when API not available"""
        return {
            'regime': 'NEUTRAL',
            'confidence': 0,
            'action': 'NORMAL_TRADING',
            'fed_funds_rate': None,
            'unemployment': None,
            'treasury_spread': None,
            'vix': None,
            'reasons': ['FRED API not configured'],
            'timestamp': datetime.now().isoformat()
        }
    
    def get_macro_risk_factor(self) -> float:
        """
        Calculate position size multiplier based on macro environment
        Returns: 0.6 to 1.3 multiplier
        """
        analysis = self.get_economic_regime()
        
        if analysis['confidence'] < 50:
            return 1.0
        
        if analysis['regime'] == 'BULLISH':
            # Good macro = slightly larger positions
            if analysis['confidence'] > 80:
                return 1.3
            elif analysis['confidence'] > 70:
                return 1.15
            else:
                return 1.05
        
        elif analysis['regime'] == 'BEARISH':
            # Bad macro = reduce risk
            if analysis['confidence'] > 80:
                return 0.6  # Major risk reduction
            elif analysis['confidence'] > 70:
                return 0.75
            else:
                return 0.9
        
        return 1.0
    
    def is_recession_likely(self) -> bool:
        """Check for recession indicators"""
        analysis = self.get_economic_regime()
        
        # Inverted yield curve + high unemployment = recession
        if (analysis.get('treasury_spread') and analysis['treasury_spread'] < 0 and
            analysis.get('unemployment') and analysis['unemployment'] > 5.0):
            return True
        
        return False


if __name__ == "__main__":
    # Test the analyzer
    logging.basicConfig(level=logging.INFO)
    analyzer = FREDAnalyzer()
    
    print("Economic Regime Analysis:")
    result = analyzer.get_economic_regime()
    print(json.dumps(result, indent=2))
