
import os
import tempfile
from typing import Optional
from math import sqrt
from datetime import date

# Ensure Matplotlib writes its font/config cache to a writable directory (/tmp in AWS Lambda)
os.environ.setdefault("MPLCONFIGDIR", os.path.join(tempfile.gettempdir(), "matplotlib"))

import numpy as np
import pandas as pd
from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from finsim.estimate.fit import fit_BlackScholesMerton_model, fit_multivariate_BlackScholesMerton_model
from finsim.estimate.risk import estimate_downside_risk, estimate_upside_risk, estimate_beta
from lppl.fit import LPPLModel
from dotenv import load_dotenv
import matplotlib
from loguru import logger

from helpers.data import waiting_get_yahoofinance_data
from helpers.utils import resolve_date_range
from apischemas.schemas import SymbolEstimationResult, SymbolsCorrelationResult, SimplifiedLPPLCrashModelResult


# load additional environment variables
load_dotenv()
public_s3_bucket = os.environ.get('PUBLIC_S3_BUCKET')

# not using interactive web interface for matplotlib
matplotlib.use('agg')

# Create a basic server instance
mcp = FastMCP(name="Financial Calculator MCP Server")


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> PlainTextResponse:
    """
    Health check for the MCP server.
    """
    return PlainTextResponse("OK")


@mcp.tool
def greet(name: str) -> str:
    """
    Greet the user.
    """
    return f"Hello, {name}!"


@mcp.tool
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b


@mcp.tool
def get_symbol_closing_price_given_date(
        symbol: str,
        given_date: Optional[date] = None
) -> float:
    """
    Get the closing price of the given symbol on the given date.
    If given_date is not provided, it defaults to today's date (America/New_York).
    """
    if given_date is None:
        _, given_date = resolve_date_range(None, None)
    given_date_str = given_date.strftime("%Y-%m-%d")
    # getting stock data
    symdf = waiting_get_yahoofinance_data(symbol, given_date_str, given_date_str)
    if symdf.empty:
        raise ValueError(f"No market data returned for symbol '{symbol}' on {given_date_str}.")
    return float(symdf.loc[0, "Close"])


@mcp.tool
def estimate_symbol_info(
        symbol: str,
        startdate: Optional[date] = None,
        enddate: Optional[date] = None,
        index: str = '^GSPC'    # i.e., S&P 500 index as the base for calculating beta
) -> SymbolEstimationResult:
    """
    Estimate information about the given symbol within the start and end dates.
    It gives the yield rate, volatility, downside risk, upside risk, and beta.

    If the startdate is not given, it is assumed to be one year before the enddate.
    If the enddate is not given, it is assumed to be today.
    """
    logger.info("Handling input date range.")
    startdate, enddate = resolve_date_range(startdate, enddate)
    start_str = startdate.strftime("%Y-%m-%d")
    end_str = enddate.strftime("%Y-%m-%d")

    # getting stock data
    symdf = waiting_get_yahoofinance_data(symbol, start_str, end_str)
    if symdf.empty:
        raise ValueError(f"No market data returned for symbol '{symbol}' between {start_str} and {end_str}.")
    logger.info("Number of lines: {}".format(len(symdf)))

    # getting index
    indexdf = waiting_get_yahoofinance_data(index, start_str, end_str)

    # estimation
    isrownull = symdf['Close'].isnull()
    r, sigma = fit_BlackScholesMerton_model(
        symdf.loc[~isrownull, 'TimeStamp'].to_numpy(),
        symdf.loc[~isrownull, 'Close'].to_numpy()
    )
    downside_risk = estimate_downside_risk(
        symdf.loc[~isrownull, 'TimeStamp'].to_numpy(),
        symdf.loc[~isrownull, 'Close'].to_numpy(),
        0.0
    )
    upside_risk = estimate_upside_risk(
        symdf.loc[~isrownull, 'TimeStamp'].to_numpy(),
        symdf.loc[~isrownull, 'Close'].to_numpy(),
        0.0
    )
    try:
        mgdf = indexdf[['TimeStamp', 'Close']].merge(symdf[['TimeStamp', 'Close']], on='TimeStamp', how='left')
        mgdf = mgdf.loc[~pd.isna(mgdf['Close_x']) & ~pd.isna(mgdf['Close_y']), :]
        beta = estimate_beta(
            mgdf['TimeStamp'].to_numpy(),
            mgdf['Close_y'].to_numpy(),
            mgdf['Close_x'].to_numpy()
        )
    except Exception:
        logger.warning('Index {} failed to be integrated.'.format(index))
        beta = None

    return SymbolEstimationResult(
        symbol=symbol,
        r=r,
        volatility=sigma,
        downside_risk=downside_risk,
        upside_risk=upside_risk,
        beta=beta if beta is not None else None,
        data_startdate=symdf['TimeStamp'].iloc[0].date(),
        data_enddate=symdf['TimeStamp'].iloc[-1].date(),
        nbrecords=len(symdf.loc[~isrownull, :])
    )


