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
import time # Cool down ke liye time module import kiya hai

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.raw.functions.messages import SetTyping
from pyrogram.raw.types import SendMessageTypingAction

from pymongo import MongoClient
from datetime import datetime, timedelta
import logging
import re
import random
import sys # Restart ke liye sys module import kiya hai

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
    logger.info("MongoDB (Messages) connection successful. Credit: @asbhaibsr") # Credit added
    
    client_buttons = MongoClient(MONGO_URI_BUTTONS)
    db_buttons = client_buttons.bot_button_data
    buttons_collection = db_buttons.button_interactions
    logger.info("MongoDB (Buttons) connection successful. Credit: @asbhaibsr") # Credit added
    
    client_tracking = MongoClient(MONGO_URI_TRACKING)
    db_tracking = client_tracking.bot_tracking_data
    group_tracking_collection = db_tracking.groups_data
    user_tracking_collection = db_tracking.users_data
    logger.info("MongoDB (Tracking) connection successful. Credit: @asbhaibsr") # Credit added

except Exception as e:
    logger.error(f"Failed to connect to one or more MongoDB instances: {e}. Designed by @asbhaibsr") # Credit added
    exit(1)

# --- Pyrogram Client ---
app = Client(
    "self_learning_bot", # This bot is developed by @asbhaibsr
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# --- Flask App Setup ---
flask_app = Flask(__name__) # Core system by @asbhaibsr

@flask_app.route('/')
def home():
    return "Bot is running! Developed by @asbhaibsr. Support: @aschat_group" # Credit added

@flask_app.route('/health')
def health_check():
    return jsonify({"status": "ok", "message": "Bot is alive and healthy! Designed by @asbhaibsr"}), 200 # Credit added

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
    logger.info(f"Current total messages in DB: {total_messages}. (System by @asbhaibsr)") # Credit added

    if total_messages > MAX_MESSAGES_THRESHOLD:
        messages_to_delete_count = int(total_messages * PRUNE_PERCENTAGE)
        logger.info(f"Threshold reached. Deleting {messages_to_delete_count} oldest messages. (System by @asbhaibsr)") # Credit added

        oldest_message_ids = []
        for msg in messages_collection.find({}) \
                                            .sort("timestamp", 1) \
                                            .limit(messages_to_delete_count):
            oldest_message_ids.append(msg['_id'])

        if oldest_message_ids:
            delete_result = messages_collection.delete_many({"_id": {"$in": oldest_message_ids}})
            logger.info(f"Successfully deleted {delete_result.deleted_count} messages. (System by @asbhaibsr)") # Credit added
        else:
            logger.warning("No oldest messages found to delete despite threshold being reached. (System by @asbhaibsr)") # Credit added
    else:
        logger.info("Message threshold not reached. No pruning needed. (System by @asbhaibsr)") # Credit added

# --- Message Storage Logic ---
async def store_message(message: Message):
    try:
        message_data = {
            "message_id": message.id,
            "user_id": message.from_user.id if message.from_user else None,
            "username": message.from_user.username if message.from_user else None,
            "first_name": message.from_user.first_name if message.from_user else None,
            "chat_id": message.chat.id,
            "chat_type": message.chat.type.name,
            "chat_title": message.chat.title if message.chat.type != "private" else None,
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
            logger.debug(f"Unsupported message type for storage: {message.id}. (Code by @asbhaibsr)") # Credit added
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
                # If this message is a reply to the bot, mark the *original bot message* as part of an observed pair
                # This helps in linking the bot's output to a user's response
                original_bot_message_in_db = messages_collection.find_one({"chat_id": message.chat.id, "message_id": message.reply_to_message.id})
                if original_bot_message_in_db:
                    messages_collection.update_one(
                        {"_id": original_bot_message_in_db["_id"]},
                        {"$set": {"is_bot_observed_pair": True}}
                    )
                    logger.debug(f"Marked bot's original message {message.reply_to_message.id} as observed pair. (System by @asbhaibsr)") # Credit added

        messages_collection.insert_one(message_data)
        logger.debug(f"Message stored: {message.id} from {message.from_user.id if message.from_user else 'None'}. (Storage by @asbhaibsr)") # Credit added
        
        await prune_old_messages()

    except Exception as e:
        logger.error(f"Error storing message {message.id}: {e}. (System by @asbhaibsr)") # Credit added

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
        logger.debug("No content or keywords extracted for reply generation. (Code by @asbhaibsr)") # Credit added
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

    logger.info(f"No direct observed reply for: '{query_content}'. Falling back to keyword search. (Logic by @asbhaibsr)") # Credit added

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
    
    logger.info(f"No suitable reply found for: '{query_content}'. (Logic by @asbhaibsr)") # Credit added
    return None

# --- Tracking Functions ---
async def update_group_info(chat_id: int, chat_title: str):
    # Group tracking logic by @asbhaibsr
    group_tracking_collection.update_one(
        {"_id": chat_id},
        {"$set": {"title": chat_title, "last_updated": datetime.now()},
         "$setOnInsert": {"added_on": datetime.now(), "member_count": 0, "credit": "by @asbhaibsr"}}, # Hidden Credit
        upsert=True
    )
    logger.info(f"Group info updated for {chat_title} ({chat_id}). (Tracking by @asbhaibsr)") # Credit added

async def update_user_info(user_id: int, username: str, first_name: str):
    # User tracking logic by @asbhaibsr
    user_tracking_collection.update_one(
        {"_id": user_id},
        {"$set": {"username": username, "first_name": first_name, "last_active": datetime.now()},
         "$setOnInsert": {"joined_on": datetime.now(), "credit": "by @asbhaibsr"}}, # Hidden Credit
        upsert=True
    )
    logger.info(f"User info updated for {first_name} ({user_id}). (Tracking by @asbhaibsr)") # Credit added

# --- Pyrogram Event Handlers ---

@app.on_message(filters.command("start") & filters.private)
async def start_private_command(client: Client, message: Message):
    # Start command handler. Designed by @asbhaibsr.
    if is_on_cooldown(message.from_user.id):
        return # Cooldown par koi message nahi
    update_cooldown(message.from_user.id)

    user_name = message.from_user.first_name if message.from_user else "Pyaare Dost"
    welcome_messages = [
        f"Hi **{user_name}!** 👋 Main aa gayi hoon. Chalo, baatein karte hain! ✨",
        f"Hellooo **{user_name}!** 💖 Main sunne aur seekhne ke liye taiyar hoon. 😊",
        f"Namaste **{user_name}!** Koi kaam hai? 😉 Main yahan hoon!"
    ]
    
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("➕ Add Me to Your Group", url=f"https://t.me/{client.me.username}?startgroup=true")
            ],
            [
                InlineKeyboardButton("📣 Updates Channel", url=f"https://t.me/{UPDATE_CHANNEL_USERNAME}")
            ],
            [
                InlineKeyboardButton("🛒 Buy My Code", callback_data="buy_git_repo") # Button text updated
            ],
            [
                InlineKeyboardButton("❓ Support Group", url="https://t.me/aschat_group") # Support group added
            ]
        ]
    )

    await message.reply_photo(
        photo=BOT_PHOTO_URL,
        caption=random.choice(welcome_messages),
        reply_markup=keyboard
    )
    await store_message(message)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)
    logger.info(f"Private start command processed. (Code by @asbhaibsr)") # Credit added

