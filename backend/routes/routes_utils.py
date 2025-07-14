from enum import Enum
from pydantic import BaseModel, Field
import httpx
from config import settings
from langchain_core.messages import HumanMessage
from openai import AsyncOpenAI
from langchain_core.documents import Document
from io import BytesIO
import base64


# Hardcoded verify token for testing
WHATSAPP_VERIFY_TOKEN = "12345"
class MessageType(Enum):
    TEXT = 'text'
    IMAGE = 'image'
    AUDIO = 'audio'
    UNKNOWN = 'unknown'


class ReceivedMessage(BaseModel):
    type: MessageType = Field(default=MessageType.UNKNOWN)
    content: str | bytes | None = None 
    caption: str | None = None  # For image/audio captions 





async def download_media(media_id: str) -> bytes:
    """Download media from WhatsApp."""
    media_metadata_url = f"https://graph.facebook.com/v21.0/{media_id}"
    headers = {"Authorization": f"Bearer {settings.whatsapp_token}"}

    async with httpx.AsyncClient() as client:
        metadata_response = await client.get(media_metadata_url, headers=headers)
        metadata_response.raise_for_status()
        metadata = metadata_response.json()
        download_url = metadata.get("url")

        media_response = await client.get(download_url, headers=headers)
        media_response.raise_for_status()
        return media_response.content



async def transcribe_audio(audio_bytes: bytes) -> str:
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    
    audio_file = BytesIO(audio_bytes)
    audio_file.name = "audio.ogg"
    
    transcript = await client.audio.transcriptions.create(
        file=audio_file,
        language="ar",
        model="whisper-1",  
    )
    
    return transcript.text
    


async def parse_whatsapp_message(message: dict) -> ReceivedMessage:
    if "type" not in message:
        return MessageType.UNKNOWN
    
    msg_type = message["type"]



    if msg_type == MessageType.TEXT.value:
        text = message.get("text", {}).get("body", None)
        return ReceivedMessage(type=MessageType.TEXT, content=text)
    


    elif msg_type == MessageType.IMAGE.value:
        media_id = message.get("image", {}).get("id", None)
        caption = message.get("image", {}).get("caption", None)  # Extract caption
        if media_id:
            media_byte = await download_media(media_id)
            return ReceivedMessage(type=MessageType.IMAGE, content=media_byte, caption=caption)
        else:
            return ReceivedMessage(type=MessageType.IMAGE, content=None, caption=caption)
    


    elif msg_type == MessageType.AUDIO.value:
        media_id = message.get("audio", {}).get("id", None)
        if media_id:
            media_byte = await download_media(media_id)
            return ReceivedMessage(type=MessageType.AUDIO, content=media_byte)
        else:
            return ReceivedMessage(type=MessageType.AUDIO, content=None)


    else:
        return ReceivedMessage(type=MessageType.UNKNOWN, content=None)





async def rapup_message(meesage:ReceivedMessage)-> HumanMessage:
    """Convert ReceivedMessage to HumanMessage."""
    if meesage.type == MessageType.TEXT:
        return HumanMessage(content=meesage.content)
    
    elif meesage.type == MessageType.IMAGE:
        # Use caption as the user's question/message about the image
        prompt = meesage.caption  
        # Convert bytes to base64 string
        image_base64 = base64.b64encode(meesage.content).decode('utf-8')
        return HumanMessage(
            content=[
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
                }
            ]
        )
    elif meesage.type == MessageType.AUDIO:
        # Audio messages don't have captions
        content=await transcribe_audio(meesage.content)
        return HumanMessage(content=content)
    else:
        return HumanMessage(content="Unknown message type")


