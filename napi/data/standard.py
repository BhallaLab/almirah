"""Define the standard for the data set."""


class Specification:
    """Representation of the specification used."""

    def validate(self):
        """Returns True if path is valid."""

        raise NotImplementedError

    def build_path(self):
        """Construct path provided a set of entities."""
