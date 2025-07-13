# --- IMPORTANT: THIS BOT CODE IS PROPERTY OF @asbhaibsr ---
# --- Unauthorized FORKING, REBRANDING, or RESELLING is STRICTLY PROHIBITED. ---
# Owner Telegram ID: @asbhaibsr
# Update Channel: @asbhai_bsr
# Support Group: @aschat_group
# Contact @asbhaibsr for any official inquiries or custom bots.
# --- DO NOT REMOVE THESE CREDITS ---

import os
import asyncio
import threading
import time

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.raw.functions.messages import SetTyping
from pyrogram.raw.types import SendMessageTypingAction
from pyrogram.enums import ChatType, ChatMemberStatus, ParseMode

from pymongo import MongoClient
from datetime import datetime, timedelta
import logging
import re
import random
import sys

import pytz

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
GAME_ACTIVE_TIMEOUT = 60 # seconds (1 minute)

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

# --- Game State Management ---
# Key: chat_id, Value: {target_number, player_id, attempts, last_activity_time, game_task}
game_states = {}

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
            "credits": "Code by @asbhaibsr, Support: @aschat_group"
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

# --- Pyrogram Event Handlers ---

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


@app.on_message(filters.command("start") & filters.private)
async def start_private_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    user_name = message.from_user.first_name if message.from_user else "Dost"

    welcome_message = (
        f"🌟 हे **{user_name}** जानू! आपका स्वागत है! 🌟\n\n"
        "मैं आपकी मदद करने के लिए तैयार हूँ!\n"
        "अपनी सभी कमांड्स देखने के लिए नीचे दिए गए 'सहायता' बटन पर क्लिक करें।"
    )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("➕ मुझे ग्रुप में जोड़ें", url=f"https://t.me/{client.me.username}?startgroup=true")
            ],
            [
                InlineKeyboardButton("📣 Updates Channel", url=f"https://t.me/{UPDATE_CHANNEL_USERNAME}"),
                InlineKeyboardButton("❓ Support Group", url="https://t.me/aschat_group")
            ],
            [
                InlineKeyboardButton("ℹ️ सहायता ❓", callback_data="show_help_menu"),
                InlineKeyboardButton("💰 Earning Leaderboard", callback_data="show_earning_leaderboard")
            ]
        ]
    )

    await send_and_auto_delete_reply(
        message,
        text=welcome_message,
        photo=BOT_PHOTO_URL,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )
    # Store command usage, not for learning
    await store_message(message) 
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)
    logger.info(f"Private start command processed for user {message.from_user.id}. (Code by @asbhaibsr)")

@app.on_message(filters.command("start") & filters.group)
async def start_group_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    user_name = message.from_user.first_name if message.from_user else "Dost"

    welcome_message = (
        f"🌟 हे **{user_name}** जानू! आपका स्वागत है! 🌟\n\n"
        "मैं ग्रुप की सभी बातें सुनने और सीखने के लिए तैयार हूँ!\n"
        "अपनी सभी कमांड्स देखने के लिए नीचे दिए गए 'सहायता' बटन पर क्लिक करें।"
    )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("➕ मुझे ग्रुप में जोड़ें", url=f"https://t.me/{client.me.username}?startgroup=true")
            ],
            [
                InlineKeyboardButton("📣 Updates Channel", url=f"https://t.me/{UPDATE_CHANNEL_USERNAME}"),
                InlineKeyboardButton("❓ Support Group", url="https://t.me/aschat_group")
            ]
            ,
            [
                InlineKeyboardButton("ℹ️ सहायता ❓", callback_data="show_help_menu"),
                InlineKeyboardButton("💰 Earning Leaderboard", callback_data="show_earning_leaderboard")
            ]
        ]
    )

    await send_and_auto_delete_reply(
        message,
        text=welcome_message,
        photo=BOT_PHOTO_URL,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )
    # Store command usage, not for learning
    await store_message(message)
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        logger.info(f"Attempting to update group info from /start command in chat {message.chat.id}.")
        await update_group_info(message.chat.id, message.chat.title, message.chat.username)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)
    logger.info(f"Group start command processed in chat {message.chat.id}. (Code by @asbhaibsr)")


