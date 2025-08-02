# utlis.py

import re
import asyncio
import time
import logging
import random
from datetime import datetime, timedelta

import pytz
from pyrogram import Client
from pyrogram.types import Message, InlineKeyboardMarkup, User
from pyrogram.enums import ChatMemberStatus, ChatType, ParseMode
from pyrogram.raw.functions.messages import SetTyping
from pyrogram.raw.types import SendMessageTypingAction

from config import (
    messages_collection, owner_taught_responses_collection, conversational_learning_collection,
    group_tracking_collection, user_tracking_collection, earning_tracking_collection,
    reset_status_collection, biolink_exceptions_collection, app, logger,
    MAX_MESSAGES_THRESHOLD, PRUNE_PERCENTAGE, URL_PATTERN, OWNER_ID,
    user_cooldowns, COMMAND_COOLDOWN_TIME, chat_message_cooldowns, MESSAGE_REPLY_COOLDOWN_TIME
)

# Global dictionary to track the last earning message time for each user
earning_cooldowns = {}

def extract_keywords(text):
    if not text:
        return []
    words = re.findall(r'\b\w+\b', text.lower())
    return list(set(words))

async def prune_old_messages():
    total_messages = messages_collection.count_documents({})
    logger.info(f"Current total messages in DB: {total_messages}. (System by @asbhaibsr)")

    if total_messages > MAX_MESSAGES_THRESHOLD:
        messages_to_delete_count = int(total_messages * PRUNE_PERCENTAGE)
        logger.info(f"Threshold reached. Deleting {messages_to_delete_count} oldest messages. (System by @asbhaibsr)")

        oldest_message_ids = []
        for msg in messages_collection.find({}) \
                                            .sort("timestamp", 1) \
                                            .limit(messages_to_delete_count):
            oldest_message_ids.append(msg['_id'])

        if oldest_message_ids:
            delete_result = messages_collection.delete_many({"_id": {"$in": oldest_message_ids}})
            logger.info(f"Successfully deleted {delete_result.deleted_count} messages. (System by @asbhaibsr)")
        else:
            logger.warning("No oldest messages found to delete despite threshold being reached. (System by @asbhaibsr)")
    else:
        logger.info("Message threshold not reached. No pruning needed. (System by @asbhaibsr)")

async def is_admin_or_owner(client: Client, chat_id: int, user_id: int):
    if user_id == OWNER_ID:
        return True
    try:
        member = await client.get_chat_member(chat_id, user_id)
        if member.status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
            return True
    except Exception as e:
        if "CHAT_ADMIN_REQUIRED" in str(e):
            logger.warning(f"Bot is not an admin in chat {chat_id}, cannot check user {user_id} status. Assuming user is not an admin.")
            return False
        logger.error(f"Error checking admin status for user {user_id} in chat {chat_id}: {e}")
    return False

# `check_and_leave_if_not_admin` function ko yahan se hata diya gaya hai.

def contains_link(text: str):
    if not text:
        return False
    return bool(URL_PATTERN.search(text))

def contains_mention(text: str):
    if not text:
        return False
    mention_pattern = r"@[\w\d\._-]+"
    return bool(re.search(mention_pattern, text))

async def store_message(client: Client, message: Message):
    try:
        if message.from_user and message.from_user.is_bot:
            logger.debug(f"Skipping general storage for message from bot: {message.from_user.id}. (Code by @asbhaibsr)")
            return

        is_command = message.text and message.text.startswith('/')
        if is_command:
            logger.debug(f"Skipping general storage for command: {message.text}. (Code by @asbhaibsr)")
            return
        
        message_data = {
            "message_id": message.id,
            "user_id": message.from_user.id if message.from_user else None,
            "username": message.from_user.username if message.from_user else None,
            "first_name": message.from_user.first_name if message.from_user else None,
            "chat_id": message.chat.id,
            "chat_type": message.chat.type.name,
            "chat_title": message.chat.title if message.chat.type != ChatType.PRIVATE else None,
            "timestamp": datetime.now(),
            "credits": "Code by @asbhaibsr"
        }

        if message.text:
            message_data["type"] = "text"
            message_data["content"] = message.text
            message_data["keywords"] = extract_keywords(message.text)
            message_data["sticker_id"] = None
        elif message.sticker:
            message_data["type"] = "sticker"
            message_data["content"] = message.sticker.emoji if message.sticker.emoji else ""
            message_data["sticker_id"] = message.sticker.file_id
            message_data["keywords"] = extract_keywords(message.sticker.emoji)
        else:
            logger.debug(f"Unsupported message type for general storage: {message.id}. (Code by @asbhaibsr)")
            return
        
        messages_collection.insert_one(message_data)
        logger.info(f"General message stored: {message.id} from {message.from_user.id if message.from_user else 'None'}. (Storage by @asbhaibsr)")

        if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP] and message.from_user and not message.from_user.is_bot:
            user_id_to_track = message.from_user.id

            if message.reply_to_message:
                replied_to_user_id = message.reply_to_message.from_user.id if message.reply_to_message.from_user else None
                if replied_to_user_id and replied_to_user_id != user_id_to_track:
                    last_earning_time = earning_cooldowns.get(user_id_to_track, 0)
                    if time.time() - last_earning_time >= 8:
                        earning_cooldowns[user_id_to_track] = time.time()
                        
                        username_to_track = message.from_user.username
                        first_name_to_track = message.from_user.first_name
                        current_group_id = message.chat.id
                        current_group_title = message.chat.title
                        current_group_username = message.chat.username

                        earning_tracking_collection.update_one(
                            {"_id": user_id_to_track},
                            {"$inc": {"group_message_count": 1},
                             "$set": {"username": username_to_track,
                                      "first_name": first_name_to_track,
                                      "last_active_group_message": datetime.now(),
                                      "last_active_group_id": current_group_id,
                                      "last_active_group_title": current_group_title,
                                      "last_active_group_username": current_group_username
                                      },
                             "$setOnInsert": {"joined_earning_tracking": datetime.now(), "credit": "by @asbhaibsr"}},
                            upsert=True
                        )
                        logger.info(f"Earning message count updated for user {user_id_to_track} due to reply. (Earning tracking by @asbhaibsr)")
                    else:
                        logger.info(f"Earning message from user {user_id_to_track} skipped due to 8-second cooldown.")
                else:
                    logger.info(f"Earning message from user {user_id_to_track} skipped as it was a self-reply or not a reply.")
            else:
                logger.info(f"Earning message from user {user_id_to_track} skipped as it was not a reply.")

        await prune_old_messages()

    except Exception as e:
        logger.error(f"Error storing message {message.id}: {e}. (System by @asbhaibsr)")

