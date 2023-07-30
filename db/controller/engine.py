from sqlalchemy.engine import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import scoped_session
from config import DB_PATH, THREADS

engine = create_engine(f"sqlite:///{DB_PATH}", pool_size=THREADS, max_overflow=0)
session_factory  = sessionmaker(bind=engine)
Session = scoped_session(session_factory)
