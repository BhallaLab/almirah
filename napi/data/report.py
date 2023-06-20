"""Module for easy report generation and data summary."""

from sqlalchemy import select, distinct, func

from .layout import File, Tag


class Report:
    """Collection of report generating methods."""

    @staticmethod
    def generate(layout, level="summary"):
        """Generate report for a layout."""
        sess = layout.indexer.conn.session
        n_subjects = sess.scalar(
            select(func.count(distinct(Tag.val)))
            .where(Tag.name == "subject")
            .where(File.root == layout.root)
            .join(File)
        )

        if level == "lengthy":
            pass

        print(f"Layout ... name: {layout.name} | subjects: {n_subjects}")

    @staticmethod
    def generate_for_dataset(dataset):
        """Generate report for a dataset."""

        print(f"Dataset ... {dataset.primary.name}")

        sources = set()
        for s in dataset.sourcedata.layouts:
            sources.add(s.name)
        print(f"Sources ... {sources}")

        ders = set()
        for d in dataset.derivatives.layouts:
            ders.add(d.name)
        print(f"Pipelines ... {ders}")

        for lay in dataset.layouts:
            Report.generate(lay)
