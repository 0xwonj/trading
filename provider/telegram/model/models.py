import re
from dataclasses import dataclass
from enum import Enum


@dataclass
class RayMessage:
    wallet: str
    action: str
    token: dict
    amount: float

    @classmethod
    def from_text(cls, text: str) -> "RayMessage":
        """
        Parses a RayMessage from the provided text.

        Expected text format example (for BUY):

            🟢 BUY DBTC on RAYDIUM
            🔹 NORMAL11

            🔹NORMAL11 swapped 0.35 SOL for 241,974.68 ($73.59) DBTC @$0.000304
            ✊Holds: 241,974.68 DBTC (0.02%)

            🔗 #DBTC | MC: $304.11K | Seen: 30+d: BE | DS | DT | PH | Bullx | GMGN | 👥INFO
            BUAv6q4v5E2Pt5ms15uzxhFF1L6rXsG5i4NmSim9pump

        And for SELL:

            🔴 SELL DEEPSOUND on RAYDIUM
            🔹 NORMAL3

            🔹NORMAL3 swapped 660,887.53 ($140.18) DEEPSOUND for 0.65 SOL @$0.000212
            ➖Sold: 74.11%
            📈PnL: +0.37 SOL (+100.39%)
            ✊Holds: 230,898.38 DEEPSOUND (0.02%)

            🔗 #DEEPSOUND | MC: $212.11K | Seen: 53m: BE | DS | DT | PH | Bullx | GMGN | 👥INFO
            8bwMih9mv6jwCuAaLzU2EqkVW4Lvjo7PiC56NhZdpump

        This method extracts:
          - wallet: e.g., "NORMAL11" or "NORMAL3"
          - action: e.g., "BUY" or "SELL"
          - token: a dict with keys:
              address (from the line after the market info),
              network (always "solana"),
              name (set equal to the token symbol),
              symbol (e.g., "DBTC" or "DEEPSOUND"),
              price (parsed from the swapped details line),
              market_cap (parsed from the market info line)
          - amount: the quantity of token swapped (e.g., 241974.68 for BUY, 660887.53 for SELL)
        """
        # Split text into non-empty, stripped lines.
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            raise ValueError("Input text is empty or has no valid lines.")

        # --- 1. Extract header information ---
        header = lines[0]
        header_pattern = r"[🔴🟢]\s+(BUY|SELL)\s+(\S+)\s+on\s+RAYDIUM"
        header_match = re.search(header_pattern, header, re.IGNORECASE)
        if not header_match:
            raise ValueError("Header format not recognized.")
        action = header_match.group(1).upper()  # e.g., "BUY" or "SELL"
        token_symbol = header_match.group(2).upper()  # e.g., "DBTC" or "DEEPSOUND"

        # --- 2. Extract wallet from a line starting with "🔹" (excluding the swapped details line) ---
        wallet = None
        for line in lines:
            if line.startswith("🔹") and "swapped" not in line:
                wallet = line.lstrip("🔹").strip()
                break
        if not wallet:
            raise ValueError("Wallet information not found.")

        # --- 3. Extract swapped trade details ---
        swapped_line = None
        for line in lines:
            if "swapped" in line:
                swapped_line = line
                break
        if not swapped_line:
            raise ValueError("Swapped trade details line not found.")

        # Use different regex patterns depending on action type.
        if action == "BUY":
            # Pattern for BUY messages:
            # "swapped <SOL_amount> SOL for <token_amount> (<$total_value>) <TOKEN_SYMBOL> @$<price>"
            pattern = r"swapped\s+([\d\.,]+)\s+SOL\s+for\s+([\d\.,]+)\s+\(\$[\d\.,]+\)\s+(\S+)\s+@\$([\d\.,]+)"
            swapped_match = re.search(pattern, swapped_line, re.IGNORECASE)
            if not swapped_match:
                raise ValueError("Swapped line format not recognized for BUY.")
            # For BUY, we take token_amount from group(2) and token price from group(4).
            token_amount_str = swapped_match.group(2)
            token_price_str = swapped_match.group(4)
            # Optionally, update token symbol from the swapped line if different.
            swapped_token_symbol = swapped_match.group(3).upper()
            if swapped_token_symbol != token_symbol:
                token_symbol = swapped_token_symbol
        elif action == "SELL":
            # Pattern for SELL messages:
            # "swapped <token_amount> (<$total_value>) <TOKEN_SYMBOL> for <SOL_amount> SOL @$<price>"
            pattern = r"swapped\s+([\d\.,]+)\s+\(\$[\d\.,]+\)\s+(\S+)\s+for\s+([\d\.,]+)\s+SOL\s+@\$([\d\.,]+)"
            swapped_match = re.search(pattern, swapped_line, re.IGNORECASE)
            if not swapped_match:
                raise ValueError("Swapped line format not recognized for SELL.")
            # For SELL, we take token_amount from group(1) and token price from group(4).
            token_amount_str = swapped_match.group(1)
            token_price_str = swapped_match.group(4)
            # Optionally, update token symbol from the swapped line if different.
            swapped_token_symbol = swapped_match.group(2).upper()
            if swapped_token_symbol != token_symbol:
                token_symbol = swapped_token_symbol
        else:
            raise ValueError(f"Unsupported action: {action}")

        token_amount = float(token_amount_str.replace(",", ""))
        token_price = float(token_price_str.replace(",", ""))

        # --- 4. Extract market cap from the market info line ---
        market_line = None
        for line in lines:
            if line.startswith("🔗"):
                market_line = line
                break
        if not market_line:
            raise ValueError("Market information line not found.")

        mc_pattern = r"MC:\s+\$(\d+(?:\.\d+)?)([KMB]?)"
        mc_match = re.search(mc_pattern, market_line)
        if not mc_match:
            raise ValueError("Market cap not found in market info line.")
        mc_value = float(mc_match.group(1))
        multiplier = mc_match.group(2).upper()
        if multiplier == "K":
            market_cap = mc_value * 1_000
        elif multiplier == "M":
            market_cap = mc_value * 1_000_000
        elif multiplier == "B":
            market_cap = mc_value * 1_000_000_000
        else:
            market_cap = mc_value

        # --- 5. Extract token address (assumed to be on the line immediately after the market info line) ---
        try:
            market_index = lines.index(market_line)
        except ValueError as e:
            raise ValueError("Market line not found in the list of lines.") from e
        if market_index + 1 < len(lines):
            token_address = lines[market_index + 1]
        else:
            raise ValueError("Token address line not found after the market info line.")

        # --- 6. Build the token dictionary ---
        token = {
            "address": token_address,
            "network": "solana",
            "name": token_symbol,  # Defaulting token name to its symbol
            "symbol": token_symbol,
            "price": token_price,
            "market_cap": market_cap,
        }

        # --- 7. Return the constructed RayMessage ---
        return cls(wallet=wallet, action=action, token=token, amount=token_amount)


