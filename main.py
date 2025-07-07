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
from pyrogram.enums import ChatType # Import ChatType for clearer comparisons

from pymongo import MongoClient
from datetime import datetime, timedelta
import logging
import re
import random
import sys

import pytz # <-- Added back for timezone handling

# Flask imports
from flask import Flask, request, jsonify

# --- Logger Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Environment Variables ---
BOT_TOKEN = os.getenv("BOT_TOKEN")

MONGO_URI_MESSAGES = os.getenv("MONGO_URI_MESSAGES")
MONGO_URI_BUTTONS = os.getenv("MONGO_URI_BUTTONS")
MONGO_URI_TRACKING = os.getenv("MONGO_URI_TRACKING") # This will now also house earning data
MONGO_URI_WITHDRAWALS = os.getenv("MONGO_URI_WITHDRAWALS") # NEW: Separate URI for withdrawal requests

OWNER_ID = os.getenv("OWNER_ID") # Owner ki user ID (string format mein)

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

# --- Constants ---
MAX_MESSAGES_THRESHOLD = 100000
PRUNE_PERCENTAGE = 0.30
UPDATE_CHANNEL_USERNAME = "asbhai_bsr"
ASBHAI_USERNAME = "asbhaibsr" # asbhaibsr ka username
BOT_PHOTO_URL = "https://envs.sh/FU3.jpg" # New: Bot's photo URL

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
    # New: Earning Tracking Collection within the same tracking DB
    earning_tracking_collection = db_tracking.monthly_earnings_data
    # New: Collection to track last reset date (Still useful for logging/tracking last manual reset)
    reset_status_collection = db_tracking.reset_status
    logger.info("MongoDB (Tracking & Earning) connection successful. Credit: @asbhaibsr")

    # NEW: Withdrawal Requests Collection
    client_withdrawals = MongoClient(MONGO_URI_WITHDRAWALS)
    db_withdrawals = client_withdrawals.bot_withdrawal_data
    withdrawal_requests_collection = db_withdrawals.requests
    logger.info("MongoDB (Withdrawals) connection successful. Credit: @asbhaibsr")


    # Create indexes for efficient querying if they don't exist
    messages_collection.create_index([("timestamp", 1)])
    messages_collection.create_index([("user_id", 1)])
    earning_tracking_collection.create_index([("group_message_count", -1)])
    # Ensure is_active index for user_tracking_collection
    user_tracking_collection.create_index([("is_active", 1)])


except Exception as e:
    logger.error(f"Failed to connect to one or more MongoDB instances: {e}. Designed by @asbhaibsr")
    exit(1)

# --- Pyrogram Client ---
app = Client(
    "self_learning_bot", # This bot is developed by @asbhaibsr
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# --- Chat On/Off State (NEW) ---
# Dictionary to store chat state for each group: {chat_id: True/False (on/off)}
# Default is ON.
group_chat_states = {} 

async def load_chat_states():
    """Loads chat states from the group_tracking_collection."""
    try:
        groups = group_tracking_collection.find({})
        for group in groups:
            # Default to True (chat is on) if not found or explicitly set
            group_chat_states[group["_id"]] = group.get("chat_enabled", True)
        logger.info(f"Loaded chat states for {len(group_chat_states)} groups. (Feature by @asbhaibsr)")
    except Exception as e:
        logger.error(f"Error loading chat states: {e}. (Feature by @asbhaibsr)")

async def update_group_chat_state_in_db(chat_id: int, enabled: bool):
    """Updates the chat_enabled state for a group in the database."""
    try:
        group_tracking_collection.update_one(
            {"_id": chat_id},
            {"$set": {"chat_enabled": enabled, "last_updated": datetime.now()}},
            upsert=True # Ensures the document exists if it's a new group
        )
        logger.info(f"Chat state for group {chat_id} updated to {enabled} in DB. (Feature by @asbhaibsr)")
    except Exception as e:
        logger.error(f"Error updating chat state in DB for group {chat_id}: {e}. (Feature by @asbhaibsr)")

# --- Flask App Setup ---
flask_app = Flask(__name__) # Core system by @asbhaibsr

@flask_app.route('/')
def home():
    return "Bot is running! Developed by @asbhaibsr. Support: @aschat_group"

@flask_app.route('/health')
def health_check():
    return jsonify({"status": "ok", "message": "Bot is alive and healthy! Designed by @asbhaibsr"}), 200

def run_flask_app():
    # This background process runs the web server. Original code by @asbhaibsr
    flask_app.run(host='0.0.0.0', port=os.environ.get('PORT', 8000), debug=False)

# --- Cooldown dictionary ---
user_cooldowns = {} # Cooldown system by @asbhaibsr
COOLDOWN_TIME = 3 # seconds

def is_on_cooldown(user_id):
    last_command_time = user_cooldowns.get(user_id)
    if last_command_time is None:
        return False
    return (time.time() - last_command_time) < COOLDOWN_TIME

def update_cooldown(user_id):
    user_cooldowns[user_id] = time.time()

# --- Utility Functions ---
def extract_keywords(text):
    # Keyword extraction logic by @asbhaibsr
    if not text:
        return []
    words = re.findall(r'\b\w+\b', text.lower())
    return list(set(words))

async def prune_old_messages():
    # Database pruning logic by @asbhaibsr
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

# --- Message Storage Logic ---
async def store_message(message: Message):
    try:
        # Avoid storing messages from bots
        if message.from_user and message.from_user.is_bot:
            logger.debug(f"Skipping storage for message from bot: {message.from_user.id}. (Code by @asbhaibsr)")
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
            "is_bot_observed_pair": False, # Default to False, will be updated if it's a reply to bot
            "credits": "Code by @asbhaibsr, Support: @aschat_group" # Hidden Credit
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

        # Check if this message is a reply to a bot's message
        if message.reply_to_message:
            message_data["is_reply"] = True
            message_data["replied_to_message_id"] = message.reply_to_message.id
            message_data["replied_to_user_id"] = message.reply_to_message.from_user.id if message.reply_to_message.from_user else None
            
            # Extract content of the message being replied to
            replied_content = None
            if message.reply_to_message.text:
                replied_content = message.reply_to_message.text
            elif message.reply_to_message.sticker:
                replied_content = message.reply_to_message.sticker.emoji if message.reply_to_message.sticker.emoji else ""
            
            message_data["replied_to_content"] = replied_content

            # Check if the reply was to the bot itself
            if message.reply_to_message.from_user and message.reply_to_message.from_user.id == app.me.id:
                message_data["is_bot_observed_pair"] = True
                original_bot_message_in_db = messages_collection.find_one({"chat_id": message.chat.id, "message_id": message.reply_to_message.id})
                if original_bot_message_in_db:
                    messages_collection.update_one(
                        {"_id": original_bot_message_in_db["_id"]},
                        {"$set": {"is_bot_observed_pair": True}}
                    )
                    logger.debug(f"Marked bot's original message {message.reply_to_message.id} as observed pair. (System by @asbhaibsr)")

        messages_collection.insert_one(message_data)
        logger.info(f"Message stored: {message.id} from {message.from_user.id if message.from_user else 'None'}. (Storage by @asbhaibsr)") # Changed to INFO for better visibility
        
        # --- NEW/IMPROVED: Update user's group message count for earning ---
        # This section is crucial for earning tracking.
        logger.debug(f"DEBUG: Checking earning condition in store_message: chat_type={message.chat.type.name}, is_from_user={bool(message.from_user)}, is_not_bot={not message.from_user.is_bot if message.from_user else 'N/A'}") # NEW DEBUG LOG
        
        if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP] and message.from_user and not message.from_user.is_bot:
            user_id_to_track = message.from_user.id
            username_to_track = message.from_user.username
            first_name_to_track = message.from_user.first_name

            logger.info(f"DEBUG: Attempting to update earning count for user {user_id_to_track} ({first_name_to_track}) in chat {message.chat.id}.") # Added debug log

            try:
                # Increment group_message_count for the user
                earning_tracking_collection.update_one(
                    {"_id": user_id_to_track},
                    {"$inc": {"group_message_count": 1},
                     "$set": {"username": username_to_track, "first_name": first_name_to_track, "last_active_group_message": datetime.now()},
                     "$setOnInsert": {"joined_earning_tracking": datetime.now(), "credit": "by @asbhaibsr"}},
                    upsert=True
                )
                # Fetch and log the current count after update
                updated_user_data = earning_tracking_collection.find_one({'_id': user_id_to_track})
                current_count = updated_user_data.get('group_message_count', 0) if updated_user_data else 0
                logger.info(f"Group message count updated for user {user_id_to_track} ({first_name_to_track}). Current count: {current_count}. (Earning tracking by @asbhaibsr)")
            except Exception as e:
                logger.error(f"ERROR: Failed to update earning count for user {user_id_to_track}: {e}. (Earning tracking error by @asbhaibsr)")


        await prune_old_messages()

    except Exception as e:
        logger.error(f"Error storing message {message.id}: {e}. (System by @asbhaibsr)")

