"""Model classes to represent layouts and its components."""

import os

from typing import List

from sqlalchemy import select
from sqlalchemy import func
from sqlalchemy import tuple_
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import relationship
from sqlalchemy.orm import mapped_column

from .db import Base, SessionManager
from .standard import Specification


class File(Base):
    """Generic file representation."""

    __tablename__ = "files"
    path: Mapped[str] = mapped_column("path", primary_key=True)
    root: Mapped[str] = mapped_column("root", ForeignKey("layouts.root"))

    layout: Mapped["Layout"] = relationship(back_populates="files")
    tags: Mapped[List["Tag"]] = relationship(
        back_populates="file", cascade="all, delete-orphan"
    )

    def __init__(self, path, root):
        self.path = path
        self.root = root

    @property
    def rel_path(self):
        return os.path.relpath(self.path, self.layout.root)

    def __repr__(self):
        return f"<File path={self.rel_path}>"


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

    def __repr__(self):
        return f"<Tag {self.name}: '{self.value}'>"


class Layout(Base):
    """Representation of the file layout in the directory."""

    __tablename__ = "layouts"
    root: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]

    files: Mapped[List["File"]] = relationship(back_populates="layout")

    def __init__(self, root, name=None, spec=None, indexer=None, index_layout=True):
        self.root = root
        self.name = name if name else os.path.basename(root)
        self.spec = spec if spec else Specification()
        self.indexer = indexer
        if index_layout:
            self.index()

    def index(self):
        """Run indexer over the layout."""
        if not self.indexer:
            self.indexer = Indexer()
        self.indexer(self)

    def get_files(self, **filters):
        """Return files that match criteria."""

        # TODO: warn if keys not present.

        # unpack filters dict into tuple
        tag_reqs = [(name, value) for name, value in filters.items()]

        # Construct table of passing file paths
        tag_filter = (
            select(Tag.path)
            .where(tuple_(Tag.name, Tag.value).in_(tag_reqs))
            .group_by(Tag.path)
            .having(func.count(Tag.name) == len(tag_reqs))
            .subquery()
        )

        # Build File objects from file paths
        file_filter = (
            select(File)
            .where(File.path.in_(select(tag_filter)))
            .where(File.root == self.root)
        )

        res = self.indexer.get(file_filter)
        files = [r for r, in res]
        return files

    def __repr__(self):
        return f"<Layout root='{self.root}'>"


class Indexer:
    """Index files in a Layout."""

    def __init__(self, session_manager=None):
        self.conn = session_manager

    def __call__(self, layout):
        self.layout = layout
        if not self.conn:
            self.conn = SessionManager()
        self._index_dir(self.layout.root)

    def _index_dir(self, dir):
        SKIP_DIRS = ["sourcedata", "derivatives"]
        for content in os.listdir(dir):
            if content in SKIP_DIRS:
                continue

            path = os.path.join(dir, content)
            if os.path.isdir(path):
                self._index_dir(path)

            self._index_file(path)
        # TODO: Ignore if entry already present or upsert
        self.conn.session.commit()

    def _index_file(self, path):
        file = File(path, self.layout.root)
        self.layout.files.append(file)
        self._index_tags(file)
        self.conn.session.add(file)

    def _index_tags(self, file):
        is_dir_tag = Tag(file.path, "is_dir", os.path.isdir(file.path))
        file.tags.append(is_dir_tag)
        tags = self.layout.spec.extract_tags(file.path)
        for name, value in tags.items():
            tag = Tag(file.path, name, value)
            file.tags.append(tag)

    def get(self, query):
        """Run a query on db associated and return all results."""
        res = self.conn.session.execute(query).all()
        return res
