# CoinDesk API Endpoint Update Guide

## Current Situation

Your codebase currently uses **CoinGecko API** for all crypto functionality. The migration added support for **CoinDesk API**, but you haven't started using it yet.

### Active Crypto Functions (Currently Using CoinGecko)

**Location:** `phineas/src/phineas/tools/crypto/`

1. **prices.py** - Price data functions
   - `get_crypto_price()` - Single coin price
   - `get_multiple_crypto_prices()` - Multiple coin prices
   - `get_crypto_market_data()` - Comprehensive market data
   - `get_top_cryptos()` - Top coins by market cap

2. **ohlc.py** - Historical price data
   - `get_crypto_ohlc()` - OHLC candlestick data
   - `get_crypto_market_chart()` - Market chart data
   - `get_crypto_market_chart_range()` - Historical range data
   - `get_crypto_historical_price()` - Historical snapshot

3. **volatility.py** - Volatility calculations
   - `get_crypto_volatility()` - Volatility metrics
   - `get_crypto_bollinger_bands()` - Bollinger band analysis
   - `get_crypto_risk_metrics()` - Risk assessment

---

## Your Options

### Option 1: Keep Using CoinGecko (Recommended for Now)

**Status:** ✓ Everything working as-is

Your current functions work perfectly with CoinGecko. Since CoinDesk acquired CryptoCompare (not CoinGecko), you can continue using CoinGecko without issues.

**Action Required:** None - you're already set up correctly

---

### Option 2: Add CoinDesk Functions (When You Need Them)

Create **new** functions that use CoinDesk API for specific use cases where CoinDesk provides better data.

#### Example: Creating a CoinDesk Price Function

**File:** `phineas/src/phineas/tools/crypto/coindesk_prices.py` (new file)

```python
from langchain.tools import tool
from typing import Optional
from pydantic import BaseModel, Field
from phineas.tools.crypto.api import call_coindesk_api

class CoindeskBTCPriceInput(BaseModel):
    """Input for get_coindesk_btc_price."""
    currency: str = Field(
        default="USD",
        description="Target currency (USD, EUR, GBP)"
    )

@tool(args_schema=CoindeskBTCPriceInput)
def get_coindesk_btc_price(currency: str = "USD") -> dict:
    """
    Get current Bitcoin price from CoinDesk.

    Uses CoinDesk's Bitcoin Price Index (BPI).
    """
    # CoinDesk public API endpoint (no auth required)
    data = call_coindesk_api(
        f"/v1/bpi/currentprice/{currency}.json",
        params={}
    )
    return data

@tool
def get_coindesk_btc_historical(start_date: str, end_date: str) -> dict:
    """
    Get historical Bitcoin prices from CoinDesk.

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
    """
    data = call_coindesk_api(
        "/v1/bpi/historical/close.json",
        params={"start": start_date, "end": end_date}
    )
    return data
```

---

### Option 3: Replace CoinGecko with CoinDesk (Advanced)

If you want to fully switch from CoinGecko to CoinDesk, you'll need:

1. **Find equivalent CoinDesk endpoints** for each CoinGecko function
2. **Update each function** in prices.py, ohlc.py, volatility.py
3. **Test thoroughly** as response formats may differ

**⚠️ Challenge:** CoinDesk's Data API may not have 1:1 equivalents for all CoinGecko endpoints.

---

## How to Update Endpoints (Detailed Steps)

### Step 1: Identify Which Function to Update

**Current files using crypto APIs:**
- `prices.py` (lines 39, 76, 110, 171)
- `ohlc.py` (lines 49, 92, 148, 180)
- `volatility.py` (lines 47, 128, 237)

### Step 2: Import the CoinDesk Function

**Before:**
```python
from phineas.tools.crypto.api import call_coingecko_api
```

**After (add CoinDesk):**
```python
from phineas.tools.crypto.api import call_coingecko_api, call_coindesk_api
```

### Step 3: Update the API Call

**Example from prices.py line 39:**

**Before:**
```python
data = call_coingecko_api("/simple/price", params)
```

**After (using CoinDesk):**
```python
# Note: You need to find the CoinDesk equivalent endpoint
data = call_coindesk_api("/v1/prices", params)  # Example - verify actual endpoint
```

