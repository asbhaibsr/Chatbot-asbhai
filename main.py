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
from pyrogram.enums import ChatType, ChatMemberStatus

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

OWNER_ID = os.getenv("OWNER_ID")

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

# --- Constants ---
MAX_MESSAGES_THRESHOLD = 100000
PRUNE_PERCENTAGE = 0.30
UPDATE_CHANNEL_USERNAME = "asbhai_bsr"
ASBHAI_USERNAME = "asbhaibsr"
BOT_PHOTO_URL = "https://envs.sh/FU3.jpg"
REPO_LINK = "https://github.com/asbhaibsr/Chatbot-asbhai.git"

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
    # NEW: Collection for biolink exceptions
    biolink_exceptions_collection = db_tracking.biolink_exceptions
    logger.info("MongoDB (Tracking, Earning & Biolink Exceptions) connection successful. Credit: @asbhaibsr")

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

# --- Cooldown dictionary ---
user_cooldowns = {}
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

# NEW: Admin Check Utility
async def is_admin_or_owner(client: Client, chat_id: int, user_id: int):
    # Check if the user is the bot owner
    if str(user_id) == str(OWNER_ID):
        return True

    # Check if the user is an admin in the group
    try:
        member = await client.get_chat_member(chat_id, user_id)
        if member.status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
            return True
    except Exception as e:
        logger.error(f"Error checking admin status for user {user_id} in chat {chat_id}: {e}")
    return False

# NEW: Function to check for links in message text (Improved Regex)
def contains_link(text: str):
    if not text:
        return False
    # Regex for common URL patterns including t.me and typical link formats
    # This regex is broad to catch various forms of links
    url_pattern = r"(?:https?://|www\.|t\.me/)[^\s/$.?#].[^\s]*"
    return bool(re.search(url_pattern, text, re.IGNORECASE))

# NEW: Function to check for @mentions in message text (Improved Regex)
def contains_mention(text: str):
    if not text:
        return False
    # Regex for @mentions (starts with @ followed by word characters, dots, or dashes)
    mention_pattern = r"@[\w\d\._-]+"
    return bool(re.search(mention_pattern, text))

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
            "is_bot_observed_pair": False,
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
                replied_content = message.reply_to_message.sticker.emoji if message.reply_to_message.emoji else ""

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
        logger.info(f"Message stored: {message.id} from {message.from_user.id if message.from_user else 'None'}. (Storage by @asbhaibsr)")

        logger.debug(f"DEBUG: Checking earning condition in store_message: chat_type={message.chat.type.name}, is_from_user={bool(message.from_user)}, is_not_bot={not message.from_user.is_bot if message.from_user else 'N/A'}")

        if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP] and message.from_user and not message.from_user.is_bot:
            user_id_to_track = message.from_user.id
            username_to_track = message.from_user.username
            first_name_to_track = message.from_user.first_name
            current_group_id = message.chat.id
            current_group_title = message.chat.title
            current_group_username = message.chat.username

            logger.info(f"DEBUG: Attempting to update earning count for user {user_id_to_track} ({first_name_to_track}) in chat {message.chat.id}.")

            try:
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

    potential_replies = []

    observed_replies_cursor = messages_collection.find({
        "is_bot_observed_pair": True,
        "replied_to_content": {"$regex": f"^{re.escape(query_content)}$", "$options": "i"},
        "user_id": app.me.id
    })
    for doc in observed_replies_cursor:
        potential_replies.append(doc)

    if potential_replies:
        chosen_reply = random.choice(potential_replies)
        logger.info(f"Contextual reply found for '{query_content}': {chosen_reply.get('content') or chosen_reply.get('sticker_id')}. (Logic by @asbhaibsr)")
        return chosen_reply

    logger.info(f"No direct observed reply for: '{query_content}'. Falling back to keyword search. (Logic by @asbhaibsr)")

    keyword_regex = "|".join([re.escape(kw) for kw in query_keywords])

    general_replies_cursor = messages_collection.find({
        "type": {"$in": ["text", "sticker"]},
        "content": {"$regex": f".*({keyword_regex}).*", "$options": "i"} if keyword_regex else {"$exists": True}
    })

    potential_replies = []
    for doc in general_replies_cursor:
        potential_replies.append(doc)

    if potential_replies:
        chosen_reply = random.choice(potential_replies)
        logger.info(f"Keyword-based reply found for '{query_content}': {chosen_reply.get('content') or chosen_reply.get('sticker_id')}. (Logic by @asbhaibsr)")
        return chosen_reply

    logger.info(f"No suitable reply found for: '{query_content}'. (Logic by @asbhaibsr)")
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

@app.on_message(filters.command("start") & filters.private)
async def start_private_command(client: Client, message: Message):
    if is_on_cooldown(message.from_user.id):
        return
    update_cooldown(message.from_user.id)

    user_name = message.from_user.first_name if message.from_user else "Dost"

    welcome_message = f"Hello **{user_name}!** 👋 Main aa gayi hoon. Chalo, baatein karte hain! 😊"

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
                InlineKeyboardButton("ℹ️ Help", callback_data="show_help_menu"),
                InlineKeyboardButton("💰 Earning Leaderboard", callback_data="show_earning_leaderboard")
            ]
        ]
    )

    await message.reply_photo(
        photo=BOT_PHOTO_URL,
        caption=welcome_message,
        reply_markup=keyboard
    )
    await store_message(message)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)
    logger.info(f"Private start command processed for user {message.from_user.id}. (Code by @asbhaibsr)")

