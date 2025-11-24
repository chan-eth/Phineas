"""
Coinbase Advanced Trade API client with secure JWT authentication.

Implements Coinbase's Advanced Trade API with proper JWT signing using EC keys.
Includes all security features: SSL verification, timeouts, rate limiting.
"""

import os
import time
import json
import requests
import logging
from typing import Optional, Dict, Any
from phineas.tools.crypto.rate_limiter import get_rate_limiter

# Security: Load API keys from environment only
COINBASE_KEY_ID = os.getenv("COINBASE_KEY_ID")
COINBASE_API_KEY_NAME = os.getenv("COINBASE_API_KEY_NAME")
COINBASE_PRIVATE_KEY = os.getenv("COINBASE_PRIVATE_KEY")

# Security: Set timeouts to prevent hanging requests
REQUEST_TIMEOUT = 30  # seconds
MAX_RESPONSE_SIZE = 10 * 1024 * 1024  # 10MB limit

# Performance: Initialize rate limiter
rate_limiter = get_rate_limiter()

logger = logging.getLogger(__name__)


def _create_jwt_token(service: str, uri: str) -> str:
    """
    Create JWT token for Coinbase authentication.

    Security: Implements Coinbase's JWT authentication protocol with EC signing

    Args:
        service: Service name (e.g., 'retail_rest_api_proxy')
        uri: Request URI

    Returns:
        str: JWT token

    Raises:
        Exception: If jwt or cryptography libraries not available
    """
    try:
        import jwt
        from cryptography.hazmat.primitives import serialization
    except ImportError:
        raise Exception(
            "Coinbase authentication requires 'pyjwt' and 'cryptography' libraries. "
            "Install with: pip install pyjwt cryptography"
        )

    if not COINBASE_KEY_ID or not COINBASE_API_KEY_NAME or not COINBASE_PRIVATE_KEY:
        missing = []
        if not COINBASE_KEY_ID:
            missing.append("COINBASE_KEY_ID")
        if not COINBASE_API_KEY_NAME:
            missing.append("COINBASE_API_KEY_NAME")
        if not COINBASE_PRIVATE_KEY:
            missing.append("COINBASE_PRIVATE_KEY")
        raise Exception(f"Coinbase API credentials not configured. Missing: {', '.join(missing)}. Check .env file.")

    # Parse the private key
    try:
        # Handle escaped newlines in the key
        private_key_str = COINBASE_PRIVATE_KEY.replace('\\n', '\n')

        private_key = serialization.load_pem_private_key(
            private_key_str.encode('utf-8'),
            password=None
        )
    except Exception as e:
        logger.error(f"Failed to load Coinbase private key: {e}")
        raise Exception("Invalid Coinbase private key format")

    # Create JWT claims
    claims = {
        "sub": COINBASE_API_KEY_NAME,
        "iss": "coinbase-cloud",
        "nbf": int(time.time()),
        "exp": int(time.time()) + 120,  # Token expires in 2 minutes
        "aud": [service],
        "uri": uri,
    }

    # Sign the JWT with ES256 algorithm
    token = jwt.encode(
        claims,
        private_key,
        algorithm="ES256",
        headers={"kid": COINBASE_KEY_ID, "nonce": str(int(time.time() * 1000))}
    )

    return token


