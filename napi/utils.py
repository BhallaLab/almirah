"""Utility functions."""

import os
import re
import yaml
import shutil
import subprocess


def copy(src, dst):
    """Copies from source to destination."""
    if not dst:
        raise TypeError("Expected destination path, received None")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.isdir(src):
        shutil.copytree(src, dst)
    else:
        shutil.copy2(src, dst)


def get_matches(root, pattern):
    """Return list of contents in a directory that match pattern."""
    matches = list()
    for dir, subdirs, files in os.walk(root):
        contents = subdirs + files
        for content in contents:
            if re.match(pattern, content):
                matches.append(os.path.join(dir, content))
    return matches


def read_yaml(path):
    """Return dict equivalent of yaml file."""
    with open(path) as f:
        content = yaml.load(f, yaml.SafeLoader)
        return content


def run_shell(cmd, suppress_output=True):
    """Execute shell command in background."""
    sp = subprocess.run(cmd)
    return sp
