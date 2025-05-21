# backtesting_framework/execution/execution_handler.py

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

# Assuming Event and specific event types are accessible
from ..core.event import OrderEvent, FillEvent
# from backtesting_framework.core.event import OrderEvent, FillEvent # Absolute import
from ..core.transaction import TransactionType # For consistency in FillEvent order_type

# If Security class or a data structure for current prices is needed:
# from ..core.security import Security # Or a simpler price provider interface

class BaseExecutionHandler(ABC):
    """
    Abstract Base Class for all execution handlers.
    The execution handler is responsible for taking OrderEvents and simulating
    their execution, producing FillEvents.
    """
    def __init__(self, handler_id: str, description: Optional[str] = None):
        self.handler_id = handler_id
        self.description = description if description else self.__class__.__name__

    def __repr__(self):
        return f"{self.__class__.__name__}(id='{self.handler_id}')"

    @abstractmethod
    def execute_order(self, order_event: OrderEvent, 
                      current_market_price: Optional[float] = None,
                      # data_handler: Optional[Any] = None # To get current price if not passed
                     ) -> Optional[FillEvent]:
        """
        Simulates the execution of an order.

        Args:
            order_event (OrderEvent): The order to be executed.
            current_market_price (Optional[float]): The current market price for the security.
                                                   Required for market orders by simple handlers.
            # data_handler: Can be used to fetch the current price if not provided.

        Returns:
            Optional[FillEvent]: A FillEvent if the order was successfully executed, 
                                 None otherwise (e.g., insufficient funds, invalid order).
        """
        pass

class SimpleExecutionHandler(BaseExecutionHandler):
    """
    A simple execution handler that simulates immediate fills at the provided
    market price. It can apply a fixed commission or a percentage-based commission.
    Does not simulate slippage for market orders beyond using the given price.
    """
    def __init__(self, handler_id: str = "SimpleExec", 
                 commission_per_share: float = 0.005, 
                 pct_commission: float = 0.00, # e.g., 0.001 for 0.1%
                 min_commission: float = 1.0,
                 description: Optional[str] = "Simple fill-at-market execution with commission."):
        super().__init__(handler_id, description)
        self.commission_per_share = commission_per_share
        self.pct_commission = pct_commission
        self.min_commission = min_commission

    def _calculate_commission(self, quantity: float, price: float) -> float:
        """Calculates commission for a trade."""
        commission = 0.0
        if self.commission_per_share > 0:
            commission += quantity * self.commission_per_share
        if self.pct_commission > 0:
            commission += quantity * price * self.pct_commission
        
        return max(commission, self.min_commission) if quantity > 0 else 0.0

    def execute_order(self, order_event: OrderEvent, 
                      current_market_price: Optional[float] = None) -> Optional[FillEvent]:
        """
        Simulates filling an order. For 'MARKET' orders, current_market_price is required.
        Limit orders are not supported by this simple handler.

        Args:
            order_event (OrderEvent): The order to execute.
            current_market_price (Optional[float]): The price at which to fill a market order.

        Returns:
            Optional[FillEvent]: The generated FillEvent or None if order can't be processed.
        """
        if order_event.order_kind != "MARKET":
            print(f"{self.handler_id}: Warning - Only MARKET orders are supported. Order {order_event} ignored.")
            return None

        if current_market_price is None:
            print(f"{self.handler_id}: Error - current_market_price is required for MARKET orders. Order {order_event} ignored.")
            return None
        
        if current_market_price <= 0:
            print(f"{self.handler_id}: Error - Invalid market price ({current_market_price}). Order {order_event} ignored.")
            return None

        if order_event.quantity <= 0:
            print(f"{self.handler_id}: Error - Order quantity must be positive. Order {order_event} ignored.")
            return None

        fill_price = current_market_price # No slippage simulation in this simple handler
        commission = self._calculate_commission(order_event.quantity, fill_price)
        
        # Use TransactionType constants for order_type in FillEvent for consistency
        # This assumes order_event.order_type is 'BUY' or 'SELL'
        fill_order_type = order_event.order_type 
        if order_event.order_type.upper() == TransactionType.BUY:
            fill_order_type = TransactionType.BUY
        elif order_event.order_type.upper() == TransactionType.SELL:
            fill_order_type = TransactionType.SELL
        else:
            print(f"{self.handler_id}: Error - Unknown order type '{order_event.order_type}'. Order ignored.")
            return None


        fill_event = FillEvent(
            timestamp=order_event.timestamp, # Or current time: datetime.now(timezone.utc)
            security_ticker=order_event.security_ticker,
            order_type=fill_order_type,
            quantity_filled=order_event.quantity,
            fill_price=fill_price,
            commission=commission,
            order_id=None # Link to original order_event.id if it had one
        )
        # print(f"{self.handler_id}: Executed order {order_event}, Fill: {fill_event}")
        return fill_event

if __name__ == '__main__':
    from datetime import datetime, timezone
    # Example Usage
    exec_handler = SimpleExecutionHandler(commission_per_share=0.01, pct_commission=0.0005, min_commission=1.50)
    print(exec_handler)

    # Create a sample OrderEvent
    buy_order = OrderEvent(
        timestamp=datetime.now(timezone.utc),
        security_ticker="AAPL",
        order_type="BUY", # Should ideally use TransactionType.BUY
        quantity=100,
        order_kind="MARKET"
    )
    
    # Simulate execution
    market_price_aapl = 150.00
    fill = exec_handler.execute_order(buy_order, market_price_aapl)
    if fill:
        print(f"Generated Fill: {fill}")
        print(f"Cost of fill (qty*price): {fill.cost}")
        assert fill.commission == max(100 * 0.01 + 100 * 150.00 * 0.0005, 1.50)
        assert fill.fill_price == market_price_aapl

    sell_order_invalid_type = OrderEvent(
        timestamp=datetime.now(timezone.utc),
        security_ticker="MSFT",
        order_type="SELL",
        quantity=50,
        order_kind="LIMIT" # Not supported
    )
    fill_limit = exec_handler.execute_order(sell_order_invalid_type, 280.00)
    if not fill_limit:
        print("Limit order correctly not processed by simple handler.")

    sell_order_no_price = OrderEvent(
        timestamp=datetime.now(timezone.utc),
        security_ticker="TSLA",
        order_type="SELL",
        quantity=10,
        order_kind="MARKET"
    )
    fill_no_price = exec_handler.execute_order(sell_order_no_price) # No market price
    if not fill_no_price:
        print("Market order without price correctly not processed.")
        
    buy_order_zero_qty = OrderEvent(
        timestamp=datetime.now(timezone.utc),
        security_ticker="NVDA",
        order_type="BUY", 
        quantity=0, # Zero quantity
        order_kind="MARKET"
    )
    fill_zero_qty = exec_handler.execute_order(buy_order_zero_qty, current_market_price=300.0)
    if not fill_zero_qty:
        print("Order with zero quantity correctly not processed.")

```
