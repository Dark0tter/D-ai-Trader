# Dai Trader - Autonomous Day Trading AI

A fully autonomous day trading system that handles everything from market analysis to order execution. Just configure your preferences, add capital, and let it trade for you.

## 🚀 Features

- **Fully Autonomous**: Set it and forget it - handles all trading decisions
- **Multiple Strategies**: Momentum, Mean Reversion, and ML Hybrid strategies
- **Risk Management**: Built-in stop losses, take profits, and position sizing
- **Paper Trading**: Test strategies safely before going live
- **Real-time Monitoring**: Track performance with comprehensive logging
- **Backtesting**: Test strategies on historical data before deploying
- **Database Tracking**: Complete trade history and analytics
- **Smart Position Management**: Automatic trailing stops and profit taking

## 📋 Prerequisites

- Python 3.8 or higher
- Alpaca trading account (free paper trading account available at [alpaca.markets](https://alpaca.markets))
- Basic understanding of trading risks

## 🔧 Installation

### 1. Clone or Download

Download this project to your local machine.

### 2. Install Dependencies

```powershell
# Create a virtual environment (recommended)
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install required packages
pip install -r requirements.txt
```

**Note**: `ta-lib` may require additional steps on Windows:
- Download the appropriate wheel file from [here](https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib)
- Install: `pip install TA_Lib-0.4.XX-cpXXX-cpXXX-win_amd64.whl`

### 3. Configure Environment

```powershell
# Copy the example environment file
copy .env.example .env

# Edit .env with your settings
notepad .env
```

### 4. Get Alpaca API Keys

1. Sign up at [alpaca.markets](https://alpaca.markets)
2. Navigate to "Paper Trading" section
3. Generate API keys
4. Add them to your `.env` file:
   ```
   ALPACA_API_KEY=your_key_here
   ALPACA_SECRET_KEY=your_secret_here
   ALPACA_PAPER=True
   ```

## ⚙️ Configuration

Edit `.env` to customize your trading bot:

### Capital Settings
```
INITIAL_CAPITAL=10000.00          # Starting capital
MAX_POSITION_SIZE=0.1             # Max 10% per position
RISK_PER_TRADE=0.01              # Risk 1% per trade
```

### Trading Strategy
```
STRATEGY=momentum                 # Options: momentum, mean_reversion, ml_hybrid
WATCHLIST=AAPL,MSFT,GOOGL,TSLA   # Stocks to trade
```

### Risk Management
```
USE_STOP_LOSS=True
STOP_LOSS_PCT=0.02               # 2% stop loss
USE_TAKE_PROFIT=True
TAKE_PROFIT_PCT=0.04             # 4% take profit
MAX_DAILY_LOSS=0.02              # Stop if down 2% for the day
```

## 🚀 Usage

### Run the Trading Bot

```powershell
python trading_bot.py
```

The bot will:
- ✅ Connect to your broker account
- ✅ Monitor market hours
- ✅ Scan your watchlist for opportunities
- ✅ Execute trades based on your strategy
- ✅ Manage positions with stop losses and take profits
- ✅ Log all activity to console and file

### Backtest a Strategy

Before going live, test your strategy on historical data:

```powershell
python -c "from backtester import Backtester; bt = Backtester('momentum', 10000); bt.run_backtest(['AAPL', 'MSFT'], '2024-01-01')"
```

This will show you how the strategy would have performed with your settings.

## 📊 Available Strategies

### 1. Momentum Strategy
Trades based on price momentum and trend following:
- Uses RSI, MACD, and moving averages
- Buys strong uptrends, sells on reversals
- Best for trending markets

### 2. Mean Reversion Strategy
Assumes prices revert to their average:
- Uses Bollinger Bands and RSI
- Buys oversold, sells overbought
- Best for ranging markets

### 3. ML Hybrid Strategy
Combines multiple indicators with scoring:
- Weighted scoring system
- Adapts to different market conditions
- Balanced approach

## 📁 Project Structure

```
Dai Trader/
├── trading_bot.py         # Main bot orchestrator
├── config.py              # Configuration management
├── data_fetcher.py        # Market data fetching
├── broker.py              # Broker integration (Alpaca)
├── strategies.py          # Trading strategies
├── risk_manager.py        # Risk management
├── backtester.py          # Backtesting framework
├── logger.py              # Logging and monitoring
├── database.py            # Trade history database
├── requirements.txt       # Python dependencies
├── .env                   # Your configuration (create from .env.example)
└── README.md             # This file
```

## 🛡️ Safety Features

- **Paper Trading Mode**: Test without real money
- **Daily Loss Limits**: Automatically stops trading if daily loss limit hit
- **Position Size Limits**: Never risk too much on one trade
- **Stop Losses**: Automatic exit on adverse moves
- **Market Hours Check**: Only trades during market hours
- **Comprehensive Logging**: Full audit trail of all actions

## 📈 Monitoring

The bot provides real-time logging:

```
2025-11-16 09:35:00 - INFO - Running trading cycle...
2025-11-16 09:35:01 - INFO - Portfolio Value: $10,234.50
2025-11-16 09:35:05 - INFO - BUY executed: 10 shares of AAPL at $150.25
2025-11-16 09:35:05 - INFO - Stop Loss: $147.25, Take Profit: $156.26
```

View logs in:
- Console (real-time colored output)
- `logs/trading_bot.log` (detailed file log)

## 📊 Performance Tracking

Check your performance:
- End-of-day summaries automatically generated
- Database tracks all trades: `trading_bot.db`
- Performance metrics: win rate, P&L, Sharpe ratio

## ⚠️ Important Warnings

1. **Trading involves risk**: You can lose money. Start with paper trading.
2. **No guarantees**: Past performance doesn't guarantee future results.
3. **Monitor regularly**: Even autonomous bots should be supervised.
4. **Start small**: Begin with small amounts until comfortable.
5. **Test thoroughly**: Use backtesting and paper trading first.

## 🔄 Going from Paper to Live Trading

When you're ready to trade with real money:

1. Generate live trading API keys from Alpaca
2. Update `.env`:
   ```
   ALPACA_PAPER=False
   TRADING_MODE=live
   ```
3. **Start with small amounts**
4. Monitor closely for the first few days

## 🛠️ Customization

### Add Your Own Strategy

```python
# In strategies.py, create a new class:
class MyCustomStrategy(Strategy):
    def generate_signals(self, symbol, data):
        # Your logic here
        return 'BUY'  # or 'SELL' or 'HOLD'
    
    def calculate_position_size(self, symbol, price, account_value):
        # Your sizing logic
        return shares
```

Then update `.env`:
```
STRATEGY=my_custom
```

### Modify Watchlist

Edit `.env`:
```
WATCHLIST=AAPL,MSFT,GOOGL,TSLA,NVDA,AMD,META,AMZN,NFLX,DIS
```

## 🐛 Troubleshooting

### Bot won't start
- Check API keys are correct in `.env`
- Verify all dependencies installed: `pip install -r requirements.txt`

### No trades being placed
- Confirm market is open (Mon-Fri, 9:30 AM - 4:00 PM ET)
- Check if daily loss limit was hit
- Review strategy signals are generating

### Import errors
- Ensure virtual environment is activated
- Reinstall dependencies: `pip install -r requirements.txt --upgrade`

## 📚 Resources

- [Alpaca API Documentation](https://alpaca.markets/docs/)
- [Technical Analysis Library](https://technical-analysis-library-in-python.readthedocs.io/)
- [Quantitative Trading Guide](https://www.quantstart.com/)

## 📝 License

This is for personal use only. Use at your own risk.

## 🤝 Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the logs in `logs/trading_bot.log`
3. Ensure your `.env` configuration is correct

## 🎯 Quick Start Summary

```powershell
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure
copy .env.example .env
notepad .env  # Add your Alpaca keys

# 3. Backtest (optional but recommended)
python -c "from backtester import Backtester; bt = Backtester('momentum', 10000); bt.run_backtest(['AAPL'], '2024-01-01')"

# 4. Run in paper trading mode
python trading_bot.py
```

---

**Remember**: This bot trades autonomously based on your configuration. Always start with paper trading and thoroughly test before using real money. Trading involves substantial risk of loss.
