import asyncio
from fastapi import FastAPI
from contextlib import asynccontextmanager

from config import mongo_client
from routes.webhook import router as webhook_router
from workers.user_writer import start_user_writer
from workers.chat_logger import start_chat_logger
from workers.session_pruner import start_session_pruner
from agents.openai_agent_v2 import MirAgent   

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ─── Startup ───────────────────────────────────────────────────────────────
    start_user_writer()         
    start_chat_logger()         
    start_session_pruner()
    app.state.mir_agent = MirAgent()   


    # Give them a moment to spin up if needed
    await asyncio.sleep(0)
    yield
    # ─── Shutdown ──────────────────────────────────────────────────────────────
    # Close MongoDB connection
    if mongo_client:
        mongo_client.close()

# Create FastAPI with our lifespan manager
app = FastAPI(lifespan=lifespan)

# Include your webhook router (and any others)
app.include_router(webhook_router)
