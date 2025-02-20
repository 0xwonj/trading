import asyncio
from typing import Optional

from trading.bot.event_bus import EventBus
from trading.model.event import Event, EventType
from trading.strategy.sell.stop_loss import TokenMarketCapData

from .client import DexScreenerClient


class DexScreenerPoller:
    """
    A client for polling market cap data from DexScreener API.
    Manages token subscriptions and publishes market cap updates to the event bus.
    """

    DEFAULT_POLLING_INTERVAL = 1.0  # seconds
    BATCH_SIZE = 30  # Maximum tokens per request as per API limit

    def __init__(
        self,
        client: DexScreenerClient,
        polling_interval: float = DEFAULT_POLLING_INTERVAL,
    ):
        """
        Initialize the DexScreener poller.

        Args:
            client: DexScreener client instance
            polling_interval: Interval between market cap updates in seconds
        """
        self._client = client
        self._polling_interval = polling_interval
        self._event_bus = EventBus()
        self._subscribed_tokens: set[tuple[str, str]] = set()  # (network, address)
        self._polling_task: Optional[asyncio.Task] = None

    def subscribe(self, network: str, token_address: str) -> None:
        """
        Subscribe to market cap updates for a token.

        Args:
            network: Network name (e.g., "solana")
            token_address: Token address
        """
        self._subscribed_tokens.add((network, token_address))

    def unsubscribe(self, network: str, token_address: str) -> None:
        """
        Unsubscribe from market cap updates for a token.

        Args:
            network: Network name (e.g., "solana")
            token_address: Token address
        """
        self._subscribed_tokens.discard((network, token_address))

    def is_subscribed(self, network: str, token_address: str) -> bool:
        """
        Check if a token is currently subscribed.

        Args:
            network: Network name (e.g., "solana")
            token_address: Token address

        Returns:
            True if the token is subscribed, False otherwise
        """
        return (network, token_address) in self._subscribed_tokens

    async def _process_batch(self, network: str, batch: list[str]) -> None:
        """
        Process a batch of tokens for a specific network.

        Args:
            network: Network name
            batch: List of token addresses to process
        """
        try:
            pairs = await self._client.get_pairs_by_token(network, batch)

            # Process each pair and publish market cap updates
            update_tasks = []
            for pair in pairs:
                if not pair.get("baseToken"):
                    continue

                base_token = pair["baseToken"]
                market_cap_data = TokenMarketCapData(
                    network=network,
                    address=base_token["address"],
                    market_cap=float(base_token.get("marketCap", 0)),
                )

                # Create task for publishing market cap update event
                event = Event(EventType.MARKET_CAP_UPDATE, market_cap_data)
                update_tasks.append(self._event_bus.publish(event))

            # Wait for all update events to be published
            if update_tasks:
                await asyncio.gather(*update_tasks)

        except Exception as e:
            print(f"Error fetching market caps for batch in {network}: {str(e)}")

    async def _poll_market_caps(self) -> None:
        """
        Poll market caps for all subscribed tokens in batches.
        Processes multiple networks and batches concurrently.
        """
        try:
            # Group tokens by network
            network_tokens: dict[str, list[str]] = {}
            for network, address in self._subscribed_tokens:
                if network not in network_tokens:
                    network_tokens[network] = []
                network_tokens[network].append(address)

            # Create tasks for all batches across all networks
            batch_tasks = []
            for network, tokens in network_tokens.items():
                for i in range(0, len(tokens), self.BATCH_SIZE):
                    batch = tokens[i : i + self.BATCH_SIZE]
                    batch_tasks.append(self._process_batch(network, batch))

            # Process all batches concurrently
            if batch_tasks:
                await asyncio.gather(*batch_tasks)

        except Exception as e:
            print(f"Error in market cap polling: {str(e)}")

    async def start_polling(self) -> None:
        """
        Start polling market caps for subscribed tokens.
        """
        if self._polling_task is not None:
            return

        async def _polling_loop():
            while True:
                await self._poll_market_caps()
                await asyncio.sleep(self._polling_interval)

        self._polling_task = asyncio.create_task(_polling_loop())

    async def stop_polling(self) -> None:
        """
        Stop polling market caps.
        """
        if self._polling_task is not None:
            self._polling_task.cancel()
            try:
                await self._polling_task
            except asyncio.CancelledError:
                pass
            self._polling_task = None
