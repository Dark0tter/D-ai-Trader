"""
Short Interest Tracker - Monitor short squeeze potential
Detect stocks with high short interest that could squeeze
Uses Alpaca API and public data sources
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

try:
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False

class ShortInterestTracker:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Alpaca API for basic data
        self.api_key = os.environ.get('ALPACA_API_KEY', '')
        self.api_secret = os.environ.get('ALPACA_SECRET_KEY', '')
        
        self.client = None
        if ALPACA_AVAILABLE and self.api_key and self.api_secret:
            try:
                self.client = StockHistoricalDataClient(self.api_key, self.api_secret)
            except Exception as e:
                self.logger.warning(f"Alpaca client not available: {e}")
        
        self.cache = {}
        self.cache_duration = 3600  # 1 hour
        
        # Known high short interest stocks (manually tracked for now)
        # In production, would use Fintel/Ortex/S3 Partners API
        self.known_high_short = {
            'GME': {'short_float': 15.0, 'days_to_cover': 2.5},
            'AMC': {'short_float': 18.0, 'days_to_cover': 1.8},
            'BBBY': {'short_float': 45.0, 'days_to_cover': 8.0},
        }
    
    def get_short_interest_analysis(self, symbol: str) -> Dict:
        """
        Analyze short interest and squeeze potential
        Note: Real short interest data requires paid APIs (Fintel, Ortex, S3)
        This uses proxy indicators
        """
        cache_key = f"short_{symbol}"
        now = datetime.now()
        
        # Check cache
        if cache_key in self.cache:
            cached_time, cached_data = self.cache[cache_key]
            if (now - cached_time).total_seconds() < self.cache_duration:
                return cached_data
        
        try:
            # Check if we have data for this symbol
            short_data = self.known_high_short.get(symbol, {})
            
            # Get recent price action (squeeze indicator)
            price_action = self._analyze_price_action(symbol)
            
            # Combine analysis
            analysis = self._calculate_squeeze_potential(symbol, short_data, price_action)
            
            # Cache result
            self.cache[cache_key] = (now, analysis)
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing short interest for {symbol}: {e}")
            return self._empty_response()
    
    def _analyze_price_action(self, symbol: str) -> Dict:
        """
        Analyze recent price action for squeeze indicators:
        - Rapid price increase
        - High volume
        - Consecutive green days
        """
        if not self.client:
            return {'squeeze_signs': False, 'volume_spike': False}
        
        try:
            # Get last 10 days of data
            end = datetime.now()
            start = end - timedelta(days=10)
            
            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Day,
                start=start,
                end=end
            )
            
            bars = self.client.get_stock_bars(request)
            if symbol not in bars.data:
                return {'squeeze_signs': False, 'volume_spike': False}
            
            data = bars.data[symbol]
            if len(data) < 5:
                return {'squeeze_signs': False, 'volume_spike': False}
            
            # Calculate indicators
            recent_bars = data[-5:]
            older_bars = data[-10:-5] if len(data) >= 10 else data[:5]
            
            # Check for consecutive gains
            consecutive_gains = sum(1 for bar in recent_bars if bar.close > bar.open)
            
            # Check for volume spike
            recent_avg_vol = sum(bar.volume for bar in recent_bars) / len(recent_bars)
            older_avg_vol = sum(bar.volume for bar in older_bars) / len(older_bars)
            volume_ratio = recent_avg_vol / older_avg_vol if older_avg_vol > 0 else 1
            
            # Check for price momentum
            price_change = ((recent_bars[-1].close - recent_bars[0].open) / 
                           recent_bars[0].open * 100)
            
            return {
                'squeeze_signs': consecutive_gains >= 3 and price_change > 10,
                'volume_spike': volume_ratio > 2,
                'consecutive_gains': consecutive_gains,
                'volume_ratio': volume_ratio,
                'price_change_5d': price_change
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing price action: {e}")
            return {'squeeze_signs': False, 'volume_spike': False}
    
    def _calculate_squeeze_potential(self, symbol: str, short_data: Dict, 
                                     price_action: Dict) -> Dict:
        """
        Calculate short squeeze potential
        """
        signal = "NEUTRAL"
        confidence = 0
        reasons = []
        
        short_float = short_data.get('short_float', 0)
        days_to_cover = short_data.get('days_to_cover', 0)
        
        # High short interest
        if short_float > 20:
            signal = "SQUEEZE_POTENTIAL"
            confidence += 40
            reasons.append(f"Very high short interest ({short_float}%)")
        elif short_float > 10:
            signal = "SQUEEZE_POTENTIAL"
            confidence += 25
            reasons.append(f"High short interest ({short_float}%)")
        
        # Days to cover (higher = harder to cover)
        if days_to_cover > 5:
            confidence += 30
            reasons.append(f"High days to cover ({days_to_cover})")
        elif days_to_cover > 3:
            confidence += 15
            reasons.append(f"Moderate days to cover ({days_to_cover})")
        
        # Price action squeeze signs
        if price_action.get('squeeze_signs'):
            confidence += 20
            reasons.append("Active squeeze indicators detected")
            signal = "ACTIVE_SQUEEZE"
        
        if price_action.get('volume_spike'):
            confidence += 10
            reasons.append(f"Volume spike ({price_action.get('volume_ratio', 0):.1f}x)")
        
        # No short interest data
        if short_float == 0:
            return self._empty_response()
        
        # Determine action
        action = "HOLD"
        if signal == "ACTIVE_SQUEEZE" and confidence > 70:
            action = "BUY"  # Ride the squeeze
        elif signal == "SQUEEZE_POTENTIAL" and confidence > 60:
            action = "WATCH"  # Monitor for squeeze trigger
        
        return {
            'signal': signal,
            'confidence': min(100, int(confidence)),
            'action': action,
            'short_float': short_float,
            'days_to_cover': days_to_cover,
            'squeeze_active': price_action.get('squeeze_signs', False),
            'volume_spike': price_action.get('volume_spike', False),
            'price_change_5d': price_action.get('price_change_5d', 0),
            'reasons': reasons,
            'timestamp': datetime.now().isoformat()
        }
    
    def _empty_response(self) -> Dict:
        """Return empty response when no data available"""
        return {
            'signal': 'NEUTRAL',
            'confidence': 0,
            'action': 'HOLD',
            'short_float': 0,
            'days_to_cover': 0,
            'squeeze_active': False,
            'volume_spike': False,
            'price_change_5d': 0,
            'reasons': ['No short interest data available'],
            'timestamp': datetime.now().isoformat()
        }
    
    def is_squeeze_candidate(self, symbol: str) -> Tuple[bool, str]:
        """
        Check if stock is a squeeze candidate
        Returns: (is_candidate, reason)
        """
        analysis = self.get_short_interest_analysis(symbol)
        
        # Active squeeze
        if analysis['signal'] == 'ACTIVE_SQUEEZE' and analysis['confidence'] > 70:
            return True, f"Active short squeeze ({analysis['short_float']}% short)"
        
        # Squeeze potential
        if analysis['signal'] == 'SQUEEZE_POTENTIAL' and analysis['confidence'] > 60:
            return True, f"Squeeze potential ({analysis['short_float']}% short, {analysis['days_to_cover']} DTC)"
        
        return False, "No squeeze potential"
    
    def get_squeeze_boost(self, symbol: str) -> float:
        """
        Calculate position size multiplier for squeeze plays
        Returns: 1.0 to 2.0 multiplier
        Short squeezes can be very volatile - use carefully
        """
        analysis = self.get_short_interest_analysis(symbol)
        
        if analysis['confidence'] < 50:
            return 1.0
        
        # Active squeeze = big opportunity (but risky)
        if analysis['signal'] == 'ACTIVE_SQUEEZE':
            if analysis['confidence'] > 80:
                return 2.0  # Maximum boost for confirmed squeeze
            elif analysis['confidence'] > 70:
                return 1.7
            else:
                return 1.4
        
        # Squeeze potential = moderate boost
        elif analysis['signal'] == 'SQUEEZE_POTENTIAL':
            if analysis['confidence'] > 70:
                return 1.3
            else:
                return 1.1
        
        return 1.0
    
    def get_summary(self, symbols: List[str]) -> Dict:
        """Get short squeeze summary for multiple symbols"""
        summary = {
            'active_squeezes': [],
            'squeeze_candidates': [],
            'high_short_interest': [],
            'timestamp': datetime.now().isoformat()
        }
        
        for symbol in symbols:
            analysis = self.get_short_interest_analysis(symbol)
            
            if analysis['signal'] == 'ACTIVE_SQUEEZE':
                summary['active_squeezes'].append({
                    'symbol': symbol,
                    'confidence': analysis['confidence'],
                    'short_float': analysis['short_float'],
                    'price_change_5d': analysis['price_change_5d']
                })
            
            elif analysis['signal'] == 'SQUEEZE_POTENTIAL' and analysis['confidence'] > 60:
                summary['squeeze_candidates'].append({
                    'symbol': symbol,
                    'confidence': analysis['confidence'],
                    'short_float': analysis['short_float'],
                    'days_to_cover': analysis['days_to_cover']
                })
            
            if analysis['short_float'] > 15:
                summary['high_short_interest'].append({
                    'symbol': symbol,
                    'short_float': analysis['short_float']
                })
        
        return summary


if __name__ == "__main__":
    # Test the tracker
    logging.basicConfig(level=logging.INFO)
    tracker = ShortInterestTracker()
    
    test_symbols = ['GME', 'AMC', 'AAPL']
    for symbol in test_symbols:
        print(f"\n{symbol} Short Interest Analysis:")
        result = tracker.get_short_interest_analysis(symbol)
        print(json.dumps(result, indent=2))
