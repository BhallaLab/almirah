"""Database functionality for data access."""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .data.layout import Base


def get_db(db_path):
    if not db_path:
        db_path = os.path.join(os.path.expanduser("~"), "db_index.sqlite")
    return f"sqlite:///{db_path}"


class SessionManager:
    """Represents a session with the db."""

    def __init__(self, db_path=None):
        db = get_db(db_path)
        engine = create_engine(db)
        Base.metadata.create_all(engine)
        self._sessionmaker = sessionmaker(engine)
        self._session = None

    @property
    def session(self):
        if self._session is None:
            self._session = self._sessionmaker()
        return self._session
