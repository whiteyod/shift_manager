import os
from sqlmodel import Session, SQLModel, create_engine
from loguru import logger
from typing import Generator

from app.core.config import settings


# Create engine and session factory
engine = create_engine(settings.database_url, pool_pre_ping=True)


# DataBase session manager
def get_session() -> Generator[Session, None, None]:
    ''' Yields a database session.
    Ensures session closed after use. 
    '''
    with Session(engine) as session:
        yield session


# Create tables
def init_db() -> None:
    import app.models
    SQLModel.metadata.create_all(engine)