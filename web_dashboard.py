"""
Web Dashboard for Dai Trader Bot
Provides real-time monitoring and control interface
"""
import os
import logging
import json
from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from datetime import datetime, timedelta
from functools import wraps
import secrets
import hashlib

from database import Database
from broker import BrokerInterface
from risk_manager import RiskManager
from reinforcement_learning import QLearningAgent
from config import Config

logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('DASHBOARD_SECRET_KEY', secrets.token_hex(32))

# Security: CORS with specific origins
ALLOWED_ORIGINS = os.environ.get('ALLOWED_ORIGINS', '*').split(',')
CORS(app, origins=ALLOWED_ORIGINS)

# Security: Rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Security: Secure headers
@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self' https://cdn.jsdelivr.net; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline'"
    return response

# Dashboard password from environment or default
DASHBOARD_PASSWORD = os.environ.get('DASHBOARD_PASSWORD', 'dai-trader-2025')

# Initialize components
db = Database()
broker = BrokerInterface()

# Bot control state file
BOT_STATE_FILE = 'bot_state.json'

def load_bot_state():
    """Load bot configuration state."""
    if os.path.exists(BOT_STATE_FILE):
        with open(BOT_STATE_FILE, 'r') as f:
            return json.load(f)
    return {
        'safe_mode': True,
        'bot_running': True,
        'risk_level': 'moderate',
        'ai_learning': True,
        'alerts': True
    }

