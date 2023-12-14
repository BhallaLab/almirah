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

- a :class:`~almirah.Specification` object that takes in the
  :doc:`writing-configs/specification` config as an argument to
  describe the details of the specification to be abided by. If no
  config is provided, the BIDS specification is used by default.

- an :doc:`writing-configs/rules` config that lays down the rules that
  will be followed for organization.

.. code-block:: python
		
		spec = almirah.Specification("/path to details")
		spec.organize("/path to rules")

.. note::

   For modalities such as Eye tracking, and Genomics where the
   BIDS-specification is still in the proposal stage or is only
   present as a descriptor, a custom BIDS-like specification that
   mimics the general pattern of the specification is used.

Indexing
--------

The indexing operation crawls through the organized dataset and stores
files and directories that have a matching path in the specification
in a database. This enables easy querying and filtering.

At an abstract level, each dataset can be thought of as a
:class:`~almirah.Layout` of files. Each :class:`~almirah.File` is associated
with a bunch of tags. Each :class:`~almirah.Tag` is a *name:value* pair
that is derived from the filename and metadata files associated to a
file. To create an instance of :class:`~almirah.Layout`, pass the root
directory path of the dataset as an argument to
:meth:`~almirah.Layout.create`:

.. code-block:: python

		lay = almirah.Layout.create("/path to dataset")

Unless otherwise specified by passing a :class:`~almirah.Specification`
instance via ``spec``, almirah will use the BIDS specification.

almirah automatically retrieves a previous index and skips indexing if
the layout is found, to force reindexing set ``reindex = True``.

Setting ``valid_only = False`` does not limit the files indexed to
only those that having matching paths in the specification
associated. This can act as a quick way to index the whole directory
or a dirty trick when you do not have time to redefine the
specification to accomodate a new path.

It is also possible to have a collection of layouts as a
:class`~almirah.Dataset`:

.. code-block:: python

		ds = almirah.Dataset.create(["/path to datasets"])

By this, parts of a dataset located in diverse paths can be virtually
collected into one while querying.

Filter and Query
----------------

To retrieve a subset of files that match certain tags, provide the
criterions as keyword arguments to :meth:`~almirah.Layout.get_files`
and almirah will return the :class:`~almirah.File` objects of passing files:

.. code-block:: python

		lay.get_files(subject = "A3456", extension = "png")

Converting file formats
-----------------------

Sometimes you want to convert the file format of a file. For example,
from DICOM to NIfTI, or from EDF (Eyelink Data Format) to ASCII. These
are possible by provided the files to be converted, the output format
desired, and the output directory as arguments to
:meth:`~almirah.data.convert`:

.. code-block:: python

		files = lay.get_files(extension = "dcm")
		lay.data.convert(files, "NIfTI", "/path to output dir")

Currently, the following conversions are supported:

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

almirah can connect to databases `supported by SQLAlchemy
<https://docs.sqlalchemy.org/en/20/core/engines.html#supported-databases>`_
with :class:`~almirah.DBManager` based on a `Database URL
<https://docs.sqlalchemy.org/en/20/core/engines.html#database-urls>`_:

.. code-block:: python

		import almirah

		# Create connection with database
		db = almirah.DBManager("database URL")

To create a table in the database, the table schema is described by
the :doc:`writing-configs/mapping` config and passed to
:meth:`~almirah.DBManager.create_table`:

.. code-block:: python

		db.create_table("/path to mapping")

To insert records into a table in the database, a
:class:`pandas.DataFrame` object whose columns match the table columns
is provided as an argument to :meth:`~almirah.DBManager.to_table` along
with the table name:

.. code-block:: python

		db.to_table(df, "table name")

.. important::

   If no table of the name is present, a table is created
   automatically. This might not be desirable if you would like to
   define relationships between tables as the created table is vanilla
   and lacks these.

:meth:`~almirah.DBManager.get_table` can retrieve records from a table in
the database given the table name. A subset of table columns can be
provided via ``cols``, if not all columns are retrieved.

.. code-block:: python

		db.get_table("table name")

Analyzing
---------

It should be possible to interface almirah with any tooklit available in
python. We recommend the below libaries as we have found them to play
well with almirah for neuroimaging and genomics datasets:

.. list-table::
   :header-rows: 1

   * - Datatype
     - Recommended libraries
   * - Magnetic resonance imaging
     - `nibabel <https://nipy.org/nibabel/>`_
   * - Electroencephalography
     - `mne <https://mne.tools/stable/index.html>`_
   * - Eye tracking
     - `mne <https://mne.tools/stable/index.html>`_
   * - Functional near-infrared spectroscopy
     - `mne-nirs <https://mne.tools/mne-nirs/stable/index.html>`_
   * - Genomics
     - `pysam <https://pysam.readthedocs.io/en/latest/index.html>`_,
       `scikit-allel <https://scikit-allel.readthedocs.io/en/latest/>`_

Typically, it might be desirable to extract features from each file
and represent them as a :class:`~pandas.DataFrame`:

.. code-block:: python

		# Query and retrieve files
		files = lay.get_files(datatype="eeg", extension="edf")

		import mne              # For Electroencephalography data
		import pandas           # To store the features

		# Create a function to extract and return feature
		def extract_feature(file):
		    raw = mne.io.read_raw_edf(file.path)
		    feature = raw.get_data.mean()
		    return feature
		    
		# Extract for all files
		feature_df = pandas.concat(map(extract_feature, files))

Reporting
---------

High-level summaries of a dataset can be reported by passing a
:class:`~almirah.Layout` or :class:`~almirah.Dataset` instance to
:class:`~almirah.Report`.

.. code-block:: python

		almirah.Report(lay)

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
		
.. rubric:: The ADBS Dataset
   
If you would like to use almirah to access the ADBS dataset, visit
:doc:`adbs/index` documentation.

