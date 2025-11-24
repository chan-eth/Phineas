"""
Test script for Kraken and Coinbase exchange API integration.

Tests:
1. Environment variable configuration
2. API connectivity
3. Price fetching
4. Authentication
5. Rate limiting
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
print("Exchange API Integration Test")
print("=" * 70)


def test_environment_variables():
    """Test that required environment variables are set."""
    print("\n[1/5] Environment Variables Check")
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
            length = len(value) if len(value) < 50 else "50+"
            print(f"✓ {key}: Set ({length} chars)")
        else:
            print(f"✗ {key}: NOT SET")
            all_set = False

    return all_set


def test_dependencies():
    """Test that required libraries are installed."""
    print("\n[2/5] Dependency Check")
    print("-" * 70)

    dependencies = {
        "requests": "HTTP requests",
        "jwt": "Coinbase JWT authentication",
        "cryptography": "Coinbase key signing",
    }

    all_available = True
    for module, description in dependencies.items():
        try:
            __import__(module)
            print(f"✓ {module}: Installed ({description})")
        except ImportError:
            print(f"✗ {module}: NOT INSTALLED - Required for {description}")
            all_available = False

    if not all_available:
        print("\nInstall missing dependencies:")
        print("  pip install pyjwt cryptography")

    return all_available


def test_kraken_api():
    """Test Kraken API connectivity."""
    print("\n[3/5] Kraken API Test")
    print("-" * 70)

    try:
        from phineas.tools.crypto.exchanges.kraken_api import get_kraken_ticker

        print("Testing public endpoint (BTC/USD ticker)...")
        data = get_kraken_ticker("XXBTZUSD")

        if data:
            ticker = data.get("XXBTZUSD", {})
            price = ticker.get('c', [0])[0] if ticker else "N/A"
            print(f"✓ Kraken API connection successful")
            print(f"  BTC/USD Price: ${price}")
            return True
        else:
            print("✗ No data returned from Kraken")
            return False

    except Exception as e:
        print(f"✗ Kraken API test failed: {str(e)}")
        return False


def test_coinbase_api():
    """Test Coinbase API connectivity."""
    print("\n[4/5] Coinbase API Test")
    print("-" * 70)

    try:
        from phineas.tools.crypto.exchanges.coinbase_api import get_coinbase_product_ticker

        print("Testing authenticated endpoint (BTC-USD ticker)...")
        data = get_coinbase_product_ticker("BTC-USD")

        if data:
            trades = data.get('trades', [{}])
            price = trades[0].get('price', 'N/A') if trades else "N/A"
            print(f"✓ Coinbase API connection successful")
            print(f"  BTC-USD Price: ${price}")
            return True
        else:
            print("✗ No data returned from Coinbase")
            return False

    except Exception as e:
        error_msg = str(e)
        if "pyjwt" in error_msg.lower() or "cryptography" in error_msg.lower():
            print(f"✗ Missing dependencies: {error_msg}")
            print("  Install with: pip install pyjwt cryptography")
        else:
            print(f"✗ Coinbase API test failed: {error_msg}")
        return False


def test_price_functions():
    """Test high-level price functions."""
    print("\n[5/5] Price Function Test")
    print("-" * 70)

    success_count = 0
    total_tests = 2

    # Test Kraken price function
    try:
        from phineas.tools.crypto.exchanges.exchange_prices import get_kraken_price

        print("Testing get_kraken_price('BTC/USD')...")
        result = get_kraken_price.invoke({"pair": "BTC/USD"})

        if result and result.get("price"):
            print(f"✓ Kraken price function works")
            print(f"  Price: ${result['price']}")
            print(f"  Bid: ${result.get('bid', 'N/A')}")
            print(f"  Ask: ${result.get('ask', 'N/A')}")
            success_count += 1
        else:
            print("✗ Kraken price function returned no data")
    except Exception as e:
        print(f"✗ Kraken price function failed: {str(e)}")

    print()

    # Test Coinbase price function
    try:
        from phineas.tools.crypto.exchanges.exchange_prices import get_coinbase_price

        print("Testing get_coinbase_price('BTC-USD')...")
        result = get_coinbase_price.invoke({"product_id": "BTC-USD"})

        if result and result.get("price"):
            print(f"✓ Coinbase price function works")
            print(f"  Price: ${result['price']}")
            print(f"  Bid: ${result.get('bid', 'N/A')}")
            print(f"  Ask: ${result.get('ask', 'N/A')}")
            success_count += 1
        else:
            print("✗ Coinbase price function returned no data")
    except Exception as e:
        print(f"✗ Coinbase price function failed: {str(e)}")

    return success_count == total_tests


def main():
    """Run all tests."""
    results = {
        "Environment Variables": test_environment_variables(),
        "Dependencies": test_dependencies(),
        "Kraken API": test_kraken_api(),
        "Coinbase API": test_coinbase_api(),
        "Price Functions": test_price_functions(),
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
        print("\n🎉 All tests passed! Exchange APIs are ready to use.")
        print("\nAvailable functions:")
        print("  • get_kraken_price(pair='BTC/USD')")
        print("  • get_coinbase_price(product_id='BTC-USD')")
        print("  • compare_exchange_prices(crypto='BTC', fiat='USD')")
        return 0
    else:
        failed = total_tests - total_passed
        print(f"\n⚠ {failed} test(s) failed. Review output above.")

        if not results["Dependencies"]:
            print("\n📦 Install missing dependencies:")
            print("  pip install pyjwt cryptography")

        return 1


if __name__ == "__main__":
    sys.exit(main())
