from trading.action.buy import Buy
from trading.action.sell import Sell
from trading.bot.bot import Bot
from trading.bot.manager import BotManager
from trading.model.event import EventType
from trading.model.token import Token, TokenRegistry
from trading.strategy.buy.copy import CopyStrategy
from trading.strategy.sell.stop_loss import StopLossStrategy
from trading.strategy.sizing import SizingStrategy


class CopyTradingBotBuilder:
    """
    Builder for configuring and creating trading bots with necessary components.
    """

    def __init__(self, name: str, manager: BotManager):
        """
        Initialize the bot builder.

        :param name: Name of the bot to create
        :param manager: BotManager instance for managing the bot
        """
        self.name = name
        self.manager = manager
        self.initial_balance = 1000.0
        self.base_token = ("solana", "So11111111111111111111111111111111111111112")
        self.trader_weights: dict[str, float] = {}
        self.buy_threshold = 2.0
        self.sell_threshold = 2.0
        self.stop_loss_threshold = 10.0

    def with_initial_balance(self, balance: float) -> "CopyTradingBotBuilder":
        """
        Set the initial balance for the bot.

        :param balance: Initial balance in base token
        :return: Builder instance for chaining
        """
        self.initial_balance = balance
        return self

    def with_base_token(self, address: str, network: str) -> "CopyTradingBotBuilder":
        """
        Set the base token for trading.

        :param address: Token address
        :param network: Network name
        :return: Builder instance for chaining
        """
        self.base_token = (address, network)
        return self

    def with_trader_weights(self, weights: dict[str, float]) -> "CopyTradingBotBuilder":
        """
        Set the trader weights for copy trading.

        :param weights: Dictionary mapping trader addresses to their weights
        :return: Builder instance for chaining
        """
        self.trader_weights = weights
        return self

    def with_thresholds(
        self, buy_threshold: float, sell_threshold: float
    ) -> "CopyTradingBotBuilder":
        """
        Set the buy and sell thresholds for copy trading.

        :param buy_threshold: Weight threshold to trigger a buy
        :param sell_threshold: Weight threshold to trigger a sell
        :return: Builder instance for chaining
        """
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold
        return self

    def with_sizing_strategy(
        self, max_position_size: float, max_risk_per_trade: float
    ) -> "CopyTradingBotBuilder":
        """
        Set the sizing strategy for the bot.
        """
        self.sizing_strategy = SizingStrategy(max_position_size, max_risk_per_trade)
        return self

    def with_stop_loss_threshold(self, threshold: float) -> "CopyTradingBotBuilder":
        """
        Set the stop loss threshold for the bot.

        :param threshold: Price percentage drop to trigger stop loss
        :return: Builder instance for chaining
        """
        self.stop_loss_threshold = threshold
        return self

    async def build(self) -> Bot:
        """
        Build and configure the bot with all components.

        :return: configured Bot instance
        """
        # Create bot instance
        bot = Bot(self.name, self.manager)

        # Set up base token
        TokenRegistry.set_token(
            Token(
                self.base_token[0],
                self.base_token[1],
                "Sol",
                "SOL",
                1.0,
                1_000_000,
            )
        )

        # Initialize portfolio with base token
        bot.add_to_portfolio(self.base_token, self.initial_balance)

        # Set up strategies
        copy_strategy = CopyStrategy(
            self.trader_weights,
            self.buy_threshold,
            self.sell_threshold,
        )
        stop_loss_strategy = StopLossStrategy(self.stop_loss_threshold)

        # Register strategies
        bot.set_strategy(EventType.RAY_BOT, copy_strategy)
        bot.set_strategy(EventType.POSITION_SIZING, self.sizing_strategy)
        bot.set_strategy(EventType.MARKET_CAP_UPDATE, stop_loss_strategy)
        # Register actions
        bot.set_action("BUY", Buy(self.base_token))
        bot.set_action("SELL", Sell(self.base_token))

        return bot