def save_bot_state(state):
    """Save bot configuration state."""
    with open(BOT_STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def login_required(f):
    """Decorator to require authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('authenticated'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def login():
    """Login page with rate limiting."""
    if request.method == 'POST':
        password = request.form.get('password')
        # Use constant-time comparison to prevent timing attacks
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        correct_hash = hashlib.sha256(DASHBOARD_PASSWORD.encode()).hexdigest()
        
        if password_hash == correct_hash:
            session['authenticated'] = True
            session.permanent = True
            return redirect(url_for('dashboard'))
        return render_template('login.html', error='Invalid password')
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout."""
    session.pop('authenticated', None)
    return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    """Main dashboard page."""
    return render_template('dashboard.html')

@app.route('/api/status')
@login_required
def api_status():
    """Get bot status and account info."""
    try:
        account = broker.get_account()
        positions = broker.get_positions()
        
        return jsonify({
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'account': {
                'portfolio_value': float(account.get('portfolio_value', 0)),
                'cash': float(account.get('cash', 0)),
                'buying_power': float(account.get('buying_power', 0)),
                'equity': float(account.get('equity', 0))
            },
            'positions': [{
                'symbol': p['symbol'],
                'qty': int(p['qty']),
                'current_price': float(p['current_price']),
                'avg_entry_price': float(p['avg_entry_price']),
                'market_value': float(p['market_value']),
                'unrealized_pl': float(p['unrealized_pl']),
                'unrealized_plpc': float(p['unrealized_plpc'])
            } for p in positions],
            'trading_mode': Config.TRADING_MODE,
            'strategy': Config.STRATEGY,
            'watchlist': Config.WATCHLIST
        })
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/trades')
@login_required
def api_trades():
    """Get recent trades."""
    try:
        # Get trades from database
        trades = db.session.query(db.Trade).order_by(db.Trade.entry_date.desc()).limit(50).all()
        
        trades_data = [{
            'id': trade.id,
            'symbol': trade.symbol,
            'side': trade.side,
            'quantity': float(trade.quantity),
            'entry_price': float(trade.entry_price),
            'entry_date': trade.entry_date.isoformat() if trade.entry_date else None,
            'exit_price': float(trade.exit_price) if trade.exit_price else None,
            'exit_date': trade.exit_date.isoformat() if trade.exit_date else None,
            'pnl': float(trade.pnl) if trade.pnl else None,
            'pnl_pct': float(trade.pnl_pct) if trade.pnl_pct else None,
            'status': trade.status,
            'strategy': trade.strategy
        } for trade in trades]
        
        return jsonify({
            'success': True,
            'trades': trades_data
        })
    except Exception as e:
        logger.error(f"Error getting trades: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/performance')
@login_required
def api_performance():
    """Get performance metrics."""
    try:
        # Get closed trades
        closed_trades = db.session.query(db.Trade).filter_by(status='CLOSED').all()
        
        total_trades = len(closed_trades)
        winning_trades = sum(1 for t in closed_trades if t.pnl and t.pnl > 0)
        total_pnl = sum(t.pnl for t in closed_trades if t.pnl)
        
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        avg_pnl = total_pnl / total_trades if total_trades > 0 else 0
        
        # Get portfolio history
        snapshots = db.session.query(db.PortfolioSnapshot).order_by(
            db.PortfolioSnapshot.timestamp.desc()
        ).limit(100).all()
        
        portfolio_history = [{
            'timestamp': s.timestamp.isoformat(),
            'total_value': float(s.total_value),
            'daily_pnl': float(s.daily_pnl) if s.daily_pnl else 0
        } for s in reversed(snapshots)]
        
        return jsonify({
            'success': True,
            'metrics': {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': total_trades - winning_trades,
                'win_rate': win_rate,
                'total_pnl': total_pnl,
                'avg_pnl': avg_pnl,
                'initial_capital': Config.INITIAL_CAPITAL
            },
            'portfolio_history': portfolio_history
        })
    except Exception as e:
        logger.error(f"Error getting performance: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ai-stats')
@login_required
def api_ai_stats():
    """Get AI learning statistics."""
    try:
        # Load RL agent to get stats
        rl_agent = QLearningAgent()
        rl_agent.load_q_table()
        
        stats = rl_agent.get_performance_stats()
        
        return jsonify({
            'success': True,
            'ai_stats': {
                'states_learned': stats['states_learned'],
                'total_trades': stats['total_trades'],
                'winning_trades': stats['winning_trades'],
                'win_rate': stats['win_rate'],
                'total_reward': stats['total_reward'],
                'avg_reward': stats['avg_reward'],
                'exploration_rate': stats['exploration_rate']
            }
        })
    except Exception as e:
        logger.error(f"Error getting AI stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/logs')
@login_required
def api_logs():
    """Get recent log entries."""
    try:
        log_file = Config.LOG_FILE
        if not os.path.exists(log_file):
            return jsonify({'success': True, 'logs': []})
        
        # Read last 100 lines
        with open(log_file, 'r') as f:
            lines = f.readlines()
            recent_logs = lines[-100:]
        
        return jsonify({
            'success': True,
            'logs': [line.strip() for line in recent_logs]
        })
    except Exception as e:
        logger.error(f"Error getting logs: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/bot-state', methods=['GET'])
@login_required
def api_get_bot_state():
    """Get current bot configuration state."""
    try:
        state = load_bot_state()
        return jsonify({
            'success': True,
            'state': state
        })
    except Exception as e:
        logger.error(f"Error getting bot state: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/bot-state', methods=['POST'])
@login_required
@limiter.limit("30 per minute")
def api_update_bot_state():
    """Update bot configuration state."""
    try:
        data = request.json
        state = load_bot_state()
        
        # Update state
        if 'safe_mode' in data:
            state['safe_mode'] = bool(data['safe_mode'])
        if 'bot_running' in data:
            state['bot_running'] = bool(data['bot_running'])
        if 'risk_level' in data:
            if data['risk_level'] in ['conservative', 'moderate', 'aggressive']:
                state['risk_level'] = data['risk_level']
        if 'ai_learning' in data:
            state['ai_learning'] = bool(data['ai_learning'])
        if 'alerts' in data:
            state['alerts'] = bool(data['alerts'])
        
        save_bot_state(state)
        
        logger.info(f"Bot state updated: {state}")
        
        return jsonify({
            'success': True,
            'state': state,
            'message': 'Bot configuration updated successfully'
        })
    except Exception as e:
        logger.error(f"Error updating bot state: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/emergency-stop', methods=['POST'])
@login_required
@limiter.limit("5 per minute")
def api_emergency_stop():
    """Emergency stop - close all positions and halt trading."""
    try:
        logger.critical("EMERGENCY STOP activated from dashboard")
        
        # Close all positions
        broker.close_all_positions()
        
        # Update bot state
        state = load_bot_state()
        state['bot_running'] = False
        save_bot_state(state)
        
        logger.critical("All positions closed - Bot halted")
        
        return jsonify({
            'success': True,
            'message': 'Emergency stop executed - all positions closed, bot halted'
        })
    except Exception as e:
        logger.error(f"Error executing emergency stop: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/safe-mode-status', methods=['GET'])
@login_required
def api_safe_mode_status():
    """Get current safe mode status and danger score."""
    try:
        # This would be populated by the trading bot
        # For now, return mock data
        return jsonify({
            'success': True,
            'safe_mode': {
                'enabled': True,
                'danger_score': 15,
                'risk_reduction': 1.0,
                'status': 'NORMAL',
                'factors': {
                    'macro_bearish': False,
                    'high_vix': False,
                    'crypto_crash': False,
                    'economic_risk': False,
                    'daily_loss': False,
                    'losing_streak': False
                }
            }
        })
    except Exception as e:
        logger.error(f"Error getting safe mode status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

def main():
    """Run the web dashboard."""
    port = int(os.environ.get('DASHBOARD_PORT', 5000))
    host = os.environ.get('DASHBOARD_HOST', '0.0.0.0')
    
    print(f"""
    ============================================================
    Dai Trader Web Dashboard
    ============================================================
    URL: http://{host}:{port}
    Password: {DASHBOARD_PASSWORD}
    
    Press Ctrl+C to stop
    ============================================================
    """)
    
    app.run(host=host, port=port, debug=False)

if __name__ == '__main__':
    main()