### Step 4: Update Response Parsing

CoinDesk and CoinGecko may return different JSON structures. You'll need to adjust parsing:

**Example:**
```python
# CoinGecko response format
{
  "bitcoin": {
    "usd": 45000,
    "usd_market_cap": 850000000000
  }
}

# CoinDesk response format (may differ - check docs)
{
  "bpi": {
    "USD": {
      "rate": "45,000.00",
      "rate_float": 45000.0
    }
  }
}
```

---

## Finding CoinDesk Endpoints

### Documentation Resources

1. **Official Developer Portal:**
   - https://developers.coindesk.com/documentation/data-api/info_v1_openapi

2. **Public Bitcoin Price Index (No Auth Required):**
   - Current Price: `https://api.coindesk.com/v1/bpi/currentprice.json`
   - Historical: `https://api.coindesk.com/v1/bpi/historical/close.json`

3. **Data API (Requires Auth - Your Key):**
   - Base: `https://data-api.coindesk.com`
   - Contact CoinDesk support for endpoint documentation

### Testing CoinDesk Endpoints

**Quick test in Python:**
```python
from phineas.tools.crypto.api import call_coindesk_api

# Test public endpoint (no auth needed)
try:
    # This uses the public api.coindesk.com, not data-api.coindesk.com
    # You may need to adjust base URL in api.py for public endpoints
    result = call_coindesk_api("/v1/bpi/currentprice/USD.json", {})
    print("Success:", result)
except Exception as e:
    print("Error:", e)
```

---

## Practical Example: Adding a CoinDesk Function

Let's add a new function that uses CoinDesk alongside your existing CoinGecko functions:

### Create: `phineas/src/phineas/tools/crypto/coindesk_tools.py`

```python
"""
CoinDesk-specific crypto tools.

Uses CoinDesk Bitcoin Price Index (BPI) for Bitcoin data.
Complements existing CoinGecko tools.
"""

from langchain.tools import tool
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from phineas.tools.crypto.api import call_coindesk_api


class CoindeskCurrentPriceInput(BaseModel):
    """Input for get_coindesk_current_btc_price."""
    currency: str = Field(
        default="USD",
        description="Target currency code (USD, EUR, GBP)"
    )


@tool(args_schema=CoindeskCurrentPriceInput)
def get_coindesk_current_btc_price(currency: str = "USD") -> dict:
    """
    Get current Bitcoin price from CoinDesk Bitcoin Price Index.

    The BPI is calculated as an average of bitcoin prices across major exchanges.
    Updated every minute.

    Returns current BPI value, rate description, and last update time.
    """
    endpoint = f"/v1/bpi/currentprice/{currency.upper()}.json"

    try:
        data = call_coindesk_api(endpoint, {})

        # Parse CoinDesk response
        bpi_data = data.get("bpi", {}).get(currency.upper(), {})

        return {
            "currency": currency.upper(),
            "rate": bpi_data.get("rate"),
            "rate_float": bpi_data.get("rate_float"),
            "description": bpi_data.get("description"),
            "updated": data.get("time", {}).get("updated"),
            "source": "CoinDesk Bitcoin Price Index"
        }
    except Exception as e:
        raise Exception(f"Failed to fetch CoinDesk BPI: {str(e)}")


class CoindeskHistoricalInput(BaseModel):
    """Input for get_coindesk_btc_historical."""
    days_back: int = Field(
        default=30,
        description="Number of days of historical data to fetch (1-365)"
    )


@tool(args_schema=CoindeskHistoricalInput)
def get_coindesk_btc_historical(days_back: int = 30) -> dict:
    """
    Get historical Bitcoin closing prices from CoinDesk.

    Returns daily closing prices for the specified number of days.
    Uses CoinDesk's historical Bitcoin Price Index data.
    """
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)

    # Format dates as YYYY-MM-DD
    start = start_date.strftime("%Y-%m-%d")
    end = end_date.strftime("%Y-%m-%d")

    endpoint = "/v1/bpi/historical/close.json"
    params = {"start": start, "end": end}

    try:
        data = call_coindesk_api(endpoint, params)

        # CoinDesk returns {date: price} format
        prices = data.get("bpi", {})

        return {
            "start_date": start,
            "end_date": end,
            "prices": prices,
            "count": len(prices),
            "source": "CoinDesk Bitcoin Price Index"
        }
    except Exception as e:
        raise Exception(f"Failed to fetch historical BPI: {str(e)}")


# Export tools for use in your agent
__all__ = [
    "get_coindesk_current_btc_price",
    "get_coindesk_btc_historical"
]
```

