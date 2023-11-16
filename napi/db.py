"""Database and DataFrame functionality for data access and manipulation."""

import os
import logging
import pandas as pd

from sqlalchemy import Table
from sqlalchemy import Column
from sqlalchemy import MetaData
from sqlalchemy import ForeignKey
from sqlalchemy import ForeignKeyConstraint

from sqlalchemy.types import Boolean
from sqlalchemy.types import Float
from sqlalchemy.types import Integer
from sqlalchemy.types import String
from sqlalchemy.types import DateTime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from . import utils

__all__ = ["DBManager", "common_records", "migrate", "transform", "validate"]


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

    def get_primary(self, table):
        """Returns priamry keys for table."""
        return [c.name for c in self.meta.tables[table].primary_key]

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

    def to_table(
        self,
        df,
        table,
        drop_na=None,
        check_dups=True,
        resolve_dups=False,
        check_fks=True,
        resolve_fks=False,
        if_exists="append",
        index=False,
        insert_method=None,
        **kwargs,
    ):
        """Write records in DataFrame to a table.

        Parameters
        ----------
        df : pandas.DataFrame
            DataFrame containing records.

        table : str
            Table in database into which the records will be inserted.

        drop_na : list of df column names, default None
            If provided, records with na in all given columns is dropped.

        check_dups : bool, default True
            Check for duplicates in records.

        resolve_dups : [False, 'first', 'last'], default False
            Resolution method for duplicates if found.

        check_fks : bool, default False
            Check if foreign keys present in parent.

        resolve_fks : bool, default False
            Attempt to resolve missing foreign keys by inserting to parent.

        if_exists : ['append', 'replace', 'fail'], default 'append'
            Insert behavior in case table exists.

            - 'append' : Insert new values to the existing table.
            - 'replace' : Drop the table before inserting new values.
            - 'fail' : Raise a ValueError if table exists.

        index : bool, default False
            Write DataFrame index as a column. Uses index_label as the
            column name in the table.

        insert_method : {None, 'multi', callable}, optional
            Controls the SQL insertion clause used.

            - None : Uses standard SQL INSERT clause (one per row).
            - ‘multi’: Pass multiple values in a single INSERT clause.
            - callable with signature ``(pd_table, conn, keys, data_iter)``.

            Details and a sample callable implementation can be found
            in the pandas section `insert method
            <https://pandas.pydata.org/docs/user_guide/io.html#io-sql-method>`_.

        kwargs : key, value mappings Other keyword arguments are
            passed down to `pandas.DataFrame.to_sql()
            <https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.to_sql.html>`_

        Returns
        -------
        rows : None or int
            Number of rows affected by to_sql. None is returned if the
            callable passed into `insert_method` does not return an
            integer number of rows.

        Raises
        ------
        ValueError
            - When values provided are not sufficient for insert operation.
            - When the table already exists and `if_exists` is 'fail'.

        OperationalError
            - Most likely there are duplicates records in the
              DataFrame. Other reasons are related to the database
              operation and are detailed in sqlalchemy section
              `OperationalError
              <https://docs.sqlalchemy.org/en/20/errors.html#operationalerror>`_.

        """

        if drop_na:
            df = df.dropna(subset=drop_na)

        if check_dups:
            df = df[self.resolve_dups(df, table, resolve_dups)]

        if check_fks:
            df = df[self.resolve_fks(df, table, resolve_fks)]

        df.to_sql(
            table,
            self.connection,
            if_exists=if_exists,
            index=index,
            method=insert_method,
            **kwargs,
        )

    def resolve_dups(self, df, table, resolve=False):
        """
        Resolve duplicate primary keys in DataFrame.

        Parameters
        ----------
        df : pandas.DataFrame
            DataFrame to check for duplicate records.
        table : str
            Table the records will be inserted into.
        resolve : [False, 'first', 'last'], default False
            Determines resolution method.

            * False : Mark all duplicates as False.
            * 'first' : Mark duplicates as False except for first occurence.
            * 'last' : Mark duplicates as False except for last occurence.

        Returns
        -------
        mask : pandas.Series
            Series of booleans showing whether each record in the
            Dataframe is not a duplicate.

        Raises
        ------
        ValueError
            When primary key duplicates are found and `resolve` is True.

        """
        dups = df.duplicated(self.get_primary(table), resolve)
        utils.log_df(df[dups], "Found duplicate records: \n {df}")
        return ~dups

    def resolve_fks(self, df, table, resolve=False):
        """
        Parameters
        ----------
        df : pandas.DataFrame
            Non-duplicated records to be checked.
        table : str
            Table the records will be inserted into.
        resolve : bool, optional
            If True, attempt to resolve missing parent records by inserting.

        Returns
        -------
        mask : pandas.Series
             Series of booleans showing whether each record in the
             DataFrame has all required parent records.

        Warnings
        --------
        Resolution fails with a ValueError when a foreign key
        constraint on a table does not reference all the columns that
        provide the required values to insert records into the parent
        table.

        """
        mask = pd.Series(True, index=df.index)

        for fkc in self.meta.tables[table].foreign_key_constraints:
            p_cols = [fk.column.name for fk in fkc.elements]
            p_df = self.get_table(fkc.referred_table.name, p_cols)
            p_mask = common_records(df, p_df, fkc.column_keys, p_cols)

            utils.log_df(df[~p_mask], "Missing parent records: \n {df}")

            if not p_mask.all() and resolve:
                logging.info("Resolving missing records by insert to parent")
                self.to_table(
                    df[~p_mask][fkc.column_keys].set_axis(p_cols, axis=1),
                    fkc.referred_table.name,
                    check_dups=True,
                    resolve_dups="first",
                    check_fks=True,
                    resolve_fks=True,
                )
                p_mask[~p_mask] = True

            mask &= p_mask
        return mask

    def __repr__(self):
        return f"<DBManager '{self.engine.url}'>"


