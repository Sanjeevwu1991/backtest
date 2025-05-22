# backtesting_framework/execution/execution_handler.py
# backtesting_framework/执行/执行处理器.py

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

# 假设Event和特定的事件类型是可以访问的
from ..core.event import OrderEvent, FillEvent
# from backtesting_framework.core.event import OrderEvent, FillEvent # 绝对导入
from ..core.transaction import TransactionType # 为了FillEvent中order_type的一致性

# 如果需要Security类或当前价格的数据结构：
# from ..core.security import Security # 或者一个更简单的价格提供者接口

class BaseExecutionHandler(ABC):
    """
    所有执行处理器的抽象基类。
    执行处理器负责接收OrderEvents并模拟它们的执行，从而产生FillEvents。
    """
    def __init__(self, handler_id: str, description: Optional[str] = None):
        self.handler_id = handler_id
        self.description = description if description else self.__class__.__name__

    def __repr__(self):
        return f"{self.__class__.__name__}(id='{self.handler_id}')"

    @abstractmethod
    def execute_order(self, order_event: OrderEvent, 
                      current_market_price: Optional[float] = None,
                      # data_handler: Optional[Any] = None # 如果未传递，则用于获取当前价格
                     ) -> Optional[FillEvent]:
        """
        模拟订单的执行。

        参数:
            order_event (OrderEvent): 要执行的订单。
            current_market_price (Optional[float]): 证券的当前市场价格。
                                                   简单处理器处理市价单时需要。
            # data_handler: 如果未提供，可用于获取当前价格。

        返回:
            Optional[FillEvent]: 如果订单成功执行，则返回FillEvent；
                                 否则返回None（例如，资金不足，订单无效）。
        """
        pass

class SimpleExecutionHandler(BaseExecutionHandler):
    """
    一个简单的执行处理器，它模拟以提供的市场价格立即成交。
    它可以应用固定佣金或基于百分比的佣金。
    除了使用给定价格外，不模拟市价单的滑点。
    """
    def __init__(self, handler_id: str = "SimpleExec", 
                 commission_per_share: float = 0.005, 
                 pct_commission: float = 0.00, # 例如，0.001 代表 0.1%
                 min_commission: float = 1.0,
                 description: Optional[str] = "简单的按市价成交执行，带佣金。"):
        super().__init__(handler_id, description)
        self.commission_per_share = commission_per_share
        self.pct_commission = pct_commission
        self.min_commission = min_commission

    def _calculate_commission(self, quantity: float, price: float) -> float:
        """计算交易佣金。"""
        commission = 0.0
        if self.commission_per_share > 0:
            commission += quantity * self.commission_per_share
        if self.pct_commission > 0:
            commission += quantity * price * self.pct_commission
        
        return max(commission, self.min_commission) if quantity > 0 else 0.0

    def execute_order(self, order_event: OrderEvent, 
                      current_market_price: Optional[float] = None) -> Optional[FillEvent]:
        """
        模拟订单成交。对于 'MARKET' 订单，需要 current_market_price。
        此简单处理器不支持限价单。

        参数:
            order_event (OrderEvent): 要执行的订单。
            current_market_price (Optional[float]): 市价单的成交价格。

        返回:
            Optional[FillEvent]: 生成的FillEvent，如果订单无法处理则为None。
        """
        if order_event.order_kind != "MARKET":
            print(f"{self.handler_id}: 警告 - 仅支持 MARKET 订单。订单 {order_event} 已忽略。")
            return None

        if current_market_price is None:
            print(f"{self.handler_id}: 错误 - MARKET 订单需要 current_market_price。订单 {order_event} 已忽略。")
            return None
        
        if current_market_price <= 0:
            print(f"{self.handler_id}: 错误 - 无效的市场价格 ({current_market_price})。订单 {order_event} 已忽略。")
            return None

        if order_event.quantity <= 0:
            print(f"{self.handler_id}: 错误 - 订单数量必须为正。订单 {order_event} 已忽略。")
            return None

        fill_price = current_market_price # 此简单处理器中没有滑点模拟
        commission = self._calculate_commission(order_event.quantity, fill_price)
        
        # 在FillEvent中使用TransactionType常量作为order_type以保持一致性
        # 这假设order_event.order_type是 'BUY' 或 'SELL'
        fill_order_type = order_event.order_type 
        if order_event.order_type.upper() == TransactionType.BUY:
            fill_order_type = TransactionType.BUY
        elif order_event.order_type.upper() == TransactionType.SELL:
            fill_order_type = TransactionType.SELL
        else:
            print(f"{self.handler_id}: 错误 - 未知的订单类型 '{order_event.order_type}'。订单已忽略。")
            return None


        fill_event = FillEvent(
            timestamp=order_event.timestamp, # 或当前时间: datetime.now(timezone.utc)
            security_ticker=order_event.security_ticker,
            order_type=fill_order_type,
            quantity_filled=order_event.quantity,
            fill_price=fill_price,
            commission=commission,
            order_id=None # 如果原始order_event有ID，则链接到它
        )
        # print(f"{self.handler_id}: 已执行订单 {order_event}, 成交: {fill_event}")
        return fill_event

if __name__ == '__main__':
    from datetime import datetime, timezone
    # 示例用法
    exec_handler = SimpleExecutionHandler(commission_per_share=0.01, pct_commission=0.0005, min_commission=1.50)
    print(exec_handler)

    # 创建一个示例OrderEvent
    buy_order = OrderEvent(
        timestamp=datetime.now(timezone.utc),
        security_ticker="AAPL",
        order_type="BUY", # 理想情况下应使用 TransactionType.BUY
        quantity=100,
        order_kind="MARKET"
    )
    
    # 模拟执行
    market_price_aapl = 150.00
    fill = exec_handler.execute_order(buy_order, market_price_aapl)
    if fill:
        print(f"生成的成交回报: {fill}")
        print(f"成交成本 (数量*价格): {fill.cost}")
        assert fill.commission == max(100 * 0.01 + 100 * 150.00 * 0.0005, 1.50)
        assert fill.fill_price == market_price_aapl

    sell_order_invalid_type = OrderEvent(
        timestamp=datetime.now(timezone.utc),
        security_ticker="MSFT",
        order_type="SELL",
        quantity=50,
        order_kind="LIMIT" # 不支持
    )
    fill_limit = exec_handler.execute_order(sell_order_invalid_type, 280.00)
    if not fill_limit:
        print("限价单被简单处理器正确地未处理。")

    sell_order_no_price = OrderEvent(
        timestamp=datetime.now(timezone.utc),
        security_ticker="TSLA",
        order_type="SELL",
        quantity=10,
        order_kind="MARKET"
    )
    fill_no_price = exec_handler.execute_order(sell_order_no_price) # 没有市场价格
    if not fill_no_price:
        print("没有价格的市价单被正确地未处理。")
        
    buy_order_zero_qty = OrderEvent(
        timestamp=datetime.now(timezone.utc),
        security_ticker="NVDA",
        order_type="BUY", 
        quantity=0, # 零数量
        order_kind="MARKET"
    )
    fill_zero_qty = exec_handler.execute_order(buy_order_zero_qty, current_market_price=300.0)
    if not fill_zero_qty:
        print("零数量订单被正确地未处理。")

```

[end of backtesting_framework/execution/execution_handler.py]
