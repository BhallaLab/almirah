"""Model base class."""

from typing import Any
from typing import Dict
from typing import List
from typing import Type
from typing import Optional

from sqlalchemy.orm import DeclarativeBase

from ..indexer import index


class Base(DeclarativeBase):
    """ORM Base object representation."""

    @classmethod
    def get(cls: Type["Base"], **filters) -> Optional["Base"]:
        """
        Return an instance from index if found, else None.

        Parameters
        ----------
        filters: dict
            Dictionary of filter conditions used for querying.

        Returns
        -------
            An instance of cls or None if not found.
        """
        return index.get(cls, **filters)

    @classmethod
    def get_identifiers(cls: Type["Base"], **kwargs) -> Dict[str, Any]:
        """
        Return dictionary of class identifier attributes and their values.

        Parameters
        ----------
        kwargs: key, value pairs
            Key-value pairs of identifier attributes and their values.

        Returns
        -------
            A dictionary of the identifiers with their respective values.
        """
        if not hasattr(cls, "__identifier_attrs__"):
            raise AttributeError(
                f"{cls.__name__} does not define '__identifier_attrs__'."
            )
        return {a: kwargs.get(a, None) for a in getattr(cls, "__identifier_attrs__")}

    @classmethod
    def options(cls: Type["Base"], **filters) -> List["Base"]:
        """
        Return all existing instances from index.

        Parameters
        ----------
        filters: dict
            Dictionary of filter conditions used for querying.

        Returns
        -------
            A list of instances of cls that match the filters.
        """
        return index.options(cls, **filters)
