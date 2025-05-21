# backtesting_framework/core/event_queue.py

import collections
from typing import Optional
from .event import Event # Assuming Event class is in event.py in the same directory

class EventQueue:
    """
    A simple event queue using collections.deque to store and manage events.
    Events are processed in FIFO order.
    """
    def __init__(self):
        self._queue = collections.deque()

    def __repr__(self):
        return f"EventQueue(size={len(self._queue)})"

    def put_event(self, event: Event):
        """
        Adds an event to the end of the queue.

        Args:
            event (Event): The event to be added.
        """
        if not isinstance(event, Event):
            # Or log a warning, or handle more gracefully depending on strictness
            raise ValueError("Only Event objects can be added to the EventQueue.")
        self._queue.append(event)

    def get_event(self) -> Optional[Event]:
        """
        Removes and returns an event from the front of the queue.
        Returns None if the queue is empty.
        """
        if not self._queue:
            return None
        return self._queue.popleft()

    def is_empty(self) -> bool:
        """
        Checks if the event queue is empty.

        Returns:
            bool: True if the queue is empty, False otherwise.
        """
        return len(self._queue) == 0
    
    @property
    def size(self) -> int:
        """
        Returns the current number of events in the queue.
        """
        return len(self._queue)

# Example Usage (for testing purposes)
if __name__ == '__main__':
    from .event import MarketEvent, EventType # Assuming EventType is also in event.py
    from datetime import datetime

    # Create an event queue
    eq = EventQueue()
    print(f"Initial queue: {eq}, Empty: {eq.is_empty()}, Size: {eq.size}")

    # Create some dummy events
    event1 = MarketEvent(timestamp=datetime.now(), security_ticker="AAPL", new_price=150.0)
    event2 = MarketEvent(timestamp=datetime.now(), security_ticker="GOOG", new_price=2500.0)

    # Put events into the queue
    eq.put_event(event1)
    eq.put_event(event2)
    print(f"Queue after adding events: {eq}, Empty: {eq.is_empty()}, Size: {eq.size}")

    # Get events from the queue
    retrieved_event1 = eq.get_event()
    print(f"Retrieved event 1: {retrieved_event1}")
    print(f"Queue after getting one event: {eq}, Size: {eq.size}")

    retrieved_event2 = eq.get_event()
    print(f"Retrieved event 2: {retrieved_event2}")
    print(f"Queue after getting second event: {eq}, Empty: {eq.is_empty()}, Size: {eq.size}")

    # Try to get from empty queue
    empty_event = eq.get_event()
    print(f"Retrieved from empty queue: {empty_event}")
    print(f"Final queue state: {eq}, Empty: {eq.is_empty()}, Size: {eq.size}")

    # Test adding non-Event type (should raise ValueError)
    try:
        eq.put_event("not an event")
    except ValueError as e:
        print(f"Caught expected error: {e}")
```
