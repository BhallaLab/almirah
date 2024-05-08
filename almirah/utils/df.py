"""Dataframe manipulation utility functions."""

import pandas as pd

from typing import Any

from .lib import extract_dtype_from_db_type_string


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

    dtype_conversion_map = {
        str: lambda x: x.astype(dtype),
        "datetime": lambda x: pd.to_datetime(x, errors="coerce", **kwargs),
        "float": lambda x: pd.to_numeric(x, errors="coerce", downcast="float"),
        "integer": lambda x: pd.to_numeric(x, errors="coerce", downcast="integer"),
        "boolean": lambda x: x.replace(
            {
                "1": True,
                "0": False,
                "True": True,
                "False": False,
                "Yes": True,
                "No": False,
            }
        ).astype(dtype),
    }

    return dtype_conversion_map.get(dtype, lambda x: x)(series).convert_dtypes()


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