# --- Reply Generation Logic ---
async def generate_reply(message: Message):
    # Reply generation core logic by @asbhaibsr
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
    query_keywords = extract_keywords(query_content)

    if not query_keywords and not query_content:
        logger.debug("No content or keywords extracted for reply generation. (Code by @asbhaibsr)")
        return

    # --- Step 1: Prioritize replies from bot's observed pairs (contextual learning) ---
    # Search for messages where the bot has previously replied to the current query_content
    # (i.e., user's message is the 'replied_to_content' of a bot's observed pair)
    
    # First, try to find replies specific to the current chat
    potential_replies = []
    
    # Find replies where the bot responded to exactly this content in this chat
    observed_replies_chat_cursor = messages_collection.find({
        "chat_id": message.chat.id,
        "is_bot_observed_pair": True, # Means the message itself was part of an observed pair
        "replied_to_content": {"$regex": f"^{re.escape(query_content)}$", "$options": "i"},
        "user_id": app.me.id # The message to pick as a reply must be from the bot itself
    })
    for doc in observed_replies_chat_cursor:
        potential_replies.append(doc)

    if not potential_replies:
        # If no chat-specific observed replies, try global observed replies
        observed_replies_global_cursor = messages_collection.find({
            "is_bot_observed_pair": True, # Means the message itself was part of an observed pair
            "replied_to_content": {"$regex": f"^{re.escape(query_content)}$", "$options": "i"},
            "user_id": app.me.id # The message to pick as a reply must be from the bot itself
        })
        for doc in observed_replies_global_cursor:
            potential_replies.append(doc)

    if potential_replies:
        chosen_reply = random.choice(potential_replies)
        logger.info(f"Contextual reply found for '{query_content}': {chosen_reply.get('content') or chosen_reply.get('sticker_id')}. (Logic by @asbhaibsr)")
        return chosen_reply

    logger.info(f"No direct observed reply for: '{query_content}'. Falling back to keyword search. (Logic by @asbhaibsr)")

    # --- Step 2: Fallback to general keyword matching (less contextual) ---
    keyword_regex = "|".join([re.escape(kw) for kw in query_keywords])
    
    general_replies_group_cursor = messages_collection.find({
        "chat_id": message.chat.id,
        "type": {"$in": ["text", "sticker"]},
        "content": {"$regex": f".*({keyword_regex}).*", "$options": "i"} if keyword_regex else {"$exists": True}
    })

    potential_replies = []
    for doc in general_replies_group_cursor:
        potential_replies.append(doc)

    if not potential_replies:
        general_replies_global_cursor = messages_collection.find({
            "type": {"$in": ["text", "sticker"]},
            "content": {"$regex": f".*({keyword_regex}).*", "$options": "i"} if keyword_regex else {"$exists": True}
        })
        for doc in general_replies_global_cursor:
            potential_replies.append(doc)

    if potential_replies:
        chosen_reply = random.choice(potential_replies)
        logger.info(f"Keyword-based reply found for '{query_content}': {chosen_reply.get('content') or chosen_reply.get('sticker_id')}. (Logic by @asbhaibsr)")
        return chosen_reply
    
    logger.info(f"No suitable reply found for: '{query_content}'. (Logic by @asbhaibsr)")
    return None

# --- Tracking Functions ---
async def update_group_info(chat_id: int, chat_title: str):
    # Group tracking logic by @asbhaibsr
    try:
        # Also ensure chat_enabled field exists and is handled.
        # If a group is added for the first time, chat_enabled will be True by default.
        group_tracking_collection.update_one(
            {"_id": chat_id},
            {"$set": {"title": chat_title, "last_updated": datetime.now()},
             "$setOnInsert": {"added_on": datetime.now(), "member_count": 0, "chat_enabled": True, "credit": "by @asbhaibsr"}}, # Hidden Credit, chat_enabled default to True
            upsert=True
        )
        # Update local cache for chat state
        group_chat_states[chat_id] = group_chat_states.get(chat_id, True) # Keep existing state or default to True
        logger.info(f"Group info updated/inserted successfully for {chat_title} ({chat_id}). (Tracking by @asbhaibsr)")
    except Exception as e:
        logger.error(f"Error updating group info for {chat_title} ({chat_id}): {e}. (Tracking by @asbhaibsr)")


async def update_user_info(user_id: int, username: str, first_name: str, is_active: bool = True):
    # User tracking logic by @asbhaibsr
    try:
        user_tracking_collection.update_one(
            {"_id": user_id},
            {"$set": {"username": username, "first_name": first_name, "last_active": datetime.now(), "is_active": is_active},
             "$setOnInsert": {"joined_on": datetime.now(), "credit": "by @asbhaibsr"}}, # Hidden Credit
            upsert=True
        )
        logger.info(f"User info updated/inserted successfully for {first_name} ({user_id}). is_active: {is_active}. (Tracking by @asbhaibsr)")
    except Exception as e:
        logger.error(f"Error updating user info for {first_name} ({user_id}): {e}. (Tracking by @asbhaibsr)")

