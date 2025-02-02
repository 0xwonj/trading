from typing import TYPE_CHECKING

from trading.model.token import TokenRegistry

if TYPE_CHECKING:
    from trading.bot.core import Bot


class CopyStrategy:
    def __init__(self, trader_weights: dict[str, float]):
        # trader_weights maps trader wallet addresses to weight multipliers.
        self.trader_weights = trader_weights

    def execute(self, data: any, bot: "Bot") -> None:
        # Expected event data structure:
        # {
        #     "wallet": str,         # Trader's wallet address
        #     "action": str,         # "buy" or "sell"
        #     "token": dict,         # Token info: address, network, name, symbol, price, market_cap
        #     "amount": float        # Quantity traded by the trader
        # }
        trader_wallet = data.get("wallet")
        trade_action = data.get("action")
        token_data = data.get("token")
        amount = data.get("amount")
        if not trader_wallet or not trade_action or not token_data or amount is None:
            print("[Copy] Incomplete event data received.")
            return

        # Check if the trader is in our predefined list.
        if trader_wallet not in self.trader_weights:
            print(f"[Copy] Trader {trader_wallet} is not in the copy trading list.")
            return

        weight = self.trader_weights[trader_wallet]
        # Calculate the quantity to copy based on the trader's weight.
        quantity = amount * weight
        print(
            f"[Copy] Trader {trader_wallet} {trade_action} {amount} of {token_data.get('symbol')}, "
            f"copying {quantity} based on weight {weight}."
        )

        # Build trade data for action execution.
        trade_data = {
            "token": token_data,
            "price": token_data.get("price"),
            "quantity": quantity,
            "source_wallet": trader_wallet,
        }

        if trade_action == "buy":
            buy_action = bot.actions.get("buy")
            if buy_action:
                buy_action.execute(trade_data, bot)
            else:
                print("[Copy] Buy action not registered.")
        elif trade_action == "sell":
            # For sell events, execute only if the token is already held.
            token = TokenRegistry.get_or_create_token(
                token_data["address"],
                token_data["network"],
                token_data.get("name"),
                token_data.get("symbol"),
                token_data.get("price"),
                token_data.get("market_cap"),
            )
            key = (token.address, token.network)
            current_position = bot.portfolio.get(key, 0)
            if current_position <= 0:
                print(f"[Copy] No position held for {token.symbol} to sell.")
            else:
                sell_quantity = min(quantity, current_position)
                trade_data["quantity"] = sell_quantity
                sell_action = bot.actions.get("sell")
                if sell_action:
                    sell_action.execute(trade_data, bot)
                else:
                    print("[Copy] Sell action not registered.")
        else:
            print(f"[Copy] Unknown trade action: {trade_action}")
