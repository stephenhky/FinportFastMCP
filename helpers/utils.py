
import random
from datetime import datetime


def generate_timestr_filename() -> str:
    name = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=20))
    timestr = datetime.strftime(datetime.utcnow(), '%Y%m%d%H%M%SUTC%z')
    return f"{timestr}_{name}"
