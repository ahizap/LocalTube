from sqlalchemy import Boolean, Column, Integer, String, Float, JSON, DateTime
from database import Base
import datetime

class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    path = Column(String, unique=True, index=True)
    duration = Column(Float, default=0.0)
    thumbnail_path = Column(String, nullable=True)
    preview_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.now(datetime.timezone.utc))

class Setting(Base):
    __tablename__ = "settings"

    key = Column(String, primary_key=True, index=True)
    value = Column(String) # Store as JSON strings for simplicity
