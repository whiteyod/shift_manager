import os
from pathlib import Path
from sqlite3 import connect
from sqlalchemy import text, create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from app.models.base import Base


# Create data dir if not exists
DATA_DIR = Path(__file__).parent.parent.parent / 'data'
DATA_DIR.mkdir(exist_ok=True, parents=True)


# Get database url from env
def get_db_url() -> str:
    if os.getenv('DATABASE_URL'):
        return os.getenv('DATABASE_URL')
    else:
        # Init db url if it missing in env
        return f'sqlite:///{DATA_DIR}/shifts.db'


# Create engine and session factory
engine = create_engine(
    get_db_url(),
    connect_args={'check_same_thread': False} \
    if 'sqlite' in get_db_url() else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# DataBase session manager
def get_db() -> Generator[Session, None, None]:
    ''' Yields a database session.
    Ensures session closed after use. 
    '''
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        print(f'{'>' * 56} \n We have an error: {e}')
        db.rollback()
        raise
    finally:
        db.close()


# Create tables
def init_db() -> None:
    Base.metadata.create_all(bind=engine)