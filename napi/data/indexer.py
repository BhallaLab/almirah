"""Indexing functionality for metadata search and filtering."""

import os
import logging

from sqlalchemy import select
from sqlalchemy import func
from sqlalchemy import tuple_

from .layout import Base, File, Tag
from ..db import DBManager


class Indexer:
    """Index files in a Layout."""

    def __init__(self, db_manager=None):
        self.db = db_manager if db_manager else DBManager()
        Base.metadata.create_all(self.db.engine)

    def __call__(self, layout, valid_only=True):
        logging.info(f"Indexing layout with root {layout.root}")
        self.layout = layout
        self.valid_only = valid_only
        self._index_dir(self.layout.root)

    def _merge(self, obj):
        return self.db.session.merge(obj)

    def _index_dir(self, dir):
        """Iteratively index all directories in layout."""
        logging.info(f"Indexing directory {dir}")
        SKIP_DIRS = ["sourcedata", "derivatives"]
        for content in os.listdir(dir):
            if content in SKIP_DIRS:
                logging.info(f"Skipping content {content}")
                continue

            path = os.path.join(dir, content)
            if not (self._index_file(path) and self.valid_only) and os.path.isdir(path):
                self._index_dir(path)

        self.db.session.commit()

    def _index_file(self, path):
        """Add valid files to index and return true if successful."""
        logging.info(f"Indexing file at {path}")
        file = File(path, self.layout.root)
        if self.valid_only and not self.layout.spec.validate(
            os.path.join(self.layout.prefix, file.rel_path)
        ):
            logging.info("Skipping invalid file")
            return False
        file = self._merge(file)
        self.layout.files.append(file)
        self._index_tags(file)
        self.add(file)
        return True

    def _index_tags(self, file):
        """Add tags of file to index."""
        logging.info("Adding file tags")
        file.add_tag_from_func("is_dir", os.path.isdir)
        tags = self.layout.spec.extract_tags(file.rel_path)
        file.add_tags(**tags)

    def _tags_filter(self, **filters):
        # Unpack filters dict to tuple
        tag_reqs = [(name, value) for name, value in filters.items()]
        logging.debug(f"Tags required: {tag_reqs}")

        # Construct table of passing file paths
        tags_filter = select(Tag.path)

        # If filters present
        if filters:
            tags_filter = (
                tags_filter.where(tuple_(Tag.name, Tag.value).in_(tag_reqs))
                .group_by(Tag.path)
                .having(func.count(Tag.name) == len(tag_reqs))
            )

        return tags_filter

    def _files_filter(self, root, **filters):
        tags_filter = self._tags_filter(**filters).subquery()

        # Build File objects from file paths
        files_filter = (
            select(File)
            .where(File.path.in_(select(tags_filter)))
            .where(File.root == root)
        )

        return files_filter

    def _tag_values(self, root, name, **filters):
        files_filter = self._files_filter(root, **filters).subquery()

        # Build Tag values from file paths
        tag_values = (
            select(Tag.value)
            .where(Tag.path.in_(select(files_filter.c.path)))
            .where(Tag.name == name)
            .distinct()
        )

        return tag_values

    def add(self, obj):
        self.db.session.add(obj)

    def get(self, cls, primary):
        """Get record as an object provided its ORM class and primary key."""
        return self.db.session.get(cls, primary)

    def run_query(self, query):
        """Run a query on db associated and return all results."""
        return self.db.session.scalars(query).all()