@app.on_callback_query()
async def callback_handler(client, callback_query):
    # Answer the callback query immediately to remove loading state
    await callback_query.answer()

    if callback_query.data == "buy_git_repo":
        await send_and_auto_delete_reply(
            callback_query.message,
            text=f"🤩 अगर आपको मेरे जैसा खुद का bot बनवाना है, तो आपको ₹500 देने होंगे. इसके लिए **@{ASBHAI_USERNAME}** से contact करें और unhe bataiye ki aapko is bot ka code chahiye banwane ke liye. Jaldi karo, deals hot hain! 💸\n\n**Owner:** @asbhaibsr\n**Updates:** @asbhai_bsr\n**Support:** @aschat_group",
            parse_mode=ParseMode.MARKDOWN
        )
        buttons_collection.insert_one({
            "user_id": callback_query.from_user.id,
            "username": callback_query.from_user.username,
            "first_name": callback_query.from_user.first_name,
            "button_data": callback_query.data,
            "timestamp": datetime.now(),
            "credit": "by @asbhaibsr"
        })
    elif callback_query.data == "show_earning_leaderboard":
        await top_users_command(client, callback_query.message) # Pass the original message object
        buttons_collection.insert_one({
            "user_id": callback_query.from_user.id,
            "username": callback_query.from_user.username,
            "first_name": callback_query.from_user.first_name,
            "button_data": callback_query.data,
            "timestamp": datetime.now(),
            "credit": "by @asbhaibsr"
        })
    elif callback_query.data == "show_help_menu":
        help_text = (
            "💡 **Main Kaise Kaam Karti Hoon?**\n\n"
            "Main ek self-learning bot hoon jo conversations se seekhti hai. Aap groups mein ya mujhse private mein baat kar sakte hain, aur main aapke messages ko yaad rakhti hoon. Jab koi user similar baat karta hai, toh main usse seekhe hue reply deti hoon.\n\n"
            "**✨ Meri Commands:**\n"
            "• `/start`: Mujhse baat shuru karne ke liye.\n"
            "• `/help`: Yeh menu dekhne ke liye (jo aap abhi dekh rahe hain!).\n"
            "• `/topusers`: Sabse active users ka leaderboard dekhne ke liye.\n"
            "• `/clearmydata`: Apni saari baatein (jo maine store ki hain) delete karne ke liye.\n"
            "• `/chat on/off`: (Sirf Group Admins ke liye) Group mein meri messages band/chalu karne ke liye.\n"
            "• `/groups`: (Sirf Owner ke liye) Jin groups mein main hoon, unki list dekhne ke liye.\n"
            "• `/stats check`: Bot ke statistics dekhne ke liye.\n"
            "• `/cleardata <percentage>`: (Sirf Owner ke liye) Database se data delete karne ke liye.\n"
            "• `/deletemessage <content>`: (Sirf Owner ke liye) Specific **text message** delete karne ke liye.\n" # UPDATED HELP TEXT
            "• `/delsticker <percentage>`: (Sirf Owner ke liye) Database se **stickers** delete karne ke liye (e.g., `10%`, `20%`, `40%`).\n" # NEW HELP TEXT
            "• `/clearearning`: (Sirf Owner ke liye) Earning data reset karne ke liye.\n"
            "• `/clearall`: (Sirf Owner ke liye) Saara database (3 DBs) clear karne ke liye. **(Dhyan se!)**\n"
            "• `/leavegroup <group_id>`: (Sirf Owner ke liye) Kisi group ko chhodne ke liye.\n"
            "• `/broadcast <message>`: (Sirf Owner ke liye) Sabhi groups mein message bhejne ke liye.\n"
            "• `/restart`: (Sirf Owner ke liye) Bot ko restart karne ke liye.\n"
            "• `/linkdel on/off`: (Sirf Group Admins ke liye) Group mein **sabhi prakar ke links** delete/allow karne ke liye.\n"
            "• `/biolinkdel on/off`: (Sirf Group Admins ke liye) Group mein **users ke bio mein `t.me` aur `http/https` links** wale messages ko delete/allow karne ke liye.\n"
            "• `/biolink <userid>`: (Sirf Group Admins ke liye) `biolinkdel` on hone par bhi kisi user ko **bio mein `t.me` aur `http/https` links** रखने की permission dene ke liye.\n"
            "• `/usernamedel on/off`: (Sirf Group Admins ke liye) Group mein **'@' mentions** allow ya delete karne ke liye.\n\n"
            "**🔗 Mera Code (GitHub Repository):**\n"
            f"[**{REPO_LINK}**]({REPO_LINK})\n\n"
            "**Powered By:** @asbhaibsr\n**Updates:** @asbhai_bsr\n**Support:** @aschat_group"
        )
        await send_and_auto_delete_reply(callback_query.message, text=help_text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        buttons_collection.insert_one({
            "user_id": callback_query.from_user.id,
            "username": callback_query.from_user.username,
            "first_name": callback_query.from_user.first_name,
            "button_data": callback_query.data,
            "timestamp": datetime.now(),
            "credit": "by @asbhaibsr"
        })
    elif callback_query.data == "show_earning_rules":
        earning_rules_text = (
            "👑 **Earning Rules - VIP Guide!** 👑\n\n"
            "यहाँ बताया गया है कि आप मेरे साथ कैसे कमाई कर सकते हैं:\n\n"
            "**1. सक्रिय रहें (Be Active):**\n"
            "   • आपको ग्रुप में **वास्तविक और सार्थक बातचीत** करनी होगी।\n"
            "   • बेतरतीब मैसेज, स्पैमिंग, या सिर्फ़ इमोजी भेजने से आपकी रैंकिंग नहीं बढ़ेगी और आप अयोग्य भी हो सकते हैं।\n"
            "   • जितनी ज़्यादा अच्छी बातचीत, उतनी ज़्यादा कमाई के अवसर!\n\n"
            "**2. क्या करें, क्या न करें (Do's and Don'ts):**\n"
            "   • **करें:** सवालों के जवाब दें, चर्चा में भाग लें, नए विषय शुरू करें, अन्य सदस्यों के साथ इंटरैक्ट करें।\n"
            "   • **न करें:** बार-बार एक ही मैसेज भेजें, सिर्फ़ स्टिकर या GIF भेजें, असंबद्ध सामग्री पोस्ट करें, या ग्रुप के नियमों का उल्लंघन करें।\n\n"
            "**3. कमाई का समय (Earning Period):**\n"
            "   • कमाई हर **महीने** के पहले दिन रीसेट होगी। इसका मतलब है कि हर महीने आपके पास टॉप पर आने का एक नया मौका होगा!\n\n"
            "**4. अयोग्य होना (Disqualification):**\n"
            "   • यदि आप स्पैमिंग करते हुए पाए जाते हैं, या किसी भी तरह से सिस्टम का दुरुपयोग करने की कोशिश करते हैं, तो आपको लीडरबोर्ड से हटा दिया जाएगा और आप भविष्य की कमाई के लिए अयोग्य घोषित हो सकते हैं।\n"
            "   • ग्रुप के नियमों का पालन करना अनिवार्य है।\n\n"
            "**5. विथड्रावल (Withdrawal):**\n"
            "   • विथड्रावल हर महीने के **पहले हफ़्ते** में होगा।\n"
            "   • अपनी कमाई निकालने के लिए, आपको मुझे `@asbhaibsr` पर DM (डायरेक्ट मैसेज) करना होगा।\n\n"
            "**शुभकामनाएँ!** 🍀\n"
            "मुझे आशा है कि आप सक्रिय रहेंगे और हमारी कम्युनिटी में योगदान देंगे।\n\n"
            "**Powered By:** @asbhaibsr\n**Updates:** @asbhai_bsr\n**Support:** @aschat_group"
        )
        await send_and_auto_delete_reply(callback_query.message, text=earning_rules_text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        buttons_collection.insert_one({
            "user_id": callback_query.from_user.id,
            "username": callback_query.from_user.username,
            "first_name": callback_query.from_user.first_name,
            "button_data": callback_query.data,
            "timestamp": datetime.now(),
            "credit": "by @asbhaibsr"
        })

    logger.info(f"Callback query '{callback_query.data}' processed for user {callback_query.from_user.id}. (Code by @asbhaibsr)")

@app.on_message(filters.command("topusers") & (filters.private | filters.group))
async def top_users_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    top_users = await get_top_earning_users()

    if not top_users:
        await send_and_auto_delete_reply(message, text="😢 अब तक कोई भी उपयोगकर्ता लीडरबोर्ड पर नहीं है! सक्रिय होकर पहले बनें! ✨\n\n**Powered By:** @asbhaibsr", parse_mode=ParseMode.MARKDOWN)
        return

    earning_messages = [
        "👑 **Top Active Users - ✨ VIP Leaderboard! ✨** 👑\n\n"
    ]

    prizes = {
        1: "💰 ₹50",
        2: "💸 ₹30",
        3: "🎁 ₹20",
        4: f"🎬 @{ASFILTER_BOT_USERNAME} का 1 हफ़्ते का प्रीमियम प्लान", # Updated prize for 4th rank
        5: f"🎬 @{ASFILTER_BOT_USERNAME} का 3 दिन का प्रीमियम प्लान"  # New prize for 5th rank
    }

    for i, user in enumerate(top_users[:5]): # Display top 5 users
        rank = i + 1
        user_name = user.get('first_name', 'Unknown User')
        username_str = f"@{user.get('username')}" if user.get('username') else f"ID: `{user.get('user_id')}`"
        message_count = user.get('message_count', 0)
        
        # Determine prize string
        prize_str = prizes.get(rank, "🏅 कोई पुरस्कार नहीं") # Default for ranks > 5

        group_info = ""
        last_group_id = user.get('last_active_group_id')
        last_group_title = user.get('last_active_group_title', 'Unknown Group')

        if last_group_id:
            try:
                chat_obj = await client.get_chat(last_group_id)
                if chat_obj.type == ChatType.PRIVATE:
                    group_info = f"   • सक्रिय था: **[निजी चैट में](tg://user?id={user.get('user_id')})**\n"
                elif chat_obj.username:
                    group_info = f"   • सक्रिय था: **[{chat_obj.title}](https://t.me/{chat_obj.username})**\n"
                else:
                    # If no public username, try to get an invite link (only for supergroups/channels)
                    try:
                        # Note: export_chat_invite_link might not work if bot is not admin or for basic groups
                        invite_link = await client.export_chat_invite_link(last_group_id)
                        group_info = f"   • सक्रिय था: **[{chat_obj.title}]({invite_link})**\n"
                    except Exception:
                        group_info = f"   • सक्रिय था: **{chat_obj.title}** (निजी ग्रुप)\n"
            except Exception as e:
                logger.warning(f"Could not fetch chat info for group ID {last_group_id} for leaderboard: {e}")
                group_info = f"   • सक्रिय था: **{last_group_title}** (जानकारी उपलब्ध नहीं)\n"
        else:
            group_info = "   • सक्रिय था: **कोई ग्रुप गतिविधि नहीं**\n"


        earning_messages.append(
            f"**{rank}.** 🌟 **{user_name}** ({username_str}) 🌟\n"
            f"   • कुल मैसेज: **{message_count} 💬**\n"
            f"   • संभावित पुरस्कार: **{prize_str}**\n"
            f"{group_info}"
        )
    
    earning_messages.append(
        "\n_हर महीने की पहली तारीख को यह सिस्टम रीसेट होता है!_\n"
        "_ग्रुप के नियमों को जानने के लिए `/help` का उपयोग करें।_"
    )


    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("💰 पैसे निकलवाएँ (Withdraw)", url=f"https://t.me/{ASBHAI_USERNAME}"),
                InlineKeyboardButton("💰 Earning Rules", callback_data="show_earning_rules")
            ]
        ]
    )

    await send_and_auto_delete_reply(message, text="\n".join(earning_messages), reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
    # Store command usage, not for learning
    await store_message(message)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)
    logger.info(f"Top users command processed for user {message.from_user.id} in chat {message.chat.id}. (Code by @asbhaibsr)")

