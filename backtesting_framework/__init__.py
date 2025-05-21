# backtesting_framework/__init__.py

from .core import * # Import all from core
from .strategy import * # Import all from strategy
from .execution import * # Import all from execution
# from .data import * # Will be added when data_handler is defined
from .backtester import Backtester

__all__ = [
    # Spread out from core, strategy, execution
    "Security", "Transaction", "TransactionType", "Holding", "Portfolio",
    "Event", "EventType", "MarketEvent", "SignalEvent", "OrderEvent", "FillEvent", "DividendEvent",
    "EventQueue",
    "Strategy", "BuyAndHoldStrategy", # Example strategy
    "BaseExecutionHandler", "SimpleExecutionHandler",
    "Backtester",
    # DataHandler components will be added here later
]
