
from typing import Dict, Any, Callable, Awaitable
from datetime import datetime, timezone, timedelta
from agents.openai_agent_v2 import MirAgent
from langchain_community.chat_message_histories import ChatMessageHistory

# ---------------------------------------------------------------------------
# SessionManager — in‑memory session store with roll‑up (summary) capability.
# Tracks *unsummarised* token usage precisely instead of using heuristics.
# ---------------------------------------------------------------------------

class SessionManager:
    def __init__(self):
        self._sessions: Dict[str, Dict[str, Any]] = {}

    # ─── basic lifecycle ────────────────────────────────────────────────────
    def exists(self, user_id: str) -> bool:
        return user_id in self._sessions

    def create(
        self,
        user_id: str,
        *,
        summary: str = "",
        totalInputTokens: int = 0,
        totalOutputTokens: int = 0,
    ) -> Dict[str, Any]:
        """Create a fresh session seeded with optional summary + token totals."""
        self._sessions[user_id] = {
            "history": ChatMessageHistory(),
            "summary": summary,
            "slots": {},
            "lastActive": datetime.now(timezone.utc),
            "totalInputTokens": totalInputTokens,
            "totalOutputTokens": totalOutputTokens,
            "unsummarisedInputTokens": 0,
            "unsummarisedOutputTokens": 0,
        }
        return self._sessions[user_id]

    def delete(self, user_id: str):
        self._sessions.pop(user_id, None)

    def all_sessions(self) -> Dict[str, Dict[str, Any]]:
        return self._sessions

    # ─── internals ──────────────────────────────────────────────────────────
    def _get_or_create(self, user_id: str) -> Dict[str, Any]:
        if user_id not in self._sessions:
            return self.create(user_id)
        return self._sessions[user_id]

    def get(self, user_id: str) -> Dict[str, Any]:
        session = self._get_or_create(user_id)
        session["lastActive"] = datetime.now(timezone.utc)
        return session

    def update_last_active(self, user_id: str, when: datetime | None = None):
        if user_id in self._sessions:
            self._sessions[user_id]["lastActive"] = when or datetime.now(timezone.utc)

    # ─── chat history manipulation ─────────────────────────────────────────
    def get_history(self, user_id: str) -> ChatMessageHistory:
        return self.get(user_id)["history"]

    def append_message(self, user_id: str, role: str, content: str):
        session = self.get(user_id)
        history: ChatMessageHistory = session["history"]
        if role == "user":
            history.add_user_message(content)
        else:
            history.add_ai_message(content)
        session["lastActive"] = datetime.now(timezone.utc)

    # ─── token accounting ─────────────────────────────────────────────────
    def add_tokens(
        self,
        user_id: str,
        *,
        input_tokens: int = 0,
        output_tokens: int = 0,
        unsummarised: bool = True,
    ):
        """Increment both cumulative and (optionally) unsummarised token counts."""
        session = self.get(user_id)
        session["totalInputTokens"] += input_tokens
        session["totalOutputTokens"] += output_tokens
        if unsummarised:
            session["unsummarisedInputTokens"] += input_tokens
            session["unsummarisedOutputTokens"] += output_tokens

    # ─── roll‑up / summarisation helpers ───────────────────────────────────
    def needs_rollup(self,user_id: str,*,max_unsummarised_tokens: int = 5000, idle_ttl: timedelta | None = None,) -> bool:
        """Decide if we should summarise based on exact unsummarised tokens.

        • `max_unsummarised_tokens` – threshold on unsummarisedInput+Output tokens.
        • `max_messages` – optional cap on raw message count.
        • `idle_ttl` – optional: roll up if no activity for this duration.
        """
        if user_id not in self._sessions:
            return False
        s = self._sessions[user_id]
        hist: ChatMessageHistory = s["history"]

        if (
            s["unsummarisedInputTokens"] + s["unsummarisedOutputTokens"]
            >= max_unsummarised_tokens
        ):
            return True

        if idle_ttl:
            last_active: datetime = s["lastActive"]
            if datetime.now(timezone.utc) - last_active > idle_ttl:
                return True
        return False

    async def rollup_history(self,user_id: str, summarizer: Callable[[str, str], Awaitable[str]], ) -> str | None:
        """Replace detailed history with a condensed summary via `summarizer`."""
        if user_id not in self._sessions:
            return None

        session = self._sessions[user_id]
        hist: ChatMessageHistory = session["history"]
        if not hist.messages:
            # Nothing to summarise; reset unsummarised counters anyway
            session["unsummarisedInputTokens"] = 0
            session["unsummarisedOutputTokens"] = 0
            return session["summary"]

        # Flatten recent messages
        history_text = "\n".join(f"{m.type}: {m.content}" for m in hist.messages)

        result = await summarizer(session["summary"], history_text)
        new_summary = result.get("reply","")
        input_tokens = result.get("input_tokens", 0)
        output_tokens = result.get("output_tokens", 0)


        # Keep the new summary; clear history and reset counters
        session["summary"] = new_summary
        session["history"] = ChatMessageHistory()
        session["unsummarisedInputTokens"] = 0
        session["unsummarisedOutputTokens"] = 0
        
        # add the tokens of the summary 
        session["totalInputTokens"] += input_tokens
        session["totalOutputTokens"] += output_tokens

        print(f" the tokens of the summary are {input_tokens} input and {output_tokens} output")


        return new_summary


# Shared singleton instance
session_mgr = SessionManager()