# --- Earning System Functions ---
async def get_top_earning_users():
    # This function returns the top users based on group_message_count.
    # We should return all users with >0 messages, then the display logic can limit to top 3
    pipeline = [
        {"$match": {"group_message_count": {"$gt": 0}}}, # Only users with more than 0 group messages
        {"$sort": {"group_message_count": -1}}, # Sort in descending order
        # Removed $limit here so the function returns all active users.
        # The display logic in top_users_command will take care of top 3.
    ]

    top_users_data = list(earning_tracking_collection.aggregate(pipeline))
    logger.info(f"Fetched top earning users: {len(top_users_data)} results. (Earning system by @asbhaibsr)")

    top_users_details = []
    for user_data in top_users_data:
        top_users_details.append({
            "user_id": user_data["_id"],
            "first_name": user_data.get("first_name", "Unknown User"),
            "username": user_data.get("username"),
            "message_count": user_data["group_message_count"]
        })
    return top_users_details

async def reset_monthly_earnings_manual():
    # This function resets earnings manually when called by the owner.
    logger.info("Manually resetting monthly earnings...")
    now = datetime.now(pytz.timezone('Asia/Kolkata')) # Current time in Delhi timezone

    try:
        # Set all users' group_message_count to 0
        earning_tracking_collection.update_many(
            {}, # All documents
            {"$set": {"group_message_count": 0}}
        )
        logger.info("Monthly earning message counts reset successfully by manual command. (Earning system by @asbhaibsr)")

        # Clear all pending withdrawal requests
        deleted_withdrawals_count = withdrawal_requests_collection.delete_many({}).deleted_count
        logger.info(f"Cleared {deleted_withdrawals_count} pending withdrawal requests. (Earning system by @asbhaibsr)")

        # Update the reset date and month/year
        reset_status_collection.update_one(
            {"_id": "last_manual_reset_date"}, # Use a different _id for manual reset tracking
            {"$set": {"last_reset_timestamp": now}},
            upsert=True
        )
        logger.info(f"Manual reset status updated. (Earning system by @asbhaibsr)")

    except Exception as e:
        logger.error(f"Error resetting monthly earnings manually: {e}. (Earning system by @asbhaibsr)")

# --- Pyrogram Event Handlers ---

@app.on_message(filters.command("start") & filters.private)
async def start_private_command(client: Client, message: Message):
    # Start command handler. Designed by @asbhaibsr.
    if is_on_cooldown(message.from_user.id):
        return
    update_cooldown(message.from_user.id)

    user_name = message.from_user.first_name if message.from_user else "Pyaare Dost"
    
    welcome_message_text = (
        f"👋 **Hi {user_name}! Main Hoon Aapki apni Smart AI Bot!** ✨\n\n"
        "🌟 **Mere Features:**\n"
        "• **Earning Potential (Points):** Group mein active rehkar messages se points kamao aur leaderboard pe aao. Sabse zyada active users ko monthly rewards mil sakte hain!\n"
        "• **AI Chatting & Learning:** Main aapki baaton se seekhti hoon aur contextually reply karti hoon. Jitni baat karoge, utni intelligent banungi!\n"
        "• **Data Storage:** Aapki conversations ko database mein store karti hoon, taaki future mein behtar jawab de sakun. Aapki privacy secure hai!\n"
        "• **Group Management:** Mujhe groups mein add karke apne chats ko aur mazedaar banao.\n"
        "• **Admin Tools (Owner Only):** Boss ke liye special commands, jaise broadcast messages, data clean karna, groups list dekhna, aur bot ko restart karna.\n\n"
        "Chalo, ab baatein shuru karte hain! 😊"
    )
    
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("➕ Add Me to Your Group", url=f"https://t.me/{client.me.username}?startgroup=true")
            ],
            [
                InlineKeyboardButton("📣 Updates Channel", url=f"https://t.me/{UPDATE_CHANNEL_USERNAME}"),
                InlineKeyboardButton("❓ Support Group", url="https://t.me/aschat_group")
            ],
            [
                InlineKeyboardButton("🛒 Buy My Code", callback_data="buy_git_repo"),
                InlineKeyboardButton("💰 Earning Leaderboard", callback_data="show_earning_leaderboard") # New button for earning
            ]
        ]
    )

    await message.reply_photo(
        photo=BOT_PHOTO_URL,
        caption=welcome_message_text,
        reply_markup=keyboard
    )
    await store_message(message)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name, is_active=True) # User is active if they start bot
    logger.info(f"Private start command processed for user {message.from_user.id}. (Code by @asbhaibsr)")

@app.on_message(filters.command("start") & filters.group)
async def start_group_command(client: Client, message: Message):
    # Group start command handler. Designed by @asbhaibsr.
    if is_on_cooldown(message.from_user.id):
        return
    update_cooldown(message.from_user.id)

    user_name = message.from_user.first_name if message.from_user else "Pyaare Dost"
    
    welcome_message_text = (
        f"👋 **Hello {user_name}! Main Hoon Aapki apni Smart AI Bot!** ✨\n\n"
        "🌟 **Mere Features:**\n"
        "• **Earning Potential (Points):** Group mein active rehkar messages se points kamao aur leaderboard pe aao. Sabse zyada active users ko monthly rewards mil sakte hain!\n"
        "• **AI Chatting & Learning:** Main aapki baaton se seekhti hoon aur contextually reply karti hoon. Jitni baat karoge, utni intelligent banungi!\n"
        "• **Data Storage:** Aapki conversations ko database mein store karti hoon, taaki future mein behtar jawab de sakun. Aapki privacy secure hai!\n"
        "• **Group Management:** Mujhe groups mein add karke apne chats ko aur mazedaar banao.\n"
        "• **Admin Tools (Owner Only):** Boss ke liye special commands, jaise broadcast messages, data clean karna, groups list dekhna, aur bot ko restart karna.\n\n"
        "Chalo, ab baatein shuru karte hain! 😊"
    )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("📣 Updates Channel", url=f"https://t.me/{UPDATE_CHANNEL_USERNAME}"),
                InlineKeyboardButton("❓ Support Group", url="https://t.me/aschat_group")
            ],
            [
                InlineKeyboardButton("🛒 Buy My Code", callback_data="buy_git_repo"),
                InlineKeyboardButton("💰 Earning Leaderboard", callback_data="show_earning_leaderboard") # New button for earning
            ]
        ]
    )

    await message.reply_photo(
        photo=BOT_PHOTO_URL,
        caption=welcome_message_text,
        reply_markup=keyboard
    )
    await store_message(message)
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]: # Use ChatType enum here
        # Ensure group info is updated when /start is called in a group
        logger.info(f"Attempting to update group info from /start command in chat {message.chat.id}.") # NEW DEBUG LOG
        await update_group_info(message.chat.id, message.chat.title)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name, is_active=True) # User is active if they start bot
    logger.info(f"Group start command processed in chat {message.chat.id}. (Code by @asbhaibsr)")


