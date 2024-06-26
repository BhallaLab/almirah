Tutorial
========

.. currentmodule:: almirah

``almirah`` is a tool to organize, query, and summarize data. In this
tutorial we will use ``almirah`` on a dummy test dataset that
represents imaging data obtained from mice to illustrate some of its
usecases. In case you have not installed ``almirah`` yet, please go to
the :ref:`Installing` section and follow the instructions.

The dummy dataset that we will be using comes along with ``almirah``
and can be created at a convenient location using
:meth:`~utils.lib.create_tutorial_dataset`.

.. code-block:: python

	       from almirah.utils import create_tutorial_dataset

	       create_tutorial_dataset("path/to/store")

The dataset contents can be listed using the ``tree`` command.

.. code-block:: bash

		$ tree "path/to/store"

.. code-block:: output
		
		.
		├── 72
		│   ├── DAY01_G72_20180201.npy
		│   └── DAY02_G72_20180202.npy
		├── DAY01_G171_20180101.npy
		├── Day2_171_20180102.npy
		└── G433
		    ├── DAY_G433_20180301.npy
		    └── day02_G433_20180301.npy

		3 directories, 6 files

The dataset is not formatted and is difficult to navigate as can be
seen from content hierarchy. Let us attempt to change this.

Defining a Specification
--------------------------

The first step to all things ``almirah`` can do is defining the
:doc:`writing-configs/specification`. To come up with a
:class:`~specification.Specification` for this dataset, let us think
about how we would structure this dataset manually.

Deciding path patterns
~~~~~~~~~~~~~~~~~~~~~~

We would prefer to navigate in the following order from the dataset
root directory, ``mice`` -> ``day`` -> ``file``. This is intuitive and
leaves scope for expansion on new data generation. Based on this, the
path relative to the dataset root would look like `mice/day/file`. The
file name should contain the details of mice, day, and the type of
imaging to uniquely identify it from others just using filename. For
example, a nice file name would be `mice-G433_day-01_imaging-calcium.npy`.

The above decided path can be mentioned in the
:doc:`writing-configs/specification` under the ``path_patterns`` key
like:

.. code-block:: yaml

		path_patterns:
		  - "mice-{mice}/day-{day}/mice-{mice}_day-{day}_imaging-{imaging}{extension}"

Here, contents enclosed in ``{}`` represent that these are tag
values. A :class:`~layout.File` in ``almirah`` is associated with a
bunch of tags. It is possible to provide more details on tags
regarding valid values, the default value, and if the
:class:`~layout.Tag` is mandatory.

Building paths
~~~~~~~~~~~~~~

Now that we have the basic :doc:`writing-configs/specification`, we
can build valid paths by providing the required tags. The
:doc:`writing-configs/specification` can either be stored as a `YAML
<https://yaml.org/spec/1.2.2/>`_ file and the
:class:`~specification.Specification` created using
:meth:`~specification.Specification.create_from_file`, or the contents
can be passed directly as a dictionary via the details argument of
:class:`~specification.Specification`.

Tags are *key*:*value* pairs that convey an information regarding the file. For
our decided path, the tags we require for path building are ``mice``,
``day``, ``imaging``, and ``extension``.

.. code-block:: python

		from almirah import Specification

		# Create a Specification object
		spec = Specification.create_from_file("/path/to/config")

		# Check out paths built based on tags provided
		spec.build_path(mice='G433', day='01', imaging='calcium', extension='.npy')
		# mice-G433/day-01/mice-G433_day-01_imaging-calcium.npy

		spec.build_path(mice='G41', imaging='calcium', extension='.npy')
		# Returns None as no valid path be built using only these tags
		    
Extracting tags from path
~~~~~~~~~~~~~~~~~~~~~~~~~

Certain times, we might need to extract tags from a path. For example,
what is the ``mice`` tag or the ``day`` tag given the path? These can
be provided as a sequence of *name*:*regex pattern* pairs under the
``tags`` key like:

