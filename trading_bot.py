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
from quarterly_manager import QuarterlyManager
from overnight_analyzer import OvernightPatternAnalyzer
from news_sentiment import NewsSentimentAnalyzer
from options_flow_analyzer import OptionsFlowAnalyzer
from insider_tracker import InsiderTracker
from social_sentiment import SocialSentimentAnalyzer
from short_interest_tracker import ShortInterestTracker
from economic_calendar import EconomicCalendar
from fred_analyzer import FREDAnalyzer
from crypto_correlation import CryptoCorrelationTracker
from trends_analyzer import GoogleTrendsAnalyzer
from safe_mode import SafeMode

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
        
        # Quarterly principal protection & gain distribution
        self.quarterly_manager = QuarterlyManager()
        
        # Multi-source intelligence analyzers
        self.news_analyzer = NewsSentimentAnalyzer()
        self.options_analyzer = OptionsFlowAnalyzer()
        self.insider_tracker = InsiderTracker()
        self.social_analyzer = SocialSentimentAnalyzer()
        self.short_tracker = ShortInterestTracker()
        self.economic_calendar = EconomicCalendar()
        self.fred_analyzer = FREDAnalyzer()
        self.crypto_tracker = CryptoCorrelationTracker()
        self.trends_analyzer = GoogleTrendsAnalyzer()
        
        # Safe Mode - Automatic risk protection
        self.safe_mode = SafeMode()
        
        # State
        self.is_running = False
        self.watchlist = Config.WATCHLIST
        self.trade_states = {}  # Track states for RL learning
        
        # Get quarterly status
        q_status = self.quarterly_manager.get_status()
        
        logger.info(f"Trading Mode: {Config.TRADING_MODE}")
        logger.info(f"Strategy: {self.strategy.name}")
        logger.info(f"Watchlist: {', '.join(self.watchlist)}")
        logger.info(f"Paper Trading: {Config.is_paper_trading()}")
        logger.info(f"AI Learning: ENABLED (Q-Learning + Adaptive Strategy)")
        logger.info(f"Intelligence Sources: 10+ APIs (News, Options, Insiders, Social, Economic, Crypto, Trends)")
        logger.info(f"Quarterly Protection: {q_status['quarter']} | Daily Floor: ${q_status['daily_floor']:,.2f} | Recovery Mode: {q_status['in_recovery_mode']}")
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
            
            # UPDATE QUARTERLY MANAGER - Track balance and calculate volatility
            q_result = self.quarterly_manager.update_balance(account_value)
            
            if q_result['in_recovery']:
                logger.warning(f"⚠️  RECOVERY MODE: Need ${q_result['recovery_needed']:.2f} to reach today's floor ${q_result['daily_floor']:.2f}")
            elif q_result['can_distribute']:
                logger.info(f"📈 Above Floor: Today's Gains=${q_result['current_gain']:.2f} | Distributable (40%)=${q_result['distributable_amount']:.2f}")
            
            # Get quarterly risk adjustment (reduces position sizes based on volatility/drawdown)
            quarterly_risk_multiplier = self.quarterly_manager.get_risk_adjustment()
            
            # SAFE MODE CHECK - Evaluate market safety
            all_intelligence = {
                'macro': self.fred_analyzer.get_economic_regime(),
                'crypto': self.crypto_tracker.get_crypto_sentiment(),
                'economic': self.economic_calendar.get_todays_events()
            }
            
            account_performance = {
                'daily_pnl_pct': 0,  # TODO: Calculate from database
                'losing_streak': 0   # TODO: Calculate from recent trades
            }
            
            is_safe, safe_reason, risk_reduction = self.safe_mode.evaluate_market_safety(
                all_intelligence, account_performance
            )
            
            # Check for emergency exit
            should_emergency_exit, exit_reason = self.safe_mode.should_close_all_positions(
                all_intelligence, account_performance
            )
            
            if should_emergency_exit:
                logger.critical(exit_reason)
                logger.critical("🚨 CLOSING ALL POSITIONS IMMEDIATELY")
                self.broker.close_all_positions()
                self.alert_system.risk_alert(exit_reason)
                return
            
            # Log safe mode status
            if risk_reduction < 1.0:
                logger.warning(safe_reason)
                logger.warning(f"💰 Position sizing reduced to {risk_reduction*100:.0f}%")
            
            # Combine Safe Mode and Quarterly risk adjustments
            combined_risk_multiplier = risk_reduction * quarterly_risk_multiplier
            
            if quarterly_risk_multiplier < 1.0:
                logger.warning(f"📊 Quarterly risk adjustment: {quarterly_risk_multiplier*100:.0f}% (volatility/drawdown protection)")
            
            logger.info(f"🎯 Combined risk multiplier: {combined_risk_multiplier*100:.0f}%")
            
            # Check risk limits
            can_trade, reason = self.risk_manager.can_trade(account_value)
            if not can_trade:
                self.alert_system.risk_alert(reason)
                logger.warning(f"Trading halted: {reason}")
                return
            
            # Update positions with stop loss/take profit checks
            self.manage_positions(account_value)
            
            # Scan watchlist for new opportunities (with combined risk reduction)
            self.scan_opportunities(account_value, combined_risk_multiplier)
            
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
    
    def scan_opportunities(self, account_value: float, safe_mode_reduction: float = 1.0):
        """Scan watchlist for trading opportunities."""
        # Get current positions to avoid duplicates
        positions = self.broker.get_positions()
        position_symbols = {p['symbol'] for p in positions}
        
        # Portfolio allocation by risk tier (NO POSITION LIMITS)
        # 20% High Risk - short-term plays, high conviction
        # 30% Medium Risk - swing trades, moderate conviction
        # 50% Low Risk - long-term holds, stable growth
        # Bot can take unlimited positions, but capital is allocated by risk tier
        
        # Apply safe mode reduction to all allocations
        if safe_mode_reduction == 0.0:
            logger.warning("🚫 SAFE MODE: No new trades allowed")
            return
        
        for symbol in self.watchlist:
            if symbol in position_symbols:
                continue  # Already have a position
            
            try:
                # CHECK NEWS SENTIMENT FIRST - Avoid trading on bad news
                should_avoid, avoid_reason = self.news_analyzer.should_avoid_trading(symbol)
                if should_avoid:
                    logger.warning(f"📰 {symbol}: Avoiding trade - {avoid_reason}")
                    continue
                
                # Get historical data with indicators
                data = self.market_data.get_historical_data(symbol, period='3mo', interval='1d')
                if data.empty:
                    continue
                
                data = self.market_data.calculate_technical_indicators(data)
                
                # UNIFIED INTELLIGENCE GATHERING - Collect all data sources
                intelligence = self.gather_intelligence(symbol, data)
                
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
                
                # UNIFIED DECISION ENGINE - Combine all intelligence sources
                final_signal, confidence_score = self.make_intelligent_decision(
                    symbol, rl_signal, intelligence
                )
                
                # Store state for learning when position closes
                if final_signal == 'BUY':
                    current_price = self.market_data.get_realtime_price(symbol)
                    if current_price:
                        # Calculate unified position size boost from all sources
                        unified_boost = self.calculate_unified_boost(intelligence)
                        
                        # Determine risk tier based on intelligence confidence
                        risk_tier = self.classify_risk_tier(confidence_score, intelligence)
                        
                        self.trade_states[symbol] = {
                            'state': market_state,
                            'action': final_signal,
                            'entry_time': datetime.now(),
                            'entry_price': current_price,
                            'intelligence': intelligence,
                            'confidence_score': confidence_score,
                            'position_boost': unified_boost,
                            'risk_tier': risk_tier
                        }
                        self.execute_buy(symbol, current_price, account_value, unified_boost, risk_tier, safe_mode_reduction)
                        
            except Exception as e:
                logger.error(f"Error scanning {symbol}: {e}")
    
    def execute_buy(self, symbol: str, price: float, account_value: float, 
                    sentiment_boost: float = 1.0, risk_tier: str = 'MEDIUM', 
                    safe_mode_reduction: float = 1.0):
        """Execute a buy order with risk-based position sizing."""
        try:
            # Risk-based capital allocation (NO POSITION LIMITS)
            # HIGH RISK: 20% of total capital
            # MEDIUM RISK: 30% of total capital
            # LOW RISK: 50% of total capital
            
            # Calculate how much capital is allocated to each risk tier
            base_allocation = {
                'HIGH': account_value * 0.20,    # 20% of total capital
                'MEDIUM': account_value * 0.30,  # 30% of total capital
                'LOW': account_value * 0.50      # 50% of total capital
            }
            
            # Apply safe mode reduction
            risk_capital_allocation = {
                tier: amount * safe_mode_reduction 
                for tier, amount in base_allocation.items()
            }
            
            # Get current positions to calculate used capital per tier
            positions = self.broker.get_positions()
            used_capital = {'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
            
            for pos in positions:
                pos_tier = self.trade_states.get(pos['symbol'], {}).get('risk_tier', 'MEDIUM')
                used_capital[pos_tier] += abs(pos['market_value'])
            
            # Check if we have capital available in this risk tier
            available_capital = risk_capital_allocation[risk_tier] - used_capital[risk_tier]
            
            if available_capital <= 0:
                logger.info(f"🚫 {symbol}: No capital available in {risk_tier} RISK tier "
                           f"(${used_capital[risk_tier]:,.0f} / ${risk_capital_allocation[risk_tier]:,.0f} used)")
                return
            
            # Calculate position size (use 2% risk per trade within available capital)
            max_position_value = min(available_capital * 0.10, available_capital)  # 10% of available or all available
            base_shares = int(max_position_value / price)
            
            # Apply intelligence boost
            shares = int(base_shares * sentiment_boost)
            
            if shares <= 0:
                logger.info(f"Position size too small for {symbol}")
                return
            
            position_value = shares * price
            tier_usage_pct = (used_capital[risk_tier] + position_value) / risk_capital_allocation[risk_tier] * 100
            
            logger.info(f"🎯 {symbol}: {risk_tier} RISK tier - ${position_value:,.0f} "
                       f"({tier_usage_pct:.1f}% of {risk_tier} allocation)")
            if sentiment_boost != 1.0:
                logger.info(f"📊 {symbol}: Intelligence boost: {sentiment_boost:.2f}x "
                           f"({base_shares} → {shares} shares)")
            
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
        
        # Multi-source Intelligence Summary
        logger.info("="*60)
        logger.info("MULTI-SOURCE INTELLIGENCE SUMMARY")
        logger.info("="*60)
        
        # News sentiment
        news_summary = self.news_analyzer.get_news_summary(self.watchlist)
        logger.info(f"📰 News - Bullish: {len(news_summary['bullish_symbols'])}, Bearish: {len(news_summary['bearish_symbols'])}")
        
        # Options flow
        options_summary = self.options_analyzer.get_summary(self.watchlist)
        logger.info(f"📊 Options - Bullish Flows: {len(options_summary['bullish_signals'])}, "
                   f"Whale Activity: {len(options_summary['whale_activity'])}")
        
        # Insider trading
        insider_summary = self.insider_tracker.get_summary(self.watchlist)
        logger.info(f"👔 Insiders - Buying: {len(insider_summary['insider_buying'])}, "
                   f"Selling: {len(insider_summary['insider_selling'])}")
        
        # Social sentiment
        social_summary = self.social_analyzer.get_summary(self.watchlist)
        logger.info(f"💬 Social - Trending: {len(social_summary['trending'])}, "
                   f"Bullish Buzz: {len(social_summary['bullish_buzz'])}")
        
        # Short interest
        short_summary = self.short_tracker.get_summary(self.watchlist)
        logger.info(f"🔥 Short Squeeze - Active: {len(short_summary['active_squeezes'])}, "
                   f"Potential: {len(short_summary['squeeze_candidates'])}")
        
        # Economic events
        econ_events = self.economic_calendar.get_todays_events()
        logger.info(f"📅 Economic - Events Today: {econ_events['event_count']}, "
                   f"Risk Level: {econ_events['risk_level']}")
        
        # Macro regime
        macro = self.fred_analyzer.get_economic_regime()
        logger.info(f"🌍 Macro - Regime: {macro['regime']}, Confidence: {macro['confidence']}%")
        
        # Crypto sentiment
        crypto = self.crypto_tracker.get_crypto_sentiment()
        logger.info(f"₿ Crypto - Signal: {crypto['signal']}, BTC 24h: {crypto['btc_change_24h']:+.1f}%")
        
        # QUARTERLY PROTECTION SUMMARY
        logger.info("="*60)
        logger.info("DAILY RATCHETING PRINCIPAL PROTECTION")
        logger.info("="*60)
        q_status = self.quarterly_manager.get_status()
        logger.info(f"Quarter: {q_status['quarter']}")
        logger.info(f"Quarter Start Principal: ${q_status['quarter_start_principal']:,.2f}")
        logger.info(f"Today's Floor (Ratcheted): ${q_status['daily_floor']:,.2f}")
        logger.info(f"Yesterday's Floor: ${q_status['yesterday_floor']:,.2f}")
        logger.info(f"Current Balance: ${q_status['current_balance']:,.2f}")
        logger.info(f"Today's Gain: ${q_status['todays_gain']:,.2f}")
        logger.info(f"Quarter Total Gain: ${q_status['quarter_total_gain']:,.2f}")
        logger.info(f"Recovery Mode: {q_status['in_recovery_mode']}")
        
        if q_status['todays_gain'] > 0:
            distributable = q_status['todays_gain'] * 0.40
            stays_in = q_status['todays_gain'] * 0.60
            logger.info(f"💰 Available to Distribute (40% of today): ${distributable:,.2f}")
            logger.info(f"📈 Stays In System (60%): ${stays_in:,.2f} → Tomorrow's Floor")
        
        logger.info(f"Total Distributed This Quarter: ${q_status['total_distributed']:,.2f}")
        logger.info(f"Volatility Score: {q_status['volatility_score']:.1f}/100")
        logger.info(f"Max Drawdown: {q_status['max_drawdown_pct']:.2f}%")
        logger.info(f"Risk Adjustment: {q_status['risk_adjustment']*100:.0f}%")
        
        # Calculate and update volatility for next day
        recent_trades = self.database.get_recent_trades(days=5)
        if len(recent_trades) > 0:
            returns = [t.get('pnl_pct', 0) for t in recent_trades if 'pnl_pct' in t]
            if returns:
                import numpy as np
                volatility = np.std(returns) * 100  # Convert to 0-100 scale
                self.quarterly_manager.update_volatility(volatility)
                logger.info(f"📊 5-Day Volatility Updated: {volatility:.1f}")
        
        logger.info("="*60)
    
    def gather_intelligence(self, symbol: str, data) -> Dict:
        """
        Gather intelligence from all sources for a symbol
        Returns: Comprehensive intelligence dict
        """
        intelligence = {}
        
        try:
            # Overnight patterns
            intelligence['overnight'] = self.overnight_analyzer.get_next_day_prediction(symbol)
            
            # News sentiment
            intelligence['news'] = self.news_analyzer.get_news_sentiment(symbol, hours=24)
            
            # Options flow
            intelligence['options'] = self.options_analyzer.get_unusual_options_activity(symbol)
            
            # Insider trading
            intelligence['insiders'] = self.insider_tracker.get_insider_activity(symbol)
            
            # Social sentiment
            intelligence['social'] = self.social_analyzer.get_social_sentiment(symbol)
            
            # Short interest
            intelligence['short'] = self.short_tracker.get_short_interest_analysis(symbol)
            
            # Google Trends
            intelligence['trends'] = self.trends_analyzer.get_search_interest(symbol)
            
            # Economic/macro (same for all symbols, cached)
            intelligence['economic'] = self.economic_calendar.get_todays_events()
            intelligence['macro'] = self.fred_analyzer.get_economic_regime()
            intelligence['crypto'] = self.crypto_tracker.get_crypto_sentiment()
            
        except Exception as e:
            logger.error(f"Error gathering intelligence for {symbol}: {e}")
        
        return intelligence
    
    def make_intelligent_decision(self, symbol: str, rl_signal: str, 
                                  intelligence: Dict) -> tuple:
        """
        Make trading decision combining RL signal with all intelligence sources
        Returns: (final_signal, confidence_score)
        """
        final_signal = rl_signal
        confidence_score = 50  # Base confidence
        
        # Check for absolute blockers first
        
        # 1. Economic events - avoid trading on high-risk days
        if intelligence.get('economic', {}).get('avoid_trading', False):
            logger.info(f"🚫 {symbol}: Avoiding trade - {intelligence['economic']['reasons'][0]}")
            return 'HOLD', 0
        
        # 2. News - avoid on strong bearish news
        news = intelligence.get('news', {})
        should_avoid_news, news_reason = self.news_analyzer.should_avoid_trading(symbol)
        if should_avoid_news:
            logger.info(f"📰 {symbol}: {news_reason}")
            return 'HOLD', 0
        
        # Now collect bullish/bearish signals with weights
        bullish_score = 0
        bearish_score = 0
        signals_log = []
        
        # Overnight prediction (weight: 15%)
        overnight = intelligence.get('overnight', {})
        if overnight and overnight.get('confidence', 0) > 60:
            action = overnight.get('recommended_action', 'HOLD')
            conf = overnight['confidence']
            if action == 'BUY':
                bullish_score += 15 * (conf / 100)
                signals_log.append(f"🌙 Overnight BUY ({conf}%)")
            elif action == 'WAIT':
                bearish_score += 10 * (conf / 100)
                signals_log.append(f"🌙 Overnight WAIT ({conf}%)")
        
        # News sentiment (weight: 20%)
        if news.get('sentiment_label') == 'BULLISH' and news.get('confidence', 0) > 60:
            conf = news['confidence']
            bullish_score += 20 * (conf / 100)
            signals_log.append(f"📰 Bullish News ({conf}%)")
        elif news.get('sentiment_label') == 'BEARISH' and news.get('confidence', 0) > 60:
            conf = news['confidence']
            bearish_score += 15 * (conf / 100)
            signals_log.append(f"📰 Bearish News ({conf}%)")
        
        # Options flow (weight: 18%) - institutional signal
        options = intelligence.get('options', {})
        if options.get('signal') == 'BULLISH' and options.get('confidence', 0) > 65:
            conf = options['confidence']
            bullish_score += 18 * (conf / 100)
            signals_log.append(f"📊 Bullish Options ({conf}%)")
        elif options.get('signal') == 'BEARISH' and options.get('confidence', 0) > 65:
            conf = options['confidence']
            bearish_score += 18 * (conf / 100)
            signals_log.append(f"📊 Bearish Options ({conf}%)")
        
        # Insider trading (weight: 17%) - very strong signal
        insiders = intelligence.get('insiders', {})
        if insiders.get('signal') == 'BULLISH' and insiders.get('confidence', 0) > 70:
            conf = insiders['confidence']
            bullish_score += 17 * (conf / 100)
            signals_log.append(f"👔 Insider Buying ({insiders.get('buy_count', 0)} txns)")
        elif insiders.get('signal') == 'BEARISH' and insiders.get('confidence', 0) > 65:
            bearish_score += 12 * (insiders['confidence'] / 100)
            signals_log.append(f"👔 Insider Selling ({insiders.get('sell_count', 0)} txns)")
        
        # Social sentiment (weight: 12%)
        social = intelligence.get('social', {})
        if social.get('signal') == 'BULLISH' and social.get('confidence', 0) > 60:
            bullish_score += 12 * (social['confidence'] / 100)
            signals_log.append(f"💬 Social Buzz ({social.get('mentions', 0)} mentions)")
        
        # Short squeeze (weight: 10%)
        short = intelligence.get('short', {})
        if short.get('signal') == 'ACTIVE_SQUEEZE' and short.get('confidence', 0) > 65:
            bullish_score += 10 * (short['confidence'] / 100)
            signals_log.append(f"🔥 Squeeze Active ({short.get('short_float', 0)}% short)")
        
        # Google Trends (weight: 8%)
        trends = intelligence.get('trends', {})
        if trends.get('signal') == 'SURGING' and trends.get('confidence', 0) > 60:
            bullish_score += 8 * (trends['confidence'] / 100)
            signals_log.append(f"🔍 Search Surge")
        
        # Calculate final confidence and decision
        net_score = bullish_score - bearish_score
        confidence_score = int(50 + net_score)  # Base 50 + net signals
        confidence_score = max(0, min(100, confidence_score))
        
        # Decision logic
        if rl_signal == 'BUY':
            # RL wants to buy - check if intelligence agrees
            if net_score < -15:  # Strong bearish signals
                final_signal = 'HOLD'
                logger.info(f"⚠️ {symbol}: RL suggested BUY but strong bearish signals "
                           f"(score: {net_score:.1f}) - HOLDING")
            else:
                final_signal = 'BUY'
                if signals_log:
                    logger.info(f"✅ {symbol}: BUY with {confidence_score}% confidence - {', '.join(signals_log[:3])}")
        
        elif rl_signal == 'HOLD':
            # RL wants to hold - check if strong bullish signals override
            if net_score > 25:  # Very strong bullish signals
                final_signal = 'BUY'
                logger.info(f"🚀 {symbol}: Intelligence override - Upgrading to BUY "
                           f"(score: +{net_score:.1f}) - {', '.join(signals_log[:3])}")
            else:
                final_signal = 'HOLD'
        
        else:  # SELL
            final_signal = 'SELL'
        
        return final_signal, confidence_score
    
    def calculate_unified_boost(self, intelligence: Dict) -> float:
        """
        Calculate unified position size multiplier from all intelligence sources
        Returns: 0.4 to 2.0 multiplier (capped for safety)
        """
        boost = 1.0
        
        # News sentiment boost
        news_boost = self.news_analyzer.get_sentiment_boost(
            intelligence.get('news', {}).get('symbol', '')
        ) if intelligence.get('news') else 1.0
        
        # Options flow boost
        options_boost = self.options_analyzer.get_options_boost(
            intelligence.get('options', {}).get('symbol', '')
        ) if intelligence.get('options') else 1.0
        
        # Insider trading boost (strongest signal)
        insider_boost = self.insider_tracker.get_insider_boost(
            intelligence.get('insiders', {}).get('symbol', '')
        ) if intelligence.get('insiders') else 1.0
        
        # Social sentiment boost
        social_boost = self.social_analyzer.get_social_boost(
            intelligence.get('social', {}).get('symbol', '')
        ) if intelligence.get('social') else 1.0
        
        # Short squeeze boost (risky but potentially huge)
        squeeze_boost = self.short_tracker.get_squeeze_boost(
            intelligence.get('short', {}).get('symbol', '')
        ) if intelligence.get('short') else 1.0
        
        # Google Trends boost
        trends_boost = self.trends_analyzer.get_trends_boost(
            intelligence.get('trends', {}).get('symbol', '')
        ) if intelligence.get('trends') else 1.0
        
        # Economic event risk reduction
        econ_risk = self.economic_calendar.get_event_risk_factor()
        
        # Macro regime adjustment
        macro_risk = self.fred_analyzer.get_macro_risk_factor()
        
        # Crypto correlation
        crypto_risk = self.crypto_tracker.get_crypto_risk_factor()
        
        # Combine boosts (average the individual source boosts)
        individual_boosts = [news_boost, options_boost, insider_boost, social_boost, 
                            squeeze_boost, trends_boost]
        avg_boost = sum(individual_boosts) / len(individual_boosts)
        
        # Apply macro/risk adjustments
        boost = avg_boost * econ_risk * macro_risk * crypto_risk
        
        # Safety cap: 0.4x to 2.0x
        boost = max(0.4, min(2.0, boost))
        
        if boost != 1.0:
            logger.info(f"📊 Position size multiplier: {boost:.2f}x "
                       f"(News:{news_boost:.2f} Opt:{options_boost:.2f} "
                       f"Ins:{insider_boost:.2f} Soc:{social_boost:.2f} "
                       f"Macro:{macro_risk:.2f})")
        
        return boost
    
    def classify_risk_tier(self, confidence_score: int, intelligence: Dict) -> str:
        """
        Classify trade into risk tier based on intelligence confidence
        HIGH RISK: 20% allocation - Short-term plays, high volatility
        MEDIUM RISK: 30% allocation - Swing trades, moderate confidence  
        LOW RISK: 50% allocation - Long-term holds, stable growth
        """
        # Factors for HIGH RISK classification
        high_risk_factors = 0
        
        # Short squeeze active = high risk, high reward
        if intelligence.get('short', {}).get('signal') == 'ACTIVE_SQUEEZE':
            high_risk_factors += 2
        
        # Social media frenzy = high risk (retail FOMO)
        if intelligence.get('social', {}).get('mentions', 0) > 30:
            high_risk_factors += 1
        
        # Google Trends surging = high risk (momentum play)
        if intelligence.get('trends', {}).get('signal') == 'SURGING':
            high_risk_factors += 1
        
        # Factors for LOW RISK classification
        low_risk_factors = 0
        
        # Insider buying = low risk (fundamentals)
        if intelligence.get('insiders', {}).get('buy_count', 0) >= 2:
            low_risk_factors += 2
        
        # Positive macro regime = low risk environment
        if intelligence.get('macro', {}).get('regime') == 'BULLISH':
            low_risk_factors += 1
        
        # High confidence + multiple confirming signals = lower risk
        if confidence_score > 85:
            low_risk_factors += 1
        
        # Classification logic
        if high_risk_factors >= 2:
            return 'HIGH'  # Volatile, short-term opportunity
        elif low_risk_factors >= 2:
            return 'LOW'   # Stable, long-term growth
        else:
            return 'MEDIUM'  # Standard swing trade
    
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
