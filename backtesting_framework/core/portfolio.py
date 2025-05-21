# backtesting_framework/core/portfolio.py

from datetime import datetime
from typing import Dict, List, Optional
from .holding import Holding
from .transaction import Transaction, TransactionType

class Portfolio:
    """
    Manages the state of a trading portfolio, including cash, holdings,
    and transaction history.
    """
    def __init__(self, initial_cash: float = 100000.0, start_date: Optional[datetime] = None):
        """
        Initializes the Portfolio.

        Args:
            initial_cash (float, optional): The starting cash balance. Defaults to 100000.0.
            start_date (Optional[datetime], optional): The official start date of the portfolio.
                                                     Defaults to current datetime if None.
        """
        if not isinstance(initial_cash, (int, float)) or initial_cash < 0:
            raise ValueError("Initial cash must be a non-negative number.")

        self.start_date = start_date if start_date else datetime.now()
        self.current_cash = float(initial_cash)
        self.holdings: Dict[str, Holding] = {} # Ticker -> Holding object
        self.transactions_history: List[Transaction] = []
        
        # To store snapshots of portfolio value and composition over time
        # Each record could be a dictionary or a custom object
        self.daily_records: List[Dict] = []
        self.current_datetime: Optional[datetime] = self.start_date

    def __repr__(self):
        return (f"Portfolio(start_date='{self.start_date.strftime('%Y-%m-%d')}', "
                f"current_cash={self.current_cash:.2f}, "
                f"holdings_count={len(self.holdings)}, "
                f"total_net_value={self.get_net_value():.2f})")

    def update_datetime(self, new_datetime: datetime):
        """
        Updates the portfolio's internal current datetime.
        This is crucial for timestamping transactions and records correctly.
        """
        if not isinstance(new_datetime, datetime):
            raise ValueError("New datetime must be a datetime object.")
        self.current_datetime = new_datetime

    def add_cash(self, amount: float):
        """Adds cash to the portfolio."""
        if not isinstance(amount, (int, float)) or amount < 0:
            raise ValueError("Amount to add must be a non-negative number.")
        self.current_cash += amount

    def remove_cash(self, amount: float):
        """Removes cash from the portfolio. Raises ValueError if insufficient cash."""
        if not isinstance(amount, (int, float)) or amount < 0:
            raise ValueError("Amount to remove must be a non-negative number.")
        if amount > self.current_cash:
            raise ValueError(f"Cannot remove {amount:.2f}: insufficient cash. Available: {self.current_cash:.2f}")
        self.current_cash -= amount

    def get_total_holdings_value(self) -> float:
        """Calculates the total market value of all current holdings."""
        return sum(holding.market_value for holding in self.holdings.values())

    def get_net_value(self) -> float:
        """Calculates the total net asset value (NAV) of the portfolio (holdings + cash)."""
        return self.get_total_holdings_value() + self.current_cash

    def update_holding_price(self, security_ticker: str, new_price: float):
        """
        Updates the price of a specific holding.
        If the holding doesn't exist, this method does nothing (as portfolio
        should only track securities it has interacted with or holds).
        """
        if security_ticker in self.holdings:
            self.holdings[security_ticker].update_last_price(new_price)
        # If not in holdings, it means we don't own it, so its price change
        # doesn't directly affect our holdings' market value calculation,
        # though it's important for general market data.

    def _add_transaction_to_history(self, transaction: Transaction):
        """Appends a transaction to the history."""
        self.transactions_history.append(transaction)

    def execute_transaction(self, transaction: Transaction):
        """
        Processes a transaction (buy or sell), updating holdings and cash.
        This method assumes the transaction is valid and has already occurred (a FillEvent).

        Args:
            transaction (Transaction): The transaction to process.
        """
        if not isinstance(transaction, Transaction):
            raise ValueError("Invalid transaction object provided.")
        
        ticker = transaction.security_ticker
        
        # Deduct commission first, regardless of transaction type
        self.remove_cash(transaction.commission)

        if transaction.transaction_type == TransactionType.BUY:
            cost_of_purchase = transaction.quantity * transaction.price
            self.remove_cash(cost_of_purchase)

            if ticker not in self.holdings:
                self.holdings[ticker] = Holding(security_ticker=ticker)
            
            self.holdings[ticker].add_shares(transaction.quantity, transaction.price)
            # The add_shares method in Holding already updates its own last_price and market_value

        elif transaction.transaction_type == TransactionType.SELL:
            proceeds_from_sale = transaction.quantity * transaction.price
            self.add_cash(proceeds_from_sale)

            if ticker not in self.holdings:
                # This should ideally not happen if logic is correct,
                # as we can't sell what we don't have (unless shorting, not supported yet)
                raise ValueError(f"Attempted to sell {ticker} but not in holdings.")
            
            # remove_shares updates quantity and market_value, and returns cost_basis
            # which could be used for P&L calculation if needed here.
            self.holdings[ticker].remove_shares(transaction.quantity)

            # If quantity of a holding becomes zero, remove it from the holdings dict
            if self.holdings[ticker].quantity == 0:
                del self.holdings[ticker]
        else:
            raise ValueError(f"Unknown transaction type: {transaction.transaction_type}")

        self._add_transaction_to_history(transaction)
        # print(f"Executed: {transaction}, Cash: {self.current_cash:.2f}") # For debugging

    def record_daily_snapshot(self, timestamp: datetime):
        """
        Records a snapshot of the portfolio's state.
        This should be called typically at the end of each trading day.
        """
        if not isinstance(timestamp, datetime):
            raise ValueError("Timestamp must be a datetime object.")

        current_holdings_snapshot = {
            ticker: {
                "quantity": holding.quantity,
                "average_cost": holding.average_cost,
                "last_price": holding.last_price,
                "market_value": holding.market_value,
            }
            for ticker, holding in self.holdings.items()
        }
        
        snapshot = {
            "timestamp": timestamp,
            "net_value": self.get_net_value(),
            "cash": self.current_cash,
            "holdings_value": self.get_total_holdings_value(),
            "holdings_detail": current_holdings_snapshot,
            # "transactions_today": [] # This would require more logic to filter
        }
        self.daily_records.append(snapshot)
        # print(f"Snapshot @ {timestamp.strftime('%Y-%m-%d')}: NAV {snapshot['net_value']:.2f}")

