"""
Logging and monitoring system.
Handles all logging, performance tracking, and alerts.
"""
import logging
import colorlog
from datetime import datetime
import os
from typing import Dict
from pathlib import Path

def setup_logging(log_level: str = 'INFO', log_file: str = None):
    """
    Setup comprehensive logging system with color output and file logging.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Path to log file
    """
    # Create logs directory if it doesn't exist
    if log_file:
        log_dir = Path(log_file).parent
        log_dir.mkdir(parents=True, exist_ok=True)
    
    # Color formatter for console
    color_formatter = colorlog.ColoredFormatter(
        '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    )
    
    # File formatter
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(color_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    return root_logger

class PerformanceTracker:
    """Track and report trading performance."""
    
    def __init__(self):
        self.trades = []
        self.daily_stats = {}
        self.start_time = datetime.now()
        self.logger = logging.getLogger(__name__)
    
    def record_trade(self, trade: Dict):
        """Record a completed trade."""
        trade['timestamp'] = datetime.now()
        self.trades.append(trade)
        self.logger.info(f"Trade recorded: {trade['symbol']} - P&L: ${trade.get('pnl', 0):.2f}")
    
    def get_performance_summary(self) -> Dict:
        """Get overall performance summary."""
        if not self.trades:
            return {
                'total_trades': 0,
                'total_pnl': 0,
                'win_rate': 0,
                'avg_pnl': 0
            }
        
        total_trades = len(self.trades)
        total_pnl = sum(t.get('pnl', 0) for t in self.trades)
        winning_trades = sum(1 for t in self.trades if t.get('pnl', 0) > 0)
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        avg_pnl = total_pnl / total_trades if total_trades > 0 else 0
        
        return {
            'total_trades': total_trades,
            'total_pnl': total_pnl,
            'winning_trades': winning_trades,
            'win_rate': win_rate,
            'avg_pnl': avg_pnl,
            'runtime': (datetime.now() - self.start_time).total_seconds() / 3600  # hours
        }
    
    def print_summary(self):
        """Print performance summary."""
        summary = self.get_performance_summary()
        
        print("\n" + "="*50)
        print("PERFORMANCE SUMMARY")
        print("="*50)
        print(f"Total Trades:       {summary['total_trades']}")
        print(f"Total P&L:          ${summary['total_pnl']:,.2f}")
        print(f"Winning Trades:     {summary['winning_trades']}")
        print(f"Win Rate:           {summary['win_rate']:.2f}%")
        print(f"Average P&L:        ${summary['avg_pnl']:.2f}")
        print(f"Runtime:            {summary['runtime']:.2f} hours")
        print("="*50 + "\n")

class AlertSystem:
    """Alert system for important events."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def send_alert(self, level: str, message: str):
        """
        Send an alert.
        
        Args:
            level: Alert level (INFO, WARNING, ERROR, CRITICAL)
            message: Alert message
        """
        if level.upper() == 'INFO':
            self.logger.info(f"ALERT: {message}")
        elif level.upper() == 'WARNING':
            self.logger.warning(f"ALERT: {message}")
        elif level.upper() == 'ERROR':
            self.logger.error(f"ALERT: {message}")
        elif level.upper() == 'CRITICAL':
            self.logger.critical(f"ALERT: {message}")
        
        # In production, you could extend this to send emails, SMS, etc.
    
    def trade_alert(self, action: str, symbol: str, quantity: float, price: float):
        """Send alert for trade execution."""
        message = f"{action} {quantity} shares of {symbol} at ${price:.2f}"
        self.send_alert('INFO', message)
    
    def risk_alert(self, message: str):
        """Send risk-related alert."""
        self.send_alert('WARNING', f"RISK: {message}")
    
    def error_alert(self, message: str):
        """Send error alert."""
        self.send_alert('ERROR', f"ERROR: {message}")
