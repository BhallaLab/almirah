Database mapping
================

.. currentmodule:: napi.db

It is convenient to store tabular records in a SQL database. There
might be usecases where it is necessary to migrate to another
schema. For this, the mapping between the columns in the previous
schema to the new schema is required along with any transformations to
be performed. napi supports database migration with help from a
user-written mapping config whose options are detailed in this
document. Each table is defined as a seperated document and are
separated by ``---``.

A minimal configuration to migrate a table with columns ``id`` and
``name`` looks like this:

.. code-block:: yaml

		table: source_table_name
		maps: target_table_name
		cols:
		  - name: id
		    dtype: integer
		    maps: id
		  - name: name
		    dtype: str
		    maps: name

The above mapping can be used for database migration with :meth:`~migrate`:

.. code-blocK:: python

		# First, import migrate from the db module
		from napi.db import migrate

		# Migrate from source to target according to mapping
		migrate(src, target, mapping)

Top-level keys
--------------

``table``
~~~~~~~~~

The table in target database to which records will be inserted.

If the table does not exist, it is created. 

``maps``
~~~~~~~~

The table in source database from which records will be selected.

``cols``
~~~~~~~~

All details regarding fixed column mappings sit inside the ``cols``
key. It consists of a sequence of entries that provide information on
the column, its datatype, validations to pass, and transformations if
any.

The column mapping is defined using:

``name``
    The column in target table that corresponds to the source column.

``dtype``
    The datatype of the column values.

    Can be ``bool``, ``datetime``, ``float``, ``integer``, or
    ``str``. Optionally ``str`` accepts a length parameter as
    ``str(length)`` that defines the maximum number of characters
    allowed.

    If the values received from source column is of a different type,
    then type casting is attempted which on failing default to ``Not
    Available`` or ``None``.

``maps``
    The column in the source table that this columns corresponds to.

``primary``
    Boolean value indicating whether the column is a primary key.

``refs``
    If the column refers to a column in a different table, its complete name.

    This is used to provide foreign key constraints. The complete name
    should be of the form ``{table name}.{column name}``.

Validations can be provided using:    

``like``
    Regex pattern defining how the value should look like from start to end.

``between``
    Bounds within which the value should lie.

    The bounds can be provided as comma-separated values enclosed in
    square brackets. For example, ``[0, 10]`` to indicate that the
    value should lie between ``0`` and ``10``.

``in``
    Sequence of valid values.

    The valid values can be comma-separated in square brackets. For
    example, ``[Yes, No]`` to indicated that the value should be
    either ``Yes`` or ``No``.

Values can be transformed and massaged to a different format using:

``extract``
    Regex pattern with a capturing group.

    The value captured is used in place of the complete value.

``case``
    Perform case tranformations to the value.

    Accepts ``lower`` or ``upper`` to convert all characters to
    lowercase and uppercase respectively.

``replace``
    Replace one value with another.

    Accepts a sequence of ``value``:``with`` key pairs where ``with``
    replaces ``value``.

``attach``
~~~~~~~~~~

Columns that will be attached due to reshaping sit inside the
``attach`` key. It supports all sub-keys supported by ``cols``.

It is redundant to provide map value for columns in ``attach`` as
their value are inferred from the records based on the reshape
procedure. If your column needs to map to a column in source table,
maybe ``cols`` or ``detach`` is more relevant.

``detach``
~~~~~~~~~~

Columns that will be removed in the processing of reshaping sit inside
the ``detach`` key. It supports all sub-keys supported by ``cols``.

Columns under ``detach`` are typically serve as columns that are
considered for melting into one.

``refs``
~~~~~~~~

If a set of columns make a composite foreign key constraint, they can
be provided as a sequence of columns and their respective foreign key
link.

``cols``
    Columns in the table that are part of the composite reference.

``links``
    The complete name of the column referred to in the same order as ``cols``.

Both ``cols`` and ``links`` can be provided as comma-separated values
enclosed in square brackets.

``reshape``
~~~~~~~~~~~

Provide step-wise instructions to massage the records from one
structure to another.

Reshaping instructions can be provided as a sequence of supported
procedures as keys with a sequence of their respective arguments under
them. The procedures are implemented using pandas methods and will
thus use the same argument names as the specific pandas method.

Reshaping procedures:

``add``
    Add new column ``name`` with given ``value``. Takes a ``name`` and
    ``value`` key sequence with their values.

``split``
    Split column ``name`` into multiple columns based on delimiter
    ``pat`` and rename the generated columns to ``rename``.

``melt``
    Massage a set of columns into a single column.

    Uses arguments similar to :meth:`~pandas.DataFrame.melt`.

``pivot``
    Pivot to wide-form by grouping rows with similar identifiers.

    Uses arguments similar to :meth:`~pandas.DataFrame.pivot_table`.
