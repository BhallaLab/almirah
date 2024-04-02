From access to analysis
=======================

.. currentmodule:: almirah

The CALM-BRAINS dataset is a rich collection of data obtained from
over 2000 subjects. To know more about the contents of the dataset,
please head over to :doc:`reference/index`. The dataset is made of two
parts: files that organized according to `BIDS
<https://bids.neuroimaging.io/>`_ and questionnaires that are stored
in SQL tables.

Requesting for access
---------------------

If you are interested and would like access, we are happy to help
you. Due to the sensitive nature of the dataset, it is currently not
possible to make it openly available. Please write to `us`_ with a
short message with information on your affiliation and how you plan to
use the data. Your request will be discussed by the program committee
and if approved, we will share your credentials. We promise to get
back at the earliest.

Once you have hold of your credentials, you can access the dataset!!
To quickly skim through the contents that are files, head over to the
`GIN instance`_ that is home to the dataset. You can think of this as
GitHub for datasets. Once you login, you will notice that you are a
part of the CBM organization and can access datasets you have been
approved to. You can now download the dataset files to your local
system and use it :)

.. note::

   The dataset is `DataLad`_ compatible. This means, when the dataset
   is cloned, not all file contents will be available right
   after. Only small files will be available right away. So, you can
   `look without touching`_.

To have a peek at the questionnaires, head over to the `Questionnaire
explorer`_. On login, you can browse through tables and even query
using SQL. Outputs can be downloaded as csv files.

.. _DataLad: https://www.datalad.org/
.. _GIN instance: http://tekeli.ncbs.res.in:3000/
.. _Questionnaire explorer: http://tekeli.ncbs.res.in:3001/
.. _look without touching: https://handbook.datalad.org/en/latest/basics/101-116-sharelocal.html

Obtaining a subset of data files
--------------------------------

It is often the case that only a subset of data is required. Let's
say, you would like to download data relating to only the OCD cohort
or specific to resting state EEG. Can this be achieved? Definitely!!

Each dataset release comes with an index. The index is an `SQlite`
database that can be downloaded. It helps you filter through the
dataset. This is possible as each file in the dataset is associated to
a set of tags and this information is stored in the index. Further, it
is pre-population with the details of the different data components
that make up CALM-BRAINS. `almirah`_ by default looks for this at
system home. But this is not ready to use out-of-the-box post
download.

Since, we do not know where you plan to store the dataset components,
the path is set to */path/to/data*. It is **NECESSARY** that you set
this!! This can be done with `almirah`_ like so:

#. Download the release-specific index to your home directory.
   
#. Clone the dataset and set path.

   .. code-block:: python
		   
   		from almirah import Dataset
   
		# Retrieve the layout you have access to from the dataset.
		# Keep the path to /path/to/data as this is the dummy info
		# used to create the index.
		dataset = Dataset(name='calmbrains')
		layout = dataset.get_layout(path='/path/to/data')

		# Change the layout path.
		layout.set_path(path='/your/local/path')
		
		# Clone the dataset from host to local path.
		layout.clone()

Now, you have successfully got the look-only version of the data. You
can now query the layout object to get files that only match your
needs.

Say, you only want resting state EEG data, then:

.. code-block:: python

		# Provide tags that fit your search criteria
		files = layout.query_files(datatype='eeg', task='rest')
		files.get()

Now, you only have files that fit your search criteria. The rest are
still look-only files without their contents.

.. note::

   The same effect can be achieved using only `DataLad`_ commands to
   some extent. One approach would be to pair commands with patterns
   to choose specific filenames. But obtaining files that match
   certain metadata and study-specific parameters would not be
   possible this way.

Retrieving questionnaire data
-----------------------------

It is possible to query questionnaire data in tables, or for that
matter, any table in a database using `almirah`_. The database
information is already built into the index, so all you need extra are
your credentials.

   .. code-block:: python

		   from almirah import Dataset

		   # Retrieve the db from the dataset.
		   dataset = Dataset(name='calmbrains')
		   db = dataset.get_db(name='questionnaires')

		   # Get the records you need from a table.
		   records = db.get_table(name='table_name')

The records are returned as a :doc:`pandas:reference/api/pandas.DataFrame`.

.. tip::

   Use the :doc:`reference/index` to checkout the info provided by
   each table. This will help you find which table has the info you
   need.

Analysis
--------

Now you know how to access and retrieve contents of the CALM-BRAINS
dataset. How can you use it?

We leave that to you and look forward to how this dataset helps with
the question of your interest. Since it is not possible to
exhaustively support all analysis possibilities, we are unfortunately
unable to help with this to a great extent. But if there is something
specific you think we can help, do contact `us`_.

If you would like to get acquainted with CALM-BRAINS and `almirah`_,
do follow through the :doc:`examples/index`. They will lead you
through simple analysis flows.

Citing and Contributing
-----------------------

If you use the dataset in your work, please cite the dataset release
version you used. If you would like your analysis outputs to be
available for others, do reach out to `us`_. We would be happy to add
them as derivatives.

.. _us: bhalla@ncbs.res.in
.. _almirah: https://girishmm.github.io/almirah/


