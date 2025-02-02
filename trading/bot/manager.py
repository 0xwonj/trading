from trading.bot.core import Bot
from trading.model.event import Event


class BotManager:
    def __init__(self) -> None:
        # A dictionary mapping bot names to Bot instances.
        self.bots: dict[str, Bot] = {}

    def add_bot(self, bot: Bot) -> None:
        """
        Add a bot to the manager.

        :param bot: A Bot instance to be added.
        """
        self.bots[bot.name] = bot
        print(f"Added bot: {bot.name}")

    def remove_bot(self, bot_name: str) -> None:
        """
        Remove a bot from the manager by its name.

        :param bot_name: The name of the bot to remove.
        """
        if bot_name in self.bots:
            del self.bots[bot_name]
            print(f"Removed bot: {bot_name}")
        else:
            print(f"Bot '{bot_name}' not found in manager.")

    def dispatch_event(self, event: Event) -> None:
        """
        Dispatch an event to all bots that have a strategy registered for
        the event type.

        :param event: An Event object containing event type and data.
        """
        for bot in self.bots.values():
            if event.event_type in bot.strategies:
                bot.send_event(event.event_type, event.data)
                print(f"Dispatched event {event.event_type} to bot '{bot.name}'.")
            else:
                print(
                    f"Bot '{bot.name}' does not handle event type {event.event_type}."
                )

    def process_all_events(self) -> None:
        """
        Instruct every managed bot to process its internal event queue.
        """
        for bot in self.bots.values():
            bot.process_events()
            print(f"Processed events for bot '{bot.name}'.")
