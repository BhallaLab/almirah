"""Model classes to represent layouts, files, and tags."""

import os
import re

from typing import List
from typing import Dict

from datalad.api import get
from datalad.api import clone

from sqlalchemy import or_
from sqlalchemy import and_
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy import ForeignKey
from sqlalchemy import UniqueConstraint
from sqlalchemy import ForeignKeyConstraint

from sqlalchemy.orm import Mapped
from sqlalchemy.orm import relationship
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import attribute_keyed_dict

from sqlalchemy.ext.associationproxy import AssociationProxy
from sqlalchemy.ext.associationproxy import association_proxy

from .core import Base
from .core import uniquify
from .indexer import index
from .dataset import Component
from .specification import Specification

from .utils.gen import listify
from .utils.gen import denest_dict
from .utils.gen import get_metadata


@uniquify(index)
class Layout(Component):
    """Represents a structured layout of files in a directory."""

    __tablename__ = "layouts"
    __identifier_attrs__ = {"root"}

    id: Mapped[int] = mapped_column(ForeignKey("components.id"), primary_key=True)
    root: Mapped[str] = mapped_column(unique=True, nullable=False)
    url: Mapped[str] = mapped_column(unique=True, nullable=True)
    specification_name: Mapped[str] = mapped_column(ForeignKey("specifications.name"))

    specification: Mapped["Specification"] = relationship()

    files: Mapped[List["File"]] = relationship(
        back_populates="layout", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("root", "url"),
        UniqueConstraint("root", "specification_name"),
    )

    __mapper_args__ = {"polymorphic_identity": "layout"}

    def __init__(self, *, root: str, specification_name: str):
        """
        Initialize a new Layout with a root directory and a linked specification.

        Parameters
        ----------
        root : str
            The filesystem path to the root of the layout.
        specification_name : str
            The name of the specification to apply to this layout.
        """
        self.root = os.path.expanduser(root)
        self.specification_name = specification_name

    def add(self, *files: List["File"]):
        """
        Adds files to the layout, ensuring they fall within the layout's directory scope.

        Parameters
        ----------
        files : File
            One or more `File` objects to be added to the layout.

        Raises
        ------
        ValueError
            If any file is outside the layout's root directory.
        """
        if not any(f.path.startswith(self.root) for f in files):
            raise TypeError(f"Found file outside layout scope of {self.root}")
        self.files.extend(files)

    def clone(self, url=None):
        """Clone Layout from datalad url."""
        if not self.url and not url:
            raise ValueError(f"Remote url for {self} not set")

        if not self.url:
            self.url = url

        clone(source=self.url, path=self.root)

    def index(
        self,
        root=None,
        metadata=False,
        valid_only=True,
        skip=None,
        reset=False,
        **funcs,
    ):
        """Perform indexing to add files in root to index."""

        # Start from scratch if reset set
        if reset:
            self.files = []

        # If skip provided, construct regex string
        if skip:
            skip_regex = "(" + ")|(".join(skip) + ")"

        # If path not provided, index layout root
        if not root:
            root = self.root

        # Ensure path is present in layout
        if not root.startswith(self.root):
            raise ValueError(f"{root} does not belong to {self}")

        for entry in os.scandir(root):
            if skip and re.match(skip_regex, str(entry)):
                continue

            path = os.path.join(root, entry)
            rel_path = os.path.relpath(path, self.root)
            path_valid = True

            if valid_only and not self.specification.validate_path(rel_path):
                path_valid = False

            if not path_valid and entry.is_dir():
                self.index(path, metadata, valid_only, skip, reset, **funcs)

            if path_valid:
                file = File(path=path)
                self.add(file)
                file.index(metadata, reset, **funcs)

    def query(self, returns="file", **filters):
        """Return File instances that fit filter criteria."""

        if not returns:
            returns = "file"

        filters = listify(filters)

        # Combine table for consolidated view
        combine = select(File).join(Marking).join(Tag)

        # Dynamically add conditions for filtering
        conditions = [and_(Tag.name == n, Tag.value.in_(v)) for n, v in filters.items()]

        # Combine conditions using AND to find matches
        match = combine.where(File.root == self.root).where(or_(*conditions))

        # Trim down matches to only those that have all mentioned tags
        trim = match.group_by(File).having(func.count(Tag.name) == len(filters))

        # Retrieve File objects
        files = index.retrieve(trim).all()

        if returns == "file":
            return files

        elif returns == "path":
            return [f.path for f in files]

        elif returns == "rel_path":
            return [f.rel_path for f in files]

        returns = [returns] if isinstance(returns, str) else returns
        return [[f.tags.get(t) for t in returns] for f in files]

    def move_root(self, path):
        """Abstractly move Layout and its entries to path."""
        for file in self.files:
            file.path = os.path.join(path, file.rel_path)
            file.root = path

        self.root = path

    def report(self):
        """Generate report for the Layout."""
        pass

    def __repr__(self):
        return f"<Layout root: '{self.root}'>"


