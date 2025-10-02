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
    send_and_auto_delete_reply,
    store_message 
)

# --- Global Dictionaries for Manual Listener (For "Ask" replacement) ---
# Ismein hum broadcast shuru hone ka status store karenge
BROADCAST_STATUS = {}
# Ismein hum har user ke liye uske agle message ko store karenge
NEXT_MESSAGE_WAITERS = {}


# -----------------------------------------------------
# 0. MANUAL MESSAGE LISTENER (Replacing client.ask)
# -----------------------------------------------------
@app.on_message(filters.private & filters.user(OWNER_ID) & ~filters.command(["broadcast", "grp_broadcast"]))
async def custom_ask_listener(client: Client, message: Message):
    user_id = message.from_user.id
    
    # Check if the user is currently in a broadcast waiting state
    if user_id in NEXT_MESSAGE_WAITERS:
        waiter = NEXT_MESSAGE_WAITERS.pop(user_id, None)
        if waiter:
            # Set the result of the waiter to the received message
            waiter.set_result(message)
            # The next message is consumed by the broadcast handler, so we stop further processing here.
            return
    
    # Agar user koi broadcast shuru nahi kar raha hai, toh yeh message aage process hoga (e.g., normal chat).
    # NOTE: Yahan koi aur logic add karein agar aap normal private messages ko handle karte hain.
    pass 


# --- Helper function for asking without client.ask ---
async def custom_ask(client: Client, chat_id: int, prompt: str, timeout: int = 600) -> Message | None:
    """Sends a prompt and waits for the user's next message."""
    
    # 1. Send the prompt message to the user
    await client.send_message(chat_id, prompt, parse_mode=ParseMode.MARKDOWN)
    
    # 2. Create a Future object to wait for the next message
    waiter = asyncio.get_event_loop().create_future()
    NEXT_MESSAGE_WAITERS[chat_id] = waiter
    
    try:
        # 3. Wait for the message (Future is set by custom_ask_listener)
        msg = await asyncio.wait_for(waiter, timeout=timeout)
        return msg
    except asyncio.TimeoutError:
        return None
    finally:
        # 4. Clean up the waiter dictionary if it's still there
        if chat_id in NEXT_MESSAGE_WAITERS:
            del NEXT_MESSAGE_WAITERS[chat_id]


# Broadcast Sending Logic (Helper Function)
async def send_broadcast_message(client: Client, chat_id: int, message: Message):
    """
    Given a chat ID and a message object (the message to broadcast), 
    sends the message and handles different content types.
    
    Returns: (True/False, reason_string)
    """
    try:
        # We use message.copy() which is the best way to handle all media types (photo, video, text, etc.)
        await message.copy(chat_id, parse_mode=ParseMode.MARKDOWN)
        return (True, "Success")
    
    except UserIsBlocked:
        return (False, "Blocked")
    except ChatWriteForbidden:
        return (False, "Blocked") 
    except PeerIdInvalid:
        return (False, "Deleted/Invalid")
    # --- RPC Error Handling Improvement ---
    except RPCError as rpc_e:
        error_msg = str(rpc_e)
        
        # FIX for RPC Error (INPUT_USER_DEACTIVATED)
        if "INPUT_USER_DEACTIVATED" in error_msg or "USER_DEACTIVATED" in error_msg:
             return (False, "Deleted/Deactivated") # Treat deactivated users as deleted
             
        logger.error(f"RPC Error sending broadcast to chat {chat_id}: {rpc_e}")
        return (False, "Error")
    
    except FloodWait as fw:
        logger.warning(f"FloodWait of {fw.value}s encountered. Sleeping... (Broadcast by @asbhaibsr)")
        await asyncio.sleep(fw.value)
        # Retry the message after the sleep
        return await send_broadcast_message(client, chat_id, message) 
    except Exception as e:
        logger.error(f"General Error sending broadcast to chat {chat_id}: {e}")
        return (False, "Error")


# -----------------------------------------------------
# 1. PRIVATE CHAT BROADCAST (/broadcast)
# -----------------------------------------------------

