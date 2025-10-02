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

# --- Global dictionary to store the status of ongoing broadcasts ---
# Iska upyog yeh track karne ke liye hoga ki owner ne kis prompt message ka reply kiya hai.
BROADCAST_PROMPTS = {}

# Broadcast Sending Logic (Helper Function)
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
    except FloodWait as fw:
        logger.warning(f"FloodWait of {fw.value}s encountered. Sleeping... (Broadcast by @asbhaibsr)")
        await asyncio.sleep(fw.value)
        return await send_broadcast_message(client, chat_id, message) 
    except RPCError as rpc_e:
        logger.error(f"RPC Error sending broadcast to chat {chat_id}: {rpc_e}")
        return (False, "Error")
    except Exception as e:
        logger.error(f"General Error sending broadcast to chat {chat_id}: {e}")
        return (False, "Error")

# -----------------------------------------------------
# 0. REPLY-BASED MESSAGE LISTENER (New)
# -----------------------------------------------------

@app.on_message(filters.private & filters.user(OWNER_ID) & filters.reply)
async def listen_for_broadcast_reply(client: Client, message: Message):
    # Check if the replied message is a prompt sent by the bot for a broadcast
    if message.reply_to_message and message.reply_to_message.id in BROADCAST_PROMPTS:
        prompt_info = BROADCAST_PROMPTS.pop(message.reply_to_message.id)
        prompt_info['message_container'][0] = message # Store the actual message
        
        # Stop the waiting future/event
        if prompt_info['event']:
            prompt_info['event'].set()
        
        # We don't need to reply here, the main broadcast function will handle the flow.


# -----------------------------------------------------
# 1. PRIVATE CHAT BROADCAST (/broadcast)
# -----------------------------------------------------

@app.on_message(filters.command("broadcast") & filters.private)
async def pm_broadcast(client: Client, message: Message):

    if message.from_user.id != OWNER_ID:
        await send_and_auto_delete_reply(message, text="Oops! Sorry sweetie, yeh command sirf mere boss ke liye hai. 🤷‍♀️ (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return
        
    b_msg_container = [None]
    timeout = 600 # 10 minutes timeout
    wait_event = asyncio.Event()

    try:
        # Step 1: Prompt the user and ask them to REPLY to this message
        prompt_msg = await client.send_message(
            chat_id=message.from_user.id,
            text="**🚀 Private Broadcast:** Ab mujhe woh message (Photo, video, ya text) **REPLY** karke bhejo jise tum users ko bhejna chahte ho. 💬",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Step 2: Set up the global tracking for this prompt
        BROADCAST_PROMPTS[prompt_msg.id] = {
            'message_container': b_msg_container,
            'event': wait_event,
            'type': 'pm_broadcast'
        }
        
        # Step 3: Wait for the reply message or timeout
        await asyncio.wait_for(wait_event.wait(), timeout=timeout)
        
        # Check if the reply message was received
        b_msg = b_msg_container[0]
        if b_msg is None:
             raise asyncio.TimeoutError # Should be handled by wait_for, but check just in case.
             
    except asyncio.TimeoutError:
        await send_and_auto_delete_reply(message, text="Mera dhyan bhatak gaya ya tumne time out kar diya. Broadcast cancel ho gaya. 😥", parse_mode=ParseMode.MARKDOWN)
        logger.warning("Broadcast cancelled by timeout: User failed to reply in time.")
        return
    except Exception as e:
        await send_and_auto_delete_reply(message, text="Koi error aa gayi. Broadcast cancel ho gaya. 😥", parse_mode=ParseMode.MARKDOWN)
        logger.error(f"Broadcast cancelled by error during listening process: {e}")
        return
    finally:
        # Clean up the prompt tracking regardless of success/failure
        if prompt_msg.id in BROADCAST_PROMPTS:
            del BROADCAST_PROMPTS[prompt_msg.id]
    
    # --- Broadcast Execution Logic ---
    
    # Target IDs nikalna (Groups aur Owner ID ko hata kar)
    private_chat_ids = [u["_id"] for u in user_tracking_collection.find({})]
    all_target_ids = list(set(private_chat_ids))
    if OWNER_ID in all_target_ids: 
        all_target_ids.remove(OWNER_ID)

    total_targets = len(all_target_ids)
    # ... (rest of the broadcast logic remains the same, using b_msg)
    
    if total_targets == 0:
        await send_and_auto_delete_reply(message, text="Mujhe koi user mila hi nahi jise message bheja ja sake (Owner ko chhodkar). 🤷‍♀️", parse_mode=ParseMode.MARKDOWN)
        return

    # Initial status message
    # ... (status message creation)
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
            elif sh == "Deleted/Invalid":
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
# 3. GROUP BROADCAST (/grp_broadcast)
# -----------------------------------------------------

@app.on_message(filters.command("grp_broadcast") & filters.private)
async def broadcast_group(client: Client, message: Message):

    if message.from_user.id != OWNER_ID:
        await send_and_auto_delete_reply(message, text="Oops! Sorry sweetie, yeh command sirf mere boss ke liye hai. 🤷‍♀️ (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return
        
    b_msg_container = [None]
    timeout = 600 # 10 minutes timeout
    wait_event = asyncio.Event()
    
    try:
        # Step 1: Prompt the user and ask them to REPLY to this message
        prompt_msg = await client.send_message(
            chat_id=message.from_user.id,
            text="**🚀 Group Broadcast:** Ab mujhe woh message (Photo, video, ya text) **REPLY** karke bhejo jise tum Groups ko bhejna chahte ho. 💬",
            parse_mode=ParseMode.MARKDOWN
        )

        # Step 2: Set up the global tracking for this prompt
        BROADCAST_PROMPTS[prompt_msg.id] = {
            'message_container': b_msg_container,
            'event': wait_event,
            'type': 'grp_broadcast'
        }
        
        # Step 3: Wait for the reply message or timeout
        await asyncio.wait_for(wait_event.wait(), timeout=timeout)
        
        # Check if the reply message was received
        b_msg = b_msg_container[0]
        if b_msg is None:
             raise asyncio.TimeoutError 

    except asyncio.TimeoutError:
        await send_and_auto_delete_reply(message, text="Mera dhyan bhatak gaya ya tumne time out kar diya. Broadcast cancel ho gaya. 😥", parse_mode=ParseMode.MARKDOWN)
        logger.warning("Broadcast cancelled by timeout: User failed to reply in time.")
        return
    except Exception as e:
        await send_and_auto_delete_reply(message, text="Koi error aa gayi. Broadcast cancel ho gaya. 😥", parse_mode=ParseMode.MARKDOWN)
        logger.error(f"Broadcast cancelled by error during listening process: {e}")
        return
    finally:
        # Clean up the prompt tracking regardless of success/failure
        if prompt_msg.id in BROADCAST_PROMPTS:
            del BROADCAST_PROMPTS[prompt_msg.id]
    
    # --- Broadcast Execution Logic ---
    
    # Target IDs nikalna (Sirf Groups)
    group_chat_ids = [g["_id"] for g in group_tracking_collection.find({})]
    all_target_ids = list(set(group_chat_ids))

    total_targets = len(all_target_ids)
    
    if total_targets == 0:
        await send_and_auto_delete_reply(message, text="Mujhe koi Group mila hi nahi jise message bheja ja sake. Pehle mujhe Groups mein add karo! 🥺", parse_mode=ParseMode.MARKDOWN)
        return

    # Initial status message
    # ... (status message creation)
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
