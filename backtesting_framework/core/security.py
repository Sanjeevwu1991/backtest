# backtesting_framework/core/security.py
# backtesting_framework/核心/证券.py

class Security:
    """
    表示一种金融工具（例如，股票）。
    """
    def __init__(self, ticker: str, name: str = "", initial_price: float = 0.0):
        """
        初始化一个Security对象。

        参数:
            ticker (str): 证券的交易代码。
            name (str, optional): 证券的名称。默认为 ""。
            initial_price (float, optional): 证券的初始价格。默认为 0.0。
        """
        if not isinstance(ticker, str) or not ticker:
            raise ValueError("交易代码必须是一个非空字符串。")
        if not isinstance(name, str):
            raise ValueError("名称必须是一个字符串。")
        if not isinstance(initial_price, (int, float)) or initial_price < 0:
            raise ValueError("初始价格必须是一个非负数。")

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
        更新证券的当前价格。

        参数:
            new_price (float): 证券的新价格。

        引发:
            ValueError: 如果新价格为负。
        """
        if not isinstance(new_price, (int, float)) or new_price < 0:
            raise ValueError("新价格必须是一个非负数。")
        self.current_price = float(new_price)
        # 在真实系统中，这可能还会生成一个PriceChangeEvent或类似事件
        # print(f"{self.ticker} 价格更新为 {self.current_price}")

```

[end of backtesting_framework/core/security.py]