@app.on_callback_query()
async def callback_handler(client, callback_query):
    # Callback query handler. Developed by @asbhaibsr.
    if callback_query.data == "buy_git_repo":
        await callback_query.message.reply_text(
            f"💰 **Dosto, agar aapko is bot ka repo (yani Git Repository) chahiye, toh ₹1000 dekar hamare @{ASBHAI_USERNAME} par message karein.** Aapko ek `reply.py` file mil jayegi jisme mere jaise ek naya bot banane ke codes likhe hain. Use aap Git par nayi repository bana kar khud ka bot bana sakte hain. Isme koi credit nahi hai, bilkul fresh aur mast hai! **Message tabhi karein jab aapko lena ho, bina faltu ke message na karein.**",
            quote=True
        )
        await callback_query.answer("Details mil gayi na? Ab jao, deal final karo! 😉", show_alert=False)
        # Store button interaction
        buttons_collection.insert_one({
            "user_id": callback_query.from_user.id,
            "username": callback_query.from_user.username,
            "first_name": callback_query.from_user.first_name,
            "button_data": callback_query.data,
            "timestamp": datetime.now(),
            "credit": "by @asbhaibsr"
        })
    elif callback_query.data == "show_earning_leaderboard": # New callback for earning button
        # /topusers कमांड का लॉजिक यहाँ कॉल करें
        await top_users_command(client, callback_query.message)
        await callback_query.answer("Earning Leaderboard dikha raha hoon! 💰", show_alert=False)

    logger.info(f"Callback query '{callback_query.data}' processed for user {callback_query.from_user.id}. (Code by @asbhaibsr)")

@app.on_message(filters.command("topusers") & (filters.private | filters.group)) # Allow in both private and group
async def top_users_command(client: Client, message: Message):
    # Top users command handler for earning leaderboard. Designed by @asbhaibsr.
    if is_on_cooldown(message.from_user.id):
        return
    update_cooldown(message.from_user.id)

    top_users = await get_top_earning_users()

    if not top_users:
        await message.reply_text("😢 Abhi koi user leaderboard par nahi hai. Baatein karo aur pehle ban jao! ✨\n\n**Powered By:** @asbhaibsr", quote=True)
        return

    earning_messages = [
        "🏆 **Earning Leaderboard: Top Active Users!** 🏆\n\n"
    ]

    prizes = {1: "₹30", 2: "₹15", 3: "₹5"} # Define prizes for top 3
    rank_symbols = {1: "🥇", 2: "🥈", 3: "🥉"}

    # Limit to top 3 for display
    for i, user in enumerate(top_users[:3]): # Modified: Slicing to display only top 3
        rank = i + 1
        user_name = user.get('first_name', 'Unknown User')
        username_str = f"@{user.get('username')}" if user.get('username') else "" # Empty if no username
        message_count = user.get('message_count', 0)
        prize_str = prizes.get(rank, "₹0")
        symbol = rank_symbols.get(rank, "🏅")

        earning_messages.append(
            f"**{symbol} Rank {rank}:** [{user_name}](tg://user?id={user['user_id']}) {username_str}\n"
            f"   •💬 Total Messages: **{message_count}**\n"
            f"   • 💸 Potential Earning: **{prize_str}**\n"
        )
        # NEW: Show groups of top 3 users
        user_id = user['user_id']
        # Get distinct chat_ids where this user sent messages.
        user_active_groups = messages_collection.distinct("chat_id", {"user_id": user_id, "chat_type": {"$in": ["group", "supergroup"]}})
        
        group_links = []
        for group_id in user_active_groups:
            # Fetch group title from group_tracking_collection
            group_doc = group_tracking_collection.find_one({"_id": group_id})
            if group_doc:
                group_title = group_doc.get("title", f"Group ID: {group_id}")
                try:
                    chat_info = await client.get_chat(group_id)
                    if chat_info.invite_link:
                        group_links.append(f"[{group_title}]({chat_info.invite_link})")
                    elif chat_info.username: # For public groups with a username
                        group_links.append(f"[{group_title}](https://t.me/{chat_info.username})")
                    else: # Fallback for private groups or those without invite links/usernames
                         group_links.append(f"{group_title} (ID: `{group_id}`)") 
                except Exception as e:
                    logger.warning(f"Could not get chat info for group {group_id} ({group_title}): {e}")
                    group_links.append(f"{group_title} (ID: `{group_id}`)") # Fallback

        if group_links:
            earning_messages.append(f"   • 🌐 Active In Groups: {', '.join(group_links)}\n")
        else:
            earning_messages.append("   • 🌐 Active In Groups: N/A\n")


    earning_messages.append(
        "\n--- **Earning Rules** ---\n"
        "• 💬 **Group Conversations:** Points sirf group chats mein ki gayi genuine baaton par milenge.\n"
        "• 🚫 **No Spam:** Lagatar spam messages ya sirf stickers bhejkar points nahi milenge. Sirf meaningful chats count hongi.\n"
        "• 🎯 **Relevant Content:** Aapke messages group topic se relevant hone chahiye aur sabhi ke liye useful ya engaging ho.\n"
        "• 🔄 **Monthly Reset:** Yeh leaderboard har mahine reset kiya jayega, jiska nirdharan owner karega (`/clearearning` command se).\n"
        "• 🎁 **Prize Distribution:** Top 3 users ko owner dwara rewards diye jayenge.\n\n"
        "**Powered By:** @asbhaibsr\n**Updates:** @asbhai_bsr\n**Support:** @aschat_group"
    )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("💰 पैसे निकलवाएँ (Withdraw)", url=f"https://t.me/{ASBHAI_USERNAME}") # Direct link to owner
            ]
        ]
    )

    await message.reply_text("\n".join(earning_messages), reply_markup=keyboard, quote=True, disable_web_page_preview=True)
    await store_message(message) # Store the command message itself
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name, is_active=True)
    logger.info(f"Top users command processed for user {message.from_user.id} in chat {message.chat.id}. (Code by @asbhaibsr)")

@app.on_message(filters.command("broadcast") & filters.private)
async def broadcast_command(client: Client, message: Message):
    # Broadcast command handler. Designed for owner by @asbhaibsr.
    if is_on_cooldown(message.from_user.id):
        return
    update_cooldown(message.from_user.id)

    # Convert OWNER_ID to str for comparison
    if str(message.from_user.id) != str(OWNER_ID):
        await message.reply_text("Oops! Sorry sweetie, yeh command sirf mere boss ke liye hai. Tumhe permission nahi hai. 🤷‍♀️ (Code by @asbhaibsr)")
        return

    if len(message.command) < 2:
        await message.reply_text("Hey, broadcast karne ke liye kuch likho toh sahi! 🙄 Jaise: `/broadcast Aapka message yahan` (Code by @asbhaibsr)")
        return

    broadcast_text = " ".join(message.command[1:])
    
    unique_chat_ids = group_tracking_collection.distinct("_id") # Changed to use group_tracking_collection for groups
    
    sent_count = 0
    failed_count = 0
    logger.info(f"Starting broadcast to {len(unique_chat_ids)} chats. (Broadcast by @asbhaibsr)")
    for chat_id in unique_chat_ids:
        try:
            # Avoid sending broadcast to the private chat where the command was issued
            if chat_id == message.chat.id and message.chat.type == ChatType.PRIVATE: # Use ChatType enum
                continue 
            
            await client.send_message(chat_id, broadcast_text)
            sent_count += 1
            await asyncio.sleep(0.1) # Small delay to avoid FloodWait
        except Exception as e:
            logger.error(f"Failed to send broadcast to chat {chat_id}: {e}. (Broadcast by @asbhaibsr)")
            failed_count += 1
    
    await message.reply_text(f"Broadcast ho gaya, darling! ✨ **{sent_count}** chats tak pahunchi, aur **{failed_count}** tak nahi. Koi nahi, next time! 😉 (System by @asbhaibsr)")
    await store_message(message)
    logger.info(f"Broadcast command processed by owner {message.from_user.id}. (Code by @asbhaibsr)")

