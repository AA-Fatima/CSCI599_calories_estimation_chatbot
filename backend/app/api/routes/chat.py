"""Chat API routes."""
from fastapi import APIRouter, HTTPException
from app.models.schemas import ChatRequest, ChatResponse
from app.services.chat_service import chat_service

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    """
    Send a message to the chatbot.
    
    Args:
        request: Chat request with message, session_id, and country
        
    Returns:
        Chat response with nutritional breakdown
    """
    try:
        response = chat_service.process_message(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{session_id}")
async def get_history(session_id: str):
    """
    Get conversation history for a session.
    
    Args:
        session_id: Session ID
        
    Returns:
        Conversation history
    """
    from app.services.session_manager import session_manager
    
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"history": session.get('history', [])}
