"""SQLAlchemy database models."""
from datetime import datetime
from typing import List, Optional
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, Index, ForeignKey
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from app.database import Base
from app.config import settings


class Dish(Base):
    """Dish model with vector embeddings for semantic search."""
    
    __tablename__ = "dishes"
    
    id = Column(Integer, primary_key=True, index=True)
    dish_name = Column(String(255), nullable=False, index=True)
    dish_name_arabic = Column(String(255), nullable=True)
    country = Column(String(100), nullable=False, index=True)
    
    # Ingredients stored as JSON
    ingredients = Column(JSON, nullable=False)
    
    # Nutritional totals
    total_calories = Column(Float, nullable=True)
    total_carbs = Column(Float, nullable=True)
    total_protein = Column(Float, nullable=True)
    total_fat = Column(Float, nullable=True)
    
    # Vector embedding for semantic search (dimension from config)
    embedding = Column(Vector(settings.embedding_dimension), nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_dish_name_lower', 'dish_name'),
        Index('idx_country', 'country'),
    )


class USDAFood(Base):
    """USDA food database with vector embeddings."""
    
    __tablename__ = "usda_foods"
    
    id = Column(Integer, primary_key=True, index=True)
    fdc_id = Column(Integer, nullable=False, unique=True, index=True)
    description = Column(String(500), nullable=False, index=True)
    description_lower = Column(String(500), nullable=False, index=True)
    
    # Nutrition per 100g
    calories = Column(Float, nullable=False, default=0.0)
    protein = Column(Float, nullable=False, default=0.0)
    carbs = Column(Float, nullable=False, default=0.0)
    fat = Column(Float, nullable=False, default=0.0)
    
    # Source information
    source = Column(String(100), nullable=True)
    
    # Vector embedding for semantic search (dimension from config)
    embedding = Column(Vector(settings.embedding_dimension), nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_description_lower', 'description_lower'),
    )


class ChatSession(Base):
    """Persistent chat sessions."""
    
    __tablename__ = "chat_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(36), unique=True, nullable=False, index=True)
    country = Column(String(100), nullable=True)
    
    # Last interaction context
    last_dish = Column(String(255), nullable=True)
    last_dish_ingredients = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    conversation_history = relationship("ConversationHistory", back_populates="session", cascade="all, delete-orphan")


class ConversationHistory(Base):
    """Conversation message history."""
    
    __tablename__ = "conversation_history"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(36), ForeignKey("chat_sessions.session_id"), nullable=False, index=True)
    
    # Message content
    user_message = Column(Text, nullable=False)
    bot_response = Column(Text, nullable=False)
    
    # Metadata
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    session = relationship("ChatSession", back_populates="conversation_history")


class MissingDish(Base):
    """Track missing dishes for admin review."""
    
    __tablename__ = "missing_dishes"
    
    id = Column(Integer, primary_key=True, index=True)
    dish_name = Column(String(255), nullable=False, index=True)
    dish_name_arabic = Column(String(255), nullable=True)
    country = Column(String(100), nullable=False, index=True)
    
    # Query information
    query_text = Column(Text, nullable=False)
    gpt_response = Column(JSON, nullable=True)
    ingredients = Column(JSON, nullable=True)
    
    # Tracking
    query_count = Column(Integer, default=1)
    first_queried = Column(DateTime, default=datetime.utcnow, index=True)
    last_queried = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Status
    status = Column(String(50), default="pending", index=True)  # pending, reviewed, added
    
    __table_args__ = (
        Index('idx_dish_country', 'dish_name', 'country'),
    )
