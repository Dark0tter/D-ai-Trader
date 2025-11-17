"""
Quarterly Reinvestment & Principal Protection Manager

Rules:
1. Daily ratcheting floor - principal moves UP with each day's gains, never down
2. 60% of gains reinvested into trading
3. 40% of gains withdrawn/distributed
4. Cannot distribute if below yesterday's floor (prevents draining)
5. At quarter end, current balance becomes new quarter's starting principal
6. Tracks volatility and adjusts risk accordingly
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class QuarterlyManager:
    """Manages quarterly principal, gain distribution, and volatility-based risk."""
    
    def __init__(self, data_file: str = "quarterly_data.json"):
        self.data_file = Path(data_file)
        self.data = self._load_data()
        
    def _load_data(self) -> Dict:
        """Load quarterly data from file."""
        if self.data_file.exists():
            with open(self.data_file, 'r') as f:
                return json.load(f)
        else:
            # Initialize with current quarter
            return self._initialize_quarter()
    
    def _save_data(self):
        """Save quarterly data to file."""
        with open(self.data_file, 'w') as f:
            json.dump(self.data, f, indent=2)
    
    def _initialize_quarter(self, starting_balance: float = None) -> Dict:
        """Initialize a new quarter."""
        now = datetime.now()
        quarter = (now.month - 1) // 3 + 1
        
        return {
            'quarter': quarter,
            'year': now.year,
            'start_date': now.isoformat(),
            'quarter_start_principal': starting_balance or 100000.0,  # Quarter starting amount
            'daily_principal': starting_balance or 100000.0,  # Today's floor (ratchets up daily)
            'yesterday_principal': starting_balance or 100000.0,  # Yesterday's floor
            'current_balance': starting_balance or 100000.0,
            'total_distributed': 0.0,
            'total_reinvested': 0.0,
            'last_distribution': None,
            'last_principal_update': now.date().isoformat(),
            'in_recovery_mode': False,
            'volatility_score': 0.0,
            'max_drawdown': 0.0,
            'peak_balance': starting_balance or 100000.0
        }
    
    def check_new_quarter(self, current_balance: float) -> bool:
        """Check if we've entered a new quarter and initialize if needed."""
        now = datetime.now()
        current_quarter = (now.month - 1) // 3 + 1
        
        if current_quarter != self.data['quarter'] or now.year != self.data['year']:
            logger.info(f"New quarter detected: Q{current_quarter} {now.year}")
            
            # Carry forward current balance as new principal
            self.data = self._initialize_quarter(current_balance)
            self._save_data()
            return True
        return False
    
    def update_balance(self, current_balance: float) -> Dict:
        """
        Update current balance and calculate gains/distributions.
        Uses DAILY RATCHETING - floor moves up each day with gains, never down.
        
        Returns dict with:
        - can_distribute: bool
        - distributable_amount: float (40% of today's gains)
        - reinvest_amount: float (60% of today's gains)
        - in_recovery: bool
        - principal_protected: bool
        """
        self.check_new_quarter(current_balance)
        
        # Check if it's a new day - if so, ratchet the principal
        now = datetime.now()
        today = now.date().isoformat()
        
        if today != self.data['last_principal_update']:
            # New day - check if yesterday's balance was higher than yesterday's floor
            yesterday_balance = self.data['current_balance']
            yesterday_floor = self.data['daily_principal']
            
            if yesterday_balance > yesterday_floor:
                # Ratchet up! Yesterday's gains become part of today's floor
                # After distributing 40%, the remaining 60% becomes the new floor
                daily_gain = yesterday_balance - yesterday_floor
                distributable = daily_gain * 0.40
                new_principal_addition = daily_gain * 0.60  # 60% stays in
                
                self.data['yesterday_principal'] = self.data['daily_principal']
                self.data['daily_principal'] = yesterday_floor + new_principal_addition
                
                logger.info(f"🔒 DAILY RATCHET: Floor raised from ${yesterday_floor:,.2f} to ${self.data['daily_principal']:,.2f}")
                logger.info(f"📤 Available to withdraw: ${distributable:,.2f} (40% of yesterday's ${daily_gain:,.2f} gain)")
            
            self.data['last_principal_update'] = today
        
        daily_floor = self.data['daily_principal']
        previous_balance = self.data['current_balance']
        self.data['current_balance'] = current_balance
        
        # Update peak balance
        if current_balance > self.data['peak_balance']:
            self.data['peak_balance'] = current_balance
        
        # Calculate drawdown from peak
        drawdown = (self.data['peak_balance'] - current_balance) / self.data['peak_balance']
        if drawdown > self.data['max_drawdown']:
            self.data['max_drawdown'] = drawdown
        
        # Check if below today's floor (recovery mode - NO DISTRIBUTIONS)
        if current_balance < daily_floor:
            self.data['in_recovery_mode'] = True
            logger.warning(f"⚠️  RECOVERY MODE: Balance ${current_balance:,.2f} below today's floor ${daily_floor:,.2f}")
            self._save_data()
            return {
                'can_distribute': False,
                'distributable_amount': 0.0,
                'reinvest_amount': 0.0,
                'in_recovery': True,
                'principal_protected': True,
                'current_gain': current_balance - daily_floor,
                'recovery_needed': daily_floor - current_balance,
                'daily_floor': daily_floor
            }
        
        # If we were in recovery and now above floor
        if self.data['in_recovery_mode'] and current_balance >= daily_floor:
            logger.info(f"✅ RECOVERED: Balance ${current_balance:,.2f} back above floor ${daily_floor:,.2f}")
            self.data['in_recovery_mode'] = False
        
        # Calculate TODAY'S gains above the floor
        todays_gain = current_balance - daily_floor
        
        if todays_gain > 0:
            # 40% can be distributed, 60% will become tomorrow's floor (after daily ratchet)
            distributable_now = todays_gain * 0.40
            staying_in = todays_gain * 0.60
            
            self._save_data()
            return {
                'can_distribute': True,
                'distributable_amount': distributable_now,
                'reinvest_amount': staying_in,
                'in_recovery': False,
                'principal_protected': True,
                'current_gain': todays_gain,
                'recovery_needed': 0.0,
                'daily_floor': daily_floor
            }
        else:
            # At floor, no gains yet today
            self._save_data()
            return {
                'can_distribute': False,
                'distributable_amount': 0.0,
                'reinvest_amount': 0.0,
                'in_recovery': False,
                'principal_protected': True,
                'current_gain': 0.0,
                'recovery_needed': 0.0,
                'daily_floor': daily_floor
            }
    
    def record_distribution(self, amount: float):
        """Record a distribution of gains."""
        self.data['total_distributed'] += amount
        self.data['last_distribution'] = datetime.now().isoformat()
        self.data['principal'] += amount  # Adjust principal after withdrawal
        self._save_data()
        logger.info(f"Distributed ${amount:.2f}. Total distributed this quarter: ${self.data['total_distributed']:.2f}")
    
    def update_volatility(self, volatility_score: float):
        """Update volatility score (0-100, higher = more volatile)."""
        self.data['volatility_score'] = volatility_score
        self._save_data()
    
    def get_risk_adjustment(self) -> float:
        """
        Get risk adjustment multiplier based on volatility and drawdown.
        
        Returns: float between 0.2 and 1.0
        - High volatility = lower multiplier (reduce position sizes)
        - High drawdown = lower multiplier (be more conservative)
        """
        volatility_factor = max(0.5, 1.0 - (self.data['volatility_score'] / 100))
        drawdown_factor = max(0.5, 1.0 - (self.data['max_drawdown'] * 2))
        
        # If in recovery mode, be extra conservative
        recovery_factor = 0.5 if self.data['in_recovery_mode'] else 1.0
        
        adjustment = volatility_factor * drawdown_factor * recovery_factor
        return max(0.2, min(1.0, adjustment))  # Clamp between 0.2 and 1.0
    
    def get_status(self) -> Dict:
        """Get current quarterly status."""
        return {
            'quarter': f"Q{self.data['quarter']} {self.data['year']}",
            'quarter_start_principal': self.data['quarter_start_principal'],
            'daily_floor': self.data['daily_principal'],
            'yesterday_floor': self.data['yesterday_principal'],
            'current_balance': self.data['current_balance'],
            'todays_gain': self.data['current_balance'] - self.data['daily_principal'],
            'quarter_total_gain': self.data['current_balance'] - self.data['quarter_start_principal'],
            'in_recovery_mode': self.data['in_recovery_mode'],
            'total_distributed': self.data['total_distributed'],
            'total_reinvested': self.data['total_reinvested'],
            'volatility_score': self.data['volatility_score'],
            'max_drawdown_pct': self.data['max_drawdown'] * 100,
            'risk_adjustment': self.get_risk_adjustment(),
            'peak_balance': self.data['peak_balance']
        }
    
    def should_reduce_risk(self) -> bool:
        """Determine if bot should reduce risk based on conditions."""
        # Reduce risk if:
        # 1. In recovery mode
        # 2. High volatility (>70)
        # 3. Large drawdown (>10%)
        return (
            self.data['in_recovery_mode'] or
            self.data['volatility_score'] > 70 or
            self.data['max_drawdown'] > 0.10
        )
    
    def reset_quarterly_stats(self):
        """Reset quarterly statistics (drawdown, volatility) for new quarter."""
        self.data['max_drawdown'] = 0.0
        self.data['volatility_score'] = 0.0
        self.data['peak_balance'] = self.data['current_balance']
        self._save_data()


