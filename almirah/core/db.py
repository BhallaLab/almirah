"""Database connection and session management."""

from sqlalchemy import MetaData
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine.base import Connection


class DBManager:
    """Manages database connections and sessions."""

    Session = None

    def __init__(self, url: str):
        self.engine = create_engine(url)
        self.metadata = MetaData()
        self.metadata.reflect(bind=self.engine, views=True)

    @property
    def connection(self) -> Connection:
        """Provides a context-managed connection to the database."""
        return self.engine.connect()

    @property
    def session(self) -> Session:
        """Provides a context-managed session for performing database operations."""
        if not self.Session:
            self.Session = sessionmaker(self.engine)
        return self.Session()

    def __repr__(self) -> str:
        return f"<DBManager url='{self.engine.url}'>"