.. code-block:: yaml

		tags:
		  - name: mice
		    pattern: "[/\\\\]mice-([a-zA-Z0-9]+)"
		  - name: day
		    pattern: "[/\\\\]+day-([0-9]+)"
		  - name: imaging
		    pattern: "[_/\\\\]+imaging-([a-zA-Z]+)"
		  - name: extension
		    pattern: "[^./\\\\](\\.[^/\\\\]+)$"

The capturing group in the regex pattern extracts the tag value from
the path.

Putting all of these together, we have our
:doc:`writing-configs/specification`:

.. code-block:: yaml

		tags:
		  - name: mice
		    pattern: "[/\\\\]mice-([a-zA-Z0-9]+)"
		  - name: day
		    pattern: "[/\\\\]+day-([0-9]+)"
		  - name: imaging
		    pattern: "[_/\\\\]+imaging-([a-zA-Z]+)"
		  - name: extension
		    pattern: "[^./\\\\](\\.[^/\\\\]+)$"
		path_patterns:
		  - "mice-{mice}/day-{day}/mice-{mice}_day-{day}_imaging-{imaging}{extension}"

Organizing the dataset
----------------------

With the :class:`~specification.Specification` defined, it is now
possible to restructure a dataset given that we are able to retrieve
the tags required to build a valid path from each target file. If we
are able to build a valid relative path, then it just boils down to
just moving the file to that position with respect to the root
directory. Lets us do this for our dataset.

Required parameters to begin organizing a dataset are:

#. ``source``: The root directory of unorganized data.
#. ``destination``: The directory where organized data will be stored.
#. ``pattern``: All filenames matching this pattern are considered for
   organizing. For our dataset, this can be ``*.npy``.

Establishing tag rules
~~~~~~~~~~~~~~~~~~~~~~

Let us consider all the file names in the dataset, namely:

.. code-block:: output

		DAY01_G72_20180201.npy
		DAY02_G72_20180202.npy
		DAY01_G171_20180101.npy
		Day2_171_20180102.npy
		DAY_G433_20180301.npy
		day02_G433_20180301.npy

We notice that the ``day`` tag value is at the beginning between the
string `day` (ignoring case) and an `_` (underscore). This can be
extracted with the regex pattern ``(?i)day([0-9]+)_``. But one of the
files does not have any info on the day value and for this no value
will be captured. Since we have exclusive information from the person
who performed the experiments, we know it is ``1`` and by default if
no value is captured we would like to choose this. Further, to
maintain uniformity we would like to ensure that the length of ``day``
tag is ``2``, and if not prefix it with ``0``. Putting these together
as a tag retrieval rule:

.. code-block:: yaml

		tags_rules:
		  - name: day
		    pattern: "(?i)day([0-9]+)_"
		    length: 2
		    iffy_prefix: 0
		    default: 1

Similarly, we see that the value following the first underscore gives
the ``mice`` info. This can be extracted with the regex pattern
``_([a-zA-Z0-9]+)_``. Since one of the files does not have the
``mice`` info beginning with the suffix *G*, we choose to extract only
the numbers with the regex pattern using ``_G?([0-9]+)_`` and prepend
it with *G*. Putting these together as a rule:

.. code-block:: yaml

		tags_rules:
		  - name: mice
		    pattern: "_G?([0-9]+)_"
		    prepend: G

There is no value for the ``imaging`` tag in path but we know that it
is *calcium* imaging data, so let us set all values to *calcium*. And
similarly, let ``extension`` be *.npy*.

.. code-block:: yaml

		tags_rules:
		  - name: imaging
		    value: calcium
		  - name: extension
		    value: npy

Putting these together, we get our organization rules config:

.. code-block:: yaml

		source: "/path/to/unorganized/data"
		destination: "/path/to/store/organized/data"
		pattern: "*.npy"
		tags_rules:
		  - name: day
		    pattern: "(?i)day([0-9]+)_"
		    length: 2
		    iffy_prefix: 0
		    default: 1
		  - name: mice
		    pattern: "_G?([0-9]+)_"
		    prepend: G
		  - name: imaging
		    value: calcium
		  - name: extension
		    value: npy

