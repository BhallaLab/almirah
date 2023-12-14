"""Model classes to represent the dataset."""

import os
from itertools import chain
from abc import ABC, abstractmethod

from .layout import Layout


class Dataset(ABC):
    """Representation of a dataset.

    Attributes
    ----------
    layout_names : list of str
        Name of all the layouts in the dataset.

    Parameters
    ----------
    layouts : list of Layout
        All layouts under the dataset.
    """

    def __init__(self, layouts=list()):
        self.layouts = layouts
        self.layout_names = None
        self._update_layout_names()

    @abstractmethod
    def _build_initialiser_args(root):
        ...

    @classmethod
    def _build_dataset(cls, args):
        return cls(args)

    @classmethod
    def build_from_root(cls, root, indexer=None):
        """Build dataset with the directory provided as root."""
        if not os.path.exists(root):
            print("Path does not exist")
            return
        args = cls._build_initialiser_args(root, indexer)
        return cls._build_dataset(args)

    def add_layout(self, layout):
        """Add a layout to the dataset."""
        if layout.root in [r.root for r in self.layouts]:
            print("Layout already part of dataset")
            return
        self.layouts.append(layout)
        self._update_layout_names()

    def get_files(self, **filters):
        """Return files that match criteria."""
        files = list()
        for lay in self.layouts:
            files.extend(lay.get_files(filters))
        return files

    def _update_layout_names(self):
        self.layout_names = [lay.name for lay in self.layouts] if self.layouts else None

    def __repr__(self):
        classname = self.__class__.__name__
        if not self.layout_names:
            return f"<{classname} layouts='empty'>"
        elif len(self.layout_names) < 4:
            return f"<{classname} layouts={self.layout_names}>"
        else:
            return f"<{classname} layouts=[{self.layout_names[0]}...{self.layout_names[-1]}]>"


class SourceDatasets(Dataset):
    """Representation of the collection of sources."""

    def _build_initialiser_args(root, indexer):
        return [
            Layout(r.path, name=r.name, indexer=indexer)
            for r in os.scandir(root)
            if r.is_dir()
        ]


class DerivativeDatasets(Dataset):
    """Representation of the collection of derivatives."""

    def _build_initialiser_args(root, indexer):
        return [
            Layout(r.path, name=r.name, indexer=indexer)
            for r in os.scandir(root)
            if r.is_dir()
        ]


class CompleteDataset(Dataset):
    """Representation of the complete dataset.

    Attributes
    ----------
    layout_names : list of str
        Name of all the layouts in the dataset.

    Parameters
    ----------
    primary : Layout
        Layout of clean and curated data in dataset.
    sourcedata : SourceDatasets or list of Layout
        Sources for the primary.
    derivatives : DerivativeDatasets or list of Layout
        Data derived from primary.
    """

    def __init__(self, primary, sourcedata=None, derivatives=None):
        if isinstance(sourcedata, list):
            sourcedata = SourceDatasets(sourcedata)

        if isinstance(derivatives, list):
            derivatives = DerivativeDatasets(derivatives)

        self.primary = primary
        self.sourcedata = sourcedata
        self.derivatives = derivatives
        self._update_layouts()

    def _build_initialiser_args(root, indexer):
        return (
            Layout(root, name=os.path.basename(root), indexer=indexer),
            SourceDatasets.build_from_root(
                os.path.join(root, "sourcedata"), indexer=indexer
            ),
            DerivativeDatasets.build_from_root(
                os.path.join(root, "derivatives"), indexer=indexer
            ),
        )

    def _build_dataset(args):
        return CompleteDataset(*args)

    def _update_layouts(self):
        """Update list of layouts under dataset."""
        primary_list = [self.primary]
        self.layouts = list(
            chain(
                primary_list,
                self.sourcedata.layouts,
                self.derivatives.layouts,
            )
        )
        self.layout_names = None
        self._update_layout_names()

    def add_derivative(self, layout):
        """Add a derivative to the dataset."""
        self.derivatives.add_layout(layout)
        self._update_layouts()

    def add_source(self, layout):
        """Add a source to the dataset."""
        self.sourcedata.add_layout(layout)
        self._update_layouts()
