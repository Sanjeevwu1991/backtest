# backtesting_framework/__init__.py
# backtesting_framework/__init__.py

from .core import * # 从core导入所有
from .strategy import * # 从strategy导入所有
from .execution import * # 从execution导入所有
# from .data import * # 定义data_handler后将添加
from .backtester import Backtester

__all__ = [
    # 从core, strategy, execution中展开
    "Security", "Transaction", "TransactionType", "Holding", "Portfolio",
    "Event", "EventType", "MarketEvent", "SignalEvent", "OrderEvent", "FillEvent", "DividendEvent",
    "EventQueue",
    "Strategy", "BuyAndHoldStrategy", # 示例策略
    "BaseExecutionHandler", "SimpleExecutionHandler",
    "Backtester",
    # DataHandler 组件稍后将在此处添加
]

```

[end of backtesting_framework/__init__.py]
