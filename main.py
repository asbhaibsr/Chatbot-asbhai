# Credit by @asbhaibsr and Telegram Channel @asbhai_bsr

import os
import asyncio
import re
import random
import logging
from datetime import datetime, timedelta
from threading import Thread
import time 
import sys # Added for sys.executable

# Pyrogram imports
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ForceReply
from pyrogram.enums import ChatType, ChatMemberStatus # Added ChatMemberStatus
from pyrogram.raw.functions.messages import SetTyping
from pyrogram.raw.types import SendMessageTypingAction
from pyrogram.errors import exceptions 

# MongoDB imports
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure 

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

# MongoDB URIs
MAIN_MONGO_DB_URI = os.getenv("MAIN_MONGO_DB_URI") 
CLONE_STATE_MONGO_DB_URI = os.getenv("CLONE_STATE_MONGO_DB_URI") 
COMMANDS_SETTINGS_MONGO_DB_URI = os.getenv("COMMANDS_SETTINGS_MONGO_DB_URI")

# --- Constants ---
MAX_MESSAGES_THRESHOLD = 100000
PRUNE_PERCENTAGE = 0.30
DEFAULT_UPDATE_CHANNEL_USERNAME = "asbhai_bsr" # यह आपके डिफ़ॉल्ट अपडेट चैनल का यूजरनेम है
REPLY_COOLDOWN_SECONDS = 3 

# --- Payment Details ---
PAYMENT_INFO = {
    "amount": "200",
    "upi_id": "arsadsaifi8272@ibl", 
    "qr_code_url": "", # <--- यदि आपके पास QR कोड URL है तो यहाँ डालें, अन्यथा खाली छोड़ दें।
    "instructions": "UPI ID par ₹200 bhejien aur payment ka screenshot 'Screenshot Bhejein' button par click karke bhejen."
}

# --- MongoDB Setup for all three connections ---
main_mongo_client = None
main_db = None
messages_collection = None 

logger.info(f"Attempting to connect to Main Learning MongoDB. MAIN_MONGO_DB_URI: {'[SET]' if MAIN_MONGO_DB_URI else '[NOT SET]'}")
if MAIN_MONGO_DB_URI:
    try:
        main_mongo_client = MongoClient(MAIN_MONGO_DB_URI, serverSelectionTimeoutMS=5000)
        main_mongo_client.admin.command('ping')
        main_db = main_mongo_client.bot_learning_database # डेटाबेस का नाम
        messages_collection = main_db.messages # सीखे हुए संदेश/स्टिकर
        logger.info("MongoDB (Main Learning DB) connection successful.")
    except ServerSelectionTimeoutError as err:
        logger.error(f"MongoDB (Main Learning DB) connection timed out: {err}")
        messages_collection = None 
    except ConnectionFailure as err:
        logger.error(f"MongoDB (Main Learning DB) connection failed: {err}")
        messages_collection = None
    except Exception as e:
        logger.error(f"An unexpected error occurred while connecting to Main Learning MongoDB: {e}", exc_info=True)
        messages_collection = None
else:
    logger.error("MAIN_MONGO_DB_URI environment variable is NOT SET. Main learning database will not be functional.")


clone_state_mongo_client = None
clone_state_db = None
user_states_collection = None 

logger.info(f"Attempting to connect to Clone/State MongoDB. CLONE_STATE_MONGO_DB_URI: {'[SET]' if CLONE_STATE_MONGO_DB_URI else '[NOT SET]'}")
if CLONE_STATE_MONGO_DB_URI:
    try:
        clone_state_mongo_client = MongoClient(CLONE_STATE_MONGO_DB_URI, serverSelectionTimeoutMS=5000)
        clone_state_mongo_client.admin.command('ping') 
        clone_state_db = clone_state_mongo_client.bot_clone_states_db # डेटाबेस का नाम
        user_states_collection = clone_state_db.user_states # क्लोनिंग रिक्वेस्ट की स्थिति
        logger.info("MongoDB (Clone/State DB) connection successful.")
    except ServerSelectionTimeoutError as err:
        logger.error(f"MongoDB (Clone/State DB) connection timed out: {err}")
        user_states_collection = None
    except ConnectionFailure as err:
        logger.error(f"MongoDB (Clone/State DB) connection failed: {err}")
        user_states_collection = None
    except Exception as e:
        logger.error(f"Failed to connect to Clone/State MongoDB: {e}", exc_info=True)
        user_states_collection = None
else:
    logger.error("CLONE_STATE_MONGO_DB_URI environment variable is NOT SET. Clone/State database will not be functional.")


commands_settings_mongo_client = None
commands_settings_db = None
group_configs_collection = None 

logger.info(f"Attempting to connect to Commands/Settings MongoDB. COMMANDS_SETTINGS_MONGO_DB_URI: {'[SET]' if COMMANDS_SETTINGS_MONGO_DB_URI else '[NOT SET]'}")
if COMMANDS_SETTINGS_MONGO_DB_URI:
    try:
        commands_settings_mongo_client = MongoClient(COMMANDS_SETTINGS_MONGO_DB_URI, serverSelectionTimeoutMS=5000)
        commands_settings_mongo_client.admin.command('ping') 
        commands_settings_db = commands_settings_mongo_client.bot_settings_db # डेटाबेस का नाम
        group_configs_collection = commands_settings_db.group_configs # ग्रुप सेटिंग्स
        logger.info("MongoDB (Commands/Settings DB) connection successful.")
    except ServerSelectionTimeoutError as err:
        logger.error(f"MongoDB (Commands/Settings DB) connection timed out: {err}")
        group_configs_collection = None
    except ConnectionFailure as err:
        logger.error(f"MongoDB (Commands/Settings DB) connection failed: {err}")
        group_configs_collection = None
    except Exception as e:
        logger.error(f"Failed to connect to Commands/Settings MongoDB: {e}", exc_info=True)
        group_configs_collection = None
else:
    logger.error("COMMANDS_SETTINGS_MONGO_DB_URI environment variable is NOT SET. Commands/Settings database will not be functional.")


