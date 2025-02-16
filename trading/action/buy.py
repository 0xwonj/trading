from typing import TYPE_CHECKING

from trading.model.protocols import Action
from trading.model.token import TokenRegistry

if TYPE_CHECKING:
    from trading.bot.bot import Bot


class Buy(Action):
    def __init__(self, base_token: tuple[str, str]):
        # base_token is a tuple (address, network) representing the token used for payment.
        self.base_token = base_token

    async def execute(self, data: any, bot: "Bot") -> None:
        # Expected data includes: token (dict), price, quantity
        token_data = data.get("token")
        if token_data is None:
            bot.logger.warning("No token data provided")
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
            bot.logger.warning("Quantity must be greater than zero")
            return

        # Use provided price or the token's default price.
        price = data.get("price", token.price)
        cost = price * quantity
        bot.logger.info(
            f"Buying {quantity} of {token.symbol} at price {price} (cost: {cost})"
        )

        # Retrieve current balance for the base token.
        base_balance = bot.portfolio.get(self.base_token, 0)
        if base_balance < cost:
            bot.logger.warning(
                f"Insufficient base token balance. Available: {base_balance}, required: {cost}"
            )
            return

        # Deduct the cost from the base token balance.
        bot.add_to_portfolio(self.base_token, -cost)
        bot.logger.info(
            f"Deducted {cost} from base token {self.base_token}. New balance: {bot.portfolio[self.base_token]}"
        )

        # Add the purchased token to the portfolio.
        token_key = (token.address, token.network)
        bot.add_to_portfolio(token_key, quantity)

        # Log the entire portfolio status
        portfolio_status = []
        for key, amount in bot.portfolio.items():
            if amount > 0:  # Only show tokens with non-zero balance
                token_info = TokenRegistry.get_token(key[0], key[1])
                if token_info:
                    portfolio_status.append(f"{token_info.symbol}: {amount:.4f}")
                else:
                    portfolio_status.append(f"{key}: {amount:.4f}")

        bot.logger.info(f"Portfolio status after buy - {' | '.join(portfolio_status)}")