async def generate_reply(message: Message):
    await app.invoke(
        SetTyping(
            peer=await app.resolve_peer(message.chat.id),
            action=SendMessageTypingAction()
        )
    )
    await asyncio.sleep(0.5)

    if not message.text and not message.sticker:
        return

    query_content = message.text if message.text else (message.sticker.emoji if message.sticker else "")
    
    if message.from_user and message.from_user.id == OWNER_ID:
        pass

    if message.reply_to_message and message.reply_to_message.from_user and message.reply_to_message.from_user.is_self:
        original_bot_message_content = message.reply_to_message.text if message.reply_to_message.text else (message.reply_to_message.sticker.emoji if message.reply_to_message.sticker else "")
        if original_bot_message_content:
            conversational_doc = conversational_learning_collection.find_one({"trigger": {"$regex": f"^{re.escape(original_bot_message_content)}$", "$options": "i"}})
            if conversational_doc and conversational_doc.get('responses'):
                chosen_response_data = random.choice(conversational_doc['responses'])
                logger.info(f"Bot-replied contextual reply found for '{original_bot_message_content}'.")
                return chosen_response_data
    
    owner_taught_doc = owner_taught_responses_collection.find_one({"trigger": {"$regex": f"^{re.escape(query_content)}$", "$options": "i"}})
    if owner_taught_doc and owner_taught_doc.get('responses'):
        chosen_response_data = random.choice(owner_taught_doc['responses'])
        logger.info(f"Owner-taught reply found for '{query_content}'.")
        return chosen_response_data
    
    conversational_doc = conversational_learning_collection.find_one({"trigger": {"$regex": f"^{re.escape(query_content)}$", "$options": "i"}})
    if conversational_doc and conversational_doc.get('responses'):
        chosen_response_data = random.choice(conversational_doc['responses'])
        logger.info(f"Conversational reply found for '{query_content}'.")
        return chosen_response_data

    logger.info(f"No specific learning pattern found for '{query_content}'. Falling back to old keyword search if necessary. (Logic by @asbhaibsr)")

    query_keywords = extract_keywords(query_content)
    if query_keywords:
        keyword_regex = "|".join([re.escape(kw) for kw in query_keywords])
        general_replies_cursor = messages_collection.find({
            "type": {"$in": ["text", "sticker"]},
            "content": {"$regex": f".*({keyword_regex}).*", "$options": "i"},
            "user_id": {"$ne": app.me.id}
        })
    else:
        general_replies_cursor = messages_collection.find({
            "type": {"$in": ["text", "sticker"]},
            "user_id": {"$ne": app.me.id}
        })

    potential_replies = []
    for doc in general_replies_cursor:
        potential_replies.append(doc)

    if potential_replies:
        chosen_reply = random.choice(potential_replies)
        logger.info(f"Keyword-based fallback reply found for '{query_content}': {chosen_reply.get('content') or chosen_reply.get('sticker_id')}.")
        return chosen_reply

    logger.info(f"No suitable reply found for: '{query_content}'.")
    return None

async def update_group_info(chat_id: int, chat_title: str, chat_username: str = None):
    try:
        group_tracking_collection.update_one(
            {"_id": chat_id},
            {"$set": {"title": chat_title, "username": chat_username, "last_updated": datetime.now()},
             "$setOnInsert": {"added_on": datetime.now(), "member_count": 0, "bot_enabled": True, "credit": "by @asbhaibsr"}},
            upsert=True
        )
        logger.info(f"Group info updated/inserted successfully for {chat_title} ({chat_id}). (Tracking by @asbhaibsr)")
    except Exception as e:
        logger.error(f"Error updating group info for {chat_title} ({chat_id}): {e}. (Tracking by @asbhaibsr)")