@uniquify(index)
class File(Base):
    """Generic file representation."""

    __tablename__ = "files"
    __identifier_attrs__ = {"path"}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    path: Mapped[str] = mapped_column(unique=True, nullable=False)
    root: Mapped[str] = mapped_column(ForeignKey("layouts.root"), nullable=True)

    _tags: Mapped[Dict[str, "Tag"]] = relationship(
        secondary="markings",
        back_populates="files",
        collection_class=attribute_keyed_dict("name"),
    )

    layout: Mapped["Layout"] = relationship()
    tags: AssociationProxy[Dict[str, str]] = association_proxy(
        "_tags", "value", creator=lambda n, v: Tag(name=n, value=v)
    )

    def __init__(self, *, path):
        self.path = os.path.expanduser(path)

    @property
    def attached(self):
        return True if self.layout else False

    @property
    def rel_path(self):
        if not self.attached:
            raise TypeError(f"{self} not attached to a Layout")
        return os.path.relpath(self.path, self.root)

    def download(self):
        """Download file from remote dataset."""

        if not self.attached:
            raise TypeError(f"{self} not attached to a Layout")

        if not self.layout.url:
            raise ValueError(f"Remote url for {self.layout} not set")

        get(self.path, dataset=self.layout.root)

    def index(self, metadata=False, reset=False, **funcs):
        """Perform indexing to add tags marking the file to index."""

        # Start from scratch if reset set
        if reset:
            self.tags = {}

        if metadata:
            meta = get_metadata(self.path)
            meta = denest_dict(meta)
            self.tags.update(meta)

        if self.attached:
            t = self.layout.specification.extract_tags(self.rel_path)
            self.tags.update(t)

        t = {n: f(self.path) for n, f in funcs.items()}
        self.tags.update(t)

    def report(self):
        """Generate report for the File."""
        pass

    def __repr__(self):
        return f"<File path: '{self.path}'>"


@uniquify(index)
class Tag(Base):
    """Generic tag representation."""

    __tablename__ = "tags"
    __identifier_attrs__ = {"name", "value"}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(nullable=False)
    value: Mapped[str] = mapped_column(nullable=False)

    files: Mapped[List["File"]] = relationship(
        secondary="markings", back_populates="_tags"
    )

    __table_args__ = (UniqueConstraint("name", "value"),)

    def __init__(self, *, name, value):
        self.name, self.value = name, value

    def __repr__(self):
        return f"<Tag {self.name}: '{self.value}'>"


class Marking(Base):
    """Representation of an association between a file and a tag."""

    __tablename__ = "markings"

    file_id: Mapped[int] = mapped_column(ForeignKey("files.id"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)

    __table_args__ = (
        UniqueConstraint("file_id", "name"),
        ForeignKeyConstraint([tag_id, name], [Tag.id, Tag.name]),
    )

    def __repr__(self):
        return f"<Marking file: {self.file_id} tag: {self.tag_id}>"
