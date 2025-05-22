# backtesting_framework/core/holding.py
# backtesting_framework/核心/持仓.py

class Holding:
    """
    表示投资组合中特定证券的持仓。
    """
    def __init__(self, security_ticker: str, initial_quantity: float = 0, initial_avg_cost: float = 0.0):
        """
        初始化一个Holding对象。

        参数:
            security_ticker (str): 证券的代码。
            initial_quantity (float, optional): 初始持有的数量。默认为0。
            initial_avg_cost (float, optional): 持仓的初始平均成本。默认为0.0。
        """
        if not isinstance(security_ticker, str) or not security_ticker:
            raise ValueError("证券代码必须是一个非空字符串。")
        if not isinstance(initial_quantity, (int, float)) or initial_quantity < 0:
            raise ValueError("初始数量必须是一个非负数。")
        if not isinstance(initial_avg_cost, (int, float)) or initial_avg_cost < 0:
            raise ValueError("初始平均成本必须是一个非负数。")

        self.security_ticker = security_ticker
        self.quantity = float(initial_quantity)
        self.average_cost = float(initial_avg_cost)
        self.last_price = float(initial_avg_cost) # 初始化最后价格，将由市场数据更新
        self.market_value = self.quantity * self.last_price

    def __repr__(self):
        return (f"Holding(ticker='{self.security_ticker}', quantity={self.quantity}, "
                f"average_cost={self.average_cost:.2f}, last_price={self.last_price:.2f}, "
                f"market_value={self.market_value:.2f})")

    def update_last_price(self, current_price: float):
        """
        更新此持仓的最后已知价格并重新计算市值。

        参数:
            current_price (float): 证券的当前市场价格。
        
        引发:
            ValueError: 如果当前价格为负。
        """
        if not isinstance(current_price, (int, float)) or current_price < 0:
            raise ValueError("当前价格必须是一个非负数。")
        self.last_price = float(current_price)
        self.market_value = self.quantity * self.last_price

    def add_shares(self, quantity_to_add: float, price: float):
        """
        向持仓中添加股份，更新数量和平均成本。

        参数:
            quantity_to_add (float): 要添加的股份数量。必须为正。
            price (float):购入股份的价格。必须为非负。

        引发:
            ValueError: 如果要添加的数量不是正数或价格为负。
        """
        if not isinstance(quantity_to_add, (int, float)) or quantity_to_add <= 0:
            raise ValueError("要添加的数量必须为正。")
        if not isinstance(price, (int, float)) or price < 0:
            raise ValueError("价格必须是一个非负数。")

        new_total_cost = (self.average_cost * self.quantity) + (price * quantity_to_add)
        self.quantity += quantity_to_add
        if self.quantity > 0: # 如果数量为0并添加了股份，则避免除以零
            self.average_cost = new_total_cost / self.quantity
        else: # 如果quantity_to_add是正数，则不应发生这种情况
            self.average_cost = 0 
        self.update_last_price(price) # 将最后价格更新为交易价格并重新计算市值

    def remove_shares(self, quantity_to_remove: float):
        """
        从持仓中移除股份，更新数量。平均成本保持不变。

        参数:
            quantity_to_remove (float): 要移除的股份数量。必须为正。

        返回:
            float: 移除股份的成本基础 (quantity_to_remove * self.average_cost)。

        引发:
            ValueError: 如果要移除的数量不是正数或超过当前数量。
        """
        if not isinstance(quantity_to_remove, (int, float)) or quantity_to_remove <= 0:
            raise ValueError("要移除的数量必须为正。")
        if quantity_to_remove > self.quantity:
            raise ValueError(f"无法移除 {quantity_to_remove} 股。"
                             f"当前仅持有 {self.quantity} 股 {self.security_ticker}。")

        cost_basis_of_removed_shares = quantity_to_remove * self.average_cost
        self.quantity -= quantity_to_remove
        
        # 市值需要根据新的数量和最后已知价格进行更新。
        # last_price本身在此处不会更改，仅当市场数据更新它时才会更改。
        self.market_value = self.quantity * self.last_price
        
        if self.quantity == 0:
            self.average_cost = 0.0 # 如果没有剩余股份，则重置平均成本

        return cost_basis_of_removed_shares

```

[end of backtesting_framework/core/holding.py]
