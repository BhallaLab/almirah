"""Utility functions."""

import os
import re
import yaml
import shutil
import logging
import subprocess


def copy(src, dst, overwrite=False):
    """Copies from source to destination."""
    if not dst:
        raise TypeError("Expected destination path, received None")

    if os.path.exists(dst):
        if not overwrite:
            logging.warning("Skipping copy as file exists")
            return
        if overwrite:
            logging.warning("Overwriting existing file")
            remover = shutil.rmtree if os.path.isdir(dst) else os.remove
            remover(dst)

    os.makedirs(os.path.dirname(dst), exist_ok=True)
    copier = shutil.copytree if os.path.isdir(src) else shutil.copy2
    copier(src, dst)


def get_dir_contents(root, pattern, skip=None):
    """Return list of contents in a directory that match pattern."""
    m = []
    for dir, subdirs, files in os.walk(root):
        contents = subdirs + files
        for content in contents:
            if re.match(pattern, content):
                m.append(os.path.join(dir, content))
    matches = [c for c in m if not any([re.search(s, c) for s in skip or []])]
    return matches


def read_yaml(path):
    """Return dict equivalent of yaml file."""
    with open(path) as f:
        content = yaml.load(f, yaml.SafeLoader)
        return content


def read_yamls(path):
    """Returns list of dict equivalents of yamls in a file."""
    with open(path) as f:
        content = yaml.load_all(f, yaml.SafeLoader)
        return list(content)


def run_shell(cmd, suppress_output=True):
    """Execute shell command in background."""
    sp = subprocess.run(cmd, shell=True)
    return sp

def get_dtype(dtype, default_length=250):
    """Returns supported dtype and length from provided dtype string."""

    SUPPORTED_DTYPES = {"boolean", "datetime", "float", "integer", "str"}

    dtype, length = re.match(r"(\w+).?(\d+)?", dtype).groups()

    if dtype not in SUPPORTED_DTYPES:
        raise TypeError(f"Unsupported dtype {dtype} encountered")

    if length and dtype != "str":
        raise ValueError(f"Expected zero, but received arg for dtype {dtype}")

    if not length and dtype == "str":
        length = default_length

    length = int(length) if length else None
    return dtype, length
