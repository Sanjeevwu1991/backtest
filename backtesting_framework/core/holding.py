# backtesting_framework/core/holding.py

class Holding:
    """
    Represents a holding of a specific security in the portfolio.
    """
    def __init__(self, security_ticker: str, initial_quantity: float = 0, initial_avg_cost: float = 0.0):
        """
        Initializes a Holding object.

        Args:
            security_ticker (str): The ticker symbol of the security.
            initial_quantity (float, optional): The initial quantity held. Defaults to 0.
            initial_avg_cost (float, optional): The initial average cost of the holding. Defaults to 0.0.
        """
        if not isinstance(security_ticker, str) or not security_ticker:
            raise ValueError("Security ticker must be a non-empty string.")
        if not isinstance(initial_quantity, (int, float)) or initial_quantity < 0:
            raise ValueError("Initial quantity must be a non-negative number.")
        if not isinstance(initial_avg_cost, (int, float)) or initial_avg_cost < 0:
            raise ValueError("Initial average cost must be a non-negative number.")

        self.security_ticker = security_ticker
        self.quantity = float(initial_quantity)
        self.average_cost = float(initial_avg_cost)
        self.last_price = float(initial_avg_cost) # Initialize last_price, will be updated by market data
        self.market_value = self.quantity * self.last_price

    def __repr__(self):
        return (f"Holding(ticker='{self.security_ticker}', quantity={self.quantity}, "
                f"average_cost={self.average_cost:.2f}, last_price={self.last_price:.2f}, "
                f"market_value={self.market_value:.2f})")

    def update_last_price(self, current_price: float):
        """
        Updates the last known price for this holding and recalculates market value.

        Args:
            current_price (float): The current market price of the security.
        
        Raises:
            ValueError: If the current price is negative.
        """
        if not isinstance(current_price, (int, float)) or current_price < 0:
            raise ValueError("Current price must be a non-negative number.")
        self.last_price = float(current_price)
        self.market_value = self.quantity * self.last_price

    def add_shares(self, quantity_to_add: float, price: float):
        """
        Adds shares to the holding, updating quantity and average cost.

        Args:
            quantity_to_add (float): The number of shares to add. Must be positive.
            price (float): The price at which the shares were acquired. Must be non-negative.

        Raises:
            ValueError: If quantity_to_add is not positive or price is negative.
        """
        if not isinstance(quantity_to_add, (int, float)) or quantity_to_add <= 0:
            raise ValueError("Quantity to add must be positive.")
        if not isinstance(price, (int, float)) or price < 0:
            raise ValueError("Price must be a non-negative number.")

        new_total_cost = (self.average_cost * self.quantity) + (price * quantity_to_add)
        self.quantity += quantity_to_add
        if self.quantity > 0: # Avoid division by zero if quantity was 0 and shares are added
            self.average_cost = new_total_cost / self.quantity
        else: # Should not happen if quantity_to_add is positive
            self.average_cost = 0 
        self.update_last_price(price) # Update last price to the transaction price and recalculate market value

    def remove_shares(self, quantity_to_remove: float):
        """
        Removes shares from the holding, updating quantity. Average cost remains unchanged.

        Args:
            quantity_to_remove (float): The number of shares to remove. Must be positive.

        Returns:
            float: The cost basis of the shares removed (quantity_to_remove * self.average_cost).

        Raises:
            ValueError: If quantity_to_remove is not positive or exceeds current quantity.
        """
        if not isinstance(quantity_to_remove, (int, float)) or quantity_to_remove <= 0:
            raise ValueError("Quantity to remove must be positive.")
        if quantity_to_remove > self.quantity:
            raise ValueError(f"Cannot remove {quantity_to_remove} shares. "
                             f"Only {self.quantity} shares of {self.security_ticker} are held.")

        cost_basis_of_removed_shares = quantity_to_remove * self.average_cost
        self.quantity -= quantity_to_remove
        
        # Market value needs to be updated based on the new quantity and last known price.
        # The last_price itself doesn't change here, only when market data updates it.
        self.market_value = self.quantity * self.last_price
        
        if self.quantity == 0:
            self.average_cost = 0.0 # Reset average cost if no shares are left

        return cost_basis_of_removed_shares

```
