"""Define the standard for the data set."""

import re
import warnings

from string import Formatter


_PATTERN_FIND = re.compile(r"({([\w\d]*?)(?:<([^>]+)>)?(?:\|((?:\.?[\w])+))?\})")


class Specification:
    """Representation of the specification used.

    Attributes
    ----------
    name : str
        The name of the specification.

    Parameters
    ----------
    name : str
        The name of the specification.
    spec : dict
        The dict-converted YAML file that defines the specification.

    Notes
    -----
    The YAML file that describes the specification can be split into two parts.
       - entity definitions
       - path definitions

    More information on these will follow.
    """

    def __init__(self, name, spec):
        self._spec = spec
        self.name = name

    def build_path(self, entities):
        """Construct path provided a set of entities.

        Parameters
        ----------
        entities : dict
            A dictionary with entity name, value pairs.

        Returns
        -------
        path : str
            The constructed path if successful, else `None`.
        """

        path_patterns = self._spec.get("path_patterns")

        # Attempt to match pattern with entities and return first match
        for pattern in path_patterns:
            path = pattern
            matches = _PATTERN_FIND.findall(pattern)
            entities_defined = [e[1] for e in matches]

            # Do not tamper with entities provided so that
            # it can be used for other patterns
            entities_copy = entities.copy()

            # Skip if all entities not matched
            if set(entities_copy.keys()) - set(entities_defined):
                continue

            # Validate and fill in missing entities with default
            for subpattern, name, valid, default in matches:
                valid_expanded = [v for v in valid.split("|")]

                if (
                    valid_expanded
                    and name in entities_copy
                    and entities_copy[name] not in valid_expanded
                ):
                    continue

                if name not in entities_copy and default:
                    entities_copy[name] = default

                if valid_expanded and default and default not in valid_expanded:
                    warnings.warn(
                        f"Pattern {subpattern} is inconsistent as it defines an invalid default value"
                    )

                # Simplify path
                path = path.replace(subpattern, "{%s}" % name)

            # Keep or remove optional entities
            optional_patterns = re.findall(r"(\[.*?\])", path)
            for op in optional_patterns:
                optional_entity = re.findall(r"\{(.*?)\}", op)[0]
                path = (
                    path.replace(op, op[1:-1])
                    if optional_entity in entities_copy.keys()
                    else path.replace(op, "")
                )

            # Find fields available in path
            fields = [f[1] for f in Formatter().parse(path)]

            # Proceed only if all field data available
            if set(fields) - set(entities_copy.keys()):
                continue

            # Fill in the fields
            path = path.format_map(entities_copy)

            return path

        return None

    def get_valid_entities(self):
        """Returns valid entity names."""
        return [e.get("name") for e in self._spec.get("entities")]

    def validate(self):
        """Returns True if path is valid."""
        pass

    def __repr__(self):
        return f"<Specification name={self.name}>"
