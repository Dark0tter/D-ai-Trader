"""
Economic Calendar - Track major economic events
Avoid trading during FOMC, CPI, earnings to reduce risk
Uses free economic calendar APIs
"""

import os
import json
import requests
from datetime import datetime, timedelta, time
from typing import Dict, List, Optional, Tuple
import logging

class EconomicCalendar:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Trading Economics API (has free tier)
        self.te_api_key = os.environ.get('TRADING_ECONOMICS_API_KEY', '')
        self.te_base_url = "https://api.tradingeconomics.com"
        
        self.cache = {}
        self.cache_duration = 3600  # 1 hour
        
        # Major events to track (even without API)
        self.major_events = [
            'FOMC Meeting',
            'FOMC Decision',
            'CPI',
            'Non-Farm Payrolls',
            'NFP',
            'Unemployment',
            'GDP',
            'PCE',
            'Fed Speech',
            'Powell Speech'
        ]
    
    def get_todays_events(self) -> Dict:
        """Get today's major economic events"""
        cache_key = f"events_{datetime.now().date()}"
        now = datetime.now()
        
        # Check cache
        if cache_key in self.cache:
            cached_time, cached_data = self.cache[cache_key]
            if (now - cached_time).total_seconds() < self.cache_duration:
                return cached_data
        
        try:
            # Try API first
            if self.te_api_key:
                events = self._fetch_from_api()
            else:
                # Fallback to hardcoded known events
                events = self._get_known_events()
            
            analysis = self._analyze_events(events)
            
            # Cache result
            self.cache[cache_key] = (now, analysis)
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error fetching economic events: {e}")
            return self._empty_response()
    
    def _fetch_from_api(self) -> List[Dict]:
        """Fetch events from Trading Economics API"""
        try:
            url = f"{self.te_base_url}/calendar/country/united states"
            params = {
                'c': self.te_api_key,
                'format': 'json'
            }
            
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                return resp.json()
            return []
            
        except Exception as e:
            self.logger.error(f"Error fetching from API: {e}")
            return []
    
    def _get_known_events(self) -> List[Dict]:
        """
        Hardcoded major economic events
        In production, these would be updated from a calendar feed
        """
        # This is simplified - in production would track actual dates
        today = datetime.now().date()
        
        # Example: FOMC meetings are typically 8 times per year
        # CPI is first week of each month, NFP is first Friday
        
        events = []
        
        # Check if today is first Friday (NFP day)
        if today.weekday() == 4 and 1 <= today.day <= 7:
            events.append({
                'event': 'Non-Farm Payrolls',
                'importance': 'High',
                'time': '08:30',
                'country': 'United States'
            })
        
        # Check if today is ~10th-13th (CPI week)
        if 10 <= today.day <= 13:
            events.append({
                'event': 'CPI Report',
                'importance': 'High',
                'time': '08:30',
                'country': 'United States'
            })
        
        return events
    
    def _analyze_events(self, events: List[Dict]) -> Dict:
        """Analyze events for trading impact"""
        major_events = []
        avoid_trading = False
        risk_level = "LOW"
        
        for event in events:
            event_name = event.get('event', event.get('Event', ''))
            importance = event.get('importance', event.get('Importance', 'Low'))
            
            # Check if major event
            is_major = any(term.lower() in event_name.lower() 
                          for term in self.major_events)
            
            if is_major or importance == 'High':
                major_events.append({
                    'name': event_name,
                    'time': event.get('time', event.get('Time', 'Unknown')),
                    'importance': importance
                })
        
        # Determine risk level
        if len(major_events) >= 3:
            risk_level = "EXTREME"
            avoid_trading = True
        elif len(major_events) >= 2:
            risk_level = "HIGH"
            avoid_trading = True
        elif len(major_events) >= 1:
            # Check if event is very soon
            risk_level = "MEDIUM"
            avoid_trading = self._is_event_soon(major_events[0])
        
        return {
            'has_major_events': len(major_events) > 0,
            'event_count': len(major_events),
            'major_events': major_events,
            'avoid_trading': avoid_trading,
            'risk_level': risk_level,
            'reasons': [f"{len(major_events)} major event(s) today"] if major_events else [],
            'timestamp': datetime.now().isoformat()
        }
    
    def _is_event_soon(self, event: Dict) -> bool:
        """Check if event is within next 2 hours"""
        try:
            event_time_str = event.get('time', '')
            if not event_time_str or event_time_str == 'Unknown':
                return True  # Assume risk if time unknown
            
            # Parse time (format: HH:MM)
            event_time = datetime.strptime(event_time_str, '%H:%M').time()
            now_time = datetime.now().time()
            
            # Check if within 2 hours
            event_dt = datetime.combine(datetime.now().date(), event_time)
            now_dt = datetime.now()
            
            time_diff = (event_dt - now_dt).total_seconds() / 3600
            
            return -0.5 <= time_diff <= 2  # 30 min before to 2 hours after
            
        except Exception:
            return True  # Assume risk if can't parse
    
    def _empty_response(self) -> Dict:
        """Return empty response when no data available"""
        return {
            'has_major_events': False,
            'event_count': 0,
            'major_events': [],
            'avoid_trading': False,
            'risk_level': 'LOW',
            'reasons': [],
            'timestamp': datetime.now().isoformat()
        }
    
    def should_avoid_trading_today(self) -> Tuple[bool, str]:
        """
        Check if trading should be avoided due to economic events
        Returns: (should_avoid, reason)
        """
        analysis = self.get_todays_events()
        
        if analysis['avoid_trading']:
            events_str = ', '.join([e['name'] for e in analysis['major_events'][:2]])
            return True, f"Major events today: {events_str}"
        
        return False, "No major events"
    
    def get_event_risk_factor(self) -> float:
        """
        Calculate risk multiplier for position sizing
        Returns: 0.5 to 1.0 (reduce positions on event days)
        """
        analysis = self.get_todays_events()
        
        if analysis['risk_level'] == 'EXTREME':
            return 0.5  # Half size on extreme risk days
        elif analysis['risk_level'] == 'HIGH':
            return 0.7
        elif analysis['risk_level'] == 'MEDIUM':
            return 0.85
        
        return 1.0  # No reduction
    
    def get_earnings_calendar(self, symbol: str) -> Dict:
        """
        Get earnings date for a symbol
        Note: Would use Alpaca or Earnings Whispers API in production
        """
        # Simplified - in production would fetch from API
        return {
            'has_earnings_soon': False,
            'earnings_date': None,
            'days_until_earnings': None,
            'avoid_trading': False
        }


if __name__ == "__main__":
    # Test the calendar
    logging.basicConfig(level=logging.INFO)
    calendar = EconomicCalendar()
    
    print("Today's Economic Events:")
    result = calendar.get_todays_events()
    print(json.dumps(result, indent=2))
