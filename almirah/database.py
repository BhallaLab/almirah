"""Database functionality for data write and access."""

import logging
import requests
import numpy as np
import pandas as pd

from sqlalchemy import URL
from sqlalchemy import Table
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import UniqueConstraint
from sqlalchemy import ForeignKeyConstraint

from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from .core import uniquify
from .core import DBManager
from .indexer import index
from .dataset import Component

from .utils.df import common_rows
from .utils.df import convert_column_type
from .utils.df import python_to_pandas_type

from .utils.logging import log_df
from .utils.logging import log_col

from .utils.sqlalchemy import get_sql_type


@uniquify(index)
class Database(Component):
    """Generic database representation."""

    __tablename__ = "databases"
    __identifier_attrs__ = {"name", "host", "backend"}

    id: Mapped[int] = mapped_column(ForeignKey("components.id"), primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    host: Mapped[str] = mapped_column(nullable=False)
    backend: Mapped[str] = mapped_column(nullable=True)

    __table_args__ = (UniqueConstraint("name", "host", "backend"),)
    __mapper_args__ = {"polymorphic_identity": "database"}

    def __init__(self, *, name, host, backend):
        self.name = name
        self.host = host
        self.backend = backend

    @property
    def connection(self):
        if self.backend in ["request", "gsheet"]:
            raise TypeError("Connection only permissible in connection mode")

        if not getattr(self, "db", None):
            raise TypeError(f"Connection to {self} not established")
        return self.db.connection

    @property
    def worksheet(self):
        if self.backend != "gsheet":
            raise TypeError("Worksheet only permissible in google sheets mode")

        if not getattr(self, "client"):
            raise TypeError(f"Connection to {self} not established")

    @property
    def meta(self):
        if self.backend in ["request", "gsheet"]:
            raise TypeError("Metadata only permissible in connection mode")

        if not getattr(self, "db"):
            raise ValueError(f"Connection to {self} not established")
        return self.db.metadata

    @property
    def token(self):
        if self.backend != "request":
            raise TypeError("Token only permissible in request mode")

        if not getattr(self, "_token", None):
            raise TypeError(f"Connection to {self} not established")

        return self._token

    def build_column(self, name, dtype, **kwargs):
        """Build SQLalchemy Column object given column description."""
        primary = kwargs.get("primary", False)
        fk = [ForeignKey(f)] if (f := kwargs.get("refs")) else []
        return Column(name, get_sql_type(dtype), *fk, primary_key=primary)

    def build_constraint(self, cols, links):
        """Build SQLalchmy constraint objects given links."""
        return ForeignKeyConstraint(cols, links)

    def create_table(self, table, cols, refs=[]):
        """
        Create or extend table within database given the description.

        Parameters
        ----------
        table_name : str
            Name of the table to create or extend.
        columns : list of dict
            List of columns specifications to add to the table.
        constraints : list of dict, optional
            List of table constraints.
        """
        cls = [self.build_column(**c) for c in cols]
        cns = [self.build_constraint(**r) for r in refs]
        table = Table(table, self.meta, *cls, *cns, extend_existing=True)
        table.create(bind=self.connection, checkfirst=True)

    def connect(self, username=None, password=None, keyfile=None):
        """
        Establish a connection to the database.

        Parameters
        ----------
        username : str
            The database username.
        password : str
            The database password.
        keyfile : str
            Path to the service account keyfile. Required if backend is gsheet.

        Raises
        ------
        SQLAlchemyError
            If the connection cannot be established at database.
        ValueError
            If the connection cannot be established at URL endpoint.
        """

        if self.backend == "request":
            data = {"username": username, "password": password}
            response = requests.post(f"{self.host}authenticate/", data=data).json()

            if "error" in response:
                raise ValueError(response["error"])

            self._token = response["token"]

        elif self.backend == "gsheet":
            import gspread

            self._client = gspread.service_account(keyfile)
            self.spreadsheet = self._client.open_by_url(self.host)

        else:
            url = URL.create(
                self.backend,
                username=username,
                password=password,
                host=self.host,
                database=self.name,
            )

            self.db = DBManager(url)

    def get_primary(self, table):
        """Return priamry keys for table."""

        return [c.name for c in self.meta.tables[table].primary_key]

    def get_records(self, table, cols=None):
        """Retrieve records from table in database as a DataFrame.

        Parameters
        ----------
        table : str
            Table in database from which to retrieve records.
        cols : list of str
            Column names to select from table.
        """
        if self.backend == "request":
            data = {"table": table, "cols": cols}
            header = {"Authorization": f"Bearer {self.token}"}
            response = requests.post(self.host, data=data, headers=header)
            records = pd.DataFrame(response.json())

        elif self.backend == "gsheet":
            data = self.spreadsheet.worksheet(table).get_all_values()
            headers = data.pop(0)
            records = pd.DataFrame(data, columns=headers)

            if cols:
                records = records[cols]

        else:
            dtype = {}
            for column in self.meta.tables[table].columns:
                if cols and column not in cols:
                    continue

                generic_type = column.type.as_generic()
                dtype[column.name] = python_to_pandas_type(generic_type.python_type)

            records = pd.read_sql_table(table, self.connection, columns=cols)
            records = records.astype(dtype)

        return records

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
            on Insertion method section of :ref:`pandas:io.sql.method`.
        kwargs : key, value mappings
            Other keyword arguments are passed down to
            :doc:`pandas:reference/api/pandas.DataFrame.to_sql`.

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
              operation and are detailed on :ref:`sqlalchemy:error_e3q8`.

        """

        if drop_na or threshold:
            logging.info("Dropping records with missing information")
            df = df.dropna(subset=drop_na, thresh=threshold)

        if check_dups:
            df = df[self.resolve_dups(df, table, resolve_dups)]

        if check_fks:
            df = df[self.resolve_fks(df, table, resolve_fks)]

        if insert_ignore:
            mask = common_rows(df, self.get_records(table).astype(df.dtypes))
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
        Resolve duplicate primary keys.

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
        """Resolve missing foreign keys.

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
            p_df = self.get_records(fkc.referred_table.name, p_cols)
            p_mask = common_rows(df, p_df, fkc.column_keys, p_cols)

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

    def report(self):
        """Generate report for database."""
        print(f"{self}:")

        for table in self.meta.tables:
            rows = len(self.get_records(table))
            print("{:<60} : {:>60} records".format(table, rows))

    def query(self, returns=None, **filters):
        """Return table records that fit filter criteria."""
        table = filters.pop("table", None)
        if not table:
            return None

        df = self.get_records(table, returns)

        if filters:
            df = df[np.logical_and.reduce([df[k] == v for k, v in filters.items()])]

        return df

    def __repr__(self):
        return f"<Database url: '{self.backend}:{self.name}@{self.host}'>"


def check_for_key(key, mapping):
    """Return columns in table mapping which contain the key provided."""

    return [c["name"] for c in mapping["cols"] if key in c.keys()]


def migrate(
    src,
    dst,
    mapping,
    dry_run=False,
    na_vals=[],
    dtype_kws=None,
    **kwargs,
):
    """
    Transform and migrate records from one database to another.

    Parameters
    ----------
    src: str
        Connection established source Database instance from which data is to
        be transferred.
    dst: str
        Connection established destination Database instance to which data is
        to be transferred.
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
        :func:`almirah.utils.df.convert_column_type` kwargs.
    kwargs : key, value mappings
        Other keyword arguments are passed down to
        `almirah.Database.to_table`.
    """
    na = ["", "None", "NONE", "NA", "N/A", "<NA>", "Not applicable"] + na_vals

    for m in mapping:
        logging.info(f"Transferring table {m['maps']} -> {m['table']}")

        # Extract source records
        records = src.get_records(m["maps"]).replace(na, pd.NA)

        # Transform and validate
        records = transform(records, dtype_kws, m)
        mask = validate(records, m)

        # Reshape data records
        df = reshape(records[mask], m.get("reshape", dict()))

        if dry_run:
            continue

        # Load records into target
        dst.create_table(m["table"], m["cols"] + m.get("attach", []), m.get("refs", []))
        dst.to_table(df, m["table"], threshold=m.get("threshold"), **kwargs)


def reshape(records, steps):
    """Reshape records into appropriate shape."""

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


def replace_value(value, column, mapping, file):
    """Return unique replacement for given value based on mapping in file."""

    # Load file into dataframe
    df = pd.read_csv(file, dtype=str)

    # Find value to replace
    result = df.query("`%s` == @value" % column)

    if len(result) == 0:
        logging.error(f"Value '{value}' not found in column '{column}' of '{file}'.")
        return

    if len(result) > 1:
        logging.error(f"Non-unique mappings for value '{value}' in {file}")
        return

    return result.at[0, mapping]


def replace_column(series, value, to, file, strict=True):
    """Replace values in series based on mapping in file."""

    # Load file into dataframe
    df = pd.read_csv(file, dtype=str)
    mapping = pd.Series(df[to].values, index=df[value].values)
    logging.info(f"Replacing values in '{value}' with '{to}' from {file}")

    # Stop if non-unique mappings
    if df.duplicated([value]).any():
        raise ValueError(f"Non-unique mappings found in file {file}")

    replaced = series.map(mapping)

    # Retain original value if replacement not strict
    if not strict:
        replaced.fillna(series, inplace=True)

    return replaced


def transform(records, dtype_kws, mapping):
    """Transform table into appropriate format."""

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


def transform_column(series, dtype_kws=dict(), **kwargs):
    """Transform column to appropriate datatype."""

    hide = kwargs.get("hide", False)
    s, error = series.copy(deep=True), series.isna()

    if pat := kwargs.get("extract"):
        s = s.astype(str).str.extract(pat, expand=False)
        logging.info(f"Extracting and replacing based on pattern {pat}")

    if rep := kwargs.get("replace"):
        if "file" in rep:
            s = replace_column(s, **rep)
            logging.info("Replacing values with mapping in external file")
        else:
            s = s.replace({k["value"]: k["to"] for k in rep})
            logging.info("Replacing values with given in config")

    if ca := kwargs.get("case"):
        s = s.str.upper() if ca == "upper" else s.str.lower()
        logging.info(f"Changing case to {ca}")

    s = convert_column_type(s, kwargs["dtype"], **dtype_kws)
    error = series.notna() & s.isna()
    log_col(series[error], f"Error transforming values to {kwargs['dtype']}", hide=hide)

    return s, error


def validate(records, mapping):
    """Validate table and return mask where True means valid."""

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
