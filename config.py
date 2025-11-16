"""
Configuration management for the trading bot.
Loads settings from environment variables and provides defaults.
"""
import os
from dotenv import load_dotenv
from typing import List

# Load environment variables from .env file
load_dotenv()

class Config:
    """Centralized configuration for the trading system."""
    
    # API Credentials
    ALPACA_API_KEY = os.getenv('ALPACA_API_KEY', '')
    ALPACA_SECRET_KEY = os.getenv('ALPACA_SECRET_KEY', '')
    ALPACA_PAPER = os.getenv('ALPACA_PAPER', 'True').lower() == 'true'
    POLYGON_API_KEY = os.getenv('POLYGON_API_KEY', '')
    
    # Capital and portfolio settings
    INITIAL_CAPITAL = float(os.getenv('INITIAL_CAPITAL', '10000.00'))
    MAX_POSITION_SIZE = float(os.getenv('MAX_POSITION_SIZE', '0.1'))
    MAX_DAILY_LOSS = float(os.getenv('MAX_DAILY_LOSS', '0.02'))
    RISK_PER_TRADE = float(os.getenv('RISK_PER_TRADE', '0.01'))
    
    # Trading settings
    TRADING_MODE = os.getenv('TRADING_MODE', 'paper')
    STRATEGY = os.getenv('STRATEGY', 'momentum')
    WATCHLIST = os.getenv('WATCHLIST', 'AAPL,MSFT,GOOGL,TSLA').split(',')
    
    # Risk management
    USE_STOP_LOSS = os.getenv('USE_STOP_LOSS', 'True').lower() == 'true'
    STOP_LOSS_PCT = float(os.getenv('STOP_LOSS_PCT', '0.02'))
    USE_TAKE_PROFIT = os.getenv('USE_TAKE_PROFIT', 'True').lower() == 'true'
    TAKE_PROFIT_PCT = float(os.getenv('TAKE_PROFIT_PCT', '0.04'))
    
    # Market hours
    MARKET_OPEN_HOUR = int(os.getenv('MARKET_OPEN_HOUR', '9'))
    MARKET_OPEN_MINUTE = int(os.getenv('MARKET_OPEN_MINUTE', '30'))
    MARKET_CLOSE_HOUR = int(os.getenv('MARKET_CLOSE_HOUR', '15'))
    MARKET_CLOSE_MINUTE = int(os.getenv('MARKET_CLOSE_MINUTE', '45'))
    
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///trading_bot.db')
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/trading_bot.log')
    
    @classmethod
    def validate(cls) -> bool:
        """Validate that required configuration is present."""
        if not cls.ALPACA_API_KEY or not cls.ALPACA_SECRET_KEY:
            raise ValueError("Alpaca API credentials are required. Please set ALPACA_API_KEY and ALPACA_SECRET_KEY in .env file")
        return True
    
    @classmethod
    def is_paper_trading(cls) -> bool:
        """Check if we're in paper trading mode."""
        return cls.TRADING_MODE.lower() == 'paper' or cls.ALPACA_PAPER
