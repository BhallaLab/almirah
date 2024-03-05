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

from .utils import get_dtype, log_df, log_col

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

    def create_table(self, table, cols, refs=[]):
        """Create or extend table in db given the description."""
        cls = [self.build_column(**c) for c in cols]
        cns = [self.build_constraint(**r) for r in refs]
        table = Table(table, self.meta, *cls, *cns, extend_existing=True)
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

        dtype, length = get_dtype(dtype, default_length)
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
        check_dups=True,
        resolve_dups=False,
        check_fks=True,
        resolve_fks=False,
        insert_ignore=False,
        drop_na=None,
        threshold=None,
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

        check_dups : bool, default True
            Check for duplicates in records.

        resolve_dups : [False, 'first', 'last'], default False
            Resolution method for duplicates if found.

        check_fks : bool, default False
            Check if foreign keys present in parent.

        resolve_fks : bool, default False
            Attempt to resolve missing foreign keys by inserting to parent.

        insert_ignore : bool, default Flase
            Ignore insertion of records already present in table.

        drop_na : list of df column names, default None
            If provided, records with na in all given columns are dropped.

        threshold : int, None
            If non-NA values < threshold, then record dropped.

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

        if drop_na or threshold:
            logging.info("Dropping records with missing information")
            df = df.dropna(subset=drop_na, thresh=threshold)

        if check_dups:
            df = df[self.resolve_dups(df, table, resolve_dups)]

        if check_fks:
            df = df[self.resolve_fks(df, table, resolve_fks)]

        if insert_ignore:
            mask = common_records(df, self.get_table(table).astype(df.dtypes))
            logging.info(f"Ignoring insert of {mask.sum()} common records")
            df = df[~mask]

        logging.info(f"Inserting {len(df.index)} records")

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
        log_df(df[dups], "Found duplicate records")
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

            log_df(df[~p_mask], "Missing parent records")

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

    return (
        pd.merge(
            child.reset_index(),
            parent,
            how="left",
            left_on=child_on,
            right_on=parent_on,
            indicator="exists",
        )
        .replace({"both": True, "left_only": False, "right_only": False})
        .set_index("index")["exists"]
        .astype("bool")
    )


def check_for_key(key, mapping):
    """Return columns in table mapping which contain the key provided."""

    return [c["name"] for c in mapping["cols"] if key in c.keys()]


