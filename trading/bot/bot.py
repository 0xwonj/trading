from logging import Logger

from trading.action.buy import Buy
from trading.action.sell import Sell
from trading.bot.event_bus import EventBus
from trading.model.event import Event, EventType
from trading.model.protocols import Action, Strategy
from trading.model.token import Token, TokenMeta, TokenRegistry
from trading.strategy.buy.copy import CopyStrategy
from trading.utils.logger import create_bot_logger


class Bot:
    def __init__(self, name: str):
        self.name: str = name
        self.logger: Logger = create_bot_logger(name)
        self._strategies: dict[EventType, Strategy] = {}
        self._actions: dict[str, Action] = {}  # Maps action names to actions
        # Portfolio keyed by (token.address, token.network)
        self._portfolio: dict[TokenMeta, float] = {}
        self._event_bus = EventBus()
        self.logger.info(f"Bot '{name}' initialized")

    @property
    def portfolio(self) -> dict[TokenMeta, float]:
        """
        Get a copy of the current portfolio.

        :return: Dictionary mapping token metadata to quantities
        """
        return self._portfolio.copy()

    def update_portfolio(self, token_key: TokenMeta, new_quantity: float) -> None:
        """
        Update the quantity of a token in the portfolio.

        :param token_key: Tuple of (token.address, token.network)
        :param new_quantity: New quantity to set
        """
        if new_quantity < 0:
            raise ValueError("Portfolio quantity cannot be negative")
        self._portfolio[token_key] = new_quantity

    def add_to_portfolio(self, token_key: TokenMeta, quantity: float) -> None:
        """
        Add quantity to a token position in the portfolio.

        :param token_key: Tuple of (token.address, token.network)
        :param quantity: Quantity to add (can be negative for reduction)
        """
        current = self._portfolio.get(token_key, 0)
        new_quantity = current + quantity
        if new_quantity < 0:
            raise ValueError("Portfolio quantity cannot be negative")
        self._portfolio[token_key] = new_quantity

    def get_position(self, token_key: TokenMeta) -> float:
        """
        Get the current position of a token.

        :param token_key: Tuple of (token.address, token.network)
        :return: Current quantity held
        """
        return self._portfolio.get(token_key, 0)

    def get_strategy(self, event_type: EventType) -> Strategy | None:
        """
        Get a registered strategy for a specific event type.

        :param event_type: The type of event to get strategy for
        :return: The strategy if registered, None otherwise
        """
        return self._strategies.get(event_type)

    def set_strategy(self, event_type: EventType, strategy: Strategy) -> None:
        """
        Register a strategy for a specific event type and subscribe to events.

        :param event_type: The type of event to register strategy for
        :param strategy: The strategy instance to register
        """
        self._strategies[event_type] = strategy
        # Subscribe to the event type with the handle_event method
        self._event_bus.subscribe(event_type, self.handle_event)
        self.logger.info(f"Registered strategy for {event_type}")

    def remove_strategy(self, event_type: EventType) -> None:
        """
        Remove a strategy for a specific event type and unsubscribe from events.

        :param event_type: The type of event to remove strategy for
        """
        if event_type in self._strategies:
            self._event_bus.unsubscribe(event_type, self.handle_event)
            del self._strategies[event_type]
            self.logger.info(f"Removed strategy for {event_type}")

    def unsubscribe_all(self) -> None:
        """
        Unsubscribe from all event types this bot is subscribed to.
        Called when the bot is being removed from the manager.
        """
        for event_type in list(self._strategies.keys()):
            self.remove_strategy(event_type)
        self.logger.info("Unsubscribed from all events")

    def set_action(self, action_name: str, action: Action) -> None:
        """
        Register an action by name.

        :param action_name: The name to register the action under
        :param action: The action instance to register
        """
        self._actions[action_name] = action
        self.logger.info(f"Registered action: {action_name}")

    def get_action(self, action_name: str) -> Action | None:
        """
        Get a registered action by name.

        :param action_name: Name of the action to retrieve
        :return: The action if registered, None otherwise
        """
        return self._actions.get(action_name.upper())

    async def handle_event(self, event: Event) -> None:
        """
        Handle an event using the registered strategy.
        This method is called by the event bus when a subscribed event occurs.

        :param event: The event to handle
        """
        self.logger.debug(f"Handling event: {event.event_type}")
        try:
            strategy = self._strategies.get(event.event_type)
            if strategy:
                await strategy.execute(event.data, self)
                self.logger.info(f"Executed strategy for {event.event_type}")
            else:
                self.logger.warning(f"No strategy registered for {event.event_type}")
        except Exception as e:
            self.logger.error(f"Error handling event: {str(e)}", exc_info=True)


if __name__ == "__main__":
    import asyncio

    async def main():
        # Create an instance of the bot
        bot = Bot("CopyTradingBot")

        # Set up token
        sol_token = ("0x0", "solana")
        TokenRegistry.set_token(
            Token(sol_token[0], sol_token[1], "Sol", "SOL", 1.0, 1_000_000)
        )

        # Initialize the Portfolio with some initial holdings
        bot.update_portfolio(sol_token, 1000)  # 1000 units of SOL

        # Set up trader weights
        trader_weights = {
            "trader1_wallet": 0.5,  # Copy 50% of trader1's trades
            "trader2_wallet": 1.0,  # Copy 100% of trader2's trades
        }

        # Register strategies and actions
        copy_strategy = CopyStrategy(trader_weights)
        bot.set_strategy(EventType.RAY_BOT, copy_strategy)
        bot.set_action("buy", Buy(sol_token))
        bot.set_action("sell", Sell(sol_token))

        # Test events
        test_events = [
            Event(
                EventType.RAY_BOT,
                {
                    "wallet": "trader1_wallet",
                    "action": "buy",
                    "token": {
                        "address": "0x123",
                        "network": "solana",
                        "name": "Token X",
                        "symbol": "TKX",
                        "price": 10.0,
                    },
                    "amount": 100,
                },
            ),
            Event(
                EventType.RAY_BOT,
                {
                    "wallet": "trader1_wallet",
                    "action": "sell",
                    "token": {
                        "address": "0x123",
                        "network": "solana",
                        "name": "Token X",
                        "symbol": "TKX",
                        "price": 12.0,
                    },
                    "amount": 50,
                },
            ),
        ]

        # Process test events
        for event in test_events:
            await bot._event_bus.publish(event)

        # Display the final portfolio state
        print("\nFinal portfolio state:")
        portfolio = bot.portfolio
        for key, qty in portfolio.items():
            token = TokenRegistry.get_token(key[0], key[1])
            print(f"{token.symbol}: {qty}")

    # Run the async main function
    asyncio.run(main())