def main():
    """Example usage."""
    qm = QuarterlyManager()
    
    # Simulate different scenarios with daily ratcheting
    scenarios = [
        ("Day 1: Starting balance", 100000),
        ("Day 1 EOD: Up to 105k", 105000),
        ("Day 2 Morning: Opens at 105k floor (60% of 5k gain = 3k added to floor)", 105000),
        ("Day 2 EOD: Up to 110k", 110000),
        ("Day 3 Morning: Opens at 108k floor (103k + 60% of 5k)", 108000),
        ("Day 3 Dip: Down to 107k (below floor = recovery mode)", 107000),
        ("Day 3 EOD: Recovered to 112k", 112000),
    ]
    
    print("\n=== DAILY RATCHETING PRINCIPAL PROTECTION ===\n")
    
    for desc, balance in scenarios:
        print(f"\n{desc}: ${balance:,.2f}")
        result = qm.update_balance(balance)
        
        print(f"  Daily Floor: ${result['daily_floor']:,.2f}")
        print(f"  In Recovery: {result['in_recovery']}")
        print(f"  Can Distribute: {result['can_distribute']}")
        if result['can_distribute']:
            print(f"  → Distribute TODAY (40%): ${result['distributable_amount']:,.2f}")
            print(f"  → Stays In (60%): ${result['reinvest_amount']:,.2f} (becomes tomorrow's floor)")
        elif result['in_recovery']:
            print(f"  → Recovery Needed: ${result['recovery_needed']:,.2f}")
        
        print(f"  Today's Gain: ${result['current_gain']:,.2f}")
    
    print("\n=== FINAL STATUS ===")
    status = qm.get_status()
    for key, value in status.items():
        print(f"  {key}: {value}")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()
