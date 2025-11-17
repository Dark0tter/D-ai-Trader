"""
Safe Mode - Automatic risk reduction during unfavorable market conditions
Protects capital by detecting dangerous market environments
"""

import logging
from datetime import datetime
from typing import Dict, Tuple

logger = logging.getLogger(__name__)

class SafeMode:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.safe_mode_active = False
        self.safe_mode_reason = ""
        
    def evaluate_market_safety(self, intelligence: Dict, account_performance: Dict) -> Tuple[bool, str, float]:
        """
        Evaluate if market conditions are safe for trading
        Returns: (is_safe, reason, risk_reduction_factor)
        
        risk_reduction_factor:
        - 1.0 = Normal trading
        - 0.5 = Reduce positions by 50%
        - 0.25 = Extreme caution - minimal trading
        - 0.0 = FULL SAFE MODE - no new trades
        """
        danger_score = 0
        danger_reasons = []
        
        # 1. MACRO REGIME - Check for recession/bear market
        macro = intelligence.get('macro', {})
        if macro.get('regime') == 'BEARISH' and macro.get('confidence', 0) > 75:
            danger_score += 30
            danger_reasons.append(f"Bearish macro regime ({macro['confidence']}% conf)")
        
        # Inverted yield curve = recession warning
        if macro.get('treasury_spread') and macro['treasury_spread'] < 0:
            danger_score += 20
            danger_reasons.append("Inverted yield curve (recession signal)")
        
        # 2. VIX / VOLATILITY - High fear in market
        vix = macro.get('vix')
        if vix and vix > 30:
            danger_score += 25
            danger_reasons.append(f"High volatility (VIX {vix})")
        elif vix and vix > 25:
            danger_score += 15
            danger_reasons.append(f"Elevated volatility (VIX {vix})")
        
        # 3. CRYPTO CRASH - Risk-off sentiment
        crypto = intelligence.get('crypto', {})
        btc_change = crypto.get('btc_change_24h', 0)
        if btc_change < -10:
            danger_score += 25
            danger_reasons.append(f"Crypto crash (BTC {btc_change}%)")
        elif btc_change < -5:
            danger_score += 10
            danger_reasons.append(f"Crypto selling (BTC {btc_change}%)")
        
        # 4. ECONOMIC EVENTS - Major volatility catalysts
        econ = intelligence.get('economic', {})
        if econ.get('risk_level') == 'EXTREME':
            danger_score += 30
            danger_reasons.append(f"Extreme event risk ({econ.get('event_count', 0)} major events)")
        elif econ.get('risk_level') == 'HIGH':
            danger_score += 15
            danger_reasons.append("High event risk today")
        
        # 5. ACCOUNT DRAWDOWN - Personal performance protection
        if account_performance:
            daily_pnl_pct = account_performance.get('daily_pnl_pct', 0)
            
            # Circuit breaker: Stop trading if down 3% in one day
            if daily_pnl_pct < -3.0:
                danger_score += 50
                danger_reasons.append(f"Daily loss limit hit ({daily_pnl_pct:.1f}%)")
            elif daily_pnl_pct < -2.0:
                danger_score += 30
                danger_reasons.append(f"Significant daily losses ({daily_pnl_pct:.1f}%)")
            elif daily_pnl_pct < -1.0:
                danger_score += 15
                danger_reasons.append(f"Daily losses mounting ({daily_pnl_pct:.1f}%)")
            
            # Check losing streak
            losing_streak = account_performance.get('losing_streak', 0)
            if losing_streak >= 5:
                danger_score += 20
                danger_reasons.append(f"Losing streak: {losing_streak} trades")
            elif losing_streak >= 3:
                danger_score += 10
                danger_reasons.append(f"Losing streak: {losing_streak} trades")
        
        # 6. WIDESPREAD NEGATIVE NEWS - Market sentiment crash
        news_summary = intelligence.get('news_summary', {})
        bearish_symbols = len(news_summary.get('bearish_symbols', []))
        bullish_symbols = len(news_summary.get('bullish_symbols', []))
        
        if bearish_symbols > bullish_symbols * 2 and bearish_symbols >= 3:
            danger_score += 15
            danger_reasons.append(f"Widespread negative news ({bearish_symbols} bearish vs {bullish_symbols} bullish)")
        
        # CALCULATE RISK REDUCTION
        risk_reduction = 1.0
        is_safe = True
        
        if danger_score >= 80:
            # FULL SAFE MODE - No new trades
            risk_reduction = 0.0
            is_safe = False
            reason = f"🚨 FULL SAFE MODE ACTIVATED - {', '.join(danger_reasons[:3])}"
        elif danger_score >= 60:
            # Extreme caution - minimal trading
            risk_reduction = 0.25
            is_safe = True
            reason = f"⚠️ EXTREME CAUTION MODE - {', '.join(danger_reasons[:2])}"
        elif danger_score >= 40:
            # Reduce positions by 50%
            risk_reduction = 0.5
            is_safe = True
            reason = f"⚠️ DEFENSIVE MODE - {', '.join(danger_reasons[:2])}"
        elif danger_score >= 20:
            # Slight reduction
            risk_reduction = 0.75
            is_safe = True
            reason = f"⚠️ CAUTION - {danger_reasons[0]}"
        else:
            # Normal trading
            reason = "✅ Market conditions favorable"
        
        # Log safe mode status
        if danger_score > 0:
            self.logger.warning(f"Market Safety Score: {danger_score}/100 - Risk Reduction: {risk_reduction*100:.0f}%")
            self.logger.warning(f"Reasons: {', '.join(danger_reasons)}")
        
        self.safe_mode_active = not is_safe
        self.safe_mode_reason = reason
        
        return is_safe, reason, risk_reduction
    
    def should_close_all_positions(self, intelligence: Dict, account_performance: Dict) -> Tuple[bool, str]:
        """
        Determine if we should emergency close all positions
        Only in extreme market crashes
        """
        emergency_reasons = []
        
        # Market crash detection
        crypto = intelligence.get('crypto', {})
        if crypto.get('btc_change_24h', 0) < -15:
            emergency_reasons.append("Crypto market crash (BTC -15%+)")
        
        # VIX explosion
        vix = intelligence.get('macro', {}).get('vix')
        if vix and vix > 40:
            emergency_reasons.append(f"Extreme fear (VIX {vix})")
        
        # Account protection
        if account_performance:
            daily_pnl_pct = account_performance.get('daily_pnl_pct', 0)
            if daily_pnl_pct < -5.0:
                emergency_reasons.append(f"Emergency stop loss ({daily_pnl_pct:.1f}% daily loss)")
        
        if len(emergency_reasons) >= 2:
            reason = f"🚨 EMERGENCY: {', '.join(emergency_reasons)}"
            return True, reason
        
        return False, ""
    
    def apply_safe_mode_to_allocation(self, risk_tier_allocation: Dict[str, float], 
                                       risk_reduction: float) -> Dict[str, float]:
        """
        Apply risk reduction to capital allocation
        """
        if risk_reduction >= 1.0:
            return risk_tier_allocation
        
        adjusted = {}
        for tier, amount in risk_tier_allocation.items():
            adjusted[tier] = amount * risk_reduction
        
        self.logger.info(f"💰 Capital allocation adjusted by {risk_reduction*100:.0f}% due to market conditions")
        return adjusted


if __name__ == "__main__":
    # Test safe mode
    logging.basicConfig(level=logging.INFO)
    safe_mode = SafeMode()
    
    # Test scenario: Market crash
    test_intelligence = {
        'macro': {'regime': 'BEARISH', 'confidence': 85, 'vix': 35, 'treasury_spread': -0.5},
        'crypto': {'btc_change_24h': -12},
        'economic': {'risk_level': 'HIGH', 'event_count': 2}
    }
    
    test_performance = {
        'daily_pnl_pct': -2.5,
        'losing_streak': 4
    }
    
    is_safe, reason, reduction = safe_mode.evaluate_market_safety(test_intelligence, test_performance)
    print(f"Is Safe: {is_safe}")
    print(f"Reason: {reason}")
    print(f"Risk Reduction: {reduction*100:.0f}%")