Executing the rules
~~~~~~~~~~~~~~~~~~~

To run this set of rules and obtain the organized dataset, we can use
:meth:`~specification.Specification.organize`.

.. code-block:: python

		from almirah.utils import read_yaml

		# Load rules into dictionary
		rules = read_yaml("/path/to/rules")

		# Execute rules and use Specification for path building
		spec.organize(rules)

Listing the contents of the organized dataset using ``tree`` after the
run gives:

.. code-block:: output

		.
		├── mice-G72
		│   ├── day-01
		│   │   └── mice-G72_day-01_imaging-calcium.npy
		│   └── day-02
		│       └── mice-G72_day-02_imaging-calcium.npy
		├── mice-G171
		│   ├── day-01
		│   │   └── mice-G171_day-01_imaging-calcium.npy
		│   └── day-02
		│       └── mice-G171_day-02_imaging-calcium.npy
   		└── mice-G433
		    ├── day-01
		    │   └── mice-G433_day-01_imaging-calcium.npy
		    └── day-02
		        └── mice-G433_day-02_imaging-calcium.npy		

This is much easier to navigate and structured. Along with this comes
the bonus of being able to query the dataset once indexed. In
``almirah``, a collection of files with a common root directory form a
:class:`~layout.Layout` and a collection of layouts form a
:class:`~dataset.Dataset`.

Querying
--------

Tags associated with files can help in filtering through the
dataset. We can retrieve a subset of files that satisfy certain
tags. An operation called indexing makes this possible.

The indexing operation
~~~~~~~~~~~~~~~~~~~~~~

In brief, the indexing operation on a :class:`~layout.Layout` or a
:class:`~dataset.Dataset` crawls top-down from the root directory and
figures out the *tag*:*file* associations. These associations are
stored and used while querying to filter through the
dataset. Additional associations for a file excluding tags present in
the path can be provided with an accompanying *JSON* file that shares
the same filename. Indexing is performed by
:meth:`~layout.Layout.index`.

To index our tutorial dataset:

.. code-block:: python

		from almirah import Layout

		# Create a Layout instance with data path and Specification
		layout = Layout(root="/path/to/organized/data", specification_name=spec.name)

		print(layout)
		# <Layout root: '/path/to/organized/data'>

The returned instance does not yet have all details of files in it and
tags for each file. For this, it has to be indexed.

.. code-block:: python

		# Index the Layout with tags mentioned in Specification
		layout.index()

.. code-block:: python

		print(f"Files in layout: {len(layout.files)}")
		# Files in layout: 6
		
		print(f"The first file is {layout.files[0]}.")
		# The first file is <File path=`/path/to/file`>.

.. important::

   Before :class:`~layout.Layout` creation, it is required that a
   :class:`~specification.Specification` be created. The
   ``specification_name`` argument checks for the index to retrieve
   the :class:`~specification.Specification`. This can be achieve like
   so:

With this, we can start querying in multiple ways.

Filtering with tags
~~~~~~~~~~~~~~~~~~~

Once indexed, the instance can be queried with
:meth:`~layout.Layout.query()` using tag values. For example, retrieve
all files of mice *G171* where recording was done on day *02*.

.. code-block:: python

		layout.query(mice='G171', day='02')
		# ['/root/mice-G171_day-01_imaging-calcium.npy',
		#  '/root/mice-G171_day-02_imaging-calcium.npy']

A list of :class:`File` objects is returned. These can be utilised for
further downstream analysis pipelines.

More components!!
-----------------

Great! Now, we have organized a dataset and made it
query-able. Though, we have used the word *dataset* liberally so far,
in ``almirah``, a :class:`~dataset.Dataset` and :class:`~layout.Layout`
are conceptually different.

A :class:`~layout.Layout` is a collection of files in a directory that
follow a :class:`~specification.Specification`. A collection of
*Layouts* make up a :class:`~dataset.Dataset`. These *Layouts* are
said to be the *components* of the :class:`~dataset.Dataset`.