@app.on_message(filters.command("start") & filters.group)
async def start_group_command(client: Client, message: Message):
    if is_on_cooldown(message.from_user.id):
        return
    update_cooldown(message.from_user.id)

    user_name = message.from_user.first_name if message.from_user else "Dost"

    welcome_message = f"Hello **{user_name}!** 👋 Main aa gayi hoon. Group ki baatein sunne ko taiyar hoon! 😊"

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("📣 Updates Channel", url=f"https://t.me/{UPDATE_CHANNEL_USERNAME}"),
                InlineKeyboardButton("❓ Support Group", url="https://t.me/aschat_group")
            ],
            [
                InlineKeyboardButton("ℹ️ Help", callback_data="show_help_menu"),
                InlineKeyboardButton("💰 Earning Leaderboard", callback_data="show_earning_leaderboard")
            ]
        ]
    )

    await message.reply_photo(
        photo=BOT_PHOTO_URL,
        caption=welcome_message,
        reply_markup=keyboard
    )
    await store_message(message)
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        logger.info(f"Attempting to update group info from /start command in chat {message.chat.id}.")
        await update_group_info(message.chat.id, message.chat.title, message.chat.username)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)
    logger.info(f"Group start command processed in chat {message.chat.id}. (Code by @asbhaibsr)")


@app.on_callback_query()
async def callback_handler(client, callback_query):
    if callback_query.data == "buy_git_repo":
        await callback_query.message.reply_text(
            f"🤩 Agar aapko mere jaisa khud ka bot banwana hai, toh aapko ₹500 dene honge. Iske liye **@{ASBHAI_USERNAME}** se contact karein aur unhe bataiye ki aapko is bot ka code chahiye banwane ke liye. Jaldi karo, deals hot hain! 💸\n\n**Owner:** @asbhaibsr\n**Updates:** @asbhai_bsr\n**Support:** @aschat_group",
            quote=True
        )
        await callback_query.answer("Details mil gayi na? Ab jao, deal final karo! 😉", show_alert=False)
        buttons_collection.insert_one({
            "user_id": callback_query.from_user.id,
            "username": callback_query.from_user.username,
            "first_name": callback_query.from_user.first_name,
            "button_data": callback_query.data,
            "timestamp": datetime.now(),
            "credit": "by @asbhaibsr"
        })
    elif callback_query.data == "show_earning_leaderboard":
        await top_users_command(client, callback_query.message)
        await callback_query.answer("Earning Leaderboard dikha raha hoon! 💰", show_alert=False)
    elif callback_query.data == "show_help_menu":
        help_text = (
            "💡 **Main Kaise Kaam Karti Hoon?**\n\n"
            "Main ek self-learning bot hoon jo conversations se seekhti hai. Aap groups mein ya mujhse private mein baat kar sakte hain, aur main aapke messages ko yaad rakhti hoon. Jab koi user similar baat karta hai, toh main usse seekhe hue reply deti hoon.\n\n"
            "**✨ Mere Functions:**\n"
            "• **Conversation:** Groups aur private chat mein baat karti hoon.\n"
            "• **Seekhna:** Aapki baaton se naye replies generate karna seekhti hoon.\n"
            "• **Commands:** Kuch khaas commands hain jo aap use kar sakte hain:\n"
            "  • `/start`: Mujhse baat shuru karne ke liye.\n"
            "  • `/help`: Yeh menu dekhne ke liye (jo aap abhi dekh rahe hain!).\n"
            "  • `/topusers`: Sabse active users ka leaderboard dekhne ke liye.\n"
            "  • `/chat on/off`: (Sirf Group Admins ke liye) Group mein meri messages band/chalu karne ke liye.\n"
            "  • `/groups`: (Sirf Owner ke liye) Jin groups mein main hoon, unki list dekhne ke liye.\n"
            "  • `/stats check`: Bot ke statistics dekhne ke liye.\n"
            "  • `/cleardata <percentage>`: (Sirf Owner ke liye) Database se data delete karne ke liye.\n"
            "  • `/deletemessage <content>`: (Sirf Owner ke liye) Specific message delete karne ke liye.\n"
            "  • `/clearearning`: (Sirf Owner ke liye) Earning data reset karne ke liye.\n"
            "  • `/leavegroup <group_id>`: (Sirf Owner ke liye) Kisi group ko chhodne ke liye.\n"
            "  • `/broadcast <message>`: (Sirf Owner ke liye) Sabhi groups mein message bhejne ke liye.\n"
            "  • `/restart`: (Sirf Owner ke liye) Bot ko restart karne ke liye.\n"
            "  • `/linkdel on/off`: (Sirf Group Admins ke liye) Group mein **sabhi prakar ke links** delete/allow karne ke liye.\n"
            "  • `/biolinkdel on/off`: (Sirf Group Admins ke liye) Group mein **`t.me` aur `http/https` links** wale messages ko delete/allow karne ke liye.\n"
            "  • `/biolink <userid>`: (Sirf Group Admins ke liye) `biolinkdel` on hone par bhi kisi user ko `t.me` aur `http/https` links भेजने की permission dene ke liye.\n"
            "  • `/usernamedel on/off`: (Sirf Group Admins ke liye) Group mein **'@' mentions** allow ya delete karne ke liye.\n\n"
            "**🔗 Mera Code (GitHub Repository):**\n"
            f"[**{REPO_LINK}**]({REPO_LINK})\n\n"
            "**Powered By:** @asbhaibsr\n**Updates:** @asbhai_bsr\n**Support:** @aschat_group"
        )
        await callback_query.message.reply_text(help_text, quote=True, disable_web_page_preview=True)
        await callback_query.answer("Help menu dikha raha hoon! 😊", show_alert=False)
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
    if is_on_cooldown(message.from_user.id):
        return
    update_cooldown(message.from_user.id)

    top_users = await get_top_earning_users()

    if not top_users:
        await message.reply_text("😢 Abhi koi user leaderboard par nahi hai. Baatein karo aur pehle ban jao! ✨\n\n**Powered By:** @asbhaibsr", quote=True)
        return

    earning_messages = [
        "💰 **Top 3 Active Users (This Month)** 💰\n\n"
    ]

    prizes = {1: "₹30", 2: "₹15", 3: "₹5"}

    for i, user in enumerate(top_users[:3]):
        rank = i + 1
        user_name = user.get('first_name', 'Unknown User')
        username_str = f"@{user.get('username')}" if user.get('username') else "N/A"
        message_count = user.get('message_count', 0)
        prize_str = prizes.get(rank, "₹0")

        group_info = ""
        last_group_id = user.get('last_active_group_id')
        last_group_title = user.get('last_active_group_title', 'Unknown Group')
        last_group_username = user.get('last_active_group_username')

        if last_group_id:
            try:
                # Try to get chat object for a more accurate display, especially for private chats
                chat_obj = await client.get_chat(last_group_id)
                if chat_obj and chat_obj.type == ChatType.PRIVATE:
                    # If it's a private chat, provide a direct link to the user
                    group_info = f"   • Last Active in: **Private Chat (N/A)**\n" # Modified to reflect it's private chat
                elif chat_obj and chat_obj.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
                    group_display_name = chat_obj.title if chat_obj.title else last_group_title
                    group_username_display = f" (@{chat_obj.username})" if chat_obj.username else ""
                    # Provide a direct link to the group if username is available
                    group_link = f"https://t.me/{chat_obj.username}" if chat_obj.username else "N/A"
                    group_info = f"   • Last Active in: **[{group_display_name}]({group_link})**{group_username_display}\n"
                else:
                    # Fallback if chat_obj not found or type is unexpected, but we have stored data
                    group_username_display = f" (@{last_group_username})" if last_group_username else ""
                    group_link = f"https://t.me/{last_group_username}" if last_group_username else "N/A"
                    group_info = f"   • Last Active in: **[{last_group_title}]({group_link})**{group_username_display}\n"
            except Exception as e:
                logger.warning(f"Could not fetch chat info for group ID {last_group_id} for leaderboard: {e}")
                # Fallback if API call fails
                group_username_display = f" (@{last_group_username})" if last_group_username else ""
                group_link = f"https://t.me/{last_group_username}" if last_group_username else "N/A"
                group_info = f"   • Last Active in: **[{last_group_title}]({group_link})**{group_username_display}\n"
        else:
            group_info = "   • Last Active Group: **N/A** (Private Chat/No Group Activity)\n"


        earning_messages.append(
            f"**Rank {rank}:** {user_name} ({username_str})\n"
            f"   • Total Messages: **{message_count}**\n"
            f"   • Potential Earning: **{prize_str}**\n"
            f"{group_info}"
        )

    earning_messages.append(
        "\n**Earning Rules:**\n"
        "• Earning will be based solely on **conversation (messages) within group chats.**\n"
        "• **Spamming or sending a high volume of messages in quick succession will not be counted.** Only genuine, relevant conversation will be considered.\n"
        "• Please ensure your conversations are **meaningful and engaging.**\n"
        "• This leaderboard can be **reset manually by the owner using /clearearning command.**\n\n"
        "**Powered By:** @asbhaibsr\n**Updates:** @asbhai_bsr\n**Support:** @aschat_group"
    )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("💰 पैसे निकलवाएँ (Withdraw)", url=f"https://t.me/{ASBHAI_USERNAME}")
            ]
        ]
    )

    await message.reply_text("\n".join(earning_messages), reply_markup=keyboard, quote=True, disable_web_page_preview=True) # Added disable_web_page_preview
    await store_message(message)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)
    logger.info(f"Top users command processed for user {message.from_user.id} in chat {message.chat.id}. (Code by @asbhaibsr)")

