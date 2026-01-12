"""Chat API routes."""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.schemas import ChatRequest, ChatResponse
from app.services.chat_service_new import chat_service_new
from app.api.deps import get_database

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    db: AsyncSession = Depends(get_database)
):
    """
    Send a message to the chatbot.
    
    Args:
        request: Chat request with message, session_id, and country
        db: Database session
        
    Returns:
        Chat response with nutritional breakdown
    """
    try:
        response = await chat_service_new.process_message(request, db)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{session_id}")
async def get_history(
    session_id: str,
    db: AsyncSession = Depends(get_database)
):
    """
    Get conversation history for a session.
    
    Args:
        session_id: Session ID
        db: Database session
        
    Returns:
        Conversation history
    """
    from app.repositories.sessions import SessionsRepository
    
    sessions_repo = SessionsRepository(db)
    session = await sessions_repo.get(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    history = await sessions_repo.get_history(session_id)
    
    return {
        "history": [
            {
                "user": h.user_message,
                "bot": h.bot_response,
                "timestamp": h.timestamp.isoformat()
            }
            for h in history
        ]
    }
