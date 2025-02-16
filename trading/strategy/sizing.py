from typing import TYPE_CHECKING, Dict

if TYPE_CHECKING:
    from trading.bot.bot import Bot


class SizingStrategy:
    """
    Determines the position size in base token units (e.g., SOL) based on token's market cap.

    The desired position is calculated as a fraction of the maximum base token amount allowed when the token's
    market cap reaches a pre-configured maximum (max_market_cap). For example, if max_market_cap is 10M and
    max_base_token is 10 SOL, then a token with a market cap of 5M results in a target position of 5 SOL.
    """

    def __init__(
        self, max_market_cap: float = 10_000_000, max_quantity: float = 10.0
    ) -> None:
        """
        Initializes the PositionSizingStrategy.

        :param max_market_cap: The maximum market cap threshold for scaling. Tokens with a market cap
                             equal to or greater than this value will have a maximum position size.
        :param max_base_token: The maximum amount of base token (e.g., SOL) to allocate when a token's
                             market cap is equal to or above max_market_cap.
        """
        self.max_market_cap = max_market_cap
        self.max_quantity = max_quantity

    def get_position_size(self, bot: "Bot", token_meta: Dict) -> float:
        """
        Calculate the target position size in token quantity based on market cap.
        The calculation is based on base token value (e.g., SOL) and returns the token quantity to target.

        :param bot: The bot instance containing the portfolio
        :param token_meta: Token metadata dictionary containing market_cap, price, etc.
        :return: The target quantity in base tokens
        """
        # Get the token's market cap and price from metadata
        market_cap = token_meta.get("market_cap")
        token_price = token_meta.get("price")

        if market_cap is None or not token_price:
            print("[Sizing] Missing market cap or price information")
            return 0.0

        # Calculate target position size in base tokens (e.g., SOL)
        target_quantity = (
            self.max_quantity
            * min(market_cap, self.max_market_cap)
            / self.max_market_cap
        )

        return target_quantity
