# backtesting_framework/core/event.py
# backtesting_framework/核心/事件.py

from datetime import datetime
from typing import Optional, Any, Dict # 添加了Dict，因为它被使用了但未导入
from enum import Enum # 使用Enum来定义EventType，以便更好地组织

class EventType(Enum):
    MARKET = "MARKET"       # 新的市场数据（例如，价格更新）
    SIGNAL = "SIGNAL"       # 来自策略的交易信号
    ORDER = "ORDER"         # 发送给执行处理程序的订单
    FILL = "FILL"           # 订单已被执行
    DIVIDEND = "DIVIDEND"   # 股息支付
    # 根据需要添加更多事件类型（例如，SPLIT, INFO 等）

class Event:
    """
    所有事件的基类。
    """
    def __init__(self, event_type: EventType, timestamp: Optional[datetime] = None):
        self.event_type = event_type
        # 如果未提供时间戳，则使用当前的UTC时间。
        # 在回测中，时间戳理想情况下应由数据源或事件生成器提供。
        self.timestamp = timestamp if timestamp else datetime.utcnow()

    def __repr__(self):
        return (f"{self.__class__.__name__}(type={self.event_type.value}, "
                f"timestamp={self.timestamp.strftime('%Y-%m-%d %H:%M:%S')})")

class MarketEvent(Event):
    """
    处理接收新市场数据（例如，新的K线或报价）的事件。
    """
    def __init__(self, timestamp: datetime, security_ticker: str, new_price: float, other_data: Optional[Dict[str, Any]] = None):
        """
        参数:
            timestamp (datetime): 市场数据的时间。
            security_ticker (str): 接收数据的证券代码。
            new_price (float): 新价格（例如，K线的收盘价）。
            other_data (Optional[Dict[str, Any]]): 其他数据，如OHLCV（开高低收成交量）。
        """
        super().__init__(EventType.MARKET, timestamp)
        self.security_ticker = security_ticker
        self.new_price = new_price # 通常是K线的收盘价
        self.other_data = other_data if other_data else {} # 例如：{'open': o, 'high': h, 'low': l, 'volume': v}

    def __repr__(self):
        return (f"MarketEvent(timestamp={self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}, "
                f"ticker='{self.security_ticker}', price={self.new_price:.2f})")

class SignalEvent(Event):
    """
    处理从策略对象发送信号的事件。
    此信号随后由投资组合对象处理以生成OrderEvent。
    """
    def __init__(self, timestamp: datetime, security_ticker: str, order_type: str, suggested_quantity: Optional[float] = None, strength: Optional[float] = None):
        """
        参数:
            timestamp (datetime): 信号生成的时间。
            security_ticker (str): 证券代码。
            order_type (str): 'BUY' 或 'SELL'。（应使用枚举或像TransactionType这样的常量）
            suggested_quantity (Optional[float]): 要交易的单位数量。如果为None，则投资组合可能会决定。
            strength (Optional[float]): 表示信号强度/置信度的值（例如0.0到1.0）。
        """
        super().__init__(EventType.SIGNAL, timestamp)
        self.security_ticker = security_ticker
        self.order_type = order_type # 例如：'BUY', 'SELL'
        self.suggested_quantity = suggested_quantity
        self.strength = strength # 可选：用于更高级的投资组合分配

    def __repr__(self):
        return (f"SignalEvent(timestamp={self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}, "
                f"ticker='{self.security_ticker}', type='{self.order_type}', "
                f"quantity={self.suggested_quantity}, strength={self.strength})")

class OrderEvent(Event):
    """
    处理向执行系统发送订单的事件。
    订单包含证券代码、订单类型（买入/卖出）、数量和订单类型（市价/限价）。
    """
    def __init__(self, timestamp: datetime, security_ticker: str, order_type: str, quantity: float, order_kind: str = "MARKET"):
        """
        参数:
            timestamp (datetime): 订单创建的时间。
            security_ticker (str): 证券代码。
            order_type (str): 'BUY' 或 'SELL'。
            quantity (float): 要交易的非负单位数量。
            order_kind (str, optional): 订单类型，例如 'MARKET', 'LIMIT'。默认为 'MARKET'。
                                     （对于限价单，还需要价格）。
        """
        super().__init__(EventType.ORDER, timestamp)
        self.security_ticker = security_ticker
        self.order_type = order_type # 'BUY' 或 'SELL'
        self.quantity = quantity
        self.order_kind = order_kind # 'MARKET', 'LIMIT' 等。
        # 对于限价单，需要一个 self.price 属性。

    def __repr__(self):
        return (f"OrderEvent(timestamp={self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}, "
                f"ticker='{self.security_ticker}', type='{self.order_type}', "
                f"quantity={self.quantity}, kind='{self.order_kind}')")

class FillEvent(Event):
    """
    封装从经纪商返回的已执行订单的概念。
    存储实际成交的工具数量和价格。
    此外，还存储经纪商收取的交易佣金。
    """
    def __init__(self, timestamp: datetime, security_ticker: str, order_type: str, 
                 quantity_filled: float, fill_price: float, commission: float, 
                 exchange: Optional[str] = None, order_id: Optional[str] = None):
        """
        参数:
            timestamp (datetime): 成交时间。
            security_ticker (str): 证券代码。
            order_type (str): 'BUY' 或 'SELL'。
            quantity_filled (float): 成交的单位数量。
            fill_price (float): 订单成交的价格。
            commission (float): 支付的佣金。
            exchange (Optional[str]): 订单成交的交易所。
            order_id (Optional[str]): 此成交对应的原始订单ID。
        """
        super().__init__(EventType.FILL, timestamp)
        self.security_ticker = security_ticker
        self.order_type = order_type # 'BUY' 或 'SELL'
        self.quantity_filled = quantity_filled
        self.fill_price = fill_price
        self.commission = commission
        self.exchange = exchange
        self.order_id = order_id
        
        # 计算总成本/收益（从盈亏角度看，买入不包括佣金，卖出包括佣金）
        # 但对于现金调整，更简单：成本 = 数量 * 价格
        self.cost = self.quantity_filled * self.fill_price


    def __repr__(self):
        return (f"FillEvent(timestamp={self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}, "
                f"ticker='{self.security_ticker}', type='{self.order_type}', "
                f"quantity={self.quantity_filled}, price={self.fill_price:.2f}, "
                f"commission={self.commission:.2f})")

class DividendEvent(Event):
    """
    处理证券的股息支付事件。
    """
    def __init__(self, timestamp: datetime, security_ticker: str, dividend_per_share: float,
                 payment_date: Optional[datetime] = None, ex_date: Optional[datetime] = None):
        """
        参数:
            timestamp (datetime): 股息的公告日期或记录日期。
                                  对于回测，这通常是除息日。
            security_ticker (str): 支付股息的股票的证券代码。
            dividend_per_share (float): 每股股息的现金金额。
            payment_date (Optional[datetime]): 现金实际支付日期。
            ex_date (Optional[datetime]): 除息日。
        """
        super().__init__(EventType.DIVIDEND, timestamp) # 时间戳是回测的除息日
        self.security_ticker = security_ticker
        self.dividend_per_share = dividend_per_share
        self.payment_date = payment_date if payment_date else timestamp # 如果未指定，则假定在除息日支付
        self.ex_date = ex_date if ex_date else timestamp

    def __repr__(self):
        return (f"DividendEvent(timestamp={self.timestamp.strftime('%Y-%m-%d')}, "
                f"ticker='{self.security_ticker}', dividend_per_share={self.dividend_per_share:.2f})")

```

[end of backtesting_framework/core/event.py]
