# Credit by @asbhaibsr and Telegram Channel @asbhai_bsr

import os
import asyncio
import re
import random
import logging
from datetime import datetime, timedelta
from threading import Thread
import time 

# Pyrogram imports
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ForceReply
from pyrogram.raw.functions.messages import SetTyping
from pyrogram.raw.types import SendMessageTypingAction
from pyrogram.errors import exceptions 

# MongoDB imports
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure, InvalidURI 

# Flask imports for web server
from flask import Flask, jsonify

# --- Logger Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Environment Variables ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = os.getenv("OWNER_ID") 
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

# New: All MongoDB URIs fetched from Environment Variables
MAIN_MONGO_DB_URI = os.getenv("MAIN_MONGO_DB_URI") 
CLONE_STATE_MONGO_DB_URI = os.getenv("CLONE_STATE_MONGO_DB_URI") 
COMMANDS_SETTINGS_MONGO_DB_URI = os.getenv("COMMANDS_SETTINGS_MONGO_DB_URI")

# ----------------------------------------------------------------------------------

# --- Constants ---
MAX_MESSAGES_THRESHOLD = 100000
PRUNE_PERCENTAGE = 0.30
DEFAULT_UPDATE_CHANNEL_USERNAME = "asbhai_bsr" 
REPLY_COOLDOWN_SECONDS = 0 # Changed to 0 for no delay as per request

# --- Payment Details ---
PAYMENT_INFO = {
    "amount": "200",
    "upi_id": "arsadsaifi8272@ibl", 
    "qr_code_url": "", 
    "instructions": "UPI ID par ₹200 bhejien aur payment ka screenshot 'Screenshot Bhejein' button par click karke bhejen."
}

# --- MongoDB Setup for all three connections ---
# Connection 1: For Bot's Learning Messages (from MAIN_MONGO_DB_URI)
main_mongo_client = None
main_db = None
messages_collection = None 

logger.info(f"Attempting to connect to Main Learning MongoDB. MAIN_MONGO_DB_URI: {'[SET]' if MAIN_MONGO_DB_URI else '[NOT SET]'}")
if MAIN_MONGO_DB_URI:
    try:
        main_mongo_client = MongoClient(MAIN_MONGO_DB_URI, serverSelectionTimeoutMS=5000)
        main_mongo_client.admin.command('ping')
        main_db = main_mongo_client.bot_learning_database
        messages_collection = main_db.messages
        logger.info("MongoDB (Main Learning DB) connection successful.")
    except ServerSelectionTimeoutError as err:
        logger.error(f"MongoDB (Main Learning DB) connection timed out: {err}")
        messages_collection = None 
    except ConnectionFailure as err:
        logger.error(f"MongoDB (Main Learning DB) connection failed: {err}")
        messages_collection = None
    except InvalidURI as err:
        logger.error(f"MongoDB (Main Learning DB) Invalid URI: {err}")
        messages_collection = None
    except Exception as e:
        logger.error(f"An unexpected error occurred while connecting to Main Learning MongoDB: {e}", exc_info=True)
        messages_collection = None
else:
    logger.error("MAIN_MONGO_DB_URI environment variable is NOT SET. Main learning database will not be functional.")


# Connection 2: For Clone Requests and User States (from CLONE_STATE_MONGO_DB_URI)
clone_state_mongo_client = None
clone_state_db = None
user_states_collection = None 

logger.info(f"Attempting to connect to Clone/State MongoDB. CLONE_STATE_MONGO_DB_URI: {'[SET]' if CLONE_STATE_MONGO_DB_URI else '[NOT SET]'}")
if CLONE_STATE_MONGO_DB_URI:
    try:
        clone_state_mongo_client = MongoClient(CLONE_STATE_MONGO_DB_URI, serverSelectionTimeoutMS=5000)
        clone_state_mongo_client.admin.command('ping') 
        clone_state_db = clone_state_mongo_client.bot_clone_states_db
        user_states_collection = clone_state_db.user_states
        logger.info("MongoDB (Clone/State DB) connection successful.")
    except ServerSelectionTimeoutError as err:
        logger.error(f"MongoDB (Clone/State DB) connection timed out: {err}")
        user_states_collection = None
    except ConnectionFailure as err:
        logger.error(f"MongoDB (Clone/State DB) connection failed: {err}")
        user_states_collection = None
    except InvalidURI as err:
        logger.error(f"MongoDB (Clone/State DB) Invalid URI: {err}")
        user_states_collection = None
    except Exception as e:
        logger.error(f"Failed to connect to Clone/State MongoDB: {e}", exc_info=True)
        user_states_collection = None
else:
    logger.error("CLONE_STATE_MONGO_DB_URI environment variable is NOT SET. Clone/State database will not be functional.")


# Connection 3: For Commands and Button related settings (from COMMANDS_SETTINGS_MONGO_DB_URI)
commands_settings_mongo_client = None
commands_settings_db = None
group_configs_collection = None 

logger.info(f"Attempting to connect to Commands/Settings MongoDB. COMMANDS_SETTINGS_MONGO_DB_URI: {'[SET]' if COMMANDS_SETTINGS_MONGO_DB_URI else '[NOT SET]'}")
if COMMANDS_SETTINGS_MONGO_DB_URI:
    try:
        commands_settings_mongo_client = MongoClient(COMMANDS_SETTINGS_MONGO_DB_URI, serverSelectionTimeoutMS=5000)
        commands_settings_mongo_client.admin.command('ping') 
        commands_settings_db = commands_settings_mongo_client.bot_settings_db
        group_configs_collection = commands_settings_db.group_configs
        logger.info("MongoDB (Commands/Settings DB) connection successful.")
    except ServerSelectionTimeoutError as err:
        logger.error(f"MongoDB (Commands/Settings DB) connection timed out: {err}")
        group_configs_collection = None
    except ConnectionFailure as err:
        logger.error(f"MongoDB (Commands/Settings DB) connection failed: {err}")
        group_configs_collection = None
    except InvalidURI as err:
        logger.error(f"MongoDB (Commands/Settings DB) Invalid URI: {err}")
        group_configs_collection = None
    except Exception as e:
        logger.error(f"Failed to connect to Commands/Settings MongoDB: {e}", exc_info=True)
        group_configs_collection = None
else:
    logger.error("COMMANDS_SETTINGS_MONGO_DB_URI environment variable is NOT SET. Commands/Settings database will not be functional.")


