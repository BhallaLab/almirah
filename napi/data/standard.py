"""Define the standard for the data set."""

import re
import os
import warnings

from string import Formatter

from .. import utils


_TAG_PATTERN = re.compile(r"({([\w\d]*?)(?:<([^>]+)>)?(?:\|((?:\.?[\w])+))?\})")


def get_spec(details, name):
    if not details:
        details = os.path.join(os.path.dirname(__file__), "configs", "bids.yaml")

    if isinstance(details, str) and os.path.exists(details):
        spec = utils.read_yaml(details)
        if not name:
            name = os.path.basename(os.path.splitext(details)[0])
    else:
        spec = details

    return spec, name


class Specification:
    """Representation of the specification used.

    Attributes
    ----------
    name : str
        The name of the specification.

    Parameters
    ----------
    spec : dict or str
        The dict-converted YAML specification file or its path.

    Notes
    -----
    The YAML file that describes the specification can be split into two parts.
       - tag definitions
       - path definitions

    More information on these will follow.
    """

    def __init__(self, details=None, name=None):
        self.spec, self.name = get_spec(details, name)

    def build_path(self, tags):
        """Construct path provided a set of tags.

        Parameters
        ----------
        tags : dict
            A dictionary with tag name, value pairs.

        Returns
        -------
        path : str
            The constructed path if successful, else `None`.
        """

        path_patterns = self.spec.get("path_patterns")

        # Remove none values
        tags = {k: v for k, v in tags.items() if v or v == 0}

        # Work with extension with or without .
        if "extension" in tags:
            ext = tags.get("extension")
            tags["extension"] = ext if ext.startswith(".") else "." + ext

        # Attempt to match pattern with tags and return first match
        for pattern in path_patterns:
            path = pattern
            matches = _TAG_PATTERN.findall(pattern)
            tags_defined = [t[1] for t in matches]

            # Do not tamper with tags provided so that
            # it can be used for other patterns
            tags_copy = tags.copy()

            # Skip if all tags not matched
            if set(tags_copy.keys()) - set(tags_defined):
                continue

            # Validate and fill in missing tags with default
            for subpattern, name, valid, default in matches:
                valid_expanded = [v for v in valid.split("|")]

                if (
                    valid_expanded
                    and name in tags_copy
                    and tags_copy[name] not in valid_expanded
                ):
                    continue

                if name not in tags_copy and default:
                    tags_copy[name] = default

                if valid_expanded and default and default not in valid_expanded:
                    warnings.warn(
                        f"Pattern {subpattern} is inconsistent as it defines an invalid default value"
                    )

                # Simplify path
                path = path.replace(subpattern, "{%s}" % name)

            # Keep or remove optional tags
            optional_patterns = re.findall(r"(\[.*?\])", path)
            for op in optional_patterns:
                optional_tag = re.findall(r"\{(.*?)\}", op)[0]
                path = (
                    path.replace(op, op[1:-1])
                    if optional_tag in tags_copy.keys()
                    else path.replace(op, "")
                )

            # Find fields available in path
            fields = [f[1] for f in Formatter().parse(path)]

            # Proceed only if all field data available
            if set(fields) - set(tags_copy.keys()):
                continue

            # Fill in the fields
            path = path.format_map(tags_copy)

            return path

        return None

    def extract_tags(self, path):
        """Returns tag:value pairs for file."""
        tags = dict()
        for tag in self.spec.get("tags"):
            val = re.findall(tag.get("pattern"), path)
            if val:
                tags[tag.get("name")] = val[0]
        return tags

    def get_valid_tags(self):
        """Returns valid tag names."""
        return [t.get("name") for t in self.spec.get("tags")]

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
            "tag_rules",
        ]:
            if mandatory_key not in rules:
                raise KeyError(f"Expected but not found '{mandatory_key}' in rules")

        # Organize matched files as per rules
        for file in (
            utils.get_matching_files(rules.get("source"), rules.get("pattern")) or []
        ):
            # Extract tags
            tags = dict()
            for rule in rules.get("tag_rules"):
                tag_name = rule.get("name")

                if "value" in rule:
                    tags.update({tag_name: rule.get("value")})
                    continue

                match = re.findall(rule.get("pattern"), file)
                tag_val = match[0] if match else None

                if "prepend" in rule and tag_val:
                    tag_val = "".join([str(rule.get("prepend")), tag_val])

                if "length" in rule and tag_val and len(tag_val) != rule.get("length"):
                    if "iffy_prepend" in rule:
                        tag_val = "".join([str(rule.get("iffy_prepend")), tag_val])
                    if len(tag_val) != rule.get("length"):
                        tag_val = None

                if rule.get("case") in ["lower", "upper"] and tag_val:
                    tag_val = (
                        tag_val.lower()
                        if rule.get("case") == "lower"
                        else tag_val.upper()
                    )

                if "default" in rule and not tag_val:
                    tag_val = rule.get("default")

                if not tag_val:
                    warnings.warn(
                        f"Unable to find value for tag '{tag_name}' for '{file}'"
                    )

                tags.update({tag_name: tag_val})

            # Warning, clunky code ahead. To be made better
            rel_path = self.build_path(tags)
            new_path = (
                os.path.join(rules.get("destination"), rel_path) if rel_path else None
            )
            utils.copy(file, new_path)

            if not rules.get("copy_fellows", False) or not new_path:
                continue

            # Find fellows
            fellows = [
                f.path
                for f in os.scandir(os.path.dirname(file))
                if f.name != os.path.basename(file) and not f.is_dir()
            ]

            for fellow in fellows:
                # Tag changes for fellow
                tags_copy = tags.copy()
                tags_copy.update({"extension": os.path.splitext(fellow)[1]})
                for rule in rules.get("rename_rules", []):
                    if re.findall(rule.get("target"), fellow):
                        tags_copy.update({"suffix": rule.get("suffix")})

                # Copy fellow files
                rel_path = self.build_path(tags_copy)
                new_path = (
                    os.path.join(rules.get("destination"), rel_path)
                    if rel_path
                    else None
                )

                utils.copy(fellow, new_path)

    def validate(self):
        """Returns True if path is valid."""
        pass

    def __repr__(self):
        return f"<Specification name={self.name}>"