@app.on_message(filters.command("stats") & filters.private)
async def stats_private_command(client: Client, message: Message):
    # Stats command handler for private chat. Logic by @asbhaibsr.
    if is_on_cooldown(message.from_user.id):
        return
    update_cooldown(message.from_user.id)

    if len(message.command) < 2 or message.command[1].lower() != "check":
        await message.reply_text("Umm, stats check karne ke liye theek se likho na! `/stats check` aise. 😊 (Code by @asbhaibsr)")
        return

    total_messages = messages_collection.count_documents({})
    # Only count active groups and users for stats display
    unique_group_ids = group_tracking_collection.count_documents({}) 
    num_active_users = user_tracking_collection.count_documents({"is_active": True}) # Count only active users

    stats_text = (
        "📊 **Bot Statistics** 📊\n"
        f"• Jitne groups mein main hoon: **{unique_group_ids}** lovely groups!\n"
        f"• Total active users jo maine observe kiye: **{num_active_users}** pyaare users!\n"
        f"• Total messages jo maine store kiye: **{total_messages}** baaton ka khazana! 🤩\n\n"
        f"**Powered By:** @asbhaibsr\n**Updates:** @asbhai_bsr\n**Support:** @aschat_group"
    )
    await message.reply_text(stats_text)
    await store_message(message)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name, is_active=True)
    logger.info(f"Private stats command processed for user {message.from_user.id}. (Code by @asbhaibsr)")

@app.on_message(filters.command("stats") & filters.group)
async def stats_group_command(client: Client, message: Message):
    # Stats command handler for groups. Logic by @asbhaibsr.
    if is_on_cooldown(message.from_user.id):
        return
    update_cooldown(message.from_user.id)

    if len(message.command) < 2 or message.command[1].lower() != "check":
        await message.reply_text("Umm, stats check karne ke liye theek se likho na! `/stats check` aise. 😊 (Code by @asbhaibsr)")
        return

    total_messages = messages_collection.count_documents({})
    unique_group_ids = group_tracking_collection.count_documents({})
    num_active_users = user_tracking_collection.count_documents({"is_active": True}) # Count only active users

    stats_text = (
        "📊 **Bot Statistics** 📊\n"
        f"• Jitne groups mein main hoon: **{unique_group_ids}** lovely groups!\n"
        f"• Total active users jo maine observe kiye: **{num_active_users}** pyaare users!\n"
        f"• Total messages jo maine store kiye: **{total_messages}** baaton ka khazana! 🤩\n\n"
        f"**Powered By:** @asbhaibsr\n**Updates:** @asbhai_bsr\n**Support:** @aschat_group"
    )
    await message.reply_text(stats_text)
    await store_message(message)
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]: # Use ChatType enum
        await update_group_info(message.chat.id, message.chat.title)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name, is_active=True)
    logger.info(f"Group stats command processed for user {message.from_user.id} in chat {message.chat.id}. (Code by @asbhaibsr)")

# --- Group Management Commands ---

@app.on_message(filters.command("groups") & filters.private)
async def list_groups_command(client: Client, message: Message):
    # List groups command. Admin only. Code by @asbhaibsr.
    if is_on_cooldown(message.from_user.id):
        return
    update_cooldown(message.from_user.id)

    # Convert OWNER_ID to str for comparison
    if str(message.from_user.id) != str(OWNER_ID):
        await message.reply_text("Oops! Sorry sweetie, yeh command sirf mere boss ke liye hai. Tumhe permission nahi hai. 🤷‍♀️ (Code by @asbhaibsr)")
        return

    all_groups = list(group_tracking_collection.find({}))
    
    if not all_groups:
        await message.reply_text("Main abhi kisi group mein nahi hoon. Akeli hoon, koi add kar lo na! 🥺 (Code by @asbhaibsr)")
        return

    group_list_text = "📚 **Groups Jahan Main Hoon** 📚\n\n"
    found_any_group = False
    for i, group in enumerate(all_groups):
        group_id = group.get("_id")
        
        try:
            chat_info = await client.get_chat(group_id)
            # Filter out private groups and channels
            if chat_info.type == ChatType.PRIVATE or chat_info.type == ChatType.CHANNEL or chat_info.type == ChatType.BOT:
                continue # Skip private chats and channels, and bots
            
            title = group.get("title", "Unknown Group")
            username = chat_info.username
            added_on = group.get("added_on", "N/A").strftime("%Y-%m-%d %H:%M") if isinstance(group.get("added_on"), datetime) else "N/A"
            
            group_list_text += f"{i+1}. **{title}** (`{group_id}`)\n"
            if username:
                group_list_text += f"   • Username: @{username}\n"
            group_list_text += f"   • Joined: {added_on}\n"
            found_any_group = True

        except Exception as e:
            logger.warning(f"Could not fetch chat info for group ID {group_id}: {e}")
            # Even if chat_info fails, list it if it's in tracking, but mark as inaccessible
            title = group.get("title", "Unknown Group")
            added_on = group.get("added_on", "N/A").strftime("%Y-%m-%d %H:%M") if isinstance(group.get("added_on"), datetime) else "N/A"
            group_list_text += f"{i+1}. **{title}** (`{group_id}`)\n"
            group_list_text += f"   • Status: Inaccessible/Private (Details cannot be fetched)\n"
            group_list_text += f"   • Joined: {added_on}\n"
            found_any_group = True
            continue # Continue to next group

    if not found_any_group:
        group_list_text = "Main abhi kisi public group mein nahi hoon. Akeli hoon, koi add kar lo na! 🥺 (Code by @asbhaibsr)"

    group_list_text += "\n_Yeh data tracking database se hai, bilkul secret!_ 🤫\n**Code & System By:** @asbhaibsr"
    await message.reply_text(group_list_text)
    await store_message(message)
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name, is_active=True)
    logger.info(f"Groups list command processed by owner {message.from_user.id}. (Code by @asbhaibsr)")