# --- Pyrogram Client ---
app = Client(
    "self_learning_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# --- Global variable to track last reply time per chat ---
# {chat_id: last_reply_timestamp (float)}
last_bot_reply_time = {}


# --- Utility Functions ---

def extract_keywords(text):
    if not text: return []
    words = re.findall(r'\b\w+\b', text.lower())
    return list(set(words))

async def prune_old_messages():
    if messages_collection is None:
        logger.warning("messages_collection is None. Cannot prune messages.")
        return
    try:
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
    except Exception as e:
        logger.error(f"Error during pruning: {e}", exc_info=True)


async def store_message(message: Message, is_bot_sent: bool = False, sent_message_id: int = None):
    # If messages_collection is not initialized, we cannot store.
    if messages_collection is None:
        logger.error("messages_collection is NOT initialized. Cannot store message. Please check MongoDB connection for MAIN_MONGO_DB_URI.")
        return

    try:
        if message.from_user and message.from_user.is_bot and not is_bot_sent:
            return

        content_type = "text" if message.text else ("sticker" if message.sticker else "other")
        
        # FIX: Store sticker file_id as content for stickers
        content_value = None
        if message.text:
            content_value = message.text
        elif message.sticker:
            content_value = message.sticker.file_id # Store file_id for stickers
            content_type = "sticker" # Ensure content type is explicitly 'sticker'
        else:
            content_value = None # For other content types

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
            "content_type": content_type,
            "content": content_value,
            "sticker_id": message.sticker.file_id if message.sticker else None, # Keep sticker_id separate for direct access
            "keywords": extract_keywords(message.text) if message.text else [], # Only extract keywords from text content
            "replied_to_message_id": message.reply_to_message.id if message.reply_to_message else None,
            "replied_to_user_id": message.reply_to_message.from_user.id if message.reply_to_message and message.reply_to_message.from_user else None,
            "replied_to_content": message.reply_to_message.text if message.reply_to_message and message.reply_to_message.text else (message.reply_to_message.sticker.file_id if message.reply_to_message and message.reply_to_message.sticker else None), # Store sticker file_id for replied_to_content
            "is_bot_observed_pair": False,
        }

        if message.reply_to_message and message.reply_to_message.from_user and message.reply_to_message.from_user.is_self:
            message_data["is_bot_observed_pair"] = True
            logger.debug(f"Observed user reply to bot's message: {message.reply_to_message.id}")
            if messages_collection is not None:
                messages_collection.update_one(
                    {"chat_id": message.chat.id, "message_id": message.reply_to_message.id, "is_bot_sent": True},
                    {"$set": {"is_bot_observed_pair": True}}
                )

        if messages_collection is not None:
            messages_collection.insert_one(message_data)
            logger.debug(f"Message stored: {message.id} from {message.from_user.id if message.from_user else 'None'}. Bot sent: {is_bot_sent}")
            await prune_old_messages()
        else:
            logger.error("messages_collection is STILL None after initial check. This should not happen here.")
    except ServerSelectionTimeoutError as e:
        logger.error(f"MongoDB connection error while storing message {message.id}: {e}")
    except Exception as e:
        logger.error(f"Error storing message {message.id}: {e}", exc_info=True)


async def generate_reply(message: Message):
    # Removed asyncio.sleep(0.5) for immediate typing indicator
    await app.invoke(SetTyping(peer=await app.resolve_peer(message.chat.id), action=SendMessageTypingAction()))

    query_content = message.text if message.text else (message.sticker.file_id if message.sticker else "") # Use file_id for stickers
    query_keywords = extract_keywords(message.text) # Only extract keywords from text content

    query_content_type = "text" if message.text else ("sticker" if message.sticker else "other")

    if not query_keywords and not query_content:
        logger.debug("No content or keywords extracted for reply generation.")
        return None

    if messages_collection is None:
        logger.error("messages_collection is None. Cannot generate reply.")
        return None

    # --- Strategy 1: Direct observed reply (User-to-User, or Bot-to-User) ---
    if message.reply_to_message:
        replied_to_content = message.reply_to_message.text if message.reply_to_message.text else (message.reply_to_message.sticker.file_id if message.reply_to_message and message.reply_to_message.sticker else None)
        if replied_to_content:
            logger.info(f"Searching for observed replies to: '{replied_to_content}' (Type: {message.reply_to_message.content_type if message.reply_to_message else 'N/A'})")
            
            # Try finding contextual reply within the same chat first
            observed_replies_cursor = messages_collection.find({
                "replied_to_content": replied_to_content, # Exact match for content
                "is_bot_observed_pair": True,
                "chat_id": message.chat.id,
                "content_type": {"$in": ["text", "sticker"]} # Ensure reply is text or sticker
            })
            potential_replies = list(observed_replies_cursor)
            if potential_replies:
                logger.info(f"Found {len(potential_replies)} contextual replies based on direct reply in same chat.")
                # FIX: Ensure chosen reply has content/sticker_id
                filtered_potential_replies = [
                    doc for doc in potential_replies 
                    if (doc.get("content_type") == "text" and doc.get("content")) or \
                       (doc.get("content_type") == "sticker" and doc.get("sticker_id"))
                ]
                if filtered_potential_replies:
                    return random.choice(filtered_potential_replies)

            # Fallback to global contextual reply
            observed_replies_cursor = messages_collection.find({
                "replied_to_content": replied_to_content, # Exact match for content
                "is_bot_observed_pair": True,
                "content_type": {"$in": ["text", "sticker"]} # Ensure reply is text or sticker
            })
            potential_replies = list(observed_replies_cursor)
            if potential_replies:
                logger.info(f"Found {len(potential_replies)} global contextual replies based on direct reply.")
                # FIX: Ensure chosen reply has content/sticker_id
                filtered_potential_replies = [
                    doc for doc in potential_replies 
                    if (doc.get("content_type") == "text" and doc.get("content")) or \
                       (doc.get("content_type") == "sticker" and doc.get("sticker_id"))
                ]
                if filtered_potential_replies:
                    return random.choice(filtered_potential_replies)

    # --- Strategy 2: Keyword-based general reply ---
    logger.info(f"No direct contextual reply. Falling back to keyword search for: '{query_content}'")
    keyword_regex = "|".join([re.escape(kw) for kw in query_keywords]) if query_keywords else ""

    # Try finding general keyword reply within the same chat first
    general_replies_group_cursor = messages_collection.find({
        "chat_id": message.chat.id,
        "content_type": {"$in": ["text", "sticker"]},
        "$or": [
            {"content": {"$regex": f".*({keyword_regex}).*", "$options": "i"}} if keyword_regex else {},
            {"sticker_id": {"$exists": True, "$ne": None}} if query_content_type == "sticker" else {}
        ]
    })
    potential_replies = list(general_replies_group_cursor)

    if not potential_replies:
        # Fallback to global keyword search
        general_replies_global_cursor = messages_collection.find({
            "content_type": {"$in": ["text", "sticker"]},
            "$or": [
                {"content": {"$regex": f".*({keyword_regex}).*", "$options": "i"}} if keyword_regex else {},
                {"sticker_id": {"$exists": True, "$ne": None}} if query_content_type == "sticker" else {}
            ]
        })
        potential_replies = list(general_replies_global_cursor)

    if potential_replies:
        logger.info(f"Found {len(potential_replies)} general keyword-based replies.")
        
        # FIX: Filter out replies that are identical to the incoming message and ensure content/sticker_id
        filtered_replies = [
            doc for doc in potential_replies
            if not (doc.get("content", "").lower() == query_content.lower() and doc.get("content_type") == query_content_type) and
               (doc.get("content_type") == "text" and doc.get("content")) or \
               (doc.get("content_type") == "sticker" and doc.get("sticker_id"))
        ]
        
        if filtered_replies:
            return random.choice(filtered_replies)
        elif potential_replies: # If all were filtered out because they were identical, just pick one (if any left)
            # This case means all found replies are identical to the input,
            # which might happen if the database only has the same input as a reply.
            # In this case, we might still want to return something or fall back.
            # For now, if filtered_replies is empty, we let it fall through to generic replies.
            logger.warning(f"All potential replies were identical to input or had no content for '{query_content}'. Falling back.")


    logger.info(f"No suitable reply found for: '{query_content}'.")

    # --- Strategy 3: Fallback generic replies ---
    fallback_messages = [
        {"type": "text", "content": "Hmm, main is bare mein kya kahoon?"},
        {"type": "text", "content": "Interesting! Aur kuch?"},
        {"type": "text", "content": "Main sun rahi hoon... 👋"},
        {"type": "text", "content": "Aapki baat sunkar acha laga!"},
        {"type": "text", "content": "Kya haal-chal?"}
    ]
    return random.choice(fallback_messages) # Return dict with 'type' and 'content'


