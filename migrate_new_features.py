# migrate_new_features.py
from motor.motor_asyncio import AsyncIOMotorClient
from config import DB_URI
import asyncio

async def migrate():
    """Create new collections for blueprint features"""
    client = AsyncIOMotorClient(DB_URI)
    db = client.get_database()
    
    collections_to_create = [
        "force_channels",
        "sessions", 
        "verifications",
        "link_access",
        "admin_settings",
        "analytics"
    ]
    
    existing = await db.list_collection_names()
    
    for col in collections_to_create:
        if col not in existing:
            await db.create_collection(col)
            print(f"✅ Created: {col}")
    
    # Create indexes
    await db.sessions.create_index([("expiry_time", 1)], expireAfterSeconds=0)
    await db.sessions.create_index([("user_id", 1), ("is_active", 1)])
    await db.verifications.create_index("token", unique=True)
    await db.verifications.create_index([("created_at", -1)])
    
    print("🎉 Migration completed!")
    client.close()

if __name__ == "__main__":
    asyncio.run(migrate())
