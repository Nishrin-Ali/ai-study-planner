from typing import List, Optional
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(..., description="Role of the sender: 'user' or 'model'")
    text: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    plan_id: str = Field(..., description="Target study plan ID")
    item_id: Optional[str] = Field(None, description="Plan item ID if chatting about a specific timetable slot")
    question_text: str = Field(..., description="The study question or topic title")
    user_message: str = Field(..., description="Student query or prompt")
    history: List[ChatMessage] = Field(default_factory=list, description="Prior conversation messages (max 10)")
    stream: Optional[bool] = Field(True, description="Whether to stream the response via SSE")


class ChatResponse(BaseModel):
    reply: str = Field(..., description="Complete assistant response text")
    source_attribution: str = Field(..., description="Attribution to source notes or syllabus")
    grounded: bool = Field(..., description="Whether response is directly grounded in uploaded notes or curriculum")
