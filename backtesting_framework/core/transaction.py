# backtesting_framework/core/transaction.py

from typing import NamedTuple
from datetime import datetime

class TransactionType:
    BUY = "BUY"
    SELL = "SELL"

class Transaction(NamedTuple):
    """
    Represents a single trading transaction.
    """
    timestamp: datetime
    security_ticker: str
    transaction_type: str  # Should be TransactionType.BUY or TransactionType.SELL
    quantity: float
    price: float
    commission: float = 0.0
    order_id: str = None # Optional: to link with an order

    def __repr__(self):
        return (f"Transaction(timestamp={self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}, "
                f"ticker='{self.security_ticker}', type='{self.transaction_type}', "
                f"quantity={self.quantity}, price={self.price:.2f}, "
                f"commission={self.commission:.2f}, order_id='{self.order_id}')")