@app.on_message(filters.command("broadcast") & filters.private)
async def broadcast_command(client: Client, message: Message):
    if is_on_cooldown(message.from_user.id):
        return
    update_cooldown(message.from_user.id)

    if str(message.from_user.id) != str(OWNER_ID):
        await message.reply_text("Oops! Sorry sweetie, yeh command sirf mere boss ke liye hai. Tumhe permission nahi hai. 🤷‍♀️ (Code by @asbhaibsr)")
        return

    if len(message.command) < 2:
        await message.reply_text("Hey, broadcast karne ke liye kuch likho toh sahi! 🙄 Jaise: `/broadcast Aapka message yahan` (Code by @asbhaibsr)")
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

    await message.reply_text(f"Broadcast ho gaya, darling! ✨ **{sent_count}** chats tak pahunchi, aur **{failed_count}** tak nahi. Koi nahi, next time! 😉 (System by @asbhaibsr)")
    await store_message(message)
    logger.info(f"Broadcast command processed by owner {message.from_user.id}. (Code by @asbhaibsr)")

@app.on_message(filters.command("stats") & filters.private)
async def stats_private_command(client: Client, message: Message):
    if is_on_cooldown(message.from_user.id):
        return
    update_cooldown(message.from_user.id)

    if len(message.command) < 2 or message.command[1].lower() != "check":
        await message.reply_text("Umm, stats check karne ke liye theek se likho na! `/stats check` aise. 😊 (Code by @asbhaibsr)")
        return

    total_messages = messages_collection.count_documents({})
    unique_group_ids = group_tracking_collection.count_documents({})
    num_users = user_tracking_collection.count_documents({})

    stats_text = (
        "📊 **Bot Statistics** 📊\n"
        f"• Jitne groups mein main hoon: **{unique_group_ids}** lovely groups!\n"
        f"• Total users jo maine observe kiye: **{num_users}** pyaare users!\n"
        f"• Total messages jo maine store kiye: **{total_messages}** baaton ka khazana! 🤩\n\n"
        f"**Powered By:** @asbhaibsr\n**Updates:** @asbhai_bsr\n**Support:** @aschat_group"
    )
    await message.reply_text(stats_text)
    await store_message(message)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)
    logger.info(f"Private stats command processed for user {message.from_user.id}. (Code by @asbhaibsr)")

