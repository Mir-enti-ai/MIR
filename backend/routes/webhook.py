"""routes/webhook.py — WhatsApp webhook with session restore + roll‑up.

Key additions vs. previous version:
    • Restores session from `users.summary` if no live session exists.
    • Uses SessionManager.needs_rollup / rollup_history after each turn.
    • Saves condensed summary + token totals back to the same user doc when
      the prune loop in this file retires an idle session (code unchanged).
"""

import asyncio
import traceback

from fastapi import APIRouter, Request, Response
from langchain_core.messages import HumanMessage,SystemMessage

from workers.queues import user_upsert_queue, chat_log_queue
from sessions.manager import session_mgr
from utils import now_utc_str
from config import settings
from integrations.whatsapp import send_text_message
from agents.summary_chain import summarize 
from models import load_session_summary
from .routes_utils import  parse_whatsapp_message,rapup_message
router = APIRouter()

# ─────────────────────────────────────────────────────────────────────────────
# Utility wrapper around model back‑end (Groq/Llama‑v2 etc.)
# ─────────────────────────────────────────────────────────────────────────────

async def get_model_response(parsed_message: HumanMessage, session_id: str,mir_agent):
    """
    function to call the MIR agent
    This function takes a user message and session ID, retrieves the session's
    history and summary of the user, constructs a message for the MIR agent, and returns the
    agent's response along with token counts and any tools used.
    
    :param text: the user message to the agnet
    :param session_id: the session id of the user (the phone number)
    :param mir_agent: the MIR agent instance

    :return: a dictionary containing the reply, input tokens, output tokens, and used tools

    >>> get_model_response("Hello, how are you?", "1234567890", mir_agent)
    {   
        "reply": "Hello! I'm here to help you.",
        "input_tokens": 10,
        "output_tokens": 8,
    }
    
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
        messages.append(parsed_message)

        # Call the mir agent
        resp  = await mir_agent.ask(messages)

        return {
            "reply":         resp.get("reply", ""),
            "input_tokens":  resp.get("input_tokens", 0),
            "output_tokens": resp.get("output_tokens", 0),
            "used_tools": resp.get("tools", []),
        }

    except Exception as e:
        # Fallback if anything blows up
        return {
            "reply":         f"عذراً، حدث خطأ تقني: {e}",
            "input_tokens":  0,
            "output_tokens": 0,
            "used_tools": [],
        }



# ─────────────────────────────────────────────────────────────────────────────
# Background update task
# ─────────────────────────────────────────────────────────────────────────────
async def _background_after_reply(user_id: str, user_text: str, assistant_reply: str, in_tokens: int, out_tokens: int,
    tools_used: list = None):
    """
    function to update the session manager and queues after a reply has been sent.
    This function appends the user and assistant messages to the session manager,
    checks if a roll‑up is needed, and enqueues the user upsert and chat log
    operations for later processing.
    It also handles any exceptions that may occur during the process.

    :param user_id: the ID of the user (the phone number)
    :param user_text: the text of the user's message
    :param assistant_reply: the reply from the assistant
    :param in_tokens: the number of input tokens used
    :param out_tokens: the number of output tokens used
    :param tools_used: a list of tools used during the interaction (optional)
    :return: None

    >>> _background_after_reply("1234567890", "Hello", "Hi there!", 10, 5, ["tool1", "tool2"])    
    
    """
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
                "usedTools": tools_used or [],
            }
        )
    except Exception as e:
        print(f"[background_after_reply] failed for {user_id}: {e}\n{traceback.format_exc()}")









# ─────────────────────────────────────────────────────────────────────────────
# Webhook endpoints
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/webhook")
async def verify_webhook(request: Request):
    """
    Endpoint to verify the webhook with WhatsApp.
    This endpoint checks the verification token provided by WhatsApp
    and returns the challenge if it matches the configured token.
    :param request: The incoming request containing query parameters.
    :return: A response containing the challenge if the token matches,
             or a 403 Forbidden status if it does not.
    """

    params = request.query_params
    if params.get("hub.verify_token") != settings.whatsapp_verify_token:
        return Response("Verification token mismatch", status_code=403)
    return Response(params.get("hub.challenge"), status_code=200)


@router.post("/webhook")
async def handle_webhook(request: Request):
    """
    Endpoint to handle incoming WhatsApp messages.
    This endpoint processes the incoming webhook request from WhatsApp,
    extracts the message details, retrieves or creates a session for the user,
    generates a reply using the model, sends the reply back to the user,
    and performs background updates for session management and logging.

    :param request: The incoming request containing the webhook payload.
    :return: A response indicating the status of the operation.
    
    """

    payload = await request.json()

    # 1) Extract message envelope
    try:
        change = payload["entry"][0]["changes"][0]["value"]

        if "messages" not in change:
            return {"status": "no_user_message"}
        msg = change["messages"][0]
        print(msg)
        external_id = msg["from"]
        message_id = msg.get("id", "")


        # 1.1) Extract user message
        result= await parse_whatsapp_message(message=msg)
        human_message= await rapup_message(result)

        
       
        print(f"Received message from {external_id} (ID: {human_message})")
   
   
    except (KeyError, IndexError, TypeError) as e:
        err = f"Malformed payload: {e}\n{traceback.format_exc()}"
        print(err)
        return {"status": "error", "error": err}

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

    # 2) Get model reply
    result = await get_model_response(parsed_message=human_message,session_id=external_id,mir_agent=request.app.state.mir_agent)
    assistant_reply = result["reply"]
    in_tokens = result["input_tokens"]
    out_tokens = result["output_tokens"]
    tools_used = result.get("used_tools", [])

    # 3) Send reply ASAP
    try:
        print(f"Sending reply to {external_id}: {assistant_reply}")
        await send_text_message(external_id, assistant_reply)
    except Exception as e:
        err = f"Failed to send message: {e}\n{traceback.format_exc()}"
        print(err)
        return {"status": "error", "error": err, "message_id": message_id}

    # 4) Fire‑and‑forget background updates
    asyncio.create_task(
        _background_after_reply(
            external_id,
            human_message.content, 
            assistant_reply,
            in_tokens,
            out_tokens,
            tools_used=tools_used  
        )
    )

    # 5) Acknowledge to WhatsApp
    return {"status": "ok", "message_id": message_id}
