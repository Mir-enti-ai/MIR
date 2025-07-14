# schemas/chat.py
from datetime import datetime, timezone
from bson import ObjectId
from config import chat_logs_collection
from ..db_schemas import ChatLog

def log_message(
    user_id: ObjectId,
    asistant: str,
    user: str,
    input_tokens: int = None,
    output_tokens: int = None,
    model: str = None,
    used_tools: list = None
) -> ObjectId:
    entry = ChatLog(
        userId=user_id,
        user=user,
        asistant=asistant,
        timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        inputTokens=input_tokens,
        outputTokens=output_tokens,
        model=model,
        usedTools=used_tools
        
    ).model_dump(by_alias=True, exclude_none=True)
    result = chat_logs_collection.insert_one(entry)
    return result.inserted_id
