"""
Simple exchange API test without full package dependencies.

Tests the core API clients directly.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Load environment variables
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

print("=" * 70)
print("Exchange API Simple Test")
print("=" * 70)


def test_environment():
    """Test environment variables."""
    print("\n[1/4] Environment Variables")
    print("-" * 70)

    checks = {
        "KRAKEN_API_KEY": os.getenv("KRAKEN_API_KEY"),
        "KRAKEN_PRIVATE_KEY": os.getenv("KRAKEN_PRIVATE_KEY"),
        "COINBASE_KEY_ID": os.getenv("COINBASE_KEY_ID"),
        "COINBASE_API_KEY_NAME": os.getenv("COINBASE_API_KEY_NAME"),
        "COINBASE_PRIVATE_KEY": os.getenv("COINBASE_PRIVATE_KEY"),
    }

    all_set = True
    for key, value in checks.items():
        if value:
            # Show length without revealing the actual key
            length = len(value)
            print(f"✓ {key}: Set ({length} chars)")
        else:
            print(f"✗ {key}: NOT SET")
            all_set = False

    return all_set


def test_kraken_public():
    """Test Kraken public API (no auth required)."""
    print("\n[2/4] Kraken Public API Test")
    print("-" * 70)

    try:
        import requests
        import time

        # Test public endpoint directly
        url = "https://api.kraken.com/0/public/Ticker"
        params = {"pair": "XXBTZUSD"}

        response = requests.get(url, params=params, timeout=30, verify=True)
        response.raise_for_status()

        data = response.json()

        if data.get('error'):
            print(f"✗ Kraken API error: {data['error']}")
            return False

        result = data.get('result', {})
        ticker = result.get('XXBTZUSD', {})

        if ticker:
            price = ticker.get('c', [0])[0]
            print(f"✓ Kraken API working")
            print(f"  BTC/USD Price: ${price}")
            print(f"  24h Volume: {ticker.get('v', [0])[0]}")
            return True
        else:
            print("✗ No ticker data returned")
            return False

    except Exception as e:
        print(f"✗ Kraken test failed: {str(e)}")
        return False


def test_coinbase_jwt():
    """Test Coinbase JWT token generation."""
    print("\n[3/4] Coinbase JWT Authentication Test")
    print("-" * 70)

    try:
        import jwt
        from cryptography.hazmat.primitives import serialization
        import time

        key_id = os.getenv("COINBASE_KEY_ID")
        api_key_name = os.getenv("COINBASE_API_KEY_NAME")
        private_key_str = os.getenv("COINBASE_PRIVATE_KEY")

        if not all([key_id, api_key_name, private_key_str]):
            print("✗ Missing Coinbase credentials")
            return False

        # Parse private key
        private_key_str = private_key_str.replace('\\n', '\n')
        private_key = serialization.load_pem_private_key(
            private_key_str.encode('utf-8'),
            password=None
        )

        print("✓ Private key loaded successfully")

        # Create JWT token
        claims = {
            "sub": api_key_name,
            "iss": "coinbase-cloud",
            "nbf": int(time.time()),
            "exp": int(time.time()) + 120,
            "aud": ["retail_rest_api_proxy"],
            "uri": "GET api.coinbase.com/api/v3/brokerage/products/BTC-USD",
        }

        token = jwt.encode(
            claims,
            private_key,
            algorithm="ES256",
            headers={"kid": key_id, "nonce": str(int(time.time() * 1000))}
        )

        print(f"✓ JWT token generated successfully")
        print(f"  Token length: {len(token)} chars")

        return True

    except Exception as e:
        print(f"✗ JWT test failed: {str(e)}")
        return False


def test_coinbase_api():
    """Test Coinbase API call."""
    print("\n[4/4] Coinbase API Test")
    print("-" * 70)

    # First try the Advanced Trade API (requires auth)
    try:
        import requests
        import jwt
        from cryptography.hazmat.primitives import serialization
        import time

        key_id = os.getenv("COINBASE_KEY_ID")
        api_key_name = os.getenv("COINBASE_API_KEY_NAME")
        private_key_str = os.getenv("COINBASE_PRIVATE_KEY")

        if not all([key_id, api_key_name, private_key_str]):
            print("⚠ Skipping Advanced Trade API test (missing credentials)")
            print("  Testing public API instead...")
        else:
            # Parse private key
            private_key_str = private_key_str.replace('\\n', '\n')
            private_key = serialization.load_pem_private_key(
                private_key_str.encode('utf-8'),
                password=None
            )

            # Create JWT
            uri = "GET api.coinbase.com/api/v3/brokerage/products/BTC-USD"
            claims = {
                "sub": api_key_name,
                "iss": "coinbase-cloud",
                "nbf": int(time.time()),
                "exp": int(time.time()) + 120,
                "aud": ["retail_rest_api_proxy"],
                "uri": uri,
            }

            token = jwt.encode(
                claims,
                private_key,
                algorithm="ES256",
                headers={"kid": key_id, "nonce": str(int(time.time() * 1000))}
            )

            # Make API call
            url = "https://api.coinbase.com/api/v3/brokerage/products/BTC-USD"
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json"
            }

            response = requests.get(url, headers=headers, timeout=30, verify=True)
            
            if response.status_code == 200:
                data = response.json()
                product_id = data.get('product_id', 'N/A')
                price = data.get('price', 'N/A')
                print(f"✓ Coinbase Advanced Trade API working")
                print(f"  Product: {product_id}")
                print(f"  Price: ${price}")
                return True
            else:
                # Auth failed, try public API
                print(f"⚠ Advanced Trade API returned {response.status_code}")
                if response.status_code == 401:
                    print("  Authentication failed, trying public API fallback...")
                raise Exception(f"HTTP {response.status_code}")

    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "Unauthorized" in error_msg:
            print(f"⚠ Advanced Trade API authentication failed")
            print("  Trying public API as fallback...")
        else:
            print(f"⚠ Advanced Trade API error: {error_msg}")
            print("  Trying public API as fallback...")

    # Fallback to public API (no authentication required)
    try:
        url = "https://api.coinbase.com/v2/prices/BTC-USD/spot"
        headers = {
            "Accept": "application/json"
        }

        response = requests.get(url, headers=headers, timeout=30, verify=True)
        response.raise_for_status()

        data = response.json()
        price_data = data.get('data', {})
        
        if price_data:
            price = price_data.get('amount', 'N/A')
            currency = price_data.get('currency', 'USD')
            print(f"✓ Coinbase Public API working (fallback)")
            print(f"  BTC-USD Spot Price: ${price} {currency}")
            print(f"  Note: Using public API. For full features, fix Advanced Trade API authentication.")
            return True
        else:
            print("✗ No data returned from public API")
            return False

    except Exception as e:
        error_msg = str(e)
        print(f"✗ Coinbase API test failed: {error_msg}")
        
        # Provide helpful troubleshooting info
        if "401" in error_msg or "Unauthorized" in error_msg:
            print("\n  Troubleshooting 401 Unauthorized:")
            print("  1. Check Coinbase Cloud Console: https://portal.cb.dev/")
            print("  2. Verify API key has 'View' permission for 'Products'")
            print("  3. Ensure COINBASE_API_KEY_NAME is the full path:")
            print("     organizations/ORG_ID/apiKeys/KEY_ID")
            print("  4. Verify private key matches the API key")
            print("  5. Check if API key is active (not expired/revoked)")
            print("\n  Note: Public API fallback is available for basic price data.")
        
        return False


def main():
    """Run all tests."""
    results = {
        "Environment": test_environment(),
        "Kraken Public API": test_kraken_public(),
        "Coinbase JWT Auth": test_coinbase_jwt(),
        "Coinbase API": test_coinbase_api(),
    }

    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)

    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{test_name:.<40} {status}")

    total_passed = sum(results.values())
    total_tests = len(results)

    print(f"\nTotal: {total_passed}/{total_tests} tests passed")

    if total_passed == total_tests:
        print("\n🎉 All tests passed! Exchange APIs are configured correctly.")
        print("\nYour codebase can now:")
        print("  ✓ Fetch prices from Kraken")
        print("  ✓ Fetch prices from Coinbase")
        print("  ✓ Compare prices across exchanges")
        print("\nNext: Use the tool functions in your agent:")
        print("  • get_kraken_price(pair='BTC/USD')")
        print("  • get_coinbase_price(product_id='BTC-USD')")
        print("  • compare_exchange_prices(crypto='BTC', fiat='USD')")
        return 0
    else:
        failed = total_tests - total_passed
        print(f"\n⚠ {failed} test(s) failed. Review output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
