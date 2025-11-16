"""
Example usage scripts for the trading bot.
Run these to test different features.
"""

def run_backtest_example():
    """Example: Run a backtest on historical data."""
    from backtester import Backtester
    
    print("Running backtest example...")
    print("="*60)
    
    # Create backtester with momentum strategy
    backtester = Backtester(strategy_name='momentum', initial_capital=10000)
    
    # Run backtest on some popular stocks
    symbols = ['AAPL', 'MSFT', 'GOOGL']
    results = backtester.run_backtest(
        symbols=symbols,
        start_date='2024-01-01',
        end_date=None  # Up to today
    )
    
    print("\nBacktest completed!")
    print("Try different strategies: 'momentum', 'mean_reversion', 'ml_hybrid'")

def check_account_status():
    """Example: Check your account status."""
    from broker import BrokerInterface
    from config import Config
    
    print("Checking account status...")
    print("="*60)
    
    broker = BrokerInterface()
    account = broker.get_account()
    
    if account:
        print(f"Portfolio Value: ${account['portfolio_value']:,.2f}")
        print(f"Cash Available:  ${account['cash']:,.2f}")
        print(f"Buying Power:    ${account['buying_power']:,.2f}")
        print(f"Paper Trading:   {Config.is_paper_trading()}")
        
        # Get positions
        positions = broker.get_positions()
        if positions:
            print(f"\nOpen Positions: {len(positions)}")
            for pos in positions:
                print(f"  {pos['symbol']}: {pos['qty']} shares @ ${pos['avg_entry_price']:.2f}")
                print(f"    Current: ${pos['current_price']:.2f}, P&L: ${pos['unrealized_pl']:.2f}")
        else:
            print("\nNo open positions")
    else:
        print("Failed to connect to broker. Check your API keys in .env file")

def test_strategy_signals():
    """Example: Test strategy signals on current market data."""
    from data_fetcher import MarketData
    from strategies import StrategyFactory
    from config import Config
    
    print("Testing strategy signals...")
    print("="*60)
    
    market_data = MarketData()
    strategy = StrategyFactory.create_strategy(Config.STRATEGY)
    
    print(f"Strategy: {strategy.name}")
    print(f"Watchlist: {', '.join(Config.WATCHLIST)}\n")
    
    for symbol in Config.WATCHLIST[:5]:  # Test first 5 symbols
        # Get data
        data = market_data.get_historical_data(symbol, period='3mo', interval='1d')
        if data.empty:
            print(f"{symbol}: No data available")
            continue
        
        # Add indicators
        data = market_data.calculate_technical_indicators(data)
        
        # Generate signal
        signal = strategy.generate_signals(symbol, data)
        current_price = data.iloc[-1]['Close']
        
        print(f"{symbol}: ${current_price:.2f} - Signal: {signal}")

def view_database_stats():
    """Example: View trading history from database."""
    from database import Database
    
    print("Database Statistics...")
    print("="*60)
    
    db = Database()
    
    # Get open trades
    open_trades = db.get_open_trades()
    print(f"Open Trades: {len(open_trades)}")
    for trade in open_trades:
        print(f"  {trade.symbol}: {trade.quantity} shares @ ${trade.entry_price:.2f}")
    
    # Get latest portfolio snapshot
    snapshot = db.get_latest_portfolio_snapshot()
    if snapshot:
        print(f"\nLatest Portfolio Snapshot:")
        print(f"  Total Value: ${snapshot.total_value:,.2f}")
        print(f"  Cash: ${snapshot.cash:,.2f}")
        print(f"  Positions Value: ${snapshot.positions_value:,.2f}")
        if snapshot.total_pnl:
            print(f"  Total P&L: ${snapshot.total_pnl:,.2f}")
    
    db.close()

def main_menu():
    """Interactive menu for examples."""
    while True:
        print("\n" + "="*60)
        print("DAI TRADER - EXAMPLE SCRIPTS")
        print("="*60)
        print("1. Run Backtest")
        print("2. Check Account Status")
        print("3. Test Strategy Signals")
        print("4. View Database Stats")
        print("5. Exit")
        print("="*60)
        
        choice = input("\nEnter your choice (1-5): ").strip()
        
        if choice == '1':
            run_backtest_example()
        elif choice == '2':
            check_account_status()
        elif choice == '3':
            test_strategy_signals()
        elif choice == '4':
            view_database_stats()
        elif choice == '5':
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == '__main__':
    main_menu()
