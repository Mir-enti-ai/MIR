from fastapi import APIRouter, Request, HTTPException, Response
from workers.queues import user_upsert_queue, chat_log_queue
from sessions.manager import session_mgr
from utils import now_utc_str
from config import settings
from integrations.whatsapp import send_text_message
from agents.openai_agent import runnable_chain
from agents.qroq_agent import MirAgent
import traceback

from langchain_core.messages import HumanMessage


router = APIRouter()


async def get_openai_response(text:str,session_id:str):
    try:
        # Invoke the AI chain for a response openai
        result = await runnable_chain.ainvoke(
            {"input": text},
            {"configurable": {"session_id": session_id}}
        )
        reply = result["output"]
        in_tokens = 10
        out_tokens = 20

        return {
            "reply":reply,
            "input_tokens":in_tokens,
            "output_tokens":out_tokens
        }
    except Exception as e:
        return  {
            reply:f"Sorry We Have Tech Problem: {e}",
            "input_tokens":0,
            "output_tokens":0

        }




async def get_groq_response(text: str, session_id: str) -> str:
    """
    Call the Groq agent with user input and return the response.
    """
    try:
        agent = MirAgent(session_id=session_id)
        # get history from session id 
        history = session_mgr.get_history(session_id).messages 
        messages = history + [HumanMessage(content=text)]
        response = await agent.ask(messages)
        return {
                    "reply":response.get("reply", ""),
                    "input_tokens":response.get("input_tokens", 0),
                    "output_tokens":response.get("output_tokens", 0)
                }
    except Exception as e:
        return  {
            "reply":f"Sorry We Have Tech Problem: {e}",
            "input_tokens":0,
            "output_tokens":0

        }





def enqueue_logs(user_id, text, reply, in_tokens, out_tokens,total_in_tokens=0, total_out_tokens=0):
    now = now_utc_str()
    # Queue user upsert (worker will write to Mongo)
    user_upsert_queue.put_nowait({
        "externalId": user_id,
        "name":       None,      # if you know the name, include it here
        "createdAt":  now,
        "lastSeenAt": now,
        "totalInputTokens":  total_in_tokens,
        "totalOutputTokens": total_out_tokens

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
    print(settings.whatsapp_verify_token, token)
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


  

    try:
       # opernai_agnet 
        result = await get_openai_response(text, external_id)        
        #grqoq_agent
        # result = await get_groq_response(text, external_id)
        # Extract reply and token usage from the result

        reply = result.get("reply", "")
        in_tokens = result.get("input_tokens", 0)
        out_tokens = result.get("output_tokens", 0)
        

         # Send WhatsApp reply
        await send_text_message(external_id, reply)


        # Append incoming user message
        session_mgr.append_message(external_id, "user", text)
        # Record assistant reply and tokens
        session_mgr.append_message(external_id, "assistant", reply)
        session_mgr.add_tokens(
            external_id,
            input_tokens=result.get("input_tokens", 0),
            output_tokens=result.get("output_tokens", 0)
        )

        # Enqueue logs asynchronously
        total_in_tokens = session_mgr.get(external_id)["totalInputTokens"]
        total_out_tokens = session_mgr.get(external_id)["totalOutputTokens"]
        enqueue_logs(external_id, text, reply, in_tokens, out_tokens,total_in_tokens=total_in_tokens, total_out_tokens=total_out_tokens)

       

        return {"status": "ok", "message_id": message_id}

    except Exception as e:
        # Log the error, return 200 with error info so WhatsApp does NOT retry
        error_msg = f"Error processing webhook message: {e}\n{traceback.format_exc()}"
        print(error_msg)
        return {"status": "error", "error": error_msg, "message_id": message_id}
