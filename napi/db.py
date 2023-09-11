"""Database and DataFrame functionality for data access and manipulation."""

import os
import logging
import pandas as pd

from sqlalchemy import Table
from sqlalchemy import Column
from sqlalchemy import MetaData
from sqlalchemy import ForeignKey
from sqlalchemy import ForeignKeyConstraint


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

    def build_column(self, name, dtype, **kwargs):
        """Build SQLalchemy Column object given column description."""
        primary = kwargs.get("primary", False)
        fk = [ForeignKey(f)] if (f := kwargs.get("refs")) else []
        return Column(name, self.get_type(dtype), *fk, primary_key=primary)

    def build_constraint(self, cols, links):
        """Build SQLalchmy constraint objects given links."""
        return ForeignKeyConstraint(cols, links)

    def create_table(self, description):
        """Create or extend table in db given the description."""
        cols = [self.build_column(**c) for c in description.get("cols")]
        cns = [self.build_constraint(**r) for r in description.get("refs", [])]
        table = Table(
            description["table"], self.meta, *cols, *cns, extend_existing=True
        )
        table.create(bind=self.engine, checkfirst=True)


    def get_type(self, dtype, default_length=250):
        """
        Return supported SQLalchemy type equivalent of provided dtype string.

        Parameters
        ----------
        dtype: str
            Supported dtype string representation.

        default_length: int, optional
            Default length of string. Used if required by db backend.
        """

        SQL_TYPE_EQUIVALENT = {
            "boolean": Boolean,
            "datetime": DateTime,
            "float": Float,
            "integer": Integer,
            "str": String,
        }

        dtype, length = utils.get_dtype(dtype, default_length)
        stype = SQL_TYPE_EQUIVALENT[dtype]

        return stype(length) if length else stype()

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