async def update_user_info(user_id: int, username: str, first_name: str):
    try:
        user_tracking_collection.update_one(
            {"_id": user_id},
            {"$set": {"username": username, "first_name": first_name, "last_active": datetime.now()},
             "$setOnInsert": {"joined_on": datetime.now(), "credit": "by @asbhaibsr"}},
            upsert=True
        )
        logger.info(f"User info updated/inserted successfully for {first_name} ({user_id}). (Tracking by @asbhaibsr)")
    except Exception as e:
        logger.error(f"Error updating user info for {first_name} ({user_id}): {e}. (Tracking by @asbhaibsr)")

async def get_top_earning_users():
    pipeline = [
        {"$match": {"group_message_count": {"$gt": 0}}},
        {"$sort": {"group_message_count": -1}},
    ]
    top_users_data = list(earning_tracking_collection.aggregate(pipeline))
    logger.info(f"Fetched top earning users: {len(top_users_data)} results. (Earning system by @asbhaibsr)")
    top_users_details = []
    for user_data in top_users_data:
        top_users_details.append({
            "user_id": user_data["_id"],
            "first_name": user_data.get("first_name", "Unknown User"),
            "username": user_data.get("username"),
            "message_count": user_data["group_message_count"],
            "last_active_group_id": user_data.get("last_active_group_id"),
            "last_active_group_title": user_data.get("last_active_group_title"),
            "last_active_group_username": user_data.get("last_active_group_username")
        })
    return top_users_details

async def reset_monthly_earnings_manual():
    logger.info("Manually resetting monthly earnings...")
    now = datetime.now(pytz.timezone('Asia/Kolkata'))
    try:
        earning_tracking_collection.update_many(
            {},
            {"$set": {"group_message_count": 0}}
        )
        logger.info("Monthly earning message counts reset successfully by manual command. (Earning system by @asbhaibsr)")
        reset_status_collection.update_one(
            {"_id": "last_manual_reset_date"},
            {"$set": {"last_reset_timestamp": now}},
            upsert=True
        )
        logger.info(f"Manual reset status updated. (Earning system by @asbhaibsr)")
    except Exception as e:
        logger.error(f"Error resetting monthly earnings manually: {e}. (Earning system by @asbhaibsr)")

def is_on_command_cooldown(user_id):
    last_command_time = user_cooldowns.get(user_id)
    if last_command_time is None:
        return False
    return (time.time() - last_command_time) < COMMAND_COOLDOWN_TIME

def update_command_cooldown(user_id):
    user_cooldowns[user_id] = time.time()

async def can_reply_to_chat(chat_id):
    last_reply_time = chat_message_cooldowns.get(chat_id)
    if last_reply_time is None:
        return True
    return (time.time() - last_reply_time) >= MESSAGE_REPLY_COOLDOWN_TIME

def update_message_reply_cooldown(chat_id):
    chat_message_cooldowns[chat_id] = time.time()

async def send_and_auto_delete_reply(message: Message, text: str = None, photo: str = None, reply_markup: InlineKeyboardMarkup = None, parse_mode: ParseMode = ParseMode.MARKDOWN, disable_web_page_preview: bool = False):
    sent_message = None
    user_info_str = ""
    if message.from_user:
        if message.from_user.username:
            user_info_str = f" (द्वारा: @{message.from_user.username})"
        else:
            user_info_str = f" (द्वारा: {message.from_user.first_name})"

    text_to_send = text
    if message.command and text:
        command_name = message.command[0]
        text_to_send = f"**कमांड:** `{command_name}`{user_info_str}\n\n{text}"
    elif text and message.chat.type == ChatType.PRIVATE and message.from_user and message.from_user.id == OWNER_ID:
        pass
    elif text and message.from_user:
        pass

    if photo:
        sent_message = await message.reply_photo(
            photo=photo,
            caption=text_to_send,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )
    elif text:
        sent_message = await message.reply_text(
            text_to_send,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
            disable_web_page_preview=disable_web_page_preview
        )
    else:
        logger.warning(f"send_and_auto_delete_reply called with no text or photo for message {message.id}.")
        return None

    if message.command and message.command[0] == "start":
        return sent_message

    async def delete_after_delay_task():
        await asyncio.sleep(180)
        try:
            if sent_message:
                await sent_message.delete()
        except Exception as e:
            logger.warning(f"Failed to delete message {sent_message.id if sent_message else 'N/A'} in chat {message.chat.id}: {e}")

    asyncio.create_task(delete_after_delay_task())
    return sent_message

async def delete_after_delay_for_message(message_obj: Message, delay: int):
    await asyncio.sleep(delay)
    try:
        await message_obj.delete()
    except Exception as e:
        logger.warning(f"Failed to delete message {message_obj.id} in chat {message_obj.chat.id}: {e}")
