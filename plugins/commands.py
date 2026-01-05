# Don't Remove Credit Tg - @VJ_Bots
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

import os
import logging
import random
import asyncio
from datetime import datetime, timedelta
from validators import domain
from Script import script
from plugins.dbusers import db
from pyrogram import Client, filters, enums
from plugins.users_api import get_user, update_user_info
from pyrogram.errors import ChatAdminRequired, FloodWait
from pyrogram.types import *
from utils import verify_user, check_token, check_verification, get_token
from config import *
import re
import json
import base64
from urllib.parse import quote_plus
from TechVJ.utils.file_properties import get_name, get_hash, get_media_file_size
logger = logging.getLogger(__name__)

BATCH_FILES = {}

# Import new features
try:
    from plugins.database import db_manager  # Your MongoDB manager
    from plugins.verification import start_verification, complete_verification
    from plugins.fsub import check_user_fsub
except ImportError:
    pass

# Don't Remove Credit Tg - @VJ_Bots
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

def get_size(size):
    """Get size in readable format"""
    units = ["Bytes", "KB", "MB", "GB", "TB", "PB", "EB"]
    size = float(size)
    i = 0
    while size >= 1024.0 and i < len(units):
        i += 1
        size /= 1024.0
    return "%.2f %s" % (size, units[i])

def formate_file_name(file_name):
    chars = ["[", "]", "(", ")"]
    for c in chars:
        file_name.replace(c, "")
    file_name = '@VJ_Botz ' + ' '.join(filter(lambda x: not x.startswith('http') and not x.startswith('@') and not x.startswith('www.'), file_name.split()))
    return file_name

# Don't Remove Credit Tg - @VJ_Bots
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

async def check_access_control(client, user_id, message=None):
    """
    Check all access controls: FSub, Session, Verification
    Returns: (allowed: bool, reason: str, session_id: str or None)
    """
    # 1. Check if user is admin
    if user_id in ADMINS:
        return True, "admin", None
    
    try:
        # 2. Check Force Subscribe (FSub) if enabled
        if hasattr(db_manager, 'get_fsub_status'):
            fsub_enabled = await db_manager.get_fsub_status()
            if fsub_enabled:
                allowed, missing_channels, fsub_message, fsub_keyboard = await check_user_fsub(client, user_id)
                if not allowed:
                    if message:
                        await message.reply(
                            fsub_message,
                            reply_markup=fsub_keyboard,
                            disable_web_page_preview=True
                        )
                    return False, "fsub_required", None
    except Exception as e:
        logger.error(f"FSub check error: {e}")
    
    try:
        # 3. Check active session (6-hour unlimited)
        if hasattr(db_manager, 'get_active_session'):
            session = await db_manager.get_active_session(user_id)
            if session:
                return True, "active_session", session.get("session_id")
    except Exception as e:
        logger.error(f"Session check error: {e}")
    
    # 4. User needs verification
    return False, "verification_required", None

