# broadcast_handler.py (नया और सही कोड)

import asyncio
import time
import datetime
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait, UserIsBlocked, ChatWriteForbidden, PeerIdInvalid, RPCError

# 'config' और 'utils' से आवश्यक चीज़ें इम्पोर्ट करें
from config import (
    app, group_tracking_collection, user_tracking_collection,
    logger, OWNER_ID
)
from utils import (
    delete_after_delay_for_message,
    store_message 
)

# Broadcast Sending Logic (Helper Function) - यह फंक्शन जैसा था वैसा ही रहेगा
async def send_broadcast_message(client: Client, chat_id: int, message: Message):
    """
    Given a chat ID and a message object (the message to broadcast), 
    sends the message and handles different content types.
    
    Returns: (True/False, reason_string)
    """
    try:
        await message.copy(chat_id, parse_mode=ParseMode.MARKDOWN)
        return (True, "Success")
    
    except UserIsBlocked:
        return (False, "Blocked")
    except ChatWriteForbidden:
        return (False, "Blocked") 
    except PeerIdInvalid:
        return (False, "Deleted/Invalid")
    except RPCError as rpc_e:
        error_msg = str(rpc_e)
        if "INPUT_USER_DEACTIVATED" in error_msg or "USER_DEACTIVATED" in error_msg:
             return (False, "Deleted/Deactivated") 
        logger.error(f"RPC Error sending broadcast to chat {chat_id}: {rpc_e}")
        return (False, "Error")
    
    except FloodWait as fw:
        logger.warning(f"FloodWait of {fw.value}s encountered. Sleeping...")
        await asyncio.sleep(fw.value)
        return await send_broadcast_message(client, chat_id, message) 
    except Exception as e:
        logger.error(f"General Error sending broadcast to chat {chat_id}: {e}")
        return (False, "Error")


# -----------------------------------------------------
# 1. PRIVATE CHAT BROADCAST (/broadcast) - नया तरीका
# -----------------------------------------------------

@app.on_message(filters.command("broadcast") & filters.private & filters.user(OWNER_ID))
async def pm_broadcast(client: Client, message: Message):
    if not message.reply_to_message:
        await message.reply_text(
            "**🚀 Private Broadcast:** कृपया उस मैसेज को **रिप्लाई** करें जिसे आप सभी यूजर्स को भेजना चाहते हैं।"
        )
        return

    b_msg = message.reply_to_message
    
    # Target IDs nikalna
    private_chat_ids = [u["_id"] for u in user_tracking_collection.find({})]
    all_target_ids = list(set(private_chat_ids))
    if OWNER_ID in all_target_ids: 
        all_target_ids.remove(OWNER_ID)

    total_targets = len(all_target_ids)
    
    if total_targets == 0:
        await message.reply_text("🤷‍♀️ ब्रॉडकास्ट करने के लिए कोई यूजर नहीं मिला।")
        return

    # Initial status message
    sts = await message.reply_text(f"🚀 **Private Broadcast Shuru!**\n" 
                                   f"मैं **{total_targets}** प्राइवेट यूजर्स को मैसेज भेज रही हूँ...", 
                                   parse_mode=ParseMode.MARKDOWN)

    start_time_broadcast = time.time()
    done, success, blocked, deleted, failed = 0, 0, 0, 0, 0
    
    logger.info(f"Starting PM broadcast to {total_targets} users.")

    for chat_id in all_target_ids:
        pti, sh = await send_broadcast_message(client, chat_id, b_msg)
        
        if pti:
            success += 1
        else:
            if sh == "Blocked": blocked += 1
            elif sh == "Deleted/Invalid" or sh == "Deleted/Deactivated": deleted += 1
            else: failed += 1
        done += 1
        
        if done % 20 == 0 or done == total_targets:
            try:
                await sts.edit_text(f"🚀 **Broadcast Progress...**\n" 
                                    f"Total: **{total_targets}**\n" 
                                    f"Completed: **{done}**\n"
                                    f"Success: **{success}** ✨ | Blocked: **{blocked}** 💔 | Deleted: **{deleted}** 🗑️",
                                    parse_mode=ParseMode.MARKDOWN)
            except Exception:
                pass
                
    time_taken = datetime.timedelta(seconds=int(time.time()-start_time_broadcast))
    final_message = (f"🎉 **Private Broadcast पूरा हुआ!**\n" 
                     f"समय लगा: **{time_taken}**\n\n" 
                     f"Total Users: **{total_targets}**\n" 
                     f"सफलतापूर्वक भेजा: **{success}** ✨\n" 
                     f"Blocked: **{blocked}** 💔\n"
                     f"Deleted/Invalid: **{deleted}** 🗑️\n"
                     f"अन्य Fehler: **{failed}** 😥")
    
    await sts.edit_text(final_message, parse_mode=ParseMode.MARKDOWN)
    await store_message(client, message)


# -----------------------------------------------------
# 2. GROUP BROADCAST (/grp_broadcast) - नया तरीका
# -----------------------------------------------------

@app.on_message(filters.command("grp_broadcast") & filters.private & filters.user(OWNER_ID))
async def broadcast_group(client: Client, message: Message):
    if not message.reply_to_message:
        await message.reply_text(
            "**🚀 Group Broadcast:** कृपया उस मैसेज को **रिप्लाई** करें जिसे आप सभी ग्रुप्स में भेजना चाहते हैं।"
        )
        return
        
    b_msg = message.reply_to_message
    
    # Target IDs nikalna (Sirf Groups)
    group_chat_ids = [g["_id"] for g in group_tracking_collection.find({})]
    total_targets = len(group_chat_ids)
    
    if total_targets == 0:
        await message.reply_text("🤷‍♀️ ब्रॉडकास्ट करने के लिए कोई ग्रुप नहीं मिला।")
        return

    sts = await message.reply_text(f"🚀 **Group Broadcast Shuru!**\n" 
                                   f"मैं **{total_targets}** ग्रुप्स में मैसेज भेज रही हूँ...", 
                                   parse_mode=ParseMode.MARKDOWN)

    start_time_broadcast = time.time()
    done, success, failed = 0, 0, 0
    
    logger.info(f"Starting Group broadcast to {total_targets} groups.")

    for chat_id in group_chat_ids:
        pti, sh = await send_broadcast_message(client, chat_id, b_msg)
        
        if pti:
            success += 1
        else:
            failed += 1
        done += 1
        
        if done % 20 == 0 or done == total_targets:
            try:
                await sts.edit_text(f"🚀 **Group Broadcast Progress...**\n" 
                                    f"Total Groups: **{total_targets}**\n" 
                                    f"Completed: **{done}**\n"
                                    f"Success: **{success}** ✨ | Failed: **{failed}** 💔",
                                    parse_mode=ParseMode.MARKDOWN)
            except Exception:
                pass
                
    time_taken = datetime.timedelta(seconds=int(time.time()-start_time_broadcast))
    final_message = (f"🎉 **Group Broadcast पूरा हुआ!**\n" 
                     f"समय लगा: **{time_taken}**\n\n" 
                     f"Total Groups: **{total_targets}**\n" 
                     f"सफलतापूर्वक भेजा: **{success}** ✨\n" 
                     f"Failed: **{failed}** 💔")
    
    await sts.edit_text(final_message, parse_mode=ParseMode.MARKDOWN)
    await store_message(client, message)
