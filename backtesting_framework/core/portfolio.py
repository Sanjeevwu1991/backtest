# backtesting_framework/core/portfolio.py
# backtesting_framework/核心/投资组合.py

from datetime import datetime
from typing import Dict, List, Optional
from .holding import Holding
from .transaction import Transaction, TransactionType

class Portfolio:
    """
    管理交易投资组合的状态，包括现金、持仓和交易历史。
    """
    def __init__(self, initial_cash: float = 100000.0, start_date: Optional[datetime] = None):
        """
        初始化投资组合。

        参数:
            initial_cash (float, optional): 初始现金余额。默认为 100000.0。
            start_date (Optional[datetime], optional): 投资组合的正式开始日期。
                                                     如果为None，则默认为当前日期时间。
        """
        if not isinstance(initial_cash, (int, float)) or initial_cash < 0:
            raise ValueError("初始现金必须是非负数。")

        self.start_date = start_date if start_date else datetime.now()
        self.current_cash = float(initial_cash)
        self.holdings: Dict[str, Holding] = {} # 股票代码 -> Holding 对象
        self.transactions_history: List[Transaction] = []
        
        # 用于存储投资组合价值和组成随时间变化的快照
        # 每条记录可以是一个字典或自定义对象
        self.daily_records: List[Dict] = []
        self.current_datetime: Optional[datetime] = self.start_date

    def __repr__(self):
        return (f"Portfolio(start_date='{self.start_date.strftime('%Y-%m-%d')}', "
                f"current_cash={self.current_cash:.2f}, "
                f"holdings_count={len(self.holdings)}, "
                f"total_net_value={self.get_net_value():.2f})")

    def update_datetime(self, new_datetime: datetime):
        """
        更新投资组合内部的当前日期时间。
        这对于正确地为交易和记录添加时间戳至关重要。
        """
        if not isinstance(new_datetime, datetime):
            raise ValueError("新的日期时间必须是datetime对象。")
        self.current_datetime = new_datetime

    def add_cash(self, amount: float):
        """向投资组合中添加现金。"""
        if not isinstance(amount, (int, float)) or amount < 0:
            raise ValueError("要添加的金额必须是非负数。")
        self.current_cash += amount

    def remove_cash(self, amount: float):
        """从投资组合中移除现金。如果现金不足则引发ValueError。"""
        if not isinstance(amount, (int, float)) or amount < 0:
            raise ValueError("要移除的金额必须是非负数。")
        if amount > self.current_cash:
            raise ValueError(f"无法移除 {amount:.2f}: 现金不足。可用现金: {self.current_cash:.2f}")
        self.current_cash -= amount

    def get_total_holdings_value(self) -> float:
        """计算当前所有持仓的总市值。"""
        return sum(holding.market_value for holding in self.holdings.values())

    def get_net_value(self) -> float:
        """计算投资组合的总净资产值 (NAV) (持仓 + 现金)。"""
        return self.get_total_holdings_value() + self.current_cash

    def update_holding_price(self, security_ticker: str, new_price: float):
        """
        更新特定持仓的价格。
        如果持仓不存在，此方法不执行任何操作（因为投资组合
        应仅跟踪其已交互或持有的证券）。
        """
        if security_ticker in self.holdings:
            self.holdings[security_ticker].update_last_price(new_price)
        # 如果不在持仓中，意味着我们不拥有它，所以其价格变动
        # 不直接影响我们持仓的市值计算，
        # 尽管它对于一般市场数据很重要。

    def _add_transaction_to_history(self, transaction: Transaction):
        """将交易附加到历史记录中。"""
        self.transactions_history.append(transaction)

    def execute_transaction(self, transaction: Transaction):
        """
        处理交易（买入或卖出），更新持仓和现金。
        此方法假定交易有效且已发生（一个FillEvent）。

        参数:
            transaction (Transaction): 要处理的交易。
        """
        if not isinstance(transaction, Transaction):
            raise ValueError("提供了无效的交易对象。")
        
        ticker = transaction.security_ticker
        
        # 无论交易类型如何，首先扣除佣金
        self.remove_cash(transaction.commission)

        if transaction.transaction_type == TransactionType.BUY:
            cost_of_purchase = transaction.quantity * transaction.price
            self.remove_cash(cost_of_purchase)

            if ticker not in self.holdings:
                self.holdings[ticker] = Holding(security_ticker=ticker)
            
            self.holdings[ticker].add_shares(transaction.quantity, transaction.price)
            # Holding中的add_shares方法已经更新了其自身的last_price和market_value

        elif transaction.transaction_type == TransactionType.SELL:
            proceeds_from_sale = transaction.quantity * transaction.price
            self.add_cash(proceeds_from_sale)

            if ticker not in self.holdings:
                # 如果逻辑正确，理想情况下不应发生这种情况，
                # 因为我们不能卖出我们没有的东西（除非做空，目前不支持）
                raise ValueError(f"试图卖出 {ticker} 但不在持仓中。")
            
            # remove_shares 更新数量和市值，并返回成本基础
            # 如果此处需要，可用于计算盈亏。
            self.holdings[ticker].remove_shares(transaction.quantity)

            # 如果持仓数量变为零，则从持仓字典中删除它
            if self.holdings[ticker].quantity == 0:
                del self.holdings[ticker]
        else:
            raise ValueError(f"未知的交易类型: {transaction.transaction_type}")

        self._add_transaction_to_history(transaction)
        # print(f"已执行: {transaction}, 现金: {self.current_cash:.2f}") # 用于调试

    def record_daily_snapshot(self, timestamp: datetime):
        """
        记录投资组合状态的快照。
        通常应在每个交易日结束时调用此方法。
        """
        if not isinstance(timestamp, datetime):
            raise ValueError("时间戳必须是datetime对象。")

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
            # "transactions_today": [] # 这需要更多逻辑来筛选
        }
        self.daily_records.append(snapshot)
        # print(f"快照 @ {timestamp.strftime('%Y-%m-%d')}: NAV {snapshot['net_value']:.2f}")

