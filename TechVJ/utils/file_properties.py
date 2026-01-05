# Don't Remove Credit @VJ_Bots
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

from pyrogram import Client
from typing import Any, Optional
from pyrogram.types import Message
from pyrogram.file_id import FileId
from pyrogram.raw.types.messages import Messages

# REMOVED the problematic import
# from TechVJ.server.exceptions import FIleNotFound

# Add a local FileNotFound exception instead
class FIleNotFound(Exception):
    """Custom File Not Found exception"""
    pass

async def parse_file_id(message: "Message") -> Optional[FileId]:
    media = get_media_from_message(message)
    if media:
        return FileId.decode(media.file_id)
    return None

async def parse_file_unique_id(message: "Messages") -> Optional[str]:
    media = get_media_from_message(message)
    if media:
        return media.file_unique_id
    return None

async def get_file_ids(client: Client, chat_id: int, id: int) -> Optional[FileId]:
    try:
        message = await client.get_messages(chat_id, id)
        if message.empty:
            raise FIleNotFound("Message is empty or not found")
        
        media = get_media_from_message(message)
        if not media:
            raise FIleNotFound("No media found in message")
        
        file_unique_id = await parse_file_unique_id(message)
        file_id = await parse_file_id(message)
        
        if file_id and file_unique_id:
            setattr(file_id, "file_size", getattr(media, "file_size", 0))
            setattr(file_id, "mime_type", getattr(media, "mime_type", ""))
            setattr(file_id, "file_name", getattr(media, "file_name", ""))
            setattr(file_id, "unique_id", file_unique_id)
        
        return file_id
    except Exception as e:
        raise FIleNotFound(f"Failed to get file ids: {str(e)}")

def get_media_from_message(message: "Message") -> Any:
    media_types = (
        "audio",
        "document", 
        "photo",
        "sticker",
        "animation",
        "video",
        "voice",
        "video_note",
    )
    for attr in media_types:
        media = getattr(message, attr, None)
        if media:
            return media
    return None

def get_hash(media_msg: Message) -> str:
    media = get_media_from_message(media_msg)
    if media:
        file_unique_id = getattr(media, "file_unique_id", "")
        if file_unique_id:
            return file_unique_id[:6]
    return ""

def get_name(media_msg: Message) -> str:
    media = get_media_from_message(media_msg)
    if media:
        return getattr(media, 'file_name', "")
    return ""

def get_media_file_size(m):
    media = get_media_from_message(m)
    if media:
        return getattr(media, "file_size", 0)
    return 0

# Add this new function to resolve the import error
def get_file_ids_simple(client: Client, message: Message) -> tuple:
    """
    Simple version of get_file_ids that doesn't cause circular imports
    Returns: (channel_id, message_id, file_unique_id)
    """
    try:
        if message.media:
            media = get_media_from_message(message)
            if media:
                file_id = getattr(media, "file_id", "")
                file_unique_id = getattr(media, "file_unique_id", "")
                
                # Get channel ID
                if hasattr(message, 'forward_from_chat') and message.forward_from_chat:
                    channel_id = message.forward_from_chat.id
                else:
                    channel_id = message.chat.id
                
                return channel_id, message.id, file_unique_id
    except Exception:
        pass
    return None, None, None
