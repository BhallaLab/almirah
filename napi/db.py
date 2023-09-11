"""Database functionality for data access."""

import os
import pandas as pd

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

    @property
    def connection(self):
        return self.engine.connect()


    def get_table(self, table, cols=None):
        """
        Retrieve table records in db as a DataFrame.

        Parameters
        ----------
        table : str
            Table in database from which to retrieve records.

        cols : list of str
            Column names to select from table.
        """
        return pd.read_sql_table(table, self.connection, columns=cols)

def get_db(db_path):
    """Returns SQLalchemy engine for provided URL."""
    if not db_path:
        db_path = "sqlite:///{}".format(
            os.path.join(os.path.expanduser("~"), "index.sqlite")
        )
    return create_engine(db_path)