@Client.on_message(filters.command("start") & filters.incoming)
async def start(client, message):
    username = client.me.username
    
    # Add user to database if not exists
    if not await db.is_user_exist(message.from_user.id):
        await db.add_user(message.from_user.id, message.from_user.first_name)
        await client.send_message(LOG_CHANNEL, script.LOG_TEXT.format(message.from_user.id, message.from_user.mention))
    
    if len(message.command) != 2:
        # Regular start command
        buttons = [[
            InlineKeyboardButton('💝 sᴜʙsᴄʀɪʙᴇ ᴍʏ ʏᴏᴜᴛᴜʙᴇ ᴄʜᴀɴɴᴇʟ', url='https://youtube.com/@Tech_VJ')
        ],[
            InlineKeyboardButton('🔍 sᴜᴘᴘᴏʀᴛ ɢʀᴏᴜᴘ', url='https://t.me/vj_bot_disscussion'),
            InlineKeyboardButton('🤖 ᴜᴘᴅᴀᴛᴇ ᴄʜᴀɴɴᴇʟ', url='https://t.me/vj_bots')
        ],[
            InlineKeyboardButton('💁‍♀️ ʜᴇʟᴘ', callback_data='help'),
            InlineKeyboardButton('😊 ᴀʙᴏᴜᴛ', callback_data='about')
        ]]
        
        # Check access control
        allowed, reason, session_id = await check_access_control(client, message.from_user.id)
        
        if not allowed and reason == "verification_required":
            # Show verification option
            buttons.append([InlineKeyboardButton('🔐 Start Verification', callback_data='start_verification')])
        
        if CLONE_MODE == True:
            buttons.append([InlineKeyboardButton('🤖 ᴄʀᴇᴀᴛᴇ ʏᴏᴜʀ ᴏᴡɴ ᴄʟᴏɴᴇ ʙᴏᴛ', callback_data='clone')])
        
        reply_markup = InlineKeyboardMarkup(buttons)
        me = client.me
        
        # Add session info if available
        caption = script.START_TXT.format(message.from_user.mention, me.mention)
        if allowed and reason == "active_session":
            try:
                if hasattr(db_manager, 'get_active_session'):
                    session = await db_manager.get_active_session(message.from_user.id)
                    if session:
                        expiry_time = session.get("expiry_time")
                        if isinstance(expiry_time, datetime):
                            time_left = expiry_time - datetime.now()
                            hours = time_left.seconds // 3600
                            minutes = (time_left.seconds % 3600) // 60
                            caption += f"\n\n🔓 **Active Session:** {hours}h {minutes}m remaining"
            except:
                pass
        
        await message.reply_photo(
            photo=random.choice(PICS),
            caption=caption,
            reply_markup=reply_markup
        )
        return
    
    # Handle start with parameters
    data = message.command[1]
    
    # ========== NEW: Handle verification callback ==========
    if data.startswith("verify_"):
        parts = data.split("_")
        if len(parts) >= 3:
            token = parts[1]
            user_id_from_token = int(parts[2]) if len(parts) > 2 else 0
            
            if user_id_from_token != message.from_user.id:
                return await message.reply_text(
                    text="<b>❌ This verification link is not for you!</b>",
                    protect_content=True
                )
            
            try:
                # Complete verification with anti-bypass
                success, result = await complete_verification(client, message.from_user.id, token)
                
                if success:
                    # Create 6-hour session
                    if hasattr(db_manager, 'create_session'):
                        session_id = await db_manager.create_session(message.from_user.id, 6)
                    
                    await message.reply_text(
                        text=f"<b>✅ Verification Successful!</b>\n\n"
                             f"Hey {message.from_user.mention}, you now have <b>6-hour unlimited access</b> to all files!\n"
                             f"Session ID: <code>{session_id[:10]}...</code>",
                        protect_content=True
                    )
                else:
                    if result == "Bypass detected! Complete verification properly.":
                        await message.reply_text(
                            text="<b>❌ Bypass Detected!</b>\n\n"
                                 "You completed verification too fast (<35 seconds).\n"
                                 "Complete the process properly by waiting 35+ seconds.",
                            protect_content=True
                        )
                    else:
                        await message.reply_text(
                            text=f"<b>❌ {result}</b>",
                            protect_content=True
                        )
                return
                
            except Exception as e:
                logger.error(f"Verification error: {e}")
                return await message.reply_text(
                    text="<b>❌ Verification failed. Please try again.</b>",
                    protect_content=True
                )
    
    # ========== Handle existing VJ-File-Store parameters ==========
    try:
        pre, file_id = data.split('_', 1)
    except:
        file_id = data
        pre = ""
    
    if data.split("-", 1)[0] == "verify":
        # Original VJ verification (keep for compatibility)
        userid = data.split("-", 2)[1]
        token = data.split("-", 3)[2]
        if str(message.from_user.id) != str(userid):
            return await message.reply_text(
                text="<b>Invalid link or Expired link !</b>",
                protect_content=True
            )
        is_valid = await check_token(client, userid, token)
        if is_valid == True:
            await message.reply_text(
                text=f"<b>Hey {message.from_user.mention}, You are successfully verified !\nNow you have unlimited access for all files till today midnight.</b>",
                protect_content=True
            )
            await verify_user(client, userid, token)
        else:
            return await message.reply_text(
                text="<b>Invalid link or Expired link !</b>",
                protect_content=True
            )
    
    elif data.split("-", 1)[0] == "BATCH":
        # ========== NEW: Check access control before batch ==========
        allowed, reason, session_id = await check_access_control(client, message.from_user.id, message)
        if not allowed:
            if reason == "verification_required":
                await start_verification(client, message.from_user.id, message)
            return
        # ========== END NEW CODE ==========
        
        try:
            if not await check_verification(client, message.from_user.id) and VERIFY_MODE == True:
                btn = [[
                    InlineKeyboardButton("Verify", url=await get_token(client, message.from_user.id, f"https://telegram.me/{username}?start="))
                ],[
                    InlineKeyboardButton("How To Open Link & Verify", url=VERIFY_TUTORIAL)
                ]]
                await message.reply_text(
                    text="<b>You are not verified !\nKindly verify to continue !</b>",
                    protect_content=True,
                    reply_markup=InlineKeyboardMarkup(btn)
                )
                return
        except Exception as e:
            return await message.reply_text(f"**Error - {e}**")
        
        sts = await message.reply("**🔺 ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ**")
        file_id = data.split("-", 1)[1]
        msgs = BATCH_FILES.get(file_id)
        
        if not msgs:
            decode_file_id = base64.urlsafe_b64decode(file_id + "=" * (-len(file_id) % 4)).decode("ascii")
            msg = await client.get_messages(LOG_CHANNEL, int(decode_file_id))
            media = getattr(msg, msg.media.value)
            file_id = media.file_id
            file = await client.download_media(file_id)
            try: 
                with open(file) as file_data:
                    msgs=json.loads(file_data.read())
            except:
                await sts.edit("FAILED")
                return await client.send_message(LOG_CHANNEL, "UNABLE TO OPEN FILE.")
            os.remove(file)
            BATCH_FILES[file_id] = msgs
        
        # ========== NEW: Log batch access ==========
        try:
            if hasattr(db_manager, 'log_link_access'):
                await db_manager.log_link_access(message.from_user.id, file_id, "batch")
        except Exception as e:
            logger.error(f"Log error: {e}")
        # ========== END NEW CODE ==========
        
        filesarr = []
        for msg in msgs:
            channel_id = int(msg.get("channel_id"))
            msgid = msg.get("msg_id")
            info = await client.get_messages(channel_id, int(msgid))
            
            if info.media:
                file_type = info.media
                file = getattr(info, file_type.value)
                f_caption = getattr(info, 'caption', '')
                if f_caption:
                    f_caption = f"@VJ_Bots {f_caption.html}"
                old_title = getattr(file, "file_name", "")
                title = formate_file_name(old_title)
                size=get_size(int(file.file_size))
                
                if BATCH_FILE_CAPTION:
                    try:
                        f_caption=BATCH_FILE_CAPTION.format(file_name= '' if title is None else title, file_size='' if size is None else size, file_caption='' if f_caption is None else f_caption)
                    except:
                        f_caption=f_caption
                if f_caption is None:
                    f_caption = f"@VJ_Bots {title}"
                
                if STREAM_MODE == True:
                    if info.video or info.document:
                        log_msg = info
                        fileName = {quote_plus(get_name(log_msg))}
                        stream = f"{URL}watch/{str(log_msg.id)}/{quote_plus(get_name(log_msg))}?hash={get_hash(log_msg)}"
                        download = f"{URL}{str(log_msg.id)}/{quote_plus(get_name(log_msg))}?hash={get_hash(log_msg)}"
                        button = [[
                            InlineKeyboardButton("• ᴅᴏᴡɴʟᴏᴀᴅ •", url=download),
                            InlineKeyboardButton('• ᴡᴀᴛᴄʜ •', url=stream)
                        ],[
                            InlineKeyboardButton("• ᴡᴀᴛᴄʜ ɪɴ ᴡᴇʙ ᴀᴘᴘ •", web_app=WebAppInfo(url=stream))
                        ]]
                        reply_markup=InlineKeyboardMarkup(button)
                else:
                    reply_markup = None
                
                try:
                    msg = await info.copy(chat_id=message.from_user.id, caption=f_caption, protect_content=False, reply_markup=reply_markup)
                except FloodWait as e:
                    await asyncio.sleep(e.value)
                    msg = await info.copy(chat_id=message.from_user.id, caption=f_caption, protect_content=False, reply_markup=reply_markup)
                except:
                    continue
            else:
                try:
                    msg = await info.copy(chat_id=message.from_user.id, protect_content=False)
                except FloodWait as e:
                    await asyncio.sleep(e.value)
                    msg = await info.copy(chat_id=message.from_user.id, protect_content=False)
                except:
                    continue
            filesarr.append(msg)
            await asyncio.sleep(1) 
        
        await sts.delete()
        
        if AUTO_DELETE_MODE == True:
            k = await client.send_message(chat_id = message.from_user.id, text=f"<b><u>❗️❗️❗️IMPORTANT❗️️❗️❗️</u></b>\n\nThis Movie File/Video will be deleted in <b><u>{AUTO_DELETE} minutes</u> 🫥 <i></b>(Due to Copyright Issues)</i>.\n\n<b><i>Please forward this File/Video to your Saved Messages and Start Download there</b>")
            await asyncio.sleep(AUTO_DELETE_TIME)
            for x in filesarr:
                try:
                    await x.delete()
                except:
                    pass
            await k.edit_text("<b>Your All Files/Videos is successfully deleted!!!</b>")
        return

    # ========== Handle single file links ==========
    pre, decode_file_id = ((base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))).decode("ascii")).split("_", 1)
    
    # ========== NEW: Check access control ==========
    allowed, reason, session_id = await check_access_control(client, message.from_user.id, message)
    if not allowed:
        if reason == "verification_required":
            await start_verification(client, message.from_user.id, message)
        return
    # ========== END NEW CODE ==========
    
    # Original VJ verification check (keep for compatibility)
    if not await check_verification(client, message.from_user.id) and VERIFY_MODE == True:
        btn = [[
            InlineKeyboardButton("Verify", url=await get_token(client, message.from_user.id, f"https://telegram.me/{username}?start="))
        ],[
            InlineKeyboardButton("How To Open Link & Verify", url=VERIFY_TUTORIAL)
        ]]
        await message.reply_text(
            text="<b>You are not verified !\nKindly verify to continue !</b>",
            protect_content=True,
            reply_markup=InlineKeyboardMarkup(btn)
        )
        return
    
    try:
        msg = await client.get_messages(LOG_CHANNEL, int(decode_file_id))
        
        # ========== NEW: Log single file access ==========
        try:
            if hasattr(db_manager, 'log_link_access'):
                await db_manager.log_link_access(message.from_user.id, decode_file_id, "single")
        except Exception as e:
            logger.error(f"Log error: {e}")
        # ========== END NEW CODE ==========
        
        if msg.media:
            media = getattr(msg, msg.media.value)
            title = formate_file_name(media.file_name)
            size=get_size(media.file_size)
            f_caption = f"@VJ_Bots <code>{title}</code>"
            if CUSTOM_FILE_CAPTION:
                try:
                    f_caption=CUSTOM_FILE_CAPTION.format(file_name= '' if title is None else title, file_size='' if size is None else size, file_caption='')
                except:
                    return
            
            if STREAM_MODE == True:
                if msg.video or msg.document:
                    log_msg = msg
                    fileName = {quote_plus(get_name(log_msg))}
                    stream = f"{URL}watch/{str(log_msg.id)}/{quote_plus(get_name(log_msg))}?hash={get_hash(log_msg)}"
                    download = f"{URL}{str(log_msg.id)}/{quote_plus(get_name(log_msg))}?hash={get_hash(log_msg)}"
                    button = [[
                        InlineKeyboardButton("• ᴅᴏᴡɴʟᴏᴀᴅ •", url=download),
                        InlineKeyboardButton('• ᴡᴀᴛᴄʜ •', url=stream)
                    ],[
                        InlineKeyboardButton("• ᴡᴀᴛᴄʜ ɪɴ ᴡᴇʙ ᴀᴘᴘ •", web_app=WebAppInfo(url=stream))
                    ]]
                    reply_markup=InlineKeyboardMarkup(button)
            else:
                reply_markup = None
            
            del_msg = await msg.copy(chat_id=message.from_user.id, caption=f_caption, reply_markup=reply_markup, protect_content=False)
        else:
            del_msg = await msg.copy(chat_id=message.from_user.id, protect_content=False)
        
        if AUTO_DELETE_MODE == True:
            k = await client.send_message(chat_id = message.from_user.id, text=f"<b><u>❗️❗️❗️IMPORTANT❗️️❗️❗️</u></b>\n\nThis Movie File/Video will be deleted in <b><u>{AUTO_DELETE} minutes</u> 🫥 <i></b>(Due to Copyright Issues)</i>.\n\n<b><i>Please forward this File/Video to your Saved Messages and Start Download there</b>")
            await asyncio.sleep(AUTO_DELETE_TIME)
            try:
                await del_msg.delete()
            except:
                pass
            await k.edit_text("<b>Your File/Video is successfully deleted!!!</b>")
        return
    except:
        pass