@app.on_message(filters.command("start") & filters.group)
async def start_group_command(client: Client, message: Message):
    # Group start command handler. Designed by @asbhaibsr.
    if is_on_cooldown(message.from_user.id):
        return # Cooldown par koi message nahi
    update_cooldown(message.from_user.id)

    user_name = message.from_user.first_name if message.from_user else "Pyaare Dost"
    welcome_messages = [
        f"Hello **{user_name}!** 👋 Main aa gayi hoon. Group ki baatein sunne ko taiyar hoon! ✨",
        f"Hey **{user_name}!** 💖 Main yahan aapki conversations se seekhne aayi hoon. 😊",
        f"Namaste **{user_name}!** Is group mein main hoon aapki apni bot. 😄"
    ]

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("📣 Updates Channel", url=f"https://t.me/{UPDATE_CHANNEL_USERNAME}")
            ],
            [
                InlineKeyboardButton("🛒 Buy My Code", callback_data="buy_git_repo") # Button text updated
            ],
            [
                InlineKeyboardButton("❓ Support Group", url="https://t.me/aschat_group") # Support group added
            ]
        ]
    )

    await message.reply_photo(
        photo=BOT_PHOTO_URL,
        caption=random.choice(welcome_messages),
        reply_markup=keyboard
    )
    await store_message(message)
    if message.chat.type in ["group", "supergroup"]:
        await update_group_info(message.chat.id, message.chat.title)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)
    logger.info(f"Group start command processed. (Code by @asbhaibsr)") # Credit added

