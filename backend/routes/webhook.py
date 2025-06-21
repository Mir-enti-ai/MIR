"""routes/webhook.py — WhatsApp webhook with session restore + roll‑up.

Key additions vs. previous version:
    • Restores session from `users.summary` if no live session exists.
    • Uses SessionManager.needs_rollup / rollup_history after each turn.
    • Saves condensed summary + token totals back to the same user doc when
      the prune loop in this file retires an idle session (code unchanged).
"""
from fastapi import APIRouter, Request, Response
import asyncio
import traceback
from workers.queues import user_upsert_queue, chat_log_queue
from sessions.manager import session_mgr
from utils import now_utc_str
from config import settings
from integrations.whatsapp import send_text_message
from agents.openai_agent_v2 import MirAgent
from agents.summary_chain import summarize 
from schemas.summary import load_session_summary
from langchain_core.messages import HumanMessage,SystemMessage



router = APIRouter()

# ─────────────────────────────────────────────────────────────────────────────
# Utility wrapper around model back‑end (Groq/Llama‑v2 etc.)
# ─────────────────────────────────────────────────────────────────────────────
async def get_model_response(text: str, session_id: str):
    """
    Build the prompt as:
        1. SystemMessage containing the stored running summary (if any)
        2. The detailed ChatMessageHistory
        3. The new HumanMessage
    Then call MirAgent and return reply + token counts.
    """
    try:
        sess = session_mgr.get(session_id)
        running_summary = sess["summary"]           # may be ""
        history_msgs    = sess["history"].messages  # list[BaseMessage]

        # Assemble messages for the LLM
        messages = []
        if running_summary:
            messages.append(SystemMessage(
                content=f"ملخص سابق للمحادثة: {running_summary}"
            ))
        messages.extend(history_msgs)
        messages.append(HumanMessage(content=text))

        # Call the Groq agent
        agent = MirAgent(session_id=session_id)
        resp  = await agent.ask(messages)

        return {
            "reply":         resp.get("reply", ""),
            "input_tokens":  resp.get("input_tokens", 0),
            "output_tokens": resp.get("output_tokens", 0),
        }

    except Exception as e:
        # Fallback if anything blows up
        return {
            "reply":         f"عذراً، حدث خطأ تقني: {e}",
            "input_tokens":  0,
            "output_tokens": 0,
        }
# ─────────────────────────────────────────────────────────────────────────────
# Background update task
# ─────────────────────────────────────────────────────────────────────────────
async def _background_after_reply(
    user_id: str,
    user_text: str,
    assistant_reply: str,
    in_tokens: int,
    out_tokens: int,
):
    try:
        
        # 1) update in‑memory session
        session_mgr.append_message(user_id, "user", user_text)
        session_mgr.append_message(user_id, "assistant", assistant_reply)
        session_mgr.add_tokens(user_id, input_tokens=in_tokens, output_tokens=out_tokens)

        print(f"We are in the background function and the messgaes have been added")

        # 2) summarise if needed (size‑based roll‑up)
        if session_mgr.needs_rollup(user_id):
            await session_mgr.rollup_history(user_id, summarize)
            print(f"summary has been created",session_mgr.get(user_id)["summary"])

        # 3) enqueue write‑behind operations
        totals = session_mgr.get(user_id)
        total_in = totals["totalInputTokens"]
        total_out = totals["totalOutputTokens"]
        now_str = now_utc_str()
        user_upsert_queue.put_nowait(
            {
                "externalId": user_id,
                "name": None,
                "createdAt": now_str,
                "lastSeenAt": now_str,
                "totalInputTokens": total_in,
                "totalOutputTokens": total_out,
                "summary": totals["summary"],
            }
        )
        chat_log_queue.put_nowait(
            {
                "userId": user_id,
                "user": user_text,
                "assistant": assistant_reply,
                "message": user_text,
                "timestamp": now_str,
                "inputTokens": in_tokens,
                "outputTokens": out_tokens,
            }
        )
    except Exception as e:
        print(f"[background_after_reply] failed for {user_id}: {e}\n{traceback.format_exc()}")

# ─────────────────────────────────────────────────────────────────────────────
# Webhook endpoints
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/webhook")
async def verify_webhook(request: Request):
    params = request.query_params
    if params.get("hub.verify_token") != settings.whatsapp_verify_token:
        return Response("Verification token mismatch", status_code=403)
    return Response(params.get("hub.challenge"), status_code=200)


@router.post("/webhook")
async def handle_webhook(request: Request):
    payload = await request.json()

    # 1) Extract message envelope
    try:
        change = payload["entry"][0]["changes"][0]["value"]
        if "messages" not in change:
            return {"status": "no_user_message"}
        msg = change["messages"][0]
        external_id = msg["from"]
        user_text = msg.get("text", {}).get("body", "")
        message_id = msg.get("id", "")
        print(f"Received message from {external_id}: {user_text} (ID: {message_id})")
   
   
    except (KeyError, IndexError, TypeError) as e:
        err = f"Malformed payload: {e}\n{traceback.format_exc()}"
        print(err)
        return {"status": "error", "error": err}

    if not user_text:
        return {"status": "no_text", "message_id": message_id}

    # 1.5) Restore or create session
    if not session_mgr.exists(external_id):
        doc = await load_session_summary(external_id)
        if doc:
            session_mgr.create(
                external_id,
                summary=doc["summary"],
                totalInputTokens=doc["totalInputTokens"],
                totalOutputTokens=doc["totalOutputTokens"],
            )
        else:
            session_mgr.create(external_id)


    print(f"Session for {external_id} exists: {session_mgr.exists(external_id)}")

    # 2) Get model reply
    result = await get_model_response(user_text, external_id)
    assistant_reply = result["reply"]
    in_tokens = result["input_tokens"]
    out_tokens = result["output_tokens"]

    print(f"Reply for {external_id}: {assistant_reply} (input: {in_tokens}, output: {out_tokens})")

    # 3) Send reply ASAP
    try:
        await send_text_message(external_id, assistant_reply)
    except Exception as e:
        err = f"Failed to send message: {e}\n{traceback.format_exc()}"
        print(err)
        return {"status": "error", "error": err, "message_id": message_id}

    # 4) Fire‑and‑forget background updates
    asyncio.create_task(
        _background_after_reply(
            external_id,
            user_text,
            assistant_reply,
            in_tokens,
            out_tokens,
        )
    )

    # 5) Acknowledge to WhatsApp
    return {"status": "ok", "message_id": message_id}