class Channel(Enum):
    TEST = -4709339842
    MEME_MONITORING_BOT = -1002486434667
    RAY_BOT = "@ray_lime_bot"


if __name__ == "__main__":
    TEXT_1 = """
    🟢 BUY DBTC on RAYDIUM
    🔹 NORMAL11

    🔹NORMAL11 swapped 0.35 SOL for 241,974.68 ($73.59) DBTC @$0.000304
    ✊Holds: 241,974.68 DBTC (0.02%)

    🔗 #DBTC | MC: $304.11K | Seen: 30+d: BE | DS | DT | PH | Bullx | GMGN | 👥INFO
    BUAv6q4v5E2Pt5ms15uzxhFF1L6rXsG5i4NmSim9pump
    """
    TEXT_2 = """
    🔴 SELL DEEPSOUND on RAYDIUM
    🔹 NORMAL3

    🔹NORMAL3 swapped 660,887.53 ($140.18) DEEPSOUND for 0.65 SOL @$0.000212
    ➖Sold: 74.11%
    📈PnL: +0.37 SOL (+100.39%)
    ✊Holds: 230,898.38 DEEPSOUND (0.02%)

    🔗 #DEEPSOUND | MC: $212.11K | Seen: 53m: BE | DS | DT | PH | Bullx | GMGN | 👥INFO
    8bwMih9mv6jwCuAaLzU2EqkVW4Lvjo7PiC56NhZdpump
    """
    print(RayMessage.from_text(TEXT_1))
    print(RayMessage.from_text(TEXT_2))