@app.on_message(filters.command("stats") & filters.group)
async def stats_group_command(client: Client, message: Message):
    if is_on_cooldown(message.from_user.id):
        return
    update_cooldown(message.from_user.id)

    if len(message.command) < 2 or message.command[1].lower() != "check":
        await message.reply_text("Umm, stats check karne ke liye theek se likho na! `/stats check` aise. 😊 (Code by @asbhaibsr)")
        return

    total_messages = messages_collection.count_documents({})
    unique_group_ids = group_tracking_collection.count_documents({})
    num_users = user_tracking_collection.count_documents({})

    stats_text = (
        "📊 **Bot Statistics** 📊\n"
        f"• Jitne groups mein main hoon: **{unique_group_ids}** lovely groups!\n"
        f"• Total users jo maine observe kiye: **{num_users}** pyaare users!\n"
        f"• Total messages jo maine store kiye: **{total_messages}** baaton ka khazana! 🤩\n\n"
        f"**Powered By:** @asbhaibsr\n**Updates:** @asbhai_bsr\n**Support:** @aschat_group"
    )
    await message.reply_text(stats_text)
    await store_message(message)
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await update_group_info(message.chat.id, message.chat.title, message.chat.username)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)
    logger.info(f"Group stats command processed for user {message.from_user.id} in chat {message.chat.id}. (Code by @asbhaibsr)")

# --- Group Management Commands ---

@app.on_message(filters.command("groups") & filters.private)
async def list_groups_command(client: Client, message: Message):
    if is_on_cooldown(message.from_user.id):
        return
    update_cooldown(message.from_user.id)

    if str(message.from_user.id) != str(OWNER_ID):
        await message.reply_text("Oops! Sorry sweetie, yeh command sirf mere boss ke liye hai. Tumhe permission nahi hai. 🤷‍♀️ (Code by @asbhaibsr)")
        return

    groups = list(group_tracking_collection.find({}))
    if not groups:
        await message.reply_text("Main abhi kisi group mein nahi hoon. Akeli hoon, koi add kar lo na! 🥺 (Code by @asbhaibsr)")
        return

    group_list_text = "📚 **Groups Jahan Main Hoon** 📚\n\n"
    for i, group in enumerate(groups):
        title = group.get("title", "Unknown Group")
        group_id = group.get("_id")
        group_username_from_db = group.get("username") # Get username directly from DB
        added_on = group.get("added_on", "N/A").strftime("%Y-%m-%d %H:%M") if isinstance(group.get("added_on"), datetime) else "N/A"

        member_count = "N/A"
        group_link_display = "" # Default empty
        try:
            chat_obj = await client.get_chat(group_id)
            member_count = await client.get_chat_members_count(group_id)
            if chat_obj.username: # If a public username exists, create a direct link
                group_link_display = f" ([@{chat_obj.username}](https://t.me/{chat_obj.username}))"
            else: # If no public username, try to get a private invite link (might fail if bot can't create one)
                try:
                    invite_link = await client.export_chat_invite_link(group_id)
                    group_link_display = f" ([Invite Link]({invite_link}))"
                except Exception as e:
                    logger.warning(f"Could not get invite link for private group {group_id}: {e}")
                    group_link_display = " (Private Group)" # Fallback for private groups
        except Exception as e:
            logger.warning(f"Could not fetch chat info for group {group_id}: {e}")
            group_link_display = " (Info N/A)" # Fallback if chat object can't be fetched

        # Prioritize the actual username if available in DB, otherwise use fetched one, if available
        # The title itself can be linked if a username is available.
        group_title_link = f"[{title}]({group_link_display.replace(' ([', 'https://t.me/').replace('])', '')})" if group_link_display and "@" in group_link_display else title

        group_list_text += (
            f"{i+1}. **{group_title_link}** (`{group_id}`){group_link_display}\n"
            f"   • Joined: {added_on}\n"
            f"   • Members: {member_count}\n"
        )

    group_list_text += "\n_Yeh data tracking database se hai, bilkul secret!_ 🤫\n**Code & System By:** @asbhaibsr"
    await message.reply_text(group_list_text, disable_web_page_preview=True) # Disable preview for links
    await store_message(message)
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)
    logger.info(f"Groups list command processed by owner {message.from_user.id}. (Code by @asbhaibsr)")

