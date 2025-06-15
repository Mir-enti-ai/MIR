import asyncio

user_upsert_queue: asyncio.Queue = asyncio.Queue()
chat_log_queue: asyncio.Queue  = asyncio.Queue()
