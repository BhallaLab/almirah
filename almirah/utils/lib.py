"""Library-specific utility functins."""

import re
from typing import Tuple
from pathlib import Path


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

    SUPPORTED_DTYPES = {"str", "date", "float", "boolean", "integer", "datetime"}

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


def create_tutorial_dataset(root: str) -> None:
    """
    Create tutorial dataset at root.

    Parameters
    ----------
    root : str
        The path where the dataset will be created.
    """

    # Define the structure of directories and files
    structure = {
        "": ["DAY01_G171_20180101.npy", "Day2_171_20180102.npy"],
        "72": ["DAY01_G72_20180201.npy", "DAY02_G72_20180202.npy"],
        "G433": ["DAY_G433_20180301.npy", "day02_G433_20180301.npy"],
    }

    # Ensure the root directory exists
    root_path = Path(root)
    root_path.mkdir(parents=True, exist_ok=True)

    # Loop through the structure dictionary to create files
    for directory, files in structure.items():
        dir_path = root_path / directory
        dir_path.mkdir(parents=True, exist_ok=True)

        for file_name in files:
            file_path = dir_path / file_name
            file_path.touch()
