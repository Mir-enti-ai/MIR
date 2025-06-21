# workers/user_writer.py
import asyncio
from pymongo import UpdateOne
from config import users_collection
from workers.queues import user_upsert_queue

def start_user_writer():
    async def worker():
        while True:
            ops = []
            try:
                for _ in range(100):
                    u = user_upsert_queue.get_nowait()
                    ops.append(
                        UpdateOne(
                            {"externalId": u["externalId"]},
                            {
                                "$setOnInsert": {"createdAt": u["createdAt"]},
                                "$set": {"name": u["name"], 
                                         "lastSeenAt": u["lastSeenAt"],
                                          "totalInputTokens": u.get("totalInputTokens", 0),
                                        "totalOutputTokens": u.get("totalOutputTokens", 0),
                                            "summary": u.get("summary", None),
                                         
                                         },
                            },
                            upsert=True
                        )
                    )
            except asyncio.QueueEmpty:
                pass

            if ops:
                users_collection.bulk_write(ops, ordered=False)
            await asyncio.sleep(30)

    asyncio.create_task(worker())
