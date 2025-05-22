# backtesting_framework/core/transaction.py
# backtesting_framework/核心/交易.py

from typing import NamedTuple
from datetime import datetime

class TransactionType:
    BUY = "BUY"  # 买入
    SELL = "SELL" # 卖出

class Transaction(NamedTuple):
    """
    表示单个交易。
    """
    timestamp: datetime  # 时间戳
    security_ticker: str  # 证券代码
    transaction_type: str  # 应为 TransactionType.BUY 或 TransactionType.SELL
    quantity: float  # 数量
    price: float  # 价格
    commission: float = 0.0  # 佣金
    order_id: str = None # 可选：用于关联订单

    def __repr__(self):
        return (f"Transaction(timestamp={self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}, "
                f"ticker='{self.security_ticker}', type='{self.transaction_type}', "
                f"quantity={self.quantity}, price={self.price:.2f}, "
                f"commission={self.commission:.2f}, order_id='{self.order_id}')")

```

[end of backtesting_framework/core/transaction.py]
