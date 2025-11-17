"""
Main trading bot orchestrator.
Coordinates all components and runs autonomously.
"""
import time
import schedule
from datetime import datetime
from typing import List, Dict
import logging

from config import Config
from data_fetcher import MarketData
from broker import BrokerInterface
from strategies import StrategyFactory
from risk_manager import RiskManager
from logger import setup_logging, PerformanceTracker, AlertSystem
from database import Database
from reinforcement_learning import QLearningAgent, AdaptiveStrategySelector
from overnight_analyzer import OvernightPatternAnalyzer

logger = logging.getLogger(__name__)

class TradingBot:
    """Main autonomous trading bot."""
    
    def __init__(self):
        """Initialize trading bot with all components."""
        # Setup logging
        setup_logging(Config.LOG_LEVEL, Config.LOG_FILE)
        logger.info("="*60)
        logger.info("Initializing Dai Trader Bot")
        logger.info("="*60)
        
        # Validate configuration
        Config.validate()
        
        # Initialize components
        self.market_data = MarketData()
        self.broker = BrokerInterface()
        self.strategy = StrategyFactory.create_strategy(Config.STRATEGY)
        self.risk_manager = RiskManager()
        self.performance_tracker = PerformanceTracker()
        self.alert_system = AlertSystem()
        self.database = Database()
        
        # Reinforcement Learning components
        self.rl_agent = QLearningAgent(learning_rate=0.1, discount_factor=0.95, epsilon=0.2)
        self.strategy_selector = AdaptiveStrategySelector()
        self.overnight_analyzer = OvernightPatternAnalyzer()
        
        # State
        self.is_running = False
        self.watchlist = Config.WATCHLIST
        self.trade_states = {}  # Track states for RL learning
        
        logger.info(f"Trading Mode: {Config.TRADING_MODE}")
        logger.info(f"Strategy: {self.strategy.name}")
        logger.info(f"Watchlist: {', '.join(self.watchlist)}")
        logger.info(f"Paper Trading: {Config.is_paper_trading()}")
        logger.info(f"AI Learning: ENABLED (Q-Learning + Adaptive Strategy + Overnight Analysis)")
        logger.info("="*60)
    
    def start(self):
        """Start the trading bot."""
        logger.info("Starting Dai Trader Bot...")
        self.is_running = True
        
        # Schedule market open check
        schedule.every(1).minutes.do(self.run_trading_cycle)
        
        # Schedule end-of-day summary
        schedule.every().day.at("16:30").do(self.end_of_day_summary)
        
        # Run initial check
        self.run_trading_cycle()
        
        # Main loop
        try:
            while self.is_running:
                schedule.run_pending()
                time.sleep(30)  # Check every 30 seconds
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
            self.stop()
    
    def run_trading_cycle(self):
        """Execute one trading cycle."""
        try:
            # Check if market is open
            market_status = self.market_data.get_market_status()
            
            if not market_status['is_open']:
                logger.debug("Market is closed, running observation mode")
                self.observation_mode()
                return
            
            logger.info("Running trading cycle...")
            
            # Get account information
            account = self.broker.get_account()
            if not account:
                logger.error("Failed to get account information")
                return
            
            account_value = account['portfolio_value']
            logger.info(f"Portfolio Value: ${account_value:,.2f}")
            
            # Check risk limits
            can_trade, reason = self.risk_manager.can_trade(account_value)
            if not can_trade:
                self.alert_system.risk_alert(reason)
                logger.warning(f"Trading halted: {reason}")
                return
            
            # Update positions with stop loss/take profit checks
            self.manage_positions(account_value)
            
            # Scan watchlist for new opportunities
            self.scan_opportunities(account_value)
            
            # Save portfolio snapshot
            self.save_portfolio_snapshot(account_value)
            
            logger.info("Trading cycle completed")
            
        except Exception as e:
            logger.error(f"Error in trading cycle: {e}", exc_info=True)
            self.alert_system.error_alert(f"Trading cycle error: {e}")
    
    def manage_positions(self, account_value: float):
        """Manage existing positions - check stop loss and take profit."""
        positions = self.broker.get_positions()
        
        for position in positions:
            symbol = position['symbol']
            current_price = position['current_price']
            entry_price = position['avg_entry_price']
            unrealized_pl_pct = position['unrealized_plpc']
            
            # Check if position should be closed
            should_close, reason = self.risk_manager.should_close_position(
                symbol, current_price, entry_price, unrealized_pl_pct
            )
            
            if should_close:
                logger.info(f"Closing position for {symbol}: {reason}")
                self.close_position(symbol, position)
            else:
                # Update trailing stop
                self.risk_manager.update_stop_loss_trailing(symbol, current_price, entry_price)
    
    def scan_opportunities(self, account_value: float):
        """Scan watchlist for trading opportunities."""
        # Get current positions to avoid duplicates
        positions = self.broker.get_positions()
        position_symbols = {p['symbol'] for p in positions}
        
        # Limit number of positions
        max_positions = 5
        if len(positions) >= max_positions:
            logger.info(f"Maximum positions ({max_positions}) reached, skipping scan")
            return
        
        for symbol in self.watchlist:
            if symbol in position_symbols:
                continue  # Already have a position
            
            try:
                # Get historical data with indicators
                data = self.market_data.get_historical_data(symbol, period='3mo', interval='1d')
                if data.empty:
                    continue
                
                data = self.market_data.calculate_technical_indicators(data)
                
                # Check overnight prediction for this symbol
                overnight_prediction = self.overnight_analyzer.get_next_day_prediction(symbol)
                
                # Generate traditional signal
                traditional_signal = self.strategy.generate_signals(symbol, data)
                
                # Get RL-enhanced signal
                latest = data.iloc[-1]
                market_state_data = {
                    'RSI': latest.get('RSI', 50),
                    'MACD': latest.get('MACD', 0),
                    'price_change_pct': ((latest['Close'] - data.iloc[-2]['Close']) / data.iloc[-2]['Close']) * 100,
                    'volume_ratio': latest.get('Volume', 0) / latest.get('Volume_MA', 1) if 'Volume_MA' in latest else 1.0
                }
                
                market_state = self.rl_agent.get_state(market_state_data)
                rl_signal = self.rl_agent.get_action(market_state, traditional_signal)
                
                # Combine signals with overnight prediction
                final_signal = rl_signal
                
                # If we have a high-confidence overnight prediction, use it to adjust decision
                if overnight_prediction:
                    overnight_action = overnight_prediction.get('recommended_action', 'HOLD')
                    confidence = overnight_prediction.get('confidence', 0)
                    
                    if confidence > 70:
                        # High confidence overnight prediction influences decision
                        if overnight_action == 'BUY' and rl_signal == 'HOLD':
                            final_signal = 'BUY'
                            logger.info(f"🌙 {symbol}: Overnight prediction upgraded HOLD to BUY "
                                       f"(confidence: {confidence}%)")
                        elif overnight_action == 'WAIT' and rl_signal == 'BUY':
                            final_signal = 'HOLD'
                            logger.info(f"🌙 {symbol}: Overnight prediction suggests WAIT, holding off on BUY")
                
                # Store state for learning when position closes
                if final_signal == 'BUY':
                    current_price = self.market_data.get_realtime_price(symbol)
                    if current_price:
                        self.trade_states[symbol] = {
                            'state': market_state,
                            'action': final_signal,
                            'entry_time': datetime.now(),
                            'entry_price': current_price,
                            'overnight_prediction': overnight_prediction
                        }
                        self.execute_buy(symbol, current_price, account_value)
                        
            except Exception as e:
                logger.error(f"Error scanning {symbol}: {e}")
    
    def execute_buy(self, symbol: str, price: float, account_value: float):
        """Execute a buy order."""
        try:
            # Calculate position size
            shares = self.risk_manager.calculate_position_size(
                symbol, price, account_value
            )
            
            if shares <= 0:
                logger.info(f"Position size too small for {symbol}")
                return
            
            # Place order
            order = self.broker.place_market_order(symbol, shares, 'buy')
            
            if order:
                # Calculate stop loss and take profit
                stop_loss = self.risk_manager.calculate_stop_loss(symbol, price, 'buy')
                take_profit = self.risk_manager.calculate_take_profit(symbol, price, 'buy')
                
                logger.info(f"BUY executed: {shares} shares of {symbol} at ${price:.2f}")
                logger.info(f"Stop Loss: ${stop_loss:.2f}, Take Profit: ${take_profit:.2f}")
                
                # Alert
                self.alert_system.trade_alert('BUY', symbol, shares, price)
                
                # Save to database
                self.database.save_trade({
                    'symbol': symbol,
                    'side': 'BUY',
                    'quantity': shares,
                    'entry_price': price,
                    'entry_date': datetime.now(),
                    'strategy': self.strategy.name,
                    'status': 'OPEN'
                })
                
        except Exception as e:
            logger.error(f"Error executing buy for {symbol}: {e}")
            self.alert_system.error_alert(f"Buy execution failed for {symbol}: {e}")
    
    def close_position(self, symbol: str, position: Dict):
        """Close a position."""
        try:
            # Close position via broker
            success = self.broker.close_position(symbol)
            
            if success:
                pnl = position['unrealized_pl']
                pnl_pct = position['unrealized_plpc']
                
                logger.info(f"Position closed: {symbol}, P&L: ${pnl:.2f} ({pnl_pct*100:.2f}%)")
                
                # Reinforcement Learning: Update Q-values based on trade result
                if symbol in self.trade_states:
                    trade_data = self.trade_states[symbol]
                    holding_time = (datetime.now() - trade_data['entry_time']).total_seconds() / 3600
                    
                    # Calculate reward
                    reward = self.rl_agent.calculate_reward(pnl, pnl_pct, holding_time)
                    
                    # Get new market state
                    data = self.market_data.get_historical_data(symbol, period='1d', interval='1m')
                    if not data.empty:
                        data = self.market_data.calculate_technical_indicators(data)
                        latest = data.iloc[-1]
                        new_market_data = {
                            'RSI': latest.get('RSI', 50),
                            'MACD': latest.get('MACD', 0),
                            'price_change_pct': 0,
                            'volume_ratio': 1.0
                        }
                        new_state = self.rl_agent.get_state(new_market_data)
                        
                        # Update Q-learning
                        self.rl_agent.update_q_value(
                            trade_data['state'],
                            trade_data['action'],
                            reward,
                            new_state
                        )
                    
                    # Update strategy selector
                    self.strategy_selector.record_trade(self.strategy.name.lower(), pnl)
                    
                    # Clear trade state
                    del self.trade_states[symbol]
                    
                    logger.info(f"AI Learning: Reward={reward:.3f}, Total Trades={self.rl_agent.trade_count}")
                
                # Record trade
                self.risk_manager.record_trade(symbol, pnl)
                self.performance_tracker.record_trade({
                    'symbol': symbol,
                    'pnl': pnl,
                    'pnl_pct': pnl_pct
                })
                
                # Alert
                self.alert_system.trade_alert(
                    'SELL', symbol, position['qty'], position['current_price']
                )
                
                # Update database
                trades = self.database.get_trades_by_symbol(symbol)
                if trades:
                    latest_trade = trades[-1]
                    self.database.update_trade(
                        latest_trade.id,
                        exit_price=position['current_price'],
                        exit_date=datetime.now(),
                        pnl=pnl,
                        pnl_pct=pnl_pct,
                        status='CLOSED'
                    )
                
        except Exception as e:
            logger.error(f"Error closing position for {symbol}: {e}")
    
    def observation_mode(self):
        """
        Run analytics during market closed hours.
        Analyzes market data and trains AI without executing trades.
        """
        try:
            # Only run detailed observation every 15 minutes to save resources
            current_minute = datetime.now().minute
            if current_minute % 15 != 0:
                return
            
            logger.info("🔍 Running overnight observation mode...")
            
            overnight_predictions = []
            
            # Analyze watchlist stocks
            for symbol in self.watchlist:
                try:
                    # Get recent data (even when market closed, we can analyze historical)
                    data = self.market_data.get_historical_data(symbol, period='5d', interval='1h')
                    if data.empty:
                        continue
                    
                    data = self.market_data.calculate_technical_indicators(data)
                    latest = data.iloc[-1]
                    
                    # OVERNIGHT PATTERN ANALYSIS
                    overnight_analysis = self.overnight_analyzer.analyze_overnight_movement(symbol, data)
                    if overnight_analysis:
                        prediction = overnight_analysis.get('prediction', {})
                        overnight_predictions.append({
                            'symbol': symbol,
                            'direction': prediction.get('direction', 'NEUTRAL'),
                            'confidence': prediction.get('confidence', 0),
                            'action': prediction.get('recommended_action', 'HOLD'),
                            'reasoning': prediction.get('reasoning', '')
                        })
                        
                        logger.info(f"🌙 {symbol}: Next-day prediction = {prediction.get('direction')} "
                                   f"({prediction.get('confidence')}% conf), "
                                   f"Action: {prediction.get('recommended_action')} - "
                                   f"{prediction.get('reasoning')}")
                    
                    # Create market state for AI learning
                    market_state_data = {
                        'RSI': latest.get('RSI', 50),
                        'MACD': latest.get('MACD', 0),
                        'price_change_pct': ((latest['Close'] - data.iloc[-2]['Close']) / data.iloc[-2]['Close']) * 100,
                        'volume_ratio': latest.get('Volume', 0) / latest.get('Volume_MA', 1) if 'Volume_MA' in latest else 1.0
                    }
                    
                    market_state = self.rl_agent.get_state(market_state_data)
                    
                    # Get traditional signal (for learning, not trading)
                    signal = self.strategy.generate_signals(symbol, data)
                    
                    # Let AI observe what it would do (no actual trade)
                    ai_action = self.rl_agent.get_action(market_state, signal)
                    
                    logger.debug(f"📊 {symbol}: Signal={signal}, AI would={ai_action}, RSI={market_state_data['RSI']:.1f}")
                    
                except Exception as e:
                    logger.error(f"Error analyzing {symbol} in observation mode: {e}")
            
            # Log overnight summary
            overnight_summary = self.overnight_analyzer.get_overnight_summary()
            logger.info(f"📈 Overnight Summary: {overnight_summary['bullish_predictions']} bullish, "
                       f"{overnight_summary['bearish_predictions']} bearish, "
                       f"{overnight_summary['neutral_predictions']} neutral | "
                       f"{overnight_summary['high_confidence_calls']} high-confidence calls")
            
            # Log AI learning summary
            rl_stats = self.rl_agent.get_performance_stats()
            logger.info(f"🧠 AI Learning: {rl_stats['states_learned']} states learned, "
                       f"Exploration: {rl_stats['exploration_rate']:.2%}")
            
        except Exception as e:
            logger.error(f"Error in observation mode: {e}")
    
    def save_portfolio_snapshot(self, account_value: float):
        """Save current portfolio state to database."""
        try:
            account = self.broker.get_account()
            
            self.database.save_portfolio_snapshot({
                'timestamp': datetime.now(),
                'total_value': account_value,
                'cash': account['cash'],
                'positions_value': account_value - account['cash'],
                'daily_pnl': self.risk_manager.daily_pnl,
                'total_pnl': account_value - Config.INITIAL_CAPITAL
            })
        except Exception as e:
            logger.error(f"Error saving portfolio snapshot: {e}")
    
    def end_of_day_summary(self):
        """Generate and log end-of-day summary."""
        logger.info("="*60)
        logger.info("END OF DAY SUMMARY")
        logger.info("="*60)
        
        # Account summary
        account = self.broker.get_account()
        if account:
            logger.info(f"Portfolio Value: ${account['portfolio_value']:,.2f}")
            logger.info(f"Cash: ${account['cash']:,.2f}")
            logger.info(f"Buying Power: ${account['buying_power']:,.2f}")
        
        # Performance summary
        self.performance_tracker.print_summary()
        
        # Risk summary
        risk_summary = self.risk_manager.get_risk_summary()
        logger.info(f"Daily P&L: ${risk_summary['daily_pnl']:.2f}")
        logger.info(f"Trades Today: {risk_summary['trade_count_today']}")
        
        # AI Learning summary
        rl_stats = self.rl_agent.get_performance_stats()
        logger.info("="*60)
        logger.info("AI LEARNING STATS")
        logger.info("="*60)
        logger.info(f"States Learned: {rl_stats['states_learned']}")
        logger.info(f"Total Trades Learned From: {rl_stats['total_trades']}")
        logger.info(f"AI Win Rate: {rl_stats['win_rate']:.2f}%")
        logger.info(f"Average Reward: {rl_stats['avg_reward']:.3f}")
        logger.info(f"Current Strategy: {self.strategy_selector.current_strategy}")
        logger.info(f"Exploration Rate: {rl_stats['exploration_rate']:.2f}")
        
        logger.info("="*60)
    
    def stop(self):
        """Stop the trading bot gracefully."""
        logger.info("Stopping Dai Trader Bot...")
        self.is_running = False
        
        # Close all positions if configured
        # Uncomment to auto-close positions on shutdown:
        # self.broker.close_all_positions()
        
        # Final summary
        self.end_of_day_summary()
        
        # Close database
        self.database.close()
        
        logger.info("Dai Trader Bot stopped successfully")

def main():
    """Main entry point."""
    bot = TradingBot()
    bot.start()

if __name__ == '__main__':
    main()
