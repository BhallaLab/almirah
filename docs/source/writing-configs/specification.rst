Specification details
=====================

.. currentmodule:: almirah.Specification

A Specification is a agreed-upon standard that describes how a dataset
should be organized. It includes the file paths allowed, the tags
associated with a file, and their role in file name generation. This
document will detail how to provide each of this options.

A minimal configuration of tags for a dataset looks like this:

.. code-block:: yaml

		tags:
		  - name: filename
		    pattern: "[/\\\\](.*)\\."
		  - name: extension
		    pattern: "(\\.[^/\\\\]+)$"
		path_patterns:
		  - "{filename}{extension}"

Using the above minimal specification for path building with :meth:`~build_path`:

.. code-block:: python

		# Build path according to specification with tags as parameters
		path = specification.build_path(filename="file", extension=".txt")

		# Print the built path.
		print(path)
		# file.txt

Top-level keys
--------------

``tags``
~~~~~~~~

All details regarding permissible tags sit inside the ``tags``
key. The ``tags`` key consists of a sequence of ``name`` and
``pattern`` entries.

``name``
    The name of the tag.

``pattern``
    Regex pattern to retreive the tag value from file path.

    It is required to have a mandatory single capturing group in the
    pattern. The captured value is used as the tag value.

``path_patterns``
~~~~~~~~~~~~~~~~~

All details regarding permissible file paths sit inside the
``path_patterns`` key. The ``path_patterns`` key consists of a
sequence of paths relative to the dataset root. Usage of tag values in
paths is supported.

A path can contain both template and ordinary patterns. The template patterns are:

``[contents]``
    Used to indicate that the contents are optional.

    The path ``/dir[/subdir]/file`` will match both ``/dir/file`` and
    ``dir/subdir/file``.

``{name<values>|default}``
    Used to indicate that the template will be filled in by a tag value.

    ``name`` refers to the name of the tag, ``values`` refers to the
    set of valid values separated by ``|``, and ``default`` refers to
    the default value that is chosen while building path name from
    tags associated.  ``values`` and ``default`` are optional.

    The path ``/dir/{filename<file1|file2>|file1}`` will match
    ``/dir/file1`` and ``/dir/file2`` but not ``/dir/file3``. If no
    ``filename`` tag is provided during path building, ``file1`` is
    chosen as the default.
