"""
Utilizing financialmodelingprep.com for their free-endpoint API
to gather company financials.

CONSOLIDATED DATA ACCESS: This module now uses the consolidated data access layer
to replace direct urllib calls with unified error handling, caching, and rate limiting.

NOTE: Some code taken directly from their documentation. See: https://financialmodelingprep.com/developer/docs/.
"""

import json, traceback
import logging

logger = logging.getLogger(__name__)

# Use fmpsdk via existing fmp_client as standard
import sys
from pathlib import Path

# Add parent directory to access fmp_client
sys.path.append(str(Path(__file__).parent.parent.parent))

from analysis.DCF.modeling.fmp_client import FMPClient

logger.info("✅ Using fmpsdk via FMPClient for DCF module")


def get_jsonparsed_data(url):
    """
    Fetch url, return parsed json using fmpsdk via FMPClient.

    This function is kept for backward compatibility with existing DCF code
    but now exclusively uses fmpsdk.

    args:
        url: the url to fetch.

    returns:
        parsed json
    """
    # Note: This is a compatibility wrapper - new code should use FMPClient directly
    logger.warning(
        f"get_jsonparsed_data is deprecated - use FMPClient methods directly for: {url}"
    )

    # Extract ticker and endpoint from URL for FMPClient
    import re

    # Simple URL parsing to maintain compatibility
    if "income-statement" in url:
        ticker_match = re.search(r"/([A-Z]+)\?", url)
        if ticker_match:
            client = FMPClient()
            return {"financials": client.get_income_statement(ticker_match.group(1))}
    elif "cash-flow-statement" in url:
        ticker_match = re.search(r"/([A-Z]+)\?", url)
        if ticker_match:
            client = FMPClient()
            return {"financials": client.get_cash_flow_statement(ticker_match.group(1))}
    elif "balance-sheet-statement" in url:
        ticker_match = re.search(r"/([A-Z]+)\?", url)
        if ticker_match:
            client = FMPClient()
            return {"financials": client.get_balance_sheet(ticker_match.group(1))}
    elif "enterprise-value" in url:
        ticker_match = re.search(r"/([A-Z]+)\?", url)
        if ticker_match:
            client = FMPClient()
            return {
                "enterpriseValues": client.get_enterprise_values(ticker_match.group(1))
            }

    # If we can't parse the URL, raise an error
    raise ValueError(f"Cannot convert URL to FMPClient method: {url}")


def get_EV_statement(ticker, period="annual"):
    """
    Fetch EV statement using fmpsdk via FMPClient.

    args:
        ticker: company ticker
        period: annual default, can fetch quarterly if specified
    returns:
        parsed EV statement
    """
    client = FMPClient()
    return {"enterpriseValues": client.get_enterprise_values(ticker, period)}


# Note: These functions could be consolidated with a statement_type parameter,
# but kept separate for clarity and backward compatibility with existing DCF code
def get_income_statement(ticker, period="annual", limit=10):
    """
    Fetch income statement using fmpsdk via FMPClient.

    args:
        ticker: company ticker.
        period: annual default, can fetch quarterly if specified.
        limit: number of periods to fetch

    returns:
        parsed company's income statement
    """
    client = FMPClient()
    return {"financials": client.get_income_statement(ticker, period, limit)}


def get_cashflow_statement(ticker, period="annual", limit=10):
    """
    Fetch cashflow statement using fmpsdk via FMPClient.

    args:
        ticker: company ticker.
        period: annual default, can fetch quarterly if specified.
        limit: number of periods to fetch

    returns:
        parsed company's cashflow statement
    """
    client = FMPClient()
    return {"financials": client.get_cash_flow_statement(ticker, period, limit)}


def get_balance_statement(ticker, period="annual", limit=10):
    """
    Fetch balance sheet statement using fmpsdk via FMPClient.

    args:
        ticker: company ticker.
        period: annual default, can fetch quarterly if specified.
        limit: number of periods to fetch

    returns:
        parsed company's balance sheet statement
    """
    client = FMPClient()
    return {"financials": client.get_balance_sheet(ticker, period, limit)}


# Enhanced functions using FMPClient for comprehensive data fetching
def get_comprehensive_historical_data(
    ticker: str, years_back: int = 10, period: str = "annual"
) -> dict:
    """
    Fetch comprehensive historical data for enhanced DCF analysis using fmpsdk.
    This replaces the generalized_dcf_forecaster's data fetching functionality.

    Args:
        ticker: Stock ticker symbol
        years_back: Number of years of historical data to fetch
        period: 'annual' or 'quarter'

    Returns:
        Comprehensive historical data matching generalized_dcf_forecaster format
    """
    ticker = ticker.upper()

    try:
        client = FMPClient()

        # Get comprehensive data using FMPClient's method
        raw_data = client.get_data_matching_report_columns(
            ticker, years_back=years_back
        )

        if "error" in raw_data:
            raise Exception(f"FMPClient error: {raw_data['error']}")

        # Transform to match expected format
        yearly_metrics = raw_data.get("report_columns", {}).get("yearly_data", [])

        return {
            "ticker": ticker,
            "currency": "USD",
            "data_source": "fmpsdk_via_fmp_client",
            "years_of_data": len(yearly_metrics),
            "data_sources": ["Financial Modeling Prep via fmpsdk"],
            "yearly_metrics": yearly_metrics,
            "raw_fmp_data": raw_data.get("raw_data", {}),
        }

    except Exception as e:
        logger.error(f"FMPClient data fetch failed for {ticker}: {e}")
        raise
