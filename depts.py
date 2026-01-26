from database import SessionLocal

#def get_db():
#    db = SessionLocal()
#    try:
#        yield db
#    finally:
#        db.close()

def get_db():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except:
        db.rollback()
        raise
    finally:
        db.close()