# --- Pyrogram Event Handlers ---

# START COMMAND (PRIVATE CHAT)
@app.on_message(filters.command("start") & filters.private)
async def start_private_command(client: Client, message: Message):
    user_name = message.from_user.first_name if message.from_user else "mere pyare dost"
    welcome_message = (
        f"Hey, **{user_name}**! 👋 Main aa gayi hoon aapki baaton ka hissa banne. "
        "Mera naam hai **⎯᪵⎯꯭̽🤍꯭᪳ ⃪𝗖𝘂꯭𝘁𝗶𝗲꯭ 𝗣𝗶𝗲꯭ ⃪🌸͎᪳᪳𝆺꯭𝅥⎯꯭̽⎯꯭**! 💖"
        "\n\nAgar aap mujhe apne **group mein add karte hain**, toh main wahan ki conversations se seekh kar sabko aur bhi mazedaar jawab de paungi. "
        "Jaise, aapki har baat par main apni cute si ray dungi! 😉"
        "\n\nGroup mein add karke aapko milenge: "
        "\n✨ **Smart replies:** Main group members ki baaton se seekh kar unhe behtar jawab dungi. "
        "Meri har baat mein thodi si masti aur bahot saara pyaar hoga! 🥰"
        "\n📚 **Knowledge base:** Group ki saari conversations ko yaad rakhungi, jo baad mein kaam aa sakti hain. "
        "Kuch bhi pucho, main sab bataungi! 🤫"
        "\n\nChalo, kuch mithaas bhari baatein karte hain! Mujhe toh bas aapka saath chahiye! 💋"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Mujhe Apne Group Mein Bulao!", url=f"https://t.me/{client.me.username}?startgroup=true")],
        [InlineKeyboardButton("📣 Meri Updates Yahan Milengi! 😉", url=f"https://t.me/asbhai_bsr")] 
    ])
    await message.reply_text(welcome_message, reply_markup=keyboard)
    await store_message(message)

# START COMMAND (GROUP CHAT)
@app.on_message(filters.command("start") & filters.group) # Added filters.group
async def start_group_command(client: Client, message: Message):
    welcome_messages = [
        "Hello, my lovely group! 👋 Main aa gayi hoon aapki conversations mein shamil hone. Yahan main aap sabki baaton se seekhti rahungi, aur sabko cute cute replies dungi! 🥰",
        "Hey everyone! 💖 Main yahan aap sab ki baatein sunne aur seekhne aayi hoon. Isse main aur smart replies de paungi. Chalo, ab group mein double masti hogi! 😉",
        "Namaste to all the amazing people here! ✨ Mujhe group mein add karne ka shukriya. Main yahan ki baaton ko samjh kar aur behtar hoti jaungi. Ab toh har baat par mera jawaab milega! 🤭"
    ]
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📣 Meri Updates Yahan Milengi! 😉", url=f"https://t.me/asbhai_bsr")] 
    ])
    await message.reply_text(random.choice(welcome_messages), reply_markup=keyboard)
    await store_message(message)

# GENERAL STATS COMMAND
@app.on_message(filters.command("stats") & (filters.private | filters.group))
async def stats_command(client: Client, message: Message):
    if len(message.command) < 2 or message.command[1].lower() != "check":
        await message.reply_text("Hehe, agar mere stats dekhne hain toh aise bolo: `/stats check`. Main koi simple bot thodi na hoon! 😉")
        return

    if messages_collection is not None:
        total_messages = messages_collection.count_documents({})
        unique_group_ids = messages_collection.distinct("chat_id", {"chat_type": {"$in": ["group", "supergroup"]}})
        num_groups = len(unique_group_ids)

        stats_text = (
            "📊 **Meri Cute Cute Statistics** 📊\n"
            f"• Kitne groups mein main masti karti hoon: **{num_groups}**\n"
            f"• Kitne messages maine apne dimag mein store kiye hain: **{total_messages}**\n"
            "Ab batao, main smart hoon na? 🤩"
        )
        await message.reply_text(stats_text)
    else:
        await message.reply_text("Maaf karna, statistics abhi available nahi hain. Database mein kuch gadbad hai. 🥺 (Main Learning DB connect nahi ho paya)")
    await store_message(message) 

# HELP COMMAND
@app.on_message(filters.command("help") & (filters.private | filters.group))
async def help_command(client: Client, message: Message):
    help_text = (
        "👋 Hi! Main ek cute si self-learning bot hoon jo aapki baaton se seekhta hai, "
        "aur haan, main ladki hoon! 😉"
        "\n\n**Meri Commands (Dekho, kitni pyaari hain!):**"
        "\n• `/start` - Mujhe shuru karo, main wait kar rahi hoon! 💕"
        "\n• `/stats check` - Mere statistics dekho, main kitni cool hoon! 😎"
        "\n• `/help` - Yehi message dobara dekh lo, agar kuch bhool gaye ho! 🤭"
        "\n• `/myid` - Apni user ID dekho, kahin kho na jaye! 🆔"
        "\n• `/chatid` - Is chat ki ID dekho, sab secrets yahi hain! 🤫"
        "\n• `/clonebot` - Apna khud ka bot banao, bilkul mere jaisa! (Premium Feature, but worth it! 😉)"
        "\n\n**Admin Commands (Sirf mere Malik ke liye, shhh!):**"
        "\n• `/broadcast <message>` - Sabko mera pyaara message bhejo!"
        "\n• `/resetdata <percentage>` - Kuch purani yaadein mita do! (Agar data bahot ho jaye)"
        "\n• `/deletemessage <message_id>` - Ek khaas message delete karo!"
        "\n• `/ban <user_id_or_username>` - Gande logon ko group se bhagao! 😤"
        "\n• `/unban <user_id_or_username>` - Acha, maaf kar do unhe! 😊"
        "\n• `/kick <user_id_or_username>` - Thoda bahar ghuma ke lao! 😉"
        "\n• `/pin <message_id>` - Important message ko upar rakho, sabko dikhe! ✨"
        "\n• `/unpin` - Ab bas karo, bohot ho gaya pin! 😅"
        "\n• `/setwelcome <message>` - Group mein naye guests ka swagat, mere style mein! 💖"
        "\n• `/getwelcome` - Dekho maine kya welcome message set kiya hai!"
        "\n• `/clearwelcome` - Agar welcome message pasand nahi, toh hata do! 🤷‍♀️"
        "\n\n**Note:** Admin commands ke liye, mujhe group mein zaroori permissions dena mat bhoolna, warna main kuch nahi kar paungi! 🥺"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Mujhe Apne Group Mein Bulao! 😉", url=f"https://t.me/{client.me.username}?startgroup=true")],
        [InlineKeyboardButton("📣 Meri Updates Yahan Milengi! 💖", url=f"https://t.me/asbhai_bsr")] 
    ])
    await message.reply_text(help_text, reply_markup=keyboard)
    await store_message(message) 

