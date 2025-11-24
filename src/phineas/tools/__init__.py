# This file makes the directory a Python package
from typing_extensions import Callable
from phineas.tools.finance.filings import get_filings
from phineas.tools.finance.filings import get_10K_filing_items
from phineas.tools.finance.filings import get_10Q_filing_items
from phineas.tools.finance.filings import get_8K_filing_items
from phineas.tools.finance.fundamentals import get_income_statements
from phineas.tools.finance.fundamentals import get_balance_sheets
from phineas.tools.finance.fundamentals import get_cash_flow_statements
from phineas.tools.finance.fundamentals import get_all_financial_statements
from phineas.tools.finance.metrics import get_financial_metrics_snapshot
from phineas.tools.finance.metrics import get_financial_metrics
from phineas.tools.finance.prices import get_price_snapshot
from phineas.tools.finance.prices import get_prices
from phineas.tools.finance.news import get_news
from phineas.tools.finance.estimates import get_analyst_estimates
from phineas.tools.finance.segments import get_segmented_revenues
from phineas.tools.search.google import search_google_news
from phineas.tools.crypto.prices import get_crypto_price
from phineas.tools.crypto.prices import get_multiple_crypto_prices
from phineas.tools.crypto.prices import get_crypto_market_data
from phineas.tools.crypto.prices import get_top_cryptos
from phineas.tools.crypto.ohlc import get_crypto_ohlc
from phineas.tools.crypto.ohlc import get_crypto_market_chart
from phineas.tools.crypto.ohlc import get_crypto_market_chart_range
from phineas.tools.crypto.ohlc import get_crypto_historical_data
from phineas.tools.crypto.volatility import analyze_crypto_volatility
from phineas.tools.crypto.volatility import analyze_price_action
from phineas.tools.crypto.volatility import compare_crypto_performance

TOOLS: list[Callable[..., any]] = [
    # Stock market tools
    get_income_statements,
    get_balance_sheets,
    get_cash_flow_statements,
    get_all_financial_statements,
    get_10K_filing_items,
    get_10Q_filing_items,
    get_8K_filing_items,
    get_filings,
    get_price_snapshot,
    get_prices,
    get_financial_metrics_snapshot,
    get_financial_metrics,
    get_news,
    get_analyst_estimates,
    get_segmented_revenues,
    search_google_news,
    # Crypto market tools
    get_crypto_price,
    get_multiple_crypto_prices,
    get_crypto_market_data,
    get_top_cryptos,
    get_crypto_ohlc,
    get_crypto_market_chart,
    get_crypto_market_chart_range,
    get_crypto_historical_data,
    analyze_crypto_volatility,
    analyze_price_action,
    compare_crypto_performance,
]
