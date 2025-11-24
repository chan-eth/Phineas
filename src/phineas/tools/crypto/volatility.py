from langchain.tools import tool
from pydantic import BaseModel, Field
from phineas.tools.crypto.api import call_coingecko_api
from phineas.tools.crypto.validators import validate_coin_id, validate_coin_ids, validate_currency, validate_days
import statistics
import logging
from typing import List, Tuple
import requests

logger = logging.getLogger(__name__)


class VolatilityAnalysisInput(BaseModel):
    """Input for analyze_crypto_volatility."""
    coin_id: str = Field(
        ...,
        description="The CoinGecko coin ID (e.g., 'bitcoin', 'ethereum', 'cardano'). Use lowercase coin names."
    )
    vs_currency: str = Field(
        default="usd",
        description="The target currency for analysis (e.g., 'usd', 'eur', 'btc'). Defaults to 'usd'."
    )
    days: int = Field(
        default=30,
        description="Number of days to analyze for volatility calculation. Defaults to 30 days."
    )


@tool(args_schema=VolatilityAnalysisInput)
def analyze_crypto_volatility(coin_id: str, vs_currency: str = "usd", days: int = 30) -> dict:
    """
    Analyzes the price volatility of a cryptocurrency over a specified period.
    Calculates key volatility metrics including:
    - Price standard deviation
    - Average daily price change percentage
    - Maximum price swing (high to low)
    - Coefficient of variation (relative volatility)
    Returns volatility metrics useful for risk assessment and trading strategies.
    """
    # Security: Validate inputs
    coin_id = validate_coin_id(coin_id)
    vs_currency = validate_currency(vs_currency)
    days = validate_days(days)

    # Fetch OHLC data
    params = {"vs_currency": vs_currency, "days": days}
    ohlc_data = call_coingecko_api(f"/coins/{coin_id}/ohlc", params)

    if not ohlc_data:
        return {"error": "No OHLC data available"}

    # Extract prices from OHLC data
    # Format: [timestamp, open, high, low, close]
    closes = [candle[4] for candle in ohlc_data]
    highs = [candle[2] for candle in ohlc_data]
    lows = [candle[3] for candle in ohlc_data]

    # Calculate daily returns
    returns = [(closes[i] - closes[i-1]) / closes[i-1] * 100
               for i in range(1, len(closes))]

    # Calculate volatility metrics
    price_std = statistics.stdev(closes) if len(closes) > 1 else 0
    avg_price = statistics.mean(closes)
    returns_std = statistics.stdev(returns) if len(returns) > 1 else 0
    avg_return = statistics.mean(returns) if returns else 0
    max_price = max(closes)
    min_price = min(closes)
    max_swing = ((max_price - min_price) / min_price) * 100
    coefficient_of_variation = (price_std / avg_price * 100) if avg_price > 0 else 0

    # Calculate largest single-day moves
    max_gain = max(returns) if returns else 0
    max_loss = min(returns) if returns else 0

    return {
        "coin_id": coin_id,
        "vs_currency": vs_currency,
        "analysis_period_days": days,
        "current_price": closes[-1] if closes else None,
        "average_price": round(avg_price, 2),
        "price_std_dev": round(price_std, 2),
        "coefficient_of_variation": round(coefficient_of_variation, 2),
        "average_daily_return_pct": round(avg_return, 2),
        "returns_std_dev": round(returns_std, 2),
        "max_price": round(max_price, 2),
        "min_price": round(min_price, 2),
        "max_swing_pct": round(max_swing, 2),
        "max_single_day_gain_pct": round(max_gain, 2),
        "max_single_day_loss_pct": round(max_loss, 2),
    }


class PriceActionAnalysisInput(BaseModel):
    """Input for analyze_price_action."""
    coin_id: str = Field(
        ...,
        description="The CoinGecko coin ID (e.g., 'bitcoin', 'ethereum', 'cardano'). Use lowercase coin names."
    )
    vs_currency: str = Field(
        default="usd",
        description="The target currency for analysis (e.g., 'usd', 'eur', 'btc'). Defaults to 'usd'."
    )
    days: int = Field(
        default=30,
        description="Number of days to analyze for price action. Defaults to 30 days."
    )


