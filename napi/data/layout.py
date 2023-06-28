"""Model classes to represent layouts and its components."""

import os

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base, SessionManager
from .standard import Specification


class File(Base):
    """Generic file representation."""

    __tablename__ = "files"
    path: Mapped[str] = mapped_column("path", primary_key=True)
    root: Mapped[str] = mapped_column("root", ForeignKey("layouts.root"))

    def __init__(self, path, layout):
        self.path = path
        self.layout = layout
        self.root = layout.root

    @property
    def rel_path(self):
        return os.path.relpath(self.path, self.root)

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

    def __init__(self, root, name=None, spec=None, indexer=None):
        self.root = root
        self.name = name if name else os.path.basename(root)
        self.spec = spec if spec else Specification()
        self.indexer = indexer
        self.index()

    def index(self):
        """Run indexer over the layout."""
        if not self.indexer:
            self.indexer = Indexer()
        self.indexer(self)

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

        self.conn.session.add(self.layout)
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
        file = File(path, self.layout)
        self.conn.session.add(file)
        self._index_tags(file)

    def _index_tags(self, file):
        self.conn.session.add(Tag(file.path, "is_dir", os.path.isdir(file.path)))
        tags = self.layout.spec.extract_tags(file.path)
        for name, value in tags.items():
            tag = Tag(file.path, name, value)
            self.conn.session.add(tag)
