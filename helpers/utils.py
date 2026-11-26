
import os
import random
import tempfile
from datetime import date, datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from typing import Optional


def generate_timestr_filename() -> str:
    name = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=20))
    timestr = datetime.strftime(datetime.now(timezone.utc), '%Y%m%d%H%M%SUTC%z')
    return f"{timestr}_{name}"


def get_temp_filepath(filename: str) -> str:
    """Return a path inside the system temp directory (/tmp on AWS Lambda)."""
    return os.path.join(tempfile.gettempdir(), filename)


def resolve_date_range(
    startdate: Optional[date],
    enddate: Optional[date],
    default_days: int = 365,
) -> tuple[date, date]:
    if enddate is None:
        enddate = datetime.now(ZoneInfo("America/New_York")).date()
    if startdate is None:
        startdate = enddate - timedelta(days=default_days)
    return startdate, enddate
