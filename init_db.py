from database import engine, Base
from models import User, Receipt

def ensure_db():
    Base.metadata.create_all(bind=engine)
