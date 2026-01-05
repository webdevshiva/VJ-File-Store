# plugins/fsub.py - Force Subscribe System
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from plugins.database import db
from config import ADMINS
import asyncio

@Client.on_message(filters.command("fsub") & filters.user(ADMINS))
async def fsub_management(client, message: Message):
    """FSub management panel"""
    if len(message.command) > 1:
        subcmd = message.command[1].lower()
        
        if subcmd == "on":
            await db.set_fsub_status(True)
            await message.reply("✅ **FSub system ENABLED**")
            return
            
        elif subcmd == "off":
            await db.set_fsub_status(False)
            await message.reply("✅ **FSub system DISABLED**")
            return
            
        elif subcmd == "status":
            status = await db.get_fsub_status()
            channels = await db.get_fsub_channels()
            
            text = f"🔔 **FSub System Status:** {'✅ **ENABLED**' if status else '❌ **DISABLED**'}\n\n"
            text += f"**Total Channels:** {len(channels)}\n\n"
            
            if channels:
                text += "**Configured Channels:**\n"
                for i, channel in enumerate(channels, 1):
                    text += f"{i}. **{channel.get('title', 'Unknown')}**\n"
                    text += f"   ID: `{channel['channel_id']}`\n"
                    if channel.get('username'):
                        text += f"   @{channel['username']}\n"
                    text += f"   Status: {'✅ Active' if channel.get('is_enabled', True) else '❌ Disabled'}\n\n"
            else:
                text += "No channels configured.\nUse `/fsub add` to add channels."
            
            await message.reply(text)
            return
    
    # Show management panel
    status = await db.get_fsub_status()
    channels_count = len(await db.get_fsub_channels())
    
    text = f"""
🔔 **Force Subscribe Management**

**Status:** {'✅ **ENABLED**' if status else '❌ **DISABLED**'}
**Channels:** {channels_count} configured

**Commands:**
• `/fsub on` - Enable FSub system
• `/fsub off` - Disable FSub system
• `/fsub status` - Show current status
• `/fsub add` - Add channel (reply to forwarded message)
• `/fsub remove <id>` - Remove channel
• `/fsub toggle <id>` - Toggle channel on/off
• `/fsub list` - List all channels
• `/fsub check @username` - Check user's FSub status
    """
    
    await message.reply(text)

@Client.on_message(filters.command("fsub add") & filters.user(ADMINS))
async def fsub_add_channel(client, message: Message):
    """Add channel to FSub list"""
    try:
        if message.reply_to_message and message.reply_to_message.forward_from_chat:
            chat = message.reply_to_message.forward_from_chat
            
            # Get invite link
            try:
                invite = await client.create_chat_invite_link(
                    chat_id=chat.id,
                    member_limit=1,
                    creates_join_request=False
                )
                invite_link = invite.invite_link
            except Exception as e:
                print(f"Could not create invite: {e}")
                if chat.username:
                    invite_link = f"https://t.me/{chat.username}"
                else:
                    # Try to get existing invite links
                    try:
                        invites = await client.get_chat_invite_links(chat.id, limit=1)
                        if invites:
                            invite_link = invites[0].invite_link
                        else:
                            invite_link = "No invite link available"
                    except:
                        invite_link = "No invite link available"
            
            # Add to database
            await db.add_fsub_channel({
                "channel_id": chat.id,
                "username": chat.username,
                "title": chat.title,
                "invite_link": invite_link,
                "added_by": message.from_user.id,
                "chat_type": "channel" if hasattr(chat, 'type') and chat.type == "channel" else "group"
            })
            
            await message.reply(
                f"✅ **Channel added to FSub:**\n\n"
                f"**Name:** {chat.title}\n"
                f"**ID:** `{chat.id}`\n"
                f"**Type:** {'Channel' if chat.type == 'channel' else 'Group'}\n"
                f"**Invite:** {invite_link[:50]}..."
            )
            
        elif len(message.command) > 2:
            # Add by ID and username
            try:
                channel_id = int(message.command[2])
                username = message.command[3] if len(message.command) > 3 else None
                
                # Try to get chat info
                try:
                    chat = await client.get_chat(channel_id)
                except:
                    # If not accessible, use provided info
                    chat = type('obj', (object,), {
                        'id': channel_id,
                        'username': username,
                        'title': f"Channel {channel_id}",
                        'type': 'channel'
                    })()
                
                invite_link = f"https://t.me/{username}" if username else f"https://t.me/c/{str(abs(channel_id))[4:]}"
                
                await db.add_fsub_channel({
                    "channel_id": channel_id,
                    "username": username,
                    "title": getattr(chat, 'title', f"Channel {channel_id}"),
                    "invite_link": invite_link,
                    "added_by": message.from_user.id,
                    "chat_type": "channel"
                })
                
                await message.reply(f"✅ **Channel added by ID:** `{channel_id}`")
                
            except ValueError:
                await message.reply("❌ Invalid channel ID. Must be a number.")
            except Exception as e:
                await message.reply(f"❌ Error: {str(e)}")
                
        else:
            await message.reply(
                "❌ **How to add FSub channel:**\n\n"
                "**Method 1:** Forward a message from the channel and reply with `/fsub add`\n"
                "**Method 2:** `/fsub add <channel_id> <username>`\n\n"
                "Example: `/fsub add -1001234567890 channel_username`"
            )
            
    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}")

