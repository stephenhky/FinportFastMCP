
from time import sleep
from socket import timeout
from urllib.error import URLError

import pandas as pd
from finsim.data import get_yahoofinance_data


def waiting_get_yahoofinance_data(
        symbol: str,
        startdate: str,
        enddate: str,
        waittime: int=1
) -> pd.DataFrame:
    done = False
    while not done:
        try:
            symdf = get_yahoofinance_data(symbol, startdate, enddate)
            done = True
        except ConnectionError:
            sleep(10)
        except URLError as error:
            if isinstance(error, timeout):
                sleep(waittime)
    return symdf
