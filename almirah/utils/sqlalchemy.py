"""SQLAlchemy utility functions."""

from typing import Type
from typing import Union

from sqlalchemy.types import Float
from sqlalchemy.types import String
from sqlalchemy.types import Boolean
from sqlalchemy.types import Integer
from sqlalchemy.types import DateTime

from .lib import extract_dtype_from_db_type_string


def get_sql_type(
    type_string: str, default_length: int = 250
) -> Union[Type[Float], Type[String], Type[Boolean], Type[Integer], Type[DateTime]]:
    """
    Return the SQLAlchemy type equivalent for a given type string representation.

    Parameters
    ----------
    type_string : str
        The string representation of the data type.
    default_length : int, optional
        The default length for string types, used if no length specifie.

    Returns
    -------
    Type
        The SQLAlchemy type that corresponds to the provided type string.

    Raises
    ------
    ValueError
        If the type string does not correspond to a supported SQLAlchemy type.
    """

    SQL_TYPE_EQUIVALENT = {
        "boolean": Boolean,
        "datetime": DateTime,
        "float": Float,
        "integer": Integer,
        "str": String,
    }

    dtype, length = extract_dtype_from_db_type_string(type_string, default_length)
    if dtype not in SQL_TYPE_EQUIVALENT:
        raise ValueError(f"Unsupported dtype '{dtype}' encountered.")

    sql_type = SQL_TYPE_EQUIVALENT[dtype]
    return sql_type(length) if length else sql_type()
