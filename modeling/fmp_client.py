import os
import json
import fmpsdk
import requests
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, date
from decimal import Decimal
from dotenv import load_dotenv
from box import Box, BoxList

# Load environment variables
load_dotenv()


class FMPClient:
    """Enhanced client for Financial Modeling Prep API using fmpsdk"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or self._get_api_key()

    def _get_api_key(self) -> str:
        """Get FMP API key from environment"""
        api_key = os.getenv("FINANCIAL_MODELING_PREP_KEY") or os.getenv("FMP_API_KEY")
        if not api_key:
            raise ValueError(
                "FMP API key not found. Set FINANCIAL_MODELING_PREP_KEY or FMP_API_KEY environment variable"
            )
        return api_key

    def _to_box(self, data: List[Dict[str, Any]]) -> BoxList:
        """Convert FMP response to Box objects for cleaner access"""
        return BoxList(
            [Box(item, default_box=True, default_box_attr=None) for item in data]
        )

    def get_income_statement(
        self, ticker: str, period: str = "annual", limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get income statements for a ticker"""
        return fmpsdk.income_statement(
            apikey=self.api_key, symbol=ticker.upper(), period=period, limit=limit
        )

    def get_income_statement_box(
        self, ticker: str, period: str = "annual", limit: int = 10
    ) -> BoxList:
        """Get income statements for a ticker as Box objects"""
        data = self.get_income_statement(ticker, period, limit)
        return self._to_box(data)

    def get_balance_sheet(
        self, ticker: str, period: str = "annual", limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get balance sheet statements for a ticker"""
        return fmpsdk.balance_sheet_statement(
            apikey=self.api_key, symbol=ticker.upper(), period=period, limit=limit
        )

    def get_cash_flow_statement(
        self, ticker: str, period: str = "annual", limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get cash flow statements for a ticker"""
        return fmpsdk.cash_flow_statement(
            apikey=self.api_key, symbol=ticker.upper(), period=period, limit=limit
        )

    def get_company_profile(self, ticker: str) -> List[Dict[str, Any]]:
        """Get company profile information"""
        return fmpsdk.company_profile(apikey=self.api_key, symbol=ticker.upper())

    def get_key_metrics(
        self, ticker: str, period: str = "annual", limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get key financial metrics"""
        return fmpsdk.key_metrics(
            apikey=self.api_key, symbol=ticker.upper(), period=period, limit=limit
        )

    def get_financial_ratios(
        self, ticker: str, period: str = "annual", limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get financial ratios"""
        return fmpsdk.financial_ratios(
            apikey=self.api_key, symbol=ticker.upper(), period=period, limit=limit
        )

    def get_enterprise_values(
        self, ticker: str, period: str = "annual", limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get enterprise values"""
        return fmpsdk.enterprise_values(
            apikey=self.api_key, symbol=ticker.upper(), period=period, limit=limit
        )

    def get_dcf_values(self, ticker: str) -> List[Dict[str, Any]]:
        """Get DCF valuation"""
        return fmpsdk.discounted_cash_flow(apikey=self.api_key, symbol=ticker.upper())

    def get_financial_growth(
        self, ticker: str, period: str = "annual", limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get financial growth metrics"""
        return fmpsdk.financial_growth(
            apikey=self.api_key, symbol=ticker.upper(), period=period, limit=limit
        )

    def get_income_statement_growth(
        self, ticker: str, period: str = "annual", limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get income statement growth rates"""
        return fmpsdk.income_statement_growth(
            apikey=self.api_key, symbol=ticker.upper(), period=period, limit=limit
        )

    def get_balance_sheet_growth(
        self, ticker: str, period: str = "annual", limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get balance sheet growth rates"""
        return fmpsdk.balance_sheet_statement_growth(
            apikey=self.api_key, symbol=ticker.upper(), period=period, limit=limit
        )

    def get_cash_flow_growth(
        self, ticker: str, period: str = "annual", limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get cash flow growth rates"""
        return fmpsdk.cash_flow_statement_growth(
            apikey=self.api_key, symbol=ticker.upper(), period=period, limit=limit
        )

    def get_quote(self, ticker: str) -> List[Dict[str, Any]]:
        """Get real-time quote"""
        return fmpsdk.quote(apikey=self.api_key, symbol=ticker.upper())

    def get_market_cap(self, ticker: str) -> List[Dict[str, Any]]:
        """Get market capitalization"""
        return fmpsdk.market_capitalization(apikey=self.api_key, symbol=ticker.upper())

    def get_sp500_constituents(self) -> List[Dict[str, Any]]:
        """Get list of S&P 500 constituents

        Returns:
            List of dictionaries containing S&P 500 constituent data including:
            - symbol: Stock ticker symbol
            - name: Company name
            - sector: Company sector
            - subSector: Company sub-sector
            - headQuarter: Company headquarters location
            - dateFirstAdded: Date when the company was first added to S&P 500
            - cik: Central Index Key
            - founded: Year the company was founded
        """
        try:
            url = f"https://financialmodelingprep.com/api/v3/sp500_constituent"
            params = {"apikey": self.api_key}

            response = requests.get(url, params=params)
            response.raise_for_status()

            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error fetching S&P 500 constituents: {str(e)}")
        except json.JSONDecodeError as e:
            raise Exception(f"Error parsing S&P 500 constituents response: {str(e)}")

    def get_all_financial_data(
        self, ticker: str, period: str = "annual", limit: int = 10
    ) -> Dict[str, Any]:
        """Get comprehensive financial data for a ticker using fmpsdk"""
        ticker = ticker.upper()

        try:
            # Core financial statements
            income_statements = self.get_income_statement(ticker, period, limit)
            balance_sheets = self.get_balance_sheet(ticker, period, limit)
            cash_flows = self.get_cash_flow_statement(ticker, period, limit)

            # Company information
            company_profile = self.get_company_profile(ticker)

            # Financial metrics and ratios
            key_metrics = self.get_key_metrics(ticker, period, limit)
            financial_ratios = self.get_financial_ratios(ticker, period, limit)
            enterprise_values = self.get_enterprise_values(ticker, period, limit)

            # Growth data
            financial_growth = self.get_financial_growth(ticker, period, limit)
            income_growth = self.get_income_statement_growth(ticker, period, limit)
            balance_growth = self.get_balance_sheet_growth(ticker, period, limit)
            cashflow_growth = self.get_cash_flow_growth(ticker, period, limit)

            # Valuation
            dcf_values = self.get_dcf_values(ticker)

            # Market data
            quote = self.get_quote(ticker)
            market_cap = self.get_market_cap(ticker)

            return {
                "ticker": ticker,
                "period": period,
                "limit": limit,
                "retrieved_at": datetime.now().isoformat(),
                "data_source": "fmpsdk",
                "data": {
                    # Core financial statements
                    "income_statements": income_statements,
                    "balance_sheets": balance_sheets,
                    "cash_flow_statements": cash_flows,
                    # Company information
                    "company_profile": company_profile,
                    # Metrics and ratios
                    "key_metrics": key_metrics,
                    "financial_ratios": financial_ratios,
                    "enterprise_values": enterprise_values,
                    # Growth data
                    "financial_growth": financial_growth,
                    "income_statement_growth": income_growth,
                    "balance_sheet_growth": balance_growth,
                    "cash_flow_growth": cashflow_growth,
                    # Valuation
                    "dcf_values": dcf_values,
                    # Market data
                    "quote": quote,
                    "market_capitalization": market_cap,
                },
            }

        except Exception as e:
            return {
                "ticker": ticker,
                "period": period,
                "limit": limit,
                "retrieved_at": datetime.now().isoformat(),
                "error": str(e),
                "data": {},
            }

    def save_to_json(self, data: Dict[str, Any], filename: str) -> None:
        """Save data to JSON file"""
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        # Custom JSON encoder for Decimal and datetime objects
        def json_encoder(obj):
            if isinstance(obj, Decimal):
                return float(obj)
            elif isinstance(obj, (datetime, date)):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

        with open(filename, "w") as f:
            json.dump(data, f, indent=2, default=json_encoder)

    def fetch_and_save_historical_data(
        self, ticker: str, output_dir: str = "temp_data"
    ) -> str:
        """Fetch all historical data and save to JSON file"""
        ticker = ticker.upper()

        # Get comprehensive financial data
        data = self.get_all_financial_data(ticker, period="annual", limit=20)

        # Save to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{output_dir}/{ticker}_historical_{timestamp}.json"
        self.save_to_json(data, filename)

        return filename

    def get_data_matching_report_columns(
        self, ticker: str, report_date: Optional[date] = None, years_back: int = 10
    ) -> Dict[str, Any]:
        """
        Get data specifically matching the columns shown in UNH.jpeg report:
        - Revenue, CAPEX, Debt, FCFE, Shares, FCF/Share, Price Estimate, FCFE Yield
        - EBITDA, Debt, EBITDA/Debt, Net Cash, EV, EV/EBITDA, ROA/EBITDA
        """
        ticker = ticker.upper()
        limit = years_back

        try:
            # Get all required data
            income_statements = self.get_income_statement(ticker, "annual", limit)
            balance_sheets = self.get_balance_sheet(ticker, "annual", limit)
            cash_flows = self.get_cash_flow_statement(ticker, "annual", limit)
            key_metrics = self.get_key_metrics(ticker, "annual", limit)
            financial_ratios = self.get_financial_ratios(ticker, "annual", limit)
            enterprise_values = self.get_enterprise_values(ticker, "annual", limit)
            company_profile = self.get_company_profile(ticker)
            financial_growth = self.get_financial_growth(ticker, "annual", limit)

            # Process data to match report columns
            processed_data = {
                "ticker": ticker,
                "report_date": (
                    report_date.isoformat() if report_date else date.today().isoformat()
                ),
                "retrieved_at": datetime.now().isoformat(),
                "years_requested": years_back,
                "raw_data": {
                    "income_statements": income_statements,
                    "balance_sheets": balance_sheets,
                    "cash_flow_statements": cash_flows,
                    "key_metrics": key_metrics,
                    "financial_ratios": financial_ratios,
                    "enterprise_values": enterprise_values,
                    "company_profile": company_profile,
                    "financial_growth": financial_growth,
                },
                "report_columns": self._extract_report_columns(
                    income_statements,
                    balance_sheets,
                    cash_flows,
                    key_metrics,
                    financial_ratios,
                    enterprise_values,
                ),
            }

            return processed_data

        except Exception as e:
            return {
                "ticker": ticker,
                "error": str(e),
                "retrieved_at": datetime.now().isoformat(),
            }

    def _extract_report_columns(
        self,
        income_statements,
        balance_sheets,
        cash_flows,
        key_metrics,
        financial_ratios,
        enterprise_values,
    ) -> Dict[str, List[Dict]]:
        """Store complete FMP data organized by year with minimal transformation"""

        # Organize complete FMP data by year with minimal processing
        years_data = {}

        # Store complete income statements by year
        for stmt in income_statements:
            year = stmt.get("calendarYear")
            if not year:
                continue

            if year not in years_data:
                years_data[year] = {
                    "year": year,
                    "complete_fmp_data": {},  # Store all FMP data here
                }

            # Store complete income statement data
            years_data[year]["complete_fmp_data"]["income_statement"] = stmt

            # Only add essential computed fields for backward compatibility
            years_data[year]["currency"] = stmt.get("reportedCurrency", "USD")
            years_data[year]["revenue"] = stmt.get("revenue")
            years_data[year]["shares_outstanding"] = stmt.get("weightedAverageShsOut")

            # Calculate EBITDA (commonly needed metric)
            if stmt.get("operatingIncome") and stmt.get("depreciationAndAmortization"):
                years_data[year]["ebitda"] = stmt.get("operatingIncome") + stmt.get(
                    "depreciationAndAmortization"
                )

        # Store complete balance sheet data
        for stmt in balance_sheets:
            year = stmt.get("calendarYear")
            if year in years_data:
                # Store complete balance sheet data
                years_data[year]["complete_fmp_data"]["balance_sheet"] = stmt

                # Add commonly used fields for backward compatibility
                years_data[year]["debt"] = stmt.get("totalDebt")
                years_data[year]["net_cash"] = (
                    (stmt.get("cashAndCashEquivalents", 0) - stmt.get("totalDebt", 0))
                    if stmt.get("cashAndCashEquivalents") and stmt.get("totalDebt")
                    else None
                )

        # Store complete cash flow data
        for stmt in cash_flows:
            year = stmt.get("calendarYear")
            if year in years_data:
                # Store complete cash flow data
                years_data[year]["complete_fmp_data"]["cash_flow"] = stmt

                # Add commonly used fields for backward compatibility
                years_data[year]["capex"] = abs(
                    stmt.get("capitalExpenditure", 0)
                )  # Make positive
                years_data[year]["fcfe"] = stmt.get("freeCashFlow", 0)

                # Calculate FCF per share if we have shares outstanding
                if stmt.get("freeCashFlow") and years_data[year].get(
                    "shares_outstanding"
                ):
                    years_data[year]["fcf_per_share"] = (
                        stmt.get("freeCashFlow")
                        / years_data[year]["shares_outstanding"]
                    )

        # Store complete key metrics
        for metrics in key_metrics:
            year = metrics.get("calendarYear")
            if year in years_data:
                # Store complete key metrics data
                years_data[year]["complete_fmp_data"]["key_metrics"] = metrics

                # Add commonly used fields for backward compatibility
                years_data[year]["enterprise_value"] = metrics.get("enterpriseValue")
                years_data[year]["ev_ebitda_ratio"] = metrics.get(
                    "enterpriseValueOverEBITDA"
                )

        # Store complete enterprise values (including historical stock prices)
        for ev in enterprise_values:
            year = ev.get("date", "")[:4]  # Extract year from date (YYYY-MM-DD format)
            if year in years_data:
                # Store complete enterprise values data
                years_data[year]["complete_fmp_data"]["enterprise_values"] = ev

                # Add critical fields for backward compatibility
                years_data[year]["stock_price"] = ev.get(
                    "stockPrice"
                )  # Historical stock price!
                years_data[year]["market_cap"] = ev.get("marketCapitalization")

        # Store complete financial ratios
        for ratios in financial_ratios:
            year = ratios.get("calendarYear")
            if year in years_data:
                # Store complete financial ratios data
                years_data[year]["complete_fmp_data"]["financial_ratios"] = ratios

                # Add commonly used ratios for backward compatibility
                years_data[year]["ebitda_debt_ratio"] = ratios.get("debtEquityRatio")
                years_data[year]["roa_ebitda_ratio"] = ratios.get("returnOnAssets")

        # Calculate only essential derived metrics (most calculations can now use complete FMP data directly)
        for year, data in years_data.items():
            # FCFE Yield (commonly needed for analysis)
            if data.get("fcfe") and data.get("market_cap") and data["market_cap"] > 0:
                data["fcfe_yield"] = data["fcfe"] / data["market_cap"]

            # Store complete data reference for easy access
            data["has_complete_fmp_data"] = bool(data.get("complete_fmp_data"))

        return {
            "yearly_data": list(years_data.values()),
            "available_years": sorted(years_data.keys(), reverse=True),
            "data_points": len(years_data),
        }
