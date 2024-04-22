"""Core function and decorator for look-up object instantiation.
Adapted from: https://github.com/sqlalchemy/sqlalchemy/wiki/UniqueObject
"""

import functools

from typing import Any
from typing import Type
from typing import Callable

from ..indexer import Indexer

from ..utils.gen import commafy
from ..utils.gen import get_incomplete_keys


def unique(
    index: Indexer, cls: Type, constructor: Callable, args: tuple, kwargs: dict
) -> Any:
    """
    Check and return existing instance if present, else create it.

    Parameters
    ----------
    index : Indexer
        The almirah index used to store cached instances.
    cls : Type
        The class of the object being instantiated.
    constructor : Callable
        A callable used to create the object if not found.
    args : tuple
        Positional arguments (should be empty for this usage).
    kwargs : dict
        Keyword arguments used to instantiate the class.

    Returns
    -------
    Any
        An instance of cls.

    Raises
    ------
    TypeError
        If positional arguments are given or required keyword arguments are missing.
    """

    if args:
        raise TypeError("__init__ does not take positional arguments")

    idens = cls.get_identifiers(**kwargs)
    if inc := get_incomplete_keys(idens):
        raise TypeError(
            f"__init__ missing required keyword-only arguments: {commafy(inc)}"
        )

    cache = getattr(index, "_unique_cache", None)
    if cache is None:
        index._unique_cache = cache = dict()

    key = (cls, tuple(idens.values()))
    with index.session.no_autoflush:
        obj = constructor(**kwargs)
        obj = cls.get(**{i: getattr(obj, i) for i in idens}) or obj

        if key in cache:
            obj = cache[key]
        else:
            cache[key] = obj

        index.add(obj)

    return obj


def uniquify(index: Any) -> Callable:
    """
    Class decorator to augment classes for look-up instantiation.

    Parameters
    ----------
    index : Indexer
        The index used to manage unique instances.

    Returns
    -------
    Callable
        A decorator that modifies a class to use unique instantiation.
    """

    def decorate(cls: Type) -> Type:
        """
        Decorates a class to modify its instantiation mechanism.

        Parameters
        ----------
        cls : Type
            The class to decorate.

        Returns
        -------
        Type
            The decorated class with modified instantiation behavior.
        """

        def _null_init_(self, *args, **kwargs):
            if not kwargs:
                raise TypeError("__init__ missing required arguments")

        @functools.wraps(cls)
        def __new__(cls, bases, *args, **kwargs):
            if not args and not kwargs:
                return object.__new__(cls)

            def constructor(*args, **kwargs):
                obj = object.__new__(cls)
                obj._init_(*args, **kwargs)
                return obj

            return unique(index, cls, constructor, args, kwargs)

        cls._init_ = cls.__init__
        cls.__init__ = _null_init_
        cls.__new__ = classmethod(__new__)

        return cls

    return decorate