# Example Usage (for testing purposes, will be removed or moved to a test file)
if __name__ == '__main__':
    # Create a portfolio
    portfolio = Portfolio(initial_cash=100000.0, start_date=datetime(2023, 1, 1, 9, 30))
    print(portfolio)

    # Simulate a market update for a stock we might buy
    # In a real backtest, this would come from MarketEvents
    # For now, let's assume AAPL is at $150
    # portfolio.update_holding_price("AAPL", 150.0) # No effect if not holding

    # Simulate a BUY transaction
    buy_time = datetime(2023, 1, 1, 10, 0, 0)
    portfolio.update_datetime(buy_time) # Update portfolio time

    # Assume a FillEvent resulted in this transaction
    buy_transaction = Transaction(
        timestamp=buy_time,
        security_ticker="AAPL",
        transaction_type=TransactionType.BUY,
        quantity=10,
        price=150.0,
        commission=5.0
    )
    portfolio.execute_transaction(buy_transaction)
    print(f"After BUY AAPL: Cash {portfolio.current_cash:.2f}, Holdings: {portfolio.holdings}")
    print(f"NAV: {portfolio.get_net_value():.2f}")


    # Simulate market price change for AAPL
    price_update_time = datetime(2023, 1, 1, 15, 30, 0)
    portfolio.update_datetime(price_update_time)
    portfolio.update_holding_price("AAPL", 152.0)
    print(f"After AAPL price update: Holdings: {portfolio.holdings['AAPL']}")
    print(f"NAV: {portfolio.get_net_value():.2f}")

    # Record end-of-day snapshot
    portfolio.record_daily_snapshot(datetime(2023, 1, 1, 16, 0, 0))

    # Simulate a SELL transaction on the next day
    sell_time = datetime(2023, 1, 2, 11, 0, 0)
    portfolio.update_datetime(sell_time)

    sell_transaction = Transaction(
        timestamp=sell_time,
        security_ticker="AAPL",
        transaction_type=TransactionType.SELL,
        quantity=5, # Selling 5 out of 10 shares
        price=155.0,
        commission=5.0
    )
    portfolio.execute_transaction(sell_transaction)
    print(f"After SELL AAPL: Cash {portfolio.current_cash:.2f}, Holdings: {portfolio.holdings.get('AAPL')}")
    print(f"NAV: {portfolio.get_net_value():.2f}")

    # Record another end-of-day snapshot
    portfolio.record_daily_snapshot(datetime(2023, 1, 2, 16, 0, 0))
    
    print("\nDaily Records:")
    for record in portfolio.daily_records:
        print(record)
    
    print("\nTransaction History:")
    for trans in portfolio.transactions_history:
        print(trans)

```