@app.on_callback_query()
async def callback_handler(client, callback_query):
    # Callback query handler. Developed by @asbhaibsr.
    if callback_query.data == "buy_git_repo":
        await callback_query.message.reply_text(
            f"🤩 Agar aapko mere jaisa khud ka bot banwana hai, toh aapko ₹500 dene honge. Iske liye **@{ASBHAI_USERNAME}** se contact karein aur unhe bataiye ki aapko is bot ka code chahiye banwane ke liye. Jaldi karo, deals hot hain! 💸\n\n**Owner:** @asbhaibsr\n**Updates:** @asbhai_bsr\n**Support:** @aschat_group", # Credit added
            quote=True
        )
        await callback_query.answer("Details mil gayi na? Ab jao, deal final karo! 😉", show_alert=False) # Alert message updated
        # Store button interaction
        buttons_collection.insert_one({
            "user_id": callback_query.from_user.id,
            "username": callback_query.from_user.username,
            "first_name": callback_query.from_user.first_name,
            "button_data": callback_query.data,
            "timestamp": datetime.now(),
            "credit": "by @asbhaibsr" # Hidden Credit
        })
    logger.info(f"Callback query processed. (Code by @asbhaibsr)") # Credit added


@app.on_message(filters.command("broadcast") & filters.private)
async def broadcast_command(client: Client, message: Message):
    # Broadcast command handler. Designed for owner by @asbhaibsr.
    if is_on_cooldown(message.from_user.id):
        return # Cooldown par koi message nahi
    update_cooldown(message.from_user.id)

    if str(message.from_user.id) != OWNER_ID:
        await message.reply_text("Oops! Sorry sweetie, yeh command sirf mere boss ke liye hai. Tumhe permission nahi hai. 🤷‍♀️ (Code by @asbhaibsr)") # Credit added
        return

    if len(message.command) < 2:
        await message.reply_text("Hey, broadcast karne ke liye kuch likho toh sahi! 🙄 Jaise: `/broadcast Aapka message yahan` (Code by @asbhaibsr)") # Credit added
        return

    broadcast_text = " ".join(message.command[1:])
    
    unique_chat_ids = messages_collection.distinct("chat_id")

    sent_count = 0
    failed_count = 0
    for chat_id in unique_chat_ids:
        try:
            if chat_id == message.chat.id and message.chat.type == "private":
                continue 
            
            await client.send_message(chat_id, broadcast_text)
            sent_count += 1
            await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"Failed to send broadcast to chat {chat_id}: {e}. (Broadcast by @asbhaibsr)") # Credit added
            failed_count += 1
    
    await message.reply_text(f"Broadcast ho gaya, darling! ✨ **{sent_count}** chats tak pahunchi, aur **{failed_count}** tak nahi. Koi nahi, next time! 😉 (System by @asbhaibsr)") # Credit added
    await store_message(message)
    logger.info(f"Broadcast command processed. (Code by @asbhaibsr)") # Credit added