@Client.on_message(filters.command("fsub remove") & filters.user(ADMINS))
async def fsub_remove_channel(client, message: Message):
    """Remove channel from FSub"""
    try:
        if len(message.command) > 2:
            channel_id = int(message.command[2])
            await db.remove_fsub_channel(channel_id)
            await message.reply(f"✅ **Channel removed:** `{channel_id}`")
        else:
            await message.reply("❌ Usage: `/fsub remove <channel_id>`")
    except ValueError:
        await message.reply("❌ Invalid channel ID")
    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}")

@Client.on_message(filters.command("fsub toggle") & filters.user(ADMINS))
async def fsub_toggle_channel(client, message: Message):
    """Toggle channel on/off"""
    try:
        if len(message.command) > 3:
            channel_id = int(message.command[2])
            action = message.command[3].lower()
            
            if action in ["on", "enable", "true", "1"]:
                enable = True
                status = "✅ **ENABLED**"
            elif action in ["off", "disable", "false", "0"]:
                enable = False
                status = "❌ **DISABLED**"
            else:
                await message.reply("❌ Use: `on` or `off`")
                return
            
            await db.toggle_fsub_channel(channel_id, enable)
            await message.reply(f"✅ **Channel {status}:** `{channel_id}`")
            
        else:
            await message.reply("❌ Usage: `/fsub toggle <channel_id> <on/off>`")
    except ValueError:
        await message.reply("❌ Invalid channel ID")
    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}")

@Client.on_message(filters.command("fsub list") & filters.user(ADMINS))
async def fsub_list_channels(client, message: Message):
    """List all FSub channels"""
    channels = await db.get_fsub_channels(active_only=False)
    
    if not channels:
        await message.reply("📭 No FSub channels configured.")
        return
    
    text = "🔔 **FSub Channels List**\n\n"
    
    for i, channel in enumerate(channels, 1):
        status = "✅" if channel.get("is_enabled", True) else "❌"
        active = "🟢" if channel.get("is_active", True) else "🔴"
        
        text += f"{i}. {status} {active} **{channel.get('title', 'Unknown')}**\n"
        text += f"   ID: `{channel['channel_id']}`\n"
        if channel.get('username'):
            text += f"   @{channel['username']}\n"
        text += f"   Type: {channel.get('chat_type', 'unknown')}\n"
        text += f"   Added: {channel.get('created_at', 'N/A')}\n\n"
    
    await message.reply(text)