# --- Pyrogram Client ---
app = Client(
    "self_learning_bot",
    api_id=int(API_ID) if API_ID else None, # Ensure API_ID is int
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# --- Global variable to track last reply time per chat ---
last_bot_reply_time = {}


# --- Utility Functions ---

def extract_keywords(text):
    if not text: return []
    # Using more robust word extraction, lowercasing, and unique words
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
            # Find _id of messages to delete, sorted by timestamp
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
    if messages_collection is None:
        logger.error("messages_collection is NOT initialized. Cannot store message. Please check MongoDB connection for MAIN_MONGO_DB_URI.")
        return

    try:
        # Ignore messages sent by other bots
        if message.from_user and message.from_user.is_bot and not is_bot_sent:
            logger.debug(f"Ignoring message from another bot: {message.from_user.id}")
            return

        content_type = "text"
        file_id = None
        if message.sticker:
            content_type = "sticker"
            file_id = message.sticker.file_id
        elif message.photo:
            content_type = "photo"
            file_id = message.photo.file_id
        elif message.video:
            content_type = "video"
            file_id = message.video.file_id
        elif message.document:
            content_type = "document"
            file_id = message.document.file_id
        elif message.audio:
            content_type = "audio"
            file_id = message.audio.file_id
        elif message.voice:
            content_type = "voice"
            file_id = message.voice.file_id
        elif message.animation:
            content_type = "animation"
            file_id = message.animation.file_id
        # Add more content types if needed for learning and replying with them

        message_data = {
            "message_id": message.id,
            "user_id": message.from_user.id if message.from_user else None,
            "username": message.from_user.username if message.from_user else None,
            "first_name": message.from_user.first_name if message.from_user else None,
            "chat_id": message.chat.id,
            "chat_type": message.chat.type.name,
            "chat_title": message.chat.title if message.chat.type != ChatType.PRIVATE else None,
            "timestamp": datetime.now(),
            "is_bot_sent": is_bot_sent,
            "content_type": content_type,
            "content": message.text if message.text else (message.sticker.emoji if message.sticker else ""), # Store emoji for stickers
            "file_id": file_id, # Store file_id for media types
            "keywords": extract_keywords(message.text) if message.text else extract_keywords(message.sticker.emoji if message.sticker else ""),
            "replied_to_message_id": None,
            "replied_to_user_id": None,
            "replied_to_content": None,
            "replied_to_content_type": None,
            "is_bot_observed_pair": False, # Is this message a direct reply to bot's message?
        }

        # Store reply-to information
        if message.reply_to_message:
            message_data["replied_to_message_id"] = message.reply_to_message.id
            if message.reply_to_message.from_user:
                message_data["replied_to_user_id"] = message.reply_to_message.from_user.id

            replied_to_content = message.reply_to_message.text
            replied_to_content_type = "text"
            if message.reply_to_message.sticker:
                replied_to_content = message.reply_to_message.sticker.emoji
                replied_to_content_type = "sticker"
            elif message.reply_to_message.photo:
                replied_to_content = message.reply_to_message.caption # If photo has caption
                replied_to_content_type = "photo"
            elif message.reply_to_message.video:
                replied_to_content = message.reply_to_message.caption # If video has caption
                replied_to_content_type = "video"
            elif message.reply_to_message.document:
                replied_to_content = message.reply_to_message.caption # If document has caption
                replied_to_content_type = "document"
            elif message.reply_to_message.audio:
                replied_to_content = message.reply_to_message.caption # If audio has caption
                replied_to_content_type = "audio"
            elif message.reply_to_message.voice:
                replied_to_content = message.reply_to_message.caption # If voice has caption
                replied_to_content_type = "voice"
            elif message.reply_to_message.animation:
                replied_to_content = message.reply_to_message.caption # If animation has caption
                replied_to_content_type = "animation"
            # Add more replied_to_content_type logic for other media types if needed

            message_data["replied_to_content"] = replied_to_content
            message_data["replied_to_content_type"] = replied_to_content_type

            # Check if this message is a user's reply to the bot's own message
            if message.reply_to_message.from_user and message.reply_to_message.from_user.is_self:
                message_data["is_bot_observed_pair"] = True
                logger.debug(f"Observed user reply to bot's message ({message.reply_to_message.id}). Marking this as observed pair.")
                # Also, update the bot's sent message in DB to mark it as part of an observed pair
                if messages_collection is not None:
                    messages_collection.update_one(
                        {"chat_id": message.chat.id, "message_id": message.reply_to_message.id, "is_bot_sent": True},
                        {"$set": {"has_received_reply": True, "replied_by_user_id": message.from_user.id}}
                    )

        if messages_collection is not None:
            messages_collection.insert_one(message_data)
            logger.debug(f"Message stored: {message.id} from {message.from_user.id if message.from_user else 'None'}. Bot sent: {is_bot_sent}. Content Type: {content_type}")
            await prune_old_messages()
        else:
            logger.error("messages_collection is STILL None after initial check. This should not happen here.")
    except ServerSelectionTimeoutError as e:
        logger.error(f"MongoDB connection error while storing message {message.id}: {e}")
    except Exception as e:
        logger.error(f"Error storing message {message.id}: {e}", exc_info=True)


async def generate_reply(message: Message):
    await app.invoke(SetTyping(peer=await app.resolve_peer(message.chat.id), action=SendMessageTypingAction()))
    await asyncio.sleep(0.5)

    query_content = message.text if message.text else (message.sticker.emoji if message.sticker else "")
    query_keywords = extract_keywords(query_content)

    if not query_keywords and not query_content and not message.sticker and not message.photo and not message.video and not message.document and not message.audio and not message.voice and not message.animation:
        logger.debug("No meaningful content extracted for reply generation.")
        return None

    if messages_collection is None:
        logger.warning("messages_collection is None. Cannot generate reply.")
        return None

    # Determine the content type of the incoming message for better matching
    message_actual_content_type = "text"
    if message.sticker:
        message_actual_content_type = "sticker"
    elif message.photo:
        message_actual_content_type = "photo"
    elif message.video:
        message_actual_content_type = "video"
    elif message.document:
        message_actual_content_type = "document"
    elif message.audio:
        message_actual_content_type = "audio"
    elif message.voice:
        message_actual_content_type = "voice"
    elif message.animation:
        message_actual_content_type = "animation"


    # --- Strategy 1: Contextual Reply (User's reply to a message) ---
    # This is for "Hello" -> "Han ji bolo" type learning when the bot is the "Hello" part.
    # OR, if user replies to another user's "Hello" and the bot observes this.
    if message.reply_to_message:
        replied_to_content = message.reply_to_message.text if message.reply_to_message.text else (message.reply_to_message.sticker.emoji if message.reply_to_message.sticker else "")
        replied_to_content_type = "text"
        if message.reply_to_message.sticker:
            replied_to_content_type = "sticker"
        elif message.reply_to_message.photo:
            replied_to_content_type = "photo"
        elif message.reply_to_message.video:
            replied_to_content_type = "video"
        elif message.reply_to_message.document:
            replied_to_content_type = "document"
        elif message.reply_to_message.audio:
            replied_to_content_type = "audio"
        elif message.reply_to_message.voice:
            replied_to_content_type = "voice"
        elif message.reply_to_message.animation:
            replied_to_content_type = "animation"

        if replied_to_content:
            logger.info(f"Strategy 1: Searching for contextual replies to replied_to_content: '{replied_to_content}' (Type: {replied_to_content_type})")
            
            # Find messages that *are replies* to content similar to `replied_to_content`
            # and prefer those that were *not* sent by the bot (human-like interactions).
            contextual_query = {
                "replied_to_content": {"$regex": f"^{re.escape(replied_to_content)}$", "$options": "i"},
                "replied_to_content_type": replied_to_content_type,
                "is_bot_sent": False, # Prioritize human-observed replies
            }

            # If in a group, prioritize replies observed within that group first
            if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
                group_contextual_matches = list(messages_collection.find({"chat_id": message.chat.id, **contextual_query}))
                if group_contextual_matches:
                    logger.info(f"Found {len(group_contextual_matches)} group-specific contextual replies.")
                    return random.choice(group_contextual_matches)

            # Fallback to global contextual matches
            global_contextual_matches = list(messages_collection.find(contextual_query))
            if global_contextual_matches:
                logger.info(f"Found {len(global_contextual_matches)} global contextual replies.")
                return random.choice(global_contextual_matches)
        
        logger.info(f"No direct contextual reply found for replied_to_content: '{replied_to_content}'.")

    # --- Strategy 2: Keyword-based General Reply (including partial match and content type) ---
    logger.info(f"Strategy 2: Falling back to keyword/content search for: '{query_content}' (Type: {message_actual_content_type}) with keywords {query_keywords}")

    # Build the query for keyword matching and content type matching
    content_match_conditions = []

    # Add exact content match if it's text or sticker emoji
    if query_content:
        content_match_conditions.append({"content": {"$regex": f"^{re.escape(query_content)}$", "$options": "i"}})

    # Add keyword-based fuzzy search for text content
    if query_keywords:
        for kw in query_keywords:
            content_match_conditions.append({"content": {"$regex": f".*{re.escape(kw)}.*", "$options": "i"}})

    # Add file_id match for media if the incoming message is media
    if message.sticker and message.sticker.file_id:
        content_match_conditions.append({"file_id": message.sticker.file_id, "content_type": "sticker"})
    elif message.photo and message.photo.file_id:
        content_match_conditions.append({"file_id": message.photo.file_id, "content_type": "photo"})
    elif message.video and message.video.file_id:
        content_match_conditions.append({"file_id": message.video.file_id, "content_type": "video"})
    # Add conditions for other media types if you want to match them specifically

    final_query_conditions = {
        "is_bot_sent": False, # Prefer replies learned from human messages
    }
    
    if content_match_conditions:
        final_query_conditions["$or"] = content_match_conditions

    # Prefer content of same type as query, or text/sticker if query is media
    # This helps in responding to a sticker with a sticker, or text with text
    target_reply_content_types = ["text", "sticker"] # Default for now
    if message_actual_content_type in ["photo", "video", "document", "audio", "voice", "animation"]:
        target_reply_content_types.append(message_actual_content_type)
    
    final_query_conditions["content_type"] = {"$in": target_reply_content_types}

    potential_replies = []
    # Prioritize group-specific content for group chats
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        group_specific_query = {"chat_id": message.chat.id, **final_query_conditions}
        potential_replies.extend(list(messages_collection.find(group_specific_query)))
        logger.info(f"Found {len(potential_replies)} group-specific keyword/content matches.")
            
    # Always perform a global search as a fallback or for private chats
    global_query = {**final_query_conditions}
    potential_replies.extend(list(messages_collection.find(global_query)))
    logger.info(f"Found {len(potential_replies) - (len(group_specific_query) if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP] else 0)} global keyword/content matches.")


    # Filter out replies that are identical to the query message (to avoid loops or boring replies)
    # Also ensure the chosen reply is not the *same instance* of the message just received
    # and not a message sent by the bot itself in response previously (unless it's part of an observed pattern).
    
    if potential_replies:
        # Deduplicate, as a message might be found via both group and global search
        unique_replies = {doc['_id']: doc for doc in potential_replies}.values()
        
        filtered_replies = []
        for doc in unique_replies:
            # Avoid replying with the exact same text/emoji content to the user's query
            if doc.get("content", "").lower() == query_content.lower() and doc.get("content_type") == message_actual_content_type:
                continue
            
            # Avoid replying with the exact same media file_id
            if doc.get("file_id") and doc.get("file_id") == (message.sticker.file_id if message.sticker else (message.photo.file_id if message.photo else (message.video.file_id if message.video else None))):
                continue

            # Ensure the reply isn't the bot's own previous response that wasn't part of a learning pair
            # Or, if it was a bot's reply, ensure it was to a different query
            if doc.get("is_bot_sent", False):
                continue # For now, strictly prefer human-generated content to reply from
            
            filtered_replies.append(doc)
        
        if filtered_replies:
            logger.info(f"After filtering, {len(filtered_replies)} suitable replies remain.")
            return random.choice(filtered_replies)
        else:
            logger.info("All potential replies were filtered out.")

    logger.info(f"No suitable keyword/content reply found for: '{query_content}'.")

    # --- Strategy 3: Fallback generic replies ---
    fallback_messages = [
        "Hmm, main is bare mein kya kahoon?",
        "Interesting! Aur kuch?",
        "Main sun rahi hoon... 👋",
        "Aapki baat sunkar acha laga!",
        "Kya haal-chal?",
        "Aapki baat sunkar main bhi kuch kehna chahti hoon! 😉",
        "Mujhe samajh nahi aaya, phir se batao na! 💖",
        "Achha, theek hai! 🤔",
        "Aur sunao, kya chal raha hai? 😊",
        "Kya mast baat boli! 🥰",
        "Main bhi yahi soch rahi thi! 💭",
        "Kya baat hai! Aur kya naya hai? ✨",
        "Tumhari baatein toh kamaal hain! 😄",
        "Mere paas toh shabd hi nahi hain! 😶",
        "Main sikhti rahungi, tum bas bolte raho! 📚"
    ]
    # Add a random chance to not send a fallback message in private chats
    if message.chat.type == ChatType.PRIVATE and random.random() < 0.2: # 20% chance to not send a fallback in private
        logger.info("Randomly decided not to send a fallback reply in private chat.")
        return None
        
    return {"content_type": "text", "content": random.choice(fallback_messages)}


# --- Pyrogram Event Handlers ---

# START COMMAND (PRIVATE CHAT)
@app.on_message(filters.command("start") & filters.private)
async def start_private_command(client: Client, message: Message):
    user_name = message.from_user.first_name if message.from_user else "mere pyare dost"
    welcome_message = (
        f"Hey, **{user_name}**! 👋 Main aa gayi hoon aapki baaton ka hissa banne. "
        "Mera naam hai **⎯᪵⎯꯭̽🤍꯭᪳ ⃪𝗖𝘂꯭𝘁𝗶𝗲꯭ 𝗣𝗶𝗲꯭ ⃪🌸͎᪳᪳𝆺꯭𝅥⎯꯭̽⎯꯭**!💖"
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
        [InlineKeyboardButton("📣 Meri Updates Yahan Milengi! 😉", url=f"https://t.me/{DEFAULT_UPDATE_CHANNEL_USERNAME}")] 
    ])
    await message.reply_text(welcome_message, reply_markup=keyboard)
    await store_message(message)

