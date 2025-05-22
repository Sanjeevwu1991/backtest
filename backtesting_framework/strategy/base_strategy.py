# backtesting_framework/strategy/base_strategy.py
# backtesting_framework/策略/基础策略.py

from abc import ABC, abstractmethod
from typing import List, Optional, Any, Dict # 添加了 Dict
from datetime import datetime

# 假设Event和特定的事件类型是可以访问的，例如，通过更高级别的包
# 目前，我们假设直接导入路径，或者在构建回测器时会进行调整
from ..core.event import MarketEvent, SignalEvent, EventType # 相对导入，添加了 EventType
# from backtesting_framework.core.event import MarketEvent, SignalEvent # 如果结构允许，则绝对导入

# 如果Portfolio对象很复杂，则进行类型提示的预先声明
# from ..core.portfolio import Portfolio # 或者是它的快照/接口

class Strategy(ABC):
    """
    所有交易策略的抽象基类。
    
    Strategy对象的作用是根据MarketEvents（或其他数据）生成SignalEvents。
    """
    def __init__(self, strategy_id: str, description: Optional[str] = None, params: Optional[Dict[str, Any]] = None):
        """
        初始化基础策略。

        参数:
            strategy_id (str): 此策略实例的唯一标识符。
            description (Optional[str]): 策略的人类可读描述。
            params (Optional[Dict[str, Any]]): 策略特定的参数。
        """
        self.strategy_id = strategy_id
        self.description = description if description else self.__class__.__name__
        self.params = params if params else {}
        self.subscribed_tickers: List[str] = [] # 此策略感兴趣的股票代码列表

    def __repr__(self):
        return f"{self.__class__.__name__}(id='{self.strategy_id}', params={self.params})"

    def subscribe_tickers(self, tickers: List[str]):
        """
        允许策略指定它需要哪些股票代码的市场数据。
        DataHandler可以使用它来仅提供相关数据。
        """
        self.subscribed_tickers = list(set(self.subscribed_tickers + tickers)) # 避免重复

    @abstractmethod
    def calculate_signals(self, event: MarketEvent, 
                          # portfolio_snapshot: Optional[Any] = None, # 更复杂的状态
                          # historical_data: Optional[Any] = None      # 访问历史K线数据
                         ) -> List[SignalEvent]:
        """
        根据传入的市场事件以及可能的其他数据（如历史K线或投资组合状态）
        计算交易信号列表。

        参数:
            event (MarketEvent): 已发生的MarketEvent。
            # portfolio_snapshot: 当前投资组合状态的表示（可选）。
            # historical_data: 用于信号计算的历史数据的访问权限（可选）。

        返回:
            List[SignalEvent]: 策略生成的SignalEvent列表。
                               如果未生成信号，则返回空列表。
        """
        pass

# 具体策略示例（用于测试，稍后可移至单独文件）
class BuyAndHoldStrategy(Strategy):
    """
    一个简单的买入并持有策略。
    在第一个市场事件中购买指定资产的固定数量并持有它们。
    """
    def __init__(self, strategy_id: str, tickers_to_buy: Dict[str, float], 
                 description: Optional[str] = "在第一个数据事件中购买指定的股票代码并持有。",
                 params: Optional[Dict[str, Any]] = None):
        super().__init__(strategy_id, description, params)
        self.tickers_to_buy = tickers_to_buy # {"股票代码": 购买数量} 的字典
        self.bought_flags = {ticker: False for ticker in tickers_to_buy}
        self.subscribe_tickers(list(tickers_to_buy.keys()))

    def calculate_signals(self, event: MarketEvent) -> List[SignalEvent]:
        signals = []
        if event.event_type == EventType.MARKET and event.security_ticker in self.tickers_to_buy:
            ticker = event.security_ticker
            if not self.bought_flags[ticker]:
                quantity = self.tickers_to_buy[ticker]
                signals.append(
                    SignalEvent(
                        timestamp=event.timestamp,
                        security_ticker=ticker,
                        order_type="BUY", # 使用常量会更好：TransactionType.BUY
                        suggested_quantity=quantity
                    )
                )
                self.bought_flags[ticker] = True
                print(f"{self.strategy_id}: 为 {quantity} 数量的 {ticker} 在 {event.timestamp} 生成了买入信号")
        return signals

if __name__ == '__main__':
    # from ..core.event import EventType # 用于BuyAndHoldStrategy示例 # 此行已在上面导入
    from datetime import datetime

    # 示例用法
    # 1. 创建一个BuyAndHoldStrategy实例
    buy_hold_strat = BuyAndHoldStrategy(
        strategy_id="BH_AAPL_GOOG",
        tickers_to_buy={"AAPL": 10, "GOOG": 5}
    )
    print(buy_hold_strat)
    print(f"订阅的股票代码: {buy_hold_strat.subscribed_tickers}")

    # 2. 模拟一个MarketEvent
    market_event_aapl = MarketEvent(
        timestamp=datetime(2023, 1, 1, 10, 0, 0),
        security_ticker="AAPL",
        new_price=150.00
    )
    market_event_msft = MarketEvent( # 一个不在购买列表中的股票代码
        timestamp=datetime(2023, 1, 1, 10, 0, 0),
        security_ticker="MSFT",
        new_price=300.00
    )
    market_event_goog = MarketEvent(
        timestamp=datetime(2023, 1, 1, 10, 5, 0),
        security_ticker="GOOG",
        new_price=2500.00
    )

    # 3. 计算信号
    signals_aapl = buy_hold_strat.calculate_signals(market_event_aapl)
    print(f"来自 AAPL 事件的信号: {signals_aapl}")

    signals_msft = buy_hold_strat.calculate_signals(market_event_msft)
    print(f"来自 MSFT 事件的信号 (应为空): {signals_msft}")
    
    signals_goog = buy_hold_strat.calculate_signals(market_event_goog)
    print(f"来自 GOOG 事件的信号: {signals_goog}")

    # 模拟AAPL的另一个事件（不应生成新信号，因为它已经被“购买”）
    market_event_aapl_later = MarketEvent(
        timestamp=datetime(2023, 1, 2, 10, 0, 0),
        security_ticker="AAPL",
        new_price=152.00
    )
    signals_aapl_later = buy_hold_strat.calculate_signals(market_event_aapl_later)
    print(f"来自稍后 AAPL 事件的信号 (应为空): {signals_aapl_later}")

    print(f"事件发生后的策略状态: {buy_hold_strat.bought_flags}")
```

[end of backtesting_framework/strategy/base_strategy.py]
