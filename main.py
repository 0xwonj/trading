import asyncio
import itertools
import os
from typing import Dict, List

from dotenv import load_dotenv
from telethon import events

from provider.telegram.client import Telegram
from provider.telegram.handlers import raybot_handler
from trading.bot.bot import Bot
from trading.bot.builder import CopyTradingBotBuilder
from trading.bot.manager import BotManager


def generate_bot_configs() -> List[Dict]:
    """
    Generate different bot configurations for backtesting.

    :return: List of configuration dictionaries
    """
    # Define parameter ranges for testing
    initial_balances = [1000.0]
    trader_weights = [{"NORMAL11": 0.5, "NORMAL12": 1.0}]
    buy_thresholds = [3.0, 5.0, 10.0, 15.0, 20.0]
    sell_thresholds = [3.0, 5.0, 10.0, 15.0, 20.0]
    max_position_sizes = [100_000, 500_000, 1_000_000, 5_000_000, 10_000_000]
    max_risk_per_trades = [5.0, 10.0]

    configs = []
    # Generate all combinations of parameters
    combinations = itertools.product(
        initial_balances,
        trader_weights,
        buy_thresholds,
        sell_thresholds,
        max_position_sizes,
        max_risk_per_trades,
    )

    for combo in combinations:
        (
            initial_balance,
            weights,
            buy_threshold,
            sell_threshold,
            max_position_size,
            max_risk_per_trade,
        ) = combo

        config = {
            "initial_balance": initial_balance,
            "trader_weights": weights,
            "buy_threshold": buy_threshold,
            "sell_threshold": sell_threshold,
            "max_position_size": max_position_size,
            "max_risk_per_trade": max_risk_per_trade,
        }
        configs.append(config)

    return configs


async def setup_bot(name: str, config: Dict) -> Bot:
    """
    Set up a trading bot with the given configuration.

    :param name: Name of the bot
    :param config: Configuration dictionary containing all parameters
    :return: Configured Bot instance
    """
    builder = (
        CopyTradingBotBuilder(name)
        .with_initial_balance(config["initial_balance"])
        .with_trader_weights(config["trader_weights"])
        .with_thresholds(config["buy_threshold"], config["sell_threshold"])
        .with_sizing_strategy(config["max_position_size"], config["max_risk_per_trade"])
    )

    return await builder.build()


async def setup_telegram_client() -> Telegram:
    """
    Set up and configure the Telegram client.

    :return: Configured Telegram client instance
    """
    client = Telegram(
        "meme-bot", os.getenv("TELEGRAM_API_ID"), os.getenv("TELEGRAM_API_HASH")
    )
    await client.start()
    client.add_event_handler(
        raybot_handler, events.NewMessage(chats=os.getenv("RAY_BOT_CHANNEL"))
    )
    return client


async def main():
    # Load environment variables
    load_dotenv()

    print(os.getenv("TELEGRAM_API_ID"))
    print(os.getenv("TELEGRAM_API_HASH"))
    import time

    time.sleep(3)

    try:
        # Generate bot configurations
        configs = generate_bot_configs()

        # Create bot manager
        bot_manager = BotManager()

        # Set up all bots with different configurations
        bots = []
        for i, config in enumerate(configs):
            bot_name = f"CopyTradingBot_{i + 1}"
            bot = await setup_bot(bot_name, config)
            bot_manager.register_bot(bot)
            bots.append((bot_name, config))
            bot.logger.info(f"Created and registered {bot_name} with config: {config}")

        # Set up and run telegram client
        client = await setup_telegram_client()

        print(f"Running {len(bots)} bots for backtesting. Press Ctrl+C to stop.")
        await client.run_until_disconnected()

    except Exception as e:
        print(f"Error in main: {str(e)}")
        raise
    finally:
        # Cleanup all bots
        if "bots" in locals():
            for bot_name, _ in bots:
                bot_manager.remove_bot(bot_name)


if __name__ == "__main__":
    asyncio.run(main())
