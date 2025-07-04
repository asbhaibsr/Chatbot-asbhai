# Credit by @asbhaibsr and Telegram Channel @asbhai_bsr

import os
import asyncio
import re
import random
import logging
from datetime import datetime, timedelta
from threading import Thread
import time
import sys

# Pyrogram imports
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ForceReply
from pyrogram.enums import ChatType, ChatMemberStatus
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
DEFAULT_UPDATE_CHANNEL_USERNAME = "asbhai_bsr"
REPLY_COOLDOWN_SECONDS = 3

# --- Payment Details ---
PAYMENT_INFO = {
    "amount": "200",
    "upi_id": "arsadsaifi8272@ibl",
    "qr_code_url": "", # Keep this empty if no QR code image URL is provided
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
        main_db = main_mongo_client.bot_learning_database
        messages_collection = main_db.messages
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
        clone_state_db = clone_state_mongo_client.bot_clone_states_db
        user_states_collection = clone_state_db.user_states
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
        commands_settings_db = commands_settings_mongo_client.bot_settings_db
        group_configs_collection = commands_settings_db.group_configs
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
    api_id=int(API_ID) if API_ID else None,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# --- Global variable to track last reply time per chat ---
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


async def store_message(message: Message, is_bot_sent: bool = False):
    # Only store messages in groups for learning, or bot-sent messages
    # Commands and their immediate replies might be stored regardless of chat type if needed for logging
    if message.chat.type == ChatType.PRIVATE and not is_bot_sent and not message.text.startswith('/'):
        logger.debug(f"Ignoring message for learning in private chat from user {message.from_user.id if message.from_user else 'None'}. Message ID: {message.id}")
        return # Do not store general private messages for learning

    if messages_collection is None:
        logger.error("messages_collection is NOT initialized. Cannot store message. Please check MongoDB connection for MAIN_MONGO_DB_URI.")
        return

    try:
        # Ignore messages sent by other bots (unless it's our own bot's sent message)
        if message.from_user and message.from_user.is_bot and not is_bot_sent:
            logger.debug(f"Ignoring message from another bot: {message.from_user.id}")
            return

        content_type = "text"
        file_id = None
        # Prioritize sticker/photo content over caption if both exist
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

        # Use text if available, otherwise emoji for sticker, otherwise caption
        message_content = message.text if message.text else \
                          (message.sticker.emoji if message.sticker else \
                           (message.caption if message.caption else ""))


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
            "content": message_content, # Storing the actual content for search
            "file_id": file_id,
            "keywords": extract_keywords(message_content), # Extract keywords from message_content
            "replied_to_message_id": None,
            "replied_to_user_id": None,
            "replied_to_content": None,
            "replied_to_content_type": None,
            "is_bot_observed_pair": False, # Renamed to better reflect its purpose
        }

        # Store reply-to information
        if message.reply_to_message:
            message_data["replied_to_message_id"] = message.reply_to_message.id
            if message.reply_to_message.from_user:
                message_data["replied_to_user_id"] = message.reply_to_message.from_user.id

            replied_to_content = message.reply_to_message.text if message.reply_to_message.text else \
                                 (message.reply_to_message.sticker.emoji if message.reply_to_message.sticker else \
                                  (message.reply_to_message.caption if message.reply_to_message.caption else ""))

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

            message_data["replied_to_content"] = replied_to_content
            message_data["replied_to_content_type"] = replied_to_content_type

            # Check if this message is a user's reply to the bot's own message
            if message.reply_to_message.from_user and message.reply_to_message.from_user.is_self:
                message_data["is_bot_observed_pair"] = True
                logger.debug(f"Observed user reply to bot's message ({message.reply_to_message.id}). Marking this as observed pair.")
                # Also, update the original bot message to show it received a reply
                if messages_collection is not None:
                    messages_collection.update_one(
                        {"chat_id": message.chat.id, "message_id": message.reply_to_message.id, "is_bot_sent": True},
                        {"$set": {"has_received_reply": True, "replied_by_user_id": message.from_user.id, "replied_message_content": message_content}}
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


async def generate_reply(client: Client, message: Message): # Added client parameter
    # Only generate replies in groups where learning is active
    if message.chat.type == ChatType.PRIVATE:
        # Private chat replies are handled by specific handlers (commands, cloning flow)
        # General replies are NOT generated in private chat based on learning DB
        logger.debug(f"Skipping general reply generation for private chat {message.chat.id}")
        return None

    await app.invoke(SetTyping(peer=await app.resolve_peer(message.chat.id), action=SendMessageTypingAction()))
    await asyncio.sleep(0.5)

    query_content = message.text if message.text else (message.sticker.emoji if message.sticker else (message.caption if message.caption else ""))
    query_keywords = extract_keywords(query_content)

    if not query_keywords and not query_content and not message.sticker and not message.photo and not message.video and not message.document and not message.audio and not message.voice and not message.animation:
        logger.debug("No meaningful content extracted for reply generation.")
        return None

    if messages_collection is None:
        logger.warning("messages_collection is None. Cannot generate reply.")
        return None

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
    # This strategy now looks for user replies to *any* message,
    # and also for user replies to BOT's *own* messages
    if message.reply_to_message:
        replied_to_content = message.reply_to_message.text if message.reply_to_message.text else \
                             (message.reply_to_message.sticker.emoji if message.reply_to_message.sticker else \
                              (message.reply_to_message.caption if message.reply_to_message.caption else ""))
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

            potential_contextual_replies = []

            # 1. Look for user's replies to *other users'* messages (general human conversation flow)
            # Find messages that are replies to the *same content* as what the user replied to
            # And where the original message was *not* sent by the bot itself
            user_reply_to_user_query = {
                "replied_to_content": {"$regex": f"^{re.escape(replied_to_content)}$", "$options": "i"},
                "replied_to_content_type": replied_to_content_type,
                "is_bot_sent": False, # Looking for user responses to a given query
                "replied_to_user_id": {"$ne": client.me.id if client.me else None}, # Make sure the original message wasn't from bot
                "content": {"$ne": query_content}, # Don't reply with what the user just said
            }
            if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
                potential_contextual_replies.extend(list(messages_collection.find({"chat_id": message.chat.id, **user_reply_to_user_query})))
                potential_contextual_replies.extend(list(messages_collection.find(user_reply_to_user_query))) # Global

            # 2. Look for patterns where a user replied to the *bot's own message*
            # Here, the original message was sent by the bot (is_bot_sent: True),
            # and we are looking for a follow-up message by a user (is_bot_sent: False)
            # that was a reply to such a bot message.
            bot_reply_observed_query = {
                "replied_to_content": {"$regex": f"^{re.escape(replied_to_content)}$", "$options": "i"},
                "replied_to_content_type": replied_to_content_type,
                "is_bot_sent": False, # The message we want to use as a reply must be a user's message
                "replied_to_user_id": client.me.id if client.me else None, # The message being replied to was from the bot
                "content": {"$ne": query_content},
            }
            if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
                potential_contextual_replies.extend(list(messages_collection.find({"chat_id": message.chat.id, **bot_reply_observed_query})))
                potential_contextual_replies.extend(list(messages_collection.find(bot_reply_observed_query))) # Global

            if potential_contextual_replies:
                unique_contextual_replies = {}
                for doc in potential_contextual_replies:
                    key = (doc.get("content", ""), doc.get("content_type", ""), doc.get("file_id"))
                    if key not in unique_contextual_replies:
                        unique_contextual_replies[key] = doc

                # Filter out replies that are too similar to the original user query or bot's own messages
                filtered_contextual_replies = []
                for doc in unique_contextual_replies.values():
                    # Don't reply with the exact same thing the user just said
                    if doc.get("content", "").lower() == query_content.lower() and doc.get("content_type") == message_actual_content_type:
                        continue
                    # Don't pick bot's own replies for "training" unless it's an explicit response to a user's reply to the bot
                    # The `is_bot_sent: False` in queries above should mostly handle this
                    filtered_contextual_replies.append(doc)

                if filtered_contextual_replies:
                    logger.info(f"Returning random contextual reply from {len(filtered_contextual_replies)} candidates.")
                    return random.choice(filtered_contextual_replies)

        logger.info(f"No direct contextual reply found for replied_to_content: '{replied_to_content}'.")

    # --- Strategy 2: Keyword-based General Reply (including partial match and content type) ---
    logger.info(f"Strategy 2: Falling back to keyword/content search for: '{query_content}' (Type: {message_actual_content_type}) with keywords {query_keywords}")

    content_match_conditions = []

    if query_content:
        # Exact content match first
        content_match_conditions.append({"content": {"$regex": f"^{re.escape(query_content)}$", "$options": "i"}})
        # Partial keyword match
        for kw in query_keywords:
            content_match_conditions.append({"content": {"$regex": f".*{re.escape(kw)}.*", "$options": "i"}})

    if message.sticker and message.sticker.file_id:
        content_match_conditions.append({"file_id": message.sticker.file_id, "content_type": "sticker"})
    elif message.photo and message.photo.file_id:
        content_match_conditions.append({"file_id": message.photo.file_id, "content_type": "photo"})
    elif message.video and message.video.file_id:
        content_match_conditions.append({"file_id": message.video.file_id, "content_type": "video"})
    # Add other media types if you want to search by their file_id/content

    final_query_conditions = {
        "is_bot_sent": False, # Looking for user-sent messages as potential replies
    }

    if content_match_conditions:
        final_query_conditions["$or"] = content_match_conditions

    # Target reply can be text or sticker, or the same media type as the query
    target_reply_content_types = ["text", "sticker"]
    if message_actual_content_type in ["photo", "video", "document", "audio", "voice", "animation"]:
        target_reply_content_types.append(message_actual_content_type)

    final_query_conditions["content_type"] = {"$in": target_reply_content_types}

    potential_replies = []
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        group_specific_query = {"chat_id": message.chat.id, **final_query_conditions}
        potential_replies.extend(list(messages_collection.find(group_specific_query)))
        logger.info(f"Found {len(potential_replies)} group-specific keyword/content matches.")

    global_query = {**final_query_conditions}
    global_matches_count = messages_collection.count_documents(global_query)
    potential_replies.extend(list(messages_collection.find(global_query)))
    logger.info(f"Found {global_matches_count} global keyword/content matches.")


    if potential_replies:
        # Use a set to store unique documents to avoid sending duplicate replies
        unique_replies_set = {}
        for doc in potential_replies:
            # Create a unique key for each document (e.g., based on _id or content+type)
            # Using _id is safer if content/type can be same but documents are distinct
            unique_replies_set[str(doc['_id'])] = doc

        filtered_replies = []
        for doc in unique_replies_set.values():
            # Filter out replies that are too similar to the original user query
            if doc.get("content", "").lower() == query_content.lower() and doc.get("content_type") == message_actual_content_type:
                continue

            # Filter out replies that are the exact same file (e.g., user sends a sticker, bot finds same sticker)
            if doc.get("file_id") and doc.get("file_id") == (message.sticker.file_id if message.sticker else (message.photo.file_id if message.photo else (message.video.file_id if message.video else None))):
                continue

            # Ensure we are not replying with something the bot itself sent previously in a general context
            # (Contextual replies are different, they are direct responses to bot's messages)
            if doc.get("is_bot_sent", False):
                continue

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

    # Only send fallback replies in groups if no other strategy works
    # Private chat fallback logic is handled within handle_private_general_messages
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        return {"content_type": "text", "content": random.choice(fallback_messages)}
    
    return None # No fallback reply for private chat from here


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
        [InlineKeyboardButton("📣 Meri Updates Yahan Milengi! 😉", url=f"https://t.me/{DEFAULT_UPDATE_CHANNEL_USERNAME}")],
        [InlineKeyboardButton("🤖 Apna Khud Ka Bot Banayein! (Premium)", callback_data="clone_bot_start")]
    ])
    await message.reply_text(welcome_message, reply_markup=keyboard)
    # Commands in private chat are still "stored" for tracking, not for learning general replies
    if message.from_user:
        await store_message(message, is_bot_sent=False)