# START COMMAND (GROUP CHAT)
@app.on_message(filters.command("start") & filters.group)
async def start_group_command(client: Client, message: Message):
    welcome_messages = [
        "Hello, my lovely group! 👋 Main aa gayi hoon aapki conversations mein shamil hone. Yahan main aap sabki baaton se seekhti rahungi, aur sabko cute cute replies dungi! 🥰",
        "Hey everyone! 💖 Main yahan aap sab ki baatein sunne aur seekhne aayi hoon. Isse main aur smart replies de paungi. Chalo, ab group mein double masti hogi! 😉",
        "Namaste to all the amazing people here! ✨ Mujhe group mein add karne ka shukriya. Main yahan ki baaton ko samjh kar aur behtar hoti jaungi. Ab toh har baat par mera jawaab milega! 🤭"
    ]
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📣 Meri Updates Yahan Milengi! 😉", url=f"https://t.me/{DEFAULT_UPDATE_CHANNEL_USERNAME}")] 
    ])
    await message.reply_text(random.choice(welcome_messages), reply_markup=keyboard)
    await store_message(message)

# GENERAL STATS COMMAND
@app.on_message(filters.command("stats") & (filters.private | filters.group))
async def stats_command(client: Client, message: Message):
    if len(message.command) < 2 or message.command[1].lower() != "check":
        await message.reply_text("Hehe, agar mere stats dekhne hain toh aise bolo: `/stats check`. Main koi simple bot thodi na hoon! 😉")
        return

    if messages_collection is None:
        await message.reply_text("Maaf karna, statistics abhi available nahi hain. Database mein kuch gadbad hai. 🥺 (Main Learning DB connect nahi ho paya)")
        await store_message(message) 
        return

    total_messages = messages_collection.count_documents({})
    unique_group_ids = messages_collection.distinct("chat_id", {"chat_type": {"$in": ["group", "supergroup"]}})
    num_groups = len(unique_group_ids)

    # Clone stats
    total_clone_requests = 0
    pending_clone_requests = 0
    approved_clones = 0
    if user_states_collection is not None:
        total_clone_requests = user_states_collection.count_documents({})
        pending_clone_requests = user_states_collection.count_documents({"status": "pending_approval"})
        approved_clones = user_states_collection.count_documents({"status": "approved_for_clone"})
        
    stats_text = (
        "📊 **Meri Cute Cute Statistics** 📊\n"
        f"• Kitne groups mein main masti karti hoon: **{num_groups}**\n"
        f"• Kitne messages maine apne dimag mein store kiye hain: **{total_messages}**\n"
        f"• Total Clone Requests: **{total_clone_requests}**\n"
        f"• Pending Approvals: **{pending_clone_requests}**\n"
        f"• Approved Clones: **{approved_clones}**\n"
        "Ab batao, main smart hoon na? 🤩"
    )
    await message.reply_text(stats_text)
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
        "\n\n**Admin Commands (Sirf mere Malik aur Group Admins ke liye, shhh!):**" # Updated text
        "\n• `/broadcast <message>` - Sabko mera pyaara message bhejo! (Owner Only)"
        "\n• `/resetdata <percentage>` - Kuch purani yaadein mita do! (Agar data bahot ho jaye) (Owner Only)"
        "\n• `/deletemessage <message_id>` - Ek khaas message delete karo! (Owner Only)"
        "\n• `/ban <user_id_or_username>` - Gande logon ko group se bhagao! 😤 (Admins & Owner)" # Updated text
        "\n• `/unban <user_id_or_username>` - Acha, maaf kar do unhe! 😊 (Admins & Owner)" # Updated text
        "\n• `/kick <user_id_or_username>` - Thoda bahar ghuma ke lao! 😉 (Admins & Owner)" # Updated text
        "\n• `/pin <message_id>` - Important message ko upar rakho, sabko dikhe! ✨ (Admins & Owner)" # Updated text
        "\n• `/unpin` - Ab bas karo, bohot ho gaya pin! 😅 (Admins & Owner)" # Updated text
        "\n• `/setwelcome <message>` - Group mein naye guests ka swagat, mere style mein! 💖 (Admins & Owner)" # Updated text
        "\n• `/getwelcome` - Dekho maine kya welcome message set kiya hai! (Admins & Owner)" # Updated text
        "\n• `/clearwelcome` - Agar welcome message pasand nahi, toh hata do! 🤷‍♀️ (Admins & Owner)" # Updated text
        "\n• `/restart bot` - Mujhe dubara se shuru karo aur deploy kar do! (Owner Only! 🚨)" # Added
        "\n• `/resetall` - Saara data delete kar do, sab kuch! (Owner Only! 🚨🚨)" # Added
        "\n\n**Note:** Admin commands ke liye, mujhe group mein zaroori permissions dena mat bhoolna, warna main kuch nahi kar paungi! 🥺"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Mujhe Apne Group Mein Bulao! 😉", url=f"https://t.me/{client.me.username}?startgroup=true")],
        [InlineKeyboardButton("📣 Meri Updates Yahan Milengi! 💖", url=f"https://t.me/{DEFAULT_UPDATE_CHANNEL_USERNAME}")] 
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