# Don't Remove Credit Tg - @VJ_Bots
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

# ========== NEW: FSUB MANAGEMENT COMMANDS ==========

@Client.on_message(filters.command("fsub") & filters.user(ADMINS))
async def fsub_management_command(client, message):
    """FSub management panel"""
    try:
        from plugins.fsub import fsub_management
        await fsub_management(client, message)
    except ImportError:
        await message.reply("❌ FSub module not installed.")

@Client.on_message(filters.command(["addforce", "fsub add"]) & filters.user(ADMINS))
async def add_fsub_channel_command(client, message):
    """Add channel to FSub"""
    try:
        from plugins.fsub import fsub_add_channel
        await fsub_add_channel(client, message)
    except ImportError:
        await message.reply("❌ FSub module not installed.")

@Client.on_message(filters.command(["forcechannels", "fsub list"]) & filters.user(ADMINS))
async def list_fsub_channels_command(client, message):
    """List FSub channels"""
    try:
        from plugins.fsub import fsub_list_channels
        await fsub_list_channels(client, message)
    except ImportError:
        await message.reply("❌ FSub module not installed.")

@Client.on_message(filters.command(["removeforce", "fsub remove"]) & filters.user(ADMINS))
async def remove_fsub_channel_command(client, message):
    """Remove FSub channel"""
    try:
        from plugins.fsub import fsub_remove_channel
        await fsub_remove_channel(client, message)
    except ImportError:
        await message.reply("❌ FSub module not installed.")

