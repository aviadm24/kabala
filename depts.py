from database import SessionLocal
import logging

logger = logging.getLogger(__name__)

def get_db():
    db = SessionLocal()
    try:
        yield db
        logger.info("DB dependency completed, committing")
        db.commit()
    except Exception:
        logger.error("DB dependency rollback triggered", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()