# Handle callback from "Apna Khud Ka Bot Banayein!" button
@app.on_callback_query(filters.regex("clone_bot_start"))
async def handle_clone_bot_start_callback(client: Client, callback_query: CallbackQuery):
    await callback_query.answer("Bot cloning process shuru ho raha hai! 😉", show_alert=True)
    # Simulate /clonebot command for the user
    # Use the actual client to send a message that the /clonebot handler will pick up
    await client.send_message(
        chat_id=callback_query.message.chat.id,
        text="/clonebot"
    )

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
    if message.from_user: # Store user's command
        await store_message(message, is_bot_sent=False)

# GENERAL STATS COMMAND
@app.on_message(filters.command("stats") & (filters.private | filters.group))
async def stats_command(client: Client, message: Message):
    if len(message.command) < 2 or message.command[1].lower() != "check":
        await message.reply_text("Hehe, agar mere stats dekhne hain toh aise bolo: `/stats check`. Main koi simple bot thodi na hoon! 😉")
        if message.from_user:
            await store_message(message, is_bot_sent=False)
        return

    if messages_collection is None:
        await message.reply_text("Maaf karna, statistics abhi available nahi hain. Database mein kuch gadbad hai.🥺 (Main Learning DB connect nahi ho paya)")
        if message.from_user:
            await store_message(message, is_bot_sent=False)
        return

    total_messages = messages_collection.count_documents({})
    unique_group_ids = messages_collection.distinct("chat_id", {"chat_type": {"$in": ["group", "supergroup"]}})
    num_groups = len(unique_group_ids)

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
    if message.from_user:
        await store_message(message, is_bot_sent=False)

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
        "\n\n**Admin Commands (Sirf mere Malik aur Group Admins ke liye, shhh!):**"
        "\n• `/broadcast <message>` - Sabko mera pyaara message bhejo! (Owner Only)"
        "\n• `/resetdata <percentage>` - Kuch purani yaadein mita do! (Agar data bahot ho jaye) (Owner Only)"
        "\n• `/deletemessage <message_id>` - Ek khaas message delete karo! (Owner Only)"
        "\n• `/clearpending` - Saari pending approvals hata do! (Owner Only)"
        "\n• `/readyclone <user_id>` - User ko bot clone karne ke liye approve karein! (Owner Only) "
        "\n• `/ban <user_id_or_username>` - Gande logon ko group se bhagao! 😤 (Admins & Owner)"
        "\n• `/unban <user_id_or_username>` - Acha, maaf kar do unhe! 😊 (Admins & Owner)"
        "\n• `/kick <user_id_or_username>` - Thoda bahar ghuma ke lao! 😉 (Admins & Owner)"
        "\n• `/pin <message_id>` - Important message ko upar rakho, sabko dikhe! ✨ (Admins & Owner)"
        "\n• `/unpin` - Ab bas karo, bohot ho gaya pin! 😅 (Admins & Owner)"
        "\n• `/setwelcome <message>` - Group mein naye guests ka swagat, mere style mein! 💖 (Admins & Owner)"
        "\n• `/getwelcome` - Dekho maine kya welcome message set kiya hai! (Admins & Owner)"
        "\n• `/clearwelcome` - Agar welcome message pasand nahi, toh hata do! 🤷‍♀️ (Admins & Owner)"
        "\n• `/restart bot` - Mujhe dubara se shuru karo aur deploy kar do! (Owner Only! 🚨)"
        "\n• `/resetall` - Saara data delete kar do, sab kuch! (Owner Only! 🚨🚨)"
        "\n\n**Note:** Admin commands ke liye, mujhe group mein zaroori permissions dena mat bhoolna, warna main kuch nahi kar paungi! 🥺"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Mujhe Apne Group Mein Bulao! 😉", url=f"https://t.me/{client.me.username}?startgroup=true")],
        [InlineKeyboardButton("📣 Meri Updates Yahan Milengi! 💖", url=f"https://t.me/{DEFAULT_UPDATE_CHANNEL_USERNAME}")],
        [InlineKeyboardButton("🤖 Apna Khud Ka Bot Banayein! (Premium)", callback_data="clone_bot_start")]
    ])
    await message.reply_text(help_text, reply_markup=keyboard)
    if message.from_user:
        await store_message(message, is_bot_sent=False)

