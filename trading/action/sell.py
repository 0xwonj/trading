from typing import TYPE_CHECKING

from trading.model.token import TokenRegistry
from trading.model.protocols import Action

if TYPE_CHECKING:
    from trading.bot.core import Bot


class Sell(Action):
    def __init__(self, base_token: tuple[str, str]):
        # base_token is a tuple (address, network) representing the currency used for receiving funds.
        self.base_token = base_token

    def execute(self, data: any, bot: "Bot") -> None:
        # Expected data includes: token (dict), price, quantity, and optionally source_wallet.
        token_data = data.get("token")
        if token_data is None:
            print("[SellAction] No token data provided.")
            return

        # Get or create the token instance from the registry.
        token = TokenRegistry.get_or_create_token(
            token_data["address"],
            token_data["network"],
            token_data.get("name"),
            token_data.get("symbol"),
            token_data.get("price"),
            token_data.get("market_cap"),
        )

        quantity = data.get("quantity", 0)
        if quantity <= 0:
            print("[SellAction] Quantity must be greater than zero.")
            return

        price = data.get("price", token.price)
        token_key = (token.address, token.network)
        current_position = bot.portfolio.get(token_key, 0)
        if current_position <= 0:
            print(f"[SellAction] No position to sell for {token.symbol}.")
            return

        # Sell only up to the currently held quantity.
        sell_quantity = min(quantity, current_position)
        print(
            f"[SellAction] Selling {sell_quantity} of {token.symbol} at price {price}."
        )

        # Deduct the sold quantity from the token's portfolio.
        bot.portfolio[token_key] = current_position - sell_quantity
        print(
            f"[SellAction] {token.symbol} position reduced to {bot.portfolio[token_key]}."
        )

        # Calculate revenue from the sale.
        revenue = sell_quantity * price

        # Increase the base token balance by the sale revenue.
        base_balance = bot.portfolio.get(self.base_token, 0)
        bot.portfolio[self.base_token] = base_balance + revenue
        print(
            f"[SellAction] Added {revenue} to base token {self.base_token}. "
            f"New base token balance: {bot.portfolio[self.base_token]}."
        )
