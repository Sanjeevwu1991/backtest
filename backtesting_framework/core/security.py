# backtesting_framework/core/security.py

class Security:
    """
    Represents a financial instrument (e.g., a stock).
    """
    def __init__(self, ticker: str, name: str = "", initial_price: float = 0.0):
        """
        Initializes a Security object.

        Args:
            ticker (str): The ticker symbol of the security.
            name (str, optional): The name of the security. Defaults to "".
            initial_price (float, optional): The initial price of the security. Defaults to 0.0.
        """
        if not isinstance(ticker, str) or not ticker:
            raise ValueError("Ticker symbol must be a non-empty string.")
        if not isinstance(name, str):
            raise ValueError("Name must be a string.")
        if not isinstance(initial_price, (int, float)) or initial_price < 0:
            raise ValueError("Initial price must be a non-negative number.")

        self.ticker = ticker
        self.name = name
        self.current_price = float(initial_price)

    def __repr__(self):
        return f"Security(ticker='{self.ticker}', name='{self.name}', current_price={self.current_price})"

    def __eq__(self, other):
        if not isinstance(other, Security):
            return NotImplemented
        return self.ticker == other.ticker

    def __hash__(self):
        return hash(self.ticker)

    def update_price(self, new_price: float):
        """
        Updates the current price of the security.

        Args:
            new_price (float): The new price of the security.

        Raises:
            ValueError: If the new price is negative.
        """
        if not isinstance(new_price, (int, float)) or new_price < 0:
            raise ValueError("New price must be a non-negative number.")
        self.current_price = float(new_price)
        # In a real system, this might also generate a PriceChangeEvent or similar
        # print(f"{self.ticker} price updated to {self.current_price}")