def call_coinbase_api(
    endpoint: str,
    method: str = "GET",
    params: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Call Coinbase Advanced Trade API securely.

    Security features:
    - SSL certificate verification enforced
    - Request timeout to prevent DoS
    - JWT authentication with EC key signing
    - API keys from environment only
    - Error handling without exposing sensitive details
    - Response size limit with validation
    - User-Agent header for API provider tracking

    Performance features:
    - Request rate limiting with token bucket algorithm
    - Exponential backoff for rate limit errors

    Args:
        endpoint: API endpoint (e.g., '/api/v3/brokerage/accounts')
        method: HTTP method (GET, POST, etc.)
        params: Query parameters
        data: Request body data

    Returns:
        dict: API response data

    Raises:
        Exception: On API errors, authentication failures, or network issues
    """
    try:
        # Performance: Acquire rate limit permission
        if not rate_limiter.acquire("coinbase", timeout=REQUEST_TIMEOUT):
            raise Exception("Rate limit acquisition timeout. Please try again later.")

        base_url = "https://api.coinbase.com"
        url = f"{base_url}{endpoint}"

        # Create JWT token for authentication
        service = "retail_rest_api_proxy"
        uri = f"{method} {base_url.replace('https://', '')}{endpoint}"
        jwt_token = _create_jwt_token(service, uri)

        # Security: Build headers with JWT
        headers = {
            "User-Agent": "Phineas-Crypto-App/1.0",
            "Accept": "application/json",
            "Authorization": f"Bearer {jwt_token}",
        }

        if data is not None:
            headers["Content-Type"] = "application/json"

        # Security: Enforce timeout and SSL verification
        response = requests.request(
            method=method,
            url=url,
            params=params,
            json=data,
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

        # Performance: Reset backoff on success
        rate_limiter.reset_backoff("coinbase")

        return result

    except requests.exceptions.Timeout:
        logger.error(f"Coinbase API timeout for endpoint: {endpoint}")
        raise Exception("API request timed out. Please try again.")
    except requests.exceptions.SSLError:
        logger.error(f"SSL verification failed for Coinbase API")
        raise Exception("SSL verification failed. Connection not secure.")
    except requests.exceptions.HTTPError as e:
        logger.error(f"Coinbase API HTTP error: {e.response.status_code}")

        # Try to parse error response
        try:
            error_data = e.response.json()
            error_msg = error_data.get('message', str(e))
        except:
            error_msg = str(e)

        if e.response.status_code == 429:
            rate_limiter.report_rate_limit_error("coinbase")
            raise Exception("Rate limit exceeded. Please try again later.")
        elif e.response.status_code == 401:
            # Try to get more detailed error message
            try:
                error_data = e.response.json()
                error_detail = error_data.get('error', {}).get('message', '')
                if error_detail:
                    raise Exception(f"Authentication failed: {error_detail}. Check your Coinbase API keys and permissions.")
            except:
                pass
            raise Exception(
                "Authentication failed (401). Common causes:\n"
                "1. API key doesn't have 'View' permission for products\n"
                "2. COINBASE_API_KEY_NAME format is incorrect (should be full path: organizations/.../apiKeys/...)\n"
                "3. API key is expired or revoked\n"
                "4. Private key doesn't match the API key\n"
                "Check your Coinbase Cloud console to verify API key permissions."
            )
        elif e.response.status_code == 403:
            raise Exception("Permission denied. Check API key permissions.")
        else:
            raise Exception(f"API request failed: {error_msg}")
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Coinbase API error: {str(e)}")
        raise Exception(f"Failed to fetch data from Coinbase API: {str(e)}")


def get_coinbase_accounts() -> Dict[str, Any]:
    """
    Get list of accounts (requires authentication).

    Returns:
        dict: List of accounts with balances
    """
    return call_coinbase_api("/api/v3/brokerage/accounts", method="GET")


def get_coinbase_product(product_id: str) -> Dict[str, Any]:
    """
    Get information about a specific product/trading pair.

    Args:
        product_id: Product ID (e.g., 'BTC-USD')

    Returns:
        dict: Product information including price
    """
    return call_coinbase_api(f"/api/v3/brokerage/products/{product_id}", method="GET")


def get_coinbase_public_price(product_id: str) -> Dict[str, Any]:
    """
    Get current spot price from Coinbase public API (no authentication required).

    Uses Coinbase v2 public API endpoint for price data.
    This is a fallback when Advanced Trade API authentication fails.

    Args:
        product_id: Product ID (e.g., 'BTC-USD')

    Returns:
        dict: Current spot price data
    """
    try:
        # Performance: Acquire rate limit permission
        if not rate_limiter.acquire("coinbase", timeout=REQUEST_TIMEOUT):
            raise Exception("Rate limit acquisition timeout. Please try again later.")

        # Use public v2 API endpoint (no authentication required)
        url = f"https://api.coinbase.com/v2/prices/{product_id}/spot"

        headers = {
            "User-Agent": "Phineas-Crypto-App/1.0",
            "Accept": "application/json",
        }

        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT, verify=True)
        response.raise_for_status()

        data = response.json()
        
        # Parse v2 API response format
        price_data = data.get('data', {})
        
        return {
            'price': price_data.get('amount', '0'),
            'currency': price_data.get('currency', 'USD'),
            'base': product_id.split('-')[0],
        }
    except Exception as e:
        logger.error(f"Coinbase public API error: {str(e)}")
        raise Exception(f"Failed to fetch public price from Coinbase: {str(e)}")


def get_coinbase_product_ticker(product_id: str, use_public_fallback: bool = True) -> Dict[str, Any]:
    """
    Get current ticker for a product.

    Tries Advanced Trade API first (requires authentication), then falls back
    to public API if authentication fails.

    Args:
        product_id: Product ID (e.g., 'BTC-USD')
        use_public_fallback: If True, fall back to public API on auth failure

    Returns:
        dict: Current price, volume, etc.
    """
    # Try authenticated endpoint first
    try:
        return call_coinbase_api(
            f"/api/v3/brokerage/products/{product_id}/ticker",
            method="GET"
        )
    except Exception as e:
        # If authentication fails and fallback is enabled, use public API
        if use_public_fallback and ("401" in str(e) or "Authentication" in str(e) or "Unauthorized" in str(e)):
            logger.warning(f"Advanced Trade API auth failed, using public API fallback for {product_id}")
            public_data = get_coinbase_public_price(product_id)
            
            # Convert public API format to match expected ticker format
            return {
                'trades': [{'price': public_data.get('price', '0')}],
                'best_bid': public_data.get('price', '0'),
                'best_ask': public_data.get('price', '0'),
                'price': public_data.get('price', '0'),
            }
        else:
            # Re-raise the original exception
            raise


def list_coinbase_products() -> Dict[str, Any]:
    """
    List all available trading products.

    Returns:
        dict: List of all tradable products
    """
    return call_coinbase_api("/api/v3/brokerage/products", method="GET")
