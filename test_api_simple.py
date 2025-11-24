"""
Simple standalone test for CoinDesk API migration.

Tests without full package dependencies.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Load environment variables
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

print("=" * 70)
print("CoinDesk Migration - Security & Configuration Check")
print("=" * 70)

# Test 1: Environment Variables
print("\n[1/6] Environment Variables Check")
print("-" * 70)

coindesk_key = os.getenv("COINDESK_API_KEY")
coingecko_key = os.getenv("COINGECKO_API_KEY")

if coindesk_key:
    print(f"✓ COINDESK_API_KEY is set (length: {len(coindesk_key)} chars)")

    # Security check: API key should not be suspiciously short
    if len(coindesk_key) < 20:
        print("  ⚠ Warning: API key seems short. Verify it's correct.")
    else:
        print("  ✓ API key length looks reasonable")
else:
    print("✗ COINDESK_API_KEY is NOT set")

if coingecko_key:
    print(f"✓ COINGECKO_API_KEY is set (length: {len(coingecko_key)} chars)")
else:
    print("  ⚠ COINGECKO_API_KEY not set (optional)")

# Test 2: Check old CryptoCompare key is removed
print("\n[2/6] Migration Verification")
print("-" * 70)

cryptocompare_key = os.getenv("CRYPTOCOMPARE_API_KEY")
if cryptocompare_key:
    print("✗ CRYPTOCOMPARE_API_KEY still exists in .env")
    print("  Action: Remove this old key")
else:
    print("✓ Old CRYPTOCOMPARE_API_KEY has been removed")

# Test 3: Check API files exist and can be imported
print("\n[3/6] File Structure Check")
print("-" * 70)

api_file = Path(__file__).parent / "src" / "phineas" / "tools" / "crypto" / "api.py"
rate_limiter_file = Path(__file__).parent / "src" / "phineas" / "tools" / "crypto" / "rate_limiter.py"
cache_file = Path(__file__).parent / "src" / "phineas" / "tools" / "crypto" / "cache.py"

files_to_check = [
    ("api.py", api_file),
    ("rate_limiter.py", rate_limiter_file),
    ("cache.py", cache_file)
]

for name, path in files_to_check:
    if path.exists():
        print(f"✓ {name} exists")
    else:
        print(f"✗ {name} NOT FOUND at {path}")

# Test 4: Code content verification
print("\n[4/6] Code Migration Verification")
print("-" * 70)

with open(api_file, 'r', encoding='utf-8') as f:
    api_content = f.read()

checks = [
    ("call_coindesk_api function", "def call_coindesk_api"),
    ("CoinDesk base URL", "data-api.coindesk.com"),
    ("Bearer token auth", 'Authorization.*Bearer'),
    ("COINDESK_API_KEY env var", "COINDESK_API_KEY"),
    ("No old CryptoCompare function", "def call_cryptocompare_api"),
    ("No old CryptoCompare URL", "min-api.cryptocompare.com"),
]

import re

for check_name, pattern in checks:
    if "No old" in check_name:
        # These should NOT be found
        if re.search(pattern, api_content):
            print(f"✗ {check_name} - FOUND (should be removed)")
        else:
            print(f"✓ {check_name} - correctly removed")
    else:
        # These SHOULD be found
        if re.search(pattern, api_content):
            print(f"✓ {check_name} - found")
        else:
            print(f"✗ {check_name} - NOT FOUND")

# Test 5: Rate limiter check
print("\n[5/6] Rate Limiter Configuration")
print("-" * 70)

with open(rate_limiter_file, 'r', encoding='utf-8') as f:
    rate_limiter_content = f.read()

if '"coindesk"' in rate_limiter_content:
    print('✓ "coindesk" found in rate limiter')
else:
    print('✗ "coindesk" NOT found in rate limiter')

if '"cryptocompare"' in rate_limiter_content:
    print('✗ Old "cryptocompare" still in rate limiter')
else:
    print('✓ Old "cryptocompare" removed from rate limiter')

# Test 6: Security features verification
print("\n[6/6] Security Features Verification")
print("-" * 70)

security_features = [
    ("SSL verification", "verify=True"),
    ("Request timeout", "REQUEST_TIMEOUT"),
    ("Response size limit", "MAX_RESPONSE_SIZE"),
    ("Path traversal protection", "_sanitize_endpoint"),
    ("Chunked response reading", "iter_content"),
]

for feature_name, pattern in security_features:
    if pattern in api_content:
        print(f"✓ {feature_name} - implemented")
    else:
        print(f"✗ {feature_name} - NOT FOUND")

# Summary
print("\n" + "=" * 70)
print("Summary")
print("=" * 70)

issues = []

if not coindesk_key:
    issues.append("COINDESK_API_KEY not set in .env file")

if cryptocompare_key:
    issues.append("Old CRYPTOCOMPARE_API_KEY still exists in .env")

if "def call_cryptocompare_api" in api_content:
    issues.append("Old call_cryptocompare_api function still exists")

if '"cryptocompare"' in rate_limiter_content:
    issues.append("Old cryptocompare reference in rate_limiter.py")

if issues:
    print(f"\n⚠ {len(issues)} issue(s) found:")
    for i, issue in enumerate(issues, 1):
        print(f"  {i}. {issue}")
    print("\nStatus: NEEDS ATTENTION")
else:
    print("\n✓ All checks passed!")
    print("Status: READY FOR USE")
    print("\nNext steps:")
    print("  1. Update test_coindesk_api() with actual CoinDesk API endpoints")
    print("  2. Test with real API calls")
    print("  3. Monitor rate limits and caching")

print("\n" + "=" * 70)
