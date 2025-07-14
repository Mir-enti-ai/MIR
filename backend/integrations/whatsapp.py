import httpx
from pydantic import BaseModel
from config import settings

class OutboundMessage(BaseModel):
    to: str
    body: str

async def send_text_message(to_number: str, body: str) -> dict:
    url = f"https://graph.facebook.com/v22.0/{settings.whatsapp_phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {settings.whatsapp_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": body},
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        return resp.json()



