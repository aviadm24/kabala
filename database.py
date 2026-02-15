import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv



ENV = os.getenv("ENV")
print(f"Database environment: {ENV}")

# Check if we're running tests
IS_TEST = "pytest" in sys.modules

if IS_TEST:
    # In test mode, try to load .env.test first
    from pathlib import Path
    test_env_file = Path(__file__).parent / ".env.test"
    if test_env_file.exists():
        load_dotenv(test_env_file)
    else:
        load_dotenv()
    
    # Use test database if available
    test_db_url = os.getenv("TEST_DATABASE_URL")
    if test_db_url:
        DATABASE_URL = test_db_url
    else:
        DATABASE_URL = "sqlite:///./test.db"
    
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
elif ENV == "local":
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