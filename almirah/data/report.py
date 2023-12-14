"""Module for easy report generation and data summary."""

from sqlalchemy import select, distinct, func

from .layout import File, Tag


class Report:
    """Collection of report generating methods."""

    @staticmethod
    def generate(layout, level="summary", tags=["subject"]):
        """Generate report for a layout."""
        sess = layout.indexer.db.session
        tag_counts = []
        for tag in tags:
            count = sess.scalar(
                select(func.count(distinct(Tag.value)))
                .where(Tag.name == tag)
                .where(File.root == layout.root)
                .join(File)
            )
            tag_counts.append(count)

        if level == "lengthy":
            raise NotImplementedError

        # Generate report string
        print(f"Layout ... name: {layout.name}")
        for index, tag in enumerate(tags):
            print(f"\t | {tag} \t: {tag_counts[index]}")

    @staticmethod
    def generate_for_dataset(dataset):
        """Generate report for a dataset."""

        print(f"Dataset ... {dataset.primary.name}")

        sources = set()
        for s in dataset.sourcedata.layouts:
            sources.add(s.name)
        print(f"Sources | {','.join(sources)}")

        ders = set()
        for d in dataset.derivatives.layouts:
            ders.add(d.name)
        print(f"Pipelines | {','.join(ders)}")

        for lay in dataset.layouts:
            Report.generate(lay)