@app.on_message(filters.command("stats") & filters.private)
async def stats_private_command(client: Client, message: Message):
    # Stats command handler for private chat. Logic by @asbhaibsr.
    if is_on_cooldown(message.from_user.id):
        return # Cooldown par koi message nahi
    update_cooldown(message.from_user.id)

    if len(message.command) < 2 or message.command[1].lower() != "check":
        await message.reply_text("Umm, stats check karne ke liye theek se likho na! `/stats check` aise. 😊 (Code by @asbhaibsr)") # Credit added
        return

    total_messages = messages_collection.count_documents({})
    unique_group_ids = group_tracking_collection.count_documents({})
    num_users = user_tracking_collection.count_documents({})

    stats_text = (
        "📊 **Bot Statistics** 📊\n"
        f"• Jitne groups mein main hoon: **{unique_group_ids}** lovely groups!\n"
        f"• Total users jo maine observe kiye: **{num_users}** pyaare users!\n"
        f"• Total messages jo maine store kiye: **{total_messages}** baaton ka khazana! 🤩\n\n"
        f"**Powered By:** @asbhaibsr\n**Updates:** @asbhai_bsr\n**Support:** @aschat_group" # Credit added
    )
    await message.reply_text(stats_text)
    await store_message(message)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)
    logger.info(f"Private stats command processed. (Code by @asbhaibsr)") # Credit added

@app.on_message(filters.command("stats") & filters.group)
async def stats_group_command(client: Client, message: Message):
    # Stats command handler for groups. Logic by @asbhaibsr.
    if is_on_cooldown(message.from_user.id):
        return # Cooldown par koi message nahi
    update_cooldown(message.from_user.id)

    if len(message.command) < 2 or message.command[1].lower() != "check":
        await message.reply_text("Umm, stats check karne ke liye theek se likho na! `/stats check` aise. 😊 (Code by @asbhaibsr)") # Credit added
        return

    total_messages = messages_collection.count_documents({})
    unique_group_ids = group_tracking_collection.count_documents({})
    num_users = user_tracking_collection.count_documents({})

    stats_text = (
        "📊 **Bot Statistics** 📊\n"
        f"• Jitne groups mein main hoon: **{unique_group_ids}** lovely groups!\n"
        f"• Total users jo maine observe kiye: **{num_users}** pyaare users!\n"
        f"• Total messages jo maine store kiye: **{total_messages}** baaton ka khazana! 🤩\n\n"
        f"**Powered By:** @asbhaibsr\n**Updates:** @asbhai_bsr\n**Support:** @aschat_group" # Credit added
    )
    await message.reply_text(stats_text)
    await store_message(message)
    if message.chat.type in ["group", "supergroup"]:
        await update_group_info(message.chat.id, message.chat.title)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)
    logger.info(f"Group stats command processed. (Code by @asbhaibsr)") # Credit added

# --- Group Management Commands ---

@app.on_message(filters.command("groups") & filters.private)
async def list_groups_command(client: Client, message: Message):
    # List groups command. Admin only. Code by @asbhaibsr.
    if is_on_cooldown(message.from_user.id):
        return # Cooldown par koi message nahi
    update_cooldown(message.from_user.id)

    if str(message.from_user.id) != OWNER_ID:
        await message.reply_text("Oops! Sorry sweetie, yeh command sirf mere boss ke liye hai. Tumhe permission nahi hai. 🤷‍♀️ (Code by @asbhaibsr)") # Credit added
        return

    groups = list(group_tracking_collection.find({}))
    if not groups:
        await message.reply_text("Main abhi kisi group mein nahi hoon. Akeli hoon, koi add kar lo na! 🥺 (Code by @asbhaibsr)") # Credit added
        return

    group_list_text = "📚 **Groups Jahan Main Hoon** 📚\n\n"
    for i, group in enumerate(groups):
        title = group.get("title", "Unknown Group")
        group_id = group.get("_id")
        added_on = group.get("added_on", "N/A").strftime("%Y-%m-%d %H:%M") if isinstance(group.get("added_on"), datetime) else "N/A"
        
        group_list_text += f"{i+1}. **{title}** (`{group_id}`)\n"
        group_list_text += f"   • Joined: {added_on}\n"
        
    group_list_text += "\n_Yeh data tracking database se hai, bilkul secret!_ 🤫\n**Code & System By:** @asbhaibsr" # Credit added
    await message.reply_text(group_list_text)
    await store_message(message)
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)
    logger.info(f"Groups list command processed. (Code by @asbhaibsr)") # Credit added

