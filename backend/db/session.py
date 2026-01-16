from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import OperationalError
import time
from contextlib import contextmanager



from core.config import settings

connect_args = {}
if settings.DATABASE_URL.startswith("postgresql"):
    connect_args = {
        "connect_timeout": 10,
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5
    }
elif settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine_kwargs = {
    "pool_timeout": 60,
    "pool_recycle": 300,
    "pool_pre_ping": True,
    "connect_args": connect_args
}

if not settings.DATABASE_URL.startswith("sqlite"):
    engine_kwargs.update({
        "poolclass": QueuePool,
        "pool_size": 5,
        "max_overflow": 5
    })

engine = create_engine(
    settings.DATABASE_URL,
    **engine_kwargs
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@contextmanager
def get_db_with_retry(max_retries=3, retry_delay=1):
    """Get database session with retry logic"""
    retries = 0
    while retries < max_retries:
        try:
            db = SessionLocal()
            try:
                yield db
                db.commit()
            except Exception as e:
                db.rollback()
                raise e
            finally:
                db.close()
            break
        except OperationalError as e:
            retries += 1
            if retries == max_retries:
                raise e
            time.sleep(retry_delay)
            continue

def get_db():
    """FastAPI dependency for database sessions"""
    with get_db_with_retry() as db:
        yield db