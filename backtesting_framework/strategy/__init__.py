# backtesting_framework/strategy/__init__.py

from .base_strategy import Strategy, BuyAndHoldStrategy # Example strategy

__all__ = [
    "Strategy",
    "BuyAndHoldStrategy", # Exporting example strategy for now
]
