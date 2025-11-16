"""
Risk management module.
Handles position sizing, stop losses, portfolio limits, and risk controls.
"""
import logging
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from config import Config

logger = logging.getLogger(__name__)

class RiskManager:
    """Manages risk across all trading operations."""
    
    def __init__(self):
        self.daily_pnl = 0.0
        self.daily_start_value = 0.0
        self.trade_count_today = 0
        self.last_reset = datetime.now().date()
        self.position_limits = {}
        self.stop_losses = {}
        self.take_profits = {}
    
    def reset_daily_stats(self, current_value: float):
        """Reset daily statistics."""
        today = datetime.now().date()
        if today != self.last_reset:
            self.daily_pnl = 0.0
            self.daily_start_value = current_value
            self.trade_count_today = 0
            self.last_reset = today
            logger.info(f"Reset daily stats. Starting value: ${current_value:,.2f}")
    
    def can_trade(self, account_value: float) -> Tuple[bool, str]:
        """
        Check if trading is allowed based on risk parameters.
        
        Returns:
            Tuple of (can_trade: bool, reason: str)
        """
        self.reset_daily_stats(account_value)
        
        # Check daily loss limit
        if self.daily_start_value > 0:
            daily_loss_pct = (account_value - self.daily_start_value) / self.daily_start_value
            
            if daily_loss_pct < -Config.MAX_DAILY_LOSS:
                return False, f"Daily loss limit reached: {daily_loss_pct*100:.2f}%"
        
        return True, "OK"
    
    def calculate_position_size(self, symbol: str, price: float, 
                               account_value: float, signal_strength: float = 1.0) -> int:
        """
        Calculate safe position size based on risk parameters.
        
        Args:
            symbol: Stock ticker
            price: Current price
            account_value: Total account value
            signal_strength: Signal confidence (0-1), affects position size
        """
        if price <= 0 or account_value <= 0:
            return 0
        
        # Maximum position value based on config
        max_position_value = account_value * Config.MAX_POSITION_SIZE * signal_strength
        
        # Calculate shares
        shares = int(max_position_value / price)
        
        # Ensure we don't exceed buying power
        max_affordable = int(account_value * 0.95 / price)  # Leave 5% buffer
        shares = min(shares, max_affordable)
        
        return max(0, shares)
    
    def calculate_stop_loss(self, symbol: str, entry_price: float, 
                           side: str) -> float:
        """Calculate stop loss price."""
        if not Config.USE_STOP_LOSS:
            return 0.0
        
        if side.upper() == 'BUY':
            stop_price = entry_price * (1 - Config.STOP_LOSS_PCT)
        else:
            stop_price = entry_price * (1 + Config.STOP_LOSS_PCT)
        
        self.stop_losses[symbol] = stop_price
        return stop_price
    
    def calculate_take_profit(self, symbol: str, entry_price: float, 
                             side: str) -> float:
        """Calculate take profit price."""
        if not Config.USE_TAKE_PROFIT:
            return 0.0
        
        if side.upper() == 'BUY':
            take_profit_price = entry_price * (1 + Config.TAKE_PROFIT_PCT)
        else:
            take_profit_price = entry_price * (1 - Config.TAKE_PROFIT_PCT)
        
        self.take_profits[symbol] = take_profit_price
        return take_profit_price
    
    def check_stop_loss(self, symbol: str, current_price: float) -> bool:
        """Check if stop loss has been triggered."""
        if symbol not in self.stop_losses:
            return False
        
        stop_price = self.stop_losses[symbol]
        
        # For long positions, stop if price falls below stop
        if current_price <= stop_price:
            logger.warning(f"Stop loss triggered for {symbol}: ${current_price:.2f} <= ${stop_price:.2f}")
            return True
        
        return False
    
    def check_take_profit(self, symbol: str, current_price: float) -> bool:
        """Check if take profit has been triggered."""
        if symbol not in self.take_profits:
            return False
        
        take_profit_price = self.take_profits[symbol]
        
        # For long positions, take profit if price rises above target
        if current_price >= take_profit_price:
            logger.info(f"Take profit triggered for {symbol}: ${current_price:.2f} >= ${take_profit_price:.2f}")
            return True
        
        return False
    
    def should_close_position(self, symbol: str, current_price: float, 
                             entry_price: float, unrealized_pl_pct: float) -> Tuple[bool, str]:
        """
        Determine if a position should be closed based on risk management rules.
        
        Returns:
            Tuple of (should_close: bool, reason: str)
        """
        # Check stop loss
        if self.check_stop_loss(symbol, current_price):
            return True, "Stop loss triggered"
        
        # Check take profit
        if self.check_take_profit(symbol, current_price):
            return True, "Take profit target reached"
        
        # Check max loss even without configured stop loss
        if unrealized_pl_pct < -0.05:  # Emergency stop at 5% loss
            return True, "Emergency stop - excessive loss"
        
        return False, ""
    
    def update_stop_loss_trailing(self, symbol: str, current_price: float, 
                                  entry_price: float, trailing_pct: float = 0.02):
        """Update stop loss to trailing stop."""
        if symbol not in self.stop_losses:
            return
        
        # Only trail if we're in profit
        profit_pct = (current_price - entry_price) / entry_price
        if profit_pct > 0:
            new_stop = current_price * (1 - trailing_pct)
            
            # Only move stop loss up, never down
            if new_stop > self.stop_losses[symbol]:
                self.stop_losses[symbol] = new_stop
                logger.info(f"Updated trailing stop for {symbol} to ${new_stop:.2f}")
    
    def record_trade(self, symbol: str, pnl: float):
        """Record a completed trade."""
        self.daily_pnl += pnl
        self.trade_count_today += 1
        logger.info(f"Trade recorded: {symbol}, P&L: ${pnl:.2f}, Daily P&L: ${self.daily_pnl:.2f}")
    
    def get_risk_summary(self) -> Dict:
        """Get current risk statistics."""
        return {
            'daily_pnl': self.daily_pnl,
            'daily_start_value': self.daily_start_value,
            'trade_count_today': self.trade_count_today,
            'active_stop_losses': len(self.stop_losses),
            'active_take_profits': len(self.take_profits)
        }