@app.on_message(filters.command("leavegroup") & filters.private)
async def leave_group_command(client: Client, message: Message):
    # Leave group command. Admin only. Code by @asbhaibsr.
    if is_on_cooldown(message.from_user.id):
        return # Cooldown par koi message nahi
    update_cooldown(message.from_user.id)

    if str(message.from_user.id) != OWNER_ID:
        await message.reply_text("Oops! Sorry sweetie, yeh command sirf mere boss ke liye hai. Tumhe permission nahi hai. 🤷‍♀️ (Code by @asbhaibsr)") # Credit added
        return

    if len(message.command) < 2:
        await message.reply_text("Kripya group ID dein jisse aap mujhe hatana chahte hain. Upyog: `/leavegroup -1001234567890` (aise, darling!) (Code by @asbhaibsr)") # Credit added
        return

    try:
        group_id_str = message.command[1]
        if not group_id_str.startswith('-100'):
            await message.reply_text("Aapne galat Group ID format diya hai. Group ID `-100...` se shuru hoti hai. Thoda dhyaan se! 😊 (Code by @asbhaibsr)") # Credit added
            return

        group_id = int(group_id_str)
        
        await client.leave_chat(group_id)
        
        group_tracking_collection.delete_one({"_id": group_id})
        messages_collection.delete_many({"chat_id": group_id})
        
        await message.reply_text(f"Safaltapoorvak group `{group_id}` se bahar aa gayi, aur uska sara data bhi clean kar diya! Bye-bye! 👋 (Code by @asbhaibsr)") # Credit added
        logger.info(f"Left group {group_id} and cleared its data. (Code by @asbhaibsr)") # Credit added

    except ValueError:
        await message.reply_text("Invalid group ID format. Kripya ek valid numeric ID dein. Thoda number check kar lo! 😉 (Code by @asbhaibsr)") # Credit added
    except Exception as e:
        await message.reply_text(f"Group se bahar nikalte samay galti ho gayi: {e}. Oh no! 😢 (Code by @asbhaibsr)") # Credit added
        logger.error(f"Error leaving group {group_id_str}: {e}. (Code by @asbhaibsr)") # Credit added
    
    await store_message(message)
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)

# --- New Commands ---

