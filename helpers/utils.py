
import os
import random
import tempfile
from datetime import datetime, timezone


def generate_timestr_filename() -> str:
    name = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=20))
    timestr = datetime.strftime(datetime.now(timezone.utc), '%Y%m%d%H%M%SUTC%z')
    return f"{timestr}_{name}"


def get_temp_filepath(filename: str) -> str:
    """Return a path inside the system temp directory (/tmp on AWS Lambda)."""
    return os.path.join(tempfile.gettempdir(), filename)
