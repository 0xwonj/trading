import os

from dotenv import load_dotenv
from telethon import events

from telegram.client import Telegram
from telegram.handlers import print_handler, create_raybot_handler
from telegram.model.models import Channel
from trading.bot.core import Bot
from trading.bot.manager import BotManager
from trading.model.token import Token, TokenRegistry
from trading.strategy.copy import CopyStrategy
from trading.action.buy import Buy
from trading.action.sell import Sell
from trading.model.event import EventType


async def main():
    load_dotenv()

    # Initialize the bot
    bot = Bot("CopyTradingBot")

    # Initialize the Token Registry with the SOL token.
    sol_token = ("0x0", "solana")
    TokenRegistry.set_token(
        Token(sol_token[0], sol_token[1], "Sol", "SOL", 1.0, 1_000_000)
    )
    # Initialize the Portfolio with some initial holdings.
    bot.portfolio = {
        sol_token: 1000,  # 1000 SOL
    }

    # Hard-coded trader weights: mapping trader wallet addresses to weight multipliers.
    trader_weights = {
        "trader1_wallet": 0.5,  # Copy 50% of trader1's trades.
        "trader2_wallet": 1.0,  # Copy 100% of trader2's trades.
    }

    # Register the Copy strategy for the RAY_BOT event type.
    copy_strategy = CopyStrategy(trader_weights)
    bot.set_strategy(EventType.RAY_BOT, copy_strategy)

    # Register the Buy and Sell actions.
    bot.set_action("buy", Buy(sol_token))
    bot.set_action("sell", Sell(sol_token))

    # Initialize the bot manager
    manager = BotManager()

    # Add the bot to the manager
    manager.add_bot(bot)

    # Initialize the Telegram Client
    client = Telegram(
        "test", os.getenv("TELEGRAM_API_ID"), os.getenv("TELEGRAM_API_HASH")
    )

    # Start the client session
    await client.start()

    # Create the RayBot handler
    raybot_handler = create_raybot_handler(manager)

    # Add event handlers to the telegram client
    client.add_handler(print_handler, events.NewMessage(chats=Channel.TEST.value))
    client.add_handler(raybot_handler, events.NewMessage(chats=Channel.TEST.value))

    # Run the client until it's disconnected
    await client.run_until_disconnected()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
