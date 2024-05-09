""" Model classes to represent a dataset and its components."""

import pandas as pd

from typing import List
from typing import Optional

from sqlalchemy import ForeignKey

from sqlalchemy.orm import Mapped
from sqlalchemy.orm import relationship
from sqlalchemy.orm import mapped_column

from .core import Base
from .core import uniquify
from .indexer import index


class Component(Base):
    """Generic component representation within the dataset architecture."""

    __tablename__ = "components"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    type: Mapped[str]

    __mapper_args__ = {"polymorphic_identity": "component", "polymorphic_on": "type"}

    def __repr__(self) -> str:
        return f"<Component id: '{self.id}' type: '{self.type}'>"


@uniquify(index)
class Dataset(Component):
    """Represents a collection of components as a dataset."""

    __tablename__ = "datasets"
    __identifier_attrs__ = {"name"}

    id: Mapped[int] = mapped_column(ForeignKey("components.id"), primary_key=True)
    name: Mapped[str] = mapped_column(unique=True, nullable=False)
    components: Mapped[List["Component"]] = relationship(secondary="collections")

    __mapper_args__ = {"polymorphic_identity": "dataset"}

    def __init__(self, *, name: str) -> None:
        self.name = name

    def add(self, *components: Component) -> None:
        """
        Adds components to the dataset.

        Parameters
        ----------
        components : Component
            `Component` instances to be added to the dataset.

        Raises
        ------
        TypeError
            If a dataset is added to itself or circular references are detected.
        """
        if any(c == self or self in getattr(c, "components", []) for c in components):
            raise TypeError("Dataset cannot include itself as a component")

        self.components.extend(components)

    def index(self, **kwargs):
        """Perform indexing on components."""

        for c in self.components:
            if index := callable(getattr(c, "index")):
                index(c, **kwargs)

    def report(self) -> None:
        """Generate report for dataset."""
        print(f"Components of {self}:")

        for c in self.components:
            print("{!r:5}".format(c))

        for c in self.components:
            c.report()

    def query(self, returns: Optional[List[str]] = None, **filters) -> List:
        """
        Query components based on filter criteria.

        Parameters
        ----------
        returns : list of str, optional
            Specific fields to return, defaults to all or object if None.
        filters : dict
            Filter conditions to apply on the query.

        Returns
        -------
        list
            List of components or queried data meeting the filter criteria.
        """
        results = list()
        for c in self.components:
            result = c.query(returns, **filters)

            if isinstance(result, pd.DataFrame) and not result.empty:
                return result

            if result:
                results.extend(result)

        return results

    def __repr__(self) -> str:
        return f"<Dataset name: '{self.name}'>"


class Collection(Base):
    """
    Represents associations between a dataset and its components.

    Attributes
    ----------
    dataset_id : int
        Foreign key to the dataset.
    component_id : int
        Foreign key to the component.
    """

    __tablename__ = "collections"

    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id"), primary_key=True)
    component_id: Mapped[int] = mapped_column(
        ForeignKey("components.id"), primary_key=True
    )

    def __repr__(self):
        return f"<Collection dataset: {self.dataset_id} component: {self.component_id}>"
