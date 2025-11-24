"""
Exchange price tools for Kraken and Coinbase.

Provides high-level tools to fetch cryptocurrency prices from exchanges.
"""

from langchain.tools import tool
from pydantic import BaseModel, Field
from typing import Dict, Any
from phineas.tools.crypto.exchanges.kraken_api import get_kraken_ticker
from phineas.tools.crypto.exchanges.coinbase_api import get_coinbase_product_ticker


# Kraken pair mappings (Kraken uses specific pair names)
# Focused on primary coins: BTC, HYPE, SOL, ZEC
KRAKEN_PAIRS = {
    "BTC/USD": "XXBTZUSD",
    "SOL/USD": "SOLUSD",
    "ZEC/USD": "XZECZUSD",
    "HYPE/USD": "HYPEUSD",
}


class KrakenPriceInput(BaseModel):
    """Input for get_kraken_price."""
    pair: str = Field(
        ...,
        description="Trading pair in format 'BTC/USD', 'SOL/USD', 'ZEC/USD', 'HYPE/USD'"
    )


@tool(args_schema=KrakenPriceInput)
def get_kraken_price(pair: str) -> Dict[str, Any]:
    """
    Get current cryptocurrency price from Kraken exchange.

    Fetches real-time price data directly from your Kraken Pro account.
    Returns current price, bid, ask, volume, and 24h price changes.

    Supported pairs: BTC/USD, SOL/USD, ZEC/USD, HYPE/USD.
    """
    # Convert to Kraken pair format
    kraken_pair = KRAKEN_PAIRS.get(pair.upper())

    if not kraken_pair:
        # Try using the pair as-is
        kraken_pair = pair

    try:
        data = get_kraken_ticker(kraken_pair)

        # Kraken returns data nested by pair name
        ticker_data = data.get(kraken_pair, {})

        if not ticker_data:
            # Sometimes the key might be different, try first available
            ticker_data = list(data.values())[0] if data else {}

        # Extract price information
        return {
            "exchange": "Kraken",
            "pair": pair,
            "price": float(ticker_data.get('c', [0])[0]),  # Last trade price
            "bid": float(ticker_data.get('b', [0])[0]),    # Best bid
            "ask": float(ticker_data.get('a', [0])[0]),    # Best ask
            "high_24h": float(ticker_data.get('h', [0])[0]),  # 24h high
            "low_24h": float(ticker_data.get('l', [0])[0]),   # 24h low
            "volume_24h": float(ticker_data.get('v', [0])[0]),  # 24h volume
            "vwap_24h": float(ticker_data.get('p', [0])[0]),   # 24h VWAP
            "trades_24h": int(ticker_data.get('t', [0])[0]),   # Number of trades
        }
    except Exception as e:
        raise Exception(f"Failed to get Kraken price for {pair}: {str(e)}")


class CoinbasePriceInput(BaseModel):
    """Input for get_coinbase_price."""
    product_id: str = Field(
        ...,
        description="Product ID in format 'BTC-USD', 'SOL-USD', 'ZEC-USD', 'HYPE-USD' (use dash, not slash)"
    )


@tool(args_schema=CoinbasePriceInput)
def get_coinbase_price(product_id: str) -> Dict[str, Any]:
    """
    Get current cryptocurrency price from Coinbase Advanced Trade.

    Fetches real-time price data directly from your Coinbase account.
    Returns current price and trading information.

    Product IDs use dash format: BTC-USD, SOL-USD, ZEC-USD, HYPE-USD.
    """
    try:
        data = get_coinbase_product_ticker(product_id.upper())

        # Extract ticker data
        trades = data.get('trades', [{}])
        best_bid = data.get('best_bid', '0')
        best_ask = data.get('best_ask', '0')

        # Get latest trade price
        price = float(trades[0].get('price', 0)) if trades else 0

        return {
            "exchange": "Coinbase",
            "product_id": product_id,
            "price": price,
            "bid": float(best_bid) if best_bid else 0,
            "ask": float(best_ask) if best_ask else 0,
            "last_trade_time": trades[0].get('time') if trades else None,
            "last_trade_size": float(trades[0].get('size', 0)) if trades else 0,
        }
    except Exception as e:
        raise Exception(f"Failed to get Coinbase price for {product_id}: {str(e)}")


class ExchangePriceCompareInput(BaseModel):
    """Input for compare_exchange_prices."""
    crypto: str = Field(
        ...,
        description="Cryptocurrency symbol (e.g., 'BTC', 'SOL', 'ZEC', 'HYPE')"
    )
    fiat: str = Field(
        default="USD",
        description="Fiat currency (USD, EUR, etc.)"
    )


@tool(args_schema=ExchangePriceCompareInput)
def compare_exchange_prices(crypto: str, fiat: str = "USD") -> Dict[str, Any]:
    """
    Compare cryptocurrency prices across Kraken and Coinbase exchanges.

    Fetches the current price from both exchanges and shows the difference.
    Useful for identifying arbitrage opportunities or verifying market prices.

    Returns prices from both exchanges and calculates the spread.
    """
    crypto = crypto.upper()
    fiat = fiat.upper()

    # Format pairs for each exchange
    kraken_pair = f"{crypto}/{fiat}"
    coinbase_product = f"{crypto}-{fiat}"

    results = {
        "crypto": crypto,
        "fiat": fiat,
        "exchanges": {}
    }

    # Try Kraken
    try:
        kraken_data = get_kraken_price(kraken_pair)
        results["exchanges"]["kraken"] = {
            "price": kraken_data["price"],
            "bid": kraken_data["bid"],
            "ask": kraken_data["ask"],
            "available": True
        }
    except Exception as e:
        results["exchanges"]["kraken"] = {
            "available": False,
            "error": str(e)
        }

    # Try Coinbase
    try:
        coinbase_data = get_coinbase_price(coinbase_product)
        results["exchanges"]["coinbase"] = {
            "price": coinbase_data["price"],
            "bid": coinbase_data["bid"],
            "ask": coinbase_data["ask"],
            "available": True
        }
    except Exception as e:
        results["exchanges"]["coinbase"] = {
            "available": False,
            "error": str(e)
        }

    # Calculate spread if both available
    if (results["exchanges"].get("kraken", {}).get("available") and
        results["exchanges"].get("coinbase", {}).get("available")):

        kraken_price = results["exchanges"]["kraken"]["price"]
        coinbase_price = results["exchanges"]["coinbase"]["price"]

        spread = abs(kraken_price - coinbase_price)
        spread_percent = (spread / kraken_price) * 100

        results["spread"] = {
            "absolute": spread,
            "percent": spread_percent,
            "cheaper_exchange": "kraken" if kraken_price < coinbase_price else "coinbase"
        }

    return results


# Export all tools
__all__ = [
    "get_kraken_price",
    "get_coinbase_price",
    "compare_exchange_prices",
]
