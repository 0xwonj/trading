import asyncio
from collections import defaultdict
from typing import Callable, Coroutine

from trading.model.event import Event, EventType


class EventBus:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EventBus, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._subscribers: dict[
                EventType, list[Callable[[Event], Coroutine[any, any, None]]]
            ] = defaultdict(list)
            self._initialized = True

    def subscribe(
        self,
        event_type: EventType,
        callback: Callable[[Event], Coroutine[any, any, None]],
    ) -> None:
        """
        Subscribe to an event type with an async callback function.

        :param event_type: The type of event to subscribe to
        :param callback: The async callback function to be called when event occurs
        """
        self._subscribers[event_type].append(callback)
        print(f"Subscribed to {event_type}")

    def unsubscribe(
        self,
        event_type: EventType,
        callback: Callable[[Event], Coroutine[any, any, None]],
    ) -> None:
        """
        Unsubscribe from an event type.

        :param event_type: The type of event to unsubscribe from
        :param callback: The async callback function to remove
        """
        if callback in self._subscribers[event_type]:
            self._subscribers[event_type].remove(callback)
            print(f"Unsubscribed from {event_type}")

    async def publish(self, event: Event) -> None:
        """
        Publish an event to all subscribers asynchronously.
        All subscriber callbacks are executed concurrently using asyncio.gather.

        :param event: The event to publish
        """
        if self._subscribers[event.event_type]:
            await asyncio.gather(
                *(callback(event) for callback in self._subscribers[event.event_type])
            )
