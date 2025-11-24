"""
Kraken Pro API client with secure authentication.

Implements Kraken's REST API v0 with proper HMAC-SHA512 signing.
Includes all security features: SSL verification, timeouts, rate limiting.
"""

import os
import time
import base64
import hashlib
import hmac
import urllib.parse
import requests
import logging
from typing import Optional, Dict, Any
from phineas.tools.crypto.rate_limiter import get_rate_limiter

# Security: Load API keys from environment only
KRAKEN_API_KEY = os.getenv("KRAKEN_API_KEY")
KRAKEN_PRIVATE_KEY = os.getenv("KRAKEN_PRIVATE_KEY")

# Security: Set timeouts to prevent hanging requests
REQUEST_TIMEOUT = 30  # seconds
MAX_RESPONSE_SIZE = 10 * 1024 * 1024  # 10MB limit

# Performance: Initialize rate limiter
rate_limiter = get_rate_limiter()

logger = logging.getLogger(__name__)


def _get_kraken_signature(urlpath: str, data: Dict[str, Any], secret: str) -> str:
    """
    Generate Kraken API signature using HMAC-SHA512.

    Security: Implements Kraken's authentication protocol

    Args:
        urlpath: API endpoint path
        data: Request data including nonce
        secret: Base64-decoded private key

    Returns:
        str: Base64-encoded signature
    """
    # Encode data for signing
    postdata = urllib.parse.urlencode(data)
    encoded = (str(data['nonce']) + postdata).encode()

    # Create SHA256 hash
    message = urlpath.encode() + hashlib.sha256(encoded).digest()

    # Create HMAC-SHA512 signature
    signature = hmac.new(
        base64.b64decode(secret),
        message,
        hashlib.sha512
    )

    return base64.b64encode(signature.digest()).decode()


def call_kraken_api(
    endpoint: str,
    data: Optional[Dict[str, Any]] = None,
    public: bool = False
) -> Dict[str, Any]:
    """
    Call Kraken Pro API securely.

    Security features:
    - SSL certificate verification enforced
    - Request timeout to prevent DoS
    - HMAC-SHA512 signature authentication
    - API keys from environment only
    - Error handling without exposing sensitive details
    - Response size limit with validation
    - User-Agent header for API provider tracking

    Performance features:
    - Request rate limiting with token bucket algorithm
    - Exponential backoff for rate limit errors

    Args:
        endpoint: API endpoint (e.g., 'Ticker', 'Balance')
        data: Request parameters
        public: If True, uses public API (no auth needed)

    Returns:
        dict: API response data

    Raises:
        Exception: On API errors, authentication failures, or network issues
    """
    try:
        # Performance: Acquire rate limit permission
        if not rate_limiter.acquire("kraken", timeout=REQUEST_TIMEOUT):
            raise Exception("Rate limit acquisition timeout. Please try again later.")

        # Determine API version and path
        if public:
            api_version = "0"
            api_type = "public"
            url_path = f"/{api_version}/{api_type}/{endpoint}"
        else:
            api_version = "0"
            api_type = "private"
            url_path = f"/{api_version}/{api_type}/{endpoint}"

        base_url = "https://api.kraken.com"
        url = f"{base_url}{url_path}"

        # Prepare request data
        data = data or {}

        # Security: Build headers
        headers = {
            "User-Agent": "Phineas-Crypto-App/1.0",
            "Accept": "application/json",
        }

        # Security: Add authentication for private endpoints
        if not public:
            if not KRAKEN_API_KEY or not KRAKEN_PRIVATE_KEY:
                raise Exception("Kraken API credentials not configured. Check .env file.")

            # Add nonce (must be increasing)
            data['nonce'] = int(time.time() * 1000000)

            # Generate signature
            signature = _get_kraken_signature(url_path, data, KRAKEN_PRIVATE_KEY)

            headers['API-Key'] = KRAKEN_API_KEY
            headers['API-Sign'] = signature

        # Security: Enforce timeout and SSL verification
        response = requests.post(
            url,
            data=data,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
            verify=True,  # Enforce SSL verification
        )

        # Security: Check Content-Length if available
        content_length = response.headers.get('Content-Length')
        if content_length and int(content_length) > MAX_RESPONSE_SIZE:
            response.close()
            raise ValueError(f"Response size {content_length} exceeds maximum {MAX_RESPONSE_SIZE}")

        response.raise_for_status()

        # Parse JSON response
        result = response.json()

        # Kraken returns errors in 'error' field
        if result.get('error'):
            error_msgs = result['error']
            logger.error(f"Kraken API error: {error_msgs}")

            # Check for rate limiting
            if any('rate limit' in str(e).lower() for e in error_msgs):
                rate_limiter.report_rate_limit_error("kraken")
                raise Exception("Rate limit exceeded. Please try again later.")

            raise Exception(f"Kraken API error: {', '.join(error_msgs)}")

        # Performance: Reset backoff on success
        rate_limiter.reset_backoff("kraken")

        # Return the result data
        return result.get('result', {})

    except requests.exceptions.Timeout:
        logger.error(f"Kraken API timeout for endpoint: {endpoint}")
        raise Exception("API request timed out. Please try again.")
    except requests.exceptions.SSLError:
        logger.error(f"SSL verification failed for Kraken API")
        raise Exception("SSL verification failed. Connection not secure.")
    except requests.exceptions.HTTPError as e:
        logger.error(f"Kraken API HTTP error: {e.response.status_code}")
        if e.response.status_code == 429:
            rate_limiter.report_rate_limit_error("kraken")
            raise Exception("Rate limit exceeded. Please try again later.")
        elif e.response.status_code == 401:
            raise Exception("Authentication failed. Check your Kraken API keys.")
        else:
            raise Exception(f"API request failed with status {e.response.status_code}")
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Kraken API error: {str(e)}")
        raise Exception(f"Failed to fetch data from Kraken API: {str(e)}")


def get_kraken_ticker(pair: str) -> Dict[str, Any]:
    """
    Get ticker information for a trading pair.

    Args:
        pair: Trading pair (e.g., 'XXBTZUSD' for BTC/USD)

    Returns:
        dict: Ticker data including price, volume, etc.
    """
    return call_kraken_api("Ticker", {"pair": pair}, public=True)


def get_kraken_balance() -> Dict[str, Any]:
    """
    Get account balance (requires authentication).

    Returns:
        dict: Balance for each currency
    """
    return call_kraken_api("Balance", {}, public=False)


def get_kraken_trade_balance(asset: str = "ZUSD") -> Dict[str, Any]:
    """
    Get trade balance information (requires authentication).

    Args:
        asset: Base asset for balance (default: USD)

    Returns:
        dict: Trade balance details
    """
    return call_kraken_api("TradeBalance", {"asset": asset}, public=False)
