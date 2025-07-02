import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.raw.functions.messages import SetTyping
from pyrogram.raw.types import SendMessageTypingAction

from pymongo import MongoClient
from datetime import datetime, timedelta
import logging
import re
import random

# --- Logger Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Environment Variables ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_DB_URI = os.getenv("MONGO_DB_URI")
OWNER_ID = os.getenv("OWNER_ID")
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

# --- Constants ---
MAX_MESSAGES_THRESHOLD = 50000 # Adjusted for better memory management
PRUNE_PERCENTAGE = 0.30
UPDATE_CHANNEL_USERNAME = "asbhai_bsr"

# --- MongoDB Setup ---
try:
    client = MongoClient(MONGO_DB_URI)
    db = client.bot_database
    messages_collection = db.messages
    logger.info("MongoDB connection successful.")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {e}")
    # Bot will exit if DB connection fails, which is desirable
    exit(1)

# --- Pyrogram Client ---
app = Client(
    "self_learning_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# --- Utility Functions ---
def extract_keywords(text):
    """Extracts basic keywords from a message."""
    if not text:
        return []
    words = re.findall(r'\b\w+\b', text.lower())
    return list(set(words))

async def prune_old_messages():
    """Removes old messages from the database when the threshold is crossed."""
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

async def store_message(message: Message):
    """Stores incoming messages in the database."""
    try:
        # Don't store bot's own messages to avoid infinite loops and unnecessary data
        if message.from_user and message.from_user.is_bot:
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
            "is_bot_observed_pair": False, # Default to False, will be set true if it's a learned pair
        }

        # Handle text messages
        if message.text:
            message_data["type"] = "text"
            message_data["content"] = message.text
            message_data["keywords"] = extract_keywords(message.text)
            message_data["sticker_id"] = None
        # Handle sticker messages
        elif message.sticker:
            message_data["type"] = "sticker"
            message_data["content"] = message.sticker.emoji if message.sticker.emoji else "" # Store emoji as content
            message_data["sticker_id"] = message.sticker.file_id
            message_data["keywords"] = extract_keywords(message.sticker.emoji) # Stickers se bhi keywords (emoji)

        # Reply to message context (important for learning)
        if message.reply_to_message:
            message_data["is_reply"] = True
            message_data["replied_to_message_id"] = message.reply_to_message.id
            message_data["replied_to_user_id"] = message.reply_to_message.from_user.id if message.reply_to_message.from_user else None
            
            # Get content of the replied message
            replied_content = None
            if message.reply_to_message.text:
                replied_content = message.reply_to_message.text
            elif message.reply_to_message.sticker:
                replied_content = message.reply_to_message.sticker.emoji if message.reply_to_message.sticker.emoji else ""
            
            message_data["replied_to_content"] = replied_content

            # If this message is a reply, we can mark the original message (if found in DB)
            # as part of a learned pair (is_bot_observed_pair)
            original_msg_in_db = messages_collection.find_one({"chat_id": message.chat.id, "message_id": message.reply_to_message.id})
            if original_msg_in_db:
                messages_collection.update_one(
                    {"_id": original_msg_in_db["_id"]},
                    {"$set": {"is_bot_observed_pair": True}}
                )
                # Also mark the current message (the reply) as part of an observed pair
                message_data["is_bot_observed_pair"] = True

        messages_collection.insert_one(message_data)
        logger.debug(f"Message stored: {message.id} from {message.from_user.id if message.from_user else 'None'}")
        
        # Check for pruning after storing a message
        await prune_old_messages()

    except Exception as e:
        logger.error(f"Error storing message {message.id}: {e}")

async def generate_reply(message: Message):
    """Generates a reply for the bot."""
    # Show typing action before generating a reply
    await app.invoke(
        SetTyping(
            peer=await app.resolve_peer(message.chat.id),
            action=SendMessageTypingAction()
        )
    )
    await asyncio.sleep(0.5) # Small delay for a more natural feel

    if not message.text and not message.sticker:
        return

    query_content = message.text if message.text else (message.sticker.emoji if message.sticker else "")
    query_keywords = extract_keywords(query_content)

    if not query_keywords and not query_content:
        logger.debug("No content or keywords extracted for reply generation.")
        return

    # 1. Search for Direct Contextual Matches (is_bot_observed_pair=True)
    # Try group-specific first
    learned_replies_group_cursor = messages_collection.find({
        "chat_id": message.chat.id,
        "is_bot_observed_pair": True,
        "replied_to_content": {"$regex": f"^{re.escape(query_content)}$", "$options": "i"}
    })
    
    potential_replies = []
    for doc in learned_replies_group_cursor:
        potential_replies.append(doc)

    if not potential_replies: # If no exact match in group, look globally
        learned_replies_global_cursor = messages_collection.find({
            "is_bot_observed_pair": True,
            "replied_to_content": {"$regex": f"^{re.escape(query_content)}$", "$options": "i"}
        })
        for doc in learned_replies_global_cursor:
            potential_replies.append(doc)

    if potential_replies:
        chosen_reply = random.choice(potential_replies)
        return chosen_reply

    logger.info(f"No direct observed reply for: '{query_content}'. Falling back to keyword search.")

    # 2. Fallback to General Keyword Matching (any stored message)
    keyword_regex = "|".join([re.escape(kw) for kw in query_keywords])
    
    # Try group-specific general messages first
    general_replies_group_cursor = messages_collection.find({
        "chat_id": message.chat.id,
        "type": {"$in": ["text", "sticker"]},
        "content": {"$regex": f".*({keyword_regex}).*", "$options": "i"} if keyword_regex else {"$exists": True}
    })

    potential_replies = []
    for doc in general_replies_group_cursor:
        potential_replies.append(doc)

    if not potential_replies: # If no match in group, look globally
        general_replies_global_cursor = messages_collection.find({
            "type": {"$in": ["text", "sticker"]},
            "content": {"$regex": f".*({keyword_regex}).*", "$options": "i"} if keyword_regex else {"$exists": True}
        })
        for doc in general_replies_global_cursor:
            potential_replies.append(doc)

    if potential_replies:
        chosen_reply = random.choice(potential_replies)
        return chosen_reply
    
    logger.info(f"No general keyword reply found for: '{query_content}'.")
    return None

