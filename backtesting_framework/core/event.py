# backtesting_framework/core/event.py

from datetime import datetime
from typing import Optional, Any, Dict # Added Dict here as it was used but not imported
from enum import Enum # Using Enum for EventType for better organization

class EventType(Enum):
    MARKET = "MARKET"       # New market data (e.g., price update)
    SIGNAL = "SIGNAL"       # Trading signal from strategy
    ORDER = "ORDER"         # Order to be sent to execution handler
    FILL = "FILL"           # Order has been filled
    DIVIDEND = "DIVIDEND"   # A dividend payment
    # Add more event types as needed (e.g., SPLIT, INFO, etc.)

class Event:
    """
    Base class for all events.
    """
    def __init__(self, event_type: EventType, timestamp: Optional[datetime] = None):
        self.event_type = event_type
        # If no timestamp is provided, use current UTC time.
        # In backtesting, timestamps should ideally be provided by the data source or event generator.
        self.timestamp = timestamp if timestamp else datetime.utcnow()

    def __repr__(self):
        return (f"{self.__class__.__name__}(type={self.event_type.value}, "
                f"timestamp={self.timestamp.strftime('%Y-%m-%d %H:%M:%S')})")

class MarketEvent(Event):
    """
    Handles the event of receiving new market data (e.g., a new bar or tick).
    """
    def __init__(self, timestamp: datetime, security_ticker: str, new_price: float, other_data: Optional[Dict[str, Any]] = None):
        """
        Args:
            timestamp (datetime): The time of the market data.
            security_ticker (str): The ticker symbol for which data is received.
            new_price (float): The new price (e.g., closing price of a bar).
            other_data (Optional[Dict[str, Any]]): Additional data like OHLCV.
        """
        super().__init__(EventType.MARKET, timestamp)
        self.security_ticker = security_ticker
        self.new_price = new_price # Typically the closing price for a bar
        self.other_data = other_data if other_data else {} # e.g., {'open': o, 'high': h, 'low': l, 'volume': v}

    def __repr__(self):
        return (f"MarketEvent(timestamp={self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}, "
                f"ticker='{self.security_ticker}', price={self.new_price:.2f})")

class SignalEvent(Event):
    """
    Handles the event of sending a signal from a Strategy object.
    This signal is then processed by the Portfolio object to generate an OrderEvent.
    """
    def __init__(self, timestamp: datetime, security_ticker: str, order_type: str, suggested_quantity: Optional[float] = None, strength: Optional[float] = None):
        """
        Args:
            timestamp (datetime): The time the signal was generated.
            security_ticker (str): The ticker symbol.
            order_type (str): 'BUY' or 'SELL'. (Should use an Enum or constants like TransactionType)
            suggested_quantity (Optional[float]): Number of units to trade. If None, Portfolio might decide.
            strength (Optional[float]): A value indicating the signal's strength/confidence (e.g. 0.0 to 1.0).
        """
        super().__init__(EventType.SIGNAL, timestamp)
        self.security_ticker = security_ticker
        self.order_type = order_type # e.g., 'BUY', 'SELL'
        self.suggested_quantity = suggested_quantity
        self.strength = strength # Optional: for more advanced portfolio allocation

    def __repr__(self):
        return (f"SignalEvent(timestamp={self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}, "
                f"ticker='{self.security_ticker}', type='{self.order_type}', "
                f"quantity={self.suggested_quantity}, strength={self.strength})")

class OrderEvent(Event):
    """
    Handles the sending of an Order to an execution system.
    The order contains a security ticker, order type (BUY/SELL), quantity, and order type (Market/Limit).
    """
    def __init__(self, timestamp: datetime, security_ticker: str, order_type: str, quantity: float, order_kind: str = "MARKET"):
        """
        Args:
            timestamp (datetime): The time the order was created.
            security_ticker (str): The ticker symbol.
            order_type (str): 'BUY' or 'SELL'.
            quantity (float): Non-negative number of units to trade.
            order_kind (str, optional): Type of order, e.g., 'MARKET', 'LIMIT'. Defaults to 'MARKET'.
                                     (For limit orders, price would also be needed).
        """
        super().__init__(EventType.ORDER, timestamp)
        self.security_ticker = security_ticker
        self.order_type = order_type # 'BUY' or 'SELL'
        self.quantity = quantity
        self.order_kind = order_kind # 'MARKET', 'LIMIT' etc.
        # For LIMIT orders, a self.price attribute would be needed.

    def __repr__(self):
        return (f"OrderEvent(timestamp={self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}, "
                f"ticker='{self.security_ticker}', type='{self.order_type}', "
                f"quantity={self.quantity}, kind='{self.order_kind}')")

class FillEvent(Event):
    """
    Encapsulates the notion of a filled order, as returned from a brokerage.
    Stores the quantity of an instrument actually filled and at what price.
    Additionally, stores the commission of the trade from the brokerage.
    """
    def __init__(self, timestamp: datetime, security_ticker: str, order_type: str, 
                 quantity_filled: float, fill_price: float, commission: float, 
                 exchange: Optional[str] = None, order_id: Optional[str] = None):
        """
        Args:
            timestamp (datetime): The time of fill.
            security_ticker (str): The ticker symbol.
            order_type (str): 'BUY' or 'SELL'.
            quantity_filled (float): The number of units filled.
            fill_price (float): The price at which the order was filled.
            commission (float): The commission paid.
            exchange (Optional[str]): Exchange where the order was filled.
            order_id (Optional[str]): Original order ID this fill corresponds to.
        """
        super().__init__(EventType.FILL, timestamp)
        self.security_ticker = security_ticker
        self.order_type = order_type # 'BUY' or 'SELL'
        self.quantity_filled = quantity_filled
        self.fill_price = fill_price
        self.commission = commission
        self.exchange = exchange
        self.order_id = order_id
        
        # Calculate total cost/proceeds (excluding commission for buy, including for sell from a P&L perspective)
        # but for cash adjustment, it's simpler: cost = quantity * price
        self.cost = self.quantity_filled * self.fill_price


    def __repr__(self):
        return (f"FillEvent(timestamp={self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}, "
                f"ticker='{self.security_ticker}', type='{self.order_type}', "
                f"quantity={self.quantity_filled}, price={self.fill_price:.2f}, "
                f"commission={self.commission:.2f})")

class DividendEvent(Event):
    """
    Handles the event of a dividend payment for a security.
    """
    def __init__(self, timestamp: datetime, security_ticker: str, dividend_per_share: float,
                 payment_date: Optional[datetime] = None, ex_date: Optional[datetime] = None):
        """
        Args:
            timestamp (datetime): The announcement or record date of the dividend.
                                  For backtesting, this is typically the ex-dividend date.
            security_ticker (str): The ticker symbol of the stock paying the dividend.
            dividend_per_share (float): The cash amount of the dividend per share.
            payment_date (Optional[datetime]): Actual date cash is paid.
            ex_date (Optional[datetime]): Ex-dividend date.
        """
        super().__init__(EventType.DIVIDEND, timestamp) # Timestamp is ex-date for backtesting
        self.security_ticker = security_ticker
        self.dividend_per_share = dividend_per_share
        self.payment_date = payment_date if payment_date else timestamp # Assume payment on ex-date if not specified
        self.ex_date = ex_date if ex_date else timestamp

    def __repr__(self):
        return (f"DividendEvent(timestamp={self.timestamp.strftime('%Y-%m-%d')}, "
                f"ticker='{self.security_ticker}', dividend_per_share={self.dividend_per_share:.2f})")

```