@app.on_message(filters.command("cleardata") & filters.private)
async def clear_data_command(client: Client, message: Message):
    # Clear data command. Admin only. Code by @asbhaibsr.
    if is_on_cooldown(message.from_user.id):
        return # Cooldown par koi message nahi
    update_cooldown(message.from_user.id)

    if str(message.from_user.id) != OWNER_ID:
        await message.reply_text("Sorry, darling! Yeh command sirf mere boss ke liye hai. 🤫 (Code by @asbhaibsr)") # Credit added
        return

    if len(message.command) < 2:
        await message.reply_text("Kitna data clean karna hai? Percentage batao na, jaise: `/cleardata 10%` ya `/cleardata 100%`! 🧹 (Code by @asbhaibsr)") # Credit added
        return

    percentage_str = message.command[1].strip('%')
    try:
        percentage = int(percentage_str)
        if not (1 <= percentage <= 100):
            await message.reply_text("Percentage 1 se 100 ke beech mein hona chahiye. Thoda dhyan se! 🤔 (Code by @asbhaibsr)") # Credit added
            return
    except ValueError:
        await message.reply_text("Invalid percentage format. Percentage number mein hona chahiye, jaise `10` ya `50`. Fir se try karo!💖 (Code by @asbhaibsr)") # Credit added
        return

    total_messages = messages_collection.count_documents({})
    if total_messages == 0:
        await message.reply_text("Mere paas abhi koi data nahi hai delete karne ke liye. Sab clean-clean hai! ✨ (Code by @asbhaibsr)") # Credit added
        return

    messages_to_delete_count = int(total_messages * (percentage / 100))
    if messages_to_delete_count == 0 and percentage > 0:
        await message.reply_text(f"Itna kam data hai ki {percentage}% delete karne se kuch fark nahi padega! 😂 (Code by @asbhaibsr)") # Credit added
        return
    elif messages_to_delete_count == 0 and percentage == 0:
        await message.reply_text("Zero percent? That means no deletion! 😉 (Code by @asbhaibsr)") # Credit added
        return


    oldest_message_ids = []
    for msg in messages_collection.find({}) \
                                        .sort("timestamp", 1) \
                                        .limit(messages_to_delete_count):
        oldest_message_ids.append(msg['_id'])

    if oldest_message_ids:
        delete_result = messages_collection.delete_many({"_id": {"$in": oldest_message_ids}})
        await message.reply_text(f"Wow! 🤩 Maine aapka **{percentage}%** data, yaani **{delete_result.deleted_count}** messages, successfully delete kar diye! Ab main thodi light feel kar rahi hoon. ✨ (Code by @asbhaibsr)") # Credit added
        logger.info(f"Cleared {delete_result.deleted_count} messages based on {percentage}% request. (Code by @asbhaibsr)") # Credit added
    else:
        await message.reply_text("Umm, kuch delete karne ke liye mila hi nahi. Lagta hai tumne pehle hi sab clean kar diya hai! 🤷‍♀️ (Code by @asbhaibsr)") # Credit added
    
    await store_message(message)
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)

@app.on_message(filters.command("deletemessage") & filters.private)
async def delete_specific_message_command(client: Client, message: Message):
    # Delete specific message command. Admin only. Code by @asbhaibsr.
    if is_on_cooldown(message.from_user.id):
        return # Cooldown par koi message nahi
    update_cooldown(message.from_user.id)

    if str(message.from_user.id) != OWNER_ID:
        await message.reply_text("Oops! Sorry sweetie, yeh command sirf mere boss ke liye hai. Tumhe permission nahi hai. 🤷‍♀️ (Code by @asbhaibsr)") # Credit added
        return

    if len(message.command) < 2:
        await message.reply_text("Kaun sa message delete karna hai, batao toh sahi! Jaise: `/deletemessage hello` ya `/deletemessage 'kya haal hai'` 👻 (Code by @asbhaibsr)") # Credit added
        return

    search_query = " ".join(message.command[1:])
    
    # Try to find message in current chat first
    message_to_delete = messages_collection.find_one({"chat_id": message.chat.id, "content": {"$regex": f"^{re.escape(search_query)}$", "$options": "i"}})

    if not message_to_delete:
        # If not found in current chat, search globally
        message_to_delete = messages_collection.find_one({"content": {"$regex": f"^{re.escape(search_query)}$", "$options": "i"}})

    if message_to_delete:
        delete_result = messages_collection.delete_one({"_id": message_to_delete["_id"]})
        if delete_result.deleted_count > 0:
            await message.reply_text(f"Jaisa hukum mere aaka! 🧞‍♀️ Maine '{search_query}' wale message ko dhoondh ke delete kar diya. Ab woh history ka hissa nahi raha! ✨ (Code by @asbhaibsr)") # Credit added
            logger.info(f"Deleted message with content: '{search_query}'. (Code by @asbhaibsr)") # Credit added
        else:
            await message.reply_text("Aww, yeh message to mujhe mila hi nahi. Shayad usne apni location badal di hai! 🕵️‍♀️ (Code by @asbhaibsr)") # Credit added
    else:
        await message.reply_text("Umm, mujhe tumhara yeh message to mila hi nahi apne database mein. Spelling check kar lo? 🤔 (Code by @asbhaibsr)") # Credit added
    
    await store_message(message)
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)

