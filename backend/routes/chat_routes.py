"""Chat API routes — powered by OpenAI AI Chat Engine."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from database import get_db
from models import User, ChatHistory
from schemas import ChatQuery, ChatResponse
from dependencies import get_current_user
from ai_chat_engine import get_ai_chat_engine
import json

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/query", response_model=ChatResponse)
async def chat_query(
    query: ChatQuery,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Process a chat query using the OpenAI-powered AI Chat Engine.
    Generates SQL when needed, executes it, and returns a natural-language answer.
    """
    try:
        # Get AI engine
        engine = get_ai_chat_engine()
        
        # Process query (plan → SQL → answer)
        result = engine.query(query.query, db)
        
        # Save to chat history
        chat_record = ChatHistory(
            user_id=current_user.id,
            query=query.query,
            response=result["response"],
            retrieved_docs=json.dumps(result.get("document_ids", []))
        )
        db.add(chat_record)
        db.commit()
        db.refresh(chat_record)
        
        return ChatResponse(
            query=result["query"],
            response=result["response"],
            timestamp=chat_record.timestamp,
            retrieved_context=result["retrieved_contexts"][:3]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing query: {str(e)}"
        )


@router.get("/history")
async def get_chat_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 50
):
    """Get user's chat history."""
    history = db.query(ChatHistory).filter(
        ChatHistory.user_id == current_user.id
    ).order_by(
        ChatHistory.timestamp.desc()
    ).limit(limit).all()
    
    return {
        "history": [
            {
                "id": chat.id,
                "query": chat.query,
                "response": chat.response,
                "timestamp": chat.timestamp.isoformat()
            }
            for chat in history
        ]
    }


@router.delete("/history/{chat_id}")
async def delete_chat(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a specific chat from history."""
    chat = db.query(ChatHistory).filter(
        ChatHistory.id == chat_id,
        ChatHistory.user_id == current_user.id
    ).first()
    
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )
    
    db.delete(chat)
    db.commit()
    
    return {"message": "Chat deleted successfully"}
