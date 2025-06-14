from pydantic_settings import BaseSettings
from pymongo import MongoClient
from pymongo.server_api import ServerApi

class Settings(BaseSettings):
    # MongoDB
    mongo_uri: str

    # WhatsApp
    whatsapp_token: str
    whatsapp_phone_number_id: str
    whatsapp_verify_token: str
    # OpenAI
    openai_api_key: str
    #tavily
    tavily_api_key: str
    # groq
    groq_api_key: str
    class Config:
        env_file = ".env"


settings = Settings()

## --- MongoDB connection setup ---
try:
    mongo_client = MongoClient(
        settings.mongo_uri,
        server_api=ServerApi("1")
    )
    db = mongo_client["MIR"]
    users_collection = db["users"]
    chat_logs_collection = db["chat_logs"]
    print("MongoDB connection established.")
    mongo_client.server_info()
except Exception as e:
    print("Failed to connect to MongoDB:", e)
    mongo_client = None
    db = None
    users_collection = None
    chat_logs_collection = None

