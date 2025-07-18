import os
import asyncio
import threading
import time
import logging
import re
import random
import sys

import pytz

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.raw.functions.messages import SetTyping
from pyrogram.raw.types import SendMessageTypingAction
from pyrogram.enums import ChatType, ChatMemberStatus, ParseMode

from pymongo import MongoClient
from datetime import datetime, timedelta

# Flask imports
from flask import Flask, request, jsonify

# --- Logger Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Environment Variables ---
BOT_TOKEN = os.getenv("BOT_TOKEN")

MONGO_URI_MESSAGES = os.getenv("MONGO_URI_MESSAGES")
MONGO_URI_BUTTONS = os.getenv("MONGO_URI_BUTTONS")
MONGO_URI_TRACKING = os.getenv("MONGO_URI_TRACKING")

OWNER_ID = int(os.getenv("OWNER_ID")) # Ensure OWNER_ID is an integer for comparison

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

# --- Constants ---
MAX_MESSAGES_THRESHOLD = 100000
PRUNE_PERCENTAGE = 0.30
UPDATE_CHANNEL_USERNAME = "asbhai_bsr"
ASBHAI_USERNAME = "asbhaibsr" # Owner's username for contact
ASFILTER_BOT_USERNAME = "asfilter_bot" # The bot for premium rewards
BOT_PHOTO_URL = "https://envs.sh/FU3.jpg" # Consider updating this URL if it's generic
REPO_LINK = "https://github.com/asbhaibsr/Chatbot-asbhai.git"

# Regex for common URL patterns including t.me and typical link formats
URL_PATTERN = re.compile(r"(?:https?://|www\.|t\.me/)[^\s/$.?#].[^\s]*", re.IGNORECASE)


# --- MongoDB Setup ---
try:
    client_messages = MongoClient(MONGO_URI_MESSAGES)
    db_messages = client_messages.bot_database_messages
    messages_collection = db_messages.messages
    logger.info("MongoDB (Messages) connection successful. Credit: @asbhaibsr")

    client_buttons = MongoClient(MONGO_URI_BUTTONS)
    db_buttons = client_buttons.bot_button_data
    buttons_collection = db_buttons.button_interactions
    logger.info("MongoDB (Buttons) connection successful. Credit: @asbhaibsr")

    client_tracking = MongoClient(MONGO_URI_TRACKING)
    db_tracking = client_tracking.bot_tracking_data
    group_tracking_collection = db_tracking.groups_data
    user_tracking_collection = db_tracking.users_data
    earning_tracking_collection = db_tracking.monthly_earnings_data
    reset_status_collection = db_tracking.reset_status
    biolink_exceptions_collection = db_tracking.biolink_exceptions # For biolink deletion exceptions
    # NEW: Collection for owner-taught responses
    owner_taught_responses_collection = db_tracking.owner_taught_responses
    # NEW: Collection for conversational learning (user A -> user B)
    conversational_learning_collection = db_tracking.conversational_learning

    logger.info("MongoDB (Tracking, Earning, Biolink Exceptions, Learning Data) connection successful. Credit: @asbhaibsr")

    # Create indexes for efficient querying if they don't exist
    messages_collection.create_index([("timestamp", 1)])
    messages_collection.create_index([("user_id", 1)])
    earning_tracking_collection.create_index([("group_message_count", -1)])
    # Ensure bot_enabled field exists for all groups, default to True
    group_tracking_collection.update_many(
        {"bot_enabled": {"$exists": False}},
        {"$set": {"bot_enabled": True}}
    )
    # Ensure new flags exist for all groups, default to False
    group_tracking_collection.update_many(
        {"linkdel_enabled": {"$exists": False}},
        {"$set": {"linkdel_enabled": False}}
    )
    group_tracking_collection.update_many(
        {"biolinkdel_enabled": {"$exists": False}},
        {"$set": {"biolinkdel_enabled": False}}
    )
    group_tracking_collection.update_many(
        {"usernamedel_enabled": {"$exists": False}},
        {"$set": {"usernamedel_enabled": False}}
    )

    # NEW: Create indexes for learning collections
    owner_taught_responses_collection.create_index([("trigger", 1)])
    conversational_learning_collection.create_index([("trigger", 1)])


except Exception as e:
    logger.error(f"Failed to connect to one or more MongoDB instances: {e}. Designed by @asbhaibsr")
    exit(1)