@tool(args_schema=PriceActionAnalysisInput)
def analyze_price_action(coin_id: str, vs_currency: str = "usd", days: int = 30) -> dict:
    """
    Analyzes price action patterns and trends for a cryptocurrency.
    Identifies:
    - Trend direction (bullish/bearish/neutral)
    - Support and resistance levels
    - Price momentum
    - Key price levels
    Useful for technical analysis and identifying trading opportunities.
    """
    # Security: Validate inputs
    coin_id = validate_coin_id(coin_id)
    vs_currency = validate_currency(vs_currency)
    days = validate_days(days)

    # Fetch OHLC data
    params = {"vs_currency": vs_currency, "days": days}
    ohlc_data = call_coingecko_api(f"/coins/{coin_id}/ohlc", params)

    if not ohlc_data:
        return {"error": "No OHLC data available"}

    # Extract data
    opens = [candle[1] for candle in ohlc_data]
    highs = [candle[2] for candle in ohlc_data]
    lows = [candle[3] for candle in ohlc_data]
    closes = [candle[4] for candle in ohlc_data]

    # Calculate trend
    first_price = closes[0]
    last_price = closes[-1]
    total_change_pct = ((last_price - first_price) / first_price) * 100

    # Determine trend
    if total_change_pct > 10:
        trend = "strongly_bullish"
    elif total_change_pct > 3:
        trend = "bullish"
    elif total_change_pct < -10:
        trend = "strongly_bearish"
    elif total_change_pct < -3:
        trend = "bearish"
    else:
        trend = "neutral"

    # Calculate simple moving average
    sma_period = min(7, len(closes))
    sma = statistics.mean(closes[-sma_period:])

    # Identify support and resistance
    resistance = max(highs)
    support = min(lows)
    current_price = closes[-1]

    # Calculate distance from support/resistance
    distance_from_resistance_pct = ((resistance - current_price) / current_price) * 100
    distance_from_support_pct = ((current_price - support) / current_price) * 100

    # Calculate momentum (recent vs earlier period)
    mid_point = len(closes) // 2
    early_avg = statistics.mean(closes[:mid_point])
    recent_avg = statistics.mean(closes[mid_point:])
    momentum = ((recent_avg - early_avg) / early_avg) * 100

    # Count bullish vs bearish candles
    bullish_candles = sum(1 for i in range(len(closes)) if closes[i] > opens[i])
    bearish_candles = sum(1 for i in range(len(closes)) if closes[i] < opens[i])

    return {
        "coin_id": coin_id,
        "vs_currency": vs_currency,
        "analysis_period_days": days,
        "current_price": round(current_price, 2),
        "starting_price": round(first_price, 2),
        "total_change_pct": round(total_change_pct, 2),
        "trend": trend,
        "simple_moving_average": round(sma, 2),
        "resistance_level": round(resistance, 2),
        "support_level": round(support, 2),
        "distance_from_resistance_pct": round(distance_from_resistance_pct, 2),
        "distance_from_support_pct": round(distance_from_support_pct, 2),
        "momentum_pct": round(momentum, 2),
        "bullish_candles": bullish_candles,
        "bearish_candles": bearish_candles,
        "bullish_bearish_ratio": round(bullish_candles / bearish_candles, 2) if bearish_candles > 0 else None,
    }


class CompareCryptosInput(BaseModel):
    """Input for compare_crypto_performance."""
    coin_ids: str = Field(
        ...,
        description="Comma-separated list of CoinGecko coin IDs to compare (e.g., 'bitcoin,ethereum,cardano')."
    )
    vs_currency: str = Field(
        default="usd",
        description="The target currency for comparison (e.g., 'usd', 'eur', 'btc'). Defaults to 'usd'."
    )
    days: int = Field(
        default=30,
        description="Number of days to compare performance. Defaults to 30 days."
    )


@tool(args_schema=CompareCryptosInput)
def compare_crypto_performance(coin_ids: str, vs_currency: str = "usd", days: int = 30) -> list:
    """
    Compares the price performance and volatility of multiple cryptocurrencies.
    Returns comparative metrics including:
    - Price change percentages
    - Volatility measures
    - Return on investment
    - Relative performance rankings
    Useful for portfolio analysis and identifying best performers.
    """
    # Security: Validate inputs
    validated_ids = validate_coin_ids(coin_ids)
    vs_currency = validate_currency(vs_currency)
    days = validate_days(days)

    results = []

    for coin_id in validated_ids:
        try:
            # Fetch market chart data
            params = {"vs_currency": vs_currency, "days": days}
            market_data = call_coingecko_api(f"/coins/{coin_id}/market_chart", params)

            if not market_data or "prices" not in market_data:
                results.append({
                    "coin_id": coin_id,
                    "error": "No data available"
                })
                continue

            prices = [price[1] for price in market_data["prices"]]
            volumes = [vol[1] for vol in market_data["total_volumes"]]

            # Calculate metrics
            first_price = prices[0]
            last_price = prices[-1]
            change_pct = ((last_price - first_price) / first_price) * 100

            # Calculate returns for volatility
            returns = [(prices[i] - prices[i-1]) / prices[i-1] * 100
                       for i in range(1, len(prices))]
            volatility = statistics.stdev(returns) if len(returns) > 1 else 0

            avg_volume = statistics.mean(volumes)
            max_price = max(prices)
            min_price = min(prices)

            results.append({
                "coin_id": coin_id,
                "starting_price": round(first_price, 2),
                "ending_price": round(last_price, 2),
                "change_pct": round(change_pct, 2),
                "volatility": round(volatility, 2),
                "avg_daily_volume": round(avg_volume, 2),
                "max_price": round(max_price, 2),
                "min_price": round(min_price, 2),
                "price_range_pct": round(((max_price - min_price) / min_price) * 100, 2),
            })
        except requests.exceptions.HTTPError as e:
            # Security: Don't expose detailed HTTP errors
            logger.error(f"HTTP error for {coin_id}: {e}", exc_info=True)
            results.append({
                "coin_id": coin_id,
                "error": "Failed to fetch data for this cryptocurrency"
            })
        except requests.exceptions.RequestException as e:
            # Security: Don't expose network details
            logger.error(f"Request error for {coin_id}: {e}", exc_info=True)
            results.append({
                "coin_id": coin_id,
                "error": "Network error occurred"
            })
        except ValueError as e:
            # Security: Log validation errors but return generic message
            logger.error(f"Validation error for {coin_id}: {e}", exc_info=True)
            results.append({
                "coin_id": coin_id,
                "error": "Invalid data format"
            })
        except Exception as e:
            # Security: Log full details but return generic message
            logger.error(f"Unexpected error for {coin_id}: {e}", exc_info=True)
            results.append({
                "coin_id": coin_id,
                "error": "An unexpected error occurred"
            })

    # Sort by performance
    valid_results = [r for r in results if "error" not in r]
    valid_results.sort(key=lambda x: x["change_pct"], reverse=True)

    return results