@app.on_message(filters.command("leavegroup") & filters.private)
async def leave_group_command(client: Client, message: Message):
    if is_on_cooldown(message.from_user.id):
        return
    update_cooldown(message.from_user.id)

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
        logger.info(f"Considered cleaning earning data for users from left group {group_id}. (Code by @asbhaibsr)")

        await message.reply_text(f"Safaltapoorvak group `{group_id}` se bahar aa gayi, aur uska sara data bhi clean kar diya! Bye-bye! 👋 (Code by @asbhaibsr)")
        logger.info(f"Left group {group_id} and cleared its data. (Code by @asbhaibsr)")

    except ValueError:
        await message.reply_text("Invalid group ID format. Kripya ek valid numeric ID dein. Thoda number check kar lo! 😉 (Code by @asbhaibsr)")
    except Exception as e:
        await message.reply_text(f"Group se bahar nikalte samay galti ho gayi: {e}. Oh no! 😢 (Code by @asbhaibsr)")
        logger.error(f"Error leaving group {group_id_str}: {e}. (Code by @asbhaibsr)")

    await store_message(message)
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)

# --- New Commands ---

@app.on_message(filters.command("cleardata") & filters.private)
async def clear_data_command(client: Client, message: Message):
    if is_on_cooldown(message.from_user.id):
        return
    update_cooldown(message.from_user.id)

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
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)

@app.on_message(filters.command("deletemessage") & filters.private)
async def delete_specific_message_command(client: Client, message: Message):
    if is_on_cooldown(message.from_user.id):
        return
    update_cooldown(message.from_user.id)

    if str(message.from_user.id) != str(OWNER_ID):
        await message.reply_text("Oops! Sorry sweetie, yeh command sirf mere boss ke liye hai. Tumhe permission nahi hai. 🤷‍♀️ (Code by @asbhaibsr)")
        return

    if len(message.command) < 2:
        await message.reply_text("Kaun sa message delete karna hai, batao toh sahi! Jaise: `/deletemessage hello` ya `/deletemessage 'kya haal hai'` 👻 (Code by @asbhaibsr)")
        return

    search_query = " ".join(message.command[1:])

    message_to_delete = messages_collection.find_one({"chat_id": message.chat.id, "content": {"$regex": f"^{re.escape(search_query)}$", "$options": "i"}})

    if not message_to_delete:
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
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)

@app.on_message(filters.command("clearearning") & filters.private)
async def clear_earning_command(client: Client, message: Message):
    if is_on_cooldown(message.from_user.id):
        return
    update_cooldown(message.from_user.id)

    if str(message.from_user.id) != str(OWNER_ID):
        await message.reply_text("Sorry darling! Yeh command sirf mere boss ke liye hai. 🚫 (Code by @asbhaibsr)")
        return

    await reset_monthly_earnings_manual()
    await message.reply_text("💰 **Earning data successfully cleared!** Ab sab phir se zero se shuru karenge! 😉 (Code by @asbhaibsr)")
    logger.info(f"Owner {message.from_user.id} manually triggered earning data reset. (Code by @asbhaibsr)")

    await store_message(message)
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)

@app.on_message(filters.command("restart") & filters.private)
async def restart_command(client: Client, message: Message):
    if is_on_cooldown(message.from_user.id):
        return
    update_cooldown(message.from_user.id)

    if str(message.from_user.id) != str(OWNER_ID):
        await message.reply_text("Sorry, darling! Yeh command sirf mere boss ke liye hai. 🚫 (Code by @asbhaibsr)")
        return

    await message.reply_text("Okay, darling! Main abhi ek chhota sa nap le rahi hoon aur phir wapas aa jaungi, bilkul fresh aur energetic! Thoda wait karna, theek hai? ✨ (System by @asbhaibsr)")
    logger.info("Bot is restarting... (System by @asbhaibsr)")
    await asyncio.sleep(0.5)
    os.execl(sys.executable, sys.executable, *sys.argv)

# --- /chat on/off command ---
@app.on_message(filters.command("chat") & filters.group)
async def toggle_chat_command(client: Client, message: Message):
    if is_on_cooldown(message.from_user.id):
        return
    update_cooldown(message.from_user.id)

    if not message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await message.reply_text("Yeh command sirf groups mein kaam karti hai, darling! 😉")
        return

    member = await client.get_chat_member(message.chat.id, message.from_user.id)
    if member.status not in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
        await message.reply_text("Maaf karna, yeh command sirf group admins hi use kar sakte hain. 🤷‍♀️")
        return

    if len(message.command) < 2:
        current_status_doc = group_tracking_collection.find_one({"_id": message.chat.id})
        current_status = current_status_doc.get("bot_enabled", True) if current_status_doc else True
        status_text = "chaalu hai (ON)" if current_status else "band hai (OFF)"
        await message.reply_text(f"Main abhi is group mein **{status_text}** hoon. Use `/chat on` ya `/chat off` control karne ke liye. (Code by @asbhaibsr)")
        return

    action = message.command[1].lower()

    if action == "on":
        group_tracking_collection.update_one(
            {"_id": message.chat.id},
            {"$set": {"bot_enabled": True}}
        )
        await message.reply_text("🚀 Main phir se aa gayi! Ab main is group mein baatein karungi aur seekhungi. 😊")
        logger.info(f"Bot enabled in group {message.chat.id} by admin {message.from_user.id}. (Code by @asbhaibsr)")
    elif action == "off":
        group_tracking_collection.update_one(
            {"_id": message.chat.id},
            {"$set": {"bot_enabled": False}}
        )
        await message.reply_text("😴 Main abhi thodi der ke liye chup ho rahi hoon. Jab meri zaroorat ho, `/chat on` karke bula lena. Bye-bye! 👋")
        logger.info(f"Bot disabled in group {message.chat.id} by admin {message.from_user.id}. (Code by @asbhaibsr)")
    else:
        await message.reply_text("Galat command, darling! `/chat on` ya `/chat off` use karo. 😉")

    await store_message(message)
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)


# --- NEW: Group Management Commands ---