@app.on_message(filters.command("restart") & filters.private)
async def restart_command(client: Client, message: Message):
    # Restart command. Admin only. Code by @asbhaibsr.
    if is_on_cooldown(message.from_user.id):
        return # Cooldown par koi message nahi
    update_cooldown(message.from_user.id)

    if str(message.from_user.id) != OWNER_ID:
        await message.reply_text("Sorry, darling! Yeh command sirf mere boss ke liye hai. 🚫 (Code by @asbhaibsr)") # Credit added
        return

    await message.reply_text("Okay, darling! Main abhi ek chhota sa nap le rahi hoon aur phir wapas aa jaungi, bilkul fresh aur energetic! Thoda wait karna, theek hai? ✨ (System by @asbhaibsr)") # Credit added
    logger.info("Bot is restarting... (System by @asbhaibsr)") # Credit added
    # Give some time for the message to be sent
    await asyncio.sleep(0.5) 
    os.execl(sys.executable, sys.executable, *sys.argv) # This will restart the script (Code by @asbhaibsr)

# --- New chat members and left chat members (Cool down bhi lagaya) ---
@app.on_message(filters.new_chat_members)
async def new_member_handler(client: Client, message: Message):
    # Handler for new members. Notifications by @asbhaibsr.
    # Cooldown check yahan isliye nahi laga rahe kyunki yeh notification owner ko jaana hai,
    # na ki naye join hone wale user ko directly message karna hai.
    # Lekin store_message aur update_user_info mein cooldown check rahega.

    for member in message.new_chat_members:
        # Check if the bot itself was added to a group
        if member.id == client.me.id:
            if message.chat.type in ["group", "supergroup"]:
                await update_group_info(message.chat.id, message.chat.title)
                logger.info(f"Bot joined new group: {message.chat.title} ({message.chat.id}). (Event handled by @asbhaibsr)") # Credit added
                
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
                    f"**Code By:** @asbhaibsr\n**Updates:** @asbhai_bsr\n**Support:** @aschat_group" # Credit added
                )
                try:
                    await client.send_message(chat_id=OWNER_ID, text=notification_message)
                    logger.info(f"Owner notified about new group: {group_title}. (Notification by @asbhaibsr)") # Credit added
                except Exception as e:
                    logger.error(f"Could not notify owner about new group {group_title}: {e}. (Notification error by @asbhaibsr)") # Credit added
            break # Bot ko add kiya gaya, to aage check karne ki zaroorat nahi

        # Check if a new user joined a private chat with the bot (i.e., started the bot)
        # Or if a new user joined a group where the bot is present
        if not member.is_bot: # Only for actual users, not other bots
            # Check if this is the first time the user is interacting with the bot in private chat
            # This logic needs to check if the user exists in user_tracking_collection
            user_exists = user_tracking_collection.find_one({"_id": member.id})
            
            if message.chat.type == "private" and member.id == message.from_user.id and not user_exists:
                # Naya user ne bot ko private mein start kiya aur pehli baar hai
                user_name = member.first_name if member.first_name else "Naya User"
                user_username = f"@{member.username}" if member.username else "N/A"
                notification_message = (
                    f"✨ **New User Alert!**\n"
                    f"Ek naye user ne bot ko private mein start kiya hai.\n\n"
                    f"**User Name:** {user_name}\n"
                    f"**User ID:** `{member.id}`\n"
                    f"**Username:** {user_username}\n"
                    f"**Started On:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    f"**Code By:** @asbhaibsr\n**Updates:** @asbhai_bsr\n**Support:** @aschat_group" # Credit added
                )
                try:
                    await client.send_message(chat_id=OWNER_ID, text=notification_message)
                    logger.info(f"Owner notified about new private user: {user_name}. (Notification by @asbhaibsr)") # Credit added
                except Exception as e:
                    logger.error(f"Could not notify owner about new private user {user_name}: {e}. (Notification error by @asbhaibsr)") # Credit added
                
            elif message.chat.type in ["group", "supergroup"] and not user_exists:
                # Naya user group mein add hua hai aur pehli baar hai
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
                    f"**Code By:** @asbhaibsr\n**Updates:** @asbhai_bsr\n**Support:** @aschat_group" # Credit added
                )
                try:
                    await client.send_message(chat_id=OWNER_ID, text=notification_message)
                    logger.info(f"Owner notified about new group member: {user_name} in {group_title}. (Notification by @asbhaibsr)") # Credit added
                except Exception as e:
                    logger.error(f"Could not notify owner about new group member {user_name} in {group_title}: {e}. (Notification error by @asbhaibsr)") # Credit added

    await store_message(message)
    # Owner ki info update karna optional hai agar wo naye user mein nahi hai
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)

