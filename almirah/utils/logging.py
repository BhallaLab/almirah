"""Logging utility functions."""

import logging
import pandas as pd
from typing import List, Union


def log_df(
    df: pd.DataFrame,
    msg: str,
    hide: Union[List[str], str] = [],
    level: int = logging.ERROR,
    **kwargs
) -> None:
    """
    Log DataFrame records with a message.

    Parameters
    ----------
    df: pandas.DataFrame
        DataFrame to be logged.
    msg: str
        Log message compatible with string formatting.
    hide: list-like or scalar, optional
        Sensitive column or columns to hide.
    level: int, optional
        Logging level to use. Accepts logging.LEVEL values.
    kwargs: key, value mappings
        Other keyword arguments are passed to `str.format()`.
    """
    if not df.empty:
        logging.log(level, msg + "\n%s", df.drop(columns=hide).to_string(), **kwargs)


def log_col(
    series: pd.Series,
    msg: str,
    hide: bool = False,
    level: int = logging.ERROR,
    **kwargs
) -> None:
    """
    Log column values with a message.

    Parameters
    ----------
    series : pd.Series
        Series to be logged.
    msg : str
        Log message compatible with string formatting.
    hide : bool, optional
        If True, hides the values of the series.
    level : int, optional
        Logging level to use. Accepts logging.LEVEL values.
    kwargs : key, value mappings
        Other keyword arguments are passed to `str.format()`.
    """

    if hide:
        series = series.index.to_series()
        logging.info("Column values will not be displayed as hide set")

    if not series.empty:
        logging.log(level, msg + "\n%s", series.to_string(), **kwargs)
