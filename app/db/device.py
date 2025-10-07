from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    device_name = Column(String(100), nullable=False)
    ws_url = Column(String(255), nullable=False)
    auth_token = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=False)

    user = relationship("User", back_populates="devices")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index('idx_device_user_name', 'user_id', 'device_name', 'ws_url', 'auth_token', 'is_active'),
    )

    def __repr__(self):
        return f"<Device(id={self.id}, device_name='{self.device_name}', user_id={self.user_id}, ws_url='{self.ws_url}', auth_token='{self.auth_token}', is_active={self.is_active}, last_login_at={self.last_login_at})>"