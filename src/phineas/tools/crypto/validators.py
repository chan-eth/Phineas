"""
Security validators for crypto tools.
Provides input validation and sanitization to prevent injection attacks.
"""

import re
from datetime import datetime
from typing import List


def validate_coin_id(coin_id: str) -> str:
    """
    Validate and sanitize coin_id to prevent injection attacks.
    CoinGecko coin IDs are lowercase alphanumeric with hyphens.

    Security: Prevents path traversal, header injection, and parameter injection.

    Args:
        coin_id: The cryptocurrency identifier to validate

    Returns:
        str: The validated coin_id

    Raises:
        ValueError: If coin_id is invalid or potentially malicious
    """
    if not coin_id:
        raise ValueError("Coin ID cannot be empty")

    # Enforce maximum length to prevent DoS
    if len(coin_id) > 50:
        raise ValueError("Coin ID exceeds maximum length of 50 characters")

    # Only allow lowercase letters, numbers, and hyphens
    # This prevents path traversal, header injection, and other attacks
    if not re.match(r'^[a-z0-9-]+$', coin_id):
        raise ValueError(
            "Invalid coin ID format. Only lowercase letters, numbers, and hyphens allowed."
        )

    # Prevent consecutive hyphens or leading/trailing hyphens
    if '--' in coin_id or coin_id.startswith('-') or coin_id.endswith('-'):
        raise ValueError("Invalid coin ID format: improper hyphen usage")

    return coin_id


def validate_coin_ids(coin_ids: str) -> List[str]:
    """
    Validate a comma-separated list of coin IDs.

    Security: Validates each coin ID individually and prevents batch attacks.

    Args:
        coin_ids: Comma-separated list of coin IDs

    Returns:
        List[str]: List of validated coin IDs

    Raises:
        ValueError: If any coin ID is invalid
    """
    if not coin_ids:
        raise ValueError("Coin IDs list cannot be empty")

    # Limit number of coins to prevent resource exhaustion
    coin_list = [coin.strip() for coin in coin_ids.split(",")]
    if len(coin_list) > 100:
        raise ValueError("Maximum 100 coins allowed per request")

    # Validate each coin ID
    validated_ids = []
    for coin_id in coin_list:
        validated_ids.append(validate_coin_id(coin_id))

    return validated_ids


def validate_currency(currency: str) -> str:
    """
    Validate currency code.

    Security: Ensures currency codes are safe for use in API requests.

    Args:
        currency: Currency code (e.g., 'usd', 'eur', 'btc')

    Returns:
        str: The validated currency code

    Raises:
        ValueError: If currency code is invalid
    """
    if not currency:
        raise ValueError("Currency code cannot be empty")

    # Enforce maximum length
    if len(currency) > 10:
        raise ValueError("Currency code exceeds maximum length")

    # Only allow lowercase letters
    if not re.match(r'^[a-z]+$', currency):
        raise ValueError("Invalid currency code format. Only lowercase letters allowed.")

    return currency


def validate_date_format(date: str) -> str:
    """
    Validate date is in DD-MM-YYYY format and represents a valid date.

    Security: Prevents injection attacks and ensures valid date ranges.

    Args:
        date: Date string in DD-MM-YYYY format

    Returns:
        str: The validated date string

    Raises:
        ValueError: If date format or value is invalid
    """
    if not date:
        raise ValueError("Date cannot be empty")

    # Check format with regex first
    if not re.match(r'^\d{2}-\d{2}-\d{4}$', date):
        raise ValueError("Date must be in DD-MM-YYYY format (e.g., '30-12-2023')")

    # Validate it's a real date
    try:
        day, month, year = date.split('-')
        parsed_date = datetime(int(year), int(month), int(day))
    except ValueError:
        raise ValueError(f"Invalid date: {date}")

    # Validate date range
    if parsed_date > datetime.now():
        raise ValueError("Date cannot be in the future")

    # CoinGecko has historical data from ~2013
    if parsed_date < datetime(2010, 1, 1):
        raise ValueError("Date is too far in the past (before 2010)")

    return date


def validate_days(days: int) -> int:
    """
    Validate days parameter for historical data requests.

    Security: Prevents resource exhaustion from excessive date ranges.

    Args:
        days: Number of days to fetch

    Returns:
        int: The validated days value

    Raises:
        ValueError: If days is out of valid range
    """
    if not isinstance(days, int):
        raise ValueError("Days must be an integer")

    if days < 1:
        raise ValueError("Days must be at least 1")

    # Prevent excessive data requests
    if days > 365 * 10:  # 10 years max
        raise ValueError("Days cannot exceed 3650 (10 years)")

    return days


def validate_limit(limit: int) -> int:
    """
    Validate limit parameter for results.

    Security: Prevents resource exhaustion from large result sets.

    Args:
        limit: Maximum number of results

    Returns:
        int: The validated limit value

    Raises:
        ValueError: If limit is out of valid range
    """
    if not isinstance(limit, int):
        raise ValueError("Limit must be an integer")

    if limit < 1:
        raise ValueError("Limit must be at least 1")

    # CoinGecko API limit
    if limit > 250:
        raise ValueError("Limit cannot exceed 250")

    return limit


def validate_timestamp(timestamp: int) -> int:
    """
    Validate UNIX timestamp.

    Security: Ensures timestamps are within reasonable ranges.

    Args:
        timestamp: UNIX timestamp in seconds

    Returns:
        int: The validated timestamp

    Raises:
        ValueError: If timestamp is invalid
    """
    if not isinstance(timestamp, int):
        raise ValueError("Timestamp must be an integer")

    # Reasonable range: 2010-01-01 to 100 years in future
    min_timestamp = 1262304000  # 2010-01-01
    max_timestamp = int(datetime.now().timestamp()) + (100 * 365 * 24 * 3600)

    if timestamp < min_timestamp:
        raise ValueError("Timestamp is too far in the past (before 2010)")

    if timestamp > max_timestamp:
        raise ValueError("Timestamp is too far in the future")

    return timestamp