# --- Pyrogram Client ---
app = Client(
    "self_learning_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# --- Flask App Setup ---
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Bot is running! Developed by @asbhaibsr. Support: @aschat_group"

@flask_app.route('/health')
def health_check():
    return jsonify({"status": "ok", "message": "Bot is alive and healthy! Designed by @asbhaibsr"}), 200

def run_flask_app():
    flask_app.run(host='0.0.0.0', port=os.environ.get('PORT', 8000), debug=False)

# --- Cooldown dictionary (for commands) ---
user_cooldowns = {}
COMMAND_COOLDOWN_TIME = 3 # seconds (for commands like /start, /topusers)

def is_on_command_cooldown(user_id):
    last_command_time = user_cooldowns.get(user_id)
    if last_command_time is None:
        return False
    return (time.time() - last_command_time) < COMMAND_COOLDOWN_TIME

def update_command_cooldown(user_id):
    user_cooldowns[user_id] = time.time()

# --- Message Reply Cooldown (for general messages) ---
# Stores the timestamp when a chat's *last* general message was processed/replied to.
# Bot will wait 8 minutes after this timestamp before processing another general message in that chat.
chat_message_cooldowns = {}
MESSAGE_REPLY_COOLDOWN_TIME = 8 # seconds (8 seconds)

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

# --- Message Storage Logic ---
async def store_message(message: Message, is_owner_taught_pair=False, is_conversational_pair=False, trigger_content=None):
    # Refactored to only store relevant messages for learning or specific tracking
    try:
        # Avoid storing messages from bots
        if message.from_user and message.from_user.is_bot:
            logger.debug(f"Skipping storage for message from bot: {message.from_user.id}. (Code by @asbhaibsr)")
            return

        # NEW: Only store message data if it's part of a specific learning type
        # Or if it's a command being used (for command cooldowns and owner commands)
        # General messages will NOT be stored unless they are part of a learning pair
        is_command = message.text and message.text.startswith('/')

        if not is_owner_taught_pair and not is_conversational_pair and not is_command:
            logger.debug(f"Skipping general message storage for {message.id} as it's not a learning pair or command.")
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
            logger.debug(f"Unsupported message type for storage: {message.id}. (Code by @asbhaibsr)")
            return

        # Store for the new learning systems
        if is_owner_taught_pair and trigger_content:
            owner_taught_responses_collection.update_one(
                {"trigger": trigger_content},
                {"$addToSet": {"responses": message_data}}, # Use $addToSet to avoid duplicate responses
                upsert=True
            )
            logger.info(f"Owner-taught pair stored: Trigger '{trigger_content}', Response '{message_data.get('content') or message_data.get('sticker_id')}'")
        elif is_conversational_pair and trigger_content:
            conversational_learning_collection.update_one(
                {"trigger": trigger_content},
                {"$addToSet": {"responses": message_data}}, # Use $addToSet
                upsert=True
            )
            logger.info(f"Conversational pair stored: Trigger '{trigger_content}', Response '{message_data.get('content') or message_data.get('sticker_id')}'")
        else:
            # Only store messages_collection if it's a command or for other general tracking purposes
            # (though message_collection is mainly used for old-style learning and pruning, so we might re-evaluate its purpose)
            messages_collection.insert_one(message_data)
            logger.info(f"Message stored: {message.id} from {message.from_user.id if message.from_user else 'None'}. (Storage by @asbhaibsr)")

        # Earning tracking still happens for all eligible user messages in groups, regardless of learning storage
        if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP] and message.from_user and not message.from_user.is_bot:
            user_id_to_track = message.from_user.id
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
            logger.info(f"Group message count updated for user {user_id_to_track}. (Earning tracking by @asbhaibsr)")


        await prune_old_messages()

    except Exception as e:
        logger.error(f"Error storing message {message.id}: {e}. (System by @asbhaibsr)")

