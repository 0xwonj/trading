from typing import TYPE_CHECKING

from trading.model.token import TokenRegistry
from trading.model.protocols import Action

if TYPE_CHECKING:
    from trading.bot.core import Bot


class Buy(Action):
    def __init__(self, base_token: tuple[str, str]):
        # base_token is a tuple (address, network) representing the token used for payment.
        self.base_token = base_token

    def execute(self, data: any, bot: "Bot") -> None:
        # Expected data includes: token (dict), price, quantity, and optionally source_wallet.
        token_data = data.get("token")
        if token_data is None:
            print("[BuyAction] No token data provided.")
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
            print("[BuyAction] Quantity must be greater than zero.")
            return

        # Use provided price or the token's default price.
        price = data.get("price", token.price)
        cost = price * quantity
        print(
            f"[BuyAction] Buying {quantity} of {token.symbol} at price {price} (cost: {cost})."
        )

        # Retrieve current balance for the base token.
        base_balance = bot.portfolio.get(self.base_token, 0)
        if base_balance < cost:
            print(
                f"[BuyAction] Insufficient base token balance. Available: {base_balance}, required: {cost}."
            )
            return

        # Deduct the cost from the base token balance.
        bot.portfolio[self.base_token] = base_balance - cost
        print(
            f"[BuyAction] Deducted {cost} from base token {self.base_token}. New balance: {bot.portfolio[self.base_token]}."
        )

        # Add the purchased token to the portfolio.
        token_key = (token.address, token.network)
        bot.portfolio[token_key] = bot.portfolio.get(token_key, 0) + quantity
        print(
            f"[BuyAction] Portfolio updated: {token.symbol} position is now {bot.portfolio[token_key]}."
        )
