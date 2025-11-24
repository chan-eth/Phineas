from langchain.tools import tool
from typing import Optional
from pydantic import BaseModel, Field
from phineas.tools.crypto.api import call_coingecko_api
from phineas.tools.crypto.validators import validate_coin_id, validate_coin_ids, validate_currency, validate_limit


class CryptoPriceInput(BaseModel):
    """Input for get_crypto_price."""
    coin_id: str = Field(
        ...,
        description="The CoinGecko coin ID (e.g., 'bitcoin', 'solana', 'zcash', 'hyperliquid'). Use lowercase coin names."
    )
    vs_currency: str = Field(
        default="usd",
        description="The target currency for price (e.g., 'usd', 'eur', 'btc'). Defaults to 'usd'."
    )


@tool(args_schema=CryptoPriceInput)
def get_crypto_price(coin_id: str, vs_currency: str = "usd") -> dict:
    """
    Fetches the current real-time price for a specific cryptocurrency.
    Returns the current price, market cap, 24h volume, and 24h price change percentage.
    """
    # Security: Validate inputs
    coin_id = validate_coin_id(coin_id)
    vs_currency = validate_currency(vs_currency)

    params = {
        "ids": coin_id,
        "vs_currencies": vs_currency,
        "include_market_cap": "true",
        "include_24hr_vol": "true",
        "include_24hr_change": "true",
        "include_last_updated_at": "true"
    }

    data = call_coingecko_api("/simple/price", params)
    return data.get(coin_id, {})


class MultipleCryptoPricesInput(BaseModel):
    """Input for get_multiple_crypto_prices."""
    coin_ids: str = Field(
        ...,
        description="Comma-separated list of CoinGecko coin IDs (e.g., 'bitcoin,solana,zcash,hyperliquid'). Use lowercase coin names."
    )
    vs_currency: str = Field(
        default="usd",
        description="The target currency for prices (e.g., 'usd', 'eur', 'btc'). Defaults to 'usd'."
    )


@tool(args_schema=MultipleCryptoPricesInput)
def get_multiple_crypto_prices(coin_ids: str, vs_currency: str = "usd") -> dict:
    """
    Fetches current real-time prices for multiple cryptocurrencies at once.
    Returns prices, market caps, 24h volumes, and 24h price changes for all requested coins.
    More efficient than calling get_crypto_price multiple times.
    """
    # Security: Validate inputs
    validated_ids = validate_coin_ids(coin_ids)
    coin_ids = ",".join(validated_ids)
    vs_currency = validate_currency(vs_currency)

    params = {
        "ids": coin_ids,
        "vs_currencies": vs_currency,
        "include_market_cap": "true",
        "include_24hr_vol": "true",
        "include_24hr_change": "true",
        "include_last_updated_at": "true"
    }

    data = call_coingecko_api("/simple/price", params)
    return data


class CryptoMarketDataInput(BaseModel):
    """Input for get_crypto_market_data."""
    coin_id: str = Field(
        ...,
        description="The CoinGecko coin ID (e.g., 'bitcoin', 'solana', 'zcash', 'hyperliquid'). Use lowercase coin names."
    )


@tool(args_schema=CryptoMarketDataInput)
def get_crypto_market_data(coin_id: str) -> dict:
    """
    Fetches comprehensive market data for a specific cryptocurrency including:
    - Current price in multiple currencies
    - Market cap and rank
    - Trading volume
    - Price changes (24h, 7d, 30d, 1y)
    - All-time high/low
    - Circulating and total supply
    """
    # Security: Validate input
    coin_id = validate_coin_id(coin_id)

    params = {
        "localization": "false",
        "tickers": "false",
        "market_data": "true",
        "community_data": "false",
        "developer_data": "false"
    }

    data = call_coingecko_api(f"/coins/{coin_id}", params)

    # Extract and return the most relevant market data
    market_data = data.get("market_data", {})
    return {
        "id": data.get("id"),
        "symbol": data.get("symbol"),
        "name": data.get("name"),
        "current_price": market_data.get("current_price", {}).get("usd"),
        "market_cap": market_data.get("market_cap", {}).get("usd"),
        "market_cap_rank": data.get("market_cap_rank"),
        "total_volume": market_data.get("total_volume", {}).get("usd"),
        "high_24h": market_data.get("high_24h", {}).get("usd"),
        "low_24h": market_data.get("low_24h", {}).get("usd"),
        "price_change_24h": market_data.get("price_change_24h"),
        "price_change_percentage_24h": market_data.get("price_change_percentage_24h"),
        "price_change_percentage_7d": market_data.get("price_change_percentage_7d"),
        "price_change_percentage_30d": market_data.get("price_change_percentage_30d"),
        "price_change_percentage_1y": market_data.get("price_change_percentage_1y"),
        "ath": market_data.get("ath", {}).get("usd"),
        "ath_date": market_data.get("ath_date", {}).get("usd"),
        "atl": market_data.get("atl", {}).get("usd"),
        "atl_date": market_data.get("atl_date", {}).get("usd"),
        "circulating_supply": market_data.get("circulating_supply"),
        "total_supply": market_data.get("total_supply"),
        "max_supply": market_data.get("max_supply"),
    }


class TopCryptosInput(BaseModel):
    """Input for get_top_cryptos."""
    vs_currency: str = Field(
        default="usd",
        description="The target currency for prices (e.g., 'usd', 'eur', 'btc'). Defaults to 'usd'."
    )
    limit: int = Field(
        default=10,
        description="Number of top cryptocurrencies to return (1-250). Defaults to 10."
    )


@tool(args_schema=TopCryptosInput)
def get_top_cryptos(vs_currency: str = "usd", limit: int = 10) -> list:
    """
    Fetches the top cryptocurrencies by market cap ranking.
    Returns price, market cap, volume, and price change data for each coin.
    Useful for market overview and identifying major market movers.
    """
    # Security: Validate inputs
    vs_currency = validate_currency(vs_currency)
    limit = validate_limit(limit)

    params = {
        "vs_currency": vs_currency,
        "order": "market_cap_desc",
        "per_page": min(limit, 250),
        "page": 1,
        "sparkline": "false",
        "price_change_percentage": "24h,7d"
    }

    data = call_coingecko_api("/coins/markets", params)
    return data
