from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    phone = Column(String)
    email = Column(String)
    family_members = Column(Text)
    insurance_companies = Column(Text)
    created_at = Column(String)

    receipts = relationship("Receipt", back_populates="user")


class Receipt(Base):
    __tablename__ = "receipts"

    public_id = Column(String, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    username = Column(String)
    name = Column(String)
    date = Column(String)
    sent_to_insurance = Column(String)
    refund_details = Column(Text)
    insurance_company = Column(String)
    account_username = Column(String)
    family_count = Column(Integer)
    family_names = Column(Text)
    how_work = Column(Text)
    secure_url = Column(String)
    created_at = Column(String)

    user = relationship("User", back_populates="receipts")