# Admin check decorator for bot owner only
def owner_only_filter(_, __, message):
    if message.from_user is not None and OWNER_ID is not None:
        return is_owner(message.from_user.id)
    return False

# New decorator for group admins (including owner)
async def group_admin_filter(_, client, message):
    if not message.from_user:
        return False # यदि कोई यूजर नहीं है (जैसे चैनल पोस्ट)

    user_id = message.from_user.id
    chat_id = message.chat.id

    # बॉट ओनर हमेशा एडमिन कमांड चला सकता है
    if is_owner(user_id):
        return True

    # अगर निजी चैट है, और यूजर ओनर नहीं है, तो फॉल्स
    if message.chat.type == ChatType.PRIVATE:
        return False

    try:
        member = await client.get_chat_member(chat_id, user_id)
        # सदस्य की स्थिति OWNER या ADMINISTRATOR होनी चाहिए
        if member.status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
            return True
        else:
            return False
    except Exception as e:
        logger.error(f"Error checking admin status for user {user_id} in chat {chat_id}: {e}")
        return False # त्रुटि होने पर एडमिन नहीं माना जाएगा

# BROADCAST COMMAND
@app.on_message(filters.command("broadcast") & filters.private & filters.create(owner_only_filter))
async def broadcast_command(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("Malik, kripya broadcast karne ke liye ek pyaara sa message dein. Upyog: `/broadcast Aapka message yahan`")
        await store_message(message) 
        return
    broadcast_text = " ".join(message.command[1:])
    if messages_collection is None:
        await message.reply_text("Maaf karna, broadcast nahi kar payi. Database (Main Learning DB) connect nahi ho paya hai. 🥺")
        await store_message(message) 
        return

    unique_chat_ids = messages_collection.distinct("chat_id")
    sent_count = 0
    failed_count = 0
    await message.reply_text("Malik, main ab sabko aapka message bhej rahi hoon! 😉")
    for chat_id in unique_chat_ids:
        try:
            # Avoid sending broadcast to the owner's private chat again if it's already sent as a reply
            if chat_id == message.chat.id and message.chat.type == ChatType.PRIVATE:
                continue
            await client.send_message(chat_id, broadcast_text)
            sent_count += 1
            await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"Failed to send broadcast to chat {chat_id}: {e}")
            failed_count += 1
            await asyncio.sleep(0.5)
    await message.reply_text(f"Broadcast poora hua, Malik! {sent_count} chats ko bheja, {failed_count} chats ke liye asafal raha. Maine apna best diya! 🥰")
    await store_message(message) 

