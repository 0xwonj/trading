from typing import Callable, Awaitable

from telegram.model.protocols import TelegramEvent
from telegram.model.models import RayMessage
from trading.bot.manager import BotManager
from trading.model.event import Event, EventType


async def print_handler(event: TelegramEvent):
    print(event.raw_text)


def create_raybot_handler(
    bot_manager: BotManager,
) -> Callable[[TelegramEvent], Awaitable[None]]:
    """
    Returns an asynchronous event handler function that processes a TelegramEvent
    by parsing it into a RayMessage, converting it into an Event, and then dispatching it
    via the provided BotManager.

    :param bot_manager: An instance of BotManager to dispatch events to the appropriate bots.
    :return: An async function that accepts a TelegramEvent.
    """

    async def raybot_handler(event: TelegramEvent) -> None:
        # Parse the raw text into a RayMessage.
        ray_message = RayMessage.from_text(event.raw_text)
        # Convert the RayMessage into an Event (with type RAY_BOT).
        ray_event = Event(EventType.RAY_BOT, ray_message)
        # Dispatch the event to all bots registered in the BotManager.
        bot_manager.dispatch_event(ray_event)
        # Optionally, you can print a message to confirm the dispatch.
        print("Dispatched RAY_BOT event to BotManager.")

    return raybot_handler