@app.on_message(filters.command("broadcast") & filters.private)
async def pm_broadcast(client: Client, message: Message):

    if message.from_user.id != OWNER_ID:
        await send_and_auto_delete_reply(message, text="Oops! Sorry sweetie, yeh command sirf mere boss ke liye hai. 🤷‍♀️ (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return
        
    b_msg = None
    try:
        # Step 1: Prompt and Listen using the custom ask
        b_msg = await custom_ask(
            client=client,
            chat_id=message.from_user.id,
            prompt="**🚀 Private Broadcast:** Ab mujhe woh message bhejo jise tum users ko bhejna chahte ho. Photo, video, ya text kuch bhi! 💬",
            timeout=600 # 10 minutes timeout
        )
        
    except Exception as e:
        await send_and_auto_delete_reply(message, text="Broadcast cancel ho gaya. 😥", parse_mode=ParseMode.MARKDOWN)
        logger.error(f"Critical Broadcast Error in custom_ask: {e}")
        return
    
    # Timeout hone par 'None' return karta hai
    if b_msg is None:
        await send_and_auto_delete_reply(message, text="Mera dhyan bhatak gaya ya tumne time out kar diya. Broadcast cancel ho gaya. 😥", parse_mode=ParseMode.MARKDOWN)
        logger.warning("Broadcast cancelled by timeout: User failed to reply in time.")
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

    # Initial status message
    sts = await message.reply_text(f"🚀 **Private Broadcast Shuru!** 🚀\n" 
                                   f"Cool, main **{total_targets}** private chats par message bhej rahi hoon.\n" 
                                   f"Sent: **0** / Blocked: **0** / Deleted: **0** (Total: {total_targets})", 
                                   parse_mode=ParseMode.MARKDOWN)

    start_time_broadcast = time.time()
    done = 0
    blocked = 0
    deleted = 0
    failed = 0
    success = 0
    
    logger.info(f"Starting PM broadcast to {total_targets} users. (Broadcast by @asbhaibsr)")

    # Sending logic
    for i, chat_id in enumerate(all_target_ids):
        pti, sh = await send_broadcast_message(client, chat_id, b_msg)
        
        if pti:
            success += 1
        else:
            if sh == "Blocked":
                blocked += 1
            elif sh == "Deleted/Invalid" or sh == "Deleted/Deactivated": # Check for the new deactivated status
                deleted += 1
            elif sh == "Error":
                failed += 1

        done += 1
        
        # Update status every 20 messages or when finished
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
                await asyncio.sleep(1) # Wait before next action
                
    time_taken = datetime.timedelta(seconds=int(time.time()-start_time_broadcast))
    final_message = (f"🎉 **Private Broadcast Complete!** 🎉\n" 
                     f"Completed in **{time_taken}** seconds.\n\n" 
                     f"Total Users Targeted: **{total_targets}**\n" 
                     f"Successfully Sent: **{success}** messages ✨\n" 
                     f"Blocked/Forbidden: **{blocked}** 💔\n"
                     f"Deleted/Invalid Peer: **{deleted}** 🗑️\n"
                     f"Other Failures: **{failed}** 😥\n\n"
                     f"Koi nahi, next time! 😉 (System by @asbhaibsr)")
    
    # Final summary
    try:
        await sts.edit_text(final_message, parse_mode=ParseMode.MARKDOWN)
    except Exception as final_edit_e:
        logger.error(f"Failed to send final broadcast summary: {final_edit_e}. Sending as new message instead.")
        await message.reply_text(final_message, parse_mode=ParseMode.MARKDOWN)

    await store_message(client, message)


# -----------------------------------------------------
# 2. GROUP BROADCAST (/grp_broadcast)
# -----------------------------------------------------

@app.on_message(filters.command("grp_broadcast") & filters.private)
async def broadcast_group(client: Client, message: Message):

    if message.from_user.id != OWNER_ID:
        await send_and_auto_delete_reply(message, text="Oops! Sorry sweetie, yeh command sirf mere boss ke liye hai. 🤷‍♀️ (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return
        
    b_msg = None
    try:
        # Step 1: Prompt and Listen using the custom ask
        b_msg = await custom_ask(
            client=client,
            chat_id=message.from_user.id,
            prompt="**🚀 Group Broadcast:** Ab mujhe woh message bhejo jise tum Groups ko bhejna chahte ho. Photo, video, ya text kuch bhi! 💬",
            timeout=600 # 10 minutes timeout
        )
        
    except Exception as e:
        await send_and_auto_delete_reply(message, text="Broadcast cancel ho gaya. 😥", parse_mode=ParseMode.MARKDOWN)
        logger.error(f"Critical Broadcast Error in custom_ask: {e}")
        return
    
    # Timeout hone par 'None' return karta hai
    if b_msg is None:
        await send_and_auto_delete_reply(message, text="Mera dhyan bhatak gaya ya tumne time out kar diya. Broadcast cancel ho gaya. 😥", parse_mode=ParseMode.MARKDOWN)
        logger.warning("Broadcast cancelled by timeout: User failed to reply in time.")
        return
    
    # Target IDs nikalna (Sirf Groups)
    group_chat_ids = [g["_id"] for g in group_tracking_collection.find({})]
    all_target_ids = list(set(group_chat_ids))

    total_targets = len(all_target_ids)
    
    if total_targets == 0:
        await send_and_auto_delete_reply(message, text="Mujhe koi Group mila hi nahi jise message bheja ja sake. Pehle mujhe Groups mein add karo! 🥺", parse_mode=ParseMode.MARKDOWN)
        return

    # Initial status message
    sts = await message.reply_text(f"🚀 **Group Broadcast Shuru!** 🚀\n" 
                                   f"Cool, main **{total_targets}** Groups par message bhej rahi hoon.\n" 
                                   f"Sent: **0** / Failed: **0** (Total: {total_targets})", 
                                   parse_mode=ParseMode.MARKDOWN)

    start_time_broadcast = time.time()
    done = 0
    failed = 0
    success = 0
    
    logger.info(f"Starting Group broadcast to {total_targets} groups. (Broadcast by @asbhaibsr)")

    # Sending logic
    for i, chat_id in enumerate(all_target_ids):
        pti, sh = await send_broadcast_message(client, chat_id, b_msg)
        
        if pti:
            success += 1
        else:
            failed += 1

        done += 1
        
        # Update status every 20 messages or when finished
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
                await asyncio.sleep(1) # Wait before next action
                
    time_taken = datetime.timedelta(seconds=int(time.time()-start_time_broadcast))
    final_message = (f"🎉 **Group Broadcast Complete!** 🎉\n" 
                     f"Completed in **{time_taken}** seconds.\n\n" 
                     f"Total Groups Targeted: **{total_targets}**\n" 
                     f"Successfully Sent: **{success}** messages ✨\n" 
                     f"Failed/Forbidden: **{failed}** messages 💔\n\n"
                     f"Koi nahi, next time! 😉 (System by @asbhaibsr)")
    
    # Final summary
    try:
        await sts.edit_text(final_message, parse_mode=ParseMode.MARKDOWN)
    except Exception as final_edit_e:
        logger.error(f"Failed to send final broadcast summary: {final_edit_e}. Sending as new message instead.")
        await message.reply_text(final_message, parse_mode=ParseMode.MARKDOWN)

    await store_message(client, message)
