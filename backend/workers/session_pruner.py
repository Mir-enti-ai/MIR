import asyncio
from datetime import datetime, timezone, timedelta
from sessions.manager import session_mgr
from agents.summary_chain import summarize  # Arabic summariser
from models import save_session_summary

# Configuration (tweak in one place)
SESSION_TIMEOUT = timedelta(minutes=30)
PRUNE_INTERVAL = 300  # seconds (5 min)


def start_session_pruner():
    async def worker():
        while True:
            await asyncio.sleep(PRUNE_INTERVAL)
            now = datetime.now(timezone.utc)
            for user_id, sess in list(session_mgr.all_sessions().items()):
                if now - sess["lastActive"] > SESSION_TIMEOUT:
                    # Ensure final roll‑up
                    await session_mgr.rollup_history(user_id, summarize)
                    # Persist summary + token totals to Mongo
                    await save_session_summary(
                        user_id,
                        sess["summary"],
                        sess["totalInputTokens"],
                        sess["totalOutputTokens"],
                    )
                    # Remove session from RAM
                    session_mgr.delete(user_id)
                    print(f"[session_pruner] retired idle session {user_id}")

    asyncio.create_task(worker())
