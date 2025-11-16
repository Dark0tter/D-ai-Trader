"""
Trading strategy implementations.
Base strategy class and various strategy implementations.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)

class Strategy(ABC):
    """Base class for all trading strategies."""
    
    def __init__(self, name: str):
        self.name = name
        self.positions = {}
    
    @abstractmethod
    def generate_signals(self, symbol: str, data: pd.DataFrame) -> str:
        """
        Generate trading signal based on market data.
        
        Args:
            symbol: Stock ticker
            data: Historical price data with technical indicators
            
        Returns:
            Signal: 'BUY', 'SELL', or 'HOLD'
        """
        pass
    
    @abstractmethod
    def calculate_position_size(self, symbol: str, price: float, 
                                account_value: float) -> int:
        """Calculate the number of shares to trade."""
        pass


class MomentumStrategy(Strategy):
    """
    Momentum trading strategy.
    Buys stocks showing strong upward momentum and sells on reversal.
    """
    
    def __init__(self):
        super().__init__("Momentum")
        self.rsi_oversold = 30
        self.rsi_overbought = 70
    
    def generate_signals(self, symbol: str, data: pd.DataFrame) -> str:
        """Generate signals based on momentum indicators."""
        if data.empty or len(data) < 50:
            return 'HOLD'
        
        try:
            latest = data.iloc[-1]
            prev = data.iloc[-2]
            
            # Check if we have required indicators
            required_cols = ['RSI', 'MACD', 'MACD_Signal', 'SMA_20', 'SMA_50', 'Close']
            if not all(col in data.columns for col in required_cols):
                logger.warning(f"Missing required indicators for {symbol}")
                return 'HOLD'
            
            # Momentum signals
            rsi = latest['RSI']
            macd = latest['MACD']
            macd_signal = latest['MACD_Signal']
            price = latest['Close']
            sma_20 = latest['SMA_20']
            sma_50 = latest['SMA_50']
            
            # Volume confirmation
            volume_spike = latest['Volume'] > latest['Volume_MA'] * 1.5 if 'Volume_MA' in data.columns else False
            
            # BUY conditions
            buy_conditions = [
                rsi < self.rsi_oversold,  # RSI oversold
                macd > macd_signal,  # MACD crossover
                price > sma_20,  # Price above short-term MA
                sma_20 > sma_50,  # Golden cross trend
            ]
            
            # SELL conditions
            sell_conditions = [
                rsi > self.rsi_overbought,  # RSI overbought
                macd < macd_signal,  # MACD crossunder
                price < sma_20,  # Price below short-term MA
            ]
            
            if sum(buy_conditions) >= 3:
                return 'BUY'
            elif sum(sell_conditions) >= 2:
                return 'SELL'
            else:
                return 'HOLD'
                
        except Exception as e:
            logger.error(f"Error generating momentum signals for {symbol}: {e}")
            return 'HOLD'
    
    def calculate_position_size(self, symbol: str, price: float, 
                                account_value: float) -> int:
        """Calculate position size based on account value and risk."""
        from config import Config
        
        max_position_value = account_value * Config.MAX_POSITION_SIZE
        shares = int(max_position_value / price)
        return max(1, shares)  # At least 1 share


class MeanReversionStrategy(Strategy):
    """
    Mean reversion strategy.
    Assumes prices will revert to their mean over time.
    """
    
    def __init__(self):
        super().__init__("Mean Reversion")
        self.bb_std_threshold = 2.0
    
    def generate_signals(self, symbol: str, data: pd.DataFrame) -> str:
        """Generate signals based on mean reversion indicators."""
        if data.empty or len(data) < 20:
            return 'HOLD'
        
        try:
            latest = data.iloc[-1]
            
            # Check for Bollinger Bands
            required_cols = ['Close', 'BB_Upper', 'BB_Lower', 'BB_Middle', 'RSI']
            if not all(col in data.columns for col in required_cols):
                return 'HOLD'
            
            price = latest['Close']
            bb_upper = latest['BB_Upper']
            bb_lower = latest['BB_Lower']
            bb_middle = latest['BB_Middle']
            rsi = latest['RSI']
            
            # BUY: Price near lower band + oversold
            if price <= bb_lower and rsi < 35:
                return 'BUY'
            
            # SELL: Price near upper band + overbought
            elif price >= bb_upper and rsi > 65:
                return 'SELL'
            
            # Exit position when price returns to middle
            elif abs(price - bb_middle) / bb_middle < 0.01:
                return 'SELL'  # Close position
            
            else:
                return 'HOLD'
                
        except Exception as e:
            logger.error(f"Error generating mean reversion signals for {symbol}: {e}")
            return 'HOLD'
    
    def calculate_position_size(self, symbol: str, price: float, 
                                account_value: float) -> int:
        """Calculate position size."""
        from config import Config
        
        max_position_value = account_value * Config.MAX_POSITION_SIZE
        shares = int(max_position_value / price)
        return max(1, shares)


class MLHybridStrategy(Strategy):
    """
    Machine Learning hybrid strategy.
    Combines technical indicators with simple ML predictions.
    """
    
    def __init__(self):
        super().__init__("ML Hybrid")
        self.model = None
        self.lookback_period = 20
    
    def generate_signals(self, symbol: str, data: pd.DataFrame) -> str:
        """Generate signals using ML predictions and technical analysis."""
        if data.empty or len(data) < self.lookback_period:
            return 'HOLD'
        
        try:
            # Calculate momentum score
            latest = data.iloc[-1]
            
            score = 0
            
            # RSI score
            if 'RSI' in data.columns:
                rsi = latest['RSI']
                if rsi < 30:
                    score += 2
                elif rsi < 40:
                    score += 1
                elif rsi > 70:
                    score -= 2
                elif rsi > 60:
                    score -= 1
            
            # MACD score
            if 'MACD' in data.columns and 'MACD_Signal' in data.columns:
                if latest['MACD'] > latest['MACD_Signal']:
                    score += 1
                else:
                    score -= 1
            
            # Price trend score
            if all(col in data.columns for col in ['Close', 'SMA_20', 'SMA_50']):
                price = latest['Close']
                sma_20 = latest['SMA_20']
                sma_50 = latest['SMA_50']
                
                if price > sma_20 > sma_50:
                    score += 2
                elif price < sma_20 < sma_50:
                    score -= 2
            
            # Volume score
            if 'Volume' in data.columns and 'Volume_MA' in data.columns:
                if latest['Volume'] > latest['Volume_MA'] * 1.3:
                    score += 1
            
            # Generate signal based on score
            if score >= 4:
                return 'BUY'
            elif score <= -3:
                return 'SELL'
            else:
                return 'HOLD'
                
        except Exception as e:
            logger.error(f"Error generating ML hybrid signals for {symbol}: {e}")
            return 'HOLD'
    
    def calculate_position_size(self, symbol: str, price: float, 
                                account_value: float) -> int:
        """Calculate position size based on confidence."""
        from config import Config
        
        max_position_value = account_value * Config.MAX_POSITION_SIZE
        shares = int(max_position_value / price)
        return max(1, shares)


class StrategyFactory:
    """Factory for creating strategy instances."""
    
    @staticmethod
    def create_strategy(strategy_name: str) -> Strategy:
        """Create a strategy instance based on name."""
        strategies = {
            'momentum': MomentumStrategy,
            'mean_reversion': MeanReversionStrategy,
            'ml_hybrid': MLHybridStrategy
        }
        
        strategy_class = strategies.get(strategy_name.lower())
        if not strategy_class:
            logger.warning(f"Unknown strategy: {strategy_name}, defaulting to Momentum")
            strategy_class = MomentumStrategy
        
        return strategy_class()