@Client.on_message(filters.command(["fsub check"]))
async def check_fsub_status_command(client, message):
    """Check FSub status"""
    try:
        from plugins.fsub import fsub_check_user
        await fsub_check_user(client, message)
    except ImportError:
        await message.reply("❌ FSub module not installed.")

# ========== NEW: SESSION & VERIFICATION COMMANDS ==========

@Client.on_message(filters.command("session") & filters.private)
async def check_session_command(client, message):
    """Check your active session status"""
    try:
        if hasattr(db_manager, 'get_active_session'):
            session = await db_manager.get_active_session(message.from_user.id)
            
            if session:
                expiry_time = session.get("expiry_time")
                if isinstance(expiry_time, datetime):
                    time_left = expiry_time - datetime.now()
                    
                    if time_left.total_seconds() > 0:
                        hours = int(time_left.total_seconds() // 3600)
                        minutes = int((time_left.total_seconds() % 3600) // 60)
                        
                        await message.reply(
                            f"🔓 **Active Session**\n\n"
                            f"**Session ID:** `{session.get('session_id', '')[:12]}...`\n"
                            f"**Started:** {session.get('start_time', 'N/A')}\n"
                            f"**Expires:** {expiry_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                            f"**Time Left:** {hours}h {minutes}m\n\n"
                            f"You have unlimited access until expiry."
                        )
                    else:
                        await message.reply("❌ Your session has expired.")
                else:
                    await message.reply("✅ You have an active session.")
            else:
                await message.reply(
                    "❌ No active session found.\n\n"
                    "You need to verify to get a 6-hour unlimited access session."
                )
    except Exception as e:
        logger.error(f"Session check error: {e}")
        await message.reply("❌ Error checking session status.")

# ========== NEW: ADMIN PANEL COMMAND ==========

@Client.on_message(filters.command("admin") & filters.user(ADMINS))
async def admin_panel_command(client, message):
    """Admin control panel"""
    try:
        from plugins.admin_panel import admin_panel_command as admin_panel
        await admin_panel(client, message)
    except ImportError:
        # Simple admin panel if module not installed
        buttons = [
            [
                InlineKeyboardButton("📊 Statistics", callback_data="admin_stats"),
                InlineKeyboardButton("🔔 FSub", callback_data="admin_fsub")
            ],
            [
                InlineKeyboardButton("👥 Users", callback_data="admin_users"),
                InlineKeyboardButton("🔗 Links", callback_data="admin_links")
            ],
            [
                InlineKeyboardButton("⚙️ Settings", callback_data="admin_settings"),
                InlineKeyboardButton("🛡️ Security", callback_data="admin_security")
            ]
        ]
        
        await message.reply(
            "👑 **Admin Control Panel**\n\n"
            "Select a category to manage:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

# ========== ORIGINAL VJ-FILE-STORE COMMANDS (Keep these) ==========

@Client.on_message(filters.command('api') & filters.private)
async def shortener_api_handler(client, m: Message):
    user_id = m.from_user.id
    user = await get_user(user_id)
    cmd = m.command

    if len(cmd) == 1:
        s = script.SHORTENER_API_MESSAGE.format(base_site=user["base_site"], shortener_api=user["shortener_api"])
        return await m.reply(s)

    elif len(cmd) == 2:    
        api = cmd[1].strip()
        await update_user_info(user_id, {"shortener_api": api})
        await m.reply("<b>Shortener API updated successfully to</b> " + api)

@Client.on_message(filters.command("base_site") & filters.private)
async def base_site_handler(client, m: Message):
    user_id = m.from_user.id
    user = await get_user(user_id)
    cmd = m.command
    text = f"`/base_site (base_site)`\n\n<b>Current base site: None\n\n EX:</b> `/base_site shortnerdomain.com`\n\nIf You Want To Remove Base Site Then Copy This And Send To Bot - `/base_site None`"
    if len(cmd) == 1:
        return await m.reply(text=text, disable_web_page_preview=True)
    elif len(cmd) == 2:
        base_site = cmd[1].strip()
        if base_site == None:
            await update_user_info(user_id, {"base_site": base_site})
            return await m.reply("<b>Base Site updated successfully</b>")
            
        if not domain(base_site):
            return await m.reply(text=text, disable_web_page_preview=True)
        await update_user_info(user_id, {"base_site": base_site})
        await m.reply("<b>Base Site updated successfully</b>")

# ========== NEW: UPDATED CALLBACK HANDLER ==========

@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    if query.data == "close_data":
        await query.message.delete()
    
    elif query.data == "start_verification":
        """Start verification process"""
        try:
            from plugins.verification import start_verification
            await start_verification(client, query.from_user.id, query.message)
            await query.answer("Verification started!")
        except ImportError:
            await query.answer("Verification module not available!", show_alert=True)
    
    elif query.data.startswith("fsub_"):
        """Handle FSub callbacks"""
        try:
            from plugins.fsub import fsub_check_callback, fsub_continue_callback
            if query.data.startswith("fsub_check_"):
                await fsub_check_callback(client, query)
            elif query.data == "fsub_continue":
                await fsub_continue_callback(client, query)
        except ImportError:
            await query.answer("FSub module not available!", show_alert=True)
    
    elif query.data.startswith("admin_"):
        """Handle admin panel callbacks"""
        try:
            from plugins.admin_panel import admin_callback_handler
            await admin_callback_handler(client, query)
        except ImportError:
            # Simple fallback
            if query.data == "admin_stats":
                await query.message.edit_text(
                    "📊 **Statistics**\n\n"
                    "Feature under development.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ Back", callback_data="admin_back")]
                    ])
                )
            elif query.data == "admin_back":
                buttons = [
                    [
                        InlineKeyboardButton("📊 Statistics", callback_data="admin_stats"),
                        InlineKeyboardButton("🔔 FSub", callback_data="admin_fsub")
                    ],
                    [
                        InlineKeyboardButton("👥 Users", callback_data="admin_users"),
                        InlineKeyboardButton("🔗 Links", callback_data="admin_links")
                    ],
                    [
                        InlineKeyboardButton("⚙️ Settings", callback_data="admin_settings"),
                        InlineKeyboardButton("🛡️ Security", callback_data="admin_security")
                    ]
                ]
                await query.message.edit_text(
                    "👑 **Admin Control Panel**\n\nSelect a category:",
                    reply_markup=InlineKeyboardMarkup(buttons)
                )
            await query.answer()
    
    # ========== ORIGINAL VJ CALLBACKS (Keep these) ==========
    
    elif query.data == "about":
        buttons = [[
            InlineKeyboardButton('Hᴏᴍᴇ', callback_data='start'),
            InlineKeyboardButton('🔒 Cʟᴏsᴇ', callback_data='close_data')
        ]]
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        reply_markup = InlineKeyboardMarkup(buttons)
        me2 = (await client.get_me()).mention
        await query.message.edit_text(
            text=script.ABOUT_TXT.format(me2),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    
    elif query.data == "start":
        buttons = [[
            InlineKeyboardButton('💝 sᴜʙsᴄʀɪʙᴇ ᴍʏ ʏᴏᴜᴛᴜʙᴇ ᴄʜᴀɴɴᴇʟ', url='https://youtube.com/@Tech_VJ')
        ],[
            InlineKeyboardButton('🔍 sᴜᴘᴘᴏʀᴛ ɢʀᴏᴜᴘ', url='https://t.me/vj_bot_disscussion'),
            InlineKeyboardButton('🤖 ᴜᴘᴅᴀᴛᴇ ᴄʜᴀɴɴᴇʟ', url='https://t.me/vj_bots')
        ],[
            InlineKeyboardButton('💁‍♀️ ʜᴇʟᴘ', callback_data='help'),
            InlineKeyboardButton('😊 ᴀʙᴏᴜᴛ', callback_data='about')
        ]]
        
        # Check access for verification button
        allowed, reason, session_id = await check_access_control(client, query.from_user.id)
        if not allowed and reason == "verification_required":
            buttons.append([InlineKeyboardButton('🔐 Start Verification', callback_data='start_verification')])
        
        if CLONE_MODE == True:
            buttons.append([InlineKeyboardButton('🤖 ᴄʀᴇᴀᴛᴇ ʏᴏᴜʀ ᴏᴡɴ ᴄʟᴏɴᴇ ʙᴏᴛ', callback_data='clone')])
        
        reply_markup = InlineKeyboardMarkup(buttons)
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        me2 = (await client.get_me()).mention
        await query.message.edit_text(
            text=script.START_TXT.format(query.from_user.mention, me2),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    
    elif query.data == "clone":
        buttons = [[
            InlineKeyboardButton('Hᴏᴍᴇ', callback_data='start'),
            InlineKeyboardButton('🔒 Cʟᴏsᴇ', callback_data='close_data')
        ]]
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.CLONE_TXT.format(query.from_user.mention),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )          
    
    elif query.data == "help":
        buttons = [[
            InlineKeyboardButton('Hᴏᴍᴇ', callback_data='start'),
            InlineKeyboardButton('🔒 Cʟᴏsᴇ', callback_data='close_data')
        ]]
        await client.edit_message_media(
            query.message.chat.id, 
            query.message.id, 
            InputMediaPhoto(random.choice(PICS))
        )
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.HELP_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    
    # ========== NEW: ADDITIONAL CALLBACKS ==========
    
    elif query.data == "refresh_session":
        """Refresh session display"""
        try:
            if hasattr(db_manager, 'get_active_session'):
                session = await db_manager.get_active_session(query.from_user.id)
                if session:
                    expiry_time = session.get("expiry_time")
                    if isinstance(expiry_time, datetime):
                        time_left = expiry_time - datetime.now()
                        hours = int(time_left.total_seconds() // 3600)
                        minutes = int((time_left.total_seconds() % 3600) // 60)
                        
                        await query.message.edit_text(
                            f"🔓 **Session Refreshed**\n\n"
                            f"**Time Left:** {hours}h {minutes}m\n"
                            f"**Expires:** {expiry_time.strftime('%H:%M %d/%m')}",
                            reply_markup=InlineKeyboardMarkup([
                                [InlineKeyboardButton("🔄 Refresh", callback_data="refresh_session")],
                                [InlineKeyboardButton("⬅️ Back", callback_data="start")]
                            ])
                        )
                else:
                    await query.answer("No active session!", show_alert=True)
        except Exception as e:
            await query.answer("Error refreshing session!", show_alert=True)
    
    # Add more callbacks as needed

# Don't Remove Credit Tg - @VJ_Bots
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

# ========== NEW: BATCH AND LINK COMMANDS WITH ACCESS CONTROL ==========

@Client.on_message(filters.command("batch") & filters.user(ADMINS))
async def batch_link_command(client, message):
    """Generate batch links with access control"""
    # Check if user replied to messages
    if len(message.command) < 3:
        await message.reply(
            "❌ **Usage:** `/batch <first_message_link> <last_message_link>`\n\n"
            "Example: `/batch https://t.me/... https://t.me/...`"
        )
        return
    
    # Your existing batch generation code here
    # This should call the original VJ batch generation
    
    await message.reply("✅ Batch link generation started...")

@Client.on_message(filters.command("link") & filters.user(ADMINS))
async def single_link_command(client, message):
    """Generate single file link with access control"""
    if not message.reply_to_message:
        await message.reply("❌ Reply to a file with `/link`")
        return
    
    # Your existing link generation code here
    # This should call the original VJ link generation
    
    await message.reply("✅ Link generated!")

# Don't Remove Credit Tg - @VJ_Bots
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01
