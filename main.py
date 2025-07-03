# Credit by @asbhaibsr and Telegram Channel @asbhai_bsr

import os
import asyncio
import re
import random
import logging
from datetime import datetime, timedelta
from threading import Thread

# Pyrogram imports
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ForceReply
from pyrogram.raw.functions.messages import SetTyping
from pyrogram.raw.types import SendMessageTypingAction
from pyrogram.errors import exceptions # CHANGED THIS LINE: Import the exceptions module

# MongoDB imports
from pymongo import MongoClient

# Flask imports for web server
from flask import Flask, jsonify

# --- Logger Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Environment Variables ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
# MONGO_DB_URI will be used for the main messages_collection (learning data)
MAIN_MONGO_DB_URI = os.getenv("MONGO_DB_URI") # This one comes from Koyeb Environment Variable
OWNER_ID = os.getenv("OWNER_ID") # Owner's user ID (string format)

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

# --- Hardcoded MongoDB URIs (DANGER: NOT RECOMMENDED FOR PRODUCTION) ---
# WARNING: Storing sensitive data like this directly in code is a SECURITY RISK.
# It is HIGHLY RECOMMENDED to use Environment Variables for these as well.

# MongoDB URI for Clone Requests and User States (as per your request)
CLONE_AND_STATE_MONGO_DB_URI = "mongodb+srv://wtqf35lojv:9uhGrKZE4i0zz05x@cluster0.nmtfsys.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# MongoDB URI for Commands and Button related settings (e.g., group configs, as per your request)
COMMANDS_AND_BUTTONS_MONGO_DB_URI = "mongodb+srv://rogola2721:LGbRLbhopZl8labG@cluster0.urfp3iw.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# ----------------------------------------------------------------------------------

# --- Constants ---
MAX_MESSAGES_THRESHOLD = 100000 
PRUNE_PERCENTAGE = 0.30          
DEFAULT_UPDATE_CHANNEL_USERNAME = "asbhai_bsr" # Default update channel for cloned bots

# --- Payment Details ---
PAYMENT_INFO = {
    "amount": "200",
    "upi_id": "arsadsaifi8272@ibl", # YOUR UPDATED UPI ID
    "qr_code_url": "YOUR_QR_CODE_IMAGE_URL_URL_HERE", # <-- Replace with a link to your QR code image
    "instructions": "UPI ID par ₹200 bhejien aur payment ka screenshot 'Screenshot Bhejein' button par click karke bhejen."
}

# --- MongoDB Setup for all three connections ---
# Connection 1: For Bot's Learning Messages (from Environment Variable)
try:
    main_mongo_client = MongoClient(MAIN_MONGO_DB_URI)
    main_db = main_mongo_client.bot_learning_database 
    messages_collection = main_db.messages
    logger.info("MongoDB (Main Learning DB) connection successful.")
except Exception as e:
    logger.error(f"Failed to connect to Main Learning MongoDB: {e}")
    exit(1)

# Connection 2: For Clone Requests and User States (hardcoded)
try:
    clone_state_mongo_client = MongoClient(CLONE_AND_STATE_MONGO_DB_URI)
    clone_state_db = clone_state_mongo_client.bot_clone_states_db
    user_states_collection = clone_state_db.user_states
    logger.info("MongoDB (Clone/State DB) connection successful.")
except Exception as e:
    logger.error(f"Failed to connect to Clone/State MongoDB: {e}")
    exit(1)

# Connection 3: For Commands and Button related settings (hardcoded)
try:
    commands_settings_mongo_client = MongoClient(COMMANDS_AND_BUTTONS_MONGO_DB_URI)
    commands_settings_db = commands_settings_mongo_client.bot_settings_db
    group_configs_collection = commands_settings_db.group_configs
    logger.info("MongoDB (Commands/Settings DB) connection successful.")
except Exception as e:
    logger.error(f"Failed to connect to Commands/Settings MongoDB: {e}")
    exit(1)

# --- Pyrogram Client ---
app = Client( 
    "self_learning_bot", 
    api_id=API_ID,       
    api_hash=API_HASH,   
    bot_token=BOT_TOKEN
)

# --- Utility Functions (unchanged from previous version, just using correct collections) ---

def extract_keywords(text):
    if not text: return []
    words = re.findall(r'\b\w+\b', text.lower())
    return list(set(words))

async def prune_old_messages():
    total_messages = messages_collection.count_documents({})
    logger.info(f"Current total messages in DB: {total_messages}")
    if total_messages > MAX_MESSAGES_THRESHOLD:
        messages_to_delete_count = int(total_messages * PRUNE_PERCENTAGE)
        logger.info(f"Threshold reached. Deleting {messages_to_delete_count} oldest messages.")
        oldest_message_ids = []
        for msg in messages_collection.find({}).sort("timestamp", 1).limit(messages_to_delete_count):
            oldest_message_ids.append(msg['_id'])
        if oldest_message_ids:
            delete_result = messages_collection.delete_many({"_id": {"$in": oldest_message_ids}})
            logger.info(f"Successfully deleted {delete_result.deleted_count} messages.")
        else:
            logger.warning("No oldest messages found to delete despite threshold being reached.")
    else:
        logger.info("Message threshold not reached. No pruning needed.")

