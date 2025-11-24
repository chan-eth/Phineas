import os
import requests
import json
from typing import Optional
import logging
from phineas.tools.crypto.rate_limiter import get_rate_limiter
from phineas.tools.crypto.cache import get_cache

####################################
# API Configuration
####################################

# Security: API keys loaded from environment only
coingecko_api_key = os.getenv("COINGECKO_API_KEY")
coindesk_api_key = os.getenv("COINDESK_API_KEY")

# Security: Set timeouts to prevent hanging requests
REQUEST_TIMEOUT = 30  # seconds
MAX_RESPONSE_SIZE = 10 * 1024 * 1024  # 10MB limit

# Performance: Initialize rate limiter and cache
rate_limiter = get_rate_limiter()
cache = get_cache()

logger = logging.getLogger(__name__)


def _sanitize_endpoint(endpoint: str) -> str:
    """
    Sanitize endpoint to prevent path traversal attacks.
    Security: Ensure endpoint doesn't contain path traversal attempts.
    """
    # Remove any path traversal attempts
    if ".." in endpoint or "\\" in endpoint:
        raise ValueError("Invalid endpoint: path traversal detected")

    # Ensure endpoint starts with /
    if not endpoint.startswith("/"):
        endpoint = f"/{endpoint}"

    return endpoint


def _read_response_safely(response: requests.Response) -> dict:
    """
    Safely read and parse response with size limits.

    Security: Prevents memory exhaustion from large responses.

    Args:
        response: The HTTP response object

    Returns:
        dict: Parsed JSON response

    Raises:
        ValueError: If response exceeds size limit
        Exception: If JSON parsing fails
    """
    # Security: Read response in chunks with size limit
    content = b''
    for chunk in response.iter_content(chunk_size=8192):
        content += chunk
        if len(content) > MAX_RESPONSE_SIZE:
            response.close()
            raise ValueError(f"Response exceeded maximum size of {MAX_RESPONSE_SIZE} bytes")

    # Parse JSON with error handling
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON response: {e}")
        raise Exception("Invalid response format from API")


