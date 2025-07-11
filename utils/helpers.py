# utils/helpers.py

import asyncio
import re
import random
import time
import logging

from pyrogram import Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.raw.functions.messages import SetTyping
from pyrogram.raw.types import SendMessageTypingAction
from pyrogram.enums import ChatType, ChatMemberStatus, ParseMode

from config import (
    URL_PATTERN, COMMAND_COOLDOWN_TIME, MESSAGE_REPLY_COOLDOWN_TIME,
    MAX_MESSAGES_THRESHOLD, PRUNE_PERCENTAGE, OWNER_ID
)
# Import collections for helper functions that interact with DB
from database.mongo_setup import (
    messages_collection, buttons_collection, group_tracking_collection,
    user_tracking_collection, earning_tracking_collection
)


# --- Logger Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# --- Cooldown dictionary (for commands) ---
user_cooldowns = {}

def is_on_command_cooldown(user_id):
    last_command_time = user_cooldowns.get(user_id)
    if last_command_time is None:
        return False
    return (time.time() - last_command_time) < COMMAND_COOLDOWN_TIME

def update_command_cooldown(user_id):
    user_cooldowns[user_id] = time.time()

# --- Message Reply Cooldown (for general messages) ---
# Stores the timestamp when a chat's *last* general message was processed/replied to.
chat_message_cooldowns = {}

async def can_reply_to_chat(chat_id):
    last_reply_time = chat_message_cooldowns.get(chat_id)
    if last_reply_time is None:
        return True
    return (time.time() - last_reply_time) >= MESSAGE_REPLY_COOLDOWN_TIME

def update_message_reply_cooldown(chat_id):
    chat_message_cooldowns[chat_id] = time.time()


# --- Utility Functions ---
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

# Admin Check Utility
async def is_admin_or_owner(client: Client, chat_id: int, user_id: int):
    # Check if the user is the bot owner
    if user_id == OWNER_ID:
        return True

    # Check if the user is an admin in the group
    try:
        member = await client.get_chat_member(chat_id, user_id)
        if member.status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
            return True
    except Exception as e:
        logger.error(f"Error checking admin status for user {user_id} in chat {chat_id}: {e}")
    return False

# Function to check for links in message text (Uses global URL_PATTERN)
def contains_link(text: str):
    if not text:
        return False
    return bool(URL_PATTERN.search(text))

# Function to check for @mentions in message text
def contains_mention(text: str):
    if not text:
        return False
    # Regex for @mentions (starts with @ followed by word characters, dots, or dashes)
    mention_pattern = r"@[\w\d\._-]+"
    return bool(re.search(mention_pattern, text))


# --- Message Storage & Reply Generation moved to message_handlers.py and its sub-functions will be imported.
# Only store_message is defined here for import by handlers.
async def store_message(message: Message):
    """
    This is a placeholder for the actual store_message logic.
    The real logic is in handlers.message_handlers.py to avoid circular imports.
    This function will be called from there.
    """
    # This empty function definition here allows other modules to import it
    # without causing a circular import issue with message_handlers.py
    # The actual implementation resides in message_handlers.py
    pass

# --- Tracking Functions ---
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

# --- Earning System Functions ---
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
    logger.info("Manually resetting monthly earnings... (Earning system by @asbhaibsr)")
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

async def send_and_auto_delete_reply(message: Message, text: str = None, photo: str = None, reply_markup: InlineKeyboardMarkup = None, parse_mode: ParseMode = ParseMode.MARKDOWN, disable_web_page_preview: bool = False):
    """Sends a reply and schedules it for deletion after 3 minutes, unless it's a /start command."""
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
    elif text and message.chat.type == ChatType.PRIVATE and message.from_user.id == OWNER_ID:
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
    """Utility to delete a specific message after a delay."""
    await asyncio.sleep(delay)
    try:
        await message_obj.delete()
    except Exception as e:
        logger.warning(f"Failed to delete message {message_obj.id} in chat {message_obj.chat.id}: {e}")

