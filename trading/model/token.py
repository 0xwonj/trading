from dataclasses import dataclass
from typing import Optional

TokenMeta = tuple[str, str]


@dataclass
class Token:
    address: str
    network: str
    name: str
    symbol: str
    price: float
    market_cap: float


class TokenRegistry:
    # Class-level registry to store unique Token instances
    _registry: dict[tuple[str, str], Token] = {}

    @classmethod
    def get_token(cls, address: str, network: str) -> Optional[Token]:
        """
        Get the token instance from the registry.
        Returns None if the token is not registered.
        """
        key = (address, network)
        return cls._registry.get(key)

    @classmethod
    def set_token(cls, token: Token) -> None:
        """
        Register a token instance.
        If a token with the same address and network exists, it will be overwritten.
        """
        key = (token.address, token.network)
        cls._registry[key] = token

    @classmethod
    def update_token(
        cls,
        address: str,
        network: str,
        *,
        name: Optional[str] = None,
        symbol: Optional[str] = None,
        price: Optional[float] = None,
        market_cap: Optional[float] = None,
    ) -> Token:
        """
        Update the fields of an existing token in the registry.
        Raises ValueError if the token does not exist.
        """
        token = cls.get_token(address, network)
        if token is None:
            raise ValueError("Token not found in registry")
        if name is not None:
            token.name = name
        if symbol is not None:
            token.symbol = symbol
        if price is not None:
            token.price = price
        if market_cap is not None:
            token.market_cap = market_cap
        return token

    @classmethod
    def get_or_create_token(
        cls,
        address: str,
        network: str,
        name: Optional[str],
        symbol: Optional[str],
        price: Optional[float],
        market_cap: Optional[float],
    ) -> Token:
        """
        Return the token instance if it exists; otherwise, create a new one,
        register it, and then return it.
        """
        token = cls.get_token(address, network)
        if token is None:
            token = Token(address, network, name, symbol, price, market_cap)
            cls.set_token(token)
        return token


class Wallet:
    def __init__(self, address: str, network: str):
        self.address = address
        self.network = network
        self.balance: dict[tuple[str, str], float] = {}

    def update_balance(self, token: Token, amount: float) -> None:
        """
        Add or update the amount of a token in the wallet.
        TODO: Add error handling for negative amounts
        """
        key = (token.address, token.network)
        if key in self.balance:
            self.balance[key] += amount
        else:
            self.balance[key] = amount

    def __str__(self):
        tokens_info = []
        for (address, network), amount in self.balance.items():
            token = TokenRegistry.get_token(address, network)
            tokens_info.append(
                f"{token.name} ({token.symbol}): {amount} @ Price {token.price}"
            )
        return f"Wallet({self.address}, {self.network})\n" + "\n".join(tokens_info)


# --- Sample Code for Testing ---

if __name__ == "__main__":
    # Create or retrieve a shared Token instance via the registry
    token_a = TokenRegistry.get_or_create_token(
        "0xabc", "solana", "Token A", "TKA", 1.0, 1000.0
    )
    print("Token A:", token_a)

    # Create two wallets on the same network
    wallet1 = Wallet("wallet1_address", "solana")
    wallet2 = Wallet("wallet2_address", "solana")

    # Add the shared token instance to both wallets with different amounts
    wallet1.update_balance(token_a, 100)
    wallet2.update_balance(token_a, 200)

    # Print initial wallet states
    print("Initial Wallet States:")
    print(wallet1)
    print(wallet2)

    # Update token price using the registry's update method
    TokenRegistry.update_token("0xabc", "solana", price=2.0)

    # After updating, both wallets reflect the new token price
    print("\nAfter Updating Token Price:")
    print(wallet1)
    print(wallet2)

    # Demonstrate that get_token returns the same instance
    token_a_again = TokenRegistry.get_token("0xabc", "solana")
    print("\nToken instances are the same:", token_a is token_a_again)
