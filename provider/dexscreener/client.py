from __future__ import annotations

import asyncio
from typing import Dict, List, Optional

import httpx

from trading.bot.event_bus import EventBus
from trading.model.event import Event, EventType
from trading.strategy.sell.stop_loss import TokenMarketCapData

from .errors import DexScreenerAPIError


class DexScreenerClient:
    """
    A client for interacting with the DexScreener API.
    Rate limits:
    - Token profiles, boosts, orders: 60 requests per minute
    - Pairs, search, pools: 300 requests per minute

    Documentation: https://docs.dexscreener.com/api/reference
    """

    BASE_URL = "https://api.dexscreener.com"
    DEFAULT_TIMEOUT = 10.0  # seconds
    DEFAULT_POLLING_INTERVAL = 60.0  # seconds

    def __init__(
        self,
        timeout: float = DEFAULT_TIMEOUT,
        polling_interval: float = DEFAULT_POLLING_INTERVAL,
        use_zyte: bool = False,
        zyte_api_key: Optional[str] = None
    ):
        """
        Initialize the DexScreener API client.

        Args:
            timeout: Request timeout in seconds
            polling_interval: Interval between market cap updates in seconds
        """
        self._client = httpx.AsyncClient(
            timeout=timeout,
            headers={
                "Accept": "application/json",
                "User-Agent": "DexScreenerPythonClient/1.0",
            },
        )
        self.polling_interval = polling_interval
        self._polling_task: Optional[asyncio.Task] = None
        self._tracked_tokens: Dict[
            tuple[str, str], bool
        ] = {}  # (address, network) -> is_tracking
        self._event_bus = EventBus()
        self._subscriptions: Dict[str, asyncio.Task] = {}
        self.use_zyte = use_zyte
        self.zyte_api_key = zyte_api_key

    async def __aenter__(self) -> DexScreenerClient:
        """Enable async context manager support."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Ensure proper cleanup of resources."""
        await self.close()

    async def close(self) -> None:
        """Close the underlying HTTP client and stop polling."""
        await self.stop_polling()
        for sub_id in list(self._subscriptions.keys()):
            self.unsubscribe(sub_id)
        await self._client.aclose()

    async def _make_request(self, endpoint: str, params: dict | None = None) -> dict:
        """
        Make an async request to the DexScreener API.

        Args:
            endpoint: API endpoint to call
            params: Optional query parameters

        Returns:
            JSON response from the API

        Raises:
            DexScreenerAPIError: If the API request fails
        """
        try:
            if self.use_zyte:
                zyte_url = "https://api.zyte.com/v1/extract"
                payload = {
                    "url": endpoint,
                    "httpResponseBody": True,
                }
                if params:
                    payload.update(params)
                auth = (self.zyte_api_key, "") if self.zyte_api_key else None
                headers = {
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
                }
                response = await self._client.post(zyte_url, json=payload, auth=auth, headers=headers)
            else:
                response = await self._client.get(endpoint, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise DexScreenerAPIError(f"API request failed: {str(e)}") from e

    def track_token(self, address: str, network: str) -> None:
        """
        Start tracking a token for market cap updates.

        Args:
            address: Token address
            network: Network name (e.g., "solana")
        """
        self._tracked_tokens[(address, network)] = True
        print(f"[DexScreener] Started tracking token ({address}) on {network}")

    def untrack_token(self, address: str, network: str) -> None:
        """
        Stop tracking a token.

        Args:
            address: Token address
            network: Network name (e.g., "solana")
        """
        self._tracked_tokens.pop((address, network), None)
        print(f"[DexScreener] Stopped tracking token ({address}) on {network}")

    async def start_polling(self) -> None:
        """Start the market cap polling task."""
        if self._polling_task is None:
            self._polling_task = asyncio.create_task(self._poll_market_caps())
            print("[DexScreener] Started market cap polling")

    async def stop_polling(self) -> None:
        """Stop the market cap polling task."""
        if self._polling_task is not None:
            self._polling_task.cancel()
            try:
                await self._polling_task
            except asyncio.CancelledError:
                pass
            self._polling_task = None
            print("[DexScreener] Stopped market cap polling")

    async def _poll_market_caps(self) -> None:
        """
        Continuously poll market caps for tracked tokens and publish updates.
        """
        while True:
            try:
                tracked_tokens = list(self._tracked_tokens.keys())
                if not tracked_tokens:
                    await asyncio.sleep(self.polling_interval)
                    continue

                # Process tokens in batches of 30 (API limit)
                for i in range(0, len(tracked_tokens), 30):
                    batch = tracked_tokens[i : i + 30]
                    for address, network in batch:
                        # Get token data
                        pairs = await self.get_pairs_by_token_async(network, [address])
                        if not pairs:
                            continue

                        # Find the pair with highest liquidity
                        pair = max(
                            pairs,
                            key=lambda p: float(p.get("liquidity", {}).get("usd", 0)),
                        )

                        # Extract market cap
                        market_cap = float(
                            pair.get("fdv", 0)
                        )  # Using FDV as market cap
                        if market_cap <= 0:
                            continue

                        # Create and publish market cap update
                        market_cap_data = TokenMarketCapData(
                            address=address,
                            network=network,
                            market_cap=market_cap,
                        )

                        event = Event(EventType.MARKET_CAP_UPDATE, market_cap_data)
                        await self._event_bus.publish(event)
                        print(
                            f"[DexScreener] Published market cap update for {address}: "
                            f"{market_cap:,.2f}"
                        )

                    # Small delay between batches to respect rate limits
                    await asyncio.sleep(1)

                # Wait for next polling interval
                await asyncio.sleep(self.polling_interval)

            except Exception as e:
                print(f"[DexScreener] Error polling market caps: {str(e)}")
                await asyncio.sleep(self.polling_interval)

    async def get_pairs_by_token_async(
        self, chain_id: str, token_addresses: List[str]
    ) -> List[Dict]:
        """
        Async version of get_pairs_by_token.
        """
        if len(token_addresses) > 30:
            raise ValueError("Maximum 30 token addresses allowed")

        addresses = ",".join(token_addresses)
        return await self._make_request(
            f"{self.BASE_URL}/tokens/v1/{chain_id}/{addresses}"
        )

    def get_latest_token_profiles(self) -> list[dict]:
        """
        Get the latest token profiles.
        Rate limit: 60 requests per minute.

        Returns:
            List of token profile dictionaries
        """
        return self._make_request(f"{self.BASE_URL}/token-profiles/latest/v1")

    def get_latest_boosted_tokens(self) -> list[dict]:
        """
        Get the latest boosted tokens.
        Rate limit: 60 requests per minute.

        Returns:
            List of token boost dictionaries
        """
        return self._make_request(f"{self.BASE_URL}/token-boosts/latest/v1")

    def get_top_boosted_tokens(self) -> list[dict]:
        """
        Get the tokens with most active boosts.
        Rate limit: 60 requests per minute.

        Returns:
            List of token boost dictionaries
        """
        return self._make_request(f"{self.BASE_URL}/token-boosts/top/v1")

    def check_token_orders(self, chain_id: str, token_address: str) -> list[dict]:
        """
        Check orders paid for a token.
        Rate limit: 60 requests per minute.

        Args:
            chain_id: Chain ID (e.g., "solana")
            token_address: Token address

        Returns:
            List of order dictionaries
        """
        return self._make_request(
            f"{self.BASE_URL}/orders/v1/{chain_id}/{token_address}"
        )

    def get_pair_by_chain(self, chain_id: str, pair_id: str) -> list[dict]:
        """
        Get one or multiple pairs by chain and pair address.
        Rate limit: 300 requests per minute.

        Args:
            chain_id: Chain ID (e.g., "solana")
            pair_id: Pair contract address

        Returns:
            List of pair dictionaries
        """
        response = self._make_request(
            f"{self.BASE_URL}/latest/dex/pairs/{chain_id}/{pair_id}"
        )
        return response.get("pairs", [])

    def search_pairs(self, query: str) -> list[dict]:
        """
        Search for pairs by token address, name, or symbol.
        Rate limit: 300 requests per minute.

        Args:
            query: Search query (token address, name, or symbol)

        Returns:
            List of pair dictionaries matching the search criteria
        """
        response = self._make_request(
            f"{self.BASE_URL}/latest/dex/search", params={"q": query}
        )
        return response.get("pairs", [])

    def get_token_pools(self, chain_id: str, token_address: str) -> list[dict]:
        """
        Get the pools of a given token address.
        Rate limit: 300 requests per minute.

        Args:
            chain_id: Chain ID (e.g., "solana")
            token_address: Token address

        Returns:
            List of pair dictionaries
        """
        return self._make_request(
            f"{self.BASE_URL}/token-pairs/v1/{chain_id}/{token_address}"
        )

    def get_pairs_by_token(
        self, chain_id: str, token_addresses: list[str]
    ) -> list[dict]:
        """
        Get one or multiple pairs by token address.
        Rate limit: 300 requests per minute.
        Maximum 30 addresses allowed.

        Args:
            chain_id: Chain ID (e.g., "solana")
            token_addresses: List of token addresses (max 30)

        Returns:
            List of pair dictionaries
        """
        if len(token_addresses) > 30:
            raise ValueError("Maximum 30 token addresses allowed")

        addresses = ",".join(token_addresses)
        return self._make_request(f"{self.BASE_URL}/tokens/v1/{chain_id}/{addresses}")
    

    def subscribe(self, chain_id: str, token_addresses: List[str]) -> str:
        """
        Subscribe to token pair updates by automatically calling get_pairs_by_token_async
        with the provided chain_id and token_addresses list.

        Args:
            chain_id: Chain ID (e.g., "solana")
            token_addresses: List of token addresses

        Returns:
            A subscription ID that can be used to unsubscribe later.
        """
        subscription_id = f"{chain_id}:" + ":".join(token_addresses)
        if subscription_id in self._subscriptions:
            print(f"Subscription {subscription_id} already exists.")
            return subscription_id

        task = asyncio.create_task(self._poll_subscription(subscription_id, chain_id, token_addresses))
        self._subscriptions[subscription_id] = task
        print(f"Subscribed: {subscription_id}")
        return subscription_id

    async def _poll_subscription(self, subscription_id: str, chain_id: str, token_addresses: List[str]) -> None:
        """
        Continuously poll get_pairs_by_token_async for a specific subscription.
        """
        try:
            while True:
                pairs = await self.get_pairs_by_token_async(chain_id, token_addresses)
                print(f"Subscription {subscription_id} pairs: {pairs}")
                await asyncio.sleep(self.polling_interval)
        except asyncio.CancelledError:
            print(f"Polling cancelled for subscription {subscription_id}")

    def unsubscribe(self, subscription_id: str) -> None:
        """
        Unsubscribe from a token pair update by cancelling the polling task associated with the subscription ID.

        Args:
            subscription_id: The subscription ID returned by subscribe.
        """
        task = self._subscriptions.get(subscription_id)
        if task:
            task.cancel()
            del self._subscriptions[subscription_id]
            print(f"Unsubscribed: {subscription_id}")
        else:
            print(f"No subscription found with id: {subscription_id}")

if __name__ == "__main__":
    client = DexScreenerClient()
    print(client.get_latest_token_profiles())