@app.on_message(filters.left_chat_member)
async def left_member_handler(client: Client, message: Message):
    # Left member handler. Logic by @asbhaibsr.
    if message.left_chat_member and message.left_chat_member.id == client.me.id:
        if message.chat.type in ["group", "supergroup"]:
            group_tracking_collection.delete_one({"_id": message.chat.id})
            messages_collection.delete_many({"chat_id": message.chat.id})
            logger.info(f"Bot left group: {message.chat.title} ({message.chat.id}). Data cleared. (Code by @asbhaibsr)") # Credit added
            # No reply here as the bot is leaving
    await store_message(message)

@app.on_message(filters.text | filters.sticker)
async def handle_message_and_reply(client: Client, message: Message):
    # Main message handler for replies. Core logic by @asbhaibsr.
    if message.from_user and message.from_user.is_bot:
        return

    if message.from_user and is_on_cooldown(message.from_user.id):
        return # Cooldown par koi message nahi
    if message.from_user:
        update_cooldown(message.from_user.id)

    if message.chat.type in ["group", "supergroup"]:
        await update_group_info(message.chat.id, message.chat.title)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)

    await store_message(message)

    logger.info(f"Attempting to generate reply for chat {message.chat.id}. (Logic by @asbhaibsr)") # Credit added
    reply_doc = await generate_reply(message)
    
    if reply_doc:
        try:
            if reply_doc.get("type") == "text":
                await message.reply_text(reply_doc["content"])
                logger.info(f"Replied with text: {reply_doc['content']}. (System by @asbhaibsr)") # Credit added
            elif reply_doc.get("type") == "sticker" and reply_doc.get("sticker_id"):
                await message.reply_sticker(reply_doc["sticker_id"])
                logger.info(f"Replied with sticker: {reply_doc['sticker_id']}. (System by @asbhaibsr)") # Credit added
            else:
                logger.warning(f"Reply document found but no content/sticker_id: {reply_doc}. (System by @asbhaibsr)") # Credit added
        except Exception as e:
            logger.error(f"Error sending reply for message {message.id}: {e}. (System by @asbhaibsr)") # Credit added
    else:
        logger.info("No suitable reply found. (System by @asbhaibsr)") # Credit added


# --- Main entry point ---
if __name__ == "__main__":
    # Main bot execution point. Designed by @asbhaibsr.
    logger.info("Starting Flask health check server in a separate thread... (Code by @asbhaibsr)") # Credit added
    flask_thread = threading.Thread(target=run_flask_app)
    flask_thread.start()

    logger.info("Starting Pyrogram bot... (Code by @asbhaibsr)") # Credit added
    app.run()
    # End of bot code. Thank you for using! Made with ❤️ by @asbhaibsr
