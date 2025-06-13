from fastapi import APIRouter, Request, HTTPException, Response
from workers.queues import user_upsert_queue, chat_log_queue
from sessions.manager import session_mgr
from utils import now_utc_str
from config import settings
from integrations.whatsapp import send_text_message
from agents.openai_agent import runnable_chain
import traceback

router = APIRouter()


def enqueue_logs(user_id, text, reply, in_tokens, out_tokens):
    now = now_utc_str()
    # Queue user upsert (worker will write to Mongo)
    user_upsert_queue.put_nowait({
        "externalId": user_id,
        "name":       None,      # if you know the name, include it here
        "createdAt":  now,
        "lastSeenAt": now,
    })
    # Queue chat logs
    chat_log_queue.put_nowait({
        "userId":      user_id,
        "user":        text,
        "assistant":   reply,
        "message":     text,
        "timestamp":   now,
        "inputTokens": in_tokens,
        "outputTokens": out_tokens
    })

@router.get("/webhook")
async def verify_webhook(request: Request):  # Facebook/WhatsApp verification
    params = request.query_params
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")
    if token != settings.whatsapp_verify_token:
        return Response("Verification token mismatch", status_code=403)
    return Response(challenge, status_code=200)

@router.post("/webhook")
async def handle_webhook(request: Request):
    payload = await request.json()
    # Extract the change from the payload 
    try:
        change = payload["entry"][0]["changes"][0]["value"]
    except (KeyError, IndexError) as e:
        error_msg = f"Malformed webhook payload: {e}\n{traceback.format_exc()}"
        print(error_msg)
        return {"status": "error", "error": error_msg}

    if "messages" not in change:
        return {"status": "no_messages"}



    # Extract the first message from the change
    try:
        msg = change["messages"][0]
        external_id = msg["from"]
        text = msg.get("text", {}).get("body", "")
        message_id = msg.get("id", "")
        print("Received message from", external_id, ":", text)
    except (KeyError, IndexError, TypeError) as e:
        error_msg = f"Malformed message structure: {e}\n{traceback.format_exc()}"
        print(error_msg)
        return {"status": "error", "error": error_msg}


    # Append incoming user message
    session_mgr.append_message(external_id, "user", text)

    try:
        # Invoke the AI chain for a response
        result = await runnable_chain.ainvoke(
            {"input": text},
            {"configurable": {"session_id": external_id}}
        )
        reply = result["output"]
        in_tokens = 10
        out_tokens = 20
        print("agnet reply", reply)
        # Record assistant reply and tokens
        session_mgr.append_message(external_id, "assistant", reply)
        session_mgr.add_tokens(
            external_id,
            input_tokens=in_tokens,
            output_tokens=out_tokens,
        )

        # Enqueue logs asynchronously
        enqueue_logs(external_id, text, reply, in_tokens, out_tokens)

        # Send WhatsApp reply
        await send_text_message(external_id, reply)

        return {"status": "ok", "message_id": message_id}

    except Exception as e:
        # Log the error, return 200 with error info so WhatsApp does NOT retry
        error_msg = f"Error processing webhook message: {e}\n{traceback.format_exc()}"
        print(error_msg)
        return {"status": "error", "error": error_msg, "message_id": message_id}