@mcp.tool
def estimate_symbols_correlation(
        symbol1: str,
        symbol2: str,
        startdate: Optional[date] = None,
        enddate: Optional[date] = None
) -> SymbolsCorrelationResult:
    """
    Estimate the correlation between two given symbols within the start and end dates.

    If the startdate is not given, it is assumed to be one year before the enddate.
    If the enddate is not given, it is assumed to be today.
    """
    logger.info("Handling input date range.")
    startdate, enddate = resolve_date_range(startdate, enddate)
    start_str = startdate.strftime("%Y-%m-%d")
    end_str = enddate.strftime("%Y-%m-%d")

    # get symbols' prices
    sym1df = waiting_get_yahoofinance_data(symbol1, start_str, end_str)
    sym2df = waiting_get_yahoofinance_data(symbol2, start_str, end_str)
    combined_df = sym1df[['TimeStamp', 'Close']].rename(columns={'Close': 'Close1'}). \
        merge(
        sym2df[['TimeStamp', 'Close']].rename(columns={'Close': 'Close2'}),
        on='TimeStamp', how='inner'
    )

    # computation
    rarray, covmat = fit_multivariate_BlackScholesMerton_model(
        combined_df['TimeStamp'].to_numpy(),
        np.array([
            combined_df['Close1'].to_numpy(),
            combined_df['Close2'].to_numpy()
        ])
    )

    return SymbolsCorrelationResult(
        symbol1=symbol1,
        symbol2=symbol2,
        r1=rarray[0],
        r2=rarray[1],
        std1=sqrt(covmat[0, 0]),
        std2=sqrt(covmat[1, 1]),
        covariance=covmat[1, 0],
        correlation=covmat[1, 0] / sqrt(covmat[0, 0] * covmat[1, 1]),
        startdate=startdate,
        enddate=enddate
    )


@mcp.tool
def predict_crash(
        symbol: str="^GSPC",   # default to be S&P 500
        startdate: Optional[date] = None,
        enddate: Optional[date] = None
) -> SimplifiedLPPLCrashModelResult:
    """
    Predict the crash date of the given symbol and within the start and end dates.
    If the symbol is not given, it is assumed to be the S & P 500 index (^GSPC).

    If the startdate is not given, it is assumed to be one year before the enddate.
    If the enddate is not given, it is assumed to be today.
    """
    logger.info("Handling input date range.")
    startdate, enddate = resolve_date_range(startdate, enddate)

    # get symbols
    logger.info("Getting symbol data.")
    symdf = waiting_get_yahoofinance_data(
        symbol,
        startdate.strftime("%Y-%m-%d"),
        enddate.strftime("%Y-%m-%d"),
    )

    # fitting
    logger.info("Fiting LPPL model...")
    fitted_lppl_model = LPPLModel()
    fitted_lppl_model.tcgap = 60 * 60 * 24
    fitted_lppl_model.fit(symdf['TimeStamp'].map(lambda ts: ts.timestamp()), symdf['Close'])

    # gathering output
    logger.info("Outputting model parameters.")
    model_parameters = fitted_lppl_model.dump_model_parameters()
    result = SimplifiedLPPLCrashModelResult(
        symbol=symbol,
        startdate=startdate,
        enddate=enddate,
        estimated_crash_date=pd.Timestamp.fromtimestamp(model_parameters['tc']).to_pydatetime().date()
    )
    logger.info(result)
    return result


if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    stateless_http = os.environ.get("FASTMCP_STATELESS_HTTP", "true").lower() in ("1", "true", "yes")
    mcp.run(
        transport="streamable-http",
        host=host,
        port=port,
        stateless_http=stateless_http,
    )
