"""
Reinforcement Learning module for adaptive trading.
The bot learns from every trade to improve decision-making over time.
"""
import numpy as np
import json
import os
from typing import Dict, List, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class QLearningAgent:
    """
    Q-Learning agent that learns optimal trading actions.
    Learns which actions (BUY, SELL, HOLD) work best in different market conditions.
    """
    
    def __init__(self, learning_rate=0.1, discount_factor=0.95, epsilon=0.2):
        """
        Initialize Q-Learning agent.
        
        Args:
            learning_rate: How fast the agent learns (0-1)
            discount_factor: How much future rewards matter (0-1)
            epsilon: Exploration rate - how often to try random actions (0-1)
        """
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.epsilon = epsilon
        
        # Q-table stores learned values for state-action pairs
        self.q_table = {}
        
        # Performance tracking
        self.total_reward = 0
        self.trade_count = 0
        self.win_count = 0
        
        # Load previous learning if exists
        self.load_q_table()
        
        logger.info(f"Q-Learning agent initialized (LR={learning_rate}, DF={discount_factor}, E={epsilon})")
    
    def get_state(self, market_data: Dict) -> str:
        """
        Convert market conditions into a discrete state.
        State includes: trend, volatility, RSI level, momentum
        """
        # Extract key indicators
        rsi = market_data.get('RSI', 50)
        macd = market_data.get('MACD', 0)
        price_change = market_data.get('price_change_pct', 0)
        volume_ratio = market_data.get('volume_ratio', 1.0)
        
        # Discretize into states
        rsi_state = 'oversold' if rsi < 30 else 'overbought' if rsi > 70 else 'neutral'
        macd_state = 'bullish' if macd > 0 else 'bearish'
        trend_state = 'up' if price_change > 0.5 else 'down' if price_change < -0.5 else 'flat'
        volume_state = 'high' if volume_ratio > 1.3 else 'low' if volume_ratio < 0.7 else 'normal'
        
        # Combine into state string
        state = f"{rsi_state}_{macd_state}_{trend_state}_{volume_state}"
        return state
    
    def get_action(self, state: str, traditional_signal: str) -> str:
        """
        Choose an action (BUY, SELL, HOLD) using epsilon-greedy policy.
        
        Args:
            state: Current market state
            traditional_signal: Signal from traditional strategy
            
        Returns:
            Action to take: 'BUY', 'SELL', or 'HOLD'
        """
        # Exploration: Sometimes use traditional strategy to explore
        if np.random.random() < self.epsilon:
            logger.debug(f"Exploring: Using traditional signal {traditional_signal}")
            return traditional_signal
        
        # Exploitation: Use learned Q-values
        if state not in self.q_table:
            self.q_table[state] = {'BUY': 0.0, 'SELL': 0.0, 'HOLD': 0.0}
        
        # Choose action with highest Q-value
        q_values = self.q_table[state]
        best_action = max(q_values, key=q_values.get)
        
        logger.debug(f"State: {state}, Q-values: {q_values}, Chosen: {best_action}")
        return best_action
    
    def update_q_value(self, state: str, action: str, reward: float, next_state: str):
        """
        Update Q-value based on reward received.
        This is where learning happens!
        
        Args:
            state: Previous market state
            action: Action taken (BUY, SELL, HOLD)
            reward: Reward received (profit/loss)
            next_state: New market state after action
        """
        # Initialize states if new
        if state not in self.q_table:
            self.q_table[state] = {'BUY': 0.0, 'SELL': 0.0, 'HOLD': 0.0}
        if next_state not in self.q_table:
            self.q_table[next_state] = {'BUY': 0.0, 'SELL': 0.0, 'HOLD': 0.0}
        
        # Q-Learning update formula
        current_q = self.q_table[state][action]
        max_next_q = max(self.q_table[next_state].values())
        
        new_q = current_q + self.learning_rate * (
            reward + self.discount_factor * max_next_q - current_q
        )
        
        self.q_table[state][action] = new_q
        
        # Track performance
        self.total_reward += reward
        self.trade_count += 1
        if reward > 0:
            self.win_count += 1
        
        logger.info(f"Learning: State={state}, Action={action}, Reward={reward:.2f}, New Q={new_q:.3f}")
        
        # Save learning periodically
        if self.trade_count % 10 == 0:
            self.save_q_table()
    
    def calculate_reward(self, pnl: float, pnl_pct: float, holding_time_hours: float) -> float:
        """
        Calculate reward for reinforcement learning.
        Rewards profitable trades and penalizes losses.
        
        Args:
            pnl: Profit/loss in dollars
            pnl_pct: Profit/loss percentage
            holding_time_hours: How long position was held
            
        Returns:
            Reward value (can be positive or negative)
        """
        # Base reward from P&L percentage
        reward = pnl_pct * 100  # Scale up for better learning
        
        # Bonus for quick profitable trades
        if pnl > 0 and holding_time_hours < 4:
            reward *= 1.2
        
        # Penalty for holding losers too long
        if pnl < 0 and holding_time_hours > 24:
            reward *= 1.5  # Amplify negative reward
        
        # Small penalty for HOLD actions (encourage action)
        if pnl == 0:
            reward = -0.1
        
        return reward
    
    def save_q_table(self):
        """Save learned Q-table to disk."""
        try:
            data = {
                'q_table': self.q_table,
                'total_reward': self.total_reward,
                'trade_count': self.trade_count,
                'win_count': self.win_count,
                'timestamp': datetime.now().isoformat()
            }
            
            with open('q_learning_data.json', 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.debug("Q-table saved successfully")
        except Exception as e:
            logger.error(f"Error saving Q-table: {e}")
    
    def load_q_table(self):
        """Load previously learned Q-table from disk."""
        try:
            if os.path.exists('q_learning_data.json'):
                with open('q_learning_data.json', 'r') as f:
                    data = json.load(f)
                
                self.q_table = data.get('q_table', {})
                self.total_reward = data.get('total_reward', 0)
                self.trade_count = data.get('trade_count', 0)
                self.win_count = data.get('win_count', 0)
                
                logger.info(f"Loaded Q-table: {len(self.q_table)} states, {self.trade_count} trades learned")
        except Exception as e:
            logger.warning(f"Could not load Q-table: {e}")
    
    def get_performance_stats(self) -> Dict:
        """Get learning performance statistics."""
        win_rate = (self.win_count / self.trade_count * 100) if self.trade_count > 0 else 0
        avg_reward = self.total_reward / self.trade_count if self.trade_count > 0 else 0
        
        return {
            'states_learned': len(self.q_table),
            'total_trades': self.trade_count,
            'winning_trades': self.win_count,
            'win_rate': win_rate,
            'total_reward': self.total_reward,
            'avg_reward': avg_reward,
            'exploration_rate': self.epsilon
        }
    
    def adjust_exploration(self, performance: float):
        """
        Dynamically adjust exploration rate based on performance.
        Explore more if doing poorly, exploit more if doing well.
        """
        if performance < 0.4:  # Poor performance
            self.epsilon = min(0.3, self.epsilon + 0.05)
            logger.info(f"Increasing exploration to {self.epsilon:.2f}")
        elif performance > 0.6:  # Good performance
            self.epsilon = max(0.1, self.epsilon - 0.05)
            logger.info(f"Decreasing exploration to {self.epsilon:.2f}")


class AdaptiveStrategySelector:
    """
    Learns which strategy (Momentum, Mean Reversion, ML Hybrid) works best.
    Automatically switches strategies based on market conditions.
    """
    
    def __init__(self):
        self.strategy_performance = {
            'momentum': {'wins': 0, 'losses': 0, 'total_pnl': 0},
            'mean_reversion': {'wins': 0, 'losses': 0, 'total_pnl': 0},
            'ml_hybrid': {'wins': 0, 'losses': 0, 'total_pnl': 0}
        }
        self.current_strategy = 'momentum'
        self.evaluation_period = 20  # Evaluate every 20 trades
        self.trades_since_eval = 0
        
        self.load_performance()
    
    def record_trade(self, strategy: str, pnl: float):
        """Record trade result for a strategy."""
        if strategy in self.strategy_performance:
            if pnl > 0:
                self.strategy_performance[strategy]['wins'] += 1
            else:
                self.strategy_performance[strategy]['losses'] += 1
            
            self.strategy_performance[strategy]['total_pnl'] += pnl
            self.trades_since_eval += 1
            
            if self.trades_since_eval >= self.evaluation_period:
                self.select_best_strategy()
                self.trades_since_eval = 0
            
            self.save_performance()
    
    def select_best_strategy(self):
        """Select strategy with best performance."""
        best_strategy = None
        best_score = float('-inf')
        
        for strategy, perf in self.strategy_performance.items():
            total_trades = perf['wins'] + perf['losses']
            if total_trades == 0:
                continue
            
            win_rate = perf['wins'] / total_trades
            avg_pnl = perf['total_pnl'] / total_trades
            
            # Score combines win rate and average P&L
            score = win_rate * 0.5 + (avg_pnl / 100) * 0.5
            
            if score > best_score:
                best_score = score
                best_strategy = strategy
        
        if best_strategy and best_strategy != self.current_strategy:
            logger.info(f"Switching strategy from {self.current_strategy} to {best_strategy}")
            self.current_strategy = best_strategy
        
        return self.current_strategy
    
    def save_performance(self):
        """Save strategy performance data."""
        try:
            with open('strategy_performance.json', 'w') as f:
                json.dump({
                    'performance': self.strategy_performance,
                    'current_strategy': self.current_strategy
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving strategy performance: {e}")
    
    def load_performance(self):
        """Load strategy performance data."""
        try:
            if os.path.exists('strategy_performance.json'):
                with open('strategy_performance.json', 'r') as f:
                    data = json.load(f)
                    self.strategy_performance = data.get('performance', self.strategy_performance)
                    self.current_strategy = data.get('current_strategy', 'momentum')
                    logger.info(f"Loaded strategy performance, using: {self.current_strategy}")
        except Exception as e:
            logger.warning(f"Could not load strategy performance: {e}")
