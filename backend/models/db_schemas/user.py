from pydantic import BaseModel, Field
from bson import ObjectId
from typing import Optional
from utils import now_utc_str
# --- User model for the `users` collection ---
class User(BaseModel):
    id:         ObjectId = Field(alias="_id")
    external_id:str     = Field(..., alias="externalId")
    name:       str
    created_at: str     = Field(default_factory=now_utc_str, alias="createdAt")
    last_seen_at:str    = Field(default_factory=now_utc_str, alias="lastSeenAt")
    total_input_tokens:  int = Field(0, alias="totalInputTokens")
    total_output_tokens: int = Field(0, alias="totalOutputTokens")
    summary:     Optional[str] = None

    # Pydantic v2 configuration
    model_config = {
        "populate_by_name":    True,                
        "arbitrary_types_allowed": True,           
        "json_encoders":      {ObjectId: str},      
    }
