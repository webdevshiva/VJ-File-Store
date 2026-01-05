# plugins/admin_panel.py
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from plugins.database import db
from config import ADMINS
from datetime import datetime

@Client.on_message(filters.command("admin") & filters.user(ADMINS))
async def admin_panel_command(client, message):
    """Main admin panel"""
    buttons = [
        [
            InlineKeyboardButton("📊 Statistics", callback_data="admin_stats"),
            InlineKeyboardButton("🔔 Force Join", callback_data="admin_force")
        ],
        [
            InlineKeyboardButton("👥 Users", callback_data="admin_users"),
            InlineKeyboardButton("🔗 Links", callback_data="admin_links")
        ],
        [
            InlineKeyboardButton("🛡️ Security", callback_data="admin_security"),
            InlineKeyboardButton("⚙️ Settings", callback_data="admin_settings")
        ]
    ]
    
    await message.reply(
        "👑 **Admin Control Panel**\n\n"
        "Select a category to manage:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@Client.on_callback_query(filters.regex("^admin_"))
async def admin_callback_handler(client, callback_query):
    """Handle admin panel callbacks"""
    action = callback_query.data.split("_")[1]
    user_id = callback_query.from_user.id
    
    if user_id not in ADMINS:
        await callback_query.answer("Access denied!", show_alert=True)
        return
    
    if action == "stats":
        # Get statistics
        total_users = await db.db.users.count_documents({})
        active_sessions = await db.db.sessions.count_documents({"is_active": True})
        total_links = await db.db.links.count_documents({})
        
        text = (
            f"📊 **Bot Statistics**\n\n"
            f"• Total Users: `{total_users}`\n"
            f"• Active Sessions: `{active_sessions}`\n"
            f"• Total Links: `{total_links}`\n"
            f"• Force Channels: `{len(await db.get_force_channels())}`\n"
            f"• Today's Access: `{await db.db.link_access.count_documents({'accessed_at': {'$gte': datetime.now().replace(hour=0, minute=0, second=0)}})}`"
        )
        
        buttons = [[InlineKeyboardButton("🔄 Refresh", callback_data="admin_stats")],
                   [InlineKeyboardButton("⬅️ Back", callback_data="admin_back")]]
    
    elif action == "force":
        channels = await db.get_force_channels()
        text = f"🔔 **Force-Join Channels:** `{len(channels)}`\n\n"
        
        for i, channel in enumerate(channels, 1):
            text += f"{i}. **{channel['title']}**\n"
            text += f"   ID: `{channel['channel_id']}`\n"
            if channel.get('username'):
                text += f"   @{channel['username']}\n"
            text += f"   Added: {channel.get('created_at', 'N/A')}\n\n"
        
        buttons = [
            [InlineKeyboardButton("➕ Add Channel", callback_data="admin_addforce")],
            [InlineKeyboardButton("🗑️ Remove", callback_data="admin_removeforce")],
            [InlineKeyboardButton("⬅️ Back", callback_data="admin_back")]
        ]
    
    elif action == "back":
        # Return to main panel
        buttons = [
            [
                InlineKeyboardButton("📊 Statistics", callback_data="admin_stats"),
                InlineKeyboardButton("🔔 Force Join", callback_data="admin_force")
            ],
            [
                InlineKeyboardButton("👥 Users", callback_data="admin_users"),
                InlineKeyboardButton("🔗 Links", callback_data="admin_links")
            ],
            [
                InlineKeyboardButton("🛡️ Security", callback_data="admin_security"),
                InlineKeyboardButton("⚙️ Settings", callback_data="admin_settings")
            ]
        ]
        text = "👑 **Admin Control Panel**\n\nSelect a category to manage:"
    
    else:
        text = f"🛠️ **{action.title()} Management**\n\nThis section is under development."
        buttons = [[InlineKeyboardButton("⬅️ Back", callback_data="admin_back")]]
    
    try:
        await callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    except:
        await callback_query.message.reply(text, reply_markup=InlineKeyboardMarkup(buttons))
    
    await callback_query.answer()
