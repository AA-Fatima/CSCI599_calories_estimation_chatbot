"""Session manager - handles conversation context."""
import uuid
from typing import Dict, Optional
from datetime import datetime


class SessionManager:
    """Manages chat sessions and conversation context."""
    
    def __init__(self):
        """Initialize session manager."""
        self.sessions: Dict[str, Dict] = {}
    
    def create_session(self, country: Optional[str] = None) -> str:
        """
        Create a new session.
        
        Args:
            country: Selected country
            
        Returns:
            Session ID
        """
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            'country': country,
            'history': [],
            'last_dish': None,
            'last_dish_ingredients': None,
            'created_at': datetime.now(),
            'last_activity': datetime.now()
        }
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session by ID."""
        return self.sessions.get(session_id)
    
    def update_session(
        self,
        session_id: str,
        last_dish: str = None,
        last_dish_ingredients: list = None
    ):
        """
        Update session context.
        
        Args:
            session_id: Session ID
            last_dish: Last dish discussed
            last_dish_ingredients: Ingredients of last dish
        """
        if session_id in self.sessions:
            session = self.sessions[session_id]
            if last_dish:
                session['last_dish'] = last_dish
            if last_dish_ingredients:
                session['last_dish_ingredients'] = last_dish_ingredients
            session['last_activity'] = datetime.now()
    
    def add_to_history(
        self,
        session_id: str,
        user_message: str,
        bot_response: str
    ):
        """
        Add message to conversation history.
        
        Args:
            session_id: Session ID
            user_message: User's message
            bot_response: Bot's response
        """
        if session_id in self.sessions:
            self.sessions[session_id]['history'].append({
                'user': user_message,
                'bot': bot_response,
                'timestamp': datetime.now()
            })
    
    def get_conversation_history(self, session_id: str) -> str:
        """
        Get conversation history as formatted string.
        
        Args:
            session_id: Session ID
            
        Returns:
            Formatted conversation history
        """
        session = self.get_session(session_id)
        if not session or not session['history']:
            return ""
        
        history_lines = []
        for entry in session['history'][-3:]:  # Last 3 exchanges
            history_lines.append(f"User: {entry['user']}")
            history_lines.append(f"Bot: {entry['bot']}")
        
        return "\n".join(history_lines)
    
    def cleanup_old_sessions(self, max_age_hours: int = 24):
        """Remove sessions older than max_age_hours."""
        current_time = datetime.now()
        to_remove = []
        
        for session_id, session in self.sessions.items():
            age = (current_time - session['last_activity']).total_seconds() / 3600
            if age > max_age_hours:
                to_remove.append(session_id)
        
        for session_id in to_remove:
            del self.sessions[session_id]


# Global instance
session_manager = SessionManager()