def get_db(db_path):
    """Returns SQLalchemy engine for provided URL."""
    if not db_path:
        db_path = "sqlite:///{}".format(
            os.path.join(os.path.expanduser("~"), "index.sqlite")
        )
    return create_engine(db_path)


def common_records(child, parent, child_on=None, parent_on=None):
    """Check whether each record in a DataFrame is contained in another."""
    mask = (
        pd.merge(
            child.reset_index(),
            parent,
            how="left",
            left_on=child_on,
            right_on=parent_on,
            indicator="exists",
        )
        .replace({"both": True, "left_only": False, "right_only": False})
        .set_index("index")
    )
    return mask["exists"].astype("bool")


def migrate(
    src,
    target,
    mapping,
    dry_run=False,
    na_values=None,
    dtype_kws=None,
    **kwargs,
):
    """
    Transforms and migrates records from one db to another.

    Parameters
    ----------
    src: str
        SQLAlchemy database URL of database from which data is
        transferred.

    target: str
        SQLAlchemy database URL of database to which data is
        transferred.

    mapping: dict
        Dictionary providing information on column mappings, type,
        transformations, and validation checks.

    dry_run: bool
        If dry run, no records are inserted into target and tables are
        not created, but errors and invalid records are logged.

    na_values: list, optional
        List of values to be considered as record not available. By
        default, the values '', 'None', 'NONE', 'NA', and 'Not Applicable'
        are considered.

    dtype_kws : dict, optional
        Key, value pairs that will be passed to
        :meth:`napi.db.set_dtype()`.

    kwargs : key, value mappings
        Other keyword arguments are passed down to
        :meth:`napi.db.to_table`.
    """

    s = DBManager(src)
    t = DBManager(target)

    if not na_values:
        na_values = ["", "None", "NONE", "NA", "Not applicable"]

    for m in mapping:
        logging.info(f"Transferring table {m['maps']} -> {m['table']}")

        # Extract source records
        src_df = s.get_table(m["maps"])
        src_df = src_df.replace(na_values, pd.NA)
        tar_df = pd.DataFrame(index=src_df.index)

        # Transform and validate
        tr_error = pd.Series(False, index=src_df.index)
        mask = pd.Series(True, index=src_df.index)

        for col in m["cols"]:
            name, maps = col["name"], col["maps"]
            logging.debug(f"Transforming and validating column {name}")
            tar_df[name], err = transform(src_df[maps], dtype_kws, **col)
            mask &= validate(tar_df[name], **col)
            tr_error |= err

        utils.log_df(src_df[tr_error], "Unable to transform records: \n {df}")
        utils.log_df(src_df[~mask], "Found invalid records: \n {df}")

        if dry_run:
            continue

        # Load records into target
        t.create_table(m)
        t.to_table(tar_df[mask & ~tr_error], m["table"], **kwargs)


def set_dtype(series, dtype, **kwargs):
    """
    Set dtype of series.

    Parameters
    ----------
    series: pandas.Series
        Series for which the dtype has to set.

    dtype: str
        Supported dtype to which the series will be converted.

    kwargs: key, value mappings
        Other keyword arguments are passed down to `pandas.to_datetime()`_
        if the dtype is 'datetime'.
    """

    dtype, _ = utils.get_dtype(dtype)

    if dtype == "datetime":
        series = pd.to_datetime(series, errors="coerce", **kwargs)

    elif dtype in {"float", "integer"}:
        series = pd.to_numeric(series, errors="coerce", downcast=dtype)

    elif dtype == str:
        series = series.astype(dtype)

    elif dtype == "boolean":
        series = series.replace(
            {
                "1": True,
                "0": False,
                "True": True,
                "False": False,
                "Yes": True,
                "No": False,
            }
        )
        series = series.astype(dtype)

    return series.convert_dtypes()


def transform(series, dtype_kws=None, **kwargs):
    """Transform series and return with appropriate datatype."""

    s = series.copy(deep=True)

    if pat := kwargs.get("extract"):
        s = s.astype(str).str.extract(pat, expand=False)

    if rep := kwargs.get("replace"):
        s = s.replace({k["value"]: k["with"] for k in rep})

    if ca := kwargs.get("case"):
        s = s.str.upper() if ca == "upper" else s.str.lower()

    if not dtype_kws:
        dtype_kws = dict()

    s = set_dtype(s, kwargs["dtype"], **dtype_kws)

    error = series.notna() & s.isna()
    utils.log_df(series[error], "Bad transform: \n{df}", level=logging.DEBUG)

    return s, error


def validate(series, **kwargs):
    """Validate series and return mask."""

    mask = pd.Series(True, index=series.index)

    if kwargs.get("primary"):
        mask &= series.notna()

    if pat := kwargs.get("like"):
        mask &= series.astype(str).str.fullmatch(pat) | series.isna()

    if bounds := kwargs.get("between"):
        mask &= series.between(*bounds) | series.isna()

    if members := kwargs.get("in"):
        mask &= series.isin(members) | series.isna()

    utils.log_df(series[~mask], "Bad validation: \n{df}", level=logging.DEBUG)
    return mask
