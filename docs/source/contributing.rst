Contributing
============

napi was initially developed to handle and maintain neuroimaging
datasets. But we believe this can be useful for other datasets too!

We happily accept contributions for all things related to dataset
management.

If you wish to add a new feature or fix a bug:

#. `Check for open issues <https://github.com/girishmm/napi/issues>`_
   or open a fresh issue to start a discussion around a feature idea
   or a bug.
#. Fork the `repository on Github <https://github.com/girishmm/napi>`_
   to start making your changes.
#. Write a test which shows that the bug was fixed or that the feature
   works as expected.
#. Format your changes with black.
#. Add a `changelog entry <https://github.com/girishmm/napi/blob/main/changelog/README.md>`_
   if required.   
#. Send a pull request and bug us till it gets merged and published.

Setting up your development environment
---------------------------------------

In order to setup the development environment all you need is `poetry
<https://python-poetry.org/>`_ installed in your machine.

.. code-block:: bash
		
		$ git clone git@github.com:girishmm/napi.git
		$ cd napi
		$ poetry install

.. note::

   File format conversion functionality depends on external non-python
   dependencies such as `dcm2niix`_ and `edf2asc`_. The installation
   of these is left as an exercise to the user. Just kidding, these
   will be added in later.

   .. _dcm2niix: https://github.com/rordenlab/dcm2niix
   .. _edf2asc: https://www.sr-research.com/support/

Running tests
-------------

We use `pytest <https://docs.pytest.org/en/7.1.x/index.html>`_ for
running the test suite.

.. code-block:: bash

		$ pytest

Contributing to documentation
-----------------------------

You can build the docs locally using `sphinx <https://www.sphinx-doc.org/en/master/>`_.

.. code-block:: bash

		$ sphinx-build -b html docs/source docs/build/html

However, if you have run **sphinx-quickstart**, it creates a
*Makefile* and *make.bat* which make it easier.

.. code-block:: bash

		$ make html

The documentation is built `continuously on GitHub Actions
<https://github.com/girishmm/napi/actions>`_ with every push
request. Hence, it is not necessary to push documentation builds to
the repository.

If you are planning a release and want to update the changelog in
docs, run ``towncrier build --version X.Y.Z`` before building check
the final look.

Releases
--------

A release candidate can be created by any contributor.

- Announce intent to release by communicating to all contributors.
- Run ``towncrier build --version X.Y.Z`` to update ``CHANGES.rst``
  with the release notes. Adjust as necessary.
- Update ``pyproject.toml`` and ``conf.py`` with the proper version
  number.
- Commit the changes to a ``release-X.Y.Z`` branch.
- Create a pull request!
