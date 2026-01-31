import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv



ENV = os.getenv("ENV")
print(f"Database environment: {ENV}")
if ENV == "local":
    load_dotenv()
    DATABASE_URL = "sqlite:///./app.db"
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    DATABASE_URL = os.environ["DATABASE_URL"]
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        connect_args={"sslmode": "require"},
        echo=True   # TEMPORARY
    )

SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()