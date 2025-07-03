# models/message.py
from pydantic import BaseModel, Field
from bson import ObjectId
from typing import Optional
from utils import now_utc_str

# --- ChatLog model for the `chat_logs` collection ---
class ChatLog(BaseModel):
    id:          ObjectId    = Field(default_factory=ObjectId, alias="_id")
    user_id:    ObjectId    = Field(..., alias="userId")
    user:       str
    asistant:  str
    timestamp:  str         = Field(default_factory=now_utc_str)
    input_tokens:  Optional[int] = Field(None, alias="inputTokens")
    output_tokens: Optional[int] = Field(None, alias="outputTokens")
    model:      Optional[str] = None
    used_tools: Optional[list] = Field(None, alias="usedTools")

    model_config = {
        "populate_by_name":       True,
        "arbitrary_types_allowed": True,
        "json_encoders":         {ObjectId: str},
    }