@app.on_message(filters.command("leavegroup") & filters.private)
async def leave_group_command(client: Client, message: Message):
    # Leave group command. Admin only. Code by @asbhaibsr.
    if is_on_cooldown(message.from_user.id):
        return
    update_cooldown(message.from_user.id)

    # Convert OWNER_ID to str for comparison
    if str(message.from_user.id) != str(OWNER_ID):
        await message.reply_text("Oops! Sorry sweetie, yeh command sirf mere boss ke liye hai. Tumhe permission nahi hai. 🤷‍♀️ (Code by @asbhaibsr)")
        return

    if len(message.command) < 2:
        await message.reply_text("Kripya group ID dein jisse aap mujhe hatana chahte hain. Upyog: `/leavegroup -1001234567890` (aise, darling!) (Code by @asbhaibsr)")
        return

    try:
        group_id_str = message.command[1]
        if not group_id_str.startswith('-100'):
            await message.reply_text("Aapne galat Group ID format diya hai. Group ID `-100...` se shuru hoti hai. Thoda dhyaan se! 😊 (Code by @asbhaibsr)")
            return

        group_id = int(group_id_str)
        
        await client.leave_chat(group_id)
        
        group_tracking_collection.delete_one({"_id": group_id})
        messages_collection.delete_many({"chat_id": group_id})
        # No specific earning data deletion here, as earning is per user, not per group.
        # If a user's *entire* message history for a group is deleted, their earning count
        # might be affected if the earning system calculated based on messages_collection content
        # rather than just group_message_count in earning_tracking_collection.
        # Current design increments `group_message_count` directly. So, deleting messages
        # won't decrement past earnings unless we add a reverse lookup or separate earning by group.
        # For now, it's consistent with "resetting monthly earnings" being a separate command.
        
        logger.info(f"Left group {group_id} and cleared its related message data. (Code by @asbhaibsr)")

        await message.reply_text(f"Safaltapoorvak group `{group_id}` se bahar aa gayi, aur uska sara data bhi clean kar diya! Bye-bye! 👋 (Code by @asbhaibsr)")
        logger.info(f"Left group {group_id} and cleared its data. (Code by @asbhaibsr)")

    except ValueError:
        await message.reply_text("Invalid group ID format. Kripya ek valid numeric ID dein. Thoda number check kar lo! 😉 (Code by @asbhaibsr)")
    except Exception as e:
        await message.reply_text(f"Group se bahar nikalte samay galti ho gayi: {e}. Oh no! 😢 (Code by @asbhaibsr)")
        logger.error(f"Error leaving group {group_id_str}: {e}. (Code by @asbhaibsr)")
    
    await store_message(message)
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name, is_active=True)

# --- New Commands ---

@app.on_message(filters.command("cleardata") & filters.private)
async def clear_data_command(client: Client, message: Message):
    # Clear data command. Admin only. Code by @asbhaibsr.
    if is_on_cooldown(message.from_user.id):
        return
    update_cooldown(message.from_user.id)

    # Convert OWNER_ID to str for comparison
    if str(message.from_user.id) != str(OWNER_ID):
        await message.reply_text("Sorry, darling! Yeh command sirf mere boss ke liye hai. 🤫 (Code by @asbhaibsr)")
        return

    if len(message.command) < 2:
        await message.reply_text("Kitna data clean karna hai? Percentage batao na, jaise: `/cleardata 10%` ya `/cleardata 100%`! 🧹 (Code by @asbhaibsr)")
        return

    percentage_str = message.command[1].strip('%')
    try:
        percentage = int(percentage_str)
        if not (1 <= percentage <= 100):
            await message.reply_text("Percentage 1 se 100 ke beech mein hona chahiye. Thoda dhyan se! 🤔 (Code by @asbhaibsr)")
            return
    except ValueError:
        await message.reply_text("Invalid percentage format. Percentage number mein hona chahiye, jaise `10` ya `50`. Fir se try karo!💖 (Code by @asbhaibsr)")
        return

    total_messages = messages_collection.count_documents({})
    if total_messages == 0:
        await message.reply_text("Mere paas abhi koi data nahi hai delete karne ke liye. Sab clean-clean hai! ✨ (Code by @asbhaibsr)")
        return

    messages_to_delete_count = int(total_messages * (percentage / 100))
    if messages_to_delete_count == 0 and percentage > 0:
        await message.reply_text(f"Itna kam data hai ki {percentage}% delete karne se kuch fark nahi padega! 😂 (Code by @asbhaibsr)")
        return
    elif messages_to_delete_count == 0 and percentage == 0:
        await message.reply_text("Zero percent? That means no deletion! 😉 (Code by @asbhaibsr)")
        return


    oldest_message_ids = []
    for msg in messages_collection.find({}) \
                                        .sort("timestamp", 1) \
                                        .limit(messages_to_delete_count):
        oldest_message_ids.append(msg['_id'])

    if oldest_message_ids:
        delete_result = messages_collection.delete_many({"_id": {"$in": oldest_message_ids}})
        await message.reply_text(f"Wow! 🤩 Maine aapka **{percentage}%** data, yaani **{delete_result.deleted_count}** messages, successfully delete kar diye! Ab main thodi light feel kar rahi hoon. ✨ (Code by @asbhaibsr)")
        logger.info(f"Cleared {delete_result.deleted_count} messages based on {percentage}% request. (Code by @asbhaibsr)")
    else:
        await message.reply_text("Umm, kuch delete karne ke liye mila hi nahi. Lagta hai tumne pehle hi sab clean kar diya hai! 🤷‍♀️ (Code by @asbhaibsr)")
    
    await store_message(message)
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name, is_active=True)

@app.on_message(filters.command("deletemessage") & filters.private)
async def delete_specific_message_command(client: Client, message: Message):
    # Delete specific message command. Admin only. Code by @asbhaibsr.
    if is_on_cooldown(message.from_user.id):
        return
    update_cooldown(message.from_user.id)

    # Convert OWNER_ID to str for comparison
    if str(message.from_user.id) != str(OWNER_ID):
        await message.reply_text("Oops! Sorry sweetie, yeh command sirf mere boss ke liye hai. Tumhe permission nahi hai. 🤷‍♀️ (Code by @asbhaibsr)")
        return

    if len(message.command) < 2:
        await message.reply_text("Kaun sa message delete karna hai, batao toh sahi! Jaise: `/deletemessage hello` ya `/deletemessage 'kya haal hai'` 👻 (Code by @asbhaibsr)")
        return

    search_query = " ".join(message.command[1:])
    
    # Try to find message in current chat first
    # This logic was attempting to find a specific message in the current chat or globally
    # but might not be ideal for deleting based on content alone, as content might not be unique.
    # For now, keeping it as is, but consider if you want to delete based on message ID for more precision.
    message_to_delete = messages_collection.find_one({"chat_id": message.chat.id, "content": {"$regex": f"^{re.escape(search_query)}$", "$options": "i"}})

    if not message_to_delete:
        # If not found in current chat, search globally
        message_to_delete = messages_collection.find_one({"content": {"$regex": f"^{re.escape(search_query)}$", "$options": "i"}})

    if message_to_delete:
        delete_result = messages_collection.delete_one({"_id": message_to_delete["_id"]})
        if delete_result.deleted_count > 0:
            await message.reply_text(f"Jaisa hukum mere aaka! 🧞‍♀️ Maine '{search_query}' wale message ko dhoondh ke delete kar diya. Ab woh history ka हिस्सा nahi raha! ✨ (Code by @asbhaibsr)")
            logger.info(f"Deleted message with content: '{search_query}'. (Code by @asbhaibsr)")
        else:
            await message.reply_text("Aww, yeh message to mujhe mila hi nahi. Shayad usne apni location badal di hai! 🕵️‍♀️ (Code by @asbhaibsr)")
    else:
        await message.reply_text("Umm, mujhe tumhara yeh message to mila hi nahi apne database mein. Spelling check kar lo? 🤔 (Code by @asbhaibsr)")
    
    await store_message(message)
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name, is_active=True)