@Client.on_message(filters.command("fsub check"))
async def fsub_check_user(client, message: Message):
    """Check user's FSub status (Admin only or user checking themselves)"""
    user_id = message.from_user.id
    
    # Check if admin or checking own status
    if user_id not in ADMINS:
        # Non-admin can only check themselves
        if len(message.command) > 2 and message.command[2].startswith("@"):
            await message.reply("❌ Only admins can check other users.")
            return
    
    target_user = user_id
    if user_id in ADMINS and len(message.command) > 2:
        # Admin checking specific user
        username = message.command[2].replace("@", "")
        try:
            user = await client.get_users(username)
            target_user = user.id
        except:
            await message.reply("❌ User not found.")
            return
    
    # Check FSub requirement
    required, to_join, already_joined = await db.check_fsub_requirement(target_user)
    
    text = f"🔔 **FSub Status for User ID:** `{target_user}`\n\n"
    
    if not required:
        text += "✅ **All channels joined!**\n"
        if already_joined:
            text += f"\n**Joined channels:** {len(already_joined)}\n"
            for channel in already_joined[:5]:  # Show first 5
                text += f"• {channel.get('title', 'Unknown')}\n"
            if len(already_joined) > 5:
                text += f"• ... and {len(already_joined) - 5} more\n"
    else:
        text += f"❌ **Need to join {len(to_join)} channel(s)**\n\n"
        text += "**Channels to join:**\n"
        for i, channel in enumerate(to_join, 1):
            text += f"{i}. {channel.get('title', 'Unknown')}\n"
            if channel.get('invite_link'):
                text += f"   [Join Channel]({channel['invite_link']})\n"
    
    await message.reply(text, disable_web_page_preview=True)

async def check_user_fsub(client, user_id, chat_id=None):
    """
    Check if user has joined all required channels
    Returns: (allowed: bool, missing_channels: list, message_text: str)
    """
    # Check if FSub is enabled
    if not await db.get_fsub_status():
        return True, [], ""
    
    # Get FSub requirements
    required, to_join, already_joined = await db.check_fsub_requirement(user_id)
    
    if not required:
        # User has joined all channels
        return True, [], ""
    
    # User needs to join channels
    missing_channels = to_join
    
    # Build message
    message_text = f"🔔 **Subscription Required**\n\n"
    message_text += f"Join {len(missing_channels)} channel(s) to continue:\n\n"
    
    buttons = []
    for channel in missing_channels:
        if channel.get('invite_link'):
            buttons.append([
                InlineKeyboardButton(
                    f"Join {channel.get('title', 'Channel')}",
                    url=channel['invite_link']
                )
            ])
    
    # Add check button
    buttons.append([
        InlineKeyboardButton("✅ I've Joined - Check Now", callback_data=f"fsub_check_{user_id}")
    ])
    
    return False, missing_channels, message_text, InlineKeyboardMarkup(buttons)

@Client.on_callback_query(filters.regex("^fsub_check_"))
async def fsub_check_callback(client, callback_query):
    """Check if user has joined channels after clicking button"""
    user_id = callback_query.from_user.id
    callback_user_id = int(callback_query.data.split("_")[2])
    
    # Verify this callback is for the right user
    if user_id != callback_user_id:
        await callback_query.answer("This button is not for you!", show_alert=True)
        return
    
    # Check FSub status
    allowed, missing_channels, message_text, _ = await check_user_fsub(client, user_id)
    
    if allowed:
        # User has joined all channels
        # Mark as verified for 7 days
        for channel in await db.get_fsub_channels():
            await db.verify_user_fsub(user_id, channel["channel_id"], 7)
        
        await callback_query.message.edit_text(
            "✅ **All channels verified!**\n\n"
            "You can now access the bot features.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎉 Continue", callback_data="fsub_continue")]
            ])
        )
    else:
        # Still missing channels
        await callback_query.answer(
            f"You still need to join {len(missing_channels)} channel(s)!",
            show_alert=True
        )
    
    await callback_query.answer()

@Client.on_callback_query(filters.regex("^fsub_continue$"))
async def fsub_continue_callback(client, callback_query):
    """Continue after FSub verification"""
    await callback_query.message.delete()
    await callback_query.answer("You can now use the bot!")
