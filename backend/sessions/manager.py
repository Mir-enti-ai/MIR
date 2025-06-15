from typing import Dict, Any
from utils import now_utc_str
from langchain_community.chat_message_histories import ChatMessageHistory

class SessionManager:
    def __init__(self):
        # Store session metadata and history together per user
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def _init_session(self, user_id: str) -> Dict[str, Any]:
        """
        Initialize a new session entry with default structure.
        """
        default = {
            "history": ChatMessageHistory(),  # in-memory message history
            "slots": {},                     # arbitrary metadata
            "lastActive": now_utc_str(),     # timestamp of last update
            "totalInputTokens": 0,
            "totalOutputTokens": 0,
        }
        return self._sessions.setdefault(user_id, default.copy())

    def get(self, user_id: str) -> Dict[str, Any]:
        """
        Retrieve session data (metadata + history), updating lastActive.
        """
        session = self._init_session(user_id)
        session["lastActive"] = now_utc_str()
        return session

    def get_history(self, user_id: str) -> ChatMessageHistory:
        """
        Return the ChatMessageHistory for this session.
        """
        return self.get(user_id)["history"]

    def append_message(self, user_id: str, role: str, content: str):
        """
        Append a new message to the session history.
        """
        session = self.get(user_id)
        history: ChatMessageHistory = session["history"]
        if role == "user":
            history.add_user_message(content)
        else:
            history.add_ai_message(content)
        session["lastActive"] = now_utc_str()

    def add_tokens(self, user_id: str, input_tokens: int = 0, output_tokens: int = 0):
        """
        Accumulate token usage in the session metadata.
        """
        session = self.get(user_id)
        session["totalInputTokens"] += input_tokens
        session["totalOutputTokens"] += output_tokens

# Shared singleton instance
session_mgr = SessionManager()