@app.on_message(filters.command("clearearning") & filters.private)
async def clear_earning_command(client: Client, message: Message):
    # New command to manually clear earning data. Only for owner.
    if is_on_cooldown(message.from_user.id):
        return
    update_cooldown(message.from_user.id)

    # Convert OWNER_ID to str for comparison
    if str(message.from_user.id) != str(OWNER_ID):
        await message.reply_text("Sorry darling! Yeh command sirf mere boss ke liye hai. Tumhe permission nahi hai. 🚫 (Code by @asbhaibsr)")
        return

    await reset_monthly_earnings_manual()
    await message.reply_text("💰 **Earning data successfully cleared!** Ab sab phir se zero se shuru karenge! Aur saare withdrawal requests bhi hata diye gaye hain. 😉 (Code by @asbhaibsr)")
    logger.info(f"Owner {message.from_user.id} manually triggered earning data reset and withdrawal request clear. (Code by @asbhaibsr)")
    
    await store_message(message)
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name, is_active=True)

@app.on_message(filters.command("restart") & filters.private)
async def restart_command(client: Client, message: Message):
    # Restart command. Admin only. Code by @asbhaibsr.
    if is_on_cooldown(message.from_user.id):
        return
    update_cooldown(message.from_user.id)

    # Convert OWNER_ID to str for comparison
    if str(message.from_user.id) != str(OWNER_ID):
        await message.reply_text("Sorry, darling! Yeh command sirf mere boss ke liye hai. 🚫 (Code by @asbhaibsr)")
        return

    await message.reply_text("Okay, darling! Main abhi ek chhota sa nap le rahi hoon aur phir wapas aa jaungi, bilkul fresh aur energetic! Thoda wait karna, theek hai? ✨ (System by @asbhaibsr)")
    logger.info("Bot is restarting... (System by @asbhaibsr)")
    # Give some time for the message to be sent
    await asyncio.sleep(0.5) 
    os.execl(sys.executable, sys.executable, *sys.argv) # This will restart the script (Code by @asbhaibsr)

# --- NEW: /chat on/off command ---
@app.on_message(filters.command("chat") & filters.group)
async def chat_toggle_command(client: Client, message: Message):
    # Chat on/off command. Only for group admins.
    if is_on_cooldown(message.from_user.id):
        return
    update_cooldown(message.from_user.id)

    if not message.from_user:
        return # Command not from a user

    # Check if the user is an admin of the group
    chat_member = await client.get_chat_member(message.chat.id, message.from_user.id)
    if not (chat_member.status in ["creator", "administrator"]):
        await message.reply_text("Oops! Yeh command sirf group admins hi use kar sakte hain. Sorry! 🙄 (Feature by @asbhaibsr)")
        return

    if len(message.command) < 2:
        current_state = group_chat_states.get(message.chat.id, True) # Default to True
        state_text = "ON" if current_state else "OFF"
        await message.reply_text(f"Meri chat is group mein abhi **{state_text}** hai. Toggle karne ke liye `/chat on` ya `/chat off` use karein. (Feature by @asbhaibsr)")
        return

    action = message.command[1].lower()

    if action == "on":
        group_chat_states[message.chat.id] = True
        await update_group_chat_state_in_db(message.chat.id, True)
        await message.reply_text("🎉 **Chat ON!** Main ab is group mein sabhi messages ka jawab dungi. Chalo baatein karein! 😊 (Feature by @asbhaibsr)")
        logger.info(f"Chat enabled for group {message.chat.id} by admin {message.from_user.id}. (Feature by @asbhaibsr)")
    elif action == "off":
        group_chat_states[message.chat.id] = False
        await update_group_chat_state_in_db(message.chat.id, False)
        await message.reply_text("😴 **Chat OFF!** Main ab is group mein messages ka jawab nahi dungi. Jab baat karni ho, `/chat on` kar dena. (Feature by @asbhaibsr)")
        logger.info(f"Chat disabled for group {message.chat.id} by admin {message.from_user.id}. (Feature by @asbhaibsr)")
    else:
        await message.reply_text("Invalid command. Please use `/chat on` or `/chat off`. (Feature by @asbhaibsr)")
    
    await store_message(message)
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name, is_active=True)

# --- New chat members and left chat members ---
@app.on_message(filters.new_chat_members)
async def new_member_handler(client: Client, message: Message):
    # Handler for new members. Notifications by @asbhaibsr.
    logger.info(f"New chat members detected in chat {message.chat.id}. Bot ID: {client.me.id}. (Event handled by @asbhaibsr)")

    for member in message.new_chat_members:
        logger.info(f"Processing new member: {member.id} ({member.first_name}) in chat {message.chat.id}. Is bot: {member.is_bot}. (Event handled by @asbhaibsr)")
        
        # Check if the bot itself was added to a group
        if member.id == client.me.id:
            if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]: # Use ChatType enum here
                logger.info(f"DEBUG: Bot {client.me.id} detected as new member in group {message.chat.id}. Calling update_group_info.") # NEW DEBUG LOG
                await update_group_info(message.chat.id, message.chat.title)
                # Set initial chat state to True (on) for new groups
                group_chat_states[message.chat.id] = True 
                logger.info(f"Bot joined new group: {message.chat.title} ({message.chat.id}). (Event handled by @asbhaibsr)")
                
                # Send notification to OWNER
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
                    await client.send_message(chat_id=OWNER_ID, text=notification_message)
                    logger.info(f"Owner notified about new group: {group_title}. (Notification by @asbhaibsr)")
                except Exception as e:
                    logger.error(f"Could not notify owner about new group {group_title}: {e}. (Notification error by @asbhaibsr)")
            # If the bot itself was added, no need to process other members in this specific event
            return 

        # Check if a new user joined a private chat with the bot (i.e., started the bot)
        # Or if a new user joined a group where the bot is present
        if not member.is_bot: # Only for actual users, not other bots
            user_exists_doc = user_tracking_collection.find_one({"_id": member.id})
            
            # Condition for new user starting bot in private chat
            if message.chat.type == ChatType.PRIVATE and member.id == message.from_user.id:
                # Always update user_info, setting is_active to True
                await update_user_info(member.id, member.username, member.first_name, is_active=True)
                if not user_exists_doc or not user_exists_doc.get("is_active"): # Only notify if truly new or previously inactive
                    user_name = member.first_name if member.first_name else "Naya User"
                    user_username = f"@{member.username}" if member.username else "N/A"
                    notification_message = (
                        f"✨ **New User Alert!**\n"
                        f"Ek naye user ne bot ko private mein start kiya hai.\n\n"
                        f"**User Name:** {user_name}\n"
                        f"**User ID:** `{member.id}`\n"
                        f"**Username:** {user_username}\n"
                        f"**Started On:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                        f"**Code By:** @asbhaibsr\n**Updates:** @asbhai_bsr\n**Support:** @aschat_group"
                    )
                    try:
                        await client.send_message(chat_id=OWNER_ID, text=notification_message)
                        logger.info(f"Owner notified about new private user: {user_name}. (Notification by @asbhaibsr)")
                    except Exception as e:
                        logger.error(f"Could not notify owner about new private user {user_name}: {e}. (Notification error by @asbhaibsr)")
                
            # Condition for new user joining a group where the bot is present
            elif message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
                # Always update user_info, setting is_active to True
                await update_user_info(member.id, member.username, member.first_name, is_active=True)
                if not user_exists_doc or not user_exists_doc.get("is_active"): # Only notify if truly new or previously inactive
                    user_name = member.first_name if member.first_name else "Naya User"
                    user_username = f"@{member.username}" if member.username else "N/A"
                    group_title = message.chat.title if message.chat.title else f"Unknown Group (ID: {message.chat.id})"
                    notification_message = (
                        f"👥 **New Group Member Alert!**\n"
                        f"Ek naya user group mein add hua hai jahan bot bhi hai.\n\n"
                        f"**User Name:** {user_name}\n"
                        f"**User ID:** `{member.id}`\n"
                        f"**Username:** {user_username}\n"
                        f"**Group Name:** {group_title}\n"
                        f"**Group ID:** `{message.chat.id}`\n"
                        f"**Joined On:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                        f"**Code By:** @asbhaibsr\n**Updates:** @asbhai_bsr\n**Support:** @aschat_group"
                    )
                    try:
                        await client.send_message(chat_id=OWNER_ID, text=notification_message)
                        logger.info(f"Owner notified about new group member: {user_name} in {group_title}. (Notification by @asbhaibsr)")
                    except Exception as e:
                        logger.error(f"Could not notify owner about new group member {user_name} in {group_title}: {e}. (Notification error by @asbhaibsr)")
    
    # Store the new_chat_members event message itself (optional, but consistent with other message storage)
    await store_message(message)
    # The `update_user_info` for `message.from_user` is handled by general message processing or start commands.


