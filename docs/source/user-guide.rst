User Guide
==========

.. currentmodule:: almirah

Installing
----------

almirah can be installed with `pip <https://pip.pypa.io>`_

.. code-block:: bash

		$ python -m pip install almirah

Organizing the dataset
----------------------

The first step to using any dataset is getting it in shape to allow
manual exploration or automated retrieval of a subset. To get started,
import the almirah module:

.. code-block:: python

		import almirah

almirah relies on two components to organize a dataset:

- a :class:`~specification.Specification` object that takes in the
  contents of :doc:`writing-configs/specification` config as an
  argument to describe the details of the specification to be abided
  by.

- an :doc:`writing-configs/rules` config that lays down the rules that
  will be followed for organization.

.. code-block:: python
		
		spec = Specification.create_from_file("/path to details")
		spec.organize("/path to rules")

.. note::

   For modalities such as Eye tracking, and Genomics where the
   BIDS-specification is still in the proposal stage or is only
   present as a descriptor, a custom BIDS-like specification that
   mimics the general pattern of the specification is used in the
   config.

Indexing
--------

The indexing operation crawls through the organized dataset and stores
files and directories that have a matching path in the specification
in a database. This enables easy querying and filtering.

At an abstract level, each dataset can be thought of as a
:class:`~layout.Layout` of files. Each :class:`~layout.File` is
associated with a bunch of tags. Each :class:`~layout.Tag` is a
*name:value* pair that is derived from the filename and metadata files
associated to a file. To create an instance of
:class:`~layout.Layout`, pass the root directory path of the dataset
and the :class:`~specification.Specification` name to
:class:`~layout.Layout`:

.. code-block:: python

		lay = Layout(root="/path to dataset", specification_name="name")

almirah automatically retrieves a previous index if the layout is
found. If not, the :class:`~layout.Layout` can be indexed using
:meth:`~layout.Layout.index`. Index changes and additions are not
written unless commited using :meth:`~indexer.Indexer.commit`.

.. tip::

   Setting ``valid_only = False`` does not limit the files indexed to
   only those that having matching paths in the specification
   associated. This can act as a quick way to index the whole
   directory or a dirty trick when you do not have time to redefine
   the specification to accomodate a new path.

It is also possible to have a collection of layouts as a
:class`~dataset.Dataset`:

.. code-block:: python

		ds = Dataset(name="name")
		ds.add(layout_1, layout_2,..., layout_n)

By this, parts of a dataset located in diverse paths can be virtually
collected into one for querying.

.. tip::

   Objects can be retrieved once commited from the index, or if
   present in the current session by using `get()`. To retrieve the a
   :class:`~layout.Layout` of specification name *bids*, you can do
   ``Layout.get(specification_name='bids')``.

Filter and Query
----------------

To retrieve a subset of files that match certain tags, provide the
criterions as keyword arguments to :meth:`~layout.Layout.query` and
:class:`~layout.File` objects of passing files will be returned:

.. code-block:: python

		lay.query(subject = "A3456", extension = ".png")

.. tip::

   If you do not know the possible tags, :meth:`~layout.Tag.options`
   might be of help. ``option()`` is available for all objects in and
   can be used as a look-up.

Converting file formats
-----------------------

Sometimes you want to convert the file format of a file. For example,
from DICOM to NIfTI, or from EDF (Eyelink Data Format) to ASCII. These
are possible by provided the files to be converted, the output format
desired, and the output directory as arguments to
:meth:`~utils.convert.convert`:

.. code-block:: python

		files = lay.query(extension = ".dcm")
		lay.data.convert(files, "NIfTI", "/path to output dir")

nnCurrently, the following conversions are supported:

.. list-table::
   :header-rows: 1

   * - Input extensions
     - Output formats
     - Datatype  
   * - dcm
     - NIfTI
     - Magnetic resonance imaging
   * - bdf, cnt, data, edf, gdf, mat, mff, nxe, set, vhdr
     - BrainVision, EDF, FIF
     - Electroencephalography
   * - edf
     - ASCII
     - Eye tracking       
   * - nirx
     - SNIRF
     - Functional near-infrared spectroscopy  


Interfacing with a Database
---------------------------

almirah can connect to databases `supported by SQLAlchemy`_, `Google
sheets`_, and URL endpoints that support retrieval of database
contents with :class:`~database.Database`. During object creation,
``name``, ``host``, and ``backend`` have to be provided to
:class:`~database.Database`. Later, while querying a connection needs
to established using :meth:`~database.Database.connect` by providing
the credentials:

.. _Google Sheets: https://www.google.com/sheets/about/
.. _supported by SQLAlchemy: https://docs.sqlalchemy.org/en/20/core/engines.html#supported-databases

.. code-block:: python

		import almirah

		db = Database(name="db_name", host="db_host", backend="db_type")

		# Create connection with database
		db.connect("username", "password")		

Only reading is supported is databases that are Google sheets or URL
endpoints. Operations such as table creation, writing, metadata
manipulation are only available in SQLAlchemy-valid databases.

To create a table in the database, the table schema is described by
the :doc:`writing-configs/mapping` config and passed to
:meth:`~database.Database.create_table`:

.. code-block:: python

		db.create_table({"mapping":"dict"})

To insert records into a table in the database, a
:class:`pandas.DataFrame` object whose columns match the table columns
is provided as an argument to :meth:`~database.Database.to_table` along
with the table name:

.. code-block:: python

		db.to_table(df, "table name")

.. important::

   If no table of the name is present, a table is created
   automatically. This might not be desirable if you would like to
   define relationships between tables as the created table is vanilla
   and lacks these.

:meth:`~database.Database.get_records` can retrieve records from a
table in the database given the table name. A subset of table columns
can be provided via ``cols``, if not all columns are to be retrieved.

.. code-block:: python

		db.get_records("table_name")

Reporting
---------

High-level summaries of a dataset can be reported by using
:meth:`dataset.Database.report`.

.. code-block:: python

		obj.report()

The tags based on which the summary is to be generated can be provided
via the ``tags`` argument. `subject` is the used if no values are
provided.

Errors and Exceptions
---------------------

almirah wraps built-in python exceptions with appropriate messages, for
example:

.. code-block:: python

		raise ValueError(f"Unsupported transform value {transform}")
		
See :class:`Exception` for context.

Logging
-------

If you are using the standard library :mod:`logging` module, almirah will emit
several logs. In some cases, this can be undesireable. You can use the
standard logger interface to change the log level for almirah's logger:

.. code-block:: python

		logging.getLogger("almirah").setLevel(logging.WARNING)
		
.. rubric:: The CALM-Brain Resource
   
If you would like to use almirah to access the CALM-Brain resource,
visit the `CALM-Brain <https://girishmm.github.io/calm-brain/>`_
documentation.