@app.on_message(filters.command("broadcast") & filters.private)
async def broadcast_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    if message.from_user.id != OWNER_ID:
        await send_and_auto_delete_reply(message, text="Oops! Sorry sweetie, yeh command sirf mere boss ke liye hai. 🤷‍♀️ (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return

    if len(message.command) < 2:
        await send_and_auto_delete_reply(message, text="Hey, broadcast karne ke liye kuch likho toh sahi! 🙄 Jaise: `/broadcast Aapka message yahan` (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return

    broadcast_text = " ".join(message.command[1:])

    group_chat_ids = group_tracking_collection.distinct("_id")
    private_chat_ids = user_tracking_collection.distinct("_id")

    all_target_ids = list(set(group_chat_ids + private_chat_ids))

    sent_count = 0
    failed_count = 0
    logger.info(f"Starting broadcast to {len(all_target_ids)} chats (groups and users). (Broadcast by @asbhaibsr)")

    for chat_id in all_target_ids:
        try:
            if chat_id == message.chat.id and message.chat.type == ChatType.PRIVATE:
                continue

            await client.send_message(chat_id, broadcast_text)
            sent_count += 1
            await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"Failed to send broadcast to chat {chat_id}: {e}. (Broadcast by @asbhaibsr)")
            failed_count += 1

    await send_and_auto_delete_reply(message, text=f"Broadcast ho gaya, darling! ✨ **{sent_count}** chats tak pahunchi, aur **{failed_count}** tak nahi. Koi nahi, next time! 😉 (System by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
    # Store command usage, not for learning
    await store_message(message)
    logger.info(f"Broadcast command processed by owner {message.from_user.id}. (Code by @asbhaibsr)")

@app.on_message(filters.command("stats") & filters.private)
async def stats_private_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    if len(message.command) < 2 or message.command[1].lower() != "check":
        await send_and_auto_delete_reply(message, text="Umm, stats check karne ke liye theek se likho na! `/stats check` aise. 😊 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return

    total_messages = messages_collection.count_documents({})
    unique_group_ids = group_tracking_collection.count_documents({})
    num_users = user_tracking_collection.count_documents({})
    total_owner_taught = owner_taught_responses_collection.count_documents({})
    total_conversational_learned = conversational_learning_collection.count_documents({})


    stats_text = (
        "📊 **Bot Statistics** 📊\n"
        f"• Jitne groups mein main hoon: **{unique_group_ids}** lovely groups!\n"
        f"• Total users jo maine observe kiye: **{num_users}** pyaare users!\n"
        f"• Total messages jo maine store kiye (Old Learning): **{total_messages}** baaton ka khazana! 🤩\n"
        f"• Owner-taught patterns: **{total_owner_taught}** unique patterns!\n" # NEW STAT
        f"• Conversational patterns learned: **{total_conversational_learned}** unique patterns!\n\n" # NEW STAT
        f"**Powered By:** @asbhaibsr\n**Updates:** @asbhai_bsr\n**Support:** @aschat_group"
    )
    await send_and_auto_delete_reply(message, text=stats_text, parse_mode=ParseMode.MARKDOWN)
    # Store command usage, not for learning
    await store_message(message)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)
    logger.info(f"Private stats command processed for user {message.from_user.id}. (Code by @asbhaibsr)")

@app.on_message(filters.command("stats") & filters.group)
async def stats_group_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    if len(message.command) < 2 or message.command[1].lower() != "check":
        await send_and_auto_delete_reply(message, text="Umm, stats check karne ke liye theek se likho na! `/stats check` aise. 😊 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return

    total_messages = messages_collection.count_documents({})
    unique_group_ids = group_tracking_collection.count_documents({})
    num_users = user_tracking_collection.count_documents({})
    total_owner_taught = owner_taught_responses_collection.count_documents({})
    total_conversational_learned = conversational_learning_collection.count_documents({})

    stats_text = (
        "📊 **Bot Statistics** 📊\n"
        f"• Jitne groups mein main hoon: **{unique_group_ids}** lovely groups!\n"
        f"• Total users jo maine observe kiye: **{num_users}** pyaare users!\n"
        f"• Total messages jo maine store kiye (Old Learning): **{total_messages}** baaton ka khazana! 🤩\n"
        f"• Owner-taught patterns: **{total_owner_taught}** unique patterns!\n" # NEW STAT
        f"• Conversational patterns learned: **{total_conversational_learned}** unique patterns!\n\n" # NEW STAT
        f"**Powered By:** @asbhaibsr\n**Updates:** @asbhai_bsr\n**Support:** @aschat_group"
    )
    await send_and_auto_delete_reply(message, text=stats_text, parse_mode=ParseMode.MARKDOWN)
    # Store command usage, not for learning
    await store_message(message)
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await update_group_info(message.chat.id, message.chat.title, message.chat.username)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)

# --- Group Management Commands ---

@app.on_message(filters.command("groups") & filters.private)
async def list_groups_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    if message.from_user.id != OWNER_ID:
        await send_and_auto_delete_reply(message, text="Oops! Sorry sweetie, yeh command sirf mere boss ke liye hai. Tumhe permission nahi hai. 🤷‍♀️ (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return

    groups = list(group_tracking_collection.find({}))
    if not groups:
        await send_and_auto_delete_reply(message, text="Main abhi kisi group mein nahi hoon. Akeli hoon, koi add kar lo na! 🥺 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return

    group_list_text = "📚 **Groups Jahan Main Hoon** 📚\n\n"
    for i, group in enumerate(groups):
        title = group.get("title", "Unknown Group")
        group_id = group.get("_id")
        group_username_from_db = group.get("username")
        added_on = group.get("added_on", "N/A").strftime("%Y-%m-%d %H:%M") if isinstance(group.get("added_on"), datetime) else "N/A"

        member_count = "N/A"
        group_link_display = ""
        try:
            chat_obj = await client.get_chat(group_id)
            member_count = await client.get_chat_members_count(group_id)
            if chat_obj.username:
                group_link_display = f" ([@{chat_obj.username}](https://t.me/{chat_obj.username}))"
            else:
                try:
                    invite_link = await client.export_chat_invite_link(group_id)
                    group_link_display = f" ([Invite Link]({invite_link}))"
                except Exception as e:
                    logger.warning(f"Could not get invite link for private group {group_id}: {e}")
                    group_link_display = " (Private Group)"
        except Exception as e:
            logger.warning(f"Could not fetch chat info for group {group_id}: {e}")
            group_link_display = " (Info N/A)"

        group_list_text += (
            f"{i+1}. **{title}** (`{group_id}`){group_link_display}\n"
            f"   • Joined: {added_on}\n"
            f"   • Members: {member_count}\n"
        )

    group_list_text += "\n_Yeh data tracking database se hai, bilkul secret!_ 🤫\n**Code & System By:** @asbhaibsr"
    await send_and_auto_delete_reply(message, text=group_list_text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
    # Store command usage, not for learning
    await store_message(message)
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)
    logger.info(f"Groups list command processed by owner {message.from_user.id}. (Code by @asbhaibsr)")

@app.on_message(filters.command("leavegroup") & filters.private)
async def leave_group_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    if message.from_user.id != OWNER_ID:
        await send_and_auto_delete_reply(message, text="Oops! Sorry sweetie, yeh command sirf mere boss ke liye hai. Tumhe permission nahi hai. 🤷‍♀️ (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return

    if len(message.command) < 2:
        await send_and_auto_delete_reply(message, text="Kripya group ID dein jisse aap mujhe hatana chahte hain. Upyog: `/leavegroup -1001234567890` (aise, darling!) (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return

    try:
        group_id_str = message.command[1]
        if not group_id_str.startswith('-100'):
            await send_and_auto_delete_reply(message, text="Aapne galat Group ID format diya hai. Group ID `-100...` se shuru hoti hai. Thoda dhyaan se! 😊 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
            return

        group_id = int(group_id_str)

        await client.leave_chat(group_id)

        group_tracking_collection.delete_one({"_id": group_id})
        messages_collection.delete_many({"chat_id": group_id}) # Clear old general messages
        # NEW: Clear learning data associated with this group
        owner_taught_responses_collection.delete_many({"responses.chat_id": group_id})
        conversational_learning_collection.delete_many({"responses.chat_id": group_id})
        
        logger.info(f"Considered cleaning earning data for users from left group {group_id}. (Code by @asbhaibsr)")

        await send_and_auto_delete_reply(message, text=f"Safaltapoorvak group `{group_id}` se bahar aa gayi, aur uska sara data bhi clean kar diya! Bye-bye! 👋 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Left group {group_id} and cleared its data. (Code by @asbhaibsr)")

    except ValueError:
        await send_and_auto_delete_reply(message, text="Invalid group ID format. Kripya ek valid numeric ID dein. Thoda number check kar lo! 😉 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await send_and_auto_delete_reply(message, text=f"Group se bahar nikalte samay galti ho gayi: {e}. Oh no! 😢 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        logger.error(f"Error leaving group {group_id_str}: {e}. (Code by @asbhaibsr)")

    # Store command usage, not for learning
    await store_message(message)
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)

# --- New Commands ---

@app.on_message(filters.command("cleardata") & filters.private)
async def clear_data_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    if message.from_user.id != OWNER_ID:
        await send_and_auto_delete_reply(message, text="Sorry, darling! Yeh command sirf mere boss ke liye hai. 🤫 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return

    if len(message.command) < 2:
        await send_and_auto_delete_reply(message, text="Kitna data clean karna hai? Percentage batao na, jaise: `/cleardata 10%` ya `/cleardata 100%`! 🧹 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return

    percentage_str = message.command[1].strip('%')
    try:
        percentage = int(percentage_str)
        if not (1 <= percentage <= 100):
            await send_and_auto_delete_reply(message, text="Percentage 1 se 100 ke beech mein hona chahiye. Thoda dhyan se! 🤔 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
            return
    except ValueError:
        await send_and_auto_delete_reply(message, text="Invalid percentage format. Percentage number mein hona chahiye, jaise `10` ya `50`. Fir se try karo!💖 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return

    # NEW: Prune ALL learning collections by percentage
    total_messages_old = messages_collection.count_documents({})
    total_owner_taught = owner_taught_responses_collection.count_documents({})
    total_conversational = conversational_learning_collection.count_documents({})

    deleted_count_old = 0
    deleted_count_owner_taught = 0
    deleted_count_conversational = 0

    if total_messages_old > 0:
        messages_to_delete_old = int(total_messages_old * (percentage / 100))
        oldest_message_ids = []
        for msg in messages_collection.find({}).sort("timestamp", 1).limit(messages_to_delete_old):
            oldest_message_ids.append(msg['_id'])
        if oldest_message_ids:
            deleted_count_old = messages_collection.delete_many({"_id": {"$in": oldest_message_ids}}).deleted_count

    if total_owner_taught > 0:
        docs_to_delete_owner = int(total_owner_taught * (percentage / 100))
        oldest_owner_taught_ids = []
        # Find _id of documents to delete based on oldest timestamp
        for doc in owner_taught_responses_collection.find({}).sort("responses.timestamp", 1).limit(docs_to_delete_owner): # Sort by nested timestamp
            oldest_owner_taught_ids.append(doc['_id'])
        if oldest_owner_taught_ids:
            deleted_count_owner_taught = owner_taught_responses_collection.delete_many({"_id": {"$in": oldest_owner_taught_ids}}).deleted_count


    if total_conversational > 0:
        docs_to_delete_conv = int(total_conversational * (percentage / 100))
        oldest_conv_ids = []
        # Find _id of documents to delete based on oldest timestamp
        for doc in conversational_learning_collection.find({}).sort("responses.timestamp", 1).limit(docs_to_delete_conv): # Sort by nested timestamp
            oldest_conv_ids.append(doc['_id'])
        if oldest_conv_ids:
            deleted_count_conversational = conversational_learning_collection.delete_many({"_id": {"$in": oldest_conv_ids}}).deleted_count
            
    total_deleted = deleted_count_old + deleted_count_owner_taught + deleted_count_conversational

    if total_deleted > 0:
        await send_and_auto_delete_reply(message, text=f"Wow! 🤩 Maine aapka **{percentage}%** data successfully delete kar diya! Total **{total_deleted}** entries (Old: {deleted_count_old}, Owner-Taught: {deleted_count_owner_taught}, Conversational: {deleted_count_conversational}) clean ho gayi. Ab main thodi light feel kar rahi hoon. ✨ (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Cleared {total_deleted} messages across collections based on {percentage}% request. (Code by @asbhaibsr)")
    else:
        await send_and_auto_delete_reply(message, text="Umm, kuch delete karne ke liye mila hi nahi. Lagta hai tumne pehle hi sab clean kar diya hai! 🤷‍♀️ (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)

    # Store command usage, not for learning
    await store_message(message)
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)

@app.on_message(filters.command("deletemessage") & filters.private)
async def delete_specific_message_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    if message.from_user.id != OWNER_ID:
        await send_and_auto_delete_reply(message, text="Oops! Sorry sweetie, yeh command sirf mere boss ke liye hai. 🤷‍♀️ (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return

    if len(message.command) < 2:
        await send_and_auto_delete_reply(message, text="Kaun sa **text message** delete karna hai, batao toh sahi! Jaise: `/deletemessage hello` ya `/deletemessage 'kya haal hai'` 👻 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return

    search_query = " ".join(message.command[1:])
    deleted_count = 0

    # NEW: Only delete TEXT messages based on content from all learning collections
    if search_query:
        # Delete from old messages collection
        delete_result_old = messages_collection.delete_many({"type": "text", "content": {"$regex": f".*{re.escape(search_query)}.*", "$options": "i"}})
        deleted_count += delete_result_old.deleted_count
        
        # Delete from owner_taught_responses collection (both trigger and specific responses)
        # Delete entire documents where the trigger matches
        delete_result_owner_taught_trigger = owner_taught_responses_collection.delete_many({"trigger": {"$regex": f"^{re.escape(search_query)}$", "$options": "i"}})
        deleted_count += delete_result_owner_taught_trigger.deleted_count
        
        # Pull responses where content matches (leaving the trigger if other responses exist)
        owner_taught_pull_result = owner_taught_responses_collection.update_many(
            {"responses.content": {"$regex": f".*{re.escape(search_query)}.*", "$options": "i"}},
            {"$pull": {"responses": {"content": {"$regex": f".*{re.escape(search_query)}.*", "$options": "i"}}}}
        )
        deleted_count += owner_taught_pull_result.modified_count

        # Delete from conversational_learning collection (both trigger and specific responses)
        delete_result_conv_trigger = conversational_learning_collection.delete_many({"trigger": {"$regex": f"^{re.escape(search_query)}$", "$options": "i"}})
        deleted_count += delete_result_conv_trigger.deleted_count

        conv_pull_result = conversational_learning_collection.update_many(
            {"responses.content": {"$regex": f".*{re.escape(search_query)}.*", "$options": "i"}},
            {"$pull": {"responses": {"content": {"$regex": f".*{re.escape(search_query)}.*", "$options": "i"}}}}
        )
        deleted_count += conv_pull_result.modified_count

    if deleted_count > 0:
        await send_and_auto_delete_reply(message, text=f"Jaisa hukum mere aaka! 🧞‍♀️ Maine '{search_query}' se milte-julte **{deleted_count}** **text messages** ko dhoondh ke delete kar diya. Ab woh history ka हिस्सा nahi raha! ✨ (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Deleted {deleted_count} text messages with query: '{search_query}'. (Code by @asbhaibsr)")
    else:
        await send_and_auto_delete_reply(message, text="Umm, mujhe tumhare is query se koi **text message** mila hi nahi apne database mein. Spelling check kar lo? 🤔 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)

    # Store command usage, not for learning
    await store_message(message)
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)


@app.on_message(filters.command("delsticker") & filters.private) # NEW COMMAND
async def delete_specific_sticker_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    if message.from_user.id != OWNER_ID:
        await send_and_auto_delete_reply(message, text="Oops! Sorry sweetie, yeh command sirf mere boss ke liye hai. 🤷‍♀️ (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return

    if len(message.command) < 2:
        await send_and_auto_delete_reply(message, text="Kitne **stickers** delete karne hai? Percentage batao na, jaise: `/delsticker 10%` ya `delsticker 20%` ya `delsticker 40%`! 🧹 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return

    percentage_str = message.command[1].strip('%')
    try:
        percentage = int(percentage_str)
        if not (1 <= percentage <= 100):
            await send_and_auto_delete_reply(message, text="Percentage 1 se 100 ke beech mein hona chahiye. Thoda dhyan se! 🤔 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
            return
    except ValueError:
        await send_and_auto_delete_reply(message, text="Invalid percentage format. Percentage number mein hona chahiye, jaise `10` ya `50`. Fir se try karo!💖 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return

    deleted_count = 0
    
    # Delete from old messages collection
    total_stickers_old = messages_collection.count_documents({"type": "sticker"})
    if total_stickers_old > 0:
        stickers_to_delete_old = int(total_stickers_old * (percentage / 100))
        sticker_ids_to_delete = []
        for s in messages_collection.find({"type": "sticker"}).sort("timestamp", 1).limit(stickers_to_delete_old):
            sticker_ids_to_delete.append(s['_id'])
        if sticker_ids_to_delete:
            deleted_count += messages_collection.delete_many({"_id": {"$in": sticker_ids_to_delete}}).deleted_count

    # Delete from owner_taught_responses (if any response is a sticker)
    # Pull only the sticker responses, don't delete the whole pattern if other responses exist
    owner_taught_pull_result = owner_taught_responses_collection.update_many(
        {"responses.type": "sticker"},
        {"$pull": {"responses": {"type": "sticker"}}}
    )
    # Count how many individual stickers were removed across all matching documents
    # This is an approximation as modified_count only tells how many documents were updated.
    # To get exact number of stickers, we'd need to manually count before and after for each document.
    # For now, let's just count modified documents.
    deleted_count += owner_taught_pull_result.modified_count 

    # Delete from conversational_learning (if any response is a sticker)
    conversational_pull_result = conversational_learning_collection.update_many(
        {"responses.type": "sticker"},
        {"$pull": {"responses": {"type": "sticker"}}}
    )
    deleted_count += conversational_pull_result.modified_count


    if deleted_count > 0:
        await send_and_auto_delete_reply(message, text=f"Jaisa hukum mere aaka! 🧞‍♀️ Maine **{percentage}%** stickers ko dhoondh ke delete kar diya. Total **{deleted_count}** stickers removed. Ab woh history ka हिस्सा नहीं रहा! ✨ (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Deleted {deleted_count} stickers based on {percentage}% request. (Code by @asbhaibsr)")
    else:
        await send_and_auto_delete_reply(message, text="Umm, mujhe tumhare is query se koi **sticker** mila hi nahi apne database mein. Ya toh sticker hi nahi hai, ya percentage bahot kam hai! 🤔 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)

    # Store command usage, not for learning
    await store_message(message)
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)


@app.on_message(filters.command("clearearning") & filters.private)
async def clear_earning_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    if message.from_user.id != OWNER_ID:
        await send_and_auto_delete_reply(message, text="Sorry darling! Yeh command sirf mere boss ke liye hai. 🚫 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return

    await reset_monthly_earnings_manual()
    await send_and_auto_delete_reply(message, text="💰 **Earning data successfully cleared!** Ab sab phir se zero se shuru karenge! 😉 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
    logger.info(f"Owner {message.from_user.id} manually triggered earning data reset. (Code by @asbhaibsr)")

    # Store command usage, not for learning
    await store_message(message)
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)

@app.on_message(filters.command("restart") & filters.private)
async def restart_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    if message.from_user.id != OWNER_ID:
        await send_and_auto_delete_reply(message, text="Sorry, darling! Yeh command sirf mere boss ke liye hai. 🚫 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return

    await send_and_auto_delete_reply(message, text="Okay, darling! Main abhi ek chhota sa nap le rahi hoon aur phir wapas aa jaungi, bilkul fresh aur energetic! Thoda wait karna, theek hai? ✨ (System by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
    logger.info("Bot is restarting... (System by @asbhaibsr)")
    await asyncio.sleep(0.5)
    os.execl(sys.executable, sys.executable, *sys.argv)

# --- /chat on/off command ---
@app.on_message(filters.command("chat") & filters.group)
async def toggle_chat_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    if not message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await send_and_auto_delete_reply(message, text="Yeh command sirf groups mein kaam karti hai, darling! 😉", parse_mode=ParseMode.MARKDOWN)
        return

    member = await client.get_chat_member(message.chat.id, message.from_user.id)
    if member.status not in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
        await send_and_auto_delete_reply(message, text="Maaf karna, yeh command sirf group admins hi use kar sakte hain. 🤷‍♀️", parse_mode=ParseMode.MARKDOWN)
        return

    if len(message.command) < 2:
        current_status_doc = group_tracking_collection.find_one({"_id": message.chat.id})
        current_status = current_status_doc.get("bot_enabled", True) if current_status_doc else True
        status_text = "chaalu hai (ON)" if current_status else "band hai (OFF)"
        await send_and_auto_delete_reply(message, text=f"Main abhi is group mein **{status_text}** hoon. Use `/chat on` ya `/chat off` control karne ke liye. (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return

    action = message.command[1].lower()

    if action == "on":
        group_tracking_collection.update_one(
            {"_id": message.chat.id},
            {"$set": {"bot_enabled": True}}
        )
        await send_and_auto_delete_reply(message, text="🚀 Main phir se aa gayi! Ab main is group mein baatein karungi aur seekhungi. 😊", parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Bot enabled in group {message.chat.id} by admin {message.from_user.id}. (Code by @asbhaibsr)")
    elif action == "off":
        group_tracking_collection.update_one(
            {"_id": message.chat.id},
            {"$set": {"bot_enabled": False}}
        )
        await send_and_auto_delete_reply(message, text="😴 Main abhi thodi der ke liye chup ho rahi hoon. Jab meri zaroorat ho, `/chat on` karke bula lena. Bye-bye! 👋", parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Bot disabled in group {message.chat.id} by admin {message.from_user.id}. (Code by @asbhaibsr)")
    else:
        await send_and_auto_delete_reply(message, text="Galat command, darling! `/chat on` ya `/chat off` use karo. 😉", parse_mode=ParseMode.MARKDOWN)

    # Store command usage, not for learning
    await store_message(message)
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)


# --- NEW: Group Moderation Commands ---

@app.on_message(filters.command("linkdel") & filters.group)
async def toggle_linkdel_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    if not await is_admin_or_owner(client, message.chat.id, message.from_user.id):
        await send_and_auto_delete_reply(message, text="माफ़ करना, ये कमांड सिर्फ़ मेरे बॉस (एडमिन) ही यूज़ कर सकते हैं! 🤷‍♀️", parse_mode=ParseMode.MARKDOWN)
        return

    if len(message.command) < 2:
        current_status_doc = group_tracking_collection.find_one({"_id": message.chat.id})
        current_status = current_status_doc.get("linkdel_enabled", False) if current_status_doc else False
        status_text = "चालू है (ON)" if current_status else "बंद है (OFF)"
        await send_and_auto_delete_reply(message, text=f"मेरी 'लिंक जादू' की छड़ी अभी **{status_text}** है. इसे कंट्रोल करने के लिए `/linkdel on` या `/linkdel off` यूज़ करो. 😉", parse_mode=ParseMode.MARKDOWN)
        return

    action = message.command[1].lower()
    if action == "on":
        group_tracking_collection.update_one(
            {"_id": message.chat.id},
            {"$set": {"linkdel_enabled": True}},
            upsert=True
        )
        await send_and_auto_delete_reply(message, text="ही ही ही! 🤭 अब कोई भी शरारती लिंक भेजेगा, तो मैं उसे जादू से गायब कर दूंगी! 🪄 ग्रुप को एकदम साफ़-सुथरा रखना है न! 😉", parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Link deletion enabled in group {message.chat.id} by admin {message.from_user.id}.")
    elif action == "off":
        group_tracking_collection.update_one(
            {"_id": message.chat.id},
            {"$set": {"linkdel_enabled": False}},
            upsert=True
        )
        await send_and_auto_delete_reply(message, text="ठीक है, ठीक है! मैंने अपनी 'लिंक जादू' की छड़ी रख दी है! 😇 अब आप जो चाहे लिंक भेज सकते हैं! पर ध्यान से, ओके?", parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Link deletion disabled in group {message.chat.id} by admin {message.from_user.id}.")
    else:
        await send_and_auto_delete_reply(message, text="उम्म... मुझे समझ नहीं आया! 😕 `/linkdel on` या `/linkdel off` यूज़ करो, प्लीज़! ✨", parse_mode=ParseMode.MARKDOWN)

    # Store command usage, not for learning
    await store_message(message)


@app.on_message(filters.command("biolinkdel") & filters.group)
async def toggle_biolinkdel_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    if not await is_admin_or_owner(client, message.chat.id, message.from_user.id):
        await send_and_auto_delete_reply(message, text="माफ़ करना, ये कमांड सिर्फ़ मेरे बॉस (एडमिन) ही यूज़ कर सकते हैं! 🤷‍♀️", parse_mode=ParseMode.MARKDOWN)
        return

    if len(message.command) < 2:
        current_status_doc = group_tracking_collection.find_one({"_id": message.chat.id})
        current_status = current_status_doc.get("biolinkdel_enabled", False) if current_status_doc else False
        status_text = "चालू है (ON)" if current_status else "बंद है (OFF)"
        await send_and_auto_delete_reply(message, text=f"मेरी 'बायो-लिंक पुलिस' अभी **{status_text}** है. इसे कंट्रोल करने के लिए `/biolinkdel on` या `/biolinkdel off` यूज़ करो.👮‍♀️", parse_mode=ParseMode.MARKDOWN)
        return

    action = message.command[1].lower()
    if action == "on":
        group_tracking_collection.update_one(
            {"_id": message.chat.id},
            {"$set": {"biolinkdel_enabled": True}},
            upsert=True
        )
        await send_and_auto_delete_reply(message, text="हम्म... 😼 अब से जो भी **यूज़र अपनी बायो में `t.me` या `http/https` लिंक रखेगा**, मैं उसके **मैसेज को चुपचाप हटा दूंगी!** (अगर उसे `/biolink` से छूट नहीं मिली है). ग्रुप में कोई मस्ती नहीं! 🤫", parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Biolink deletion enabled in group {message.chat.id} by admin {message.from_user.id}.")
    elif action == "off":
        group_tracking_collection.update_one(
            {"_id": message.chat.id},
            {"$set": {"biolinkdel_enabled": False}},
            upsert=True
        )
        await send_and_auto_delete_reply(message, text="ओके डार्लिंग्स! 😇 अब मैं यूज़र्स की बायो में `t.me` और `http/https` लिंक्स को चेक करना बंद कर रही हूँ! सब फ्री-फ्री! 🎉", parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Biolink deletion disabled in group {message.chat.id} by admin {message.from_user.id}.")
    else:
        await send_and_auto_delete_reply(message, text="उम्म... मुझे समझ नहीं आया! 😕 `/biolinkdel on` या `/biolinkdel off` यूज़ करो, प्लीज़! ✨", parse_mode=ParseMode.MARKDOWN)

    # Store command usage, not for learning
    await store_message(message)


@app.on_message(filters.command("biolink") & filters.group)
async def allow_biolink_user_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    if not await is_admin_or_owner(client, message.chat.id, message.from_user.id):
        await send_and_auto_delete_reply(message, text="माफ़ करना, ये कमांड सिर्फ़ मेरे बॉस (एडमिन) ही यूज़ कर सकते हैं! 🤷‍♀️", parse_mode=ParseMode.MARKDOWN)
        return

    if len(message.command) < 2:
        await send_and_auto_delete_reply(message, text="किस यूज़र को बायो-लिंक की छूट देनी है? मुझे उसकी User ID दो ना, जैसे: `/biolink 123456789` या `/biolink remove 123456789`! 😉", parse_mode=ParseMode.MARKDOWN)
        return

    action_or_user_id = message.command[1].lower()
    target_user_id = None

    if action_or_user_id == "remove" and len(message.command) > 2:
        try:
            target_user_id = int(message.command[2])
            biolink_exceptions_collection.delete_one({"_id": target_user_id})
            await send_and_auto_delete_reply(message, text=f"ओके! ✨ यूज़र `{target_user_id}` को अब बायो में लिंक रखने की छूट नहीं मिलेगी! बाय-बाय परमिशन! 👋", parse_mode=ParseMode.MARKDOWN)
            logger.info(f"Removed user {target_user_id} from biolink exceptions in group {message.chat.id}.")
        except ValueError:
            await send_and_auto_delete_reply(message, text="उम्म, गलत यूज़रआईडी! 🧐 यूज़रआईडी एक नंबर होती है. फिर से ट्राई करो, प्लीज़! 😉", parse_mode=ParseMode.MARKDOWN)
    else:
        try:
            target_user_id = int(action_or_user_id)
            biolink_exceptions_collection.update_one(
                {"_id": target_user_id},
                {"$set": {"allowed_by_admin": True, "added_on": datetime.now(), "credit": "by @asbhaibsr"}},
                upsert=True
            )
            await send_and_auto_delete_reply(message, text=f"याय! 🎉 मैंने यूज़र `{target_user_id}` को स्पेशल परमिशन दे दी है! अब ये **अपनी बायो में `t.me` या `http/https` लिंक्स** रख पाएंगे और उनके मैसेज डिलीट नहीं होंगे! क्यूंकि एडमिन ने बोला, तो बोला!👑", parse_mode=ParseMode.MARKDOWN)
            logger.info(f"Added user {target_user_id} to biolink exceptions in group {message.chat.id}.")
        except ValueError:
            await send_and_auto_delete_reply(message, text="उम्म, गलत यूज़रआईडी! 🧐 यूज़रआईडी एक नंबर होती है. फिर से ट्राई करो, प्लीज़! 😉", parse_mode=ParseMode.MARKDOWN)

    # Store command usage, not for learning
    await store_message(message)


@app.on_message(filters.command("usernamedel") & filters.group)
async def toggle_usernamedel_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    if not await is_admin_or_owner(client, message.chat.id, message.from_user.id):
        await send_and_auto_delete_reply(message, text="माफ़ करना, ये कमांड सिर्फ़ मेरे बॉस (एडमिन) ही यूज़ कर सकते हैं! 🤷‍♀️", parse_mode=ParseMode.MARKDOWN)
        return

    if len(message.command) < 2:
        current_status_doc = group_tracking_collection.find_one({"_id": message.chat.id})
        current_status = current_status_doc.get("usernamedel_enabled", False) if current_status_doc else False
        status_text = "चालू है (ON)" if current_status else "बंद है (OFF)"
        await send_and_auto_delete_reply(message, text=f"मेरी '@' टैग पुलिस अभी **{status_text}** है. इसे कंट्रोल करने के लिए `/usernamedel on` या `/usernamedel off` यूज़ करो.🚨", parse_mode=ParseMode.MARKDOWN)
        return

    action = message.command[1].lower()
    if action == "on":
        group_tracking_collection.update_one(
            {"_id": message.chat.id},
            {"$set": {"usernamedel_enabled": True}},
            upsert=True
        )
        await send_and_auto_delete_reply(message, text="चीं-चीं! 🐦 अब से कोई भी `@` करके किसी को भी परेशान नहीं कर पाएगा! जो करेगा, उसका मैसेज मैं फट से उड़ा दूंगी!💨 मुझे डिस्टर्बेंस पसंद नहीं! 😠", parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Username deletion enabled in group {message.chat.id} by admin {message.from_user.id}.")
    elif action == "off":
        group_tracking_collection.update_one(
            {"_id": message.chat.id},
            {"$set": {"usernamedel_enabled": False}},
            upsert=True
        )
        await send_and_auto_delete_reply(message, text="ठीक है! आज से मेरी @ वाली आंखें बंद! 😴 अब आप जो चाहे @ करो! पर ज़्यादा तंग मत करना किसी को! 🥺", parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Username deletion disabled in group {message.chat.id} by admin {message.from_user.id}.")
    else:
        await send_and_auto_delete_reply(message, text="उम्म... मुझे समझ नहीं आया! 😕 `/usernamedel on` या `/usernamedel off` यूज़ करो, प्लीज़! ✨", parse_mode=ParseMode.MARKDOWN)

    # Store command usage, not for learning
    await store_message(message)

# --- NEW: /clearall command (Owner-Only, with confirmation) ---
@app.on_message(filters.command("clearall") & filters.private)
async def clear_all_dbs_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    if message.from_user.id != OWNER_ID:
        await send_and_auto_delete_reply(message, text="माफ़ करना, ये कमांड सिर्फ़ मेरे बॉस के लिए है। 🚫", parse_mode=ParseMode.MARKDOWN)
        return

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("हाँ, डिलीट करें ⚠️", callback_data='confirm_clearall_dbs'),
                InlineKeyboardButton("नहीं, रहने दें ✅", callback_data='cancel_clearall_dbs')
            ]
        ]
    )

    await send_and_auto_delete_reply(
        message,
        text="⚠️ **चेतावनी:** क्या आप वाकई अपनी सभी MongoDB डेटाबेस (Messages, Buttons, Tracking) का **सारा डेटा** डिलीट करना चाहते हैं?\n\n"
             "यह कार्रवाई **अपरिवर्तनीय (irreversible)** है और आपका सारा डेटा हमेशा के लिए हट जाएगा।\n\n"
             "सोच समझकर चुनें!",
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )
    logger.info(f"Owner {message.from_user.id} initiated /clearall command. Waiting for confirmation.")
    # Store command usage, not for learning
    await store_message(message) 

@app.on_callback_query(filters.regex("^(confirm_clearall_dbs|cancel_clearall_dbs)$"))
async def handle_clearall_dbs_callback(client: Client, callback_query):
    query = callback_query

    # Answer the callback query immediately to remove loading state
    await query.answer()

    if query.from_user.id != OWNER_ID:
        await query.edit_message_text("आप इस कार्रवाई को अधिकृत नहीं हैं।")
        return

    if query.data == 'confirm_clearall_dbs':
        await query.edit_message_text("डेटा डिलीट किया जा रहा है... कृपया प्रतीक्षा करें।⏳")
        try:
            # Drop all collections within their respective databases.
            # This is safer than dropping the entire database which might delete other dbs if the URI is for a cluster.
            # Drop messages_collection
            messages_collection.drop()
            logger.info("messages_collection dropped.")
            
            # Drop buttons_collection
            buttons_collection.drop()
            logger.info("buttons_collection dropped.")

            # Drop all collections in the tracking database
            group_tracking_collection.drop()
            logger.info("group_tracking_collection dropped.")
            user_tracking_collection.drop()
            logger.info("user_tracking_collection dropped.")
            earning_tracking_collection.drop()
            logger.info("earning_tracking_collection dropped.")
            reset_status_collection.drop()
            logger.info("reset_status_collection dropped.")
            biolink_exceptions_collection.drop()
            logger.info("biolink_exceptions_collection dropped.")
            owner_taught_responses_collection.drop() # NEW: Drop owner-taught collection
            logger.info("owner_taught_responses_collection dropped.")
            conversational_learning_collection.drop() # NEW: Drop conversational learning collection
            logger.info("conversational_learning_collection dropped.")


            await query.edit_message_text("✅ **सफलतापूर्वक:** आपकी सभी MongoDB डेटाबेस का सारा डेटा डिलीट कर दिया गया है। बॉट अब बिल्कुल नया हो गया है! ✨", parse_mode=ParseMode.MARKDOWN)
            logger.info(f"Owner {query.from_user.id} confirmed and successfully cleared all MongoDB data.")
        except Exception as e:
            await query.edit_message_text(f"❌ **त्रुटि:** डेटा डिलीट करने में समस्या आई: {e}\n\nकृपया लॉग्स चेक करें।", parse_mode=ParseMode.MARKDOWN)
            logger.error(f"Error during /clearall confirmation and deletion: {e}")
    elif query.data == 'cancel_clearall_dbs':
        await query.edit_message_text("कार्यवाही रद्द कर दी गई है। आपका डेटा सुरक्षित है। ✅", parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Owner {query.from_user.id} cancelled /clearall operation.")

# --- NEW: /clearmydata command ---
@app.on_message(filters.command("clearmydata"))
async def clear_my_data_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    target_user_id = None
    if len(message.command) > 1 and message.from_user.id == OWNER_ID:
        try:
            target_user_id = int(message.command[1])
            # Ensure owner is not trying to delete bot's own data or system data
            if target_user_id == client.me.id:
                await send_and_auto_delete_reply(message, text="आप मेरे डेटा को डिलीट नहीं कर सकते, बॉस! 😅", parse_mode=ParseMode.MARKDOWN)
                return
        except ValueError:
            await send_and_auto_delete_reply(message, text="गलत User ID फ़ॉर्मेट। कृपया एक वैध संख्यात्मक ID दें।", parse_mode=ParseMode.MARKDOWN)
            return
    elif len(message.command) > 1 and message.from_user.id != OWNER_ID:
        await send_and_auto_delete_reply(message, text="यह कमांड ऐसे उपयोग करने के लिए आप अधिकृत नहीं हैं। यह सुविधा केवल मेरे बॉस के लिए है।", parse_mode=ParseMode.MARKDOWN)
        return
    else:
        target_user_id = message.from_user.id

    if not target_user_id:
        await send_and_auto_delete_reply(message, text="मुझे पता नहीं चल रहा कि किसका डेटा डिलीet करना है। 😕", parse_mode=ParseMode.MARKDOWN)
        return

    try:
        deleted_messages_count = messages_collection.delete_many({"user_id": target_user_id}).deleted_count
        deleted_earning_data = earning_tracking_collection.delete_one({"_id": target_user_id}).deleted_count # Also clear earning data for that user
        
        # NEW: Also clear user's entries from learning collections if they contributed
        owner_taught_responses_collection.update_many(
            {"responses.user_id": target_user_id},
            {"$pull": {"responses": {"user_id": target_user_id}}}
        )
        # If a trigger was taught by this user and has no other responses left, delete the trigger
        owner_taught_responses_collection.delete_many({"responses": []})

        conversational_learning_collection.update_many(
            {"responses.user_id": target_user_id},
            {"$pull": {"responses": {"user_id": target_user_id}}}
        )
        # If a trigger was taught by this user and has no other responses left, delete the trigger
        conversational_learning_collection.delete_many({"responses": []})


        if deleted_messages_count > 0 or deleted_earning_data > 0:
            if target_user_id == message.from_user.id:
                await send_and_auto_delete_reply(message, text=f"वाह! ✨ मैंने आपकी `{deleted_messages_count}` बातचीत के मैसेज और अर्निंग डेटा डिलीट कर दिए हैं। अब आप बिल्कुल फ्रेश हो! 😊", parse_mode=ParseMode.MARKDOWN)
                logger.info(f"User {target_user_id} successfully cleared their data.")
            else: # Owner deleting another user's data
                await send_and_auto_delete_reply(message, text=f"बॉस का ऑर्डर! 👑 मैंने यूजर `{target_user_id}` के `{deleted_messages_count}` बातचीत के मैसेज और अर्निंग डेटा डिलीट कर दिए हैं। 😉", parse_mode=ParseMode.MARKDOWN)
                logger.info(f"Owner {message.from_user.id} cleared data for user {target_user_id}.")
        else:
            if target_user_id == message.from_user.id:
                await send_and_auto_delete_reply(message, text="आपके पास कोई डेटा स्टोर नहीं है जिसे डिलीट किया जा सके। मेरा डेटाबेस तो एकदम खाली है आपके लिए! 🤷‍♀️", parse_mode=ParseMode.MARKDOWN)
            else:
                await send_and_auto_delete_reply(message, text=f"यूजर `{target_user_id}` का कोई डेटा नहीं मिला जिसे डिलीट किया जा सके।", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await send_and_auto_delete_reply(message, text=f"डेटा डिलीट करने में कुछ गड़बड़ हो गई: {e}. ओह नो! 😱", parse_mode=ParseMode.MARKDOWN)
        logger.error(f"Error clearing data for user {target_user_id}: {e}")
    # Store command usage, not for learning
    await store_message(message)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)


# --- New chat members and left chat members ---
@app.on_message(filters.new_chat_members)
async def new_member_handler(client: Client, message: Message):
    logger.info(f"New chat members detected in chat {message.chat.id}. Bot ID: {client.me.id}. (Event handled by @asbhaibsr)")

    for member in message.new_chat_members:
        logger.info(f"Processing new member: {member.id} ({member.first_name}) in chat {message.chat.id}. Is bot: {member.is_bot}. (Event handled by @asbhaibsr)")
        
        # Scenario 1: The bot itself joins a new group
        if member.id == client.me.id:
            if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
                logger.info(f"DEBUG: Bot {client.me.id} detected as new member in group {message.chat.id}. Calling update_group_info.")
                await update_group_info(message.chat.id, message.chat.title, message.chat.username)
                logger.info(f"Bot joined new group: {message.chat.title} ({message.chat.id}). (Event handled by @asbhaibsr)")

                group_title = message.chat.title if message.chat.title else f"Unknown Group (ID: {message.chat.id})"
                added_by_user = message.from_user.first_name if message.from_user else "Unknown User"
                notification_message = (
                    f"🥳 **New Group Alert!**\n"
                    f"Bot ko ek naye group mein add kiya gaya hai!\n\n"
                    f"**Group Name:** {group_title}\n"
                    f"**Group ID:** `{message.chat.id}`\n"
                    f"**Added By:** {added_by_user} ({message.from_user.id if message.from_user else 'N/A'})\n"
                    f"**Added On:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    f"**Code By:** @asbhaibsr\n**Updates:** @asbhai_bsr\n**Support:** @aschat_group"
                )
                try:
                    await client.send_message(chat_id=OWNER_ID, text=notification_message, parse_mode=ParseMode.MARKDOWN)
                    logger.info(f"Owner notified about new group: {group_title}. (Notification by @asbhaibsr)")
                except Exception as e:
                    logger.error(f"Could not notify owner about new group {group_title}: {e}. (Notification error by @asbhaibsr)")
            return # Exit function if the member is the bot itself

        # Scenario 2: A new (non-bot) user starts the bot in private
        # Per user's clarification: ONLY notify owner if a NEW user starts the bot in private,
        # NOT when a new user joins a group where the bot is present.
        if not member.is_bot and message.chat.type == ChatType.PRIVATE and member.id == message.from_user.id:
            user_exists = user_tracking_collection.find_one({"_id": member.id})
            if not user_exists: # Only send notification if it's genuinely a new user to the bot's private chat
                user_name = member.first_name if member.first_name else "Naya User"
                user_username = f"@{member.username}" if member.username else "N/A"
                notification_message = (
                    f"✨ **New User Alert! (Private Chat)**\n"
                    f"Ek naye user ne bot ko private mein start kiya hai.\n\n"
                    f"**User Name:** {user_name}\n"
                    f"**User ID:** `{member.id}`\n"
                    f"**Username:** {user_username}\n"
                    f"**Started On:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    f"**Code By:** @asbhaibsr\n**Updates:** @asbhai_bsr\n**Support:** @aschat_group"
                )
                try:
                    await client.send_message(chat_id=OWNER_ID, text=notification_message, parse_mode=ParseMode.MARKDOWN)
                    logger.info(f"Owner notified about new private user: {user_name}. (Notification by @asbhaibsr)")
                except Exception as e:
                    logger.error(f"Could not notify owner about new private user {user_name}: {e}. (Notification error by @asbhaibsr)")

    # Store command usage, not for learning
    await store_message(message)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)


@app.on_message(filters.left_chat_member)
async def left_member_handler(client: Client, message: Message):
    logger.info(f"Left chat member detected in chat {message.chat.id}. Left member ID: {message.left_chat_member.id}. Bot ID: {client.me.id}. (Event handled by @asbhaibsr)")

    if message.left_chat_member and message.left_chat_member.id == client.me.id:
        if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
            group_tracking_collection.delete_one({"_id": message.chat.id})
            messages_collection.delete_many({"chat_id": message.chat.id})
            # NEW: Clear learning data associated with this group
            owner_taught_responses_collection.delete_many({"responses.chat_id": message.chat.id})
            conversational_learning_collection.delete_many({"responses.chat_id": message.chat.id})

            earning_tracking_collection.update_many(
                {}, # All users
                {"$pull": {"last_active_group_id": message.chat.id}} # If it was tracking last group specifically
            )

            logger.info(f"Bot left group: {message.chat.title} ({message.chat.id}). Data cleared. (Code by @asbhaibsr)")
            group_title = message.chat.title if message.chat.title else f"Unknown Group (ID: {message.chat.id})"
            left_by_user = message.from_user.first_name if message.from_user else "Unknown User"
            notification_message = (
                f"💔 **Group Left Alert!**\n"
                f"Bot ko ek group se remove kiya gaya hai ya woh khud leave kar gaya.\n\n"
                f"**Group Name:** {group_title}\n"
                f"**Group ID:** `{message.chat.id}`\n"
                f"**Action By:** {left_by_user} ({message.from_user.id if message.from_user else 'N/A'})\n"
                f"**Left On:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"**Code By:** @asbhaibsr\n**Updates:** @asbhai_bsr\n**Support:** @aschat_group"
            )
            try:
                await client.send_message(chat_id=OWNER_ID, text=notification_message, parse_mode=ParseMode.MARKDOWN)
                logger.info(f"Owner notified about bot leaving group: {group_title}. (Notification by @asbhaibsr)")
            except Exception as e:
                logger.error(f"Could not notify owner about bot leaving group {group_title}: {e}. (Notification error by @asbhaibsr)")
            return

    # Store command usage, not for learning
    await store_message(message)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)

# --- Game Logic Functions ---
async def game_timeout_checker(chat_id: int):
    while chat_id in game_states:
        game_info = game_states.get(chat_id)
        if game_info and (time.time() - game_info['last_activity_time']) > GAME_ACTIVE_TIMEOUT:
            logger.info(f"Game in chat {chat_id} timed out due to inactivity.")
            await app.send_message(chat_id, 
                                   f"⌛ खेल ख़त्म! किसी ने 1 मिनट तक जवाब नहीं दिया. सही जवाब था: **{game_info['target_number']}**\n\n"
                                   "अब आप चैट जारी रख सकते हैं. 😊")
            del game_states[chat_id]
            break # Exit the loop as game is over
        await asyncio.sleep(5) # Check every 5 seconds

@app.on_message(filters.regex("game started", re.IGNORECASE) & filters.group)
async def start_game(client: Client, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "खिलाड़ी"

    if chat_id in game_states:
        await message.reply_text("अरे! एक खेल पहले से ही चल रहा है. उसे ख़त्म होने दो, फिर नया शुरू करेंगे! 😉")
        return
    
    # Initialize game state
    target_number = random.randint(1, 100)
    game_states[chat_id] = {
        'target_number': target_number,
        'player_id': user_id,
        'attempts': 0,
        'last_activity_time': time.time(),
        'game_task': None # To store the task for cancellation if needed
    }
    
    await message.reply_text(
        f"🎮 **खेल शुरू!** 🎮\n\n"
        f"नमस्ते {user_name}! मैंने 1 से 100 के बीच एक संख्या सोची है. इसे 60 सेकंड के भीतर अनुमान लगाओ! 👇\n\n"
        "संकेत: आप `guess 50` जैसा कुछ भेज सकते हैं."
    )
    logger.info(f"Game started in chat {chat_id} by user {user_id}. Target: {target_number}")

    # Start the timeout checker for this game
    game_states[chat_id]['game_task'] = asyncio.create_task(game_timeout_checker(chat_id))

@app.on_message(filters.text & filters.group & -filters.command)
async def handle_game_and_chat(client: Client, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    # Check if a game is active in this chat
    if chat_id in game_states:
        game_info = game_states[chat_id]

        # Only the player can play
        if user_id != game_info['player_id']:
            logger.info(f"Ignoring non-player message in active game chat {chat_id} from user {user_id}.")
            return # Ignore messages from non-players during an active game

        # Process game input
        try:
            guess = int(message.text)
            game_info['attempts'] += 1
            game_info['last_activity_time'] = time.time() # Reset timeout on activity

            if guess == game_info['target_number']:
                await message.reply_text(
                    f"🎉 **वाह!** आपने सही अनुमान लगाया, **{message.from_user.first_name}**! "
                    f"सही संख्या थी **{game_info['target_number']}** और आपने **{game_info['attempts']}** कोशिशों में जीत हासिल की!\n\n"
                    "खेल ख़त्म! अब आप चैट जारी रख सकते हैं. 😊"
                )
                logger.info(f"Game in chat {chat_id} won by user {user_id} in {game_info['attempts']} attempts.")
                if game_info['game_task']:
                    game_info['game_task'].cancel() # Cancel the timeout task
                del game_states[chat_id] # End the game
            elif guess < game_info['target_number']:
                await message.reply_text(f"थोड़ा और ऊपर! 🤔 आपका अनुमान `{guess}` है. कोशिश करते रहो! 🎯")
            else:
                await message.reply_text(f"थोड़ा नीचे! 👇 आपका अनुमान `{guess}` है. कोशिश करते रहो! 🎯")

        except ValueError:
            # If it's not a valid number guess, and a game is active, just ignore it or provide a hint
            if message.text and "game" in message.text.lower() or "guess" in message.text.lower():
                 await message.reply_text("कृपया एक संख्या का अनुमान लगाएँ. जैसे: `50` या `guess 75`")
            logger.debug(f"Non-numeric message '{message.text}' during active game in chat {chat_id}. Ignoring.")
        
        return # Important: Stop further processing, bot is in game mode

    # If no game is active, proceed with regular message handling
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

async def delete_after_delay_for_message(message_obj: Message, delay: int):
    """Utility to delete a specific message after a delay."""
    await asyncio.sleep(delay)
    try:
        await message_obj.delete()
    except Exception as e:
        logger.warning(f"Failed to delete message {message_obj.id} in chat {message_obj.chat.id}: {e}")


# --- Main entry point ---
if __name__ == "__main__":
    logger.info("Starting Flask health check server in a separate thread...")
    flask_thread = threading.Thread(target=run_flask_app)
    flask_thread.start()

    logger.info("Starting Pyrogram bot...")

    app.run()

    # End of bot code. Thank you for using! Made with ❤️ by @asbhaibsr