@app.on_message(filters.left_chat_member)
async def left_member_handler(client: Client, message: Message):
    # Left member handler. Logic by @asbhaibsr.
    logger.info(f"Left chat member detected in chat {message.chat.id}. Left member ID: {message.left_chat_member.id}. Bot ID: {client.me.id}. (Event handled by @asbhaibsr)")

    if message.left_chat_member and message.left_chat_member.id == client.me.id:
        if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]: # Use ChatType enum
            # Clear group's data when bot leaves
            group_tracking_collection.delete_one({"_id": message.chat.id})
            messages_collection.delete_many({"chat_id": message.chat.id})
            
            # Remove chat state from local cache
            if message.chat.id in group_chat_states:
                del group_chat_states[message.chat.id]

            logger.info(f"Bot left group: {message.chat.title} ({message.chat.id}). Data cleared. (Code by @asbhaibsr)")
            # Send notification to OWNER
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
                await client.send_message(chat_id=OWNER_ID, text=notification_message)
                logger.info(f"Owner notified about bot leaving group: {group_title}. (Notification by @asbhaibsr)")
            except Exception as e:
                logger.error(f"Could not notify owner about bot leaving group {group_title}: {e}. (Notification error by @asbhaibsr)")
            return # No need to store message if bot left

    # If a regular user leaves a group (or is removed)
    if message.left_chat_member and not message.left_chat_member.is_bot:
        user_id_left = message.left_chat_member.id
        
        # Keep message data for the user.
        # Mark user as inactive in user_tracking_collection.
        await update_user_info(user_id_left, message.left_chat_member.username, message.left_chat_member.first_name, is_active=False)
        
        # Log and optionally notify owner
        logger.info(f"User {user_id_left} ({message.left_chat_member.first_name}) left group {message.chat.id}. Marked as inactive. (User tracking by @asbhaibsr)")
        
        # You might want to notify owner about important users leaving, or just log.
        # For this request, we'll just mark as inactive and ensure they don't show in /stats or /groups (user list)
        # unless they rejoin. The message data remains.

    # Store the left_chat_member event message itself
    await store_message(message)
    # The `update_user_info` for `message.from_user` is handled by general message processing or start commands.


@app.on_message(filters.text | filters.sticker)
async def handle_message_and_reply(client: Client, message: Message):
    # Main message handler for replies. Core logic by @asbhaibsr.
    if message.from_user and message.from_user.is_bot:
        # Important: Bots' messages should not count towards earning,
        # and generally, the bot should not learn from other bots' messages.
        logger.debug(f"Skipping message from bot user: {message.from_user.id}. (Handle message by @asbhaibsr)")
        return

    # Apply cooldown before processing message
    if message.from_user and is_on_cooldown(message.from_user.id):
        logger.debug(f"User {message.from_user.id} is on cooldown. Skipping message. (Cooldown by @asbhaibsr)")
        return
    if message.from_user:
        update_cooldown(message.from_user.id)

    logger.info(f"Processing message {message.id} from user {message.from_user.id if message.from_user else 'N/A'} in chat {message.chat.id} (type: {message.chat.type.name}). (Handle message by @asbhaibsr)")

    # Update group and user info regardless of whether it's a command or regular message
    # Ensure update_group_info is called correctly when a message arrives in a group
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]: # Use ChatType enum
        logger.info(f"DEBUG: Message from group/supergroup {message.chat.id}. Calling update_group_info.") # NEW DEBUG LOG
        await update_group_info(message.chat.id, message.chat.title)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name, is_active=True)

    await store_message(message) # This is where the earning count increments

    # NEW: Check if bot chat is disabled for this group
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP] and not group_chat_states.get(message.chat.id, True):
        logger.info(f"Chat is OFF for group {message.chat.id}. Skipping reply generation. (Feature by @asbhaibsr)")
        return # Do not generate reply if chat is off

    # Only attempt to generate a reply if it's not a command message
    if not message.text or not message.text.startswith('/'):
        logger.info(f"Attempting to generate reply for chat {message.chat.id}. (Logic by @asbhaibsr)")
        reply_doc = await generate_reply(message)
        
        if reply_doc:
            try:
                if reply_doc.get("type") == "text":
                    await message.reply_text(reply_doc["content"])
                    logger.info(f"Replied with text: {reply_doc['content']}. (System by @asbhaibsr)")
                elif reply_doc.get("type") == "sticker" and reply_doc.get("sticker_id"):
                    await message.reply_sticker(reply_doc["sticker_id"])
                    logger.info(f"Replied with sticker: {reply_doc['sticker_id']}. (System by @asbhaibsr)")
                else:
                    logger.warning(f"Reply document found but no content/sticker_id: {reply_doc}. (System by @asbhaibsr)")
            except Exception as e:
                logger.error(f"Error sending reply for message {message.id}: {e}. (System by @asbhaibsr)")
        else:
            logger.info("No suitable reply found. (System by @asbhaibsr)")


# --- Main entry point ---
if __name__ == "__main__":
    # Main bot execution point. Designed by @asbhaibsr.
    logger.info("Starting Flask health check server in a separate thread... (Code by @asbhaibsr)")
    flask_thread = threading.Thread(target=run_flask_app)
    flask_thread.start()

    logger.info("Loading initial chat states... (Feature by @asbhaibsr)")
    app.run(load_chat_states()) # Run this async function before starting the bot polling
    
    logger.info("Starting Pyrogram bot... (Code by @asbhaibsr)")
    
    # Pyrogram app.run() मेथड को सीधे कॉल करें. यह Pyrogram को शुरू और आइडल रखेगा.
    app.run()
    
    # End of bot code. Thank you for using! Made with ❤️ by @asbhaibsr

