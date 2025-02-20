from __future__ import annotations

import base64
import json
from typing import Optional, Protocol

import httpx

from .errors import DexScreenerAPIError


class DexScreenerClient(Protocol):
    async def get_pairs_by_token(
        self, chain_id: str, token_addresses: list[str]
    ) -> list[dict]: ...

    async def get_latest_token_profiles(self) -> list[dict]: ...

    async def get_latest_boosted_tokens(self) -> list[dict]: ...

    async def get_top_boosted_tokens(self) -> list[dict]: ...

    async def check_token_orders(
        self, chain_id: str, token_address: str
    ) -> list[dict]: ...

    async def get_pair_by_chain(self, chain_id: str, pair_id: str) -> list[dict]: ...

    async def search_pairs(self, query: str) -> list[dict]: ...

    async def get_token_pools(
        self, chain_id: str, token_address: str
    ) -> list[dict]: ...


class DexScreenerZyteClient(DexScreenerClient):
    """
    A client for interacting with the DexScreener API.
    Rate limits:
    - Token profiles, boosts, orders: 60 requests per minute
    - Pairs, search, pools: 300 requests per minute

    Documentation: https://docs.dexscreener.com/api/reference
    """

    BASE_URL = "https://api.dexscreener.com"
    DEFAULT_TIMEOUT = 10.0  # seconds

    def __init__(
        self,
        timeout: float = DEFAULT_TIMEOUT,
        zyte_api_key: Optional[str] = None,
    ):
        """
        Initialize the DexScreener API client.

        Args:
            timeout: Request timeout in seconds
            zyte_api_key: Optional Zyte API key for proxy service
        """
        self._client = httpx.AsyncClient(
            timeout=timeout,
            headers={
                "Accept": "application/json",
                "User-Agent": "DexScreenerPythonClient/1.0",
            },
        )
        self.zyte_api_key = zyte_api_key

    async def __aenter__(self) -> DexScreenerZyteClient:
        """Enable async context manager support."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Ensure proper cleanup of resources."""
        await self.close()

    async def close(self) -> None:
        """Close the underlying HTTP client."""
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
            response = await self._client.post(
                zyte_url, json=payload, auth=auth, headers=headers
            )
            response.raise_for_status()
            zyte_response = response.json()

            # Decode base64 httpResponseBody and parse as JSON
            if "httpResponseBody" in zyte_response:
                decoded_body = base64.b64decode(zyte_response["httpResponseBody"])
                return json.loads(decoded_body)
            raise DexScreenerAPIError("No httpResponseBody in Zyte response")

        except httpx.HTTPError as e:
            raise DexScreenerAPIError(f"API request failed: {str(e)}") from e
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise DexScreenerAPIError(f"Failed to decode response: {str(e)}") from e

    async def get_pairs_by_token(
        self, chain_id: str, token_addresses: list[str]
    ) -> list[dict]:
        """
        Get pairs for multiple token addresses.
        Maximum 30 token addresses allowed.

        Args:
            chain_id: Chain ID (e.g., "solana")
            token_addresses: List of token addresses

        Returns:
            List of pair dictionaries
        """
        if len(token_addresses) > 30:
            raise ValueError("Maximum 30 token addresses allowed")

        addresses = ",".join(token_addresses)
        return await self._make_request(
            f"{self.BASE_URL}/tokens/v1/{chain_id}/{addresses}"
        )

    async def get_latest_token_profiles(self) -> list[dict]:
        """
        Get the latest token profiles.
        Rate limit: 60 requests per minute.

        Returns:
            List of token profile dictionaries
        """
        return await self._make_request(f"{self.BASE_URL}/token-profiles/latest/v1")

    async def get_latest_boosted_tokens(self) -> list[dict]:
        """
        Get the latest boosted tokens.
        Rate limit: 60 requests per minute.

        Returns:
            List of token boost dictionaries
        """
        return await self._make_request(f"{self.BASE_URL}/token-boosts/latest/v1")

    async def get_top_boosted_tokens(self) -> list[dict]:
        """
        Get the tokens with most active boosts.
        Rate limit: 60 requests per minute.

        Returns:
            List of token boost dictionaries
        """
        return await self._make_request(f"{self.BASE_URL}/token-boosts/top/v1")

    async def check_token_orders(self, chain_id: str, token_address: str) -> list[dict]:
        """
        Check orders paid for a token.
        Rate limit: 60 requests per minute.

        Args:
            chain_id: Chain ID (e.g., "solana")
            token_address: Token address

        Returns:
            List of order dictionaries
        """
        return await self._make_request(
            f"{self.BASE_URL}/orders/v1/{chain_id}/{token_address}"
        )

    async def get_pair_by_chain(self, chain_id: str, pair_id: str) -> list[dict]:
        """
        Get one or multiple pairs by chain and pair address.
        Rate limit: 300 requests per minute.

        Args:
            chain_id: Chain ID (e.g., "solana")
            pair_id: Pair contract address

        Returns:
            List of pair dictionaries
        """
        response = await self._make_request(
            f"{self.BASE_URL}/latest/dex/pairs/{chain_id}/{pair_id}"
        )
        return response.get("pairs", [])

    async def search_pairs(self, query: str) -> list[dict]:
        """
        Search for pairs by token address, name, or symbol.
        Rate limit: 300 requests per minute.

        Args:
            query: Search query (token address, name, or symbol)

        Returns:
            List of pair dictionaries matching the search criteria
        """
        response = await self._make_request(
            f"{self.BASE_URL}/latest/dex/search", params={"q": query}
        )
        return response.get("pairs", [])

    async def get_token_pools(self, chain_id: str, token_address: str) -> list[dict]:
        """
        Get the pools of a given token address.
        Rate limit: 300 requests per minute.

        Args:
            chain_id: Chain ID (e.g., "solana")
            token_address: Token address

        Returns:
            List of pair dictionaries
        """
        return await self._make_request(
            f"{self.BASE_URL}/token-pairs/v1/{chain_id}/{token_address}"
        )