Now, with this in mind, we can see that we organized the tutorial
dataset into a :class:`~layout.Layout`. If we have more *Layouts*
related to the project, we can collect them under a
:class:`~dataset.Dataset`.

.. code-block:: python

		from almirah import Dataset

		# Create a Dataset
		dataset = Dataset(name="tutorial")

		# Add out previous Layout to the Dataset
		dataset.add(layout)

		# If you have more, you can add them too

Operations performed on a :class:`~layout.Layout` like indexing and
querying can be performed on a :class:`~dataset.Dataset` too using
:meth:`~dataset.Dataset.index` and :meth:`~dataset.Dataset.query`.
These will perform the operation on all the components of the dataset.

.. note::

   Objects like :class:`~dataset.Dataset` and :class:`~layout.Layout`
   are not written to the ``index`` by default. If you would like your
   objects to be persistent, you will have to write to the ``index`` by
   invoking :class:`~indexer.Indexer.commit()`

Databases as components
-----------------------

Often, datasets have relevant information stored in databases. If we
miss out on these, the dataset is not complete. Worry not, a
:class:`~database.Database` can be added as a component to a
:class:`~dataset.Dataset`. Further, :class:`~database.Database` can be
queried to retrieve records using :meth:`~database.Database.query`
too. Queries with the parameter ``table`` to a
:class:`~dataset.Dataset` are directed to its component databases
only. Connection to the :class:`~database.Database` has to be
established using :meth:`~database.Database.connect` during each
Python session. This is because, the ``index`` does not store
usernames and passwords for security reasons.

.. code-block:: python

		from almirah import Database

		# Create a Database instance for a mysql db 'tutorial' running locally
		db = Database(name="tutorial", host="127.0.0.1", backend="mysql")
		db.connect(username, password)

		# Add db to Dataset
		dataset.add(db)

A :class:`~database.Database` by SQLAlchemy is in *connection
mode*. An alternative to this, is the *request mode*. This is only
applicable for retrieving records and not other operations. To set
this mode on object creation, provide the parameter
``backend="request"``:

.. code-block:: python

		# Create a Database in 'request' mode
		db = Database(name="tutorial", host="127.0.0.1", backend="request")

		# Connect to end point
		db.connect(username, password)

In this mode, queries are sent as *POST* requests with appropriate
authentication header to the url endpoint and the response is chosen
as the result. For this to work, you should have setup a url endpoint
on the server that the :class:`~database.Database` instance is running
on and setup appropriate authentication on *host/authenticate* to
return a token. This url endpoint processes the request appropriately,
and returns the records as a response in *JSON*. One way this can be
achieved is by extracting *POST* request keys and passing them as
arguments to :meth:`~database.Database.query` in the view that handles
requests to the url endpoint.

Another mode of operation, deals with data in Google sheets. Here,
each spreadsheet is treated as the Database and each worksheet in the
spreatsheet is analogous to a table. To read data from sheets, set
``backend="gsheet"`` and to connect provide the keyfile.

.. note::

   Please have a look at the `Create service account keys`_ section of
   Google workspace docs to create a keyfile.

.. _Create service account keys: https://cloud.google.com/iam/docs/keys-create-delete

.. code-block:: python

		# Create Database in 'gsheet' mode
		db = Database(name='any name', host='gsheet url', backend='gsheet')

		# Connect to gsheet via Google API
		db.connect(keyfile='/path to keyfile')     
		
.. important::

   Only databases supported by SQLAlchemy are functional via
   ``almirah`` for operations other than reading.

Other capabilities
------------------

This tutorial is a quick run-through some of the things ``almirah``
can help with. There are other things it can do:

* Migrate database records from one schema to another
* Interface with DataLad compatible datasets

Please look up :doc:`reference/index` if you need these. If there is a
feature you would like, but ``almirah`` does not support it yet,
please do consider raising a request or :doc:`contributing`.
