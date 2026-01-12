"""Sessions repository for persistent chat sessions."""
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from loguru import logger
from app.models.database import ChatSession, ConversationHistory


class SessionsRepository:
    """Repository for chat sessions."""
    
    def __init__(self, db: AsyncSession):
        """Initialize repository with database session."""
        self.db = db
    
    async def create(self, session_id: str, country: Optional[str] = None) -> ChatSession:
        """
        Create a new chat session.
        
        Args:
            session_id: Unique session ID
            country: User's country
            
        Returns:
            Created session
        """
        session = ChatSession(
            session_id=session_id,
            country=country,
            created_at=datetime.utcnow(),
            last_activity=datetime.utcnow()
        )
        self.db.add(session)
        await self.db.flush()
        logger.info(f"Created new session: {session_id}")
        return session
    
    async def get(self, session_id: str) -> Optional[ChatSession]:
        """
        Get session by ID.
        
        Args:
            session_id: Session ID
            
        Returns:
            ChatSession or None
        """
        query = select(ChatSession).where(
            ChatSession.session_id == session_id
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def update(
        self,
        session_id: str,
        last_dish: Optional[str] = None,
        last_dish_ingredients: Optional[List] = None
    ) -> Optional[ChatSession]:
        """
        Update session context.
        
        Args:
            session_id: Session ID
            last_dish: Last dish discussed
            last_dish_ingredients: Ingredients of last dish
            
        Returns:
            Updated session or None
        """
        session = await self.get(session_id)
        
        if session:
            if last_dish is not None:
                session.last_dish = last_dish
            if last_dish_ingredients is not None:
                session.last_dish_ingredients = last_dish_ingredients
            session.last_activity = datetime.utcnow()
            await self.db.flush()
            logger.debug(f"Updated session: {session_id}")
        
        return session
    
    async def add_to_history(
        self,
        session_id: str,
        user_message: str,
        bot_response: str
    ) -> ConversationHistory:
        """
        Add message to conversation history.
        
        Args:
            session_id: Session ID
            user_message: User's message
            bot_response: Bot's response
            
        Returns:
            Created conversation history entry
        """
        history = ConversationHistory(
            session_id=session_id,
            user_message=user_message,
            bot_response=bot_response,
            timestamp=datetime.utcnow()
        )
        self.db.add(history)
        await self.db.flush()
        
        # Update session last_activity
        await self.update(session_id)
        
        return history
    
    async def get_history(
        self,
        session_id: str,
        limit: int = 10
    ) -> List[ConversationHistory]:
        """
        Get conversation history for a session.
        
        Args:
            session_id: Session ID
            limit: Maximum number of messages to retrieve
            
        Returns:
            List of conversation history entries
        """
        query = select(ConversationHistory).where(
            ConversationHistory.session_id == session_id
        ).order_by(
            ConversationHistory.timestamp.desc()
        ).limit(limit)
        
        result = await self.db.execute(query)
        history = list(result.scalars().all())
        return list(reversed(history))  # Return in chronological order
    
    async def get_formatted_history(
        self,
        session_id: str,
        limit: int = 3
    ) -> str:
        """
        Get formatted conversation history string.
        
        Args:
            session_id: Session ID
            limit: Number of recent exchanges to include
            
        Returns:
            Formatted history string
        """
        history = await self.get_history(session_id, limit)
        
        if not history:
            return ""
        
        lines = []
        for entry in history:
            lines.append(f"User: {entry.user_message}")
            lines.append(f"Bot: {entry.bot_response}")
        
        return "\n".join(lines)
    
    async def cleanup_old_sessions(self, max_age_hours: int = 24) -> int:
        """
        Remove sessions older than max_age_hours.
        
        Args:
            max_age_hours: Maximum age in hours
            
        Returns:
            Number of deleted sessions
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        
        query = delete(ChatSession).where(
            ChatSession.last_activity < cutoff_time
        )
        result = await self.db.execute(query)
        await self.db.flush()
        
        deleted_count = result.rowcount
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old sessions")
        
        return deleted_count
