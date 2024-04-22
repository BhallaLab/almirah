"""Indexing functionality for metadata search and filtering."""

import os
import traceback

from typing import Any
from typing import List
from typing import Type

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from .core import DBManager


class Indexer:
    """Interface to interact with the index."""

    db = None
    path = None
    _session = None

    def __init__(self, path=None, read_only=False):
        if not Indexer.db and not path:
            raise ValueError("Index database not set")

        if not Indexer.db or not Indexer.path:
            Indexer.path = os.path.expanduser(path)
            Indexer.db = DBManager(f"sqlite:///{Indexer.path}")
            Indexer.read_only = read_only

    def _build_query(self, cls: Type[Any], **kwargs) -> Any:
        """Builds a SQL query for the given class and filters."""
        stmt = select(cls)
        for attr, value in kwargs.items():
            stmt = stmt.where(getattr(cls, attr) == value)
        return stmt

    def add(self, *objects: Any) -> None:
        """Add objects to the index."""
        try:
            self.session.add_all(objects)
            if not Indexer.read_only:
                self.session.flush()

        except IntegrityError:
            self.rollback()
            self.commit()
            traceback.print_exc()

    def commit(self) -> None:
        """Commit the current transaction."""
        if not Indexer.read_only:
            self.session.commit()

    def get(self, cls: Type[Any], **identifiers) -> Any:
        """Retrieve a single object based on the identifiers."""
        stmt = self._build_query(cls, **identifiers)
        return self.retrieve(stmt).one_or_none()

    def options(self, cls: Type[Any], **filters) -> List[Any]:
        """Retrieve all objects matching the given filters."""
        stmt = self._build_query(cls, **filters)
        return self.retrieve(stmt).all()

    def retrieve(self, stmt):
        return self.session.scalars(stmt)

    def rollback(self):
        """Roll back the current transaction."""
        self.session.rollback()

    @property
    def session(self):
        if not Indexer._session:
            Indexer._session = Indexer.db.session
        return Indexer._session

    def __repr__(self):
        return f"<Indexer path='{Indexer.path}'>"


index = Indexer(
    path=os.environ.get("INDEX_PATH", "~/index.sqlite"),
    read_only=bool(os.environ.get("INDEX_READONLY", False)),
)
