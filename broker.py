"""
Broker integration module for order execution.
Supports Alpaca and can be extended for other brokers.
"""
import logging
from typing import Dict, List, Optional
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce, OrderType
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestQuoteRequest
from config import Config

logger = logging.getLogger(__name__)

class BrokerInterface:
    """Interface for broker operations."""
    
    def __init__(self):
        self.client = None
        self.data_client = None
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize Alpaca trading and data clients."""
        try:
            self.client = TradingClient(
                Config.ALPACA_API_KEY,
                Config.ALPACA_SECRET_KEY,
                paper=Config.is_paper_trading()
            )
            self.data_client = StockHistoricalDataClient(
                Config.ALPACA_API_KEY,
                Config.ALPACA_SECRET_KEY
            )
            logger.info(f"Initialized Alpaca client (Paper Trading: {Config.is_paper_trading()})")
        except Exception as e:
            logger.error(f"Failed to initialize broker clients: {e}")
            raise
    
    def get_account(self) -> Dict:
        """Get account information."""
        try:
            account = self.client.get_account()
            return {
                'equity': float(account.equity),
                'cash': float(account.cash),
                'buying_power': float(account.buying_power),
                'portfolio_value': float(account.portfolio_value),
                'pattern_day_trader': account.pattern_day_trader,
                'trading_blocked': account.trading_blocked,
                'account_blocked': account.account_blocked
            }
        except Exception as e:
            logger.error(f"Error fetching account info: {e}")
            return {}
    
    def get_positions(self) -> List[Dict]:
        """Get current positions."""
        try:
            positions = self.client.get_all_positions()
            return [{
                'symbol': pos.symbol,
                'qty': float(pos.qty),
                'avg_entry_price': float(pos.avg_entry_price),
                'current_price': float(pos.current_price),
                'market_value': float(pos.market_value),
                'unrealized_pl': float(pos.unrealized_pl),
                'unrealized_plpc': float(pos.unrealized_plpc),
                'side': pos.side
            } for pos in positions]
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            return []
    
    def place_market_order(self, symbol: str, qty: float, side: str) -> Optional[Dict]:
        """
        Place a market order.
        
        Args:
            symbol: Stock ticker
            qty: Quantity to trade
            side: 'buy' or 'sell'
        """
        try:
            order_side = OrderSide.BUY if side.lower() == 'buy' else OrderSide.SELL
            
            market_order_data = MarketOrderRequest(
                symbol=symbol,
                qty=qty,
                side=order_side,
                time_in_force=TimeInForce.DAY
            )
            
            order = self.client.submit_order(order_data=market_order_data)
            
            logger.info(f"Placed {side} market order: {qty} shares of {symbol}")
            
            return {
                'id': order.id,
                'symbol': order.symbol,
                'qty': float(order.qty),
                'side': order.side,
                'type': order.type,
                'status': order.status,
                'submitted_at': order.submitted_at
            }
        except Exception as e:
            logger.error(f"Error placing market order for {symbol}: {e}")
            return None
    
    def place_limit_order(self, symbol: str, qty: float, side: str, 
                         limit_price: float) -> Optional[Dict]:
        """Place a limit order."""
        try:
            order_side = OrderSide.BUY if side.lower() == 'buy' else OrderSide.SELL
            
            limit_order_data = LimitOrderRequest(
                symbol=symbol,
                qty=qty,
                side=order_side,
                time_in_force=TimeInForce.DAY,
                limit_price=limit_price
            )
            
            order = self.client.submit_order(order_data=limit_order_data)
            
            logger.info(f"Placed {side} limit order: {qty} shares of {symbol} at ${limit_price}")
            
            return {
                'id': order.id,
                'symbol': order.symbol,
                'qty': float(order.qty),
                'side': order.side,
                'type': order.type,
                'limit_price': float(order.limit_price),
                'status': order.status
            }
        except Exception as e:
            logger.error(f"Error placing limit order for {symbol}: {e}")
            return None
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order."""
        try:
            self.client.cancel_order_by_id(order_id)
            logger.info(f"Cancelled order {order_id}")
            return True
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False
    
    def get_open_orders(self) -> List[Dict]:
        """Get all open orders."""
        try:
            orders = self.client.get_orders()
            return [{
                'id': order.id,
                'symbol': order.symbol,
                'qty': float(order.qty),
                'side': order.side,
                'type': order.type,
                'status': order.status,
                'submitted_at': order.submitted_at
            } for order in orders]
        except Exception as e:
            logger.error(f"Error fetching open orders: {e}")
            return []
    
    def close_position(self, symbol: str) -> bool:
        """Close an entire position."""
        try:
            self.client.close_position(symbol)
            logger.info(f"Closed position for {symbol}")
            return True
        except Exception as e:
            logger.error(f"Error closing position for {symbol}: {e}")
            return False
    
    def close_all_positions(self) -> bool:
        """Close all open positions."""
        try:
            self.client.close_all_positions(cancel_orders=True)
            logger.info("Closed all positions")
            return True
        except Exception as e:
            logger.error(f"Error closing all positions: {e}")
            return False
    
    def get_latest_quote(self, symbol: str) -> Optional[Dict]:
        """Get the latest quote for a symbol."""
        try:
            request = StockLatestQuoteRequest(symbol_or_symbols=symbol)
            quotes = self.data_client.get_stock_latest_quote(request)
            quote = quotes[symbol]
            
            return {
                'ask_price': float(quote.ask_price),
                'bid_price': float(quote.bid_price),
                'ask_size': quote.ask_size,
                'bid_size': quote.bid_size
            }
        except Exception as e:
            logger.error(f"Error fetching quote for {symbol}: {e}")
            return None