# --- Reply Generation Logic ---
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

    # NEW: Prioritize owner-taught responses
    if message.from_user.id == OWNER_ID:
        # If owner is the one sending the message, check if they are "training"
        # This will be handled by the self_reply_learning filter, not here.
        pass

    # First, check for owner-taught patterns (these are for general use after being taught by owner)
    owner_taught_doc = owner_taught_responses_collection.find_one({"trigger": {"$regex": f"^{re.escape(query_content)}$", "$options": "i"}})
    if owner_taught_doc and owner_taught_doc.get('responses'):
        chosen_response_data = random.choice(owner_taught_doc['responses'])
        logger.info(f"Owner-taught reply found for '{query_content}'.")
        return chosen_response_data

    # Second, check for conversational learning patterns (A says X -> B says Y)
    conversational_doc = conversational_learning_collection.find_one({"trigger": {"$regex": f"^{re.escape(query_content)}$", "$options": "i"}})
    if conversational_doc and conversational_doc.get('responses'):
        chosen_response_data = random.choice(conversational_doc['responses'])
        logger.info(f"Conversational reply found for '{query_content}'.")
        return chosen_response_data

    logger.info(f"No specific learning pattern found for '{query_content}'. Falling back to old keyword search if necessary. (Logic by @asbhaibsr)")

    # Original keyword search fallback (less prioritized now)
    query_keywords = extract_keywords(query_content)
    if query_keywords:
        keyword_regex = "|".join([re.escape(kw) for kw in query_keywords])
        # Find messages that contain any of the keywords and are not from the bot itself
        general_replies_cursor = messages_collection.find({
            "type": {"$in": ["text", "sticker"]},
            "content": {"$regex": f".*({keyword_regex}).*", "$options": "i"},
            "user_id": {"$ne": app.me.id}
        })
    else:
        # If no keywords, fall back to any random message (very general)
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

