"""Database functionality for data access."""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .data.layout import Base

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from . import utils


class DBManager:
    """Interface to connect with db and perform operations."""

    def __init__(self, db_path=None):
        self.engine = get_db(db_path)
        self.meta = self._init_metadata()
        self._sessionmaker = sessionmaker(self.engine)
        self._session = None

    def _init_metadata(self):
        meta = MetaData()
        meta.reflect(bind=self.engine)
        return meta

    @property
    def session(self):
        if self._session is None:
            self._session = self._sessionmaker()
        return self._session

def get_db(db_path):
    """Returns SQLalchemy engine for provided URL."""
    if not db_path:
        db_path = "sqlite:///{}".format(
            os.path.join(os.path.expanduser("~"), "index.sqlite")
        )
    return create_engine(db_path)

