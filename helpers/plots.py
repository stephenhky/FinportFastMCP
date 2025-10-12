
from datetime import datetime

import pandas as pd
from plotnine import ggplot, aes, geom_line, theme, element_text, scale_x_datetime, labs, ggtitle
from mizani.breaks import date_breaks


def get_optimal_daybreaks(startdate: str, enddate: str) -> str:
    timediff = datetime.strptime(enddate, '%Y-%m-%d') - datetime.strptime(startdate, '%Y-%m-%d')
    nbdaysdiff = timediff.days
    if nbdaysdiff > 730:
        return '1 year'
    elif nbdaysdiff > 365:
        return '3 months'
    elif nbdaysdiff > 30:
        return '1 month'
    else:
        return '1 day'


def plot_from_dataframe(
        df: pd.DataFrame,
        date_field: str,
        price_field: str,
        color_field: str,
        daybreaks: str,
        title: str=None
) -> ggplot:
    plt = (ggplot(df)
           + geom_line(aes(date_field, price_field, color=color_field))
           + theme(axis_text_x=element_text(rotation=90, hjust=1))
           + scale_x_datetime(breaks=date_breaks(daybreaks))
           + labs(x='Date', y='Value'))
    if title is not None:
        plt += ggtitle(title)
    return plt


def plot_from_dataframe_group1(
        df: pd.DataFrame,
        date_field: str,
        price_field: str,
        color_field: str,
        daybreaks: str,
        title: str=None
) -> ggplot:
    plt = (ggplot(df)
           + geom_line(aes(date_field, price_field, color=color_field, group=1))
           + theme(axis_text_x=element_text(rotation=90, hjust=1))
           + scale_x_datetime(breaks=date_breaks(daybreaks))
           + labs(x='Date', y='Value'))
    if title is not None:
        plt += ggtitle(title)
    return plt