# MYID COMMAND
@app.on_message(filters.command("myid") & (filters.private | filters.group))
async def my_id_command(client: Client, message: Message):
    user_id = message.from_user.id if message.from_user else "N/A"
    await message.reply_text(f"Hehe, tumhari user ID: `{user_id}`. Ab tum mere liye aur bhi special ho gaye! 😊")
    if message.from_user:
        await store_message(message, is_bot_sent=False)

# CHATID COMMAND
@app.on_message(filters.command("chatid") & (filters.private | filters.group))
async def chat_id_command(client: Client, message: Message):
    chat_id = message.chat.id
    await message.reply_text(f"Is chat ki ID: `{chat_id}`. Kya tum mujhe secrets bataoge? 😉")
    if message.from_user:
        await store_message(message, is_bot_sent=False)

# --- ADMIN COMMANDS ---

# Helper function to check if user is owner
def is_owner(user_id):
    return str(user_id) == str(OWNER_ID)

# Admin check decorator for bot owner only
async def owner_only_filter(_, __, message: Message):
    if message.from_user is not None and OWNER_ID is not None:
        return is_owner(message.from_user.id)
    return False

# New decorator for group admins (including owner)
async def group_admin_filter(_, client: Client, message: Message):
    if not message.from_user:
        return False

    user_id = message.from_user.id
    chat_id = message.chat.id

    if is_owner(user_id):
        return True

    if message.chat.type == ChatType.PRIVATE:
        return False

    try:
        member = await client.get_chat_member(chat_id, user_id)
        if member.status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
            return True
        else:
            return False
    except Exception as e:
        logger.error(f"Error checking admin status for user {user_id} in chat {chat_id}: {e}")
        return False

