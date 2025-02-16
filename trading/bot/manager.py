from typing import Optional

from trading.bot.bot import Bot


class BotManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BotManager, cls).__new__(cls)
            cls._instance._bots = {}
        return cls._instance

    def __init__(self) -> None:
        # A dictionary mapping bot names to Bot instances
        self._bots: dict[str, Bot] = {}

    def register_bot(self, bot: Bot) -> None:
        """
        Add a bot to the manager.

        :param bot: A Bot instance to be added
        """
        self._bots[bot.name] = bot
        print(f"Added bot: {bot.name}")

    def get_bot(self, bot_name: str) -> Optional[Bot]:
        """
        Get a bot from the manager by its name.

        :param bot_name: The name of the bot to get
        :return: The Bot instance if found, None otherwise
        """
        return self._bots.get(bot_name)

    def remove_bot(self, bot_name: str) -> None:
        """
        Remove a bot from the manager by its name.
        This will also unsubscribe the bot from all events.

        :param bot_name: The name of the bot to remove
        """
        if bot_name in self._bots:
            bot = self._bots[bot_name]
            bot.unsubscribe_all()  # Unsubscribe from all events
            del self._bots[bot_name]
            print(f"Removed bot: {bot_name}")
        else:
            print(f"Bot '{bot_name}' not found in manager")