def call_coingecko_api(endpoint: str, params: Optional[dict] = None) -> dict:
    """
    Helper function to call the CoinGecko API securely.

    Security features:
    - SSL certificate verification enforced
    - Request timeout to prevent DoS
    - API key in headers (not URL params)
    - Input sanitization for path traversal
    - Error handling without exposing sensitive details
    - Response size limit with chunked reading
    - User-Agent header for API provider tracking

    Performance features:
    - Request caching with smart TTLs
    - Rate limiting with token bucket algorithm
    - Exponential backoff for 429 responses
    """
    try:
        # Security: Sanitize endpoint
        endpoint = _sanitize_endpoint(endpoint)

        # Performance: Check cache first
        cached_response = cache.get(endpoint, params)
        if cached_response is not None:
            logger.debug(f"Cache hit for CoinGecko {endpoint}")
            return cached_response

        # Performance: Acquire rate limit permission
        if not rate_limiter.acquire("coingecko", timeout=REQUEST_TIMEOUT):
            raise Exception("Rate limit acquisition timeout. Please try again later.")

        base_url = "https://api.coingecko.com/api/v3"
        url = f"{base_url}{endpoint}"

        # Security: API key in headers, not URL params
        headers = {
            "User-Agent": "Phineas-Crypto-App/1.0",
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate",
        }
        if coingecko_api_key:
            headers["x-cg-demo-api-key"] = coingecko_api_key

        # Security: Enforce timeout and SSL verification
        response = requests.get(
            url,
            params=params or {},
            headers=headers,
            timeout=REQUEST_TIMEOUT,
            verify=True,  # Enforce SSL verification
            stream=True   # Enable streaming for size check
        )

        # Security: Check Content-Length if available
        content_length = response.headers.get('Content-Length')
        if content_length and int(content_length) > MAX_RESPONSE_SIZE:
            response.close()
            raise ValueError(f"Response size {content_length} exceeds maximum {MAX_RESPONSE_SIZE}")

        response.raise_for_status()

        # Security: Safely read and parse response
        data = _read_response_safely(response)

        # Performance: Cache successful response
        cache.set(endpoint, params, data)

        # Performance: Reset backoff on success
        rate_limiter.reset_backoff("coingecko")

        return data

    except requests.exceptions.Timeout:
        logger.error(f"CoinGecko API timeout for endpoint: {endpoint}")
        raise Exception("API request timed out. Please try again.")
    except requests.exceptions.SSLError:
        logger.error(f"SSL verification failed for CoinGecko API")
        raise Exception("SSL verification failed. Connection not secure.")
    except requests.exceptions.HTTPError as e:
        # Security: Don't expose detailed error messages to users
        logger.error(f"CoinGecko API HTTP error: {e.response.status_code}")
        if e.response.status_code == 429:
            # Performance: Report rate limit for exponential backoff
            retry_after = e.response.headers.get('Retry-After')
            rate_limiter.report_rate_limit_error(
                "coingecko",
                int(retry_after) if retry_after else None
            )
            raise Exception("Rate limit exceeded. Please try again later.")
        elif e.response.status_code == 401:
            raise Exception("Authentication failed. Check your API key.")
        elif e.response.status_code == 404:
            raise Exception("Resource not found. Please check your request.")
        else:
            raise Exception(f"API request failed with status {e.response.status_code}")
    except ValueError as e:
        # Re-raise validation errors
        logger.error(f"Validation error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"CoinGecko API error: {str(e)}")
        raise Exception("Failed to fetch data from CoinGecko API")


def call_coindesk_api(endpoint: str, params: Optional[dict] = None) -> dict:
    """
    Helper function to call the CoinDesk Data API securely.

    Security features:
    - SSL certificate verification enforced
    - Request timeout to prevent DoS
    - API key in headers (not URL params)
    - Input sanitization for path traversal
    - Error handling without exposing sensitive details
    - Response size limit with chunked reading
    - User-Agent header for API provider tracking

    Performance features:
    - Request caching with smart TTLs
    - Rate limiting with token bucket algorithm
    - Exponential backoff for 429 responses
    """
    try:
        # Security: Sanitize endpoint
        endpoint = _sanitize_endpoint(endpoint)

        # Performance: Check cache first
        cached_response = cache.get(endpoint, params)
        if cached_response is not None:
            logger.debug(f"Cache hit for CoinDesk {endpoint}")
            return cached_response

        # Performance: Acquire rate limit permission
        if not rate_limiter.acquire("coindesk", timeout=REQUEST_TIMEOUT):
            raise Exception("Rate limit acquisition timeout. Please try again later.")

        base_url = "https://data-api.coindesk.com"
        url = f"{base_url}{endpoint}"

        # Security: Use headers for API key instead of URL params
        headers = {
            "User-Agent": "Phineas-Crypto-App/1.0",
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate",
        }
        if coindesk_api_key:
            headers["Authorization"] = f"Bearer {coindesk_api_key}"

        # Security: Enforce timeout and SSL verification
        response = requests.get(
            url,
            params=params or {},
            headers=headers,
            timeout=REQUEST_TIMEOUT,
            verify=True,  # Enforce SSL verification
            stream=True   # Enable streaming for size check
        )

        # Security: Check Content-Length if available
        content_length = response.headers.get('Content-Length')
        if content_length and int(content_length) > MAX_RESPONSE_SIZE:
            response.close()
            raise ValueError(f"Response size {content_length} exceeds maximum {MAX_RESPONSE_SIZE}")

        response.raise_for_status()

        # Security: Safely read and parse response
        data = _read_response_safely(response)

        # Performance: Cache successful response
        cache.set(endpoint, params, data)

        # Performance: Reset backoff on success
        rate_limiter.reset_backoff("coindesk")

        return data

    except requests.exceptions.Timeout:
        logger.error(f"CoinDesk API timeout for endpoint: {endpoint}")
        raise Exception("API request timed out. Please try again.")
    except requests.exceptions.SSLError:
        logger.error(f"SSL verification failed for CoinDesk API")
        raise Exception("SSL verification failed. Connection not secure.")
    except requests.exceptions.HTTPError as e:
        # Security: Don't expose detailed error messages to users
        logger.error(f"CoinDesk API HTTP error: {e.response.status_code}")
        if e.response.status_code == 429:
            # Performance: Report rate limit for exponential backoff
            retry_after = e.response.headers.get('Retry-After')
            rate_limiter.report_rate_limit_error(
                "coindesk",
                int(retry_after) if retry_after else None
            )
            raise Exception("Rate limit exceeded. Please try again later.")
        elif e.response.status_code == 401:
            raise Exception("Authentication failed. Check your API key.")
        elif e.response.status_code == 404:
            raise Exception("Resource not found. Please check your request.")
        else:
            raise Exception(f"API request failed with status {e.response.status_code}")
    except ValueError as e:
        # Re-raise validation errors
        logger.error(f"Validation error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"CoinDesk API error: {str(e)}")
        raise Exception("Failed to fetch data from CoinDesk API")


def get_cache_stats() -> dict:
    """
    Get cache statistics for monitoring.

    Returns:
        dict: Cache statistics including hit rate and size
    """
    return cache.get_stats()


def get_rate_limiter_stats() -> dict:
    """
    Get rate limiter statistics for monitoring.

    Returns:
        dict: Rate limiter statistics for each API
    """
    return rate_limiter.get_stats()