# --- Pyrogram Event Handlers ---

@app.on_message(filters.command("start") & filters.private)
async def start_private_command(client: Client, message: Message):
    """Handles /start command in private chat."""
    welcome_messages = [
        "Hi there! 👋 Main aa gayi hoon aapki baaton ka hissa banne. Chalo, kuch mithaas bhari baatein karte hain!",
        "Helloooo! 💖 Main sunne aur seekhne ke liye taiyar hoon. Aapki har baat mere liye khaas hai!",
        "Namaste, pyaare dost! ✨ Main yahan aapke shabdon ko sametne aur unhe naya roop dene aayi hoon. Kaisi ho/ho tum?",
        "Hey cutie! Main aa gayi hoon aapke sath baatein karne. Ready to chat? 😉",
        "Koshish karne walon ki kabhi haar nahi hoti! Main bhi aapki baaton se seekhne ki koshish kar rahi hoon. Aao, baat karein!",
        "Hello! Main ek bot hoon jo aapki baaton ko samajhta aur unse seekhta hai. Aao, baat karte hain, theek hai?"
    ]
    
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("➕ Add Me to Your Group", url=f"https://t.me/{client.me.username}?startgroup=true")
            ],
            [
                InlineKeyboardButton("📣 Updates Channel", url=f"https://t.me/{UPDATE_CHANNEL_USERNAME}")
            ]
        ]
    )

    await message.reply_text(random.choice(welcome_messages), reply_markup=keyboard)
    await store_message(message)

@app.on_message(filters.command("start") & filters.group)
async def start_group_command(client: Client, message: Message):
    """Handles /start command in groups."""
    welcome_messages = [
        "Hello, my lovely group! 👋 Main aa gayi hoon aapki conversations mein shamil hone. Kya chal raha hai sabke beech?",
        "Hey everyone! 💖 Main sun rahi hoon aap sab ki baatein. Chalo, kuch interesting discussions karte hain!",
        "Is group ki conversations ko samajhne aayi hoon! ✨ Aap sab ki baaton se seekhna kitna mazedaar hai. Shuru ho jao!",
        "Namaste to all the amazing people here! Let's create some beautiful memories (aur data) together. 😄",
        "Duniya gol hai, aur baatein anmol! Main bhi yahan aapki anmol baaton ko store karne aayi hoon. Sunane ko taiyar hoon! 📚"
    ]

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("📣 Updates Channel", url=f"https://t.me/{UPDATE_CHANNEL_USERNAME}")
            ]
        ]
    )

    await message.reply_text(random.choice(welcome_messages), reply_markup=keyboard)
    await store_message(message)

@app.on_message(filters.command("broadcast") & filters.private)
async def broadcast_command(client: Client, message: Message):
    """Handles /broadcast command (owner only)."""
    if str(message.from_user.id) != OWNER_ID:
        await message.reply_text("Sorry, aapko yeh command use karne ki anumati nahi hai.")
        return

    if len(message.command) < 2:
        await message.reply_text("Kripya broadcast karne ke liye ek message dein. Upyog: `/broadcast Aapka message yahan`")
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
            logger.error(f"Failed to send broadcast to chat {chat_id}: {e}")
            failed_count += 1
    
    await message.reply_text(f"Broadcast poora hua! {sent_count} chats ko bheja, {failed_count} chats ke liye asafal raha.")
    await store_message(message)

@app.on_message(filters.command("stats") & filters.private)
async def stats_private_command(client: Client, message: Message):
    """Handles /stats command in private chat."""
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

@app.on_message(filters.command("stats") & filters.group)
async def stats_group_command(client: Client, message: Message):
    """Handles /stats command in group chat."""
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

@app.on_message(filters.text | filters.sticker)
async def handle_message_and_reply(client: Client, message: Message):
    """Handles all incoming text and sticker messages."""
    # Don't process messages from other bots
    if message.from_user and message.from_user.is_bot:
        return

    # Store the incoming message first
    await store_message(message)

    # Attempt to generate and send a reply
    logger.info(f"Attempting to generate reply for chat {message.chat.id}")
    reply_doc = await generate_reply(message)
    
    if reply_doc:
        try:
            if reply_doc.get("type") == "text":
                await message.reply_text(reply_doc["content"])
                logger.info(f"Replied with text: {reply_doc['content']}")
            elif reply_doc.get("type") == "sticker" and reply_doc.get("sticker_id"):
                await message.reply_sticker(reply_doc["sticker_id"])
                logger.info(f"Replied with sticker: {reply_doc['sticker_id']}")
            else:
                logger.warning(f"Reply document found but no content/sticker_id: {reply_doc}")
        except Exception as e:
            logger.error(f"Error sending reply for message {message.id}: {e}")
    else:
        logger.info("No suitable reply found.")


# --- Main entry point ---
if __name__ == "__main__":
    logger.info("Starting bot...")
    # This will run the Pyrogram client in a blocking manner.
    # The Docker CMD will ensure the Flask server runs in parallel.
    app.run()
