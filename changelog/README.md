This directory contains changelog entries: short files that contain a
small **rst**-formatted text that will be added to ``CHANGES.rst`` by
[towncrier](https://towncrier.readthedocs.io/en/latest/).

If your change does not deserve a changelog entry, please skip this.

The ``CHANGES.rst`` will be read by **users**, so this description
should be aimed at almirah users instead of describing internal
changes which are only relevant to the developers.

Make sure to use phrases the are self-sufficient and use punctuation:

    Support for BIDS specification.
    
    Fixed bug that lead to reindexing of Layout.

Each file should be named like ``<ISSUE>.<TYPE>.rst``, where
``<ISSUE>`` is an issue number, and ``<TYPE>`` is one of the *five
towncrier default types*. The default types available and example
demonstrations can be found in [Creating news fragements][1].

If your pull request fixes an issue, use that number here. If there is
no issue, then use the pull request number after submitting one.

You can run ``towncrier build --draft --version X.Y.Z`` to get a
preview of how the change will look in the release notes.

[1]: https://towncrier.readthedocs.io/en/stable/tutorial.html#creating-news-fragments