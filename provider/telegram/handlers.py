from provider.telegram.model.models import RayMessage
from provider.telegram.model.protocols import TelegramEvent
from trading.bot.event_bus import EventBus
from trading.model.event import Event, EventType


async def print_handler(event: TelegramEvent) -> None:
    print(event.raw_text)


async def raybot_handler(event: TelegramEvent) -> None:
    """
    Processes a TelegramEvent by parsing it into a RayMessage and publishing it to the event bus.

    :param event: The telegram event to process
    """
    try:
        # Get the singleton instance of EventBus
        event_bus = EventBus()

        # Parse the raw text into a RayMessage
        ray_message = RayMessage.from_text(event.raw_text)

        # Create and publish the event
        ray_event = Event(EventType.RAY_BOT, ray_message)
        await event_bus.publish(ray_event)

        print("Successfully published RAY_BOT event to event bus")

    except Exception as e:
        print(f"Error processing telegram event: {str(e)}")
