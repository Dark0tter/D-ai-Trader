"""
Backtesting framework for testing strategies on historical data.
"""
import pandas as pd
import numpy as np
from typing import Dict, List
from datetime import datetime
import logging
from data_fetcher import MarketData
from strategies import StrategyFactory
from config import Config

logger = logging.getLogger(__name__)

class Backtester:
    """Backtest trading strategies on historical data."""
    
    def __init__(self, strategy_name: str, initial_capital: float = 10000):
        self.strategy = StrategyFactory.create_strategy(strategy_name)
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.positions = {}
        self.trades = []
        self.equity_curve = []
        self.market_data = MarketData()
    
    def run_backtest(self, symbols: List[str], start_date: str, 
                    end_date: str = None) -> Dict:
        """
        Run backtest on given symbols and date range.
        
        Args:
            symbols: List of stock tickers
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD), defaults to today
        """
        logger.info(f"Starting backtest: {self.strategy.name} strategy")
        logger.info(f"Symbols: {symbols}, Period: {start_date} to {end_date or 'now'}")
        
        for symbol in symbols:
            self._backtest_symbol(symbol, start_date, end_date)
        
        results = self._calculate_results()
        self._print_results(results)
        return results
    
    def _backtest_symbol(self, symbol: str, start_date: str, end_date: str = None):
        """Backtest a single symbol."""
        # Fetch historical data
        data = self.market_data.get_historical_data(symbol, period='1y', interval='1d')
        
        if data.empty:
            logger.warning(f"No data available for {symbol}")
            return
        
        # Add technical indicators
        data = self.market_data.calculate_technical_indicators(data)
        
        # Filter by date range
        if start_date:
            data = data[data.index >= start_date]
        if end_date:
            data = data[data.index <= end_date]
        
        # Simulate trading
        for i in range(50, len(data)):  # Start after enough data for indicators
            current_data = data.iloc[:i+1]
            current_price = data.iloc[i]['Close']
            current_date = data.index[i]
            
            # Generate signal
            signal = self.strategy.generate_signals(symbol, current_data)
            
            # Execute trades based on signal
            if signal == 'BUY' and symbol not in self.positions:
                self._open_position(symbol, current_price, current_date)
            
            elif signal == 'SELL' and symbol in self.positions:
                self._close_position(symbol, current_price, current_date)
            
            # Update equity curve
            portfolio_value = self._calculate_portfolio_value(data.iloc[i])
            self.equity_curve.append({
                'date': current_date,
                'value': portfolio_value
            })
        
        # Close any remaining positions at the end
        if symbol in self.positions:
            final_price = data.iloc[-1]['Close']
            final_date = data.index[-1]
            self._close_position(symbol, final_price, final_date)
    
    def _open_position(self, symbol: str, price: float, date):
        """Open a new position."""
        # Calculate position size
        shares = self.strategy.calculate_position_size(symbol, price, self.capital)
        
        if shares <= 0:
            return
        
        cost = shares * price
        
        if cost > self.capital:
            shares = int(self.capital / price)
            cost = shares * price
        
        if shares > 0:
            self.positions[symbol] = {
                'shares': shares,
                'entry_price': price,
                'entry_date': date,
                'cost': cost
            }
            self.capital -= cost
            
            logger.info(f"BUY: {shares} shares of {symbol} at ${price:.2f} on {date}")
    
    def _close_position(self, symbol: str, price: float, date):
        """Close an existing position."""
        if symbol not in self.positions:
            return
        
        position = self.positions[symbol]
        shares = position['shares']
        entry_price = position['entry_price']
        
        proceeds = shares * price
        self.capital += proceeds
        
        pnl = proceeds - position['cost']
        pnl_pct = (price - entry_price) / entry_price * 100
        
        # Record trade
        self.trades.append({
            'symbol': symbol,
            'entry_date': position['entry_date'],
            'exit_date': date,
            'entry_price': entry_price,
            'exit_price': price,
            'shares': shares,
            'pnl': pnl,
            'pnl_pct': pnl_pct
        })
        
        logger.info(f"SELL: {shares} shares of {symbol} at ${price:.2f} on {date}, P&L: ${pnl:.2f} ({pnl_pct:.2f}%)")
        
        del self.positions[symbol]
    
    def _calculate_portfolio_value(self, current_data) -> float:
        """Calculate current portfolio value."""
        value = self.capital
        
        for symbol, position in self.positions.items():
            if 'Close' in current_data:
                current_price = current_data['Close']
                value += position['shares'] * current_price
        
        return value
    
    def _calculate_results(self) -> Dict:
        """Calculate backtest performance metrics."""
        if not self.trades:
            return {
                'total_trades': 0,
                'total_return': 0,
                'total_return_pct': 0,
                'win_rate': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0
            }
        
        trades_df = pd.DataFrame(self.trades)
        
        # Basic metrics
        total_trades = len(trades_df)
        winning_trades = len(trades_df[trades_df['pnl'] > 0])
        losing_trades = len(trades_df[trades_df['pnl'] < 0])
        
        total_return = self.capital - self.initial_capital
        total_return_pct = (total_return / self.initial_capital) * 100
        
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        avg_win = trades_df[trades_df['pnl'] > 0]['pnl'].mean() if winning_trades > 0 else 0
        avg_loss = trades_df[trades_df['pnl'] < 0]['pnl'].mean() if losing_trades > 0 else 0
        
        # Calculate max drawdown
        equity_df = pd.DataFrame(self.equity_curve)
        if not equity_df.empty:
            cummax = equity_df['value'].cummax()
            drawdown = (equity_df['value'] - cummax) / cummax
            max_drawdown = drawdown.min() * 100
        else:
            max_drawdown = 0
        
        # Sharpe ratio (simplified)
        if not equity_df.empty and len(equity_df) > 1:
            returns = equity_df['value'].pct_change().dropna()
            sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(252) if returns.std() > 0 else 0
        else:
            sharpe_ratio = 0
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_return': total_return,
            'total_return_pct': total_return_pct,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'final_capital': self.capital
        }
    
    def _print_results(self, results: Dict):
        """Print backtest results in a formatted way."""
        print("\n" + "="*60)
        print(f"BACKTEST RESULTS - {self.strategy.name} Strategy")
        print("="*60)
        print(f"Initial Capital:    ${self.initial_capital:,.2f}")
        print(f"Final Capital:      ${results['final_capital']:,.2f}")
        print(f"Total Return:       ${results['total_return']:,.2f} ({results['total_return_pct']:.2f}%)")
        print(f"Total Trades:       {results['total_trades']}")
        print(f"Winning Trades:     {results['winning_trades']}")
        print(f"Losing Trades:      {results['losing_trades']}")
        print(f"Win Rate:           {results['win_rate']:.2f}%")
        print(f"Average Win:        ${results['avg_win']:.2f}")
        print(f"Average Loss:       ${results['avg_loss']:.2f}")
        print(f"Max Drawdown:       {results['max_drawdown']:.2f}%")
        print(f"Sharpe Ratio:       {results['sharpe_ratio']:.2f}")
        print("="*60 + "\n")
