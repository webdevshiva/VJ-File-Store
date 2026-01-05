# plugins/verification.py
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from plugins.database import db
from config import ADMINS
import asyncio

async def check_access(client, user_id, message=None):
    """
    Check if user can access files
    Returns: (allowed: bool, reason: str, session_id: str or None)
    """
    from datetime import datetime
    
    # Admins have full access
    if user_id in ADMINS:
        return True, "admin", None
    
    # Check active session
    session = await db.get_active_session(user_id)
    if session:
        return True, "active_session", session["session_id"]
    
    # Check force-join channels
    force_channels = await db.get_force_channels()
    if force_channels:
        for channel in force_channels:
            try:
                member = await client.get_chat_member(channel["channel_id"], user_id)
                if member.status not in ["member", "administrator", "creator"]:
                    if message:
                        # Show force-join message
                        buttons = []
                        for ch in force_channels:
                            buttons.append([InlineKeyboardButton(
                                f"Join {ch['title']}",
                                url=ch["invite_link"]
                            )])
                        
                        buttons.append([InlineKeyboardButton("✅ I've Joined", callback_data="check_force_join")])
                        
                        await message.reply(
                            "🔔 **Channel Membership Required**\n\n"
                            "You need to join these channels to access files:\n\n"
                            f"**{len(force_channels)} channel(s) to join**",
                            reply_markup=InlineKeyboardMarkup(buttons)
                        )
                    return False, "force_join_required", None
            except Exception as e:
                print(f"Error checking membership: {e}")
                continue
    
    # No session, start verification
    return False, "verification_required", None

async def start_verification(client, user_id, message):
    """Start verification process for user"""
    from utils import get_short_url  # Existing utility
    
    # Create verification token
    token = await db.create_verification(user_id)
    
    # Generate verification URL (use your website or a simple page)
    verify_url = f"https://your-domain.com/verify/{token}"
    
    # Shorten URL using existing system
    short_url = await get_short_url(verify_url)
    
    # Store in user data for callback
    await db.set_setting(f"pending_verification:{user_id}", token)
    
    # Send verification message
    buttons = [
        [
            InlineKeyboardButton("🌐 Verify Now", url=short_url),
            InlineKeyboardButton("📋 Copy", callback_data=f"copy_verify_{short_url}")
        ],
        [InlineKeyboardButton("🔄 Retry", callback_data="retry_verify")]
    ]
    
    await message.reply(
        "🔐 **Verification Required**\n\n"
        "**Unlock 6-hour unlimited access:**\n"
        "1. Click the link below\n"
        "2. Wait **35+ seconds** on the page\n"
        "3. Return here\n\n"
        "⚠️ **Anti-Bypass Protection:**\n"
        "Completing too fast will be detected!",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def complete_verification(client, user_id, token):
    """Complete verification and create session"""
    verification, is_bypassed = await db.verify_token(token, user_id)
    
    if not verification:
        return False, "Invalid or expired token"
    
    if is_bypassed:
        # Bypass detected
        await db.set_setting(f"bypass_detected:{user_id}:{datetime.now().timestamp()}", "1")
        return False, "Bypass detected! Complete verification properly."
    
    # Create 6-hour session
    session_id = await db.create_session(user_id, 6)
    
    # Clear pending verification
    await db.set_setting(f"pending_verification:{user_id}", "")
    
    return True, session_id

# Callback handler for verification
@Client.on_callback_query(filters.regex("^check_force_join$"))
async def check_force_join_callback(client, callback_query):
    """Check if user joined all channels"""
    user_id = callback_query.from_user.id
    force_channels = await db.get_force_channels()
    
    all_joined = True
    for channel in force_channels:
        try:
            member = await client.get_chat_member(channel["channel_id"], user_id)
            if member.status not in ["member", "administrator", "creator"]:
                all_joined = False
                break
        except:
            all_joined = False
    
    if all_joined:
        await callback_query.message.edit_text(
            "✅ **All channels joined!**\n\n"
            "Now you need to verify to access files.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔐 Start Verification", callback_data="start_verification")]
            ])
        )
    else:
        await callback_query.answer("You haven't joined all channels yet!", show_alert=True)

@Client.on_callback_query(filters.regex("^start_verification$"))
async def start_verification_callback(client, callback_query):
    """Start verification from callback"""
    await start_verification(client, callback_query.from_user.id, callback_query.message)
    await callback_query.answer()

@Client.on_callback_query(filters.regex("^retry_verify$"))
async def retry_verification_callback(client, callback_query):
    """Retry verification"""
    await start_verification(client, callback_query.from_user.id, callback_query.message)
    await callback_query.answer("New verification started!")
