"""Dataframe manipulation utility functions."""

import pandas as pd

from typing import Any

from datetime import date
from datetime import datetime

from .lib import extract_dtype_from_db_type_string


def common_rows(
    child: pd.DataFrame,
    parent: pd.DataFrame,
    child_on: Any = None,
    parent_on: Any = None,
) -> pd.Series:
    """
    Return boolean mask where True if record common in Child and Parent.

    Parameters
    ----------
    child : pd.DataFrame
        The child dataframe.
    parent : pd.DataFrame
        The parent dataframe.
    child_on : Any
        Column or index level names in child to join on.
    parent_on : Any
        Column or index level names in parent to join on.

    Returns
    -------
    pd.Series
        A Boolean series indicating common rows.
    """

    merged = pd.merge(
        child.reset_index(),
        parent,
        how="left",
        left_on=child_on,
        right_on=parent_on,
        indicator=True,
    ).set_index("index")
    return merged["_merge"].eq("both")


def convert_column_type(
    series: pd.Series,
    type_string: str,
    **kwargs,
) -> pd.Series:
    """
    Convert series to pandas dtype specified in type string representation.

    Parameters
    ----------
    series: pd.Series
        Series for which the dtype has to set.
    type_string: str
        Supported dtype to which the series will be converted.
    kwargs: key, value mappings
        Other keyword arguments are passed down to
        :doc:`pandas:reference/api/pandas.to_datetime` if the dtype
        is 'datetime'.

    Returns
    -------
    pd.Series
        The converted series with the appropriate dtype.
    """
    dtype, _ = extract_dtype_from_db_type_string(type_string)

    if dtype == str:
        series = series.astype(dtype)

    elif dtype == "datetime":
        series = pd.to_datetime(series, errors="coerce", **kwargs)

    elif dtype == "date":
        series = pd.to_datetime(series, errors="coerce", **kwargs).dt.date

    elif dtype in {"float", "integer"}:
        series = pd.to_numeric(series, errors="coerce", downcast=dtype)

    elif dtype == "boolean":
        series = series.map(
            {
                "1": True,
                "0": False,
                "True": True,
                "False": False,
                "Yes": True,
                "No": False,
            }
        )
        series = series.astype(dtype)

    return series.convert_dtypes()


def python_to_pandas_type(python_type: Any) -> str:
    """Return pandas type equivalent of python type.

    Parameters
    ----------
    python_type: Any
        Python type for which pandas equivalent is required.

    Returns
    -------
    str
        String representation of a pandas dtype.
    """
    PANDAS_TYPE_EQUIVALENT = {
        int: "Int64",
        str: "string",
        bool: "boolean",
        float: "float",
        date: "datetime64[ns]",
        datetime: "datetime64[ns]",
    }
    return PANDAS_TYPE_EQUIVALENT[python_type]
