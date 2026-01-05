# plugins/database.py - MongoDB operations for new features
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from config import DB_URI
import secrets

class DatabaseManager:
    def __init__(self):
        self.client = AsyncIOMotorClient(DB_URI)
        self.db = self.client["vj_file_store"]
    
    # Force-join channels collection
    async def add_force_channel(self, channel_data):
        await self.db.force_channels.insert_one({
            **channel_data,
            "created_at": datetime.now(),
            "is_active": True
        })
    
    async def get_force_channels(self):
        return await self.db.force_channels.find({"is_active": True}).to_list(length=20)
    
    async def remove_force_channel(self, channel_id):
        await self.db.force_channels.delete_one({"channel_id": channel_id})
    
    # Sessions collection
    async def create_session(self, user_id, duration_hours=6):
        session_id = secrets.token_hex(16)
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "start_time": datetime.now(),
            "expiry_time": datetime.now() + timedelta(hours=duration_hours),
            "is_active": True
        }
        await self.db.sessions.insert_one(session_data)
        return session_id
    
    async def get_active_session(self, user_id):
        return await self.db.sessions.find_one({
            "user_id": user_id,
            "is_active": True,
            "expiry_time": {"$gt": datetime.now()}
        })
    
    async def expire_session(self, user_id):
        await self.db.sessions.update_many(
            {"user_id": user_id, "is_active": True},
            {"$set": {"is_active": False}}
        )
    
    # Verification tokens
    async def create_verification(self, user_id, short_url=None):
        token = secrets.token_hex(16)
        verification = {
            "token": token,
            "user_id": user_id,
            "created_at": datetime.now(),
            "short_url": short_url,
            "is_used": False,
            "is_bypassed": False,
            "callback_time": None
        }
        await self.db.verifications.insert_one(verification)
        return token
    
    async def verify_token(self, token, user_id):
        verification = await self.db.verifications.find_one({
            "token": token,
            "user_id": user_id,
            "is_used": False
        })
        
        if not verification:
            return None, None
        
        time_diff = (datetime.now() - verification["created_at"]).total_seconds()
        is_bypassed = time_diff < 35  # Anti-bypass check
        
        await self.db.verifications.update_one(
            {"_id": verification["_id"]},
            {"$set": {
                "is_used": True,
                "is_bypassed": is_bypassed,
                "callback_time": datetime.now(),
                "time_diff": time_diff
            }}
        )
        
        return verification, is_bypassed
    
    # Analytics
    async def log_link_access(self, user_id, link_id, link_type="single"):
        await self.db.link_access.insert_one({
            "user_id": user_id,
            "link_id": link_id,
            "link_type": link_type,
            "accessed_at": datetime.now(),
            "ip": None  # Can add IP tracking if needed
        })
    
    async def get_user_stats(self, user_id):
        total_access = await self.db.link_access.count_documents({"user_id": user_id})
        today_access = await self.db.link_access.count_documents({
            "user_id": user_id,
            "accessed_at": {"$gte": datetime.now().replace(hour=0, minute=0, second=0)}
        })
        
        return {
            "total_access": total_access,
            "today_access": today_access
        }
    
    # Admin settings
    async def get_setting(self, key, default=None):
        setting = await self.db.settings.find_one({"key": key})
        return setting["value"] if setting else default
    
    async def set_setting(self, key, value):
        await self.db.settings.update_one(
            {"key": key},
            {"$set": {"value": value, "updated_at": datetime.now()}},
            upsert=True
        )

# Global database instance
db = DatabaseManager()
