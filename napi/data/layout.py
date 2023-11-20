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


class Tag(Base):
    """Generic tag representation."""

    __tablename__ = "tags"
    path: Mapped[str] = mapped_column(
        "path", ForeignKey("files.path"), primary_key=True
    )
    name: Mapped[str] = mapped_column("name", primary_key=True)
    value: Mapped[str] = mapped_column("value")

    file: Mapped["File"] = relationship(back_populates="tags")

    def __init__(self, path, name, value):
        self.path = path
        self.name = name
        self.value = value

    @staticmethod
    def boolean_tag(file, name, func):
        """Add a boolean tag to file based on func return value."""
        tag = Tag(file.path, name, func(file.path))
        file.tags[name] = tag

    def __repr__(self):
        return f"<Tag {self.name}:'{self.value}'>"


class File(Base):
    """Generic file representation."""

    __tablename__ = "files"
    path: Mapped[str] = mapped_column("path", primary_key=True)
    root: Mapped[str] = mapped_column("root", ForeignKey("layouts.root"))

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

    def build_modified_path(self, changes):
        "Returns the path for file given changes to tags."
        valid_tags = self.layout.spec.get_valid_tags()
        t = {n: t.value for n, t in self.tags.items() if n in valid_tags}
        t.update(changes)
        return self.layout.spec.build_path(t)

    def __repr__(self):
        return f"<File path='{self.rel_path}'>"


class Layout(Base):
    """Representation of file collection in a directory."""

    __tablename__ = "layouts"
    root: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]

    files: Mapped[List["File"]] = relationship(
        back_populates="layout", cascade="all, delete-orphan"
    )

    def __init__(self, root, name=None):
        self.root = root
        self.name = name if name else os.path.basename(root)

    @reconstructor
    def _init_on_load(self):
        self.kind = self._decipher_kind()
        self.prefix = self._decipher_prefix()

    def _decipher_kind(self):
        for k in ["sourcedata", "derivatives"]:
            if k in self.root:
                return k
        return "primary"

    def _decipher_prefix(self):
        return self.root[p:] if (p := self.root.rfind(self.kind)) != -1 else ""

    @staticmethod
    def create(
        root,
        name=None,
        spec=None,
        indexer=None,
        reindex=False,
        valid_only=True,
    ):
        """Factory method for Layout."""

        from .indexer import Indexer

        indexer = indexer if indexer else Indexer()

        logging.info("Loading existing info if any on layout")
        lay = indexer._merge(Layout(root, name))
        lay._init_on_load()

        # Set support classes
        lay.indexer = indexer
        lay.spec = spec if spec else Specification()
        indexer.add(lay)

        if reindex or not inspect(lay).persistent:
            indexer(lay, valid_only)

        return lay

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

    def __repr__(self):
        return f"<Layout root='{self.root}'>"