async def store_message(message: Message, is_bot_sent: bool = False, sent_message_id: int = None):
    try:
        if message.from_user and message.from_user.is_bot and not is_bot_sent:
            return

        message_data = {
            "message_id": message.id,
            "user_id": message.from_user.id if message.from_user else None,
            "username": message.from_user.username if message.from_user else None,
            "first_name": message.from_user.first_name if message.from_user else None,
            "chat_id": message.chat.id,
            "chat_type": message.chat.type.name,
            "chat_title": message.chat.title if message.chat.type != "private" else None,
            "timestamp": datetime.now(),
            "is_bot_sent": is_bot_sent,
            "content_type": "text" if message.text else ("sticker" if message.sticker else "other"),
            "content": message.text if message.text else (message.sticker.emoji if message.sticker else ""),
            "sticker_id": message.sticker.file_id if message.sticker else None,
            "keywords": extract_keywords(message.text) if message.text else extract_keywords(message.sticker.emoji if message.sticker else ""),
            "replied_to_message_id": message.reply_to_message.id if message.reply_to_message else None,
            "replied_to_user_id": message.reply_to_message.from_user.id if message.reply_to_message and message.reply_to_message.from_user else None,
            "replied_to_content": message.reply_to_message.text if message.reply_to_message and message.reply_to_message.text else (message.reply_to_message.sticker.emoji if message.reply_to_message and message.reply_to_message.sticker else None),
            "is_bot_observed_pair": False,
        }
        
        if message.reply_to_message and message.reply_to_message.from_user and message.reply_to_message.from_user.is_self:
            message_data["is_bot_observed_pair"] = True
            logger.debug(f"Observed user reply to bot's message: {message.reply_to_message.id}")
            messages_collection.update_one(
                {"chat_id": message.chat.id, "message_id": message.reply_to_message.id, "is_bot_sent": True},
                {"$set": {"is_bot_observed_pair": True}}
            )

        messages_collection.insert_one(message_data)
        logger.debug(f"Message stored: {message.id} from {message.from_user.id if message.from_user else 'None'}. Bot sent: {is_bot_sent}")
        await prune_old_messages()
    except Exception as e:
        logger.error(f"Error storing message {message.id}: {e}", exc_info=True)

async def generate_reply(message: Message):
    await app.invoke(SetTyping(peer=await app.resolve_peer(message.chat.id), action=SendMessageTypingAction()))
    await asyncio.sleep(0.5)

    query_content = message.text if message.text else (message.sticker.emoji if message.sticker else "")
    query_keywords = extract_keywords(query_content)

    if not query_keywords and not query_content:
        logger.debug("No content or keywords extracted for reply generation.")
        return None

    # --- Strategy 1: Direct observed reply (User-to-User, or Bot-to-User) ---
    if message.reply_to_message:
        replied_to_content = message.reply_to_message.text if message.reply_to_message.text else (message.reply_to_message.sticker.emoji if message.reply_to_message.sticker else "")
        if replied_to_content:
            logger.info(f"Searching for observed replies to: '{replied_to_content}'")
            observed_replies_cursor = messages_collection.find({
                "replied_to_content": {"$regex": f"^{re.escape(replied_to_content)}$", "$options": "i"},
                "is_bot_observed_pair": True,
                "chat_id": message.chat.id 
            })
            potential_replies = list(observed_replies_cursor)
            if potential_replies:
                logger.info(f"Found {len(potential_replies)} contextual replies based on direct reply.")
                return random.choice(potential_replies)
            else:
                observed_replies_cursor = messages_collection.find({
                    "replied_to_content": {"$regex": f"^{re.escape(replied_to_content)}$", "$options": "i"},
                    "is_bot_observed_pair": True
                })
                potential_replies = list(observed_replies_cursor)
                if potential_replies:
                    logger.info(f"Found {len(potential_replies)} global contextual replies based on direct reply.")
                    return random.choice(potential_replies)

    # --- Strategy 2: Keyword-based general reply ---
    logger.info(f"No direct contextual reply. Falling back to keyword search for: '{query_content}'")
    keyword_regex = "|".join([re.escape(kw) for kw in query_keywords])
    
    general_replies_group_cursor = messages_collection.find({
        "chat_id": message.chat.id, 
        "content_type": {"$in": ["text", "sticker"]},
        "content": {"$regex": f".*({keyword_regex}).*", "$options": "i"} if keyword_regex else {"$exists": True}
    })
    potential_replies = list(general_replies_group_cursor)

    if not potential_replies:
        general_replies_global_cursor = messages_collection.find({
            "content_type": {"$in": ["text", "sticker"]},
            "content": {"$regex": f".*({keyword_regex}).*", "$options": "i"} if keyword_regex else {"$exists": True}
        })
        potential_replies = list(general_replies_global_cursor)

    if potential_replies:
        logger.info(f"Found {len(potential_replies)} general keyword-based replies.")
        if len(potential_replies) > 1: 
            filtered_replies = [
                doc for doc in potential_replies 
                if not (doc.get("content", "").lower() == query_content.lower() and doc.get("content_type") == message.content_type)
            ]
            if filtered_replies:
                return random.choice(filtered_replies)
        return random.choice(potential_replies)
    
    logger.info(f"No general keyword reply found for: '{query_content}'.")
    
    # --- Strategy 3: Fallback generic replies ---
    fallback_messages = [
        "Hmm, main is bare mein kya kahoon?",
        "Interesting! Aur kuch?",
        "Main sun rahi hoon... 👋",
        "Aapki baat sunkar acha laga!",
        "Kya haal-chal?"
    ]
    return {"type": "text", "content": random.choice(fallback_messages)}


# --- Pyrogram Event Handlers ---

