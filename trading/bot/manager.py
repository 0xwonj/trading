from collections import defaultdict
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from provider.dexscreener.poller import DexScreenerPoller
    from trading.bot.bot import Bot


class BotManager:
    _instance = None

    def __new__(cls, dexscreener_poller: "DexScreenerPoller"):
        if cls._instance is None:
            cls._instance = super(BotManager, cls).__new__(cls)
            cls._instance._bots = {}
            cls._instance._token_subscribers = defaultdict(
                int
            )  # (network, address) -> count
            cls._instance._dexscreener_poller = dexscreener_poller
        return cls._instance

    def __init__(self, dexscreener_poller: "DexScreenerPoller") -> None:
        # Initialize only if not already initialized
        if not hasattr(self, "_bots"):
            self._bots: dict[str, Bot] = {}
            self._token_subscribers: dict[tuple[str, str], int] = defaultdict(
                int
            )  # (network, address) -> count
            self._dexscreener_poller = dexscreener_poller

    def register_bot(self, bot: "Bot") -> None:
        """
        Add a bot to the manager.

        :param bot: A Bot instance to be added
        """
        self._bots[bot.name] = bot
        bot.logger.info(f"Added bot: {bot.name}")

    def get_bot(self, bot_name: str) -> Optional["Bot"]:
        """
        Get a bot from the manager by its name.

        :param bot_name: The name of the bot to get
        :return: The Bot instance if found, None otherwise
        """
        return self._bots.get(bot_name)

    def remove_bot(self, bot_name: str) -> None:
        """
        Remove a bot from the manager by its name.
        This will also unsubscribe the bot from all events and remove it from token subscriptions.

        :param bot_name: The name of the bot to remove
        """
        if bot_name in self._bots:
            bot = self._bots[bot_name]
            bot.unsubscribe_all()  # Unsubscribe from all events

            # Remove bot from all token subscriptions
            for token_key in list(self._token_subscribers.keys()):
                self.unsubscribe_token(token_key[0], token_key[1])

            del self._bots[bot_name]
            bot.logger.info(f"Removed bot: {bot_name}")
        else:
            print(f"Bot '{bot_name}' not found in manager")

    def subscribe_token(self, network: str, token_address: str) -> None:
        """
        Subscribe to a token.

        Args:
            network: Network name (e.g., "solana")
            token_address: Token address
        """
        token_key = (network, token_address)

        # If this is the first subscriber, subscribe to the poller
        if self._token_subscribers[token_key] == 0:
            self._dexscreener_poller.subscribe(network, token_address)

        self._token_subscribers[token_key] += 1

    def unsubscribe_token(self, network: str, token_address: str) -> None:
        """
        Unsubscribe from a token.

        Args:
            network: Network name (e.g., "solana")
            token_address: Token address
        """
        token_key = (network, token_address)
        if token_key in self._token_subscribers:
            self._token_subscribers[token_key] -= 1

            # If no more subscribers, unsubscribe from the poller and clean up
            if self._token_subscribers[token_key] <= 0:
                self._dexscreener_poller.unsubscribe(network, token_address)
                del self._token_subscribers[token_key]

    def get_token_subscriber_count(self, network: str, token_address: str) -> int:
        """
        Get the number of subscribers for a token.

        Args:
            network: Network name (e.g., "solana")
            token_address: Token address

        Returns:
            Number of subscribers for the token
        """
        return self._token_subscribers.get((network, token_address), 0)
