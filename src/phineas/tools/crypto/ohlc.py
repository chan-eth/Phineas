from langchain.tools import tool
from pydantic import BaseModel, Field
from phineas.tools.crypto.api import call_coingecko_api
from phineas.tools.crypto.validators import (
    validate_coin_id,
    validate_currency,
    validate_days,
    validate_date_format,
    validate_timestamp
)


class CryptoOHLCInput(BaseModel):
    """Input for get_crypto_ohlc."""
    coin_id: str = Field(
        ...,
        description="The CoinGecko coin ID (e.g., 'bitcoin', 'ethereum', 'cardano'). Use lowercase coin names."
    )
    vs_currency: str = Field(
        default="usd",
        description="The target currency for OHLC data (e.g., 'usd', 'eur', 'btc'). Defaults to 'usd'."
    )
    days: int = Field(
        ...,
        description="Number of days to fetch OHLC data for. Valid values: 1, 7, 14, 30, 90, 180, 365, or 'max'."
    )


@tool(args_schema=CryptoOHLCInput)
def get_crypto_ohlc(coin_id: str, vs_currency: str = "usd", days: int = 7) -> list:
    """
    Fetches historical OHLC (Open, High, Low, Close) candlestick data for a cryptocurrency.
    Returns data in the format: [timestamp, open, high, low, close].
    Data granularity:
    - 1 day: 30-minute intervals
    - 7-30 days: 4-hour intervals
    - 31+ days: 4-day intervals
    """
    # Security: Validate inputs
    coin_id = validate_coin_id(coin_id)
    vs_currency = validate_currency(vs_currency)
    days = validate_days(days)

    params = {
        "vs_currency": vs_currency,
        "days": days
    }

    data = call_coingecko_api(f"/coins/{coin_id}/ohlc", params)
    return data


class CryptoMarketChartInput(BaseModel):
    """Input for get_crypto_market_chart."""
    coin_id: str = Field(
        ...,
        description="The CoinGecko coin ID (e.g., 'bitcoin', 'ethereum', 'cardano'). Use lowercase coin names."
    )
    vs_currency: str = Field(
        default="usd",
        description="The target currency for chart data (e.g., 'usd', 'eur', 'btc'). Defaults to 'usd'."
    )
    days: int = Field(
        ...,
        description="Number of days to fetch market chart data for. Use 'max' for all available data."
    )


@tool(args_schema=CryptoMarketChartInput)
def get_crypto_market_chart(coin_id: str, vs_currency: str = "usd", days: int = 7) -> dict:
    """
    Fetches historical market chart data including prices, market caps, and trading volumes.
    Returns time-series data with timestamps for:
    - Prices: [timestamp, price]
    - Market caps: [timestamp, market_cap]
    - Total volumes: [timestamp, volume]
    Data granularity:
    - 1 day: 5-minute intervals
    - 2-90 days: hourly intervals
    - 90+ days: daily intervals
    """
    # Security: Validate inputs
    coin_id = validate_coin_id(coin_id)
    vs_currency = validate_currency(vs_currency)
    days = validate_days(days)

    params = {
        "vs_currency": vs_currency,
        "days": days
    }

    data = call_coingecko_api(f"/coins/{coin_id}/market_chart", params)
    return data


class CryptoMarketChartRangeInput(BaseModel):
    """Input for get_crypto_market_chart_range."""
    coin_id: str = Field(
        ...,
        description="The CoinGecko coin ID (e.g., 'bitcoin', 'ethereum', 'cardano'). Use lowercase coin names."
    )
    vs_currency: str = Field(
        default="usd",
        description="The target currency for chart data (e.g., 'usd', 'eur', 'btc'). Defaults to 'usd'."
    )
    from_timestamp: int = Field(
        ...,
        description="Start date in UNIX timestamp format (seconds since epoch)."
    )
    to_timestamp: int = Field(
        ...,
        description="End date in UNIX timestamp format (seconds since epoch)."
    )


@tool(args_schema=CryptoMarketChartRangeInput)
def get_crypto_market_chart_range(
    coin_id: str,
    vs_currency: str,
    from_timestamp: int,
    to_timestamp: int
) -> dict:
    """
    Fetches historical market chart data for a specific date range using UNIX timestamps.
    Returns time-series data with timestamps for prices, market caps, and trading volumes.
    Useful for precise date range queries and historical analysis.
    Data granularity is automatically determined based on the range:
    - 1 day: 5-minute intervals
    - 2-90 days: hourly intervals
    - 90+ days: daily intervals
    """
    # Security: Validate inputs
    coin_id = validate_coin_id(coin_id)
    vs_currency = validate_currency(vs_currency)
    from_timestamp = validate_timestamp(from_timestamp)
    to_timestamp = validate_timestamp(to_timestamp)

    # Additional validation: ensure from < to
    if from_timestamp >= to_timestamp:
        raise ValueError("from_timestamp must be earlier than to_timestamp")

    params = {
        "vs_currency": vs_currency,
        "from": from_timestamp,
        "to": to_timestamp
    }

    data = call_coingecko_api(f"/coins/{coin_id}/market_chart/range", params)
    return data


class CryptoHistoricalDataInput(BaseModel):
    """Input for get_crypto_historical_data."""
    coin_id: str = Field(
        ...,
        description="The CoinGecko coin ID (e.g., 'bitcoin', 'ethereum', 'cardano'). Use lowercase coin names."
    )
    date: str = Field(
        ...,
        description="Date in DD-MM-YYYY format (e.g., '30-12-2023')."
    )


@tool(args_schema=CryptoHistoricalDataInput)
def get_crypto_historical_data(coin_id: str, date: str) -> dict:
    """
    Fetches a snapshot of cryptocurrency data at a specific historical date.
    Returns price, market cap, and volume data for that specific date.
    Useful for point-in-time analysis and historical comparisons.
    """
    # Security: Validate inputs
    coin_id = validate_coin_id(coin_id)
    date = validate_date_format(date)

    params = {
        "date": date,
        "localization": "false"
    }

    data = call_coingecko_api(f"/coins/{coin_id}/history", params)

    # Extract market data
    market_data = data.get("market_data", {})
    return {
        "id": data.get("id"),
        "symbol": data.get("symbol"),
        "name": data.get("name"),
        "date": date,
        "current_price": market_data.get("current_price", {}).get("usd"),
        "market_cap": market_data.get("market_cap", {}).get("usd"),
        "total_volume": market_data.get("total_volume", {}).get("usd"),
    }