# START COMMAND (PRIVATE CHAT)
@app.on_message(filters.command("start") & filters.private)
async def start_private_command(client: Client, message: Message):
    user_name = message.from_user.first_name if message.from_user else "dost"
    welcome_message = (
        f"Hey, **{user_name}**! 👋 Main aa gayi hoon aapki baaton ka hissa banne."
        "\n\nAgar aap mujhe apne **group mein add karte hain**, toh main wahan ki conversations se seekh kar sabko aur bhi mazedaar jawab de paungi."
        "\n\nGroup mein add karke aapko milenge: "
        "\n✨ **Smart replies:** Main group members ki baaton se seekh kar unhe behtar jawab dungi."
        "\n📚 **Knowledge base:** Group ki saari conversations ko yaad rakhungi, jo baad mein kaam aa sakti hain."
        "\n\nChalo, kuch mithaas bhari baatein karte hain! 💖"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Me to Your Group", url=f"https://t.me/{client.me.username}?startgroup=true")],
        [InlineKeyboardButton("📣 Updates Channel", url=f"https://t.me/{(DEFAULT_UPDATE_CHANNEL_USERNAME)}")]
    ])
    await message.reply_text(welcome_message, reply_markup=keyboard)
    await store_message(message)

# START COMMAND (GROUP CHAT)
@app.on_message(filters.command("start") & filters.group)
async def start_group_command(client: Client, message: Message):
    welcome_messages = [
        "Hello, my lovely group! 👋 Main aa gayi hoon aapki conversations mein shamil hone. Yahan main aap sabki baaton se seekhti rahungi.",
        "Hey everyone! 💖 Main yahan aap sab ki baatein sunne aur seekhne aayi hoon. Isse main aur smart replies de paungi.",
        "Namaste to all the amazing people here! ✨ Mujhe group mein add karne ka shukriya. Main yahan ki baaton ko samjh kar aur behtar hoti jaungi."
    ]
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📣 Updates Channel", url=f"https://t.me/{(DEFAULT_UPDATE_CHANNEL_USERNAME)}")]
    ])
    await message.reply_text(random.choice(welcome_messages), reply_markup=keyboard)
    await store_message(message)

# GENERAL STATS COMMAND
@app.on_message(filters.command("stats") & (filters.private | filters.group))
async def stats_command(client: Client, message: Message):
    if len(message.command) < 2 or message.command[1].lower() != "check":
        await message.reply_text("Upyog: `/stats check`")
        return
    
    total_messages = messages_collection.count_documents({})
    unique_group_ids = messages_collection.distinct("chat_id", {"chat_type": {"$in": ["group", "supergroup"]}})
    num_groups = len(unique_group_ids)
    
    stats_text = (
        "📊 **Bot Statistics** 📊\n"
        f"• Jitne groups mein main hoon: **{num_groups}**\n"
        f"• Total messages jo maine store kiye: **{total_messages}**"
    )
    await message.reply_text(stats_text)
    await store_message(message)

# HELP COMMAND
@app.on_message(filters.command("help") & (filters.private | filters.group))
async def help_command(client: Client, message: Message):
    help_text = (
        "👋 Hi! Main ek self-learning bot hoon jo aapki baaton se seekhta hai."
        "\n\n**Commands:**"
        "\n• `/start` - Bot ko shuru kare."
        "\n• `/stats check` - Bot ke statistics dekhe."
        "\n• `/help` - Is help message ko dekhe."
        "\n• `/myid` - Apni user ID dekhe."
        "\n• `/chatid` - Current chat ki ID dekhe."
        "\n• `/clonebot` - Apna khud ka bot deploy karne ke bare mein janein (Premium Feature)."
        "\n\n**Admin Commands (Sirf Owner ke liye):**"
        "\n• `/broadcast <message>` - Sabhi chats par message bheje."
        "\n• `/resetdata <percentage>` - Database se X% purana data delete kare."
        "\n• `/deletemessage <message_id>` - Specific message ko database se hataye."
        "\n• `/ban <user_id_or_username>` - User ko group se ban kare."
        "\n• `/unban <user_id_or_username>` - User ko group se unban kare."
        "\n• `/kick <user_id_or_username>` - User ko group se kick kare."
        "\n• `/pin <message_id>` - Message ko group mein pin kare."
        "\n• `/unpin` - Sabhi pinned messages ko unpin kare."
        "\n• `/setwelcome <message>` - Group ke liye custom welcome message set kare."
        "\n• `/getwelcome` - Group ka set kiya hua welcome message dekhe."
        "\n• `/clearwelcome` - Group ka custom welcome message hataye."
        "\n\n**Note:** Admin commands ke liye bot ko group mein zaroori admin rights hone chahiye."
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Me to Your Group", url=f"https://t.me/{client.me.username}?startgroup=true")],
        [InlineKeyboardButton("📣 Updates Channel", url=f"https://t.me/{(DEFAULT_UPDATE_CHANNEL_USERNAME)}")]
    ])
    await message.reply_text(help_text, reply_markup=keyboard)
    await store_message(message)

# MYID COMMAND
@app.on_message(filters.command("myid") & (filters.private | filters.group))
async def my_id_command(client: Client, message: Message):
    user_id = message.from_user.id
    await message.reply_text(f"Tumhari user ID: `{user_id}`")
    await store_message(message)

# CHATID COMMAND
@app.on_message(filters.command("chatid") & (filters.private | filters.group))
async def chat_id_command(client: Client, message: Message):
    chat_id = message.chat.id
    await message.reply_text(f"Is chat ki ID: `{chat_id}`")
    await store_message(message)

# --- ADMIN COMMANDS ---

# Helper function to check if user is owner
def is_owner(user_id):
    return str(user_id) == OWNER_ID

