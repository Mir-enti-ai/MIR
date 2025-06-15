# workers/chat_logger.py
import asyncio
from pymongo import InsertOne
from config import chat_logs_collection
from workers.queues import chat_log_queue

def start_chat_logger():
    async def worker():
        while True:
            ops = []
            try:
                for _ in range(200):
                    msg = chat_log_queue.get_nowait()
                    ops.append(InsertOne(msg))
            except asyncio.QueueEmpty:
                pass

            if ops:
                chat_logs_collection.bulk_write(ops, ordered=False)
            await asyncio.sleep(30)

    asyncio.create_task(worker())
