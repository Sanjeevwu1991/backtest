# backtesting_framework/backtester.py

from datetime import datetime, timedelta
from typing import Optional, Type

from .core.event_queue import EventQueue
from .core.event import MarketEvent, SignalEvent, OrderEvent, FillEvent, DividendEvent, Event, EventType
from .core.portfolio import Portfolio
from .core.transaction import Transaction, TransactionType
# DataHandler, Strategy, ExecutionHandler will be type hints for now
# from .data.data_handler import BaseDataHandler # Placeholder
# from .strategy.base_strategy import Strategy # Placeholder
# from .execution.execution_handler import BaseExecutionHandler # Placeholder

# Forward declare for type hinting to avoid circular imports if they were concrete classes here
BaseDataHandler = "BaseDataHandler"
Strategy = "Strategy"
BaseExecutionHandler = "BaseExecutionHandler"


class Backtester:
    """
    The main backtesting engine. Orchestrates the flow of events and data
    between different components (DataHandler, Strategy, Portfolio, ExecutionHandler).
    """
    def __init__(self,
                 start_date: datetime,
                 end_date: datetime,
                 initial_cash: float,
                 data_handler: Type[BaseDataHandler], # Actual DataHandler instance
                 strategy: Type[Strategy],           # Actual Strategy instance
                 execution_handler: Type[BaseExecutionHandler], # Actual ExecutionHandler instance
                 portfolio_class: Type[Portfolio] = Portfolio,
                 event_queue_class: Type[EventQueue] = EventQueue,
                 benchmark_ticker: Optional[str] = None):
        """
        Initializes the Backtester.

        Args:
            start_date (datetime): The start date of the backtest.
            end_date (datetime): The end date of the backtest.
            initial_cash (float): The initial cash for the portfolio.
            data_handler: An instance of a DataHandler.
            strategy: An instance of a Strategy.
            execution_handler: An instance of an ExecutionHandler.
            portfolio_class (Type[Portfolio]): The class to use for the portfolio.
            event_queue_class (Type[EventQueue]): The class to use for the event queue.
            benchmark_ticker (Optional[str]): Ticker for benchmark comparison (e.g. SPY).
        """
        self.start_date = start_date
        self.end_date = end_date
        self.initial_cash = initial_cash
        self.benchmark_ticker = benchmark_ticker # Not used in core loop yet

        self.event_queue = event_queue_class()
        self.data_handler = data_handler
        self.strategy = strategy
        self.execution_handler = execution_handler
        
        # Initialize Portfolio with start_date and initial_cash
        self.portfolio = portfolio_class(initial_cash=self.initial_cash, start_date=self.start_date)

        self._continue_backtest = True
        self.current_simulation_time = self.start_date

        # Subscribe strategy tickers to data_handler
        if hasattr(self.strategy, 'subscribed_tickers') and hasattr(self.data_handler, 'subscribe_tickers'):
            self.data_handler.subscribe_tickers(self.strategy.subscribed_tickers)
            if self.benchmark_ticker:
                 self.data_handler.subscribe_tickers([self.benchmark_ticker])


    def _process_event(self, event: Event):
        """
        Processes a single event from the event queue.
        """
        if event is None:
            return

        # Update portfolio's current time to the event's timestamp
        # This is important for consistent record keeping and decision making
        if event.timestamp > self.portfolio.current_datetime:
             self.portfolio.update_datetime(event.timestamp)

        if event.event_type == EventType.MARKET:
            # Update portfolio with new market price (for P&L, MTM)
            # The event.new_price is typically close price
            self.portfolio.update_holding_price(event.security_ticker, event.new_price)
            
            # Let strategy process market data
            signal_events = self.strategy.calculate_signals(event) # portfolio_snapshot could be passed
            for signal_event in signal_events:
                self.event_queue.put_event(signal_event)

        elif event.event_type == EventType.SIGNAL:
            # Portfolio converts signal to order (applies risk management, sizing)
            # For now, a simple conversion:
            # This part will need significant enhancement for actual order generation logic
            # e.g., checking cash, position limits, calculating actual quantity based on signal strength etc.
            if event.suggested_quantity is None or event.suggested_quantity <= 0:
                print(f"Backtester: SignalEvent for {event.security_ticker} has no or invalid quantity. Ignoring.")
                return

            order_event = OrderEvent(
                timestamp=event.timestamp,
                security_ticker=event.security_ticker,
                order_type=event.order_type, # BUY/SELL
                quantity=event.suggested_quantity,
                order_kind="MARKET" # Default to market order
            )
            self.event_queue.put_event(order_event)

        elif event.event_type == EventType.ORDER:
            # Execution handler processes the order
            # For market orders, it needs the current market price.
            # This implies data_handler must be able to provide this.
            current_price = self.data_handler.get_latest_price(event.security_ticker, event.timestamp)
            if current_price is None:
                print(f"Backtester: Could not get current price for {event.security_ticker} to execute order. Order ignored.")
                return

            fill_event = self.execution_handler.execute_order(event, current_price)
            if fill_event:
                self.event_queue.put_event(fill_event)

        elif event.event_type == EventType.FILL:
            # Portfolio updates its state based on the fill
            transaction = Transaction(
                timestamp=event.timestamp,
                security_ticker=event.security_ticker,
                transaction_type=event.order_type, # FillEvent's order_type should be BUY/SELL
                quantity=event.quantity_filled,
                price=event.fill_price,
                commission=event.commission,
                order_id=event.order_id
            )
            try:
                self.portfolio.execute_transaction(transaction)
            except ValueError as e:
                print(f"Backtester: Error executing transaction: {e}. Fill event: {event}")


        elif event.event_type == EventType.DIVIDEND:
            # Portfolio handles dividend payment
            # This requires the portfolio to have a method like process_dividend_payment
            self.portfolio.process_dividend_payment(event) # Assuming this method exists

        # Add other event types as needed

    def run_backtest(self):
        """
        Runs the main backtesting event loop.
        """
        print(f"Starting backtest from {self.start_date} to {self.end_date}...")
        print(f"Initial Portfolio: {self.portfolio}")

        last_recorded_date = None

        while self._continue_backtest:
            # 1. Get next market data update from DataHandler
            # This method should yield MarketEvents and potentially DividendEvents
            # It should also update self.current_simulation_time
            new_events = self.data_handler.stream_next() # Returns a list of events (Market, Dividend etc.)

            if not new_events and self.event_queue.is_empty():
                # No more data from data_handler and event queue is empty
                self._continue_backtest = False
                break
            
            for new_event in new_events:
                if new_event.timestamp > self.end_date:
                    self._continue_backtest = False # Stop if data goes beyond specified end_date
                    break
                self.event_queue.put_event(new_event)
                self.current_simulation_time = new_event.timestamp
            
            if not self._continue_backtest: # Check if end_date condition was met
                break


            # 2. Process events from the queue
            while not self.event_queue.is_empty():
                event = self.event_queue.get_event()
                if event:
                    if event.timestamp > self.end_date: # Ensure no event processing beyond end_date
                        continue
                    self._process_event(event)
            
            # 3. Portfolio housekeeping (e.g., end-of-day processing)
            # Record daily snapshot if the day has changed or it's the first day
            # This logic needs to be robust
            current_event_date = self.current_simulation_time.date()
            if last_recorded_date is None or current_event_date > last_recorded_date:
                # It's a new day or the very first snapshot.
                # Ensure it's not beyond the backtest end_date.
                snapshot_time = datetime.combine(current_event_date, datetime.min.time()) # Or end of day time
                if snapshot_time.date() <= self.end_date.date():
                     # Use a consistent time for daily snapshots, e.g., market close or just date part
                    self.portfolio.record_daily_snapshot(self.current_simulation_time) # Or a fixed EOD time
                    last_recorded_date = current_event_date

            # Check if simulation time has passed the end_date
            if self.current_simulation_time.date() >= self.end_date.date() and self.event_queue.is_empty():
                 # If all events for the end_date (or before) are processed.
                self._continue_backtest = False


        print(f"Backtest finished. Simulation time: {self.current_simulation_time}")
        print(f"Final Portfolio: {self.portfolio}")
        # Final snapshot on the very last day if not already taken
        if last_recorded_date is None or last_recorded_date < self.end_date.date():
            if self.portfolio.current_datetime <= self.end_date : # Ensure we don't record for future
                 self.portfolio.record_daily_snapshot(self.portfolio.current_datetime) # or self.end_date

    def get_results(self) -> dict:
        """
        Returns the results of the backtest.
        This would typically include daily portfolio records, transaction history, etc.
        """
        return {
            "daily_records": self.portfolio.daily_records,
            "transactions_history": self.portfolio.transactions_history,
            # Later, add performance metrics here
        }

# Note: The actual DataHandler, Strategy, and ExecutionHandler classes
# will be imported and instantiated when a backtest is set up.
# The `BaseDataHandler` needs methods like `stream_next()` and `get_latest_price()`.
# The `Portfolio` needs `process_dividend_payment()` if DividendEvents are used.
# The `Strategy` needs `calculate_signals(MarketEvent)`.
# The `ExecutionHandler` needs `execute_order(OrderEvent, current_price)`.
```
