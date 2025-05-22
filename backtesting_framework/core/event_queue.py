# backtesting_framework/core/event_queue.py
# backtesting_framework/核心/事件队列.py

import collections
from typing import Optional
from .event import Event # 假设Event类在同一目录下的event.py中

class EventQueue:
    """
    一个简单的事件队列，使用collections.deque来存储和管理事件。
    事件按先进先出（FIFO）的顺序处理。
    """
    def __init__(self):
        self._queue = collections.deque()

    def __repr__(self):
        return f"EventQueue(size={len(self._queue)})"

    def put_event(self, event: Event):
        """
        将事件添加到队列的末尾。

        参数:
            event (Event): 要添加的事件。
        """
        if not isinstance(event, Event):
            # 或者记录警告，或者根据严格程度更优雅地处理
            raise ValueError("只有Event对象才能添加到EventQueue中。")
        self._queue.append(event)

    def get_event(self) -> Optional[Event]:
        """
        从队列的前端移除并返回一个事件。
        如果队列为空，则返回None。
        """
        if not self._queue:
            return None
        return self._queue.popleft()

    def is_empty(self) -> bool:
        """
        检查事件队列是否为空。

        返回:
            bool: 如果队列为空则为True，否则为False。
        """
        return len(self._queue) == 0
    
    @property
    def size(self) -> int:
        """
        返回队列中当前的事件数量。
        """
        return len(self._queue)

# 示例用法（用于测试目的）
if __name__ == '__main__':
    from .event import MarketEvent, EventType # 假设EventType也在event.py中
    from datetime import datetime

    # 创建一个事件队列
    eq = EventQueue()
    print(f"初始队列: {eq}, 是否为空: {eq.is_empty()}, 大小: {eq.size}")

    # 创建一些虚拟事件
    event1 = MarketEvent(timestamp=datetime.now(), security_ticker="AAPL", new_price=150.0)
    event2 = MarketEvent(timestamp=datetime.now(), security_ticker="GOOG", new_price=2500.0)

    # 将事件放入队列
    eq.put_event(event1)
    eq.put_event(event2)
    print(f"添加事件后的队列: {eq}, 是否为空: {eq.is_empty()}, 大小: {eq.size}")

    # 从队列中获取事件
    retrieved_event1 = eq.get_event()
    print(f"取出的事件1: {retrieved_event1}")
    print(f"取出一个事件后的队列: {eq}, 大小: {eq.size}")

    retrieved_event2 = eq.get_event()
    print(f"取出的事件2: {retrieved_event2}")
    print(f"取出第二个事件后的队列: {eq}, 是否为空: {eq.is_empty()}, 大小: {eq.size}")

    # 尝试从空队列中获取
    empty_event = eq.get_event()
    print(f"从空队列中取出的事件: {empty_event}")
    print(f"最终队列状态: {eq}, 是否为空: {eq.is_empty()}, 大小: {eq.size}")

    # 测试添加非Event类型（应引发ValueError）
    try:
        eq.put_event("不是一个事件")
    except ValueError as e:
        print(f"捕获到预期错误: {e}")
```

[end of backtesting_framework/core/event_queue.py]
