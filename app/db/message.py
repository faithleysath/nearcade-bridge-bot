from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    sender = Column(String(255), nullable=False)
    platform = Column(String(100), nullable=False)
    bot_id = Column(Integer, ForeignKey("bots.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 建立与Bot的关系
    bot = relationship("Bot", back_populates="messages")

    def __repr__(self):
        return f"<Message(id={self.id}, sender='{self.sender}', platform='{self.platform}')>"