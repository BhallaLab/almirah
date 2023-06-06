"""Model classes to represent data files."""


class Config:
    """Representation of the collection of configuration files."""

    def get_config(self):
        """Return config as a dictionary.

        If there are multiple config files, then retrieve based on
        name. Else, return the file in provided path.
        """


class File:
    """Generic file representation."""