@app.on_message(filters.command("linkdel") & filters.group)
async def toggle_linkdel_command(client: Client, message: Message):
    if is_on_cooldown(message.from_user.id):
        return
    update_cooldown(message.from_user.id)

    if not await is_admin_or_owner(client, message.chat.id, message.from_user.id):
        await message.reply_text("माफ़ करना, ये कमांड सिर्फ़ मेरे बॉस (एडमिन) ही यूज़ कर सकते हैं! 🤷‍♀️", quote=True)
        return

    if len(message.command) < 2:
        current_status_doc = group_tracking_collection.find_one({"_id": message.chat.id})
        current_status = current_status_doc.get("linkdel_enabled", False) if current_status_doc else False
        status_text = "चालू है (ON)" if current_status else "बंद है (OFF)"
        await message.reply_text(f"मेरी 'लिंक जादू' की छड़ी अभी **{status_text}** है. इसे कंट्रोल करने के लिए `/linkdel on` या `/linkdel off` यूज़ करो. 😉", quote=True)
        return

    action = message.command[1].lower()
    if action == "on":
        group_tracking_collection.update_one(
            {"_id": message.chat.id},
            {"$set": {"linkdel_enabled": True}},
            upsert=True
        )
        await message.reply_text("ही ही ही! 🤭 अब कोई भी शरारती लिंक भेजेगा, तो मैं उसे जादू से गायब कर दूंगी! 🪄 ग्रुप को एकदम साफ़-सुथरा रखना है न! 😉", quote=True)
        logger.info(f"Link deletion enabled in group {message.chat.id} by admin {message.from_user.id}.")
    elif action == "off":
        group_tracking_collection.update_one(
            {"_id": message.chat.id},
            {"$set": {"linkdel_enabled": False}},
            upsert=True
        )
        await message.reply_text("ठीक है, ठीक है! मैंने अपनी 'लिंक जादू' की छड़ी रख दी है! 😇 अब आप जो चाहे लिंक भेज सकते हैं! पर ध्यान से, ओके?", quote=True)
        logger.info(f"Link deletion disabled in group {message.chat.id} by admin {message.from_user.id}.")
    else:
        await message.reply_text("उम्म... मुझे समझ नहीं आया! 😕 `/linkdel on` या `/linkdel off` यूज़ करो, प्लीज़! ✨", quote=True)

    await store_message(message)


@app.on_message(filters.command("biolinkdel") & filters.group)
async def toggle_biolinkdel_command(client: Client, message: Message):
    if is_on_cooldown(message.from_user.id):
        return
    update_cooldown(message.from_user.id)

    if not await is_admin_or_owner(client, message.chat.id, message.from_user.id):
        await message.reply_text("माफ़ करना, ये कमांड सिर्फ़ मेरे बॉस (एडमिन) ही यूज़ कर सकते हैं! 🤷‍♀️", quote=True)
        return

    if len(message.command) < 2:
        current_status_doc = group_tracking_collection.find_one({"_id": message.chat.id})
        current_status = current_status_doc.get("biolinkdel_enabled", False) if current_status_doc else False
        status_text = "चालू है (ON)" if current_status else "बंद है (OFF)"
        await message.reply_text(f"मेरी 'बायो-लिंक पुलिस' अभी **{status_text}** है. इसे कंट्रोल करने के लिए `/biolinkdel on` या `/biolinkdel off` यूज़ करो. 👮‍♀️", quote=True)
        return

    action = message.command[1].lower()
    if action == "on":
        group_tracking_collection.update_one(
            {"_id": message.chat.id},
            {"$set": {"biolinkdel_enabled": True}},
            upsert=True
        )
        await message.reply_text("हम्म... 😼 अब से जो भी **t.me या http/https लिंक** भेजेगा (अगर उसे `/biolink` से छूट नहीं मिली है), मैं उसका मैसेज चुपचाप हटा दूंगी! ग्रुप में कोई मस्ती नहीं! 🤫", quote=True)
        logger.info(f"Biolink deletion enabled in group {message.chat.id} by admin {message.from_user.id}.")
    elif action == "off":
        group_tracking_collection.update_one(
            {"_id": message.chat.id},
            {"$set": {"biolinkdel_enabled": False}},
            upsert=True
        )
        await message.reply_text("ओके डार्लिंग्स! 😇 अब मैं `t.me` और `http/https` लिंक्स को चेक करना बंद कर रही हूँ! सब फ्री-फ्री! 🎉", quote=True)
        logger.info(f"Biolink deletion disabled in group {message.chat.id} by admin {message.from_user.id}.")
    else:
        await message.reply_text("उम्म... मुझे समझ नहीं आया! 😕 `/biolinkdel on` या `/biolinkdel off` यूज़ करो, प्लीज़! ✨", quote=True)

    await store_message(message)