async def send_and_auto_delete_reply(message: Message, text: str = None, photo: str = None, reply_markup: InlineKeyboardMarkup = None, parse_mode: ParseMode = ParseMode.MARKDOWN, disable_web_page_preview: bool = False):
    """Sends a reply and schedules it for deletion after 3 minutes, unless it's a /start command."""
    # This function is now more robust for handling photo vs text, and deleting after delay.
    # The `disable_web_page_preview` is only passed to `reply_text`.

    sent_message = None

    user_info_str = ""
    if message.from_user:
        if message.from_user.username:
            user_info_str = f" (द्वारा: @{message.from_user.username})"
        else:
            user_info_str = f" (द्वारा: {message.from_user.first_name})"

    # Add user info to the reply text for command replies
    text_to_send = text
    # Only add command info if it's actually a command message
    if message.command and text:
        command_name = message.command[0]
        text_to_send = f"**कमांड:** `{command_name}`{user_info_str}\n\n{text}"
    elif text and message.chat.type == ChatType.PRIVATE and message.from_user.id == OWNER_ID:
        # For owner's private messages that aren't commands, just send the text as is.
        # This prevents "कमांड: None" when owner replies in private to bot.
        pass
    elif text and message.from_user:
        # For non-command messages from users, don't add "कमांड:" prefix
        pass


    if photo:
        sent_message = await message.reply_photo(
            photo=photo,
            caption=text_to_send, # Caption is for photo, use text_to_send here
            reply_markup=reply_markup,
            parse_mode=parse_mode,
            # disable_web_page_preview is NOT a valid argument for reply_photo
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

    # Do not delete /start messages
    if message.command and message.command[0] == "start":
        return sent_message

    # Schedule deletion after 3 minutes (180 seconds)
    async def delete_after_delay_task():
        await asyncio.sleep(180)
        try:
            if sent_message:
                await sent_message.delete()
            # Optionally, delete the user's original command message too
            # await message.delete()
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

# Import other parts of the bot
from earning_system import get_top_earning_users, reset_monthly_earnings_manual
from bot_commands import (
    start_private_command, start_group_command, callback_handler,
    top_users_command, broadcast_command, stats_private_command,
    stats_group_command, list_groups_command, leave_group_command,
    clear_data_command, delete_specific_message_command, delete_specific_sticker_command,
    clear_earning_command, restart_command, toggle_chat_command,
    toggle_linkdel_command, toggle_biolinkdel_command, allow_biolink_user_command,
    toggle_usernamedel_command, clear_all_dbs_command, handle_clearall_dbs_callback,
    clear_my_data_command, new_member_handler, left_member_handler
)

# --- Register Pyrogram Event Handlers ---
app.on_message(filters.command("start") & filters.private)(start_private_command)
app.on_message(filters.command("start") & filters.group)(start_group_command)
app.on_callback_query()(callback_handler)
app.on_message(filters.command("topusers") & (filters.private | filters.group))(top_users_command)
app.on_message(filters.command("broadcast") & filters.private)(broadcast_command)
app.on_message(filters.command("stats") & filters.private)(stats_private_command)
app.on_message(filters.command("stats") & filters.group)(stats_group_command)
app.on_message(filters.command("groups") & filters.private)(list_groups_command)
app.on_message(filters.command("leavegroup") & filters.private)(leave_group_command)
app.on_message(filters.command("cleardata") & filters.private)(clear_data_command)
app.on_message(filters.command("deletemessage") & filters.private)(delete_specific_message_command)
app.on_message(filters.command("delsticker") & filters.private)(delete_specific_sticker_command)
app.on_message(filters.command("clearearning") & filters.private)(clear_earning_command)
app.on_message(filters.command("restart") & filters.private)(restart_command)
app.on_message(filters.command("chat") & filters.group)(toggle_chat_command)
app.on_message(filters.command("linkdel") & filters.group)(toggle_linkdel_command)
app.on_message(filters.command("biolinkdel") & filters.group)(toggle_biolinkdel_command)
app.on_message(filters.command("biolink") & filters.group)(allow_biolink_user_command)
app.on_message(filters.command("usernamedel") & filters.group)(toggle_usernamedel_command)
app.on_message(filters.command("clearall") & filters.private)(clear_all_dbs_command)
app.on_callback_query(filters.regex("^(confirm_clearall_dbs|cancel_clearall_dbs)$"))(handle_clearall_dbs_callback)
app.on_message(filters.command("clearmydata"))(clear_my_data_command)
app.on_message(filters.new_chat_members)(new_member_handler)
app.on_message(filters.left_chat_member)(left_member_handler)

@app.on_message(filters.text | filters.sticker | filters.photo | filters.video | filters.document)
async def handle_all_messages(client: Client, message: Message):
    # Ignore messages from bots
    if message.from_user and message.from_user.is_bot:
        logger.debug(f"Skipping message from bot user: {message.from_user.id}.")
        return

    is_group_chat = message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]

    # Check if bot is enabled in group chats
    if is_group_chat:
        group_status = group_tracking_collection.find_one({"_id": message.chat.id})
        if group_status and not group_status.get("bot_enabled", True):
            logger.info(f"Bot is disabled in group {message.chat.id}. Skipping message handling.")
            return

    # Apply cooldown for general messages (not commands)
    # Commands are handled by their individual cooldowns
    if message.from_user and not (message.text and message.text.startswith('/')):
        chat_id_for_cooldown = message.chat.id
        if not await can_reply_to_chat(chat_id_for_cooldown): # Check cooldown for the specific chat
            logger.info(f"Chat {chat_id_for_cooldown} is on message reply cooldown. Skipping message {message.id}.")
            return # Skip processing and replying to this message

    logger.info(f"Processing message {message.id} from user {message.from_user.id if message.from_user else 'N/A'} in chat {message.chat.id} (type: {message.chat.type.name}).")

    if is_group_chat:
        logger.info(f"DEBUG: Message from group/supergroup {message.chat.id}. Calling update_group_info.")
        await update_group_info(message.chat.id, message.chat.title, message.chat.username)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)

    # --- NEW: Learning Logic (Owner-Taught & Conversational) ---

    # 1. Owner-Taught Learning (Owner replies to OWN message)
    if message.from_user and message.from_user.id == OWNER_ID and message.reply_to_message:
        replied_to_msg = message.reply_to_message
        if replied_to_msg.from_user and replied_to_msg.from_user.id == OWNER_ID:
            trigger_content = replied_to_msg.text if replied_to_msg.text else (replied_to_msg.sticker.emoji if replied_to_msg.sticker else None)

            if trigger_content:
                # Prepare response data (similar structure to message_data in store_message)
                response_data = {
                    "message_id": message.id,
                    "user_id": message.from_user.id,
                    "username": message.from_user.username,
                    "first_name": message.from_user.first_name,
                    "chat_id": message.chat.id,
                    "chat_type": message.chat.type.name,
                    "chat_title": message.chat.title if message.chat.type != ChatType.PRIVATE else None,
                    "timestamp": datetime.now(),
                    "credits": "Code by @asbhaibsr"
                }
                if message.text:
                    response_data["type"] = "text"
                    response_data["content"] = message.text
                elif message.sticker:
                    response_data["type"] = "sticker"
                    response_data["content"] = message.sticker.emoji if message.sticker.emoji else ""
                    response_data["sticker_id"] = message.sticker.file_id

                owner_taught_responses_collection.update_one(
                    {"trigger": trigger_content},
                    {"$addToSet": {"responses": response_data}}, # Use $addToSet to add unique responses
                    upsert=True
                )
                await message.reply_text("मालिक! 👑 मैंने यह बातचीत सीख ली है और अब इसे याद रखूंगी! 😉", parse_mode=ParseMode.MARKDOWN)
                logger.info(f"Owner {OWNER_ID} taught a new pattern: '{trigger_content}' -> '{response_data.get('content') or response_data.get('sticker_id')}'")
                return # Stop further processing as this was a learning action


    # 2. Conversational Learning (User A says X -> User B replies Y)
    # Only if the current message is a reply, not from the bot, and not from the owner (as owner has separate learning)
    if message.reply_to_message and message.from_user and message.from_user.id != OWNER_ID:
        replied_to_msg = message.reply_to_message
        # Ensure the replied-to message is not from a bot and not from the same user
        if replied_to_msg.from_user and not replied_to_msg.from_user.is_bot and replied_to_msg.from_user.id != message.from_user.id:
            trigger_content = replied_to_msg.text if replied_to_msg.text else (replied_to_msg.sticker.emoji if replied_to_msg.sticker else None)

            if trigger_content:
                response_data = {
                    "message_id": message.id,
                    "user_id": message.from_user.id,
                    "username": message.from_user.username,
                    "first_name": message.from_user.first_name,
                    "chat_id": message.chat.id,
                    "chat_type": message.chat.type.name,
                    "chat_title": message.chat.title if message.chat.type != ChatType.PRIVATE else None,
                    "timestamp": datetime.now(),
                    "credits": "Code by @asbhaibsr"
                }
                if message.text:
                    response_data["type"] = "text"
                    response_data["content"] = message.text
                elif message.sticker:
                    response_data["type"] = "sticker"
                    response_data["content"] = message.sticker.emoji if message.sticker.emoji else ""
                    response_data["sticker_id"] = message.sticker.file_id

                conversational_learning_collection.update_one(
                    {"trigger": trigger_content},
                    {"$addToSet": {"responses": response_data}}, # Add unique responses
                    upsert=True
                )
                logger.info(f"Learned conversational pattern: '{trigger_content}' -> '{response_data.get('content') or response_data.get('sticker_id')}'")
                # No direct reply from bot here to avoid interrupting natural conversation, just passive learning

    # --- END NEW LEARNING LOGIC ---


    # --- Moderation Checks ---
    # Moved moderation checks here to ensure they happen even if learning is not triggered
    if is_group_chat:
        current_group_settings = group_tracking_collection.find_one({"_id": message.chat.id})
        user_id = message.from_user.id if message.from_user else None

        is_sender_admin = False
        if user_id:
            is_sender_admin = await is_admin_or_owner(client, message.chat.id, user_id)

        # 1. Link Deletion Check (any link in message content)
        if current_group_settings and current_group_settings.get("linkdel_enabled", False) and message.text:
            if contains_link(message.text) and not is_sender_admin:
                try:
                    await message.delete()
                    sent_delete_alert = await message.reply_text(f"ओहो, ये क्या भेज दिया {message.from_user.mention}? 🧐 सॉरी-सॉरी, यहाँ **लिंक्स अलाउड नहीं हैं!** 🚫 आपका मैसेज तो गया!💨 अब से ध्यान रखना, हाँ?", quote=True, parse_mode=ParseMode.MARKDOWN)
                    asyncio.create_task(delete_after_delay_for_message(sent_delete_alert, 180)) # 3 minutes
                    logger.info(f"Deleted link message {message.id} from user {message.from_user.id} in chat {message.chat.id}.")
                    return
                except Exception as e:
                    logger.error(f"Error deleting link message {message.id}: {e}")
            elif contains_link(message.text) and is_sender_admin:
                logger.info(f"Admin's link message {message.id} was not deleted in chat {message.chat.id}.")

        # 2. Biolink Deletion Check (links in user's BIO)
        if current_group_settings and current_group_settings.get("biolinkdel_enabled", False) and user_id:
            try:
                user_chat_obj = await client.get_chat(user_id)
                user_bio = user_chat_obj.bio or ""

                is_biolink_exception = biolink_exceptions_collection.find_one({"_id": user_id})

                if not is_sender_admin and not is_biolink_exception:
                    if URL_PATTERN.search(user_bio):
                        try:
                            await message.delete()
                            sent_delete_alert = await message.reply_text(
                                f"अरे बाबा रे {message.from_user.mention}! 😲 आपकी **बायो में लिंक है!** इसीलिए आपका मैसेज गायब हो गया!👻\n"
                                "कृपया अपनी बायो से लिंक हटाएँ। यदि आपको यह अनुमति चाहिए, तो कृपया एडमिन से संपर्क करें और उन्हें `/biolink आपका_यूजरआईडी` कमांड देने को कहें।",
                                quote=True, parse_mode=ParseMode.MARKDOWN
                            )
                            asyncio.create_task(delete_after_delay_for_message(sent_delete_alert, 180)) # 3 minutes
                            logger.info(f"Deleted message {message.id} from user {user_id} due to link in bio in chat {message.chat.id}.")
                            return
                        except Exception as e:
                            logger.error(f"Error deleting message {message.id} due to bio link: {e}")
                elif (is_sender_admin or is_biolink_exception) and URL_PATTERN.search(user_bio):
                    logger.info(f"Admin's or excepted user's bio link was ignored for message {message.id} in chat {message.chat.id}.")

            except Exception as e:
                logger.error(f"Error checking user bio for user {user_id} in chat {message.chat.id}: {e}")

        # 3. Username Deletion Check (@mentions in message content)
        if current_group_settings and current_group_settings.get("usernamedel_enabled", False) and message.text:
            if contains_mention(message.text) and not is_sender_admin:
                try:
                    await message.delete()
                    sent_delete_alert = await message.reply_text(f"टच-टच {message.from_user.mention}! 😬 आपने `@` का इस्तेमाल किया! सॉरी, वो मैसेज तो चला गया आसमान में! 🚀 अगली बार से ध्यान रखना, हाँ? 😉", quote=True, parse_mode=ParseMode.MARKDOWN)
                    asyncio.create_task(delete_after_delay_for_message(sent_delete_alert, 180)) # 3 minutes
                    logger.info(f"Deleted username mention message {message.id} from user {message.from_user.id} in chat {message.chat.id}.")
                    return
                except Exception as e:
                    logger.error(f"Error deleting username message {message.id}: {e}")
            elif contains_mention(message.text) and is_sender_admin:
                logger.info(f"Admin's username mention message {message.id} was not deleted in chat {message.chat.id}.")
    # --- END MODERATION CHECKS ---

    # Only generate reply if message was NOT deleted by any of the above checks AND it's not a command
    if not (message.text and message.text.startswith('/')):
        logger.info(f"Attempting to generate reply for chat {message.chat.id}.")
        reply_doc = await generate_reply(message)

        if reply_doc:
            try:
                if reply_doc.get("type") == "text":
                    await message.reply_text(reply_doc["content"], parse_mode=ParseMode.MARKDOWN)
                    logger.info(f"Replied with text: {reply_doc['content']}.")
                elif reply_doc.get("type") == "sticker" and reply_doc.get("sticker_id"):
                    await message.reply_sticker(reply_doc["sticker_id"])
                    logger.info(f"Replied with sticker: {reply_doc['sticker_id']}.")
                else:
                    logger.warning(f"Reply document found but no content/sticker_id: {reply_doc}.")
            except Exception as e:
                logger.error(f"Error sending reply for message {message.id}: {e}.")
            finally:
                # Set cooldown AFTER a reply is sent
                update_message_reply_cooldown(message.chat.id)
        else:
            logger.info("No suitable reply found.")


# --- Main entry point ---
if __name__ == "__main__":
    logger.info("Starting Flask health check server in a separate thread...")
    flask_thread = threading.Thread(target=run_flask_app)
    flask_thread.start()

    logger.info("Starting Pyrogram bot...")

    app.run()

    # End of bot code. Thank you for using! Made with ❤️ by @asbhaibsr

