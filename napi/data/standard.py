"""Define the standard for the data set."""

import re
import os
import warnings

from string import Formatter

from ..utils import get_matching_files, copy


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

        # Remove none values
        entities = {k: v for k, v in entities.items() if v or v == 0}

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

    def organize(self, rules):
        """Create a organized copy of a source directory based on rules.

        Parameters
        ----------
        rules : dict
            A dictionary describing the instructions for organizing.

        Returns
        -------
        None
        """

        # Check for required keys
        for mandatory_key in [
            "source",
            "destination",
            "pattern",
            "entity_rules",
        ]:
            if mandatory_key not in rules:
                print(f"Missing mandatory key '{mandatory_key}' in rule")
                return

        # Organize matched files as per rules
        for file in get_matching_files(rules.get("source"), rules.get("pattern")) or []:
            # Extract entities
            entities = dict()
            for rule in rules.get("entity_rules"):
                entity_name = rule.get("name")

                if "value" in rule:
                    entities.update({entity_name: rule.get("value")})
                    continue

                match = re.findall(rule.get("pattern"), file)
                entity_val = match[0] if match else None

                if "prepend" in rule and entity_val:
                    entity_val = "".join([str(rule.get("prepend")), entity_val])

                if (
                    "length" in rule
                    and entity_val
                    and len(entity_val) != rule.get("length")
                ):
                    if "iffy_prepend" in rule:
                        entity_val = "".join(
                            [str(rule.get("iffy_prepend")), entity_val]
                        )
                    if len(entity_val) != rule.get("length"):
                        entity_val = None

                if rule.get("case") in ["lower", "upper"] and entity_val:
                    entity_val = (
                        entity_val.lower()
                        if rule.get("case") == "lower"
                        else entity_val.upper()
                    )

                if "default" in rule and not entity_val:
                    entity_val = rule.get("default")

                if not entity_val:
                    warnings.warn(
                        f"Unable to find value for entity '{entity_name}' for '{file}'"
                    )

                entities.update({entity_name: entity_val})

            # Warning, clunky code ahead. To be made better
            rel_path = self.build_path(entities)
            new_path = (
                os.path.join(rules.get("destination"), rel_path) if rel_path else None
            )
            copy(file, new_path)

            if not rules.get("copy_fellows", False) or not new_path:
                continue

            # Find fellows
            fellows = [
                f.path
                for f in os.scandir(os.path.dirname(file))
                if f.name != os.path.basename(file) and not f.is_dir()
            ]

            for fellow in fellows:
                # Entity changes for fellow
                entities_copy = entities.copy()
                entities_copy.update({"extension": os.path.splitext(fellow)[1]})
                for rule in rules.get("rename_rules", []):
                    if re.findall(rule.get("target"), fellow):
                        entities_copy.update({"suffix": rule.get("suffix")})

                # Copy fellow files
                rel_path = self.build_path(entities_copy)
                new_path = (
                    os.path.join(rules.get("destination"), rel_path)
                    if rel_path
                    else None
                )

                copy(fellow, new_path)

    def validate(self):
        """Returns True if path is valid."""
        pass

    def __repr__(self):
        return f"<Specification name={self.name}>"