def migrate(
    src,
    target,
    mapping,
    dry_run=False,
    na_vals=[],
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

    na_vals: list, optional
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

    na = ["", "None", "NONE", "NA", "N/A", "<NA>", "Not applicable"] + na_vals

    for m in mapping:
        logging.info(f"Transferring table {m['maps']} -> {m['table']}")

        # Extract source records
        records = s.get_table(m["maps"]).replace(na, pd.NA)

        # Transform and validate
        records = transform(records, dtype_kws, m)
        mask = validate(records, m)

        # Reshape data records
        df = reshape(records[mask], m.get("reshape", dict()))

        if dry_run:
            continue

        # Load records into target
        t.create_table(m["table"], m["cols"] + m.get("attach", []), m.get("refs", []))
        t.to_table(df, m["table"], threshold=m.get("threshold"), **kwargs)


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

    dtype, _ = get_dtype(dtype)

    if dtype == str:
        series = series.astype(dtype)

    elif dtype == "datetime":
        series = pd.to_datetime(series, errors="coerce", **kwargs)

    elif dtype in {"float", "integer"}:
        series = pd.to_numeric(series, errors="coerce", downcast=dtype)

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


def reshape(records, steps):
    """Reshape table records into appropriate shape."""

    for procedure in steps:
        [(p, k)] = procedure.items()

        if p == "add":
            records[k["name"]] = k["value"]

        if p == "split":
            records[k["rename"]] = records[k["name"]].str.split(k["pat"], expand=True)

        if p == "melt":
            records = records.melt(**k)

        if p == "pivot":
            records = records.pivot_table(**k).reset_index()

    return records


def transform(records, dtype_kws, mapping):
    """Transform table records into appropriate format."""

    df = pd.DataFrame(index=records.index)
    to_hide = check_for_key("hide", mapping)
    error = pd.Series(False, index=records.index)

    for col in mapping["cols"] + mapping.get("detach", []):
        name, maps = col["name"], col["maps"]
        logging.debug(f"Transforming column {name}")
        df[name], col_error = transform_column(records[maps], dtype_kws, **col)
        error |= col_error

    log_df(records[error], "Error transforming records", hide=to_hide)
    return df[~error]


def replace_value(value, field, using, file):
    # Get mapping
    mapping = pd.read_csv(file, dtype=str)

    # Find value to replace
    result = mapping.query("`%s` == @value" % field)

    if len(result) == 0:
        logging.error(f"Value '{value}' not found in field '{field}' of file '{file}'.")
        return

    if len(result) > 1:
        logging.error(f"Non-unique mappings for value '{value}' in file {file}")
        return

    return result.at[0, using]


def replace_column(series, field, using, file, strict=True):
    # Load mapping from file
    mapping = pd.read_csv(file, dtype=str)
    logging.info(f"Replacing values in '{field}' with '{using}' from {file}")

    # Stop if non-unique mappings
    if mapping.duplicated([field]).any():
        raise ValueError(f"Non-unique mappings found in file {file}")

    mapping = pd.Series(mapping[using], index=mapping[field])
    replaced = series.map(mapping)

    # Retain original value if replacement not strict
    if not strict:
        replaced.fillna(series, inplace=True)

    return replaced


def transform_column(series, dtype_kws=dict(), **kwargs):
    """Transform column to appropriate datatype."""

    hide = kwargs.get("hide", False)
    s, error = series.copy(deep=True), series.isna()

    if pat := kwargs.get("extract"):
        s = s.astype(str).str.extract(pat, expand=False)
        logging.info(f"Extracting and replacing based on pattern {pat}")

    if rep := kwargs.get("replace"):
        if "field" in rep:
            replace_column(s, **rep)
            logging.info("Replacing values with mapping in external file")
        else:
            s = s.replace({k["value"]: k["with"] for k in rep})
            logging.info("Replacing values with given in config")

    if ca := kwargs.get("case"):
        s = s.str.upper() if ca == "upper" else s.str.lower()
        logging.info(f"Changing case to {ca}")

    s = set_dtype(s, kwargs["dtype"], **dtype_kws)
    error = series.notna() & s.isna()
    log_col(series[error], f"Error transforming values to {kwargs['dtype']}", hide=hide)

    return s, error


def validate(records, mapping):
    """Validate table records and return mask where True means valid."""

    to_hide = check_for_key("hide", mapping)
    mask = pd.Series(True, index=records.index)

    for col in mapping["cols"] + mapping.get("detach", []):
        logging.debug(f"Validating column {col['name']}")
        mask &= validate_column(records[col["name"]], **col)

    log_df(records[~mask], "Found invalid records", hide=to_hide)
    return mask


def validate_column(series, **kwargs):
    """Validate column and return mask where True means valid."""

    hide = kwargs.get("hide", False)
    mask = pd.Series(True, index=series.index)

    if kwargs.get("primary"):
        mask &= (m := series.notna())
        log_col(series[~m], "Primary column values cannot be NA", hide=hide)

    if pat := kwargs.get("like"):
        mask &= (m := series.astype(str).str.fullmatch(pat) | series.isna())
        log_col(series[~m], f"Values do not match pattern {pat}", hide=hide)

    if bounds := kwargs.get("between"):
        mask &= (m := series.between(*bounds) | series.isna())
        log_col(series[~m], f"Values not between bounds {bounds}", hide=hide)

    if members := kwargs.get("in"):
        mask &= (m := series.isin(members) | series.isna())
        log_col(series[~m], f"Values not in {members}", hide=hide)

    return mask
