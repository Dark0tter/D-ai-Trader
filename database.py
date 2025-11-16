"""
Database module for storing and retrieving trading data.
"""
from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import logging
from config import Config

logger = logging.getLogger(__name__)

Base = declarative_base()

class Trade(Base):
    """Trade record model."""
    __tablename__ = 'trades'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), nullable=False)
    side = Column(String(4), nullable=False)  # BUY or SELL
    quantity = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=True)
    entry_date = Column(DateTime, nullable=False)
    exit_date = Column(DateTime, nullable=True)
    pnl = Column(Float, nullable=True)
    pnl_pct = Column(Float, nullable=True)
    strategy = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False)  # OPEN, CLOSED, CANCELLED
    created_at = Column(DateTime, default=datetime.now)

class Portfolio(Base):
    """Portfolio snapshot model."""
    __tablename__ = 'portfolio'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.now)
    total_value = Column(Float, nullable=False)
    cash = Column(Float, nullable=False)
    positions_value = Column(Float, nullable=False)
    daily_pnl = Column(Float, nullable=True)
    total_pnl = Column(Float, nullable=True)

class Database:
    """Database manager for trading bot."""
    
    def __init__(self, db_url: str = None):
        self.db_url = db_url or Config.DATABASE_URL
        self.engine = create_engine(self.db_url)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        logger.info(f"Database initialized: {self.db_url}")
    
    def save_trade(self, trade_data: dict) -> Trade:
        """Save a trade to the database."""
        trade = Trade(**trade_data)
        self.session.add(trade)
        self.session.commit()
        logger.info(f"Trade saved: {trade.symbol} - {trade.side}")
        return trade
    
    def update_trade(self, trade_id: int, **kwargs):
        """Update a trade record."""
        trade = self.session.query(Trade).filter_by(id=trade_id).first()
        if trade:
            for key, value in kwargs.items():
                setattr(trade, key, value)
            self.session.commit()
            logger.info(f"Trade {trade_id} updated")
    
    def get_open_trades(self):
        """Get all open trades."""
        return self.session.query(Trade).filter_by(status='OPEN').all()
    
    def get_trades_by_symbol(self, symbol: str):
        """Get all trades for a symbol."""
        return self.session.query(Trade).filter_by(symbol=symbol).all()
    
    def save_portfolio_snapshot(self, snapshot_data: dict):
        """Save a portfolio snapshot."""
        snapshot = Portfolio(**snapshot_data)
        self.session.add(snapshot)
        self.session.commit()
    
    def get_latest_portfolio_snapshot(self):
        """Get the most recent portfolio snapshot."""
        return self.session.query(Portfolio).order_by(Portfolio.timestamp.desc()).first()
    
    def get_portfolio_history(self, days: int = 30):
        """Get portfolio history for the last N days."""
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(days=days)
        return self.session.query(Portfolio).filter(Portfolio.timestamp >= cutoff).all()
    
    def close(self):
        """Close database connection."""
        self.session.close()
