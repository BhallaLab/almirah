Tutorial
========

.. currentmodule:: almirah

``almirah`` is a tool to organize, query, and summarize data. In this
tutorial we will use ``almirah`` on a dummy test dataset that represents
imaging data obtained from mice to illustrate some of its usecases. In
case you have not installed ``almirah`` yet, please go to the
:ref:`Installing` section and follow the instructions.

First, let us obtain the dataset to work on for the tutorial. It comes
along with ``almirah`` and can be copied to a convenient location using
the :meth:`~utils.get_tutorial_dataset`.

.. code-block:: python

	       from almirah.utils import get_tutorial_dataset

	       get_tutorial_dataset("path/to/store")

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
``Specification`` for this dataset, let us think about how we would
structure this dataset manually.

Deciding path patterns
~~~~~~~~~~~~~~~~~~~~~~

We would prefer to navigate in the following order from the dataset
root directory, ``mice`` -> ``day`` -> ``file``. This is intuitive and
leaves scope for expansion on new data generation. Based on this, the
path relative to the dataset root would look like `mice/day/file`.
Further, the file name should contain the details of mice, day, and
the type of imaging for identification. For example, a nice file name
would be `mice-G433_day-01_imaging-calcium.npy`.

The above decided path can be mentioned in the ``Specification``
config under the ``path_patterns`` key like:

.. code-block:: yaml

		path_patterns:
		  - "mice-{mice}/day-{day}/mice-{mice}_day-{day}_imaging-{imaging}{extension}"

Here, contents enclosed in ``{}`` represent that these are tag
values. A :class:`~File` in ``almirah`` is associated with a bunch of
tags. It is possible to provide more details on tags regarding valid
values, the default value, and if the :class:`~Tag` is mandatory.

Building paths
~~~~~~~~~~~~~~

Now that we have the basic :doc:`writing-configs/specification`, we
can build valid paths by providing the required tags. Tags are
`key`:`value` pairs that convey an information regarding the file. For
our decided path, the tags we require for path building are ``mice``,
``day``, ``imaging``, and ``extension``.

.. code-block:: python

		from almirah import Specification

		# Create a Specification object
		spec = Specification("/path/to/config")

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

.. code-block:: python

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

Putting all of these together, we have our ``Specification`` config:

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

With the :class:`~Specification` defined, it is now possible to
restructure a dataset given that we are able to retrieve the tags
required to build a valid path from each target file. If we are able
to build a valid relative path, then it just boils down to just moving
the file to that position with respect to the root directory. Lets us
do this for our dataset.

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
:meth:`~Specification.organize`.

.. code-block:: python

		from utils import read_yaml

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
:class:`~Layout` and a collection of layouts form a :class:`~Dataset`.

Querying
--------

Tags associated with files can help in filtering through the
dataset. We can retrieve a subset of files that satisfy certain
tags. An operation called indexing makes this possible.

The indexing operation
~~~~~~~~~~~~~~~~~~~~~~

In brief, the indexing operation on a :class:`~Layout` or a
:class:`~Dataset` crawls top-down from the root directory and figures
out the *tag*:*file* associations. These associations are stored and
used while querying to filter through the dataset. Additional
associations for a file excluding tags present in the path can be
provided with an accompanying *JSON* file that shares the same
filename. Indexing is performed automatically on creation of a
:class:`~Layout` or :class:`~Dataset`.

To index our tutorial dataset:

.. code-block:: python

		from almirah import Layout

		# Create a Layout instance with data path and Specification
		layout = Layout.create("/path/to/organized/data", spec=spec)

		print(layout.root)
		# /path/to/organized/data

The returned instance has all details including the files in it and
tags for each file.

.. code-block:: python

		print(f"Files in layout: {len(layout.files)}")
		# Files in layout: 6
		
		print(f"The first file is {layout.files[0]}.")
		# The first file is <File path=`/path/to/file`>.




With this, we can start querying in multiple ways.

Filtering with tags
~~~~~~~~~~~~~~~~~~~

An instance associated with the indexer can be queried with
:meth:`~Layout.get_files()` using tag values. For example, retrieve
all files of mice *G171* where recording was done on day *02*.

.. code-block:: python

		layout.get_files(mice='G171', day='02')
		# ['/root/mice-G171_day-01_imaging-calcium.npy',
		#  '/root/mice-G171_day-02_imaging-calcium.npy']

A list of :class:`File` objects is returned. These can be utilised for
further downstream analysis pipelines.

Other capabilities
------------------

This tutorial is a quick run-through some of the things ``almirah`` can help with. There are other things it can do:

* Migrate database records from one schema to another
* Interface with DataLad compatible datasets

The :doc:`reference/index` acts as good starting point if you need these.  

		

      



		
		
   


