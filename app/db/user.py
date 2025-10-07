from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=False)
    username = Column(String(100), nullable=False)
    api_key = Column(String(100), nullable=True, unique=True, index=True)
    passkeys = relationship("PassKey", back_populates="user")
    devices = relationship("Device", back_populates="user")
    group_configs = relationship("GroupConfig", back_populates="user")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_active_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"

class PassKey(Base):
    __tablename__ = "passkeys"

    id = Column(Integer, primary_key=True, index=True)
    passkey_name = Column(String(100), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    key = Column(String(255), nullable=False, unique=True)

    user = relationship("User", back_populates="passkeys")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index('idx_passkey_user_key', 'user_id', 'key'),
    )

    def __repr__(self):
        return f"<PassKey(id={self.id}, passkey_name='{self.passkey_name}', user_id={self.user_id})>"