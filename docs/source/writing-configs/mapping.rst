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

All details regarding column mappings sit inside the ``cols`` key. It
consists of a sequence of entries that provide information on the
column, its datatype, validations to pass, and transformations if any.

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

``transform``
    Perform string tranformations to the value.

    Currently, ``lowercase`` and ``uppercase`` to convert all cased
    characters to lowercase and uppercase respectively are supported.

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



    



