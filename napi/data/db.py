"""Database functionality for indexing and data access."""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import DeclarativeBase


def get_db(db_path):
    if not db_path:
        db_path = os.path.join(os.path.expanduser("~"), "db_index.sqlite")
    return f"sqlite:///{db_path}"


class Base(DeclarativeBase):
    pass


class SessionManager:
    """Represents a session with the db."""

    def __init__(self, db_path=None):
        db = get_db(db_path)
        engine = create_engine(db, echo=True)
        Base.metadata.create_all(engine)
        self._sessionmaker = sessionmaker(engine)
        self._session = None

    @property
    def session(self):
        if self._session is None:
            self._session = self._sessionmaker()
        return self._session
