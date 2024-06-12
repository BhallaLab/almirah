"""Define the specification for the dataset."""

import re
import os
import logging
import pandas as pd

from string import Formatter

from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from sqlalchemy_json import NestedMutableJson

from .core import Base
from .core import uniquify
from .indexer import index

from .utils.gen import copy
from .utils.gen import filename
from .utils.gen import read_yaml
from .utils.gen import get_dir_contents


_TAG_PATTERN_TEMPLATE = re.compile(
    r"({([\w\d]*?)(?:<([^>]+)>)?(?:\|((?:\.?[\w])+))?\})"
)


@uniquify(index)
class Specification(Base):
    """Generic specification representation."""

    __tablename__ = "specifications"
    __identifier_attrs__ = {"name"}

    name: Mapped[str] = mapped_column(primary_key=True, nullable=False)
    details: Mapped[list[str]] = mapped_column(NestedMutableJson, nullable=False)

    def __init__(self, *, name, details):
        self.name = name
        self.details = details

    def build_path(self, strict=True, **tags):
        """
        Construct path given a set of tags.

        Parameters
        ----------
        strict : bool
            If True, the tags provided should exactly match the
            requirements. If False, extra tags are ignored and the
            first matching path is built.

        tags : key, value mappings
            name:value tag pairs used for path building.

        Returns
        -------
        path : str
            The constructed path if successful, else `None`.
        """
        path_patterns = self.details.get("path_patterns")
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
            matches = _TAG_PATTERN_TEMPLATE.findall(pattern)

            # Do not tamper with tags provided so that
            # it can be used for other patterns
            tags_copy = tags.copy()

            # Skip if strict set and all tags not matched
            if strict and set(tags_copy.keys()) - set([t[1] for t in matches]):
                continue

            # Validate and fill in missing tags with default value
            for subpat, name, valid_vals, default in matches:
                valid = [v for v in valid_vals.split("|")]

                if valid and name in tags_copy and tags_copy[name] not in valid:
                    continue

                if name not in tags_copy and default:
                    tags_copy[name] = default

                if valid and default and default not in valid:
                    raise ValueError(f"Inconsistent default in pattern {subpat}")

                # Simplify path
                path = path.replace(subpat, "{%s}" % name)

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

    @staticmethod
    def create_from_file(path):
        """Create Specification from yaml file."""
        n, d = filename(path), read_yaml(path)
        spec = Specification(name=n, details=d)
        index.add(spec)
        return spec

    def extract_tags(self, path):
        """Return tag:value pairs based on file path."""
        t = {}
        for tag in self.details.get("tags"):
            val = re.findall(tag["pattern"], path)
            if val:
                t[tag["name"]] = val[0]
        return t

    @classmethod
    def get(cls, **identifiers):
        d = identifiers.pop("details", None)
        obj = index.get(cls, **identifiers)

        if obj and d and obj.details != d:
            return None

        return obj

    def organize(self, rules):
        """
        Create organized copy of source directories based on defined rules.

        Parameters
        ----------
        rules : dict
            Dictionary describing instructions for organizing.
        """

        # Check for required keys
        for mandatory_key in [
            "source",
            "destination",
            "pattern",
            "tag_rules",
        ]:
            if mandatory_key not in rules:
                raise KeyError(f"Expected '{mandatory_key}' key in rule.")

        src = rules.get("source")
        dst = rules.get("destination")
        logging.info(f"Organizing {src} based on {self.name} -> {dst}")

        overwrite = rules.get("overwrite", False)
        if overwrite:
            logging.warning("Overwrite set: Existing files will be overwritten")

        add = rules.get("add", None)
        for a in add or []:
            logging.info(f"File {a['path']} will be added as {a['position']}.")

        logging.debug(f"Matching contents with pattern {rules.get('pattern')}")

        # Organize files matching pattern using rules
        matches = get_dir_contents(src, rules["pattern"], rules.get("skip", None))
        for file in matches or []:
            logging.info(f"Found match with file {file}")

            # Extract tags for file
            tags = {}
            for rule in rules.get("tag_rules"):
                tag_name = rule.get("name")
                logging.debug(f"Foraging for {tag_name} tag")

                if "value" in rule:
                    val = rule.get("value")
                    tags[tag_name] = val
                    logging.debug(f"Setting tag with {val}")
                else:
                    match = re.findall(rule.get("pattern"), file)
                    if match and len(match) != 1:
                        logging.warning("Expected single match, found more.")

                    # Choose last match always
                    val = match[-1] if match else None
                    logging.debug(f"Matching with pattern yields {val}")

                    if "prepend" in rule and val:
                        val = "".join([str(rule.get("prepend")), val])
                        logging.debug(f"Prepending tag value to get {val}")

                    if "length" in rule and val and len(val) != rule.get("length"):
                        if "iffy_prepend" in rule:
                            logging.debug("Insufficient length, prepending")
                            val = "".join([str(rule.get("iffy_prepend")), val])

                        if len(val) != rule.get("length"):
                            logging.debug("Tag value of insufficient length")
                            val = None

                    if "pad" in rule and val:
                        pad_args = rule["pad"]
                        val = val.rjust(pad_args["length"], str(pad_args["character"]))

                    if c := rule.get("case") in ["lower", "upper"] and val:
                        val = val.lower() if c == "lower" else val.upper()

                    if "default" in rule and not val:
                        val = rule.get("default")
                        logging.debug(f"Using default value of {val} for tag")

                    if "padding" in rule and val:
                        pad = rule.get("padding")

                        # Set defaults
                        direction = (pad.get("direction", "left"),)
                        char = (pad.get("char", "0"),)
                        length = pad["length"]

                        if direction == "left":
                            val.rjust(length, char)

                        elif direction == "right":
                            val.ljust(length, char)

                    if "replace" in rule and val:
                        rep = rule.get("replace")
                        col, with_, from_ = [rep[x] for x in ["col", "with", "from"]]
                        logging.info(f"File {from_} will be used to map tag values")
                        mapping = pd.read_csv(from_, dtype=str)

                        # TODO: Modularize below code snippet
                        m = mapping.where(mapping[col] == val).dropna()

                        if len(m) == 0:
                            logging.error(f"No mapping found for {val}")
                            continue

                        if len(m) > 1:
                            logging.error(f"Expected unique map for {val}, found many")
                            continue

                        val = m[with_].values[0]

                    if not val:
                        logging.error(f"Value for {tag_name} tag not found in {file}.")

                logging.info(f"File marked with {tag_name}:{val} tag")
                tags.update({tag_name: val})

            # Warning, clunky code ahead. To be made better
            rel_path = self.build_path(**tags)
            if not rel_path:
                logging.error("Unable to build destination path for file")
                continue

            new_path = os.path.join(dst, rel_path)
            logging.info(f"Target destination path is {new_path}")
            copy(file, new_path, overwrite)
            logging.info("Moved file to target")

            if add:
                for addition in add:
                    if addition["position"] == "content":
                        addition_path = os.path.join(
                            new_path, os.path.basename(addition["path"])
                        )
                    elif addition["position"] == "fellow":
                        addition_path = os.path.join(
                            os.path.dirname(new_path), addition["path"]
                        )
                    else:
                        raise ValueError(
                            "Expected position to be either content or fellow"
                        )
                    copy(addition["path"], addition_path, overwrite)
                    logging.info(f"Added addition at {addition_path}")

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
                rel_path = self.build_path(**tags_copy)
                if not rel_path:
                    logging.error(f"Unable to build destination path for file {file}")
                    continue
                new_path = os.path.join(dst, rel_path)
                logging.info(f"Target destination path is {new_path}")
                copy(fellow, new_path, overwrite)

    @property
    def tags(self):
        """Return list of tags defined in the specification."""
        return [t.get("name") for t in self.details.get("tags")]

    def validate_path(self, path):
        """Return True if path is valid according to specification."""
        tags = self.extract_tags(path)
        if self.build_path(**tags) == path:
            return True
        return False

    def __repr__(self):
        return f"<Specification name: '{self.name}'>"