# BROADCAST COMMAND
@app.on_message(filters.command("broadcast") & filters.private & filters.create(owner_only_filter))
async def broadcast_command(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("Malik, kripya broadcast karne ke liye ek pyaara sa message dein. Upyog: `/broadcast Aapka message yahan`")
        if message.from_user:
            await store_message(message, is_bot_sent=False)
        return
    broadcast_text = " ".join(message.command[1:])
    if messages_collection is None:
        await message.reply_text("Maaf karna, broadcast nahi kar payi. Database (Main Learning DB) connect nahi ho paya hai. 🥺")
        if message.from_user:
            await store_message(message, is_bot_sent=False)
        return

    unique_chat_ids = messages_collection.distinct("chat_id")
    sent_count = 0
    failed_count = 0
    await message.reply_text("Malik, main ab sabko aapka message bhej rahi hoon! 😉")
    for chat_id in unique_chat_ids:
        try:
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
    if message.from_user:
        await store_message(message, is_bot_sent=False)

# RESET DATA COMMAND
@app.on_message(filters.command("resetdata") & filters.private & filters.create(owner_only_filter))
async def reset_data_command(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("Malik, kitna data delete karna hai? Percentage batao (1 se 100 ke beech). Upyog: `/resetdata <percentage>`")
        if message.from_user:
            await store_message(message, is_bot_sent=False)
        return
    try:
        percentage = int(message.command[1])
        if not (1 <= percentage <= 100):
            await message.reply_text("Percentage 1 se 100 ke beech hona chahiye, Malik! 😊")
            if message.from_user:
                await store_message(message, is_bot_sent=False)
            return

        if messages_collection is None:
            await message.reply_text("Maaf karna, data reset nahi kar payi. Database (Main Learning DB) connect nahi ho paya hai. 🥺")
            if message.from_user:
                await store_message(message, is_bot_sent=False)
            return

        total_messages = messages_collection.count_documents({})
        if total_messages == 0:
            await message.reply_text("Malik, database mein koi message hai hi nahi! Main kya delete karun? 🤷‍♀️")
            if message.from_user:
                await store_message(message, is_bot_sent=False)
            return

        messages_to_delete_count = int(total_messages * (percentage / 100))
        if messages_to_delete_count == 0 and percentage > 0 and total_messages > 0:
            messages_to_delete_count = 1

        if messages_to_delete_count == 0:
            await message.reply_text("Malik, itne kam messages hain ki diye gaye percentage par kuch delete nahi hoga. Kya karna hai? 🤔")
            if message.from_user:
                await store_message(message, is_bot_sent=False)
            return

        await message.reply_text(f"{messages_to_delete_count} sabse purane messages delete kiye ja rahe hain ({percentage}% of {total_messages}). Kripya intezaar karein, main saaf-safai kar rahi hoon! 🧹✨")

        oldest_message_ids = []
        for msg in messages_collection.find({}).sort("timestamp", 1).limit(messages_to_delete_count):
            oldest_message_ids.append(msg['_id'])

        if oldest_message_ids:
            delete_result = messages_collection.delete_many({"_id": {"$in": oldest_message_ids}})
            await message.reply_text(f"Successfully {delete_result.deleted_count} messages database se delete ho गए, Malik! Ab main aur smart banungi!💖")
            logger.info(f"Owner {message.from_user.id} deleted {delete_result.deleted_count} messages ({percentage}%).")
        else:
            await message.reply_text("Malik, koi message delete nahi ho paya. Shayad database khaali hai ya koi problem hai. 🥺")

    except ValueError:
        await message.reply_text("Invalid percentage. Kripya ek number dein, Malik! 🔢")
    except Exception as e:
        await message.reply_text(f"Data reset karte samay error aaya, Malik: {e}. Kya hua? 😭")
        logger.error(f"Error resetting data by owner {message.from_user.id}: {e}", exc_info=True)
    if message.from_user:
        await store_message(message, is_bot_sent=False)

# DELETE MESSAGE BY ID COMMAND
@app.on_message(filters.command("deletemessage") & filters.private & filters.create(owner_only_filter))
async def delete_message_by_id_command(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("Malik, kripya us message ki ID dein jise delete karna hai. Upyog: `/deletemessage <message_id>`")
        if message.from_user:
            await store_message(message, is_bot_sent=False)
        return
    try:
        msg_id_to_delete = int(message.command[1])

        if messages_collection is None:
            await message.reply_text("Maaf karna, message delete nahi kar payi. Database (Main Learning DB) connect nahi ho paya hai. 🥺")
            if message.from_user:
                await store_message(message, is_bot_sent=False)
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
    if message.from_user:
        await store_message(message, is_bot_sent=False)

# CLEAR PENDING REQUESTS COMMAND (NEW)
@app.on_message(filters.command("clearpending") & filters.private & filters.create(owner_only_filter))
async def clear_pending_requests_command(client: Client, message: Message):
    if user_states_collection is None:
        await message.reply_text("Maaf karna, pending requests clear nahi kar payi. Database (Clone/State DB) connect nahi ho paya hai. 🥺")
        if message.from_user:
            await store_message(message, is_bot_sent=False)
        return

    try:
        delete_result = user_states_collection.delete_many({"status": "pending_approval"})
        if delete_result.deleted_count > 0:
            await message.reply_text(f"Malik, {delete_result.deleted_count} pending approval requests delete ho gayi hain! Ab database saaf hai! ✨")
            logger.info(f"Owner {message.from_user.id} cleared {delete_result.deleted_count} pending clone requests.")
        else:
            await message.reply_text("Malik, koi pending approval request mili hi nahi! Sab theek hai! 😊")
    except Exception as e:
        await message.reply_text(f"Pending requests clear karte samay error aaya, Malik: {e}. Kya hua? 😭")
        logger.error(f"Error clearing pending requests by owner {message.from_user.id}: {e}", exc_info=True)
    if message.from_user:
        await store_message(message, is_bot_sent=False)


# NEW COMMAND: /readyclone <user_id> to approve a user for cloning
@app.on_message(filters.command("readyclone") & filters.private & filters.create(owner_only_filter))
async def ready_clone_command(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("Malik, kripya us user ki ID dein jise clone karne ki anumati deni hai. Upyog: `/readyclone <user_id>`")
        if message.from_user:
            await store_message(message, is_bot_sent=False)
        return

    try:
        target_user_id = str(message.command[1])

        if user_states_collection is None:
            await message.reply_text("Maaf karna, service abhi available nahi hai. Database (Clone/State DB) connect nahi ho paya hai. 🥺")
            if message.from_user:
                await store_message(message, is_bot_sent=False)
            return

        user_state = user_states_collection.find_one({"user_id": target_user_id})

        if not user_state:
            await message.reply_text(f"Malik, user ID `{target_user_id}` ka koi record nahi mila. Shayad usne abhi tak bot cloning start nahi kiya hai ya uska state clear ho gaya hai. 🤔")
            if message.from_user:
                await store_message(message, is_bot_sent=False)
            return

        if user_state.get("status") == "approved_for_clone":
            await message.reply_text(f"Malik, user `{target_user_id}` pehle se hi approved hai. Dobara karne ki zaroorat nahi! 😉")
            if message.from_user:
                await store_message(message, is_bot_sent=False)
            return

        # Update user status to approved_for_clone
        user_states_collection.update_one(
            {"user_id": target_user_id},
            {"$set": {"status": "approved_for_clone", "approved_on": datetime.now()}},
            upsert=True
        )
        logger.info(f"Owner {message.from_user.id} manually approved user {target_user_id} for cloning.")

        await message.reply_text(f"Malik, user `{target_user_id}` ko bot clone karne ke liye approve kar diya gaya hai! ✅")

        # Notify the user
        notify_message = (
            "Badhai ho, mere dost! 🎉 Tumhari Bot Cloning request approve ho gayi hai! ✅\n"
            "Ab tum apni pyaari si bot banane ke liye token bhej sakte ho:\n"
            "**Kaise?** `/clonebot YOUR_BOT_TOKEN_HERE`\n"
            "(Pura token ek hi line mein hona chahiye, jaldi karo na! 😉)"
        )
        try:
            await client.send_message(int(target_user_id), notify_message)
            await message.reply_text(f"User `{target_user_id}` ko approval notification bhej diya gaya hai. 😉")
        except Exception as e:
            logger.error(f"Error notifying user {target_user_id} about approval: {e}")
            await message.reply_text(f"User `{target_user_id}` ko notification bhejne mein error aaya: {e}. Lekin state update ho gayi hai! 🥺")

    except ValueError:
        await message.reply_text("Invalid user ID. Kripya ek valid number dein, Malik! 🔢")
    except Exception as e:
        await message.reply_text(f"Malik, user ko approve karte samay error aaya: {e}. Kya hua? 😭")
        logger.error(f"Error approving user for clone by owner {message.from_user.id}: {e}", exc_info=True)
    if message.from_user:
        await store_message(message, is_bot_sent=False)


# GROUP ADMIN COMMANDS (BAN, UNBAN, KICK, PIN, UNPIN)
async def perform_chat_action(client: Client, message: Message, action_type: str):
    if not message.reply_to_message and len(message.command) < 2:
        await message.reply_text(f"Malik, kripya us user ko reply karein jise {action_type} karna hai, ya user ID/username dein.\nUpyog: `/{action_type} <user_id_or_username>` ya message ko reply karein. Jaldi karo, mujhe masti karni hai! 💃")
        if message.from_user:
            await store_message(message, is_bot_sent=False)
        return

    target_user_id = None
    if message.reply_to_message and message.reply_to_message.from_user:
        target_user_id = message.reply_to_message.from_user.id
    elif len(message.command) >= 2:
        try:
            target_user_id = int(message.command[1])
        except ValueError:
            target_user_id = message.command[1]

    if not target_user_id:
        await message.reply_text("Malik, main us user ko dhundh nahi pa rahi hoon! Kya tumne sahi ID ya username diya? 🤔")
        if message.from_user:
            await store_message(message, is_bot_sent=False)
        return

    try:
        me_in_chat = await client.get_chat_member(message.chat.id, client.me.id)
        if not me_in_chat.privileges or (
            (not me_in_chat.privileges.can_restrict_members) and action_type in ["ban", "unban", "kick"]
        ) or (
            (not me_in_chat.privileges.can_pin_messages) and action_type in ["pin", "unpin"]
        ):
            await message.reply_text(f"Malik, mujhe {action_type} karne ke liye zaroori permissions ki zaroorat hai. Please de do na! 🙏")
            if message.from_user:
                await store_message(message, is_bot_sent=False)
            return
    except Exception as e:
        logger.error(f"Error checking bot permissions in chat {message.chat.id}: {e}", exc_info=True)
        await message.reply_text("Malik, permissions check karte samay error aaya. Kripya सुनिश्चित करें ki bot ko sahi permissions hain. 🥺")
        if message.from_user:
            await store_message(message, is_bot_sent=False)
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
                if message.from_user:
                    await store_message(message, is_bot_sent=False)
                return
            await client.pin_chat_message(message.chat.id, message.reply_to_message.id)
            await message.reply_text("Message pin kar diya gaya, Malik! Ab sabko dikhega! ✨")
        elif action_type == "unpin":
            await client.unpin_chat_messages(message.chat.id)
            await message.reply_text("Sabhi pinned messages unpin kar diye gaye, Malik! Ab group free hai! 🥳")
    except Exception as e:
        await message.reply_text(f"Malik, {action_type} karte samay error aaya: {e}. Mujhse ho nahi pa raha! 😭")
        logger.error(f"Error performing {action_type} by user {message.from_user.id if message.from_user else 'None'}: {e}", exc_info=True)
    if message.from_user:
        await store_message(message, is_bot_sent=False)

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
@app.on_message(filters.command("setwelcome") & filters.group & filters.create(group_admin_filter))
async def set_welcome_command(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("Malik, kripya welcome message dein.\nUpyog: `/setwelcome Aapka naya welcome message {user} {chat_title}`. Naye members ko surprise karte hain! 🥳")
        if message.from_user:
            await store_message(message, is_bot_sent=False)
        return
    welcome_msg_text = " ".join(message.command[1:])
    if group_configs_collection is None:
        await message.reply_text("Maaf karna, welcome message set nahi kar payi. Database (Commands/Settings DB) connect nahi ho paya hai. 🥺")
        if message.from_user:
            await store_message(message, is_bot_sent=False)
        return

    group_configs_collection.update_one(
        {"chat_id": message.chat.id},
        {"$set": {"welcome_message": welcome_msg_text}},
        upsert=True
    )
    await message.reply_text("Naya welcome message set kar diya gaya hai, Malik! Jab naya member aayega, toh main yahi pyaara message bhejoongi! 🥰")
    if message.from_user:
        await store_message(message, is_bot_sent=False)

@app.on_message(filters.command("getwelcome") & filters.group & filters.create(group_admin_filter))
async def get_welcome_command(client: Client, message: Message):
    config = None
    if group_configs_collection is not None:
        config = group_configs_collection.find_one({"chat_id": message.chat.id})

    if config and "welcome_message" in config:
        await message.reply_text(f"Malik, current welcome message:\n`{config['welcome_message']}`. Pasand aaya? 😉")
    else:
        await message.reply_text("Malik, is group ke liye koi custom welcome message set nahi hai. Kya set karna chahte ho? 🥺")
    if message.from_user:
        await store_message(message, is_bot_sent=False)

@app.on_message(filters.command("clearwelcome") & filters.group & filters.create(group_admin_filter))
async def clear_welcome_command(client: Client, message: Message):
    if group_configs_collection is None:
        await message.reply_text("Maaf karna, welcome message clear nahi kar payi. Database (Commands/Settings DB) connect nahi ho paya hai. 🥺")
        if message.from_user:
            await store_message(message, is_bot_sent=False)
        return

    group_configs_collection.update_one(
        {"chat_id": message.chat.id},
        {"$unset": {"welcome_message": ""}}
    )
    await message.reply_text("Malik, custom welcome message hata diya gaya hai. Ab main default welcome message bhejoongi. Kya main bori...ng ho gayi? 😔")
    if message.from_user:
        await store_message(message, is_bot_sent=False)

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
    if message.from_user:
        await store_message(message, is_bot_sent=False)


# --- PREMIUM CLONING LOGIC ---

# New callback for "Buy Git Repo" button
@app.on_callback_query(filters.regex("buy_git_repo"))
async def handle_buy_git_repo_callback(client: Client, callback_query: CallbackQuery):
    await callback_query.answer("Git Repo kharidne ki jaankari 😉", show_alert=False)
    repo_info_message = (
        "**Repository kharidne ke liye @asbhaibsr ko message kijiye. 📩**\n"
        "Yehi bot jo aap abhi use kar rahe hain, iska poora code base aapko ₹2000 mein mil jayega.\n\n"
        "**Kripya dhyan dein:** Sirf tabhi message karein jab aap sach mein ise kharidna chahte hon. Serious buyers hi sampark karein! 😊"
    )
    await callback_query.message.reply_text(repo_info_message)
    if callback_query.from_user:
        # We don't store button clicks as "messages" in the learning DB directly
        # but if specific logging for this action is needed, it would go here.
        pass


# Step 1: Initial /clonebot command (requires payment)
@app.on_message(filters.command("clonebot") & filters.private)
async def initiate_clone_payment(client: Client, message: Message):
    user_id = str(message.from_user.id)

    # Check if the command includes a bot token (meaning user is trying to clone immediately)
    if len(message.command) > 1:
        # If a token is provided, defer to the specific handler for token processing after approval
        # This prevents the payment flow from restarting if a token is given prematurely
        logger.info(f"User {user_id} sent /clonebot with a token. Passing to process_clone_bot_after_approval.")
        await process_clone_bot_after_approval(client, message)
        return

    if user_states_collection is None:
        await message.reply_text("Maaf karna, abhi bot cloning service available nahi hai. Database (Clone/State DB) connect nahi ho paya hai. 🥺")
        if message.from_user:
            await store_message(message, is_bot_sent=False)
        return

    user_state = user_states_collection.find_one({"user_id": user_id})

    if user_state and user_state.get("status") == "approved_for_clone":
        await message.reply_text(
            "Tum toh pehle se hi meri permission le chuke ho, mere dost! ✅\n"
            "Ab bas apna bot token bhejo, main tumhare liye ek naya bot bana dungi:\n"
            "**Kaise?** `/clonebot YOUR_BOT_TOKEN_HERE`\n"
            "(Pura token ek hi line mein hona chahiye, theek hai? 😉)"
        )
        if message.from_user:
            await store_message(message, is_bot_sent=False)
        return

    pending_request = user_states_collection.find_one({"user_id": user_id, "status": "pending_approval"})
    if pending_request:
        await message.reply_text(
            "Meri cute si request pehle se hi pending hai, darling! ⏳\n"
            "Kripya admin ke approval ka intezaar karo. Agar payment aur screenshot bhej diya hai, toh thoda sabar karo na! 😊"
        )
        if message.from_user:
            await store_message(message, is_bot_sent=False)
        return

    # If no pending or approved state, start fresh
    payment_message = (
        f"Clone banane ke liye aapko ₹{PAYMENT_INFO['amount']} dene zaroori hai tabhi aap clone bana sakte hain. 💰"
        f"\n\n**Payment Details (Meri Secret Jaan!):**\n"
        f"UPI ID: `{PAYMENT_INFO['upi_id']}`\n\n"
        f"{PAYMENT_INFO['instructions']}\n"
        "Jaldi karo, main wait kar rahi hoon! 😉"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Screenshot Bhejo Na! 🥰", callback_data="send_screenshot_prompt")],
        [InlineKeyboardButton("🚫 Rehne Do, Nahi Banwana 😔", callback_data="cancel_clone_request")],
        [InlineKeyboardButton("Git Repo Khareedein 💸", callback_data="buy_git_repo")] # Added new button here
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
    if message.from_user:
        await store_message(message, is_bot_sent=False)

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
        # It's better to reset the state if it's not the expected "awaiting_screenshot"
        if user_states_collection is not None:
            user_states_collection.delete_one({"user_id": user_id})
        logger.warning(f"User {user_id} tried screenshot prompt from wrong state: {user_state.get('status') if user_state else 'None'}")


# Step 3: Receive screenshot and forward to owner
@app.on_message(
    filters.photo & filters.private &
    (lambda client_obj, message: message.from_user and user_states_collection is not None and user_states_collection.find_one({"user_id": str(message.from_user.id), "status": "expecting_screenshot"})) # Corrected lambda and MongoDB check
)
async def receive_screenshot(client: Client, message: Message):
    user_id = str(message.from_user.id)

    if user_states_collection is None:
        logger.error("user_states_collection is None. Cannot process screenshot. Please check MongoDB connection for CLONE_STATE_MONGO_DB_URI.")
        await message.reply_text("Maaf karna, payment screenshot service abhi available nahi hai. Database mein kuch gadbad hai. 🥺")
        return

    user_state = user_states_collection.find_one({"user_id": user_id})
    logger.info(f"Received photo from user {user_id}. User state: {user_state.get('status') if user_state else 'None'}")

    if user_state and user_state.get("status") == "expecting_screenshot":
        await message.reply_text(
            "Aapka pyaara screenshot mujhe mil gaya hai! ✅\n"
            "Abhi rukiye ye screenshot hamre owner ko check karne ke liye gaya hai. Wo ise check karenge aur aapko bot clone karne ki anumati denge. Saath hi, aapko is command ko dhyaan se istemal karna hoga: `/clonebot YOUR_BOT_TOKEN_HERE` tabhi aap bot bana payenge! 😉"
        )

        caption_to_owner = (
            f"💰 **New Payment Proof (Malik, Dekho!):**\n"
            f"User: {message.from_user.mention} (`{user_id}`)\n"
            f"Amount: ₹{PAYMENT_INFO['amount']}\n\n"
            f"Is user ko approve karne ke liye: `/readyclone {user_id}`"
        )
        try:
            await client.send_photo(
                chat_id=int(OWNER_ID),
                photo=message.photo.file_id,
                caption=caption_to_owner
            )
            logger.info(f"Screenshot received from user {user_id}. Forwarded to owner ({OWNER_ID}) for approval with user ID.")
        except Exception as e:
            logger.error(f"Error forwarding screenshot to owner {OWNER_ID}: {e}", exc_info=True)
            await message.reply_text("Maaf karna, aapka screenshot owner tak pahunchane mein kuch error ho gaya. Kripya baad mein koshish karein. 🥺")


        if user_states_collection is not None:
            user_states_collection.update_one(
                {"user_id": user_id},
                {"$set": {"status": "pending_approval", "screenshot_message_id": message.id}}
            )
    else:
        logger.warning(f"Photo received from user {user_id} but not in expected state for screenshot: {user_state.get('status') if user_state else 'None'}. Not processing as screenshot.")
        # If photo is sent but not in the right state, give a hint
        await message.reply_text("Arre, tumne galat samay par screenshot bhej diya! 😳 Kripya `/clonebot` se shuru karo aur phir jab main kahoon tab screenshot bhejo. 😉")


    if message.from_user:
        await store_message(message, is_bot_sent=False)

# NEW: Handle cancel clone request
@app.on_callback_query(filters.regex("cancel_clone_request"))
async def cancel_clone_request(client: Client, callback_query: CallbackQuery):
    user_id = str(callback_query.from_user.id)
    if user_states_collection is None:
        await callback_query.answer("Maaf karna, abhi service available nahi hai. Database mein kuch gadbad hai. 🥺", show_alert=True)
        return

    user_states_collection.delete_one({"user_id": user_id})
    await callback_query.message.edit_text("Theek hai, agar aap abhi clone nahi banana chahte toh koi baat nahi. Jab man kare, `/clonebot` se dobara shuru kar sakte hain! 😉")
    await callback_query.answer("Clone request cancel kar di gayi.", show_alert=True)
    logger.info(f"User {user_id} cancelled clone request.")


# Step 5: Process actual clonebot command after approval
@app.on_message(filters.command("clonebot") & filters.private & filters.regex(r'/clonebot\s+([A-Za-z0-9:_-]+)'))
async def process_clone_bot_after_approval(client: Client, message: Message):
    user_id = str(message.from_user.id)

    if user_states_collection is None:
        await message.reply_text("Maaf karna, abhi bot cloning service available nahi hai. Database (Clone/State DB) connect nahi ho paya hai. 🥺")
        if message.from_user:
            await store_message(message, is_bot_sent=False)
        return

    user_state = user_states_collection.find_one({"user_id": user_id})

    if not user_state or user_state.get("status") != "approved_for_clone":
        # If user is not approved, or in a wrong state, tell them to start the /clonebot process first
        await message.reply_text(
            "Arre, tum bot clone karne ke liye approved nahi ho! 🥺\n"
            "Clone banane ke liye aapko ₹200 dene zaroori hai. Kripya pehle payment process poora karo, "
            "`/clonebot` command dekar. Main intzaar kar rahi hoon! 😉"
        )
        if message.from_user:
            await store_message(message, is_bot_sent=False)
        return

    bot_token = message.command[1].strip()
    if not re.match(r'^\d+:[A-Za-z0-9_-]+$', bot_token):
        await message.reply_text("Yeh bot token sahi nahi lag raha. Kripya ek valid token dein. Main confuse ho gayi! 😵‍💫")
        if message.from_user:
            await store_message(message, is_bot_sent=False)
        return

    await message.reply_text("Tumhare bot token ki jaanch kar rahi hoon, darling! Thoda wait karo... 💖")

    try:
        # Ensure API_ID is not None before converting
        if API_ID is None:
            await message.reply_text("API_ID environment variable set nahi hai, darling! Kripya bot owner se contact karein. 😭")
            # Keep user in approved_for_clone state so they can try again if owner fixes API_ID
            if user_states_collection is not None:
                user_states_collection.update_one({"user_id": user_id}, {"$set": {"status": "approved_for_clone"}})
            return

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
        # Keep user in approved_for_clone state so they can try again with correct token
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

    if message.from_user:
        await store_message(message, is_bot_sent=False)

# Step 6: Receive update channel link and finalize clone
@app.on_message(
    filters.text & filters.private &
    filters.reply & # Ensure it's a reply
    (lambda client_obj, message: message.reply_to_message and message.reply_to_message.from_user and message.reply_to_message.from_user.is_self and
                         message.reply_to_message.reply_markup and isinstance(message.reply_to_message.reply_markup, ForceReply) and
                         "update channel" in message.reply_to_message.text.lower())
)
async def finalize_clone_process(client: Client, message: Message):
    user_id = str(message.from_user.id)

    if user_states_collection is None:
        logger.error("user_states_collection is None. Cannot process channel link for clone flow. Please check MongoDB connection for CLONE_STATE_MONGO_DB_URI.")
        return

    user_state = user_states_collection.find_one({"user_id": user_id, "status": "awaiting_channel"})

    if not user_state:
        logger.warning(f"Text received from user {user_id} but not in expected state for channel: {user_state.get('status') if user_state else 'None'}. Not processing as channel link.")
        # If it's not in the expected state, let the general message handler take over
        # This will prevent an infinite loop if the user replies with something irrelevant
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
                # Attempt to get chat to verify it's a valid channel
                chat = await client.get_chat(f"@{final_update_channel}")
                if not chat.type == ChatType.CHANNEL:
                    await message.reply_text("Yeh ek valid channel username/link nahi lag raha, darling! Kripya sahi channel ka username (@channelname) ya link (t.me/channelname) dein, ya 'no' type karo. Mujhko samjho na! 🥺")
                    if message.from_user:
                        await store_message(message, is_bot_sent=False)
                    return
            except Exception as e:
                logger.warning(f"Could not verify channel {final_update_channel}: {e}")
                await message.reply_text("Channel ko verify nahi kar payi, darling! Kripya sahi channel ka username (@channelname) ya link (t.me/channelname) dein, ya 'no' type karo. Kya main galti kar rahi hoon? 😔")
                if message.from_user:
                    await store_message(message, is_bot_sent=False)
                return

            logger.info(f"User {user_id} set update channel to @{final_update_channel}")
        else:
            await message.reply_text("Invalid channel username/link, darling! Kripya sahi channel ka username (@channelname) ya link (t.me/channelname) dein, ya 'no' type karo. Main confusion mein hoon! 😵‍💫")
            if message.from_user:
                await store_message(message, is_bot_sent=False)
            return

    else:
        logger.info(f"User {user_id} chose default update channel: @{DEFAULT_UPDATE_CHANNEL_USERNAME}")

    await message.reply_text(
        "Badhai ho, mere cute dost! 🎉 Tumhare bot ke liye saari settings complete ho gayi hain.\n\n"
        "Ab tum is pyaare bot ko deploy kar sakte ho! Tumhara bot token aur update channel niche diye gaye hain:\n"
        f"**Bot Token:** `{user_state['bot_token']}`\n"
        f"**Bot Username:** `@{user_state['bot_username']}`\n"
        f"**Updates Channel:** `https://t.me/{final_update_channel}`\n\n"
        "**Deployment ke liye easy steps:**\n"
        "1. Meri GitHub repository ko fork karo (agar nahi kiya hai toh).\n"
        "2. Apni `main.py` file mein `BOT_TOKEN`, `API_ID`, `API_HASH` aur `OWNER_ID` ko apne hisaab se Environment Variables mein set karo.\n"
        f"3. Aur haan, `main.py` mein `DEFAULT_UPDATE_CHANNEL_USERNAME` ko `'{final_update_channel}'` par set karna mat bhoolna! (Ya phir apne forked repo mein yeh value directly daal do)\n"
        "4. Koyeb (ya kisi bhi hosting) par deploy karo, Environment Variables mein saari details dena. Fir dekho mera jaisa pyaara bot kaise kaam karta hai! 💖\n\n"
        "Kisi bhi sawal ke liye @aschat_group channel par aana na bhoolna! Main wahin milungi! 😉"
    )

    if user_states_collection is not None:
        user_states_collection.delete_one({"user_id": user_id})
    logger.info(f"User {user_id} clone process finalized and state cleared.")
    if message.from_user:
        await store_message(message, is_bot_sent=False)


# --- Private Chat General Message Handler (Fallback for non-commands/non-cloning) ---
@app.on_message(
    filters.private &
    (filters.text | filters.sticker | filters.photo | filters.video | filters.document | filters.audio | filters.voice | filters.animation) &
    ~filters.via_bot &
    (lambda client_obj, msg: not msg.text or not msg.text.startswith('/')) & # Ensure it's not a command
    ~filters.reply # IMPORTANT: This excludes replies, letting specific handlers like receive_screenshot handle them for cloning
)
async def handle_private_general_messages(client: Client, message: Message):
    user_id = str(message.from_user.id) if message.from_user else "N/A"

    # Store user's message if it's a command (already handled by specific command handlers)
    # or if it's part of the cloning flow where we specifically need to track replies (e.g., screenshot)
    # General private chat messages are NOT stored for learning as per new requirement.
    # The store_message function itself now filters based on ChatType.PRIVATE

    if user_states_collection is None:
        await message.reply_text("Maaf karna, bot abhi poori tarah se ready nahi hai. Kuch database issues hain (Clone/State DB connect nahi ho paya). 🥺")
        return

    user_state = user_states_collection.find_one({"user_id": user_id})

    # Handle messages relevant to the cloning flow
    if user_state is not None:
        status = user_state.get("status")
        if status == "awaiting_screenshot" or status == "expecting_screenshot":
            # If user sent a text message in these states, prompt for screenshot again
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
    
    # If not part of cloning flow and not a command, do nothing in private chat.
    # As per user's request, no general "learning-based" replies in private chat.
    logger.debug(f"Ignoring general private message {message.id} from user {user_id}. Not part of cloning flow or command, and no general replies in private.")


# --- Standard message handler (general text/sticker messages in groups) ---
@app.on_message(filters.group & (filters.text | filters.sticker | filters.photo | filters.video | filters.document | filters.audio | filters.voice | filters.animation))
async def handle_general_messages(client: Client, message: Message):
    global last_bot_reply_time

    if message.from_user and message.from_user.is_bot:
        return

    if message.text and message.text.startswith('/'):
        return

    # Store the message for learning if it's in a group
    if message.from_user:
        await store_message(message, is_bot_sent=False)

    chat_id = message.chat.id
    current_time = time.time()

    if chat_id in last_bot_reply_time:
        time_since_last_reply = current_time - last_bot_reply_time[chat_id]
        if time_since_last_reply < REPLY_COOLDOWN_SECONDS:
            logger.info(f"Cooldown active for group chat {chat_id}. Not generating reply for message {message.id}.")
            return

    logger.info(f"Attempting to generate reply for group chat {message.chat.id}")
    reply_doc = await generate_reply(client, message) # Passed client here

    if reply_doc:
        try:
            sent_msg = None
            content_type = reply_doc.get("content_type")
            content_to_send = reply_doc.get("content")
            file_to_send = reply_doc.get("file_id")

            # Store the bot's own reply for future learning
            bot_reply_message_data = {
                "chat_id": message.chat.id,
                "message_id": -1, # Placeholder, will be updated after sending
                "user_id": client.me.id,
                "username": client.me.username,
                "first_name": client.me.first_name,
                "chat_type": message.chat.type.name,
                "chat_title": message.chat.title if message.chat.type != ChatType.PRIVATE else None,
                "timestamp": datetime.now(),
                "is_bot_sent": True,
                "content_type": content_type,
                "content": content_to_send,
                "file_id": file_to_send,
                "keywords": extract_keywords(content_to_send),
                "replied_to_message_id": message.id, # The message this bot replied to
                "replied_to_user_id": message.from_user.id if message.from_user else None,
                "replied_to_content": message.text, # The content of the message this bot replied to
                "replied_to_content_type": message.media.value if message.media else ("text" if message.text else "unknown"),
                "has_received_reply": False, # Will be set to True if a user replies to this bot's message
                "replied_by_user_id": None,
                "replied_message_content": None,
                "is_bot_observed_pair": False, # This is a bot's reply, not a user's reply to a bot.
            }


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
                logger.warning(f"Reply document found but no recognized content type or file_id: {reply_doc}")

            if sent_msg:
                bot_reply_message_data["message_id"] = sent_msg.id # Update with actual message ID
                if messages_collection is not None:
                    messages_collection.insert_one(bot_reply_message_data)
                    logger.debug(f"Bot's reply stored: {sent_msg.id} to user message {message.id}")
                last_bot_reply_time[chat_id] = time.time()
                # await store_message(sent_msg, is_bot_sent=True) # This is now handled by the explicit insert_one above
        except Exception as e:
            logger.error(f"Error sending reply for message {message.id}: {e}", exc_info=True)
    else:
        logger.info(f"No suitable reply generated for message {message.id}.")


# --- New Admin Commands ---

@app.on_message(filters.command("restart") & filters.private & filters.create(owner_only_filter))
async def restart_bot_command(client: Client, message: Message):
    if len(message.command) < 2 or message.command[1].lower() != "bot":
        await message.reply_text("Malik, agar mujhe restart karna hai toh aise bolo: `/restart bot`. Main sab samajh jaungi! 😉")
        if message.from_user:
            await store_message(message, is_bot_sent=False)
        return

    await message.reply_text("Malik, main ab khud ko restart kar rahi hoon. Thoda intezaar karo, main jaldi wapas aungi!💖")
    logger.info(f"Owner {message.from_user.id} initiated bot restart.")

    # Stop Pyrogram client gracefully
    await app.stop()
    logger.info("Pyrogram client stopped. Restarting process...")

    # Restart the current Python script
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
        if message.from_user:
            await store_message(message, is_bot_sent=False)
        return

    await message.reply_text("Malik, aapne mujhe saara data delete karne ka bol diya! Main ab sab kuch mita rahi hoon. 🗑️✨\n"
                             "Kripya intezaar karein, yeh thoda samay le sakta hai...")

    try:
        deleted_collections_count = 0

        # Drop all collections in main_db
        if main_db:
            collection_names = await main_db.list_collection_names()
            for collection_name in collection_names:
                await main_db.drop_collection(collection_name)
                logger.info(f"Collection '{collection_name}' dropped from Main Learning DB.")
                deleted_collections_count += 1
        else:
            logger.warning("Main Learning DB not connected, skipping data deletion.")

        # Drop all collections in clone_state_db
        if clone_state_db:
            collection_names = await clone_state_db.list_collection_names()
            for collection_name in collection_names:
                await clone_state_db.drop_collection(collection_name)
                logger.info(f"Collection '{collection_name}' dropped from Clone/State DB.")
                deleted_collections_count += 1
        else:
            logger.warning("Clone/State DB not connected, skipping data deletion.")

        # Drop all collections in commands_settings_db
        if commands_settings_db:
            collection_names = await commands_settings_db.list_collection_names()
            for collection_name in collection_names:
                await commands_settings_db.drop_collection(collection_name)
                logger.info(f"Collection '{collection_name}' dropped from Commands/Settings DB.")
                deleted_collections_count += 1
        else:
            logger.warning("Commands/Settings DB not connected, skipping data deletion.")

        await message.reply_text(
            f"Malik, saara data delete ho gaya! Total **{deleted_collections_count}** collections saaf kar diye. "
            "Ab main bilkul nayi ho gayi hoon! 🥰\n"
            "Mujhe dobara train karna padega! "
            "Agar aap chahen toh ab bot ko restart kar sakte hain: `/restart bot`"
        )
        logger.info(f"Owner {message.from_user.id} successfully reset all MongoDB data.")

    except Exception as e:
        await message.reply_text(f"Malik, data delete karte samay error aaya: {e}. Mujhse ho nahi pa raha! 😭")
        logger.error(f"Error resetting all data by owner {message.from_user.id}: {e}", exc_info=True)
    if message.from_user:
        await store_message(message, is_bot_sent=False)

# --- Flask Web Server for Health Check ---
flask_app = Flask(__name__)

@flask_app.route('/')
def health_check():
    mongo_status_main = "Disconnected"
    mongo_status_clone_state = "Disconnected"
    mongo_status_commands_settings = "Disconnected"

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
        mongo_db_clone_state_status=mongo_status_clone_state, # Corrected: now shows correct status for clone state
        mongo_db_commands_settings_status=mongo_status_commands_settings,
        timestamp=datetime.now().isoformat()
    )

def run_flask_app():
    port = int(os.getenv('PORT', 8000))
    logger.info(f"Flask health check server starting on 0.0.0.0:{port}")
    # In a production environment, consider using a WSGI server like Gunicorn instead of Flask's built-in server.
    flask_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False, threaded=True)

# --- Main entry point ---
if __name__ == "__main__":
    logger.info("Cutie Pie bot running. ✨")

    flask_thread = Thread(target=run_flask_app)
    flask_thread.daemon = True
    flask_thread.start()

    app.run()