### Register the New Tools

**Update:** `phineas/src/phineas/tools/__init__.py`

```python
# Add to your existing imports
from phineas.tools.crypto.coindesk_tools import (
    get_coindesk_current_btc_price,
    get_coindesk_btc_historical
)

# Add to your tools list
crypto_tools = [
    # Existing CoinGecko tools
    get_crypto_price,
    get_multiple_crypto_prices,
    # ... other existing tools ...

    # New CoinDesk tools
    get_coindesk_current_btc_price,
    get_coindesk_btc_historical,
]
```

---

## Important Notes

### CoinDesk API Limitations

1. **Public BPI API** (api.coindesk.com):
   - ✓ No authentication required
   - ✓ Bitcoin only
   - ✓ Simple price data
   - ✗ Limited to BTC/USD/EUR/GBP

2. **Data API** (data-api.coindesk.com):
   - ✓ Requires your API key (already configured)
   - ✓ Broader crypto coverage
   - ✓ Institutional-grade data
   - ⚠ Documentation requires CoinDesk account access

### Base URL Configuration

The migration configured your `api.py` to use:
- `https://data-api.coindesk.com` (Data API - requires auth)

If you want to use the **public BPI API**, you have two options:

**Option A:** Create a separate function for public API:
```python
def call_coindesk_public_api(endpoint: str, params: Optional[dict] = None) -> dict:
    """Call CoinDesk public API (no auth required)."""
    base_url = "https://api.coindesk.com"
    # ... rest similar to call_coindesk_api but without auth header
```

**Option B:** Make base URL configurable:
```python
def call_coindesk_api(endpoint: str, params: Optional[dict] = None, use_data_api: bool = True) -> dict:
    base_url = "https://data-api.coindesk.com" if use_data_api else "https://api.coindesk.com"
    # ... rest of function
```

---

## Recommendation

**Start Simple:**

1. ✓ **Keep CoinGecko** for your existing functions (they work great)
2. ✓ **Add CoinDesk** only for Bitcoin-specific features using the public BPI API
3. ✓ **Contact CoinDesk** support to get Data API endpoint documentation for your API key

**When to Use Which:**
- **CoinGecko:** Comprehensive altcoin data, market analysis, historical data
- **CoinDesk Public API:** Bitcoin prices, industry-standard BPI
- **CoinDesk Data API:** Institutional features, once you have endpoint docs

---

## Next Steps

1. **Review CoinDesk API documentation** with your account:
   - Log in to https://developers.coindesk.com
   - Access Data API endpoint documentation
   - Review available endpoints for your tier

2. **Test public endpoints** first:
   - Create `coindesk_tools.py` with BPI functions
   - Test with public API (no auth needed)
   - Verify response formats

3. **Gradually migrate** if needed:
   - Start with one function
   - Compare data quality vs CoinGecko
   - Expand based on results

---

## Getting Help

**CoinDesk Support:**
- Developer portal: https://developers.coindesk.com
- Contact support for Data API endpoint documentation

**Your API Configuration:**
- ✓ COINDESK_API_KEY: Configured (64 chars)
- ✓ Authentication: Bearer token
- ✓ Base URL: data-api.coindesk.com

**Test Files:**
- `test_api_simple.py` - Configuration verification
- `test_coindesk_migration.py` - Full test suite (update with endpoints)

---

## Sources

- [CoinDesk API Documentation](https://developers.coindesk.com/documentation/data-api/info_v1_openapi)
- [CoinDesk Public API](https://publicapis.io/coin-desk-api)
- [CoinDesk BPI API](https://api.coindesk.com/v1/bpi/currentprice.json)
- [CoinDesk API Resources](https://www.coindesk.com/api/)