@app.on_message(filters.command("biolink") & filters.group)
async def allow_biolink_user_command(client: Client, message: Message):
    if is_on_cooldown(message.from_user.id):
        return
    update_cooldown(message.from_user.id)

    if not await is_admin_or_owner(client, message.chat.id, message.from_user.id):
        await message.reply_text("माफ़ करना, ये कमांड सिर्फ़ मेरे बॉस (एडमिन) ही यूज़ कर सकते हैं! 🤷‍♀️", quote=True)
        return

    if len(message.command) < 2:
        await message.reply_text("किस यूज़र को बायो-लिंक की छूट देनी है? मुझे उसकी User ID दो ना, जैसे: `/biolink 123456789` या `/biolink remove 123456789`! 😉", quote=True)
        return

    action_or_user_id = message.command[1].lower()
    target_user_id = None

    if action_or_user_id == "remove" and len(message.command) > 2:
        try:
            target_user_id = int(message.command[2])
            biolink_exceptions_collection.delete_one({"_id": target_user_id})
            await message.reply_text(f"ओके! ✨ यूज़र `{target_user_id}` को अब बायो-लिंक की छूट नहीं मिलेगी! बाय-बाय परमिशन! 👋", quote=True)
            logger.info(f"Removed user {target_user_id} from biolink exceptions in group {message.chat.id}.")
        except ValueError:
            await message.reply_text("उम्म, गलत यूज़रआईडी! 🧐 यूज़रआईडी एक नंबर होती है. फिर से ट्राई करो, प्लीज़! 😉", quote=True)
    else:
        try:
            target_user_id = int(action_or_user_id)
            biolink_exceptions_collection.update_one(
                {"_id": target_user_id},
                {"$set": {"allowed_by_admin": True, "added_on": datetime.now(), "credit": "by @asbhaibsr"}},
                upsert=True
            )
            await message.reply_text(f"याय! 🎉 मैंने यूज़र `{target_user_id}` को स्पेशल परमिशन दे दी है! अब ये `t.me` या `http/https` लिंक्स भेजकर भी मैसेज कर पाएंगे! क्यूंकि एडमिन ने बोला, तो बोला! 👑", quote=True)
            logger.info(f"Added user {target_user_id} to biolink exceptions in group {message.chat.id}.")
        except ValueError:
            await message.reply_text("उम्म, गलत यूज़रआईडी! 🧐 यूज़रआईडी एक नंबर होती है. फिर से ट्राई करो, प्लीज़! 😉", quote=True)

    await store_message(message)


@app.on_message(filters.command("usernamedel") & filters.group)
async def toggle_usernamedel_command(client: Client, message: Message):
    if is_on_cooldown(message.from_user.id):
        return
    update_cooldown(message.from_user.id)

    if not await is_admin_or_owner(client, message.chat.id, message.from_user.id):
        await message.reply_text("माफ़ करना, ये कमांड सिर्फ़ मेरे बॉस (एडमिन) ही यूज़ कर सकते हैं! 🤷‍♀️", quote=True)
        return

    if len(message.command) < 2:
        current_status_doc = group_tracking_collection.find_one({"_id": message.chat.id})
        current_status = current_status_doc.get("usernamedel_enabled", False) if current_status_doc else False
        status_text = "चालू है (ON)" if current_status else "बंद है (OFF)"
        await message.reply_text(f"मेरी '@' टैग पुलिस अभी **{status_text}** है. इसे कंट्रोल करने के लिए `/usernamedel on` या `/usernamedel off` यूज़ करो. 🚨", quote=True)
        return

    action = message.command[1].lower()
    if action == "on":
        group_tracking_collection.update_one(
            {"_id": message.chat.id},
            {"$set": {"usernamedel_enabled": True}},
            upsert=True
        )
        await message.reply_text("चीं-चीं! 🐦 अब से कोई भी `@` करके किसी को भी परेशान नहीं कर पाएगा! जो करेगा, उसका मैसेज मैं फट से उड़ा दूंगी! 💨 मुझे डिस्टर्बेंस पसंद नहीं! 😠", quote=True)
        logger.info(f"Username deletion enabled in group {message.chat.id} by admin {message.from_user.id}.")
    elif action == "off":
        group_tracking_collection.update_one(
            {"_id": message.chat.id},
            {"$set": {"usernamedel_enabled": False}},
            upsert=True
        )
        await message.reply_text("ठीक है! आज से मेरी @ वाली आंखें बंद! 😴 अब आप जो चाहे @ करो! पर ज़्यादा तंग मत करना किसी को! 🥺", quote=True)
        logger.info(f"Username deletion disabled in group {message.chat.id} by admin {message.from_user.id}.")
    else:
        await message.reply_text("उम्म... मुझे समझ नहीं आया! 😕 `/usernamedel on` या `/usernamedel off` यूज़ करो, प्लीज़! ✨", quote=True)

    await store_message(message)

# --- New chat members and left chat members ---
@app.on_message(filters.new_chat_members)
async def new_member_handler(client: Client, message: Message):
    logger.info(f"New chat members detected in chat {message.chat.id}. Bot ID: {client.me.id}. (Event handled by @asbhaibsr)")

    for member in message.new_chat_members:
        logger.info(f"Processing new member: {member.id} ({member.first_name}) in chat {message.chat.id}. Is bot: {member.is_bot}. (Event handled by @asbhaibsr)")
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
                    await client.send_message(chat_id=OWNER_ID, text=notification_message)
                    logger.info(f"Owner notified about new group: {group_title}. (Notification by @asbhaibsr)")
                except Exception as e:
                    logger.error(f"Could not notify owner about new group {group_title}: {e}. (Notification error by @asbhaibsr)")
            return

        if not member.is_bot:
            user_exists = user_tracking_collection.find_one({"_id": member.id})

            if message.chat.type == ChatType.PRIVATE and member.id == message.from_user.id and not user_exists:
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

            elif message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP] and not user_exists:
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
            earning_tracking_collection.update_many(
                {"_id": {"$in": [user["_id"] for user in earning_tracking_collection.find({})]}},
                {"$pull": {"groups": message.chat.id}}
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
                await client.send_message(chat_id=OWNER_ID, text=notification_message)
                logger.info(f"Owner notified about bot leaving group: {group_title}. (Notification by @asbhaibsr)")
            except Exception as e:
                logger.error(f"Could not notify owner about bot leaving group {group_title}: {e}. (Notification error by @asbhaibsr)")
            return

    await store_message(message)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)


