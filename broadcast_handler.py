# broadcast_handler.py
import asyncio
import os
import sys
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatType, ParseMode
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

# -----------------------------------------------------
# BROADCAST COMMAND
# -----------------------------------------------------

@app.on_message(filters.command("broadcast") & filters.private)
async def broadcast_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    if message.from_user.id != OWNER_ID:
        await send_and_auto_delete_reply(message, text="Oops! Sorry sweetie, yeh command sirf mere boss ke liye hai. 🤷‍♀️ (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return

    broadcast_text = None
    broadcast_photo = None
    broadcast_sticker = None
    broadcast_video = None
    broadcast_document = None

    if message.reply_to_message:
        replied_msg = message.reply_to_message
        if replied_msg.text: broadcast_text = replied_msg.text
        elif replied_msg.photo: broadcast_photo = replied_msg.photo.file_id; broadcast_text = replied_msg.caption
        elif replied_msg.sticker: broadcast_sticker = replied_msg.sticker.file_id
        elif replied_msg.video: broadcast_video = replied_msg.video.file_id; broadcast_text = replied_msg.caption
        elif replied_msg.document: broadcast_document = replied_msg.document.file_id; broadcast_text = replied_msg.caption
    elif len(message.command) > 1:
        broadcast_text = message.text.split(None, 1)[1] 

    if not any([broadcast_text, broadcast_photo, broadcast_sticker, broadcast_video, broadcast_document]):
        await send_and_auto_delete_reply(message, text="Broadcast karne ke liye koi content nahi mila. Please text, sticker, photo, video, ya document bhejo ya reply karo. 🤔", parse_mode=ParseMode.MARKDOWN)
        return

    # Database se IDs nikalna
    group_chat_ids = [g["_id"] for g in group_tracking_collection.find({})]
    private_chat_ids = [u["_id"] for u in user_tracking_collection.find({})]
    all_target_ids = list(set(group_chat_ids + private_chat_ids))
    if OWNER_ID in all_target_ids: all_target_ids.remove(OWNER_ID)

    total_targets = len(all_target_ids)
    sent_count = 0
    failed_count = 0
    
    status_message = await message.reply_text(f"🚀 **Broadcast Shuru!** 🚀\n" f"Cool, main **{total_targets}** chats par message bhej rahi hoon.\n" f"Sent: **0** / Failed: **0** (Total: {total_targets})", parse_mode=ParseMode.MARKDOWN)

    logger.info(f"Starting broadcast to {total_targets} chats (groups and users). (Broadcast by @asbhaibsr)")

    for i, chat_id in enumerate(all_target_ids):
        try:
            if broadcast_photo: await client.send_photo(chat_id, broadcast_photo, caption=broadcast_text, parse_mode=ParseMode.MARKDOWN)
            elif broadcast_sticker: await client.send_sticker(chat_id, broadcast_sticker)
            elif broadcast_video: await client.send_video(chat_id, broadcast_video, caption=broadcast_text, parse_mode=ParseMode.MARKDOWN)
            elif broadcast_document: await client.send_document(chat_id, broadcast_document, caption=broadcast_text, parse_mode=ParseMode.MARKDOWN)
            elif broadcast_text: await client.send_message(chat_id, broadcast_text, parse_mode=ParseMode.MARKDOWN)
            
            sent_count += 1
            if (i + 1) % 10 == 0 or (i + 1) == total_targets:
                try:
                    await status_message.edit_text(f"🚀 **Broadcast Progress...** 🚀\n" f"Cool, main **{total_targets}** chats par message bhej rahi hoon.\n" f"Sent: **{sent_count}** / Failed: **{failed_count}** (Total: {total_targets})", parse_mode=ParseMode.MARKDOWN)
                except Exception as edit_e:
                    logger.warning(f"Failed to edit broadcast status message: {edit_e}")
            await asyncio.sleep(0.1)
        except (UserIsBlocked, ChatWriteForbidden, PeerIdInvalid) as client_error:
            failed_count += 1
            logger.warning(f"Skipping broadcast to {chat_id} due to client error (blocked/forbidden/invalid): {client_error}")
        except FloodWait as fw:
            failed_count += 1
            logger.warning(f"FloodWait of {fw.value} seconds encountered. Sleeping... (Broadcast by @asbhaibsr)")
            await asyncio.sleep(fw.value)
        except RPCError as rpc_e:
            failed_count += 1
            logger.error(f"RPC Error sending broadcast to chat {chat_id}: {rpc_e}. (Broadcast by @asbhaibsr)")
        except Exception as e:
            failed_count += 1
            logger.error(f"Failed to send broadcast to chat {chat_id}: {e}. (Broadcast by @asbhaibsr)")
        
    final_message = (f"🎉 **Broadcast Complete!** 🎉\n" f"Total chats targeted: **{total_targets}**\n" f"Successfully sent: **{sent_count}** messages ✨\n" f"Failed to send: **{failed_count}** messages 💔\n\n" f"Koi nahi, next time! 😉 (System by @asbhaibsr)")
    
    try:
        await status_message.edit_text(final_message, parse_mode=ParseMode.MARKDOWN)
    except Exception as final_edit_e:
        logger.error(f"Failed to send final broadcast summary: {final_edit_e}. Sending as new message instead.")
        await send_and_auto_delete_reply(message, text=final_message, parse_mode=ParseMode.MARKDOWN)

    await store_message(message)
    logger.info(f"Broadcast command processed by owner {message.from_user.id}. (Code by @asbhaibsr)")
