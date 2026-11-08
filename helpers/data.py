
from time import sleep
from socket import timeout
from urllib.error import URLError

import pandas as pd
from finsim.data import get_yahoofinance_data
from loguru import logger


def waiting_get_yahoofinance_data(
        symbol: str,
        startdate: str,
        enddate: str,
        waittime: int = 1,
        max_retries: int = 5
) -> pd.DataFrame:
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            symdf = get_yahoofinance_data(symbol, startdate, enddate)
            return symdf
        except ConnectionError as error:
            last_error = error
            logger.warning(
                f"ConnectionError fetching {symbol} (attempt {attempt}/{max_retries}): {error}"
            )
            if attempt < max_retries:
                sleep(min(10, waittime * attempt))
        except (URLError, timeout) as error:
            last_error = error
            logger.warning(
                f"Network timeout/URLError fetching {symbol} (attempt {attempt}/{max_retries}): {error}"
            )
            if attempt < max_retries:
                sleep(waittime * attempt)
    raise RuntimeError(
        f"Failed to retrieve Yahoo Finance data for {symbol} ({startdate} to {enddate}) "
        f"after {max_retries} attempts: {last_error}"
    ) from last_error
