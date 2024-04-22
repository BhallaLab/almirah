"""Library-specific utility functins."""

import os
import re
from typing import Tuple

from os.path import dirname as up

from .gen import copy


def extract_dtype_from_db_type_string(
    type_string: str, default_length: int = 250
) -> Tuple[str, int]:
    """
    Extract supported dtype and length from type string representation.

    Parameters
    ----------
    type_string : str
        String representation of the data type.
    default_length : int, optional
        Default length for string data type if not specified.

    Returns
    -------
    Tuple[str, int]
        A tuple containing the data type and its length.

    Raises
    ------
    TypeError
        If the data type is not supported.
    ValueError
        If a non-string data type incorrectly specifies a length.
    """

    SUPPORTED_DTYPES = {"boolean", "datetime", "float", "integer", "str"}

    match = re.match(r"(\w+).?(\d+)?", type_string)
    if not match:
        raise ValueError(f"Invalid type string format: {type_string}")

    dtype, length = match.groups()
    if dtype not in SUPPORTED_DTYPES:
        raise TypeError(f"Unsupported dtype '{dtype}' encountered")

    if length is not None and dtype != "str":
        raise ValueError(f"Length specified for non-string dtype '{dtype}'")

    if length is None and dtype == "str":
        length = default_length

    return dtype, int(length) if length else None


def get_tutorial_dataset(dst: str) -> None:
    """
    Copies the tutorial dataset to destination.

    Parameters
    ----------
    dst : str
        The destination path where the dataset will be copied.
    """

    from almirah import __file__ as this_file

    path = os.path.join(up(up(this_file)), "tests/data/tutorial")
    copy(path, dst)
