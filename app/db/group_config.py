from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index, Boolean, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class GroupConfig(Base):
    __tablename__ = "group_configs"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(String(100), nullable=False, unique=True, index=True)
    group_name = Column(String(100), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    enable = Column(Boolean, default=True)

    alia_maps = Column(JSON, nullable=True) # 字典，键
    specific_arcade_count_extract_regex = Column(String(255), nullable=True)

    user = relationship("User", back_populates="group_configs")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<GroupConfig(id={self.id}, group_id='{self.group_id}', group_name='{self.group_name}', is_active={self.is_active})>"