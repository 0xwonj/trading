from collections import deque

from trading.model.event import Event, EventType
from trading.model.token import Token, TokenMeta, TokenRegistry
from trading.model.protocols import Action, Strategy
from trading.strategy.copy import CopyStrategy
from trading.action.buy import Buy
from trading.action.sell import Sell


class Bot:
    def __init__(self, name: str):
        self.name: str = name
        self.strategies: dict[EventType, Strategy] = {}

        self.actions: dict[str, Action] = {}  # Maps action names to actions
        # Portfolio keyed by (token.address, token.network)
        self.portfolio: dict[TokenMeta, float] = {}
        self.event_queue: deque[Event] = deque()  # Internal event queue

    def set_strategy(self, event_type: EventType, strategy: Strategy) -> None:
        """
        Register a strategy for a specific event type.
        """
        self.strategies[event_type] = strategy

    def set_action(self, action_name: str, action: Action) -> None:
        """
        Register an action by name.
        """
        self.actions[action_name] = action

    def send_event(self, event_type: EventType, data: any) -> None:
        """
        Enqueue an event for processing.
        """
        self.event_queue.append(Event(event_type, data))
        print(f"[Bot] Enqueued event {event_type}")

    def process_events(self) -> None:
        """
        Process all events in the queue.
        """
        while self.event_queue:
            event = self.event_queue.popleft()
            self.handle_event(event)

    def handle_event(self, event: Event) -> None:
        """
        Dispatch the event to the registered strategy.
        """
        strategy = self.strategies.get(event.event_type)
        if strategy:
            strategy.execute(event.data, self)
        else:
            print(f"[Bot] No strategy registered for event type {event.event_type}")


if __name__ == "__main__":
    # Create an instance of the bot.
    bot = Bot("CopyTradingBot")

    sol_token = ("0x0", "solana")
    TokenRegistry.set_token(
        Token(sol_token[0], sol_token[1], "Sol", "SOL", 1.0, 1_000_000)
    )
    # Initialize the Portfolio with some initial holdings.
    bot.portfolio = {
        sol_token: 1000,  # 100 units of Token X
    }

    # Hard-coded trader weights: mapping trader wallet addresses to weight multipliers.
    trader_weights = {
        "trader1_wallet": 0.5,  # Copy 50% of trader1's trades.
        "trader2_wallet": 1.0,  # Copy 100% of trader2's trades.
        # Additional traders can be added here.
    }

    # Register the Copy strategy for the RAY_BOT event type.
    copy_strategy = CopyStrategy(trader_weights)
    bot.set_strategy(EventType.RAY_BOT, copy_strategy)

    # Register the Buy and Sell actions.
    bot.set_action("buy", Buy(sol_token))
    bot.set_action("sell", Sell(sol_token))

    # -----------------------------
    # Simulate a RAY_BOT "buy" event.
    # -----------------------------
    buy_event_data = {
        "wallet": "trader1_wallet",
        "action": "buy",
        "token": {
            "address": "0x123",
            "network": "solana",
            "name": "Token X",
            "symbol": "TKX",
            "price": 10.0,
        },
        "amount": 100,  # Trader bought 100 units.
    }
    bot.send_event(EventType.RAY_BOT, buy_event_data)

    # Process the event queue (the Copy strategy will trigger a buy action).
    bot.process_events()

    # -----------------------------
    # Simulate a RAY_BOT "sell" event.
    # -----------------------------
    sell_event_data = {
        "wallet": "trader1_wallet",
        "action": "sell",
        "token": {
            "address": "0x123",
            "network": "solana",
            "name": "Token X",
            "symbol": "TKX",
            "price": 12.0,  # Price at which the trader sold.
        },
        "amount": 50,  # Trader sold 50 units.
    }
    bot.send_event(EventType.RAY_BOT, sell_event_data)

    # Process the event queue (the Copy strategy will trigger a sell action if possible).
    bot.process_events()

    # Display the final portfolio state.
    print("\nFinal portfolio state:")
    for key, qty in bot.portfolio.items():
        token = TokenRegistry.get_token(key[0], key[1])
        print(f"{token.symbol}: {qty}")
