# backtesting_framework/backtester.py
# backtesting_framework/回测器.py

from datetime import datetime, timedelta
from typing import Optional, Type

from .core.event_queue import EventQueue
from .core.event import MarketEvent, SignalEvent, OrderEvent, FillEvent, DividendEvent, Event, EventType
from .core.portfolio import Portfolio
from .core.transaction import Transaction, TransactionType
# DataHandler, Strategy, ExecutionHandler 现在将作为类型提示
# from .data.data_handler import BaseDataHandler # 占位符
# from .strategy.base_strategy import Strategy # 占位符
# from .execution.execution_handler import BaseExecutionHandler # 占位符

# 为了类型提示而预先声明，以避免具体类在此处时的循环导入
BaseDataHandler = "BaseDataHandler"
Strategy = "Strategy"
BaseExecutionHandler = "BaseExecutionHandler"


class Backtester:
    """
    主回测引擎。协调不同组件（DataHandler, Strategy, Portfolio, ExecutionHandler）之间
    事件和数据的流动。
    """
    def __init__(self,
                 start_date: datetime,
                 end_date: datetime,
                 initial_cash: float,
                 data_handler: Type[BaseDataHandler], # 实际的DataHandler实例
                 strategy: Type[Strategy],           # 实际的Strategy实例
                 execution_handler: Type[BaseExecutionHandler], # 实际的ExecutionHandler实例
                 portfolio_class: Type[Portfolio] = Portfolio,
                 event_queue_class: Type[EventQueue] = EventQueue,
                 benchmark_ticker: Optional[str] = None):
        """
        初始化回测器。

        参数:
            start_date (datetime): 回测的开始日期。
            end_date (datetime): 回测的结束日期。
            initial_cash (float): 投资组合的初始现金。
            data_handler: DataHandler的一个实例。
            strategy: Strategy的一个实例。
            execution_handler: ExecutionHandler的一个实例。
            portfolio_class (Type[Portfolio]): 用于投资组合的类。
            event_queue_class (Type[EventQueue]): 用于事件队列的类。
            benchmark_ticker (Optional[str]): 用于基准比较的代码（例如 SPY）。
        """
        self.start_date = start_date
        self.end_date = end_date
        self.initial_cash = initial_cash
        self.benchmark_ticker = benchmark_ticker # 核心循环中尚未使用

        self.event_queue = event_queue_class()
        self.data_handler = data_handler
        self.strategy = strategy
        self.execution_handler = execution_handler
        
        # 使用start_date和initial_cash初始化Portfolio
        self.portfolio = portfolio_class(initial_cash=self.initial_cash, start_date=self.start_date)

        self._continue_backtest = True
        self.current_simulation_time = self.start_date

        # 将策略订阅的代码添加到data_handler
        if hasattr(self.strategy, 'subscribed_tickers') and hasattr(self.data_handler, 'subscribe_tickers'):
            self.data_handler.subscribe_tickers(self.strategy.subscribed_tickers)
            if self.benchmark_ticker:
                 self.data_handler.subscribe_tickers([self.benchmark_ticker])


    def _process_event(self, event: Event):
        """
        处理来自事件队列的单个事件。
        """
        if event is None:
            return

        # 将投资组合的当前时间更新为事件的时间戳
        # 这对于一致的记录保存和决策制定非常重要
        if event.timestamp > self.portfolio.current_datetime:
             self.portfolio.update_datetime(event.timestamp)

        if event.event_type == EventType.MARKET:
            # 用新的市场价格更新投资组合（用于盈亏、按市值计价）
            # event.new_price 通常是收盘价
            self.portfolio.update_holding_price(event.security_ticker, event.new_price)
            
            # 让策略处理市场数据
            signal_events = self.strategy.calculate_signals(event) # 可以传递 portfolio_snapshot
            for signal_event in signal_events:
                self.event_queue.put_event(signal_event)

        elif event.event_type == EventType.SIGNAL:
            # 投资组合将信号转换为订单（应用风险管理、规模控制）
            # 目前，一个简单的转换：
            # 这部分需要针对实际订单生成逻辑进行重大增强
            # 例如，检查现金、头寸限制、根据信号强度计算实际数量等。
            if event.suggested_quantity is None or event.suggested_quantity <= 0:
                print(f"回测器：{event.security_ticker}的SignalEvent没有数量或数量无效。已忽略。")
                return

            order_event = OrderEvent(
                timestamp=event.timestamp,
                security_ticker=event.security_ticker,
                order_type=event.order_type, # 买入/卖出
                quantity=event.suggested_quantity,
                order_kind="MARKET" # 默认为市价单
            )
            self.event_queue.put_event(order_event)

        elif event.event_type == EventType.ORDER:
            # 执行处理器处理订单
            # 对于市价单，它需要当前的市场价格。
            # 这意味着data_handler必须能够提供此信息。
            current_price = self.data_handler.get_latest_price(event.security_ticker, event.timestamp)
            if current_price is None:
                print(f"回测器：无法获取{event.security_ticker}的当前价格以执行订单。订单已忽略。")
                return

            fill_event = self.execution_handler.execute_order(event, current_price)
            if fill_event:
                self.event_queue.put_event(fill_event)

        elif event.event_type == EventType.FILL:
            # 投资组合根据成交回报更新其状态
            transaction = Transaction(
                timestamp=event.timestamp,
                security_ticker=event.security_ticker,
                transaction_type=event.order_type, # FillEvent的order_type应该是买入/卖出
                quantity=event.quantity_filled,
                price=event.fill_price,
                commission=event.commission,
                order_id=event.order_id
            )
            try:
                self.portfolio.execute_transaction(transaction)
            except ValueError as e:
                print(f"回测器：执行交易时出错：{e}。成交事件：{event}")


        elif event.event_type == EventType.DIVIDEND:
            # 投资组合处理股息支付
            # 这要求投资组合有一个类似 process_dividend_payment 的方法
            self.portfolio.process_dividend_payment(event) # 假设此方法存在

        # 根据需要添加其他事件类型

    def run_backtest(self):
        """
        运行主回测事件循环。
        """
        print(f"从 {self.start_date} 到 {self.end_date} 开始回测...")
        print(f"初始投资组合: {self.portfolio}")

        last_recorded_date = None

        while self._continue_backtest:
            # 1. 从DataHandler获取下一个市场数据更新
            # 此方法应产生MarketEvents和可能的DividendEvents
            # 它还应更新self.current_simulation_time
            new_events = self.data_handler.stream_next() # 返回事件列表（市场、股息等）

            if not new_events and self.event_queue.is_empty():
                # data_handler没有更多数据，并且事件队列为空
                self._continue_backtest = False
                break
            
            for new_event in new_events:
                if new_event.timestamp > self.end_date:
                    self._continue_backtest = False # 如果数据超出指定的结束日期，则停止
                    break
                self.event_queue.put_event(new_event)
                self.current_simulation_time = new_event.timestamp
            
            if not self._continue_backtest: # 检查是否满足结束日期条件
                break


            # 2. 处理队列中的事件
            while not self.event_queue.is_empty():
                event = self.event_queue.get_event()
                if event:
                    if event.timestamp > self.end_date: # 确保在结束日期之后不处理任何事件
                        continue
                    self._process_event(event)
            
            # 3. 投资组合内务处理（例如，日终处理）
            # 如果日期已更改或者是第一天，则记录每日快照
            # 这个逻辑需要稳健
            current_event_date = self.current_simulation_time.date()
            if last_recorded_date is None or current_event_date > last_recorded_date:
                # 这是新的一天或第一个快照。
                # 确保它不超出回测结束日期。
                snapshot_time = datetime.combine(current_event_date, datetime.min.time()) # 或每日结束时间
                if snapshot_time.date() <= self.end_date.date():
                     # 为每日快照使用一致的时间，例如，收盘时间或仅日期部分
                    self.portfolio.record_daily_snapshot(self.current_simulation_time) # 或固定的每日结束时间
                    last_recorded_date = current_event_date

            # 检查模拟时间是否已超过结束日期
            if self.current_simulation_time.date() >= self.end_date.date() and self.event_queue.is_empty():
                 # 如果结束日期（或之前）的所有事件都已处理完毕。
                self._continue_backtest = False


        print(f"回测完成。模拟时间：{self.current_simulation_time}")
        print(f"最终投资组合: {self.portfolio}")
        # 如果尚未拍摄，则在最后一天拍摄最终快照
        if last_recorded_date is None or last_recorded_date < self.end_date.date():
            if self.portfolio.current_datetime <= self.end_date : # 确保我们不会为将来记录
                 self.portfolio.record_daily_snapshot(self.portfolio.current_datetime) # 或 self.end_date

    def get_results(self) -> dict:
        """
        返回回测结果。
        这通常包括每日投资组合记录、交易历史等。
        """
        return {
            "daily_records": self.portfolio.daily_records,
            "transactions_history": self.portfolio.transactions_history,
            # 稍后在此处添加性能指标
        }

# 注意：实际的DataHandler、Strategy和ExecutionHandler类
# 将在设置回测时导入和实例化。
# `BaseDataHandler` 需要像 `stream_next()` 和 `get_latest_price()` 这样的方法。
# 如果使用DividendEvents，`Portfolio` 需要 `process_dividend_payment()`。
# `Strategy` 需要 `calculate_signals(MarketEvent)`。
# `ExecutionHandler` 需要 `execute_order(OrderEvent, current_price)`。
