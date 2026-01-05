# plugins/database.py - MongoDB operations for new features
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from config import DB_URI
import secrets

class DatabaseManager:
    def __init__(self):
        self.client = AsyncIOMotorClient(DB_URI)
        self.db = self.client["vj_file_store"]
    
 # Add these methods to your existing DatabaseManager class in plugins/database.py

class DatabaseManager:
    # ... existing methods ...
    
    # FSub Channels Management
    async def add_fsub_channel(self, channel_data):
        """Add channel to FSub list"""
        # Check if already exists
        existing = await self.db.fsub_channels.find_one({
            "channel_id": channel_data["channel_id"]
        })
        
        if existing:
            await self.db.fsub_channels.update_one(
                {"channel_id": channel_data["channel_id"]},
                {"$set": {
                    **channel_data,
                    "updated_at": datetime.now(),
                    "is_active": True
                }}
            )
        else:
            await self.db.fsub_channels.insert_one({
                **channel_data,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "is_active": True,
                "is_enabled": True  # Enable by default
            })
    
    async def get_fsub_channels(self, active_only=True):
        """Get all FSub channels"""
        query = {"is_enabled": True}
        if active_only:
            query["is_active"] = True
        
        return await self.db.fsub_channels.find(query).to_list(length=50)
    
    async def toggle_fsub_channel(self, channel_id, enable=True):
        """Enable/disable FSub channel"""
        await self.db.fsub_channels.update_one(
            {"channel_id": channel_id},
            {"$set": {"is_enabled": enable, "updated_at": datetime.now()}}
        )
    
    async def remove_fsub_channel(self, channel_id):
        """Remove FSub channel (soft delete)"""
        await self.db.fsub_channels.update_one(
            {"channel_id": channel_id},
            {"$set": {"is_active": False, "is_enabled": False}}
        )
    
    async def get_fsub_status(self):
        """Check if FSub system is enabled globally"""
        setting = await self.get_setting("fsub_enabled", "1")
        return setting == "1"
    
    async def set_fsub_status(self, enabled=True):
        """Enable/disable FSub system globally"""
        await self.set_setting("fsub_enabled", "1" if enabled else "0")
    
    async def get_user_fsub_status(self, user_id):
        """Check which channels user has joined"""
        channels = await self.get_fsub_channels()
        user_status = {}
        
        for channel in channels:
            # Check if we've already verified this user for this channel
            verified = await self.db.fsub_verification.find_one({
                "user_id": user_id,
                "channel_id": channel["channel_id"],
                "verified_until": {"$gt": datetime.now()}
            })
            
            user_status[channel["channel_id"]] = {
                "channel": channel,
                "verified": bool(verified),
                "verified_until": verified["verified_until"] if verified else None
            }
        
        return user_status
    
    async def verify_user_fsub(self, user_id, channel_id, days_valid=7):
        """Mark user as verified for a channel"""
        verified_until = datetime.now() + timedelta(days=days_valid)
        
        await self.db.fsub_verification.update_one(
            {"user_id": user_id, "channel_id": channel_id},
            {"$set": {
                "verified_at": datetime.now(),
                "verified_until": verified_until,
                "is_active": True
            }},
            upsert=True
        )
    
    async def check_fsub_requirement(self, user_id):
        """
        Check if user needs to join any channels
        Returns: (required: bool, channels_to_join: list, already_joined: list)
        """
        # Check if FSub is enabled globally
        if not await self.get_fsub_status():
            return False, [], []
        
        channels = await self.get_fsub_channels()
        if not channels:
            return False, [], []
        
        channels_to_join = []
        already_joined = []
        
        for channel in channels:
            # Check verification status
            verified = await self.db.fsub_verification.find_one({
                "user_id": user_id,
                "channel_id": channel["channel_id"],
                "verified_until": {"$gt": datetime.now()},
                "is_active": True
            })
            
            if verified:
                already_joined.append(channel)
            else:
                channels_to_join.append(channel)
        
        return len(channels_to_join) > 0, channels_to_join, already_joined
    
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
