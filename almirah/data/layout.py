"""Model classes to represent layouts and its components."""

import os
import logging

from typing import List
from typing import Dict

from sqlalchemy import inspect
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import relationship
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import reconstructor
from sqlalchemy.orm import attribute_keyed_dict
from sqlalchemy.orm import DeclarativeBase

from .specification import Specification

__all__ = ["Tag", "File", "Layout"]


class Base(DeclarativeBase):
    """Represents base object of ORM."""

    @classmethod
    def get_existing(cls, *primary, indexer):
        """Returns existing record as ORM object if present."""

        obj = indexer.get(cls, primary)
        return obj


class Tag(Base):
    """Generic tag representation."""

    __tablename__ = "tags"

    path: Mapped[str] = mapped_column(ForeignKey("files.path"), primary_key=True)
    name: Mapped[str] = mapped_column(primary_key=True)
    value: Mapped[str]

    files: Mapped["File"] = relationship(back_populates="tags")

    def __init__(self, path, name, value):
        self.path = path
        self.name = name
        self.value = value

    def __repr__(self):
        return f"<Tag {self.name}:'{self.value}'>"


class File(Base):
    """Generic file representation."""

    __tablename__ = "files"

    path: Mapped[str] = mapped_column(primary_key=True)
    root: Mapped[str] = mapped_column(ForeignKey("layouts.root"))

    layout: Mapped["Layout"] = relationship(back_populates="files")
    tags: Mapped[Dict[str, "Tag"]] = relationship(
        collection_class=attribute_keyed_dict("name"),
        cascade="all, delete-orphan",
    )

    def __init__(self, path, root):
        self.path = path
        self.root = root

    @property
    def rel_path(self):
        r = os.path.relpath(self.path, self.root)
        r = os.path.join(self.layout.prefix, r) if self.layout else r
        return r

    def add_tag(self, name, value):
        """Add a tag to file."""
        self.tags[name] = Tag(self.path, name, value)

    def add_tags(self, **tags):
        """Add tags to file. If tag present, value is updated."""
        for name, value in tags.items():
            self.add_tag(name, value)

    def add_tag_from_func(self, name, func):
        """Add a tag to the file based on func return value."""
        self.tags[name] = Tag(self.path, name, func(self.path))

    def build_path(self):
        """Build path based on tags associated with file."""
        t = self.get_tags()
        return self.layout.spec.build_path(t)

    def build_modified_path(self, **changes):
        "Returns the path for file given changes to tags."
        tags = self.get_tags()
        tags.update(changes)
        return self.layout.spec.build_path(tags)

    def get(self):
        """Get file from remote dataset."""
        from datalad import api

        api.get(self.path, dataset=self.root)

    def get_tags(self):
        """Returns tags associated with the file."""
        return {n: t.value for n, t in self.tags.items()}

    def __repr__(self):
        return f"<File path='{self.rel_path}'>"


class Layout(Base):
    """Representation of file collection in a directory."""

    __tablename__ = "layouts"

    root: Mapped[str] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(nullable=True)

    files: Mapped[List["File"]] = relationship(
        back_populates="layout", cascade="all, delete-orphan"
    )

    def __init__(self, root, url):
        self.root = root
        self.url = url

    @reconstructor
    def _init_on_load(self):
        self.kind = self._decipher_kind()
        self.prefix = self._decipher_prefix()

    @staticmethod
    def _get_indexer(indexer):
        from .indexer import Indexer

        if not indexer:
            indexer = Indexer()
        return indexer

    def _decipher_kind(self):
        for k in ["sourcedata", "derivatives"]:
            if k in self.root:
                return k
        return "primary"

    def _decipher_prefix(self):
        return self.root[p:] if (p := self.root.rfind(self.kind)) != -1 else ""

    def _setup_support(self, indexer, specification):
        self.indexer = indexer
        self.spec = specification

    @staticmethod
    def create(
        root,
        url=None,
        indexer=None,
        spec=Specification(),
        reindex=False,
        valid_only=True,
        from_url=False,
    ):
        """Factory method for Layout.

        Parameters
        ----------
        root : str
            Path of root directory of data.

        url : str
            Datalad supported URL for remote residence.

        indexer : almirah.Indexer
            db to use for indexing.

        spec : almirah.Specification
            Specification to apply.

        reindex : bool, default False
            If True, force reindexing of Layout.

        valid_only : bool, default True
            If False, all contents of indexed irrespective of spec abidance.

        from_url : bool, default False
            If True, clone data from url to populate layout.

        Returns
        -------
        layout: almirah.Layout
            If layout has already been indexed before, a reference to
            the indexed Layout is returned. Else, a new Layout
            instance is indexed and returned.

        """

        indexer = Layout._get_indexer(indexer)
        layout = Layout.get_existing(root, indexer=indexer)

        if not layout:
            layout = Layout(root, url)
            layout._init_on_load()

        layout._setup_support(indexer, spec)
        indexer.add(layout)

        if from_url:
            layout.clone_from_url()

        if reindex or not inspect(layout).persistent:
            layout.reindex(valid_only)

        return layout

    def clone_from_url(self):
        """Clone layout from a datalad url."""

        from datalad import api

        api.clone(source=self.url, path=self.root)
        logging.info(f"Cloning layout from {self.url}")

    def get_files(self, **filters):
        """Return files that match criteria."""
        files_filter = self.indexer._files_filter(self.root, **filters)
        files = self.indexer.run_query(files_filter)
        return files

    def get_tag_values(self, name, **filters):
        """Return all values available for a tag name."""
        tag_values = self.indexer._tag_values(self.root, name, **filters)
        values = self.indexer.run_query(tag_values)
        return values

    def reindex(self, valid_only=True):
        """Reindex layout to include additions to the layout."""
        logging.info(f"Reindexing {self}")
        self.indexer(self, valid_only)

    def __repr__(self):
        return f"<Layout root='{self.root}'>"
