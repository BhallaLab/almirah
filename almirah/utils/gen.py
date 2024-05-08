"""General-purpose utility functions."""

import os
import re
import json
import yaml
import shutil
import logging
import subprocess

from pathlib import Path
from functools import reduce

from typing import Any
from typing import List
from typing import Dict


def commafy(sequence: List[Any]) -> str:
    """Return the comma separated string version of a sequence."""
    return ", ".join(map(str, sequence))


def copy(src: str, dst: str, overwrite: bool = False) -> None:
    """Copy content from source path to destination path."""

    if not os.path.exists(src):
        raise FileNotFoundError(f"No file found on {src}")

    if not dst:
        raise TypeError("Expected destination path, received None")

    if os.path.exists(dst) and not overwrite:
        logging.error(f"Skipping copy of {src} to {dst} as file exists")
        return

    if os.path.exists(dst) and overwrite:
        logging.warning(f"Overwriting and copying {src} to {dst}")
        remover = shutil.rmtree if os.path.isdir(dst) else os.remove
        remover(dst)

    logging.debug(f"Initiating copy of {src} to {dst}")
    copier = shutil.copytree if os.path.isdir(src) else shutil.copy2
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    copier(src, dst)


def deep_get(dictionary: Dict[Any, Any], keys: str, default: Any = None) -> Any:
    """dict.get() for nested dictionaries."""
    return reduce(
        lambda d, key: d.get(key, default) if isinstance(d, dict) else default,
        keys.split("."),
        dictionary,
    )


def denest_dict(dictionary: Dict[Any, Any]) -> Dict[Any, Any]:
    """Return denested dict with all nested elements removed."""
    return {k: v for k, v in dictionary.items() if not isinstance(v, dict)}


def filename(path: str) -> str:
    """Return the filename without extension given the path."""
    return os.path.splitext(os.path.basename(os.path.expanduser(path)))[0]


def get_dir_contents(root: str, pattern: str, skip: List[str] = None) -> List[str]:
    """Return list of contents in a directory that match pattern."""
    m = []
    for dir, subdirs, files in os.walk(root):
        contents = subdirs + files
        for content in contents:
            if re.match(pattern, content):
                m.append(os.path.join(dir, content))
    matches = [c for c in m if not any([re.search(s, c) for s in skip or []])]
    return matches


def get_incomplete_keys(dict: Dict[Any, Any]) -> List[Any]:
    """Return keys whose value are None."""
    return [k for k, v in dict.items() if v is None]


def get_metadata(path: str) -> Dict[str, Any]:
    """Return dict equivalent of json in file."""
    path = Path(path).with_suffix(".json")

    if not path.exists:
        return dict()

    with open(path) as file:
        content = json.load(file)
        return content


def listify(dictionary: dict) -> Dict[str, List]:
    """Return dict with value type always List."""
    return {
        k: v if isinstance(v, (list, tuple)) else [v] for k, v in dictionary.items()
    }


def read_yaml(path: str) -> Dict[Any, Any]:
    """Return dict equivalent of yaml in file."""
    with open(os.path.expanduser(path)) as file:
        return yaml.safe_load(file)


def read_multi_yaml(path: str) -> List[Dict[Any, Any]]:
    """Return list of dict equivalents of yamls in file."""
    with open(os.path.expanduser(path)) as file:
        return [f for f in yaml.safe_load_all(file)]


def run_shell(cmd: str, suppress_output: bool = True) -> subprocess.CompletedProcess:
    """Execute shell command in background."""
    return subprocess.run(
        cmd, shell=True, stdout=subprocess.DEVNULL if suppress_output else None
    )
