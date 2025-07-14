# schemas/user.py
from datetime import datetime, timezone
from bson import ObjectId
from config import users_collection

def upsert_user(external_id: str, name: str = None) -> ObjectId:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    update = {"lastSeenAt": now}
    if name:
        update["name"] = name
    result = users_collection.update_one(
        {"externalId": external_id},
        {
            "$setOnInsert": {"createdAt": now, "name": name or "Unknown"},
            "$set": update,
        },
        upsert=True
    )
    if result.upserted_id:
        return result.upserted_id
    doc = users_collection.find_one({"externalId": external_id}, {"_id": 1})
    return doc["_id"]
