
import os
from typing import Optional
from math import sqrt
from datetime import datetime, timedelta

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
def estimate_symbol_info(
        symbol: str,
        startdate: str,
        enddate: str,
        index: str='^GSPC'    # i.e., S&P 500 index as the base for calculating beta
) -> SymbolEstimationResult:
    """
    Estimate information about the given symbol within the start and end dates.
    It gives the yield rate, volatility, downside risk, upside risk, and beta.
    """
    # getting stock data
    symdf = waiting_get_yahoofinance_data(symbol, startdate, enddate)
    print("Number of lines: {}".format(len(symdf)))

    # getting index
    indexdf = waiting_get_yahoofinance_data(index, startdate, enddate)

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
    except:
        logger.warning('Index {} failed to be integrated.'.format(index))
        beta = None

    return SymbolEstimationResult(
        symbol=symbol,
        r=r,
        volatility=sigma,
        downside_risk=downside_risk,
        upside_risk=upside_risk,
        beta=beta if beta is not None else None,
        data_startdate=symdf['TimeStamp'][0].date(),
        data_enddate=symdf['TimeStamp'][len(symdf) - 1].date(),
        nbrecords=len(symdf.loc[~isrownull, :])
    )


@mcp.tool
def estimate_symbols_correlation(
        symbol1: str,
        symbol2: str,
        startdate: str,
        enddate: str
) -> SymbolsCorrelationResult:
    """
    Estimate the correlation between two given symbols within the start and end dates.
    """
    # get symbols' prices
    sym1df = waiting_get_yahoofinance_data(symbol1, startdate, enddate)
    sym2df = waiting_get_yahoofinance_data(symbol2, startdate, enddate)
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
        startdate: Optional[str]=None,
        enddate: Optional[str]=None
) -> SimplifiedLPPLCrashModelResult:
    """
    Predict the crash date of the given symbol and within the start and end dates.
    If the symbol is not given, it is assumed to be the S & P 500 index.
    If the date range is None (not given), it is assumed to be the past year as the given data range.
    """
    logger.info("Handling input date range.")
    if startdate is None:
        startdate = (datetime.today() - timedelta(days=365)).strftime('%Y-%m-%d')
    if enddate is None:
        enddate = datetime.today().strftime('%Y-%m-%d')

    # get symbols
    logger.info("Getting symbol data.")
    symdf = waiting_get_yahoofinance_data(symbol, startdate, enddate)

    # fitting
    logger.info("Fiting LPPL model...")
    fitted_lppl_model = LPPLModel()
    fitted_lppl_model.tcgap = 60 * 60 * 24
    fitted_lppl_model.fit(symdf['TimeStamp'].map(lambda ts: ts.timestamp()), symdf['Close'])

    # gathering output
    logger.info("Outputting model parameters.")
    model_parameters = fitted_lppl_model.dump_model_parameters()
    logger.info(SimplifiedLPPLCrashModelResult(
        symbol=symbol,
        startdate=datetime.strptime(startdate, "%Y-%m-%d"),
        enddate=datetime.strptime(enddate, "%Y-%m-%d"),
        estimated_crash_date=pd.Timestamp.fromtimestamp(model_parameters['tc']).to_pydatetime().date()
    ))
    return SimplifiedLPPLCrashModelResult(
        symbol=symbol,
        startdate=startdate,
        enddate=enddate,
        estimated_crash_date=pd.Timestamp.fromtimestamp(model_parameters['tc']).to_pydatetime().date()
    )


if __name__ == "__main__":
    mcp.run(transport='streamable-http')