@app.on_message(filters.text | filters.sticker)
async def handle_message_and_reply(client: Client, message: Message):
    if message.from_user and message.from_user.is_bot:
        logger.debug(f"Skipping message from bot user: {message.from_user.id}. (Handle message by @asbhaibsr)")
        return

    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        group_status = group_tracking_collection.find_one({"_id": message.chat.id})
        if group_status and not group_status.get("bot_enabled", True):
            logger.info(f"Bot is disabled in group {message.chat.id}. Skipping message handling. (Code by @asbhaibsr)")
            return

    if message.from_user and is_on_cooldown(message.from_user.id):
        logger.debug(f"User {message.from_user.id} is on cooldown. Skipping message. (Cooldown by @asbhaibsr)")
        return
    if message.from_user:
        update_cooldown(message.from_user.id)

    logger.info(f"Processing message {message.id} from user {message.from_user.id if message.from_user else 'N/A'} in chat {message.chat.id} (type: {message.chat.type.name}). (Handle message by @asbhaibsr)")

    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        logger.info(f"DEBUG: Message from group/supergroup {message.chat.id}. Calling update_group_info.")
        await update_group_info(message.chat.id, message.chat.title, message.chat.username)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)

    # --- NEW: Check for /linkdel, /biolinkdel, /usernamedel conditions ---
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        current_group_settings = group_tracking_collection.find_one({"_id": message.chat.id})
        user_id = message.from_user.id if message.from_user else None

        # Always check if the sender is an admin/owner first
        is_sender_admin = False
        if user_id:
            is_sender_admin = await is_admin_or_owner(client, message.chat.id, user_id)

        # Link Deletion Check
        if current_group_settings and current_group_settings.get("linkdel_enabled", False) and message.text:
            if contains_link(message.text) and not is_sender_admin:
                try:
                    await message.delete()
                    await message.reply_text("ओहो, ये क्या भेज दिया? 🧐 सॉरी-सॉरी, यहाँ **लिंक्स अलाउड नहीं हैं!** 🚫 आपका मैसेज तो गया! 💨 अब से ध्यान रखना, हाँ?", quote=True)
                    logger.info(f"Deleted link message {message.id} from user {message.from_user.id} in chat {message.chat.id}.")
                    return # Stop further processing as message is deleted
                except Exception as e:
                    logger.error(f"Error deleting link message {message.id}: {e}")
            elif contains_link(message.text) and is_sender_admin:
                logger.info(f"Admin's link message {message.id} was not deleted in chat {message.chat.id}.")

        # Biolink Deletion Check (Updated Logic)
        # This now targets t.me and general http/https links directly within the message content
        if current_group_settings and current_group_settings.get("biolinkdel_enabled", False) and message.text and user_id:
            is_biolink_exception = biolink_exceptions_collection.find_one({"_id": user_id})

            if not is_sender_admin and not is_biolink_exception: # If user is not admin AND not in exception list
                # Check for t.me links or general http/https links in the message text
                if contains_link(message.text) and ("t.me" in message.text or "http" in message.text or "https" in message.text):
                    try:
                        await message.delete()
                        await message.reply_text(
                            "अरे बाबा रे! 😲 आपने `t.me` या `http/https` लिंक भेजा! इसीलिए आपका मैसेज गायब हो गया! 👻\n"
                            "अगर आपको यह अनुमति चाहिए, तो कृपया एडमिन से संपर्क करें और उन्हें `/biolink आपका_यूजरआईडी` कमांड देने को कहें।",
                            quote=True
                        )
                        logger.info(f"Deleted t.me/http/https link message {message.id} from user {message.from_user.id} in chat {message.chat.id}.")
                        return # Stop further processing as message is deleted
                    except Exception as e:
                        logger.error(f"Error deleting t.me/http/https link message {message.id}: {e}")
            elif (is_sender_admin or is_biolink_exception) and contains_link(message.text) and ("t.me" in message.text or "http" in message.text or "https" in message.text):
                logger.info(f"Admin's or excepted user's t.me/http/https link message {message.id} was not deleted in chat {message.chat.id}.")


        # Username Deletion Check
        if current_group_settings and current_group_settings.get("usernamedel_enabled", False) and message.text:
            if contains_mention(message.text) and not is_sender_admin:
                try:
                    await message.delete()
                    await message.reply_text("टच-टच! 😬 आपने `@` का इस्तेमाल किया! सॉरी, वो मैसेज तो चला गया आसमान में! 🚀 अगली बार से ध्यान रखना, हाँ? 😉", quote=True)
                    logger.info(f"Deleted username mention message {message.id} from user {message.from_user.id} in chat {message.chat.id}.")
                    return # Stop further processing as message is deleted
                except Exception as e:
                    logger.error(f"Error deleting username message {message.id}: {e}")
            elif contains_mention(message.text) and is_sender_admin:
                logger.info(f"Admin's username mention message {message.id} was not deleted in chat {message.chat.id}.")
    # --- END NEW CHECKS ---

    # Only store message and generate reply if it wasn't deleted by any of the above checks
    await store_message(message)

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
    logger.info("Starting Flask health check server in a separate thread... (Code by @asbhaibsr)")
    flask_thread = threading.Thread(target=run_flask_app)
    flask_thread.start()

    logger.info("Starting Pyrogram bot... (Code by @asbhaibsr)")

    app.run()

    # End of bot code. Thank you for using! Made with ❤️ by @asbhaibsr