# 示例用法（用于测试目的，将被移除或移至测试文件）
if __name__ == '__main__':
    # 创建一个投资组合
    portfolio = Portfolio(initial_cash=100000.0, start_date=datetime(2023, 1, 1, 9, 30))
    print(portfolio)

    # 模拟我们可能购买的股票的市场更新
    # 在真实的回测中，这将来自MarketEvents
    # 现在，我们假设AAPL的价格是$150
    # portfolio.update_holding_price("AAPL", 150.0) # 如果不持有则无效

    # 模拟一个买入交易
    buy_time = datetime(2023, 1, 1, 10, 0, 0)
    portfolio.update_datetime(buy_time) # 更新投资组合时间

    # 假设一个FillEvent导致了此交易
    buy_transaction = Transaction(
        timestamp=buy_time,
        security_ticker="AAPL",
        transaction_type=TransactionType.BUY,
        quantity=10,
        price=150.0,
        commission=5.0
    )
    portfolio.execute_transaction(buy_transaction)
    print(f"买入 AAPL 后: 现金 {portfolio.current_cash:.2f}, 持仓: {portfolio.holdings}")
    print(f"净资产值: {portfolio.get_net_value():.2f}")


    # 模拟AAPL的市场价格变动
    price_update_time = datetime(2023, 1, 1, 15, 30, 0)
    portfolio.update_datetime(price_update_time)
    portfolio.update_holding_price("AAPL", 152.0)
    print(f"AAPL 价格更新后: 持仓: {portfolio.holdings['AAPL']}")
    print(f"净资产值: {portfolio.get_net_value():.2f}")

    # 记录日终快照
    portfolio.record_daily_snapshot(datetime(2023, 1, 1, 16, 0, 0))

    # 模拟第二天的卖出交易
    sell_time = datetime(2023, 1, 2, 11, 0, 0)
    portfolio.update_datetime(sell_time)

    sell_transaction = Transaction(
        timestamp=sell_time,
        security_ticker="AAPL",
        transaction_type=TransactionType.SELL,
        quantity=5, # 卖出10股中的5股
        price=155.0,
        commission=5.0
    )
    portfolio.execute_transaction(sell_transaction)
    print(f"卖出 AAPL 后: 现金 {portfolio.current_cash:.2f}, 持仓: {portfolio.holdings.get('AAPL')}")
    print(f"净资产值: {portfolio.get_net_value():.2f}")

    # 记录另一个日终快照
    portfolio.record_daily_snapshot(datetime(2023, 1, 2, 16, 0, 0))
    
    print("\n每日记录:")
    for record in portfolio.daily_records:
        print(record)
    
    print("\n交易历史:")
    for trans in portfolio.transactions_history:
        print(trans)

```

[end of backtesting_framework/core/portfolio.py]
