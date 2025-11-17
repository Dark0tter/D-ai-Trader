"""
Overnight Pattern Analyzer
Analyzes after-hours and overnight price movements to predict next-day behavior
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List
import numpy as np
from database import Database

logger = logging.getLogger(__name__)

class OvernightPatternAnalyzer:
    """Analyzes overnight patterns to predict next-day market behavior."""
    
    def __init__(self):
        self.database = Database()
        self.patterns = {}  # Store learned patterns
        self.predictions = {}  # Next-day predictions
    
    def analyze_overnight_movement(self, symbol: str, data) -> Dict:
        """
        Analyze overnight price movement and volume patterns.
        
        Returns:
            Dict with overnight analysis and next-day prediction
        """
        try:
            if len(data) < 2:
                return {}
            
            latest = data.iloc[-1]
            previous = data.iloc[-2]
            
            # Calculate overnight metrics
            overnight_change = ((latest['Close'] - previous['Close']) / previous['Close']) * 100
            volume_change = ((latest.get('Volume', 0) - previous.get('Volume', 1)) / previous.get('Volume', 1)) * 100
            
            # Analyze volatility
            recent_prices = data['Close'].tail(10)
            volatility = recent_prices.std() / recent_prices.mean() * 100
            
            # Calculate momentum
            if len(data) >= 5:
                short_ma = data['Close'].tail(5).mean()
                long_ma = data['Close'].tail(10).mean() if len(data) >= 10 else short_ma
                momentum = ((short_ma - long_ma) / long_ma) * 100 if long_ma > 0 else 0
            else:
                momentum = 0
            
            # Gap analysis (difference between previous close and current open)
            if 'Open' in latest and 'Open' in previous:
                gap = ((latest['Open'] - previous['Close']) / previous['Close']) * 100
            else:
                gap = 0
            
            analysis = {
                'symbol': symbol,
                'timestamp': datetime.now(),
                'overnight_change_pct': overnight_change,
                'volume_change_pct': volume_change,
                'volatility': volatility,
                'momentum': momentum,
                'gap_pct': gap,
                'current_price': float(latest['Close']),
                'rsi': float(latest.get('RSI', 50))
            }
            
            # Generate prediction for next day
            prediction = self._predict_next_day_behavior(analysis)
            analysis['prediction'] = prediction
            
            # Store pattern for learning
            self._store_pattern(symbol, analysis)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing overnight movement for {symbol}: {e}")
            return {}
    
    def _predict_next_day_behavior(self, analysis: Dict) -> Dict:
        """
        Predict next-day market behavior based on overnight patterns.
        
        Returns predictions for:
        - Expected direction (UP/DOWN/NEUTRAL)
        - Volatility level (HIGH/MEDIUM/LOW)
        - Recommended action (BUY/SELL/HOLD/WAIT)
        """
        overnight_change = analysis['overnight_change_pct']
        volume_change = analysis['volume_change_pct']
        volatility = analysis['volatility']
        momentum = analysis['momentum']
        gap = analysis['gap_pct']
        rsi = analysis['rsi']
        
        # Direction prediction logic
        direction_score = 0
        
        # Strong overnight gains often continue into morning
        if overnight_change > 1:
            direction_score += 2
        elif overnight_change < -1:
            direction_score -= 2
        
        # Momentum indicator
        if momentum > 0.5:
            direction_score += 1
        elif momentum < -0.5:
            direction_score -= 1
        
        # Volume surge suggests continuation
        if volume_change > 20:
            direction_score += 1 if overnight_change > 0 else -1
        
        # RSI extremes suggest reversal
        if rsi > 70:  # Overbought
            direction_score -= 1
        elif rsi < 30:  # Oversold
            direction_score += 1
        
        # Gap behavior (gaps often fill)
        if abs(gap) > 1:
            # Large gaps tend to reverse
            direction_score -= 1 if gap > 0 else 1
        
        # Determine direction
        if direction_score >= 2:
            direction = "UP"
            confidence = min(abs(direction_score) * 15, 85)
        elif direction_score <= -2:
            direction = "DOWN"
            confidence = min(abs(direction_score) * 15, 85)
        else:
            direction = "NEUTRAL"
            confidence = 50
        
        # Volatility prediction
        if volatility > 3:
            volatility_level = "HIGH"
        elif volatility > 1.5:
            volatility_level = "MEDIUM"
        else:
            volatility_level = "LOW"
        
        # Recommended action
        if direction == "UP" and confidence > 65 and rsi < 65:
            action = "BUY"
            action_strength = "STRONG" if confidence > 75 else "MODERATE"
        elif direction == "DOWN" and confidence > 65:
            action = "SELL"
            action_strength = "STRONG" if confidence > 75 else "MODERATE"
        elif volatility_level == "HIGH":
            action = "WAIT"
            action_strength = "CAUTION"
        else:
            action = "HOLD"
            action_strength = "NEUTRAL"
        
        return {
            'direction': direction,
            'confidence': confidence,
            'volatility_level': volatility_level,
            'recommended_action': action,
            'action_strength': action_strength,
            'reasoning': self._generate_reasoning(
                overnight_change, volume_change, volatility, momentum, gap, rsi, direction
            )
        }
    
    def _generate_reasoning(self, overnight_change, volume_change, volatility, 
                           momentum, gap, rsi, direction) -> str:
        """Generate human-readable reasoning for the prediction."""
        reasons = []
        
        if abs(overnight_change) > 1:
            reasons.append(f"Overnight {'gain' if overnight_change > 0 else 'loss'} of {abs(overnight_change):.1f}%")
        
        if abs(volume_change) > 20:
            reasons.append(f"Volume {'surge' if volume_change > 0 else 'decline'} of {abs(volume_change):.1f}%")
        
        if abs(momentum) > 0.5:
            reasons.append(f"{'Positive' if momentum > 0 else 'Negative'} momentum trend")
        
        if rsi > 70:
            reasons.append(f"Overbought (RSI {rsi:.0f})")
        elif rsi < 30:
            reasons.append(f"Oversold (RSI {rsi:.0f})")
        
        if abs(gap) > 1:
            reasons.append(f"{'Upward' if gap > 0 else 'Downward'} gap of {abs(gap):.1f}% may fill")
        
        if volatility > 3:
            reasons.append(f"High volatility ({volatility:.1f}%)")
        
        return "; ".join(reasons) if reasons else "Normal market conditions"
    
    def _store_pattern(self, symbol: str, analysis: Dict):
        """Store overnight pattern for historical learning."""
        if symbol not in self.patterns:
            self.patterns[symbol] = []
        
        # Keep last 30 days of patterns
        self.patterns[symbol].append(analysis)
        if len(self.patterns[symbol]) > 30:
            self.patterns[symbol].pop(0)
        
        # Store prediction for next day
        self.predictions[symbol] = analysis['prediction']
    
    def get_next_day_prediction(self, symbol: str) -> Dict:
        """Get stored prediction for next trading day."""
        return self.predictions.get(symbol, {})
    
    def get_pattern_accuracy(self, symbol: str) -> float:
        """
        Calculate how accurate overnight predictions have been.
        Compares predicted direction vs actual next-day movement.
        """
        if symbol not in self.patterns or len(self.patterns[symbol]) < 5:
            return 0.0
        
        # This would be enhanced with actual next-day results
        # For now, return a placeholder
        return 0.0  # To be implemented with historical validation
    
    def get_overnight_summary(self) -> Dict:
        """Get summary of all overnight analyses."""
        summary = {
            'timestamp': datetime.now(),
            'total_symbols_analyzed': len(self.predictions),
            'bullish_predictions': sum(1 for p in self.predictions.values() if p.get('direction') == 'UP'),
            'bearish_predictions': sum(1 for p in self.predictions.values() if p.get('direction') == 'DOWN'),
            'neutral_predictions': sum(1 for p in self.predictions.values() if p.get('direction') == 'NEUTRAL'),
            'high_confidence_calls': sum(1 for p in self.predictions.values() if p.get('confidence', 0) > 70),
            'predictions_by_symbol': self.predictions
        }
        return summary