# RESET DATA COMMAND
@app.on_message(filters.command("resetdata") & filters.private & filters.create(owner_only_filter))
async def reset_data_command(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("Malik, kitna data delete karna hai? Percentage batao (1 se 100 ke beech). Upyog: `/resetdata <percentage>`")
        await store_message(message) 
        return
    try:
        percentage = int(message.command[1])
        if not (1 <= percentage <= 100):
            await message.reply_text("Percentage 1 se 100 ke beech hona chahiye, Malik! 😊")
            await store_message(message) 
            return

        if messages_collection is None:
            await message.reply_text("Maaf karna, data reset nahi kar payi. Database (Main Learning DB) connect nahi ho paya hai. 🥺")
            await store_message(message) 
            return

        total_messages = messages_collection.count_documents({})
        if total_messages == 0:
            await message.reply_text("Malik, database mein koi message hai hi nahi! Main kya delete karun? 🤷‍♀️")
            await store_message(message) 
            return

        messages_to_delete_count = int(total_messages * (percentage / 100))
        if messages_to_delete_count == 0 and percentage > 0 and total_messages > 0:
            messages_to_delete_count = 1

        if messages_to_delete_count == 0:
            await message.reply_text("Malik, itne kam messages hain ki diye gaye percentage par kuch delete nahi hoga. Kya karna hai? 🤔")
            await store_message(message) 
            return

        await message.reply_text(f"{messages_to_delete_count} sabse purane messages delete kiye ja rahe hain ({percentage}% of {total_messages}). Kripya intezaar karein, main saaf-safai kar rahi hoon! 🧹✨")

        oldest_message_ids = []
        for msg in messages_collection.find({}).sort("timestamp", 1).limit(messages_to_delete_count):
            oldest_message_ids.append(msg['_id'])

        if oldest_message_ids:
            delete_result = messages_collection.delete_many({"_id": {"$in": oldest_message_ids}})
            await message.reply_text(f"Successfully {delete_result.deleted_count} messages database se delete ho gaye, Malik! Ab main aur smart banungi!💖")
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
        await store_message(message) 
        return
    try:
        msg_id_to_delete = int(message.command[1])

        if messages_collection is None:
            await message.reply_text("Maaf karna, message delete nahi kar payi. Database (Main Learning DB) connect nahi ho paya hai. 🥺")
            await store_message(message) 
            return

        delete_result = messages_collection.delete_one({"message_id": msg_id_to_delete})

        if delete_result.deleted_count > 0:
            await message.reply_text(f"Message ID `{msg_id_to_delete}` database se successfully delete kar diya gaya, Malik! Poof! ✨")
            logger.info(f"Owner {message.from_user.id} deleted message ID {msg_id_to_delete}.") 
        else:
            await message.reply_text(f"Message ID `{msg_id_to_delete}` database mein nahi mila, Malik. Shayad main use janti hi nahi thi! 😅")
    except ValueError:
        await message.reply_text("Invalid message ID. Kripya ek number dein, Malik! 🔢")
    except Exception as e:
        await message.reply_text(f"Message delete karne mein error aaya, Malik: {e}. Kya hua? 🥺")
        logger.error(f"Error deleting message by owner {message.from_user.id}: {e}", exc_info=True)
    await store_message(message) 

# GROUP ADMIN COMMANDS (BAN, UNBAN, KICK, PIN, UNPIN)
async def perform_chat_action(client: Client, message: Message, action_type: str):
    if not message.reply_to_message and len(message.command) < 2:
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
        if not me_in_chat.privileges or (
            (not me_in_chat.privileges.can_restrict_members) and action_type in ["ban", "unban", "kick"]
        ) or (
            (not me_in_chat.privileges.can_pin_messages) and action_type in ["pin", "unpin"]
        ):
            await message.reply_text(f"Malik, mujhe {action_type} karne ke liye zaroori permissions ki zaroorat hai. Please de do na! 🙏")
            return
    except Exception as e:
        logger.error(f"Error checking bot permissions in chat {message.chat.id}: {e}", exc_info=True)
        await message.reply_text("Malik, permissions check karte samay error aaya. Kripya सुनिश्चित करें ki bot ko sahi permissions hain. 🥺")
        return

    try:
        if action_type == "ban":
            await client.ban_chat_member(message.chat.id, target_user_id)
            await message.reply_text(f"User {target_user_id} ko ban kar diya gaya, Malik! Ab koi shor nahi! 🤫")
        elif action_type == "unban":
            await client.unban_chat_member(message.chat.id, target_user_id)
            await message.reply_text(f"User {target_user_id} ko unban kar diya gaya, Malik! Shayad usne sabak seekh liya hoga! 😉")
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

# Changed filters for group admin commands to allow all group admins
@app.on_message(filters.command("ban") & filters.group & filters.create(group_admin_filter))
async def ban_command(client: Client, message: Message):
    await perform_chat_action(client, message, "ban")

@app.on_message(filters.command("unban") & filters.group & filters.create(group_admin_filter))
async def unban_command(client: Client, message: Message):
    await perform_chat_action(client, message, "unban")

@app.on_message(filters.command("kick") & filters.group & filters.create(group_admin_filter))
async def kick_command(client: Client, message: Message):
    await perform_chat_action(client, message, "kick")

@app.on_message(filters.command("pin") & filters.group & filters.create(group_admin_filter))
async def pin_command(client: Client, message: Message):
    await perform_chat_action(client, message, "pin")

@app.on_message(filters.command("unpin") & filters.group & filters.create(group_admin_filter))
async def unpin_command(client: Client, message: Message):
    await perform_chat_action(client, message, "unpin")

# --- CUSTOM WELCOME MESSAGE ---
@app.on_message(filters.command("setwelcome") & filters.group & filters.create(group_admin_filter)) # Changed filter
async def set_welcome_command(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("Malik, kripya welcome message dein.\nUpyog: `/setwelcome Aapka naya welcome message {user} {chat_title}`. Naye members ko surprise karte hain! 🥳")
        await store_message(message) 
        return
    welcome_msg_text = " ".join(message.command[1:])
    if group_configs_collection is None:
        await message.reply_text("Maaf karna, welcome message set nahi kar payi. Database (Commands/Settings DB) connect nahi ho paya hai. 🥺")
        await store_message(message) 
        return

    group_configs_collection.update_one(
        {"chat_id": message.chat.id},
        {"$set": {"welcome_message": welcome_msg_text}},
        upsert=True
    )
    await message.reply_text("Naya welcome message set kar diya gaya hai, Malik! Jab naya member aayega, toh main yahi pyaara message bhejoongi! 🥰")
    await store_message(message) 

@app.on_message(filters.command("getwelcome") & filters.group & filters.create(group_admin_filter)) # Changed filter
async def get_welcome_command(client: Client, message: Message):
    config = None
    if group_configs_collection is not None:
        config = group_configs_collection.find_one({"chat_id": message.chat.id})
    
    if config and "welcome_message" in config:
        await message.reply_text(f"Malik, current welcome message:\n`{config['welcome_message']}`. Pasand aaya? 😉")
    else:
        await message.reply_text("Malik, is group ke liye koi custom welcome message set nahi hai. Kya set karna chahte ho? 🥺")
    await store_message(message) 

@app.on_message(filters.command("clearwelcome") & filters.group & filters.create(group_admin_filter)) # Changed filter
async def clear_welcome_command(client: Client, message: Message):
    if group_configs_collection is None:
        await message.reply_text("Maaf karna, welcome message clear nahi kar payi. Database (Commands/Settings DB) connect nahi ho paya hai. 🥺")
        await store_message(message) 
        return

    group_configs_collection.update_one(
        {"chat_id": message.chat.id},
        {"$unset": {"welcome_message": ""}}
    )
    await message.reply_text("Malik, custom welcome message hata diya gaya hai. Ab main default welcome message bhejoongi. Kya main bori...ng ho gayi? 😔")
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
        await store_message(message) 
        return

    # Check if user is already approved for clone
    user_state = user_states_collection.find_one({"user_id": user_id, "status": "approved_for_clone"})
    if user_state:
        await message.reply_text(
            "Tum toh pehle se hi meri permission le chuke ho, mere dost! ✅\n"
            "Ab bas apna bot token bhejo, main tumhare liye ek naya bot bana dungi:\n"
            "**Kaise?** `/clonebot YOUR_BOT_TOKEN_HERE`\n"
            "(Pura token ek hi line mein hona chahiye, theek hai? 😉)"
        )
        await store_message(message) 
        return

    # Check if there's a pending request
    pending_request = user_states_collection.find_one({"user_id": user_id, "status": "pending_approval"})
    if pending_request:
        await message.reply_text(
            "Meri cute si request pehle se hi pending hai, darling! ⏳\n"
            "Kripya admin ke approval ka intezaar karo. Agar payment aur screenshot bhej diya hai, toh thoda sabar karo na! 😊"
        )
        await store_message(message) 
        return

    # User needs to pay
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
        # If user_states_collection is None, we can't check cloning state,
        # so pass to general message handler.
        await handle_private_general_messages(client, message) # Changed to handle_private_general_messages
        return 

    user_state = user_states_collection.find_one({"user_id": user_id})
    logger.info(f"Received photo from user {user_id}. User state: {user_state.get('status') if user_state else 'None'}")

    # Check if the message is a reply to the ForceReply from prompt_for_screenshot
    is_reply_to_force_reply = False
    if message.reply_to_message and \
       message.reply_to_message.from_user and message.reply_to_message.from_user.is_self and \
       message.reply_to_message.reply_markup and \
       isinstance(message.reply_to_message.reply_markup, ForceReply): 
        is_reply_to_force_reply = True

    if is_reply_to_force_reply:
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
                chat_id=int(OWNER_ID), # Ensure OWNER_ID is int
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
        # Pass to general message handler if not part of clone flow
        await handle_private_general_messages(client, message) # Changed to handle_private_general_messages
        
    await store_message(message)


# Step 4: Owner approves/rejects clone request
@app.on_callback_query(filters.regex(r"^(approve_clone|reject_clone)_(\d+)$") & filters.create(owner_only_filter))
async def handle_clone_approval(client: Client, callback_query: CallbackQuery):
    action, _, target_user_id_str = callback_query.data.split('_', 2)
    target_user_id = str(target_user_id_str) # Keep as string for MongoDB
    
    if user_states_collection is None:
        await callback_query.answer("Maaf karna, service abhi available nahi hai. Database (Clone/State DB) connect nahi ho paya hai. 🥺", show_alert=True)
        return

    user_state = user_states_collection.find_one({"user_id": target_user_id})

    if not user_state or user_state.get("status") != "pending_approval":
        await callback_query.answer("Arre! Yeh request ab valid nahi hai ya pehle hi process ho chuki hai, Malik! 🙄", show_alert=True)
        return

    new_caption = callback_query.message.caption + (f"\n\n**Admin ne Approve Kar Diya! ✅**" if action == "approve_clone" else "\n\n**Admin ne Reject Kar Diya! ❌**")
    try:
        await callback_query.message.edit_caption(
            caption=new_caption,
            reply_markup=None
        )
    except Exception as e:
        logger.error(f"Error editing owner's message for approval: {e}", exc_info=True)
        await client.send_message(int(OWNER_ID), f"Maaf karna Malik, user {target_user_id} ke message ko edit nahi kar payi. {action} status: {new_caption}")

    if action == "approve_clone":
        if user_states_collection is not None: 
            user_states_collection.update_one(
                {"user_id": target_user_id},
                {"$set": {"status": "approved_for_clone", "approved_on": datetime.now()}}
            )
        try:
            await client.send_message(
                int(target_user_id),
                "Badhai ho, mere dost! 🎉 Tumhari Bot Cloning request approve ho gayi hai! ✅\n"
                "Ab tum apni pyaari si bot banane ke liye token bhej sakte ho:\n"
                "**Kaise?** `/clonebot YOUR_BOT_TOKEN_HERE`\n"
                "(Pura token ek hi line mein hona chahiye, jaldi karo na! 😉)"
            )
            logger.info(f"User {target_user_id} approved for cloning.")
        except Exception as e:
            logger.error(f"Error notifying user {target_user_id} about approval: {e}")
            await client.send_message(int(OWNER_ID), f"User {target_user_id} ko approval notification bhejne mein error aaya. {e}")

    elif action == "reject_clone":
        if user_states_collection is not None: 
            user_states_collection.delete_one({"user_id": target_user_id}) 
        try:
            await client.send_message(
                int(target_user_id),
                "Maaf karna, darling! 😔 Tumhari Bot Cloning request reject ho gayi hai.\n"
                "Kisi bhi sawal ke liye mere Malik se contact karo na! 🥺"
            )
            logger.info(f"User {target_user_id} rejected for cloning.")
        except Exception as e:
            logger.error(f"Error notifying user {target_user_id} about rejection: {e}")
            await client.send_message(int(OWNER_ID), f"User {target_user_id} ko rejection notification bhejne mein error aaya. {e}")
    
    await callback_query.answer(f"Request {action.split('_')[0]}d for user {target_user_id}.", show_alert=True)


# Step 5: Process actual clonebot command after approval
@app.on_message(filters.command("clonebot") & filters.private & filters.regex(r'/clonebot\s+([A-Za-z0-9:_-]+)'))
async def process_clone_bot_after_approval(client: Client, message: Message):
    user_id = str(message.from_user.id)
    
    if user_states_collection is None:
        await handle_private_general_messages(client, message) # Changed to handle_private_general_messages
        return

    user_state = user_states_collection.find_one({"user_id": user_id, "status": "approved_for_clone"})

    if not user_state:
        await message.reply_text("Arre, tum bot clone karne ke liye approved nahi ho! 🥺 Kripya pehle payment process poora karo na! 😉")
        await store_message(message)
        return

    bot_token = message.command[1].strip()
    if not re.match(r'^\d+:[A-Za-z0-9_-]+$', bot_token):
        await message.reply_text("Yeh bot token sahi nahi lag raha. Kripya ek valid token dein. Main confuse ho gayi! 😵‍💫")
        await store_message(message)
        return

    await message.reply_text("Tumhare bot token ki jaanch kar rahi hoon, darling! Thoda wait karo... 💖")
    
    try:
        test_client = Client(
            f"cloned_bot_session_{user_id}",
            api_id=int(API_ID),
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
# Modified filter to be more specific for replies to ForceReply
@app.on_message(
    filters.text & filters.private &
    filters.reply # Ensure it's a reply
    & (lambda _, __, msg: msg.reply_to_message and msg.reply_to_message.from_user and msg.reply_to_message.from_user.is_self and
                         msg.reply_to_message.reply_markup and isinstance(msg.reply_to_message.reply_markup, ForceReply))
)
async def finalize_clone_process(client: Client, message: Message):
    user_id = str(message.from_user.id)
    
    if user_states_collection is None:
        await handle_private_general_messages(client, message) # Changed to handle_private_general_messages
        return 

    user_state = user_states_collection.find_one({"user_id": user_id, "status": "awaiting_channel"})

    if not user_state:
        # If not in this state, let general private handler take over
        await handle_private_general_messages(client, message) # Changed to handle_private_general_messages
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
                # Verify if it's a valid channel and bot can access it (optional, but good practice)
                chat = await client.get_chat(f"@{final_update_channel}")
                if not chat.type == ChatType.CHANNEL:
                    await message.reply_text("Yeh ek valid channel username/link nahi lag raha, darling! Kripya sahi channel ka username (@channelname) ya link (t.me/channelname) dein, ya 'no' type karo. Mujhko samjho na! 🥺")
                    await store_message(message)
                    return
            except Exception as e:
                logger.warning(f"Could not verify channel {final_update_channel}: {e}")
                await message.reply_text("Channel ko verify nahi kar payi, darling! Kripya sahi channel ka username (@channelname) ya link (t.me/channelname) dein, ya 'no' type karo. Kya main galti kar rahi hoon? 😔")
                await store_message(message)
                return
            
            logger.info(f"User {user_id} set update channel to @{final_update_channel}")
        else:
            await message.reply_text("Invalid channel username/link, darling! Kripya sahi channel ka username (@channelname) ya link (t.me/channelname) dein, ya 'no' type karo. Main confusion mein hoon! 😵‍💫")
            await store_message(message)
            return

    else:
        logger.info(f"User {user_id} chose default update channel: @{DEFAULT_UPDATE_CHANNEL_USERNAME}")
    
    await message.reply_text(
        "Badhai ho, mere cute dost! 🎉 Tumhare bot ke liye saari settings complete ho gayi hain.\n\n"
        "Ab tum is pyaare bot ko deploy kar sakte ho! Tumhara bot token aur update channel niche diye gaye hain:\n"
        f"**Bot Token:** `{user_state['bot_token']}`\n"
        f"**Bot Username:** `@{user_state['bot_username']}`\n"
        f"**Meri Updates:** `https://t.me/{final_update_channel}`\n\n" # Use link for clarity
        "**Deployment ke liye easy steps:**\n"
        "1. Meri GitHub repository ko fork karo (agar nahi kiya hai toh).\n"
        "2. Apni `main.py` file mein `BOT_TOKEN`, `API_ID`, `API_HASH` aur `OWNER_ID` ko apne hisaab se Environment Variables mein set karo.\n"
        f"3. Aur haan, `main.py` mein `DEFAULT_UPDATE_CHANNEL_USERNAME` ko `'{final_update_channel}'` par set karna mat bhoolna! (Ya phir apne forked repo mein yeh value directly daal do)\n"
        "4. Koyeb (ya kisi bhi hosting) par deploy karo, Environment Variables mein saari details dena. Fir dekho mera jaisa pyaara bot kaise kaam karta hai! 💖\n\n"
        "Kisi bhi sawal ke liye @aschat_group channel par aana na bhoolna! Main wahin milungi! 😉" 
    )
    
    # Clear the user state after successful clone finalization
    if user_states_collection is not None: 
        user_states_collection.delete_one({"user_id": user_id})
    logger.info(f"User {user_id} clone process finalized and state cleared.")
    await store_message(message) 


# --- Private Chat General Message Handler (Fallback for non-commands/non-cloning) ---
# Removed the old handle_private_non_command_messages and integrated its checks here.
# This handler will act as the final fallback for private text messages.
@app.on_message(filters.private & (filters.text | filters.sticker | filters.photo | filters.video | filters.document | filters.audio | filters.voice | filters.animation) & ~filters.via_bot & (lambda _, __, msg: not msg.text.startswith('/')))
async def handle_private_general_messages(client: Client, message: Message):
    user_id = str(message.from_user.id)
    
    # Store message ONLY IF it's not a bot's message
    if not message.from_user.is_self: # Make sure this is a user's message
        await store_message(message, is_bot_sent=False)
    
    if user_states_collection is None:
        await message.reply_text("Maaf karna, bot abhi poori tarah se ready nahi hai. Kuch database issues hain (Clone/State DB connect nahi ho paya). 🥺")
        return # Do not store bot's own error messages as user input

    user_state = user_states_collection.find_one({"user_id": user_id})

    # If user is in any cloning state, don't interfere, give specific prompt
    # The `finalize_clone_process` and `receive_screenshot` filters are more specific and will run first.
    # This block catches remaining text messages in cloning states that weren't specific replies.
    if user_state is not None:
        status = user_state.get("status")
        if status == "awaiting_screenshot" or status == "expecting_screenshot":
            await message.reply_text("Kripya apna payment screenshot bhej do, darling! Main uska intezaar kar rahi hoon. 👇")
            return
        elif status == "awaiting_channel":
            await message.reply_text("Hehe, darling! Main abhi bas channel link ka intezaar kar rahi hoon. Ya toh apna channel link bhej do, ya 'no' type kar do. 😉")
            return
        elif status == "pending_approval":
            await message.reply_text("Meri cute si request pehle se hi pending hai, darling! ⏳ Admin ke approval ka intezaar karo. 😊")
            return
        elif status == "approved_for_clone":
            await message.reply_text("Tum toh pehle se hi meri permission le chuke ho, mere dost! ✅ Ab bas apna bot token bhejo: `/clonebot YOUR_BOT_TOKEN_HERE`")
            return

    # If not in any cloning state, not a command, then process as general self-learning reply
    chat_id = message.chat.id
    current_time = time.time()

    # Check cooldown *before* generating reply
    if chat_id in last_bot_reply_time:
        time_since_last_reply = current_time - last_bot_reply_time[chat_id]
        if time_since_last_reply < REPLY_COOLDOWN_SECONDS:
            logger.info(f"Cooldown active for private chat {chat_id}. Not generating reply for message {message.id}.")
            return 

    logger.info(f"Attempting to generate reply for private chat {message.chat.id}")
    reply_doc = await generate_reply(message) 

    if reply_doc: 
        try:
            sent_msg = None
            content_type = reply_doc.get("content_type")
            content_to_send = reply_doc.get("content")
            file_to_send = reply_doc.get("file_id") # Get file_id if available
            
            if content_type == "text":
                sent_msg = await message.reply_text(content_to_send)
                logger.info(f"Replied with text: {content_to_send}")
            elif content_type == "sticker" and file_to_send:
                sent_msg = await message.reply_sticker(file_to_send)
                logger.info(f"Replied with sticker: {file_to_send}")
            elif content_type == "photo" and file_to_send:
                sent_msg = await message.reply_photo(file_to_send, caption=content_to_send)
                logger.info(f"Replied with photo: {file_to_send}")
            elif content_type == "video" and file_to_send:
                sent_msg = await message.reply_video(file_to_send, caption=content_to_send)
                logger.info(f"Replied with video: {file_to_send}")
            elif content_type == "document" and file_to_send:
                sent_msg = await message.reply_document(file_to_send, caption=content_to_send)
                logger.info(f"Replied with document: {file_to_send}")
            elif content_type == "audio" and file_to_send:
                sent_msg = await message.reply_audio(file_to_send, caption=content_to_send)
                logger.info(f"Replied with audio: {file_to_send}")
            elif content_type == "voice" and file_to_send:
                sent_msg = await message.reply_voice(file_to_send, caption=content_to_send)
                logger.info(f"Replied with voice: {file_to_send}")
            elif content_type == "animation" and file_to_send:
                sent_msg = await message.reply_animation(file_to_send, caption=content_to_send)
                logger.info(f"Replied with animation: {file_to_send}")
            else:
                logger.warning(f"Reply document found but no recognized content type or file_id for private chat: {reply_doc}")

            if sent_msg:
                last_bot_reply_time[chat_id] = time.time()
                await store_message(sent_msg, is_bot_sent=True, sent_message_id=sent_msg.id)
        except Exception as e:
            logger.error(f"Error sending reply for private message {message.id}: {e}", exc_info=True)
    else:
        logger.info(f"No suitable reply generated for private message {message.id}.")


# --- Standard message handler (general text/sticker messages in groups, or bot replies in private) ---
# This handler will now primarily focus on group chats.
@app.on_message(filters.group & (filters.text | filters.sticker | filters.photo | filters.video | filters.document | filters.audio | filters.voice | filters.animation))
async def handle_general_messages(client: Client, message: Message):
    global last_bot_reply_time

    if message.from_user and message.from_user.is_bot:
        return 
    
    # Ignore commands in groups here, they are handled by specific command handlers
    if message.text and message.text.startswith('/'):
        return

    # Store all incoming messages (except those from bot itself or commands)
    await store_message(message, is_bot_sent=False)
    
    chat_id = message.chat.id
    current_time = time.time()

    # Check cooldown *before* generating reply
    if chat_id in last_bot_reply_time:
        time_since_last_reply = current_time - last_bot_reply_time[chat_id]
        if time_since_last_reply < REPLY_COOLDOWN_SECONDS:
            logger.info(f"Cooldown active for group chat {chat_id}. Not generating reply for message {message.id}.")
            return 

    logger.info(f"Attempting to generate reply for group chat {message.chat.id}")
    reply_doc = await generate_reply(message) 

    if reply_doc: 
        try:
            sent_msg = None
            content_type = reply_doc.get("content_type")
            content_to_send = reply_doc.get("content")
            file_to_send = reply_doc.get("file_id") # Get file_id if available
            
            if content_type == "text":
                sent_msg = await message.reply_text(content_to_send)
                logger.info(f"Replied with text: {content_to_send}")
            elif content_type == "sticker" and file_to_send:
                sent_msg = await message.reply_sticker(file_to_send)
                logger.info(f"Replied with sticker: {file_to_send}")
            # Add handling for other media types if you plan to store and reply with them
            elif content_type == "photo" and file_to_send:
                sent_msg = await message.reply_photo(file_to_send, caption=content_to_send)
                logger.info(f"Replied with photo: {file_to_send}")
            elif content_type == "video" and file_to_send:
                sent_msg = await message.reply_video(file_to_send, caption=content_to_send)
                logger.info(f"Replied with video: {file_to_send}")
            elif content_type == "document" and file_to_send:
                sent_msg = await message.reply_document(file_to_send, caption=content_to_send)
                logger.info(f"Replied with document: {file_to_send}")
            elif content_type == "audio" and file_to_send:
                sent_msg = await message.reply_audio(file_to_send, caption=content_to_send)
                logger.info(f"Replied with audio: {file_to_send}")
            elif content_type == "voice" and file_to_send:
                sent_msg = await message.reply_voice(file_to_send, caption=content_to_send)
                logger.info(f"Replied with voice: {file_to_send}")
            elif content_type == "animation" and file_to_send:
                sent_msg = await message.reply_animation(file_to_send, caption=content_to_send)
                logger.info(f"Replied with animation: {file_to_send}")
            else:
                logger.warning(f"Reply document found but no recognized content type or file_id: {reply_doc}")

            if sent_msg:
                last_bot_reply_time[chat_id] = time.time()
                # Store bot's own reply
                await store_message(sent_msg, is_bot_sent=True, sent_message_id=sent_msg.id)
        except Exception as e:
            logger.error(f"Error sending reply for message {message.id}: {e}", exc_info=True)
    else:
        logger.info(f"No suitable reply generated for message {message.id}.")


# --- New Admin Commands ---

@app.on_message(filters.command("restart") & filters.private & filters.create(owner_only_filter))
async def restart_bot_command(client: Client, message: Message):
    if len(message.command) < 2 or message.command[1].lower() != "bot":
        await message.reply_text("Malik, agar mujhe restart karna hai toh aise bolo: `/restart bot`. Main sab samajh jaungi! 😉")
        return

    await message.reply_text("Malik, main ab khud ko restart kar rahi hoon. Thoda intezaar karo, main jaldi wapas aungi! 💖")
    logger.info(f"Owner {message.from_user.id} initiated bot restart.")
    
    # Close Pyrogram client gracefully
    await app.stop()
    logger.info("Pyrogram client stopped. Restarting process...")
    
    # Restart the script (this will work differently based on deployment environment)
    # For a simple Python script, os.execv will replace the current process.
    # In a Docker container, it will cause the container to exit, and the orchestrator will restart it.
    python = sys.executable
    os.execv(python, [python] + sys.argv)


@app.on_message(filters.command("resetall") & filters.private & filters.create(owner_only_filter))
async def reset_all_data_command(client: Client, message: Message):
    confirm_text = "YES_DELETE_ALL_DATA"
    if len(message.command) < 2 or message.command[1] != confirm_text:
        await message.reply_text(
            f"**🚨 WARNING, MALIK! Yeh command saara database data delete kar dega!** 🚨\n"
            "Kya aap pakka sure hain? Agar haan, toh kripya yeh type karein:\n"
            f"`/resetall {confirm_text}`\n"
            "Main galti nahi karna chahti, Malik! 😥"
        )
        return

    await message.reply_text("Malik, aapne mujhe saara data delete karne ka bol diya! Main ab sab kuch mita rahi hoon. 🗑️✨\n"
                             "Kripya intezaar karein, yeh thoda samay le sakta hai...")
    
    try:
        deleted_count = 0
        
        # Main Learning DB
        if main_db:
            for collection_name in await main_db.list_collection_names():
                await main_db[collection_name].drop()
                logger.info(f"Collection '{collection_name}' dropped from Main Learning DB.")
                deleted_count += 1
        else:
            logger.warning("Main Learning DB not connected, skipping data deletion.")
        
        # Clone/State DB
        if clone_state_db:
            for collection_name in await clone_state_db.list_collection_names():
                await clone_state_db[collection_name].drop()
                logger.info(f"Collection '{collection_name}' dropped from Clone/State DB.")
                deleted_count += 1
        else:
            logger.warning("Clone/State DB not connected, skipping data deletion.")

        # Commands/Settings DB
        if commands_settings_db:
            for collection_name in await commands_settings_db.list_collection_names():
                await commands_settings_db[collection_name].drop()
                logger.info(f"Collection '{collection_name}' dropped from Commands/Settings DB.")
                deleted_count += 1
        else:
            logger.warning("Commands/Settings DB not connected, skipping data deletion.")

        await message.reply_text(
            f"Malik, saara data delete ho gaya! Total **{deleted_count}** collections saaf kar diye. "
            "Ab main bilkul nayi ho gayi hoon! 🥰\n"
            "Mujhe dobara train karna padega! "
            "Agar aap chahen toh ab bot ko restart kar sakte hain: `/restart bot`"
        )
        logger.info(f"Owner {message.from_user.id} successfully reset all MongoDB data.")

    except Exception as e:
        await message.reply_text(f"Malik, data delete karte samay error aaya: {e}. Mujhse ho nahi pa raha! 😭")
        logger.error(f"Error resetting all data by owner {message.from_user.id}: {e}", exc_info=True)
    await store_message(message) 

# --- Flask Web Server for Health Check ---
flask_app = Flask(__name__)

@flask_app.route('/')
def health_check():
    mongo_status_main = "Disconnected"
    mongo_status_clone_state = "Disconnected"
    mongo_status_commands_settings = "Disconnected"
    
    # Pyrogram connection status
    pyrogram_connected = app.is_connected
    
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
        pyrogram_connected=pyrogram_connected,
        mongo_db_main_status=mongo_status_main,
        mongo_db_clone_state_status=mongo_status_clone_state,
        mongo_db_commands_settings_status=mongo_status_commands_settings,
        timestamp=datetime.now().isoformat()
    )

def run_flask_app():
    port = int(os.getenv('PORT', 8000))
    logger.info(f"Flask health check server starting on 0.0.0.0:{port}")
    # Setting threaded=True is important for Flask to not block Pyrogram
    flask_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False, threaded=True)

# --- Main entry point ---
if __name__ == "__main__":
    logger.info("Cutie Pie bot running. ✨") 
    
    # Start Flask app in a separate thread
    flask_thread = Thread(target=run_flask_app)
    flask_thread.daemon = True # Allows the main program to exit even if thread is running
    flask_thread.start()

    # Start Pyrogram bot (blocking call)
    app.run()

