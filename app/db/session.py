from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import DATABASE_URL

# declare ORM Base Class
Base = declarative_base()

# DB 連線(pre_ping mprove stability -> ping before connect)
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# communicate with db -> use Session
# create session by this
# autocommit=False -> call commit() to write in the db
# autoflush=False -> do not synchronize the db before search
# bind=engine -> bind the engine(just create)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
