"""Model classes to represent layouts and its components."""

import os

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base, SessionManager


class File(Base):
    """Generic file representation."""

    __tablename__ = "files"
    _path: Mapped[str] = mapped_column("path", primary_key=True)
    _root: Mapped[str] = mapped_column("root", ForeignKey("layouts.root"))

    def __init__(self, path, layout):
        self._path = path
        self._layout = layout
        self._root = layout.root

    def __repr__(self):
        return f"<File path={self.path}>"


class Layout(Base):
    """Representation of the file layout in the directory."""

    __tablename__ = "layouts"
    root: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]

    def __init__(self, root, name=None, indexer=None):
        self.root = root
        self.name = name if name else os.path.basename(root)
        self._indexer = indexer
        self.index()

    def index(self):
        """Run indexer over the layout."""
        if not self._indexer:
            self._indexer = Indexer()
        self._indexer(self)

    def __repr__(self):
        return f"<Layout root='{self.root}'>"


class Indexer:
    """Index files in a Layout."""

    def __init__(self, session_manager=None):
        self._conn = session_manager

    def __call__(self, layout):
        self._layout = layout
        if not self._conn:
            self._conn = SessionManager()

        self._conn.session.add(self._layout)
        self._index_dir(self._layout.root)

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
        self._conn.session.commit()

    def _index_file(self, path):
        file = File(path, self._layout)
        self._conn.session.add(file)
