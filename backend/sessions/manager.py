# # sessions/manager.py

# from typing import Dict, Any
# from utils import now_utc_str
# from collections import defaultdict

# # in-memory session store
# _session_store: Dict[str, Dict[str, Any]] = {}

# class SessionManager:
#     def __init__(self):
#         self.store = _session_store

#     def get(self, user_id: str) -> Dict[str, Any]:
#         # Get or create session with lock to ensure thread safety
       
#         if user_id not in self.store:
#             self.store[user_id] = {
#                 "context": [],
#                 "slots": {},
#                 "lastActive": now_utc_str(),
#                 "totalInputTokens": 0,
#                 "totalOutputTokens": 0,
#             }
#         return self.store[user_id]

#     def save(self, user_id: str, session: Dict[str, Any]):
#         session["lastActive"] = now_utc_str()
#         self.store[user_id] = session

#     def add_tokens(self, user_id: str, input_tokens: int = 0, output_tokens: int = 0):
#         """
#         Increment the session's cumulative token usage.
#         Call this after you count tokens for a user message (input_tokens)
#         and after you generate a reply (output_tokens).
#         """
       
#         session = self.store.get(user_id, {
#             "context": [],
#             "slots": {},
#             "lastActive": now_utc_str(),
#             "totalInputTokens": 0,
#             "totalOutputTokens": 0,
#         })
#         session["totalInputTokens"] = session.get("totalInputTokens", 0) + input_tokens
#         session["totalOutputTokens"] = session.get("totalOutputTokens", 0) + output_tokens
#         self.store[user_id] = session

#     def append_message(self, user_id: str, role: str, content: str):
#         """Atomic append of a message to the context"""
#         session = self.get(user_id)
#         session["context"].append({"role": role, "content": content})
#         session["lastActive"] = now_utc_str()
#         self.store[user_id] = session

# # single shared instance
# session_mgr = SessionManager()

# sessions/manager.py
# sessions/manager.py

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