# Admin check decorator
def owner_only_filter(_, __, message):
    return is_owner(message.from_user.id)

# BROADCAST COMMAND
@app.on_message(filters.command("broadcast") & filters.private & filters.create(owner_only_filter))
async def broadcast_command(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("Kripya broadcast karne ke liye ek message dein. Upyog: `/broadcast Aapka message yahan`")
        return
    broadcast_text = " ".join(message.command[1:])
    unique_chat_ids = messages_collection.distinct("chat_id")
    sent_count = 0
    failed_count = 0
    await message.reply_text("Broadcasting shuru ho raha hai...")
    for chat_id in unique_chat_ids:
        try:
            if chat_id == message.chat.id and message.chat.type == "private":
                continue
            await client.send_message(chat_id, broadcast_text)
            sent_count += 1
            await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"Failed to send broadcast to chat {chat_id}: {e}")
            failed_count += 1
    await message.reply_text(f"Broadcast poora hua! {sent_count} chats ko bheja, {failed_count} chats ke liye asafal raha.")
    await store_message(message)

# RESET DATA COMMAND
@app.on_message(filters.command("resetdata") & filters.private & filters.create(owner_only_filter))
async def reset_data_command(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("Upyog: `/resetdata <percentage>`. Percentage 1 se 100 ke beech hona chahiye.")
        return
    try:
        percentage = int(message.command[1])
        if not (1 <= percentage <= 100):
            await message.reply_text("Percentage 1 se 100 ke beech hona chahiye.")
            return

        total_messages = messages_collection.count_documents({})
        if total_messages == 0:
            await message.reply_text("Database mein koi message nahi hai.")
            return

        messages_to_delete_count = int(total_messages * (percentage / 100))
        if messages_to_delete_count == 0 and percentage > 0 and total_messages > 0: 
            messages_to_delete_count = 1

        if messages_to_delete_count == 0:
            await message.reply_text("Itne kam messages hain ki diye gaye percentage par kuch delete nahi hoga.")
            return

        await message.reply_text(f"{messages_to_delete_count} sabse purane messages delete kiye ja rahe hain ({percentage}% of {total_messages}). Kripya intezaar karein...")

        oldest_message_ids = []
        for msg in messages_collection.find({}).sort("timestamp", 1).limit(messages_to_delete_count):
            oldest_message_ids.append(msg['_id'])
        
        if oldest_message_ids:
            delete_result = messages_collection.delete_many({"_id": {"$in": oldest_message_ids}})
            await message.reply_text(f"Successfully deleted {delete_result.deleted_count} messages from database.")
            logger.info(f"Owner {message.from_user.id} deleted {delete_result.deleted_count} messages ({percentage}%).")
        else:
            await message.reply_text("Koi message delete nahi ho paya. Shayad database khaali hai ya koi problem hai.")

    except ValueError:
        await message.reply_text("Invalid percentage. Kripya ek number dein.")
    except Exception as e:
        await message.reply_text(f"Data reset karne mein error aaya: {e}")
        logger.error(f"Error resetting data by owner {message.from_user.id}: {e}", exc_info=True)
    await store_message(message)

# DELETE MESSAGE BY ID COMMAND
@app.on_message(filters.command("deletemessage") & filters.private & filters.create(owner_only_filter))
async def delete_message_by_id_command(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("Upyog: `/deletemessage <message_id>`. Kripya us message ki ID dein jise delete karna hai.")
        return
    try:
        msg_id_to_delete = int(message.command[1])
        
        delete_result = messages_collection.delete_one({"message_id": msg_id_to_delete})
        
        if delete_result.deleted_count > 0:
            await message.reply_text(f"Message ID `{msg_id_to_delete}` database se successfully delete kar diya gaya.")
            logger.info(f"Owner {message.from_user.id} deleted message ID {msg_id_to_delete}.")
        else:
            await message.reply_text(f"Message ID `{msg_id_to_delete}` database mein nahi mila.")
    except ValueError:
        await message.reply_text("Invalid message ID. Kripya ek number dein.")
    except Exception as e:
        await message.reply_text(f"Message delete karne mein error aaya: {e}")
        logger.error(f"Error deleting message by owner {message.from_user.id}: {e}", exc_info=True)
    await store_message(message)

# GROUP ADMIN COMMANDS (BAN, UNBAN, KICK, PIN, UNPIN)
async def perform_chat_action(client: Client, message: Message, action_type: str):
    if not message.reply_to_message and len(message.command) < 2:
        await message.reply_text(f"Kripya us user ko reply karein jise {action_type} karna hai, ya user ID/username dein.\nUpyog: `/{action_type} <user_id_or_username>` ya message ko reply karein.")
        return

    target_user_id = None
    if message.reply_to_message and message.reply_to_message.from_user:
        target_user_id = message.reply_to_message.from_user.id
    elif len(message.command) >= 2:
        try:
            target_user_id = int(message.command[1])
        except ValueError:
            target_user_id = message.command[1] # It's a username or invalid ID

    if not target_user_id:
        await message.reply_text("User ko identify nahi kar paya. Kripya sahi user ID ya username dein.")
        return

    me_in_chat = await client.get_chat_member(message.chat.id, client.me.id)
    if not me_in_chat.can_restrict_members and action_type in ["ban", "unban", "kick"]:
        await message.reply_text(f"Mujhe {action_type} karne ke liye 'Ban Users' permission ki zaroorat hai.")
        return
    if not me_in_chat.can_pin_messages and action_type in ["pin", "unpin"]:
        await message.reply_text(f"Mujhe {action_type} karne ke liye 'Pin Messages' permission ki zaroorat hai.")
        return
    
    try:
        if action_type == "ban":
            await client.ban_chat_member(message.chat.id, target_user_id)
            await message.reply_text(f"User {target_user_id} ko ban kar diya gaya.")
        elif action_type == "unban":
            await client.unban_chat_member(message.chat.id, target_user_id)
            await message.reply_text(f"User {target_user_id} ko unban kar diya gaya.")
        elif action_type == "kick":
            await client.kick_chat_member(message.chat.id, target_user_id)
            await message.reply_text(f"User {target_user_id} ko kick kar diya gaya.")
        elif action_type == "pin":
            if not message.reply_to_message:
                await message.reply_text("Pin karne ke liye kripya ek message ko reply karein ya message ID dein.")
                return
            await client.pin_chat_message(message.chat.id, message.reply_to_message.id)
            await message.reply_text("Message pin kar diya gaya.")
        elif action_type == "unpin":
            await client.unpin_chat_messages(message.chat.id)
            await message.reply_text("Sabhi pinned messages unpin kar diye gaye.")
    except Exception as e:
        await message.reply_text(f"Error {action_type} karte samay: {e}")
        logger.error(f"Error performing {action_type} by user {message.from_user.id}: {e}", exc_info=True)
    await store_message(message)

@app.on_message(filters.command("ban") & filters.group & filters.create(owner_only_filter))
async def ban_command(client: Client, message: Message):
    await perform_chat_action(client, message, "ban")

@app.on_message(filters.command("unban") & filters.group & filters.create(owner_only_filter))
async def unban_command(client: Client, message: Message):
    await perform_chat_action(client, message, "unban")

@app.on_message(filters.command("kick") & filters.group & filters.create(owner_only_filter))
async def kick_command(client: Client, message: Message):
    await perform_chat_action(client, message, "kick")

@app.on_message(filters.command("pin") & filters.group & filters.create(owner_only_filter))
async def pin_command(client: Client, message: Message):
    await perform_chat_action(client, message, "pin")

@app.on_message(filters.command("unpin") & filters.group & filters.create(owner_only_filter))
async def unpin_command(client: Client, message: Message):
    await perform_chat_action(client, message, "unpin")

# --- CUSTOM WELCOME MESSAGE ---
@app.on_message(filters.command("setwelcome") & filters.group & filters.create(owner_only_filter))
async def set_welcome_command(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("Kripya welcome message dein.\nUpyog: `/setwelcome Aapka naya welcome message {user} {chat_title}`")
        return
    welcome_msg_text = " ".join(message.command[1:])
    group_configs_collection.update_one(
        {"chat_id": message.chat.id},
        {"$set": {"welcome_message": welcome_msg_text}},
        upsert=True
    )
    await message.reply_text("Naya welcome message set kar diya gaya hai. Jab naya member aayega, to main yahi message bhejoongi.")
    await store_message(message)

@app.on_message(filters.command("getwelcome") & filters.group & filters.create(owner_only_filter))
async def get_welcome_command(client: Client, message: Message):
    config = group_configs_collection.find_one({"chat_id": message.chat.id})
    if config and "welcome_message" in config:
        await message.reply_text(f"Current welcome message:\n`{config['welcome_message']}`")
    else:
        await message.reply_text("Is group ke liye koi custom welcome message set nahi hai.")
    await store_message(message)

@app.on_message(filters.command("clearwelcome") & filters.group & filters.create(owner_only_filter))
async def clear_welcome_command(client: Client, message: Message):
    group_configs_collection.update_one(
        {"chat_id": message.chat.id},
        {"$unset": {"welcome_message": ""}}
    )
    await message.reply_text("Custom welcome message hata diya gaya hai. Ab main default welcome message bhejoongi.")
    await store_message(message)

# Handle new chat members for welcome message
@app.on_message(filters.new_chat_members & filters.group)
async def new_member_welcome(client: Client, message: Message):
    config = group_configs_collection.find_one({"chat_id": message.chat.id})
    welcome_text = "Hello {user}, welcome to {chat_title}!"
    if config and "welcome_message" in config:
        welcome_text = config["welcome_message"]

    for user in message.new_chat_members:
        if user.is_self:
            await start_group_command(client, message)
            continue
        
        final_welcome_text = welcome_text.replace("{user}", user.mention)
        final_welcome_text = final_welcome_text.replace("{chat_title}", message.chat.title)
        
        await client.send_message(message.chat.id, final_welcome_text)
    await store_message(message)


# --- PREMIUM CLONING LOGIC ---

# Step 1: Initial /clonebot command (requires payment)
@app.on_message(filters.command("clonebot") & filters.private)
async def initiate_clone_payment(client: Client, message: Message):
    user_id = str(message.from_user.id)
    # Check if user is already approved using clone_state_mongo_client
    user_state = user_states_collection.find_one({"user_id": user_id, "status": "approved_for_clone"})
    if user_state:
        await message.reply_text(
            "आप पहले से ही Bot Cloning ke liye approved hain! ✅\n"
            "Ab aap seedhe apna bot token bhej sakte hain:\n"
            "**Upyog:** `/clonebot YOUR_BOT_TOKEN_HERE`\n"
            "(Pura token ek hi line mein hona chahiye.)"
        )
        return

    # Check if there's a pending request
    pending_request = user_states_collection.find_one({"user_id": user_id, "status": "pending_approval"})
    if pending_request:
        await message.reply_text(
            "Aapki cloning request pehle se hi pending hai. ⏳\n"
            "Kripya admin ke approval ka intezaar karein. Yadi aapne payment kar diya hai aur screenshot bhej diya hai, to dhairya rakhein."
        )
        return

    # User needs to pay
    payment_message = (
        f"Bot Clone karne ke liye aapko ₹{PAYMENT_INFO['amount']} ka payment karna hoga. 💰\n\n"
        f"**Payment Details:**\n"
        f"UPI ID: `{PAYMENT_INFO['upi_id']}`\n\n"
        f"{PAYMENT_INFO['instructions']}"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Screenshot Bhejein", callback_data="send_screenshot_prompt")],
        [InlineKeyboardButton("🚫 Cancel", callback_data="cancel_clone_request")]
    ])
    
    if PAYMENT_INFO['qr_code_url']:
        try:
            await message.reply_photo(
                photo=PAYMENT_INFO['qr_code_url'],
                caption=payment_message,
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Error sending QR code image: {e}")
            await message.reply_text(payment_message, reply_markup=keyboard)
    else:
        await message.reply_text(payment_message, reply_markup=keyboard)
    
    user_states_collection.update_one(
        {"user_id": user_id},
        {"$set": {"status": "awaiting_screenshot", "timestamp": datetime.now()}},
        upsert=True
    )
    await store_message(message)

# Step 2: Handle 'Screenshot Bhejein' callback
@app.on_callback_query(filters.regex("send_screenshot_prompt"))
async def prompt_for_screenshot(client: Client, callback_query: CallbackQuery):
    user_id = str(callback_query.from_user.id)
    user_state = user_states_collection.find_one({"user_id": user_id})

    if user_state and user_state.get("status") == "awaiting_screenshot":
        await callback_query.answer("Kripya apna payment screenshot bhejen.")
        await callback_query.message.reply_text(
            "Ab aap apna payment screenshot bhej sakte hain. 👇",
            reply_markup=ForceReply(True)
        )
        user_states_collection.update_one(
            {"user_id": user_id},
            {"$set": {"status": "expecting_screenshot"}}
        )
    else:
        await callback_query.answer("Kuch galat ho gaya, kripya /clonebot se dobara shuru karein.", show_alert=True)
        user_states_collection.delete_one({"user_id": user_id})

# Step 3: Receive screenshot and send to owner for approval
@app.on_message(filters.photo & filters.private)
async def receive_screenshot(client: Client, message: Message):
    user_id = str(message.from_user.id)
    user_state = user_states_collection.find_one({"user_id": user_id})

    if user_state and user_state.get("status") == "expecting_screenshot":
        await message.reply_text("Aapka screenshot mil gaya hai! ✅\nAdmin approval ka wait karein.")
        
        caption = f"💰 **Payment Proof:**\n" \
                  f"User: {message.from_user.mention} (`{user_id}`)\n" \
                  f"Amount: ₹{PAYMENT_INFO['amount']}"
        
        approve_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Approve Clone", callback_data=f"approve_clone_{user_id}")],
            [InlineKeyboardButton("❌ Reject Clone", callback_data=f"reject_clone_{user_id}")]
        ])
        
        await app.send_photo(
            chat_id=OWNER_ID,
            photo=message.photo.file_id,
            caption=caption,
            reply_markup=approve_keyboard
        )
        logger.info(f"Screenshot received from user {user_id}. Sent to owner for approval.")
        
        user_states_collection.update_one(
            {"user_id": user_id},
            {"$set": {"status": "pending_approval", "screenshot_message_id": message.id}}
        )
    else:
        pass # Silently ignore if not in expected state

# Step 4: Owner approves/rejects clone request
@app.on_callback_query(filters.regex(r"^(approve_clone|reject_clone)_(\d+)$") & filters.create(owner_only_filter))
async def handle_clone_approval(client: Client, callback_query: CallbackQuery):
    action, _, target_user_id = callback_query.data.split('_', 2) # "approve_clone_12345" -> ["approve", "clone", "12345"]
    
    user_state = user_states_collection.find_one({"user_id": target_user_id})

    if not user_state or user_state.get("status") != "pending_approval":
        await callback_query.answer("Yah request ab valid nahi hai ya pehle hi process ho chuki hai.", show_alert=True)
        return

    new_caption = callback_query.message.caption + (f"\n\n**{action.capitalize()}d by Admin!**" if action == "approve_clone" else "\n\n**Rejected by Admin!**")
    try:
        await callback_query.message.edit_caption(
            caption=new_caption,
            reply_markup=None
        )
    except Exception as e:
        logger.error(f"Error editing owner's message for approval: {e}", exc_info=True)
        await client.send_message(OWNER_ID, f"Could not edit message for user {target_user_id}. {action} status: {new_caption}")

    if action == "approve_clone":
        user_states_collection.update_one(
            {"user_id": target_user_id},
            {"$set": {"status": "approved_for_clone", "approved_on": datetime.now()}}
        )
        await client.send_message(
            int(target_user_id),
            "Badhai ho! 🎉 Aapki Bot Cloning request approve ho gayi hai! ✅\n"
            "Ab aap apna bot token bhej sakte hain:\n"
            "**Upyog:** `/clonebot YOUR_BOT_TOKEN_HERE`\n"
            "(Pura token ek hi line mein hona chahiye.)"
        )
        logger.info(f"User {target_user_id} approved for cloning.")
    elif action == "reject_clone":
        user_states_collection.delete_one({"user_id": target_user_id})
        await client.send_message(
            int(target_user_id),
            "Maaf karna! 😔 Aapki Bot Cloning request reject kar di gayi hai.\n"
            "Kisi bhi sawal ke liye owner se contact karein."
        )
        logger.info(f"User {target_user_id} rejected for cloning.")
    
    await callback_query.answer(f"Request {action.split('_')[0]}d for user {target_user_id}.", show_alert=True)


# Step 5: Process actual clonebot command after approval
@app.on_message(filters.command("clonebot") & filters.private & filters.regex(r'/clonebot\s+([A-Za-z0-9:_-]+)'))
async def process_clone_bot_after_approval(client: Client, message: Message):
    user_id = str(message.from_user.id)
    user_state = user_states_collection.find_one({"user_id": user_id, "status": "approved_for_clone"})

    if not user_state:
        await message.reply_text("Aap bot clone karne ke liye approved nahi hain. Kripya pehle payment process poora karein.")
        return

    bot_token = message.command[1].strip()
    if not re.match(r'^\d+:[A-Za-z0-9_-]+$', bot_token):
        await message.reply_text("Yeh bot token sahi nahi lag raha. Kripya valid token dein.")
        return

    await message.reply_text("Aapke bot token ki jaanch ki ja rahi hai...")
    
    temp_mongo_client = None
    try:
        # We don't actually need to connect to a new Mongo for just token validation.
        # But if you want to store cloned bot's specific data later,
        # this is where you'd use CLONE_AND_STATE_MONGO_DB_URI for their specific data.
        # For this part, we just validate the token.

        test_client = Client(
            f"cloned_bot_session_{user_id}",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=bot_token,
            in_memory=True
        )

        await test_client.start()
        bot_info = await test_client.get_me()
        await test_client.stop()

        await message.reply_text(
            f"Bot **@{bot_info.username}** successfully connect ho gaya! ✅\n"
            "Ab apne cloned bot ke liye update channel set karein."
            "\nKripya apne Update Channel ka Username/Link bhejien (eg. `@myupdates` ya `https://t.me/myupdates`)."
            "\nAgar aap apna channel nahi lagana chahte, to `no` type karein. Default channel (@asbhai_bsr) set ho jayega."
            , reply_markup=ForceReply(True)
        )
        logger.info(f"Bot token valid for user {user_id}. Proceeding to channel setup.")
        user_states_collection.update_one(
            {"user_id": user_id},
            {"$set": {"status": "awaiting_channel", "bot_token": bot_token, "bot_username": bot_info.username}}
        )

    except exceptions.unauthorized.BotTokenInvalid: # CHANGED THIS LINE
        await message.reply_text("Yeh bot token invalid hai. Kripya sahi token dein.")
        logger.warning(f"Bot token invalid during cloning for user {user_id}.")
        user_states_collection.update_one({"user_id": user_id}, {"$set": {"status": "approved_for_clone"}})
    except (exceptions.bad_request.ApiIdInvalid, exceptions.bad_request.ApiIdPublishedFlood): # CHANGED THIS LINE
        await message.reply_text("Hamare API ID/HASH mein kuch problem hai, kripya bot owner se contact karein.")
        logger.error(f"API ID/HASH issue during bot cloning attempt by user {user_id}.")
        user_states_collection.update_one({"user_id": user_id}, {"$set": {"status": "approved_for_clone"}})
    except Exception as e:
        await message.reply_text(f"Bot connect karne mein error aaya: `{e}`\nKripya koshish karein ya sahi token dein.")
        logger.error(f"Error during bot cloning for user {user_id}: {e}", exc_info=True)
        user_states_collection.update_one({"user_id": user_id}, {"$set": {"status": "approved_for_clone"}})
    finally:
        if temp_mongo_client: # If a temporary mongo client was created, close it
            temp_mongo_client.close()

    await store_message(message)

# Step 6: Receive update channel link and finalize clone
@app.on_message(filters.text & filters.private)
async def finalize_clone_process(client: Client, message: Message):
    user_id = str(message.from_user.id)
    user_state = user_states_collection.find_one({"user_id": user_id, "status": "awaiting_channel"})

    if not user_state:
        # This message is not part of clone process. Let other handlers handle it.
        return 

    update_channel_input = message.text.strip()
    final_update_channel = DEFAULT_UPDATE_CHANNEL_USERNAME

    if update_channel_input.lower() != "no":
        if re.match(r'^(https?://t\.me/|@)?([a-zA-Z0-9_]+)$', update_channel_input):
            if update_channel_input.startswith("http"):
                final_update_channel = update_channel_input.split('/')[-1]
            else:
                final_update_channel = update_channel_input.replace('@', '')
            
            try:
                chat = await client.get_chat(f"@{final_update_channel}")
                if not chat.type == "channel":
                    await message.reply_text("Yeh ek valid channel username/link nahi lag raha. Kripya sahi channel ka username (@channelname) ya link (t.me/channelname) dein, ya 'no' type karein.")
                    return
            except Exception as e:
                logger.warning(f"Could not verify channel {final_update_channel}: {e}")
                await message.reply_text("Channel ko verify nahi kar paya. Kripya sahi channel ka username (@channelname) ya link (t.me/channelname) dein, ya 'no' type karein.")
                return
            
            logger.info(f"User {user_id} set update channel to @{final_update_channel}")
        else:
            await message.reply_text("Invalid channel username/link. Kripya sahi channel ka username (@channelname) ya link (t.me/channelname) dein, ya 'no' type karein.")
            return

    else:
        logger.info(f"User {user_id} chose default update channel: @{DEFAULT_UPDATE_CHANNEL_USERNAME}")
    
    await message.reply_text(
        "Badhai ho! 🎉 Aapke bot ke liye saari settings complete ho gayi hain.\n\n"
        "Ab aap is bot ko deploy kar sakte hain. Aapka bot token aur update channel niche diye gaye hain:\n"
        f"**Bot Token:** `{user_state['bot_token']}`\n"
        f"**Bot Username:** `@{user_state['bot_username']}`\n"
        f"**Update Channel:** `@{final_update_channel}`\n\n"
        "**Deployment ke liye steps:**\n"
        "1. Hamari GitHub repository ko fork karein.\n"
        "2. Apni `main.py` file mein `BOT_TOKEN`, `API_ID`, `API_HASH` aur `OWNER_ID` ko apne hisaab se Environment Variables mein set karein.\n"
        f"3. Aur `main.py` mein `DEFAULT_UPDATE_CHANNEL_USERNAME` ko `'{final_update_channel}'` par set karein. (Ya phir apne forked repo mein yeh value directly daal dein)\n"
        "4. Koyeb (ya kisi bhi hosting) par deploy karein, Environment Variables mein saari details dein.\n\n"
        "Kisi bhi sawal ke liye @asbhai_bsr channel par aayein."
    )
    
    user_states_collection.delete_one({"user_id": user_id})
    await store_message(message)


# --- Standard message handler (general text/sticker messages) ---
# This filter ensures that messages intended for clone process are handled by specific functions.
# Other text messages fall through to the main learning handler.
@app.on_message(filters.text | filters.sticker)
async def handle_general_messages(client: Client, message: Message):
    if message.from_user and message.from_user.is_bot:
        return
    
    user_id = str(message.from_user.id)
    user_state = user_states_collection.find_one({"user_id": user_id})

    # Priority to cloning related states
    if user_state and (user_state.get("status") == "expecting_screenshot" and message.photo) or \
       (user_state.get("status") == "awaiting_channel" and message.text):
        # These are handled by specific functions, so this general handler should just return
        # The specific handlers (receive_screenshot, finalize_clone_process) are designed to catch these.
        return # Do nothing here, let the specific handlers do their job.
    
    # If the message is a text message and it's from private chat, AND not a command,
    # and not part of the cloning flow, then it falls through to the learning handler.
    if message.chat.type == "private" and message.text and not message.text.startswith('/') and \
       not (user_state and user_state.get("status") in ["awaiting_screenshot", "expecting_screenshot", "awaiting_channel", "pending_approval"]):
        await handle_message_and_reply_general(client, message)
        return
    
    # For group messages or other message types, simply store and reply if applicable
    if message.chat.type != "private" or message.sticker or (message.text and message.text.startswith('/')):
        await handle_message_and_reply_general(client, message)


# Separate handler for learning and replying to avoid conflicts with state-based handlers
# This will be called from `handle_general_messages`
async def handle_message_and_reply_general(client: Client, message: Message):
    if message.from_user and message.from_user.is_bot: # Double check to ignore bots
        return
    
    is_bot_reply_observed = False
    if message.reply_to_message and message.reply_to_message.from_user and message.reply_to_message.from_user.is_self:
        is_bot_reply_observed = True

    await store_message(message, is_bot_sent=False)
    
    if not is_bot_reply_observed:
        logger.info(f"Attempting to generate reply for chat {message.chat.id}")
        reply_doc = await generate_reply(message)
        if reply_doc:
            try:
                sent_msg = None
                if reply_doc.get("type") == "text":
                    sent_msg = await message.reply_text(reply_doc["content"])
                    logger.info(f"Replied with text: {reply_doc['content']}")
                elif reply_doc.get("type") == "sticker" and reply_doc.get("sticker_id"):
                    sent_msg = await message.reply_sticker(reply_doc["sticker_id"])
                    logger.info(f"Replied with sticker: {reply_doc['sticker_id']}")
                else:
                    logger.warning(f"Reply document found but no content/sticker_id: {reply_doc}")

                if sent_msg:
                    await store_message(sent_msg, is_bot_sent=True, sent_message_id=sent_msg.id)
            except Exception as e:
                logger.error(f"Error sending reply for message {message.id}: {e}", exc_info=True)
        else:
            logger.info("No suitable reply found.")


# --- Flask Web Server for Health Check ---
flask_app = Flask(__name__) 

@flask_app.route('/')
def health_check():
    mongo_status_main = "Disconnected"
    mongo_status_clone_state = "Disconnected"
    mongo_status_commands_settings = "Disconnected"
    try:
        main_mongo_client.admin.command('ping')
        mongo_status_main = "Connected"
    except Exception: pass
    try:
        clone_state_mongo_client.admin.command('ping')
        mongo_status_clone_state = "Connected"
    except Exception: pass
    try:
        commands_settings_mongo_client.admin.command('ping')
        mongo_status_commands_settings = "Connected"
    except Exception: pass
    
    return jsonify(
        status="Bot Health OK!", 
        pyrogram_connected=app.is_connected,
        mongo_db_main_status=mongo_status_main,
        mongo_db_clone_state_status=mongo_status_clone_state,
        mongo_db_commands_settings_status=mongo_status_commands_settings
    )

def run_flask_app():
    port = int(os.getenv('PORT', 8000)) 
    logger.info(f"Flask health check server starting on 0.0.0.0:{port}")
    flask_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False, threaded=True)

# --- Main entry point ---
if __name__ == "__main__":
    logger.info("Asbhaibsr bot running.") # Custom start log message
    
    flask_thread = Thread(target=run_flask_app)
    flask_thread.daemon = True 
    flask_thread.start()

    app.run()
