from dataclasses import dataclass
from typing import TYPE_CHECKING

from provider.telegram.model.models import RayMessage
from trading.model.event import EventType
from trading.strategy.utils.enums import SignalType

if TYPE_CHECKING:
    from trading.bot.bot import Bot


@dataclass
class TokenAccumulator:
    """
    Tracks accumulated weights and trade signals for a specific token.
    """

    token_meta: dict  # Token metadata from the original signal
    buy_weight: float = 0.0
    sell_weight: float = 0.0

    def add_signal(self, weight: float, is_buy: bool) -> None:
        """
        Add a new trade signal and update accumulator stats.

        :param weight: Weight of the trader's signal
        :param is_buy: True if it's a buy signal, False if sell
        """
        if is_buy:
            self.buy_weight += weight
        else:
            self.sell_weight += weight


class CopyStrategy:
    def __init__(
        self,
        trader_weights: dict[str, float],
        buy_threshold: float = 2,
        sell_threshold: float = 2,
    ):
        """
        Initialize the copy trading strategy with weighted accumulation.

        :param trader_weights: Dictionary mapping trader addresses to their signal weights
        :param buy_threshold: Weight threshold to trigger a buy trade
        :param sell_threshold: Weight threshold to trigger a sell trade (only when holding position)
        """
        self.trader_weights = trader_weights
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold

        # Track accumulated weights per token: (address, network) -> TokenAccumulator
        self.token_accumulators: dict[tuple[str, str], TokenAccumulator] = {}

    def _process_signal(
        self, data: RayMessage, bot: "Bot"
    ) -> tuple[SignalType, TokenAccumulator] | None:
        """
        Process a trading signal and determine if a trade should be executed.

        :param data: The validated RayMessage
        :param bot: The bot instance for checking positions
        :return: Tuple of (action, token_accumulator) if trade should be executed, None otherwise
        """
        token_key = (data.token["address"], data.token["network"])

        # Check current position
        current_position = bot.portfolio.get(token_key, 0)
        has_position = current_position > 0

        # Initialize or get token accumulator
        if token_key not in self.token_accumulators:
            self.token_accumulators[token_key] = TokenAccumulator(token_meta=data.token)

        token_acc = self.token_accumulators[token_key]

        match data.action:
            case SignalType.BUY.value:
                # Process buy signal
                token_acc.add_signal(self.trader_weights[data.wallet], True)

                if token_acc.buy_weight >= self.buy_threshold:
                    token_acc.buy_weight = 0
                    return SignalType.BUY, token_acc

                bot.logger.debug(
                    f"Buy threshold not met ({token_acc.buy_weight:.2f}/{self.buy_threshold})"
                )

            case SignalType.SELL.value:
                # Process sell signal (only if we have a position)
                if not has_position:
                    bot.logger.debug(
                        f"Ignoring sell signal for {data.token['symbol']} (no position)"
                    )
                    return None

                token_acc.add_signal(self.trader_weights[data.wallet], False)

                if token_acc.sell_weight >= self.sell_threshold:
                    token_acc.sell_weight = 0
                    return SignalType.SELL, token_acc

                bot.logger.debug(
                    f"Sell threshold not met ({token_acc.sell_weight:.2f}/{self.sell_threshold})"
                )

            case _:
                bot.logger.warning(f"Unknown signal type: {data.action}")

        # Log accumulator status
        bot.logger.debug(
            f"Token {data.token['symbol']} - "
            f"Buy Weight: {token_acc.buy_weight:.2f}, "
            f"Sell Weight: {token_acc.sell_weight:.2f}"
        )

        return None

    async def execute(self, data: RayMessage, bot: "Bot") -> None:
        """
        Process a new trading signal and execute trades when thresholds are met.

        :param data: The RayMessage containing trade information
        :param bot: The bot instance executing the strategy
        """
        try:
            # Validate signal data
            if not self._validate_signal(data, bot):
                return

            # Process the signal and get trade decision
            trade_decision = self._process_signal(data, bot)
            if not trade_decision:
                return

            action, token_acc = trade_decision

            # Prepare and execute the trade
            await self._execute_trade(action, token_acc, bot)

        except Exception as e:
            bot.logger.error(f"Error executing strategy: {str(e)}", exc_info=True)

    def _validate_signal(self, data: RayMessage, bot: "Bot") -> bool:
        """
        Validate incoming signal data.

        :param data: The RayMessage to validate
        :param bot: The bot instance for logging
        :return: True if valid, False otherwise
        """
        if not all([data.wallet, data.action, data.token, data.amount]):
            bot.logger.warning("Incomplete trade data received")
            return False

        if data.wallet not in self.trader_weights:
            bot.logger.warning(f"Trader {data.wallet} is not in the copy list")
            return False

        return True

    async def _execute_trade(
        self,
        action: SignalType,
        token_acc: TokenAccumulator,
        bot: "Bot",
    ) -> None:
        """
        Execute a trade based on accumulated signals.

        :param action: The trade action (SignalType.BUY or SignalType.SELL)
        :param token_acc: The TokenAccumulator for the traded token
        :param bot: The bot instance executing the trade
        """
        token_price = token_acc.token_meta.get("price")
        if not token_price:
            bot.logger.warning(
                f"No price information for {token_acc.token_meta['symbol']}"
            )
            return

        if action == SignalType.BUY:
            # Get position-sized amount using position sizing strategy
            strategy = bot.get_strategy(EventType.POSITION_SIZING)
            if not strategy:
                bot.logger.warning("No position sizing strategy found, skipping trade")
                return

            base_amount = strategy.get_position_size(bot, token_acc.token_meta)
            if not base_amount:
                bot.logger.warning(
                    "Position sizing returned zero amount, skipping trade"
                )
                return

            token_quantity = base_amount / token_price
        else:
            # For sells, get current position
            token_key = (
                token_acc.token_meta["address"],
                token_acc.token_meta["network"],
            )
            token_quantity = bot.portfolio.get(token_key, 0)
            base_amount = token_quantity * token_price

        if token_quantity <= 0:
            bot.logger.warning(f"Invalid quantity calculated: {token_quantity}")
            return

        trade_data = {
            "token": token_acc.token_meta,
            "price": token_price,
            "quantity": token_quantity,
        }

        bot.logger.info(
            f"Executing {action.value} for {token_quantity:.4f} {token_acc.token_meta['symbol']} "
            f"(worth {base_amount:.2f} base tokens) "
            f"at price {token_price} "
            f"after accumulating {action.value.lower()} weight "
            f"{token_acc.buy_weight if action == SignalType.BUY else token_acc.sell_weight:.2f}"
        )

        match action:
            case SignalType.BUY:
                if buy_action := bot.get_action("BUY"):
                    await buy_action.execute(trade_data, bot)
                else:
                    bot.logger.error("Buy action not registered")

            case SignalType.SELL:
                if sell_action := bot.get_action("SELL"):
                    await sell_action.execute(trade_data, bot)
                else:
                    bot.logger.error("Sell action not registered")

            case _:
                bot.logger.error(f"Unsupported action type: {action}")
