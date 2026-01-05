# migrate_fsub.py
from motor.motor_asyncio import AsyncIOMotorClient
from config import DB_URI
import asyncio

async def migrate_fsub():
    """Create FSub collections"""
    client = AsyncIOMotorClient(DB_URI)
    db = client.get_database()
    
    collections = ["fsub_channels", "fsub_verification"]
    
    existing = await db.list_collection_names()
    
    for col in collections:
        if col not in existing:
            await db.create_collection(col)
            print(f"✅ Created: {col}")
    
    # Create indexes
    await db.fsub_channels.create_index("channel_id", unique=True)
    await db.fsub_channels.create_index([("is_enabled", 1), ("is_active", 1)])
    await db.fsub_verification.create_index([("user_id", 1), ("channel_id", 1)])
    await db.fsub_verification.create_index("verified_until", expireAfterSeconds=0)
    
    # Set default FSub status
    await db.settings.update_one(
        {"key": "fsub_enabled"},
        {"$set": {"value": "0", "updated_at": datetime.now()}},  # Disabled by default
        upsert=True
    )
    
    print("🎉 FSub migration completed!")
    client.close()

if __name__ == "__main__":
    import asyncio
    from datetime import datetime
    asyncio.run(migrate_fsub())