# MYID COMMAND
@app.on_message(filters.command("myid") & (filters.private | filters.group))
async def my_id_command(client: Client, message: Message):
    user_id = message.from_user.id if message.from_user else "N/A"
    await message.reply_text(f"Hehe, tumhari user ID: `{user_id}`. Ab tum mere liye aur bhi special ho gaye! 😊")
    await store_message(message) 

# CHATID COMMAND
@app.on_message(filters.command("chatid") & (filters.private | filters.group))
async def chat_id_command(client: Client, message: Message):
    chat_id = message.chat.id
    await message.reply_text(f"Is chat ki ID: `{chat_id}`. Kya tum mujhe secrets bataoge? 😉")
    await store_message(message) 

# --- ADMIN COMMANDS ---

# Helper function to check if user is owner
def is_owner(user_id):
    return str(user_id) == str(OWNER_ID) 

# Admin check decorator (FIXED: Added check for message.from_user)
def owner_only_filter(_, __, message):
    if message.from_user is not None:
        return is_owner(message.from_user.id)
    return False

# BROADCAST COMMAND
@app.on_message(filters.command("broadcast") & filters.private & filters.create(owner_only_filter))
async def broadcast_command(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("Malik, kripya broadcast karne ke liye ek pyaara sa message dein. Upyog: `/broadcast Aapka message yahan`")
        return
    broadcast_text = " ".join(message.command[1:])
    if messages_collection is not None:
        unique_chat_ids = messages_collection.distinct("chat_id")
        sent_count = 0
        failed_count = 0
        await message.reply_text("Malik, main ab sabko aapka message bhej rahi hoon! 😉")
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
        await message.reply_text(f"Broadcast poora hua, Malik! {sent_count} chats ko bheja, {failed_count} chats ke liye asafal raha. Maine apna best diya! 🥰")
    else:
        await message.reply_text("Maaf karna, broadcast nahi kar payi. Database (Main Learning DB) connect nahi ho paya hai. 🥺")
    await store_message(message) 

# RESET DATA COMMAND
@app.on_message(filters.command("resetdata") & filters.private & filters.create(owner_only_filter))
async def reset_data_command(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("Malik, kitna data delete karna hai? Percentage batao (1 se 100 ke beech). Upyog: `/resetdata <percentage>`")
        return
    try:
        percentage = int(message.command[1])
        if not (1 <= percentage <= 100):
            await message.reply_text("Percentage 1 se 100 ke beech hona chahiye, Malik! 😊")
            return

        if messages_collection is None:
            await message.reply_text("Maaf karna, data reset nahi kar payi. Database (Main Learning DB) connect nahi ho paya hai. 🥺")
            return

        total_messages = messages_collection.count_documents({})
        if total_messages == 0:
            await message.reply_text("Malik, database mein koi message hai hi nahi! Main kya delete karun? 🤷‍♀️")
            return

        messages_to_delete_count = int(total_messages * (percentage / 100))
        if messages_to_delete_count == 0 and percentage > 0 and total_messages > 0:
            messages_to_delete_count = 1

        if messages_to_delete_count == 0:
            await message.reply_text("Malik, itne kam messages hain ki diye gaye percentage par kuch delete nahi hoga. Kya karna hai? 🤔")
            return

        await message.reply_text(f"{messages_to_delete_count} sabse purane messages delete kiye ja rahe hain ({percentage}% of {total_messages}). Kripya intezaar karein, main saaf-safai kar rahi hoon! 🧹✨")

        oldest_message_ids = []
        for msg in messages_collection.find({}).sort("timestamp", 1).limit(messages_to_delete_count):
            oldest_message_ids.append(msg['_id'])

        if oldest_message_ids:
            delete_result = messages_collection.delete_many({"_id": {"$in": oldest_message_ids}})
            await message.reply_text(f"Successfully {delete_result.deleted_count} messages database se delete ho gaye, Malik! Ab main aur smart banungi! 💖")
            logger.info(f"Owner {message.from_user.id} deleted {delete_result.deleted_count} messages ({percentage}%).")
        else:
            await message.reply_text("Malik, koi message delete nahi ho paya. Shayad database khaali hai ya koi problem hai. 🥺")

    except ValueError:
        await message.reply_text("Invalid percentage. Kripya ek number dein, Malik! 🔢")
    except Exception as e:
        await message.reply_text(f"Data reset karte samay error aaya, Malik: {e}. Kya hua? 😭")
        logger.error(f"Error resetting data by owner {message.from_user.id}: {e}", exc_info=True)
    await store_message(message) 

# DELETE MESSAGE BY ID COMMAND
@app.on_message(filters.command("deletemessage") & filters.private & filters.create(owner_only_filter))
async def delete_message_by_id_command(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("Malik, kripya us message ki ID dein jise delete karna hai. Upyog: `/deletemessage <message_id>`")
        return
    try:
        msg_id_to_delete = int(message.command[1])

        if messages_collection is not None:
            delete_result = messages_collection.delete_one({"message_id": msg_id_to_delete})

            if delete_result.deleted_count > 0:
                await message.reply_text(f"Message ID `{msg_id_to_delete}` database se successfully delete kar diya gaya, Malik! Poof! ✨")
                logger.info(f"Owner {message.from_user.id} deleted message ID {msg_id_to_delete}.") 
            else:
                await message.reply_text(f"Message ID `{msg_id_to_delete}` database mein nahi mila, Malik. Shayad main use janti hi nahi thi! 😅")
        else:
            await message.reply_text("Maaf karna, message delete nahi kar payi. Database (Main Learning DB) connect nahi ho paya hai. 🥺")
    except ValueError:
        await message.reply_text("Invalid message ID. Kripya ek number dein, Malik! 🔢")
    except Exception as e:
        await message.reply_text(f"Message delete karne mein error aaya, Malik: {e}. Kya hua? 🥺")
        logger.error(f"Error deleting message by owner {message.from_user.id}: {e}", exc_info=True)
    await store_message(message) 

# GROUP ADMIN COMMANDS (BAN, UNBAN, KICK, PIN, UNPIN)
async def perform_chat_action(client: Client, message: Message, action_type: str):
    if not message.reply_to_message and (len(message.command) < 2 or (len(message.command) >= 2 and not message.command[1])):
        await message.reply_text(f"Malik, kripya us user ko reply karein jise {action_type} karna hai, ya user ID/username dein.\nUpyog: `/{action_type} <user_id_or_username>` ya message ko reply karein. Jaldi karo, mujhe masti karni hai! 💃")
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
        await message.reply_text("Malik, main us user ko dhundh nahi pa rahi hoon! Kya tumne sahi ID ya username diya? 🤔")
        return
    
    try:
        me_in_chat = await client.get_chat_member(message.chat.id, client.me.id)
    except Exception as e:
        logger.error(f"Error getting bot's chat member info in {message.chat.id}: {e}", exc_info=True)
        await message.reply_text("Malik, group ki permissions check karne mein error aaya. Kya main wahan se nikal jaun? 🥺")
        return

    if action_type in ["ban", "unban", "kick"]:
        if not me_in_chat.can_restrict_members:
            await message.reply_text(f"Malik, mujhe {action_type} karne ke liye 'Users Ko Ban Karo' permission ki zaroorat hai. Please de do na! 🙏")
            return
    if action_type in ["pin", "unpin"]:
        if not me_in_chat.can_pin_messages:
            await message.reply_text(f"Malik, mujhe {action_type} karne ke liye 'Messages Pin Karo' permission ki zaroorat hai. Jaldi do! 🥺")
            return

    try:
        if action_type == "ban":
            await client.ban_chat_member(message.chat.id, target_user_id)
            await message.reply_text(f"User {target_user_id} ko ban kar diya gaya, Malik! Ab koi shor nahi! 🤫")
        elif action_type == "unban":
            await client.unban_chat_member(message.chat.id, target_user_id)
            await message.reply_text(f"User {target_user_id} ko unban kar diya gaya, Malik! Shayad usne sabak seekh liya होगा! 😉")
        elif action_type == "kick":
            await client.kick_chat_member(message.chat.id, target_user_id)
            await message.reply_text(f"User {target_user_id} ko kick kar diya gaya, Malik! Tata bye bye! 👋")
        elif action_type == "pin":
            if not message.reply_to_message:
                await message.reply_text("Malik, pin karne ke liye kripya ek message ko reply karein. Main confusion mein pad jaungi! 😵‍💫")
                return
            await client.pin_chat_message(message.chat.id, message.reply_to_message.id)
            await message.reply_text("Message pin kar diya gaya, Malik! Ab sabko dikhega! ✨")
        elif action_type == "unpin":
            await client.unpin_chat_messages(message.chat.id)
            await message.reply_text("Sabhi pinned messages unpin kar diye gaye, Malik! Ab group free hai! 🥳")
    except Exception as e:
        await message.reply_text(f"Malik, {action_type} karte samay error aaya: {e}. Mujhse ho nahi pa raha! 😭")
        logger.error(f"Error performing {action_type} by user {message.from_user.id if message.from_user else 'None'}: {e}", exc_info=True)
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
@app.on_message(filters.command("setwelcome") & filters.group & filters.create(owner_only_filter)) # Added filters.group
async def set_welcome_command(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("Malik, kripya welcome message dein.\nUpyog: `/setwelcome Aapka naya welcome message {user} {chat_title}`. Naye members ko surprise karte hain! 🥳")
        return
    welcome_msg_text = " ".join(message.command[1:])
    if group_configs_collection is not None:
        group_configs_collection.update_one(
            {"chat_id": message.chat.id},
            {"$set": {"welcome_message": welcome_msg_text}},
            upsert=True
        )
        await message.reply_text("Naya welcome message set kar diya gaya hai, Malik! Jab naya member aayega, toh main yahi pyaara message bhejoongi! 🥰")
    else:
        await message.reply_text("Maaf karna, welcome message set nahi kar payi. Database (Commands/Settings DB) connect nahi ho paya hai. 🥺")
    await store_message(message) 

@app.on_message(filters.command("getwelcome") & filters.group & filters.create(owner_only_filter)) # Added filters.group
async def get_welcome_command(client: Client, message: Message):
    config = None
    if group_configs_collection is not None:
        config = group_configs_collection.find_one({"chat_id": message.chat.id})
    
    if config and "welcome_message" in config:
        await message.reply_text(f"Malik, current welcome message:\n`{config['welcome_message']}`. Pasand aaya? 😉")
    else:
        await message.reply_text("Malik, is group ke liye koi custom welcome message set nahi hai. Kya set karna chahte ho? 🥺")
    await store_message(message) 

@app.on_message(filters.command("clearwelcome") & filters.group & filters.create(owner_only_filter)) # Added filters.group
async def clear_welcome_command(client: Client, message: Message):
    if group_configs_collection is not None:
        group_configs_collection.update_one(
            {"chat_id": message.chat.id},
            {"$unset": {"welcome_message": ""}}
        )
        await message.reply_text("Malik, custom welcome message hata diya gaya hai. Ab main default welcome message bhejoongi. Kya main bori...ng ho gayi? 😔")
    else:
        await message.reply_text("Maaf karna, welcome message clear nahi kar payi. Database (Commands/Settings DB) connect nahi ho paya hai. 🥺")
    await store_message(message) 

# Handle new chat members for welcome message
@app.on_message(filters.new_chat_members & filters.group)
async def new_member_welcome(client: Client, message: Message):
    config = None
    if group_configs_collection is not None:
        config = group_configs_collection.find_one({"chat_id": message.chat.id})
    
    welcome_text = "Hello {user}, welcome to {chat_title}! Main yahan aapka swagat karti hoon! 🥰"
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
    
    if user_states_collection is None:
        await message.reply_text("Maaf karna, abhi bot cloning service available nahi hai. Database (Clone/State DB) connect nahi ho paya hai. 🥺")
        return

    user_state = user_states_collection.find_one({"user_id": user_id, "status": "approved_for_clone"})
    if user_state:
        await message.reply_text(
            "Tum toh pehle se ही meri permission le chuke ho, mere dost! ✅\n"
            "Ab bas apna bot token bhejo, main tumhare liye ek naya bot bana dungi:\n"
            "**Kaise?** `/clonebot YOUR_BOT_TOKEN_HERE`\n"
            "(Pura token ek hi line mein hona chahiye, theek hai? 😉)"
        )
        return

    pending_request = user_states_collection.find_one({"user_id": user_id, "status": "pending_approval"})
    if pending_request:
        await message.reply_text(
            "Meri cute si request pehle se hi pending hai, darling! ⏳\n"
            "Kripya admin ke approval ka intezaar karo. Agar payment aur screenshot bhej diya hai, toh thoda sabar karo na! 😊"
        )
        return

    payment_message = (
        f"Agar tum bhi mujhse milta julta ek cute sa bot banana chahte ho, toh bas ₹{PAYMENT_INFO['amount']} ka payment karna hoga. 💰"
        f"\n\n**Payment Details (Meri Secret Jaan!):**\n"
        f"UPI ID: `{PAYMENT_INFO['upi_id']}`\n\n"
        f"{PAYMENT_INFO['instructions']}\n"
        "Jaldi karo, main wait kar rahi hoon! 😉"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Screenshot Bhejo Na! 🥰", callback_data="send_screenshot_prompt")],
        [InlineKeyboardButton("🚫 Rehne Do, Nahi Banwana 😔", callback_data="cancel_clone_request")]
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
    logger.info(f"User {user_id} initiated clone, status set to awaiting_screenshot.")
    await store_message(message) 

# Step 2: Handle 'Screenshot Bhejein' callback
@app.on_callback_query(filters.regex("send_screenshot_prompt"))
async def prompt_for_screenshot(client: Client, callback_query: CallbackQuery):
    user_id = str(callback_query.from_user.id)
    
    if user_states_collection is None:
        await callback_query.answer("Maaf karna, abhi service available nahi hai. Database (Clone/State DB) connect nahi ho paya hai. 🥺", show_alert=True)
        return

    user_state = user_states_collection.find_one({"user_id": user_id})

    if user_state and user_state.get("status") == "awaiting_screenshot":
        await callback_query.answer("Haan haan, kripya apna payment screenshot jaldi bhejo na! 🥰")
        await callback_query.message.reply_text(
            "Ab tum apna payment screenshot bhej sakte ho. Jaldi se bhej do, main dekhna chahti hoon! 👇",
            reply_markup=ForceReply(True) 
        )
        user_states_collection.update_one(
            {"user_id": user_id},
            {"$set": {"status": "expecting_screenshot"}}
        )
        logger.info(f"User {user_id} clicked screenshot prompt, status set to expecting_screenshot.")
    else:
        await callback_query.answer("Arre! Kuch gadbad ho gayi, kripya /clonebot se dobara shuru karo na! 🥺", show_alert=True)
        if user_states_collection is not None: 
            user_states_collection.delete_one({"user_id": user_id})
        logger.warning(f"User {user_id} tried screenshot prompt from wrong state: {user_state.get('status') if user_state else 'None'}")


# Step 3: Receive screenshot and send to owner for approval
@app.on_message(filters.photo & filters.private)
async def receive_screenshot(client: Client, message: Message):
    user_id = str(message.from_user.id)
    
    if user_states_collection is None:
        await message.reply_text("Maaf karna, service abhi available nahi hai. Database (Clone/State DB) connect nahi ho paya hai. 🥺")
        await store_message(message) 
        return

    user_state = user_states_collection.find_one({"user_id": user_id})
    logger.info(f"Received photo from user {user_id}. User state: {user_state.get('status') if user_state else 'None'}")

    # FIX: Check if the message is a reply to the bot's *specific* ForceReply message.
    # This is more robust than just checking for any ForceReply.
    # Assuming the bot's ForceReply message would be the *previous* message sent by the bot to the user.
    is_reply_to_bot_force_reply = False
    if message.reply_to_message and message.reply_to_message.from_user and message.reply_to_message.from_user.is_self:
        # Fetch the message to which the user replied to check its reply_markup
        try:
            replied_to_msg = await client.get_messages(message.chat.id, message.reply_to_message.id)
            if replied_to_msg and isinstance(replied_to_msg.reply_markup, ForceReply):
                is_reply_to_bot_force_reply = True
        except Exception as e:
            logger.warning(f"Could not fetch replied_to_message for ForceReply check: {e}")

    if is_reply_to_bot_force_reply:
        if user_state and user_state.get("status") == "expecting_screenshot":
            await message.reply_text(
                "Aapka pyaara screenshot mujhe mil gaya hai! ✅\n"
                "Abhi woh mere Malik ke paas approval ke liye gaya hai. Malik jaise hi approve karenge, "
                "tum phir se `/clonebot` command de kar apna clone bana sakoge! Thoda wait karo na! 😉"
            )
            
            caption = f"💰 **Payment Proof (Malik, Dekho!):**\n" \
                      f"User: {message.from_user.mention} (`{user_id}`)\n" \
                      f"Amount: ₹{PAYMENT_INFO['amount']}"
            
            approve_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Clone Approve Karo Na! 🥰", callback_data=f"approve_clone_{user_id}")],
                [InlineKeyboardButton("❌ Reject Karo! 😤", callback_data=f"reject_clone_{user_id}")]
            ])
            
            await app.send_photo(
                chat_id=OWNER_ID,
                photo=message.photo.file_id,
                caption=caption,
                reply_markup=approve_keyboard
            )
            logger.info(f"Screenshot received from user {user_id}. Sent to owner for approval.")
            
            if user_states_collection is not None: 
                user_states_collection.update_one(
                    {"user_id": user_id},
                    {"$set": {"status": "pending_approval", "screenshot_message_id": message.id}}
                )
        else:
            await message.reply_text("Yeh screenshot abhi mujhe samajh nahi aaya. Kya tum /clonebot se dobara shuru karoge? 🤔")
            logger.warning(f"Photo received from user {user_id} but not in expected state for screenshot: {user_state.get('status') if user_state else 'None'}")
    else:
        logger.debug(f"Ignoring photo from {user_id}: not a reply to ForceReply in clone flow or user state incorrect.")
        # If it's just a random photo in private chat, store it.
        await store_message(message)


# Step 4: Owner approves/rejects clone request
@app.on_callback_query(filters.regex(r"^(approve_clone|reject_clone)_(\d+)$") & filters.create(owner_only_filter))
async def handle_clone_approval(client: Client, callback_query: CallbackQuery):
    action, target_user_id = callback_query.data.split('_', 1)[0], callback_query.data.split('_', 1)[1] # FIX: Split correctly
    
    if user_states_collection is None:
        await callback_query.answer("Maaf karna, service abhi available nahi hai. Database (Clone/State DB) connect nahi ho paya hai. 🥺", show_alert=True)
        return

    user_state = user_states_collection.find_one({"user_id": target_user_id})

    if not user_state or user_state.get("status") != "pending_approval":
        await callback_query.answer("Arre! Yeh request ab valid nahi hai ya pehle hi process ho chuki hai, Malik! 🙄", show_alert=True)
        # FIX: Ensure callback query message is edited to reflect status even if already processed by another click
        try:
            await callback_query.message.edit_caption(
                caption=callback_query.message.caption + "\n\n(Already processed/Invalid request)",
                reply_markup=None
            )
        except Exception as e:
            logger.warning(f"Error editing already processed approval message: {e}")
        return

    new_caption_suffix = f"\n\n**Admin ne {'Approve Kar Diya! ✅' if 'approve' in action else 'Reject Kar Diya! ❌'}**"
    
    try:
        await callback_query.message.edit_caption(
            caption=callback_query.message.caption + new_caption_suffix,
            reply_markup=None
        )
    except Exception as e:
        logger.error(f"Error editing owner's message for approval: {e}", exc_info=True)
        await client.send_message(OWNER_ID, f"Maaf karna Malik, user {target_user_id} ke message ko edit nahi kar payi. {action} status: {new_caption_suffix}")

    if "approve" in action:
        if user_states_collection is not None: 
            user_states_collection.update_one(
                {"user_id": target_user_id},
                {"$set": {"status": "approved_for_clone", "approved_on": datetime.now()}}
            )
        await client.send_message(
            int(target_user_id),
            "Badhai ho, mere dost! 🎉 Tumhari Bot Cloning request approve ho gayi hai! ✅\n"
            "Ab tum apni pyaari si bot banane ke liye token bhej sakte ho:\n"
            "**Kaise?** `/clonebot YOUR_BOT_TOKEN_HERE`\n"
            "(Pura token ek hi line mein hona chahiye, jaldi karo na! 😉)"
        )
        logger.info(f"User {target_user_id} approved for cloning.")
    elif "reject" in action:
        if user_states_collection is not None: 
            user_states_collection.delete_one({"user_id": target_user_id}) 
        await client.send_message(
            int(target_user_id),
            "Maaf karna, darling! 😔 Tumhari Bot Cloning request reject ho gayi hai.\n"
            "Kisi bhi sawal ke liye mere Malik se contact karo na! 🥺"
        )
        logger.info(f"User {target_user_id} rejected for cloning.")
    
    await callback_query.answer(f"Request {'approved' if 'approve' in action else 'rejected'} for user {target_user_id}.", show_alert=True)


# Step 5: Process actual clonebot command after approval
@app.on_message(filters.command("clonebot") & filters.private & filters.regex(r'/clonebot\s+([A-Za-z0-9:_-]+)'))
async def process_clone_bot_after_approval(client: Client, message: Message):
    user_id = str(message.from_user.id)
    
    if user_states_collection is None:
        await message.reply_text("Maaf karna, abhi bot cloning service available nahi hai. Database (Clone/State DB) connect nahi ho paya hai. 🥺")
        await store_message(message)
        return

    user_state = user_states_collection.find_one({"user_id": user_id, "status": "approved_for_clone"})

    if not user_state:
        await message.reply_text("Arre, tum bot clone karne ke liye approved nahi ho! 🥺 Kripya pehle payment process poora karo na! 😉")
        return

    bot_token = message.command[1].strip()
    if not re.match(r'^\d+:[A-Za-z0-9_-]+$', bot_token):
        await message.reply_text("Yeh bot token sahi nahi lag raha. Kripya ek valid token dein. Main confuse ho gayi! 😵‍💫")
        return

    await message.reply_text("Tumhare bot token ki jaanch kar rahi hoon, darling! Thoda wait karo... 💖")
    
    try:
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
            f"Wow! Tumhara bot **@{bot_info.username}** successfully connect ho gaya! ✅\n"
            "Ab apne cute cloned bot ke liye update channel set karo. "
            "\nKripya apne Update Channel ka Username/Link bhejien (jaise `@myupdates` ya `https://t.me/myupdates`)."
            "\nAgar tum apna channel nahi lagana chahte, toh bas `no` type kar do. Mera default channel (@asbhai_bsr) set ho jayega. Jaldi karo na! 😉"
            , reply_markup=ForceReply(True)
        )
        logger.info(f"Bot token valid for user {user_id}. Proceeding to channel setup.")
        if user_states_collection is not None: 
            user_states_collection.update_one(
                {"user_id": user_id},
                {"$set": {"status": "awaiting_channel", "bot_token": bot_token, "bot_username": bot_info.username}}
            )

    except exceptions.unauthorized.BotTokenInvalid:
        await message.reply_text("Arre! Yeh bot token invalid hai. Kripya sahi token dein na, please! 🥺")
        logger.warning(f"Bot token invalid during cloning for user {user_id}.")
        if user_states_collection is not None: 
            user_states_collection.update_one({"user_id": user_id}, {"$set": {"status": "approved_for_clone"}})
    except (exceptions.bad_request.ApiIdInvalid, exceptions.bad_request.ApiIdPublishedFlood):
        await message.reply_text("Hamare API ID/HASH mein kuch problem hai, darling! 😭 Kripya bot owner se contact karein. Yeh toh sad ho gaya!")
        logger.error(f"API ID/HASH issue during bot cloning attempt by user {user_id}.")
        if user_states_collection is not None: 
            user_states_collection.update_one({"user_id": user_id}, {"$set": {"status": "approved_for_clone"}})
    except Exception as e:
        await message.reply_text(f"Bot connect karne mein error aaya, darling: `{e}`\nKripya dobara koshish karein ya sahi token dein. Mujhse ho nahi raha! 😭")
        logger.error(f"Error during bot cloning for user {user_id}: {e}", exc_info=True)
        if user_states_collection is not None: 
            user_states_collection.update_one({"user_id": user_id}, {"$set": {"status": "approved_for_clone"}})
    finally:
        pass

    await store_message(message) 

# Step 6: Receive update channel link and finalize clone
@app.on_message(filters.text & filters.private)
async def finalize_clone_process(client: Client, message: Message):
    user_id = str(message.from_user.id)
    
    if user_states_collection is None:
        return 

    user_state = user_states_collection.find_one({"user_id": user_id, "status": "awaiting_channel"})

    is_reply_to_bot_force_reply = False
    if message.reply_to_message and message.reply_to_message.from_user.is_self:
        try:
            replied_to_msg = await client.get_messages(message.chat.id, message.reply_to_message.id)
            if replied_to_msg and isinstance(replied_to_msg.reply_markup, ForceReply):
                is_reply_to_bot_force_reply = True
        except Exception as e:
            logger.warning(f"Could not fetch replied_to_message for ForceReply check in finalize_clone_process: {e}")

    if not user_state or not is_reply_to_bot_force_reply:
        return # Not in the cloning flow or not replying to the correct ForceReply

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
                    await message.reply_text("Yeh ek valid channel username/link nahi lag raha, darling! Kripya sahi channel ka username (@channelname) ya link (t.me/channelname) dein, ya 'no' type karo. Mujhko samjho na! 🥺")
                    return
            except Exception as e:
                logger.warning(f"Could not verify channel {final_update_channel}: {e}")
                await message.reply_text("Channel ko verify nahi kar payi, darling! Kripya sahi channel ka username (@channelname) ya link (t.me/channelname) dein, ya 'no' type karo. Kya main galti kar rahi hoon? 😔")
                return
            
            logger.info(f"User {user_id} set update channel to @{final_update_channel}")
        else:
            await message.reply_text("Invalid channel username/link, darling! Kripya sahi channel ka username (@channelname) ya link (t.me/channelname) dein, ya 'no' type karo. Main confusion mein hoon! 😵‍💫")
            return

    else:
        logger.info(f"User {user_id} chose default update channel: @{DEFAULT_UPDATE_CHANNEL_USERNAME}")
    
    await message.reply_text(
        "Badhai ho, mere cute dost! 🎉 Tumhare bot ke liye saari settings complete ho gayi hain.\n\n"
        "Ab tum is pyaare bot ko deploy kar sakte ho! Tumhara bot token aur update channel niche diye gaye hain:\n"
        f"**Bot Token:** `{user_state['bot_token']}`\n"
        f"**Bot Username:** `@{user_state['bot_username']}`\n"
        f"**Meri Updates:** `@{final_update_channel}`\n\n" 
        "**Deployment ke liye easy steps:**\n"
        "1. Meri GitHub repository ko fork karo (agar nahi kiya hai toh).\n"
        "2. Apni forked repository mein `main.py` file mein `DEFAULT_UPDATE_CHANNEL_USERNAME` ko `'{final_update_channel}'` par set kar dena.\n" # Changed instruction
        "3. Fir, Koyeb (ya kisi bhi hosting) par deploy karo, Environment Variables mein `BOT_TOKEN`, `API_ID`, `API_HASH`, `OWNER_ID`, `MAIN_MONGO_DB_URI`, `CLONE_STATE_MONGO_DB_URI`, `COMMANDS_SETTINGS_MONGO_DB_URI` (aur apne naye bot token aur APIs) ko sahi se set karna mat bhoolna!\n"
        "4. Fir dekho mera jaisa pyaara bot kaise kaam karta hai! 💖\n\n"
        "Kisi bhi sawal ke liye @aschat_group channel par aana na bhoolna! Main wahin milungi! 😉" 
    )
    
    if user_states_collection is not None: 
        user_states_collection.delete_one({"user_id": user_id})
    logger.info(f"User {user_id} clone process finalized and state cleared.")
    await store_message(message) 


# --- Private Chat Non-Command Message Handler ---
@app.on_message(filters.private & filters.text & ~filters.via_bot & (lambda _, __, msg: not msg.text.startswith('/')) & (lambda _, __, msg: not msg.reply_to_message or not msg.reply_to_message.from_user.is_self or not isinstance(msg.reply_to_message.reply_markup, ForceReply)))
async def handle_private_non_command_messages(client: Client, message: Message):
    user_id = str(message.from_user.id)
    
    if user_states_collection is None:
        await message.reply_text("Maaf karna, bot abhi poori tarah se ready nahi hai. Kuch database issues hain (Clone/State DB connect nahi ho paya). 🥺")
        await store_message(message) 
        return

    user_state = user_states_collection.find_one({"user_id": user_id})

    # If user is in any cloning state, don't interfere, let the cloning handlers manage
    if user_state is not None and user_state.get("status") in ["awaiting_screenshot", "expecting_screenshot", "awaiting_channel", "pending_approval"]:
        return 

    # Otherwise, prompt user to use commands
    await message.reply_text(
        "Hehe, darling! Main abhi sirf commands samajhti hoon. 😉\n"
        "Apne sawal poochne ke liye kripya commands ka hi use karein na! Jaise `/help` ya `/start`."
    )
    await store_message(message) 

# --- Standard message handler (general text/sticker messages in groups, or bot replies in private) ---
@app.on_message(filters.text | filters.sticker)
async def handle_general_messages(client: Client, message: Message):
    global last_bot_reply_time

    if message.from_user and message.from_user.is_bot:
        return 
    
    # Updated: If it's a private chat and not a command, let handle_private_non_command_messages handle it.
    # This prevents the bot from trying to "learn" from general private chat messages.
    # The ForceReply condition is added to the private handler now, so here we can just check if it's a private chat.
    if message.chat.type == "private" and message.text and not message.text.startswith('/'):
        # Only store if it's a regular message not part of a ForceReply flow for the private handler
        user_id = str(message.from_user.id)
        if user_states_collection is not None:
            user_state = user_states_collection.find_one({"user_id": user_id})
            is_in_clone_flow = user_state is not None and user_state.get("status") in ["awaiting_screenshot", "expecting_screenshot", "awaiting_channel", "pending_approval"]
            is_reply_to_bot_force_reply = False
            if message.reply_to_message and message.reply_to_message.from_user.is_self:
                try:
                    replied_to_msg = await client.get_messages(message.chat.id, message.reply_to_message.id)
                    if replied_to_msg and isinstance(replied_to_msg.reply_markup, ForceReply):
                        is_reply_to_bot_force_reply = True
                except Exception as e:
                    logger.warning(f"Could not fetch replied_to_message for ForceReply check in general handler: {e}")

            if not is_in_clone_flow and not is_reply_to_bot_force_reply:
                await store_message(message, is_bot_sent=False)
        else: # If user_states_collection is None, still store the message
            await store_message(message, is_bot_sent=False)
        return # Let the specific private handler manage the reply or non-reply

    # Store incoming message for learning (always store, even if not replying immediately)
    await store_message(message, is_bot_sent=False)
    
    # Only generate replies in groups for non-command messages
    if message.chat.type != "private" and message.text and not message.text.startswith('/'): 
        chat_id = message.chat.id
        current_time = time.time()

        # Check cooldown *before* generating reply
        if chat_id in last_bot_reply_time:
            time_since_last_reply = current_time - last_bot_reply_time[chat_id]
            if time_since_last_reply < REPLY_COOLDOWN_SECONDS:
                logger.info(f"Cooldown active for chat {chat_id}. Not generating reply for message {message.id}.")
                return 

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
                    last_bot_reply_time[chat_id] = time.time()
                    await store_message(sent_msg, is_bot_sent=True, sent_message_id=sent_msg.id)
            except Exception as e:
                logger.error(f"Error sending reply for message {message.id}: {e}", exc_info=True)
        else:
            logger.info(f"No suitable reply generated for message {message.id}.")


# --- Flask Web Server for Health Check ---
flask_app = Flask(__name__)

@flask_app.route('/')
def health_check():
    mongo_status_main = "Disconnected"
    mongo_status_clone_state = "Disconnected"
    mongo_status_commands_settings = "Disconnected"
    try:
        if main_mongo_client is not None:
            main_mongo_client.admin.command('ping')
            mongo_status_main = "Connected"
    except Exception: pass
    try:
        if clone_state_mongo_client is not None:
            clone_state_mongo_client.admin.command('ping')
            mongo_status_clone_state = "Connected"
    except Exception: pass
    try:
        if commands_settings_mongo_client is not None:
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
    # Setting host='0.0.0.0' makes it accessible externally
    flask_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False, threaded=True)

# --- Main entry point ---
if __name__ == "__main__":
    logger.info("Cutie Pie bot running. ✨") 
    
    flask_thread = Thread(target=run_flask_app)
    flask_thread.daemon = True # Daemon threads exit when the main program exits
    flask_thread.start()

    app.run()
