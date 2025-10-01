# broadcast_handler.py

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
    is_on_command_cooldown, update_command_cooldown, send_and_auto_delete_reply,
    store_message
)

# Broadcast Sending Logic (Helper Function)
async def send_broadcast_message(client: Client, chat_id: int, message: Message):
    """
    Given a chat ID and a message object (the message to broadcast), 
    sends the message and handles different content types.
    Returns: (True/False, reason_string)
    """
    try:
        # Check if the message has content that can be forwarded or copied
        if message.text or message.caption:
            await message.copy(chat_id, parse_mode=ParseMode.MARKDOWN)
        elif message.photo or message.video or message.sticker or message.document:
            await message.copy(chat_id)
        else:
            return (False, "No Content")
        
        return (True, "Success")
    
    except UserIsBlocked:
        return (False, "Blocked")
    except ChatWriteForbidden:
        return (False, "Blocked") # User can block, or bot was removed from group
    except PeerIdInvalid:
        return (False, "Deleted/Invalid")
    except FloodWait as fw:
        logger.warning(f"FloodWait of {fw.value}s encountered. (Broadcast by @asbhaibsr)")
        await asyncio.sleep(fw.value)
        return await send_broadcast_message(client, chat_id, message) # Retry after flood wait
    except RPCError as rpc_e:
        logger.error(f"RPC Error sending broadcast to chat {chat_id}: {rpc_e}")
        return (False, "Error")
    except Exception as e:
        logger.error(f"General Error sending broadcast to chat {chat_id}: {e}")
        return (False, "Error")


# -----------------------------------------------------
# 1. PRIVATE CHAT BROADCAST (/broadcast)
# -----------------------------------------------------

