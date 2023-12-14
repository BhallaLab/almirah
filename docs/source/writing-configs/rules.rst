Organization rules
==================

.. currentmodule:: almirah.Specification

To organize an unformatted dataset according to a specification, user
instructions are required. These can be mentioned as rules using
supported keywords. This document will list all supported rules that
will support the organization task. Multiple dataset rules can be
mentioned in a single config by separating them with ``---``.

A minimal rule config to copy all files but one looks like this:

.. code-block:: yaml

		source: "/path/to/data"
		destination: "/path/to/destination"
		pattern: ".*"
		tag_rules:
		  - name: filename
		    pattern: "(.*)\\."
		  - name: extension
		    pattern: "(\\.[^/\\\\]+)$"
		skip:
		  - ignore_this_file

The above rules can be used to organize a dataset with :meth:`~organize`:		    

.. code-block:: python

		# Organize according to a specification
		specification.organize(rules_loaded_as_dict)

Top-level keys
--------------

``source``
~~~~~~~~~~

The root directory where data is present.

``destination``
~~~~~~~~~~~~~~~

The directory in which to store the organized data.

.. _map:
``map``
~~~~~~~

Path to the *csv* file that will be used for mapping to get the value
of another tag based a retrieved tag.

If provided, then ``from`` and ``to`` keys are to be provided in the
specific tag section of ``tag_rules`` too to complete the rule. There
should be a one-to-one mapping between ``from`` and ``to``.

``pattern``
~~~~~~~~~~~

All source directory contents matching this will be considered for
organization.

``overwrite``
~~~~~~~~~~~~~

Boolean value indicating whether to overwrite data if exists.

``add``
~~~~~~~

Add common files directly to each matched source directory
content. The ``add`` key consists of a sequence of ``path`` and
``position`` entries.

``path``
    Path to the common file.

``position``
    Position at which to add the common file.

    Valid values are ``content`` and ``fellow``. They place the file
    to be added either inside or at the same level as the matched
    source directory content respectively.

``copy_fellows``
~~~~~~~~~~~~~~~~

Boolean value indicating whether to copy other files present at the
same directory level.

``skip``
~~~~~~~~

Sequence of paths to ignore.

``tag_rules``
~~~~~~~~~~~~~

All details regarding inferring tags from filenames in the source
directory sit inside the ``tag_rules`` key. The tags inferred are used
for building the path according to the specification. The
``tag_rules`` key consists of a sequence of tag ``name`` and
``pattern`` entries along with valid rules for each tag.

``name``
    The name of the tag.

``pattern``
    Regex pattern to retreive the tag value from file path.

    It is required to have a mandatory single capturing group in the
    pattern. The captured value is used as the tag value if it passes
    the rules.

The valid rules that can be used are:

``default``
    The default value to use if no value is captured via ``pattern``.

``case``
    Accepts either ``upper`` or ``lower`` and accordingly changes the
    case of the value captured.

``length``
    Mentions the valid length of captured string.

    If ``iffy_prepend`` is provided, the value is validated again post
    prefix addition.

``iffy_prepend``
    If the length of the captured string does not equal the ``length``
    rule, then the ``iffy_prepend`` value is added as a prefix to the
    captured value.

``value``
    **The** value to use for the tag. Overrides captured values if
    necessary.

``from``
    The column in :ref:`map` file that maps to the tag
    value retrieved by ``pattern``.

    ``to`` rule and :ref:`map` file path have to be provided to complete
    this rule.

``to``
    The column in :ref:`map` file that maps to the tag name mentioned.

    ``to`` rule and :ref:`map` file path have to be provided to complete
    this rule.

.. important::

    If a mandatory tag cannot be inferred from the file path, then
    path building fails and the file is not added to the organized
    dataset. More info on the tag that could not be inferred can be
    found in logs.
    


