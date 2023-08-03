"""Define the standard for the data set."""

import re
import os
import logging
import warnings

from string import Formatter

from .. import utils


_TAG_PATTERN = re.compile(r"({([\w\d]*?)(?:<([^>]+)>)?(?:\|((?:\.?[\w])+))?\})")


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

    def get_valid_tags(self):
        """Returns valid tag names."""
        return [t.get("name") for t in self.spec.get("tags")]

    def extract_tags(self, path):
        """Returns tag:value pairs for file."""
        tags = {}
        for tag in self.spec.get("tags"):
            val = re.findall(tag.get("pattern"), path)
            if val:
                tags[tag.get("name")] = val[0]
        return tags

    def validate(self, path):
        """Returns True if path is valid."""
        tags = self.extract_tags(path)
        if self.build_path(tags) == path:
            return True
        return False

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
        logging.debug(f"Building path with tags : {tags}")

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

        source = rules.get("source")
        destination = rules.get("destination")

        logging.info(f"Initiating organization of {source} -> {destination}")

        overwrite = rules.get("overwrite", False)
        if overwrite:
            logging.warning("If found, existing files will be overwritten")
        logging.info(f"Matching contents with pattern {rules.get('pattern')}")

        # Organize matched files as per rules
        for file in utils.get_matches(source, rules.get("pattern")) or []:
            logging.info(f"Found match with file {file}")

            # Extract tags
            tags = {}
            for rule in rules.get("tag_rules"):
                tag_name = rule.get("name")
                logging.debug(f"Foraging for {tag_name} tag")

                if "value" in rule:
                    tag_val = rule.get("value")
                    tags[tag_name] = tag_val
                    logging.debug(f"Setting tag with {tag_val}")
                else:
                    match = re.findall(rule.get("pattern"), file)
                    if match and len(match) != 1:
                        logging.error(
                            "Expected single match, more found. Choosing last over others"
                        )

                    tag_val = match[-1] if match else None
                    logging.debug(f"Matching with pattern yields {tag_val}")

                    if "prepend" in rule and tag_val:
                        tag_val = "".join([str(rule.get("prepend")), tag_val])
                        logging.debug(f"Prepending tag value to get {tag_val}")

                    if (
                        "length" in rule
                        and tag_val
                        and len(tag_val) != rule.get("length")
                    ):
                        if "iffy_prepend" in rule:
                            logging.debug(
                                "Additional prepends as tag of insufficient length"
                            )
                            tag_val = "".join([str(rule.get("iffy_prepend")), tag_val])
                        if len(tag_val) != rule.get("length"):
                            logging.debug("Tag value of insufficient length")
                            tag_val = None

                    if rule.get("case") in ["lower", "upper"] and tag_val:
                        tag_val = (
                            tag_val.lower()
                            if rule.get("case") == "lower"
                            else tag_val.upper()
                        )

                    if "default" in rule and not tag_val:
                        tag_val = rule.get("default")
                        logging.debug(f"Using default value of {tag_val} for tag")

                    if not tag_val:
                        logging.error(f"Unable to find value of tag {tag_name}")

                logging.info(f"File marked with {tag_name}:{tag_val} tag")
                tags.update({tag_name: tag_val})

            # Warning, clunky code ahead. To be made better
            rel_path = self.build_path(tags)
            if not rel_path:
                logging.error("Unable to build destination path for file")
                continue

            new_path = os.path.join(rules.get("destination"), rel_path)
            logging.info(f"Target destination path is {new_path}")
            utils.copy(file, new_path, overwrite)
            logging.info("Moved file to target")

            if not rules.get("copy_fellows", False):
                continue

            # Find fellows
            logging.info("Initiating copying of fellow files")
            fellows = [
                f.path
                for f in os.scandir(os.path.dirname(file))
                if f.name != os.path.basename(file) and not f.is_dir()
            ]
            logging.info(f"Found {len(fellows)} fellows accompanying the file")

            for fellow in fellows:
                # Tag changes for fellow
                logging.info(f"Changing tags for fellow {fellow}")
                tags_copy = tags.copy()
                tags_copy.update({"extension": os.path.splitext(fellow)[1]})
                for rule in rules.get("rename_rules", []):
                    if re.findall(rule.get("target"), fellow):
                        tag_val = rule.get("suffix")
                        tags_copy.update({"suffix": tag_val})
                        logging.info(f"File marked with suffix:{tag_val} tag")

                # Copy fellow files
                rel_path = self.build_path(tags_copy)
                if not rel_path:
                    logging.info("Unable to build destination path for file")
                    continue
                new_path = os.path.join(rules.get("destination"), rel_path)
                logging.info(f"Target destination path is {new_path}")
                utils.copy(fellow, new_path, overwrite)
                logging.info("Moved file to target")

    def __repr__(self):
        return f"<Specification name={self.name}>"


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
