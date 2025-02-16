from typing import TYPE_CHECKING

from trading.model.protocols import Action
from trading.model.token import TokenRegistry

if TYPE_CHECKING:
    from trading.bot.bot import Bot


class Sell(Action):
    def __init__(self, base_token: tuple[str, str]):
        # base_token is a tuple (address, network) representing the currency used for receiving funds.
        self.base_token = base_token

    async def execute(self, data: any, bot: "Bot") -> None:
        # Expected data includes: token (dict), price, quantity, and optionally source_wallet.
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

        price = data.get("price", token.price)
        token_key = (token.address, token.network)
        current_position = bot.portfolio.get(token_key, 0)
        if current_position <= 0:
            bot.logger.warning(f"No position to sell for {token.symbol}")
            return

        # Sell only up to the currently held quantity.
        sell_quantity = min(quantity, current_position)
        bot.logger.info(f"Selling {sell_quantity} of {token.symbol} at price {price}")

        # Deduct the sold quantity from the token's portfolio.
        bot.portfolio[token_key] = current_position - sell_quantity

        # Calculate revenue from the sale.
        revenue = sell_quantity * price

        # Increase the base token balance by the sale revenue.
        base_balance = bot.portfolio.get(self.base_token, 0)
        bot.portfolio[self.base_token] = base_balance + revenue

        # Log the entire portfolio status
        portfolio_status = []
        for key, amount in bot.portfolio.items():
            if amount > 0:  # Only show tokens with non-zero balance
                token_info = TokenRegistry.get_token(key[0], key[1])
                if token_info:
                    portfolio_status.append(f"{token_info.symbol}: {amount:.4f}")
                else:
                    portfolio_status.append(f"{key}: {amount:.4f}")

        bot.logger.info(f"Portfolio status after sell - {' | '.join(portfolio_status)}")
