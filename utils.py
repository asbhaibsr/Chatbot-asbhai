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
        
        # New conversational learning logic
        if message.reply_to_message and message.reply_to_message.from_user and not message.reply_to_message.from_user.is_bot:
            replied_to_message = message.reply_to_message
            
            trigger_content = None
            trigger_type = None

            if replied_to_message.text:
                trigger_content = replied_to_message.text
                trigger_type = "text"
            elif replied_to_message.sticker:
                trigger_content = replied_to_message.sticker.file_id
                trigger_type = "sticker"
            
            if trigger_content and trigger_type:
                reply_content = None
                reply_type = None
                
                if message.text:
                    reply_content = message.text
                    reply_type = "text"
                elif message.sticker:
                    reply_content = message.sticker.file_id
                    reply_type = "sticker"
                
                if reply_content and reply_type:
                    conversational_learning_collection.update_one(
                        {"trigger_content": trigger_content, "trigger_type": trigger_type},
                        {"$push": {
                            "responses": {
                                "content": reply_content,
                                "type": reply_type,
                                "timestamp": datetime.now()
                            }
                        }},
                        upsert=True
                    )
                    logger.info(f"Conversational pattern stored: '{trigger_content}' -> '{reply_content}'.")


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
    if message.reply_to_message and message.reply_to_message.from_user and not message.reply_to_message.from_user.is_self:
        logger.info(f"Skipping reply for message {message.id} as it's a reply to another user.")
        return {"type": None}
    
    await app.invoke(
        SetTyping(
            peer=await app.resolve_peer(message.chat.id),
            action=SendMessageTypingAction()
        )
    )
    await asyncio.sleep(0.5)

    if not message.text and not message.sticker:
        return {"type": None}

    query_content = message.text if message.text else (message.sticker.file_id if message.sticker else "")
    query_type = "text" if message.text else "sticker"

    # 1. Search for a conversational learning pattern (exact match)
    conversational_doc = conversational_learning_collection.find_one({
        "trigger_content": query_content,
        "trigger_type": query_type
    })
    
    if conversational_doc and conversational_doc.get('responses'):
        chosen_response_data = random.choice(conversational_doc['responses'])
        logger.info(f"Conversational pattern reply found for '{query_content}'.")
        return chosen_response_data

    # 2. Search for a conversational learning pattern (partial match)
    if message.text:
        words = query_content.split()
        for i in range(min(5, len(words)), 0, -1):
            partial_query = " ".join(words[:i])
            if len(partial_query) > 0:
                conversational_doc = conversational_learning_collection.find_one({
                    "trigger_content": {"$regex": f"^{re.escape(partial_query)}.*", "$options": "i"},
                    "trigger_type": "text"
                })
                if conversational_doc and conversational_doc.get('responses'):
                    chosen_response_data = random.choice(conversational_doc['responses'])
                    logger.info(f"Partial conversational pattern reply found for '{query_content}'.")
                    return chosen_response_data
    
    # 3. Final fallback: send a completely random sticker
    logger.info("No suitable pattern found. Falling back to random sticker.")
    
    random_sticker_doc_cursor = messages_collection.aggregate([
        {"$match": {"type": "sticker", "user_id": {"$ne": app.me.id}}},
        {"$sample": {"size": 1}}
    ])
    
    random_sticker_doc = next(random_sticker_doc_cursor, None)
    
    if random_sticker_doc:
        logger.info(f"Random sticker found: {random_sticker_doc.get('sticker_id')}.")
        return {"type": "sticker", "sticker_id": random_sticker_doc.get('sticker_id'), "content": random_sticker_doc.get('content')}
    else:
        logger.warning("No stickers found in the database. No reply will be sent.")
        return {"type": None}

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

