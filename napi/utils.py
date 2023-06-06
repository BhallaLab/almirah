"""Utility functions."""

import os
import re
import shutil


def copy(src, dst):
    """Creates a copy of file."""
    if not dst:
        print(f"Failed to copy file due to missing destination: {src}")
        return
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)


def get_matching_files(root, pattern):
    """Return list of files in a directory that match pattern."""
    matches = list()
    for dir, subdir, files in os.walk(root):
        for file in files:
            if re.match(pattern, file):
                matches.append(os.path.join(dir, file))
    return matches
