"""
Options Flow Analyzer - Detect unusual options activity
Tracks large options trades that often predict stock movements 1-2 days ahead
Uses free Tradier API data
"""

import os
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

class OptionsFlowAnalyzer:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # Tradier sandbox API (free tier)
        self.api_key = os.environ.get('TRADIER_API_KEY', 'sandbox')
        self.base_url = "https://sandbox.tradier.com/v1"
        self.cache = {}
        self.cache_duration = 1800  # 30 minutes
        
    def get_unusual_options_activity(self, symbol: str) -> Dict:
        """
        Detect unusual options activity for a symbol
        Returns signals based on large option trades
        """
        cache_key = f"options_{symbol}"
        now = datetime.now()
        
        # Check cache
        if cache_key in self.cache:
            cached_time, cached_data = self.cache[cache_key]
            if (now - cached_time).total_seconds() < self.cache_duration:
                return cached_data
        
        try:
            # Get options chain
            chain_data = self._get_options_chain(symbol)
            if not chain_data:
                return self._empty_response()
            
            # Analyze unusual activity
            analysis = self._analyze_options_flow(symbol, chain_data)
            
            # Cache result
            self.cache[cache_key] = (now, analysis)
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing options for {symbol}: {e}")
            return self._empty_response()
    
    def _get_options_chain(self, symbol: str) -> Optional[Dict]:
        """Fetch options chain from Tradier API"""
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Accept': 'application/json'
            }
            
            # Get expiration dates
            exp_url = f"{self.base_url}/markets/options/expirations"
            params = {'symbol': symbol}
            resp = requests.get(exp_url, headers=headers, params=params, timeout=10)
            
            if resp.status_code != 200:
                return None
            
            expirations = resp.json().get('expirations', {}).get('date', [])
            if not expirations:
                return None
            
            # Get nearest expiration chain
            nearest_exp = expirations[0]
            chain_url = f"{self.base_url}/markets/options/chains"
            params = {'symbol': symbol, 'expiration': nearest_exp}
            resp = requests.get(chain_url, headers=headers, params=params, timeout=10)
            
            if resp.status_code == 200:
                return resp.json()
            return None
            
        except Exception as e:
            self.logger.error(f"Error fetching options chain: {e}")
            return None
    
    def _analyze_options_flow(self, symbol: str, chain_data: Dict) -> Dict:
        """
        Analyze options flow for unusual activity
        Looks for:
        - Heavy call buying (bullish)
        - Heavy put buying (bearish)
        - Unusual volume vs open interest
        - Large bid/ask imbalances
        """
        options = chain_data.get('options', {}).get('option', [])
        if not options:
            return self._empty_response()
        
        # Separate calls and puts
        calls = [opt for opt in options if opt.get('option_type') == 'call']
        puts = [opt for opt in options if opt.get('option_type') == 'put']
        
        # Calculate total volume and open interest
        call_volume = sum(opt.get('volume', 0) for opt in calls)
        put_volume = sum(opt.get('volume', 0) for opt in puts)
        call_oi = sum(opt.get('open_interest', 0) for opt in calls)
        put_oi = sum(opt.get('open_interest', 0) for opt in puts)
        
        # Calculate put/call ratio
        total_volume = call_volume + put_volume
        if total_volume == 0:
            return self._empty_response()
        
        put_call_ratio = put_volume / call_volume if call_volume > 0 else 999
        
        # Detect unusual activity
        signal = "NEUTRAL"
        confidence = 0
        reason = []
        
        # Heavy call buying (bullish)
        if call_volume > put_volume * 2:
            signal = "BULLISH"
            confidence = min(85, 50 + (call_volume / put_volume) * 5)
            reason.append(f"Heavy call buying (C/P ratio: {call_volume/put_volume:.2f})")
        
        # Heavy put buying (bearish)
        elif put_volume > call_volume * 2:
            signal = "BEARISH"
            confidence = min(85, 50 + (put_volume / call_volume) * 5)
            reason.append(f"Heavy put buying (P/C ratio: {put_call_ratio:.2f})")
        
        # Volume spike detection
        if call_oi > 0:
            call_vol_ratio = call_volume / call_oi
            if call_vol_ratio > 2:  # Volume > 2x open interest
                if signal == "NEUTRAL":
                    signal = "BULLISH"
                    confidence = 60
                else:
                    confidence += 10
                reason.append(f"Call volume spike (Vol/OI: {call_vol_ratio:.2f})")
        
        if put_oi > 0:
            put_vol_ratio = put_volume / put_oi
            if put_vol_ratio > 2:
                if signal == "NEUTRAL":
                    signal = "BEARISH"
                    confidence = 60
                else:
                    confidence += 10
                reason.append(f"Put volume spike (Vol/OI: {put_vol_ratio:.2f})")
        
        # Find largest single trades (whale activity)
        largest_calls = sorted([opt for opt in calls if opt.get('volume', 0) > 0],
                              key=lambda x: x.get('volume', 0), reverse=True)[:3]
        largest_puts = sorted([opt for opt in puts if opt.get('volume', 0) > 0],
                             key=lambda x: x.get('volume', 0), reverse=True)[:3]
        
        whale_trades = []
        for opt in largest_calls:
            if opt.get('volume', 0) > 100:  # Significant volume
                whale_trades.append({
                    'type': 'CALL',
                    'strike': opt.get('strike'),
                    'volume': opt.get('volume'),
                    'premium': opt.get('last', 0)
                })
        
        for opt in largest_puts:
            if opt.get('volume', 0) > 100:
                whale_trades.append({
                    'type': 'PUT',
                    'strike': opt.get('strike'),
                    'volume': opt.get('volume'),
                    'premium': opt.get('last', 0)
                })
        
        # Calculate recommended action
        action = "HOLD"
        if signal == "BULLISH" and confidence > 70:
            action = "BUY"
        elif signal == "BEARISH" and confidence > 70:
            action = "SELL"
        
        return {
            'signal': signal,
            'confidence': min(100, int(confidence)),
            'action': action,
            'put_call_ratio': round(put_call_ratio, 2),
            'call_volume': call_volume,
            'put_volume': put_volume,
            'total_volume': total_volume,
            'reasons': reason,
            'whale_trades': whale_trades[:5],  # Top 5 largest trades
            'timestamp': datetime.now().isoformat()
        }
    
    def _empty_response(self) -> Dict:
        """Return empty response when no data available"""
        return {
            'signal': 'NEUTRAL',
            'confidence': 0,
            'action': 'HOLD',
            'put_call_ratio': 0,
            'call_volume': 0,
            'put_volume': 0,
            'total_volume': 0,
            'reasons': ['No options data available'],
            'whale_trades': [],
            'timestamp': datetime.now().isoformat()
        }
    
    def should_trade_on_options(self, symbol: str) -> Tuple[bool, str]:
        """
        Determine if options flow supports trading
        Returns: (should_trade, reason)
        """
        analysis = self.get_unusual_options_activity(symbol)
        
        # High confidence bullish signal
        if analysis['signal'] == 'BULLISH' and analysis['confidence'] > 75:
            return True, f"Strong bullish options flow ({analysis['confidence']}% conf)"
        
        # High confidence bearish signal - avoid buying
        if analysis['signal'] == 'BEARISH' and analysis['confidence'] > 75:
            return False, f"Strong bearish options flow ({analysis['confidence']}% conf)"
        
        # Neutral or low confidence
        return True, "Options flow neutral"
    
    def get_options_boost(self, symbol: str) -> float:
        """
        Calculate position size multiplier based on options flow
        Returns: 0.5 to 2.0 multiplier
        """
        analysis = self.get_unusual_options_activity(symbol)
        
        if analysis['confidence'] < 50:
            return 1.0  # No adjustment
        
        if analysis['signal'] == 'BULLISH':
            # Strong bullish flow = increase position
            if analysis['confidence'] > 80:
                return 1.5
            elif analysis['confidence'] > 70:
                return 1.3
            else:
                return 1.1
        
        elif analysis['signal'] == 'BEARISH':
            # Bearish flow = reduce position
            if analysis['confidence'] > 80:
                return 0.5
            elif analysis['confidence'] > 70:
                return 0.7
            else:
                return 0.9
        
        return 1.0
    
    def get_summary(self, symbols: List[str]) -> Dict:
        """Get options flow summary for multiple symbols"""
        summary = {
            'bullish_signals': [],
            'bearish_signals': [],
            'whale_activity': [],
            'timestamp': datetime.now().isoformat()
        }
        
        for symbol in symbols:
            analysis = self.get_unusual_options_activity(symbol)
            
            if analysis['signal'] == 'BULLISH' and analysis['confidence'] > 65:
                summary['bullish_signals'].append({
                    'symbol': symbol,
                    'confidence': analysis['confidence'],
                    'reasons': analysis['reasons']
                })
            
            if analysis['signal'] == 'BEARISH' and analysis['confidence'] > 65:
                summary['bearish_signals'].append({
                    'symbol': symbol,
                    'confidence': analysis['confidence'],
                    'reasons': analysis['reasons']
                })
            
            if analysis['whale_trades']:
                summary['whale_activity'].append({
                    'symbol': symbol,
                    'trades': analysis['whale_trades']
                })
        
        return summary


if __name__ == "__main__":
    # Test the analyzer
    logging.basicConfig(level=logging.INFO)
    analyzer = OptionsFlowAnalyzer()
    
    test_symbols = ['AAPL', 'TSLA', 'SPY']
    for symbol in test_symbols:
        print(f"\n{symbol} Options Flow Analysis:")
        result = analyzer.get_unusual_options_activity(symbol)
        print(json.dumps(result, indent=2))
