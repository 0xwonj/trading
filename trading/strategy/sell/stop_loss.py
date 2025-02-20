from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trading.bot.bot import Bot


@dataclass
class TokenMarketCapData:
    """
    Token market cap data for stop loss tracking.
    """

    network: str
    address: str
    market_cap: float


@dataclass
class TokenTracker:
    """
    Tracks market cap high and current data for a token.
    """

    token_meta: TokenMarketCapData  # Token market cap data
    market_cap_high: float  # Highest market cap seen
    last_market_cap: float  # Most recent market cap

    def update_market_cap(self, new_market_cap: float) -> None:
        """
        Update market cap tracking data.

        :param new_market_cap: New market cap value to process
        """
        self.last_market_cap = new_market_cap
        if new_market_cap > self.market_cap_high:
            self.market_cap_high = new_market_cap


class StopLossStrategy:
    def __init__(self, stop_loss_percentage: float = 50.0):
        """
        Initialize the stop loss strategy.

        :param stop_loss_percentage: Percentage drop from high that triggers stop loss (e.g., 50.0 for 50%)
        """
        self.stop_loss_percentage = stop_loss_percentage
        # Track tokens: (network, address) -> TokenTracker
        self.token_trackers: dict[tuple[str, str], TokenTracker] = {}

    def _should_track_token(self, token_key: tuple[str, str], bot: "Bot") -> bool:
        """
        Determine if we should track this token (only if we have a position).

        :param token_key: Tuple of (network, address)
        :param bot: Bot instance to check portfolio
        :return: True if we should track this token
        """
        position = bot.get_position(token_key)
        return position > 0

    def _check_stop_loss(self, tracker: TokenTracker) -> bool:
        """
        Check if stop loss condition is met.

        :param tracker: TokenTracker instance to check
        :return: True if stop loss should trigger
        """
        if tracker.market_cap_high <= 0:
            return False

        price_drop_percentage = (
            (tracker.market_cap_high - tracker.last_market_cap)
            / tracker.market_cap_high
            * 100
        )

        return price_drop_percentage >= self.stop_loss_percentage

    async def execute(self, token_meta: TokenMarketCapData, bot: "Bot") -> None:
        """
        Process market cap updates and trigger stop loss if needed.

        :param token_meta: Token market cap data for tracking
        :param bot: Bot instance for portfolio access
        """
        try:
            market_cap = token_meta.market_cap
            token_key = (token_meta.network, token_meta.address)

            # Check if we should track this token
            if not self._should_track_token(token_key, bot):
                # If we're tracking but no longer have position, remove tracker
                if token_key in self.token_trackers:
                    del self.token_trackers[token_key]
                return

            # Initialize or update tracker
            if token_key not in self.token_trackers:
                self.token_trackers[token_key] = TokenTracker(
                    token_meta=token_meta,
                    market_cap_high=market_cap,
                    last_market_cap=market_cap,
                )
                bot.logger.info(
                    f"Started tracking token ({token_meta.network}, {token_meta.address}) "
                    f"at market cap {market_cap:,.2f}"
                )
            else:
                tracker = self.token_trackers[token_key]
                tracker.update_market_cap(market_cap)
                bot.logger.debug(
                    f"Token ({token_meta.network}, {token_meta.address}) - "
                    f"Current: {market_cap:,.2f}, "
                    f"High: {tracker.market_cap_high:,.2f}"
                )

            # Check for stop loss condition
            tracker = self.token_trackers[token_key]
            if self._check_stop_loss(tracker):
                drop_percentage = (
                    (tracker.market_cap_high - market_cap)
                    / tracker.market_cap_high
                    * 100
                )
                bot.logger.warning(
                    f"Triggering stop loss for token ({token_meta.network}, {token_meta.address}) - "
                    f"Drop: {drop_percentage:.2f}%"
                )
                await self._execute_sell(token_meta, bot)

        except Exception as e:
            bot.logger.error(f"Error processing update: {str(e)}", exc_info=True)

    async def _execute_sell(self, token_meta: TokenMarketCapData, bot: "Bot") -> None:
        """
        Execute the stop loss sell order.

        :param token_meta: Token market cap data
        :param bot: Bot instance
        """
        token_key = (token_meta.network, token_meta.address)
        token_quantity = bot.get_position(token_key)

        if token_quantity <= 0:
            bot.logger.warning(
                f"No position to sell for token ({token_meta.network}, {token_meta.address})"
            )
            return

        # Get current price from bot or market data service
        if sell_action := bot.get_action("SELL"):
            trade_data = {
                "token": {
                    "network": token_meta.network,
                    "address": token_meta.address,
                    "market_cap": token_meta.market_cap,
                },
                "quantity": token_quantity,
            }
            await sell_action.execute(trade_data, bot)
            # Remove tracker after successful sell
            if token_key in self.token_trackers:
                del self.token_trackers[token_key]
        else:
            bot.logger.error("Sell action not registered")
