"""schemas/summary.py — centralised helpers for loading/saving running
conversation summaries inside the *users* collection.

These helpers are used by routes/webhook.py and the prune loop. They are
self‑contained: if Mongo is unavailable (e.g. during tests), they simply return
`None` or no‑op.
"""

from utils import now_utc_str
from config import db


async def load_session_summary(user_id: str):
    """Return dict with summary + token totals, or None if not found."""
    if db is None:
        return None
    doc = db["users"].find_one({"externalId": user_id})
    if not doc or not doc.get("summary"):
        return None
    return {
        "summary": doc.get("summary", ""),
        "totalInputTokens": doc.get("totalInputTokens", 0),
        "totalOutputTokens": doc.get("totalOutputTokens", 0),
    }


async def save_session_summary(
    user_id: str,
    summary: str,
    total_in: int,
    total_out: int,
):
    """Upsert the running summary and token counters back into `users`."""
    if db is None:
        return
    db["users"].update_one(
        {"externalId": user_id},
        {
            "$set": {
                "summary": summary,
                "totalInputTokens": total_in,
                "totalOutputTokens": total_out,
                "updatedAt": now_utc_str(),
            }
        },
        upsert=True,
    )