@app.on_message(filters.command("broadcast") & filters.private)
async def pm_broadcast(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    if message.from_user.id != OWNER_ID:
        await send_and_auto_delete_reply(message, text="Oops! Sorry sweetie, yeh command sirf mere boss ke liye hai. 🤷‍♀️ (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return
        
    try:
        # Owner se broadcast message pucho
        b_msg = await client.ask(chat_id=message.from_user.id, text="**🚀 Private Broadcast:** Ab mujhe woh message bhejo jise tum users ko bhejna chahte ho. Photo, video, ya text kuch bhi! 💬", parse_mode=ParseMode.MARKDOWN, timeout=300)
    except Exception as e:
        await send_and_auto_delete_reply(message, text="Mera dhyan bhatak gaya ya tumne time out kar diya. Broadcast cancel ho gaya. 😥", parse_mode=ParseMode.MARKDOWN)
        logger.warning(f"Broadcast cancelled by timeout or error: {e}")
        return
    
    # Target IDs nikalna (Groups aur Owner ID ko hata kar)
    private_chat_ids = [u["_id"] for u in user_tracking_collection.find({})]
    all_target_ids = list(set(private_chat_ids))
    if OWNER_ID in all_target_ids: 
        all_target_ids.remove(OWNER_ID)

    total_targets = len(all_target_ids)
    
    if total_targets == 0:
        await send_and_auto_delete_reply(message, text="Mujhe koi user mila hi nahi jise message bheja ja sake (Owner ko chhodkar). 🤷‍♀️", parse_mode=ParseMode.MARKDOWN)
        return

    sts = await message.reply_text(f"🚀 **Private Broadcast Shuru!** 🚀\n" 
                                   f"Cool, main **{total_targets}** private chats par message bhej rahi hoon.\n" 
                                   f"Sent: **0** / Blocked: **0** / Deleted: **0** (Total: {total_targets})", 
                                   parse_mode=ParseMode.MARKDOWN)

    start_time = time.time()
    done = 0
    blocked = 0
    deleted = 0
    failed = 0
    success = 0
    
    logger.info(f"Starting PM broadcast to {total_targets} users. (Broadcast by @asbhaibsr)")

    for i, chat_id in enumerate(all_target_ids):
        pti, sh = await send_broadcast_message(client, chat_id, b_msg)
        
        if pti:
            success += 1
        else:
            if sh == "Blocked":
                blocked += 1
            elif sh == "Deleted/Invalid":
                deleted += 1
            elif sh == "Error":
                failed += 1

        done += 1
        if done % 20 == 0 or done == total_targets:
            try:
                await sts.edit_text(f"🚀 **Private Broadcast Progress...** 🚀\n\n" 
                                    f"Total Users: **{total_targets}**\n" 
                                    f"Completed: **{done}** / **{total_targets}**\n"
                                    f"Success: **{success}** ✨\n"
                                    f"Blocked: **{blocked}** 💔\n"
                                    f"Deleted/Invalid: **{deleted}** 🗑️",
                                    parse_mode=ParseMode.MARKDOWN)
            except Exception as edit_e:
                logger.warning(f"Failed to edit broadcast status message: {edit_e}")

    time_taken = datetime.timedelta(seconds=int(time.time()-start_time))
    final_message = (f"🎉 **Private Broadcast Complete!** 🎉\n" 
                     f"Completed in **{time_taken}** seconds.\n\n" 
                     f"Total Users Targeted: **{total_targets}**\n" 
                     f"Successfully Sent: **{success}** messages ✨\n" 
                     f"Blocked/Forbidden: **{blocked}** 💔\n"
                     f"Deleted/Invalid Peer: **{deleted}** 🗑️\n"
                     f"Other Failures: **{failed}** 😥\n\n"
                     f"Koi nahi, next time! 😉 (System by @asbhaibsr)")
    
    try:
        await sts.edit_text(final_message, parse_mode=ParseMode.MARKDOWN)
    except Exception as final_edit_e:
        logger.error(f"Failed to send final broadcast summary: {final_edit_e}. Sending as new message instead.")
        await message.reply_text(final_message, parse_mode=ParseMode.MARKDOWN)

    await store_message(message)


# -----------------------------------------------------
# 2. GROUP BROADCAST (/grp_broadcast)
# -----------------------------------------------------

@app.on_message(filters.command("grp_broadcast") & filters.private)
async def broadcast_group(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    if message.from_user.id != OWNER_ID:
        await send_and_auto_delete_reply(message, text="Oops! Sorry sweetie, yeh command sirf mere boss ke liye hai. 🤷‍♀️ (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return
        
    try:
        # Owner se broadcast message pucho
        b_msg = await client.ask(chat_id=message.from_user.id, text="**🚀 Group Broadcast:** Ab mujhe woh message bhejo jise tum Groups ko bhejna chahte ho. Photo, video, ya text kuch bhi! 💬", parse_mode=ParseMode.MARKDOWN, timeout=300)
    except Exception as e:
        await send_and_auto_delete_reply(message, text="Mera dhyan bhatak gaya ya tumne time out kar diya. Broadcast cancel ho gaya. 😥", parse_mode=ParseMode.MARKDOWN)
        logger.warning(f"Broadcast cancelled by timeout or error: {e}")
        return
    
    # Target IDs nikalna (Sirf Groups)
    group_chat_ids = [g["_id"] for g in group_tracking_collection.find({})]
    all_target_ids = list(set(group_chat_ids))

    total_targets = len(all_target_ids)
    
    if total_targets == 0:
        await send_and_auto_delete_reply(message, text="Mujhe koi Group mila hi nahi jise message bheja ja sake. Pehle mujhe Groups mein add karo! 🥺", parse_mode=ParseMode.MARKDOWN)
        return

    sts = await message.reply_text(f"🚀 **Group Broadcast Shuru!** 🚀\n" 
                                   f"Cool, main **{total_targets}** Groups par message bhej rahi hoon.\n" 
                                   f"Sent: **0** / Failed: **0** (Total: {total_targets})", 
                                   parse_mode=ParseMode.MARKDOWN)

    start_time = time.time()
    done = 0
    failed = 0
    success = 0
    
    logger.info(f"Starting Group broadcast to {total_targets} groups. (Broadcast by @asbhaibsr)")

    for i, chat_id in enumerate(all_target_ids):
        pti, sh = await send_broadcast_message(client, chat_id, b_msg)
        
        if pti:
            success += 1
        else:
            failed += 1

        done += 1
        if done % 20 == 0 or done == total_targets:
            try:
                await sts.edit_text(f"🚀 **Group Broadcast Progress...** 🚀\n\n" 
                                    f"Total Groups: **{total_targets}**\n" 
                                    f"Completed: **{done}** / **{total_targets}**\n"
                                    f"Success: **{success}** ✨\n"
                                    f"Failed/Forbidden: **{failed}** 💔",
                                    parse_mode=ParseMode.MARKDOWN)
            except Exception as edit_e:
                logger.warning(f"Failed to edit broadcast status message: {edit_e}")
                
    time_taken = datetime.timedelta(seconds=int(time.time()-start_time))
    final_message = (f"🎉 **Group Broadcast Complete!** 🎉\n" 
                     f"Completed in **{time_taken}** seconds.\n\n" 
                     f"Total Groups Targeted: **{total_targets}**\n" 
                     f"Successfully Sent: **{success}** messages ✨\n" 
                     f"Failed/Forbidden: **{failed}** messages 💔\n\n"
                     f"Koi nahi, next time! 😉 (System by @asbhaibsr)")
    
    try:
        await sts.edit_text(final_message, parse_mode=ParseMode.MARKDOWN)
    except Exception as final_edit_e:
        logger.error(f"Failed to send final broadcast summary: {final_edit_e}. Sending as new message instead.")
        await message.reply_text(final_message, parse_mode=ParseMode.MARKDOWN)

    await store_message(message)
