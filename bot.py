import os
import asyncio
import random
import logging
import re
from pyrogram import Client, filters, idle
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from motor.motor_asyncio import AsyncIOMotorClient
import datetime
from collections import defaultdict

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Bot Configuration (Environment Variables) ---
API_ID = int(os.environ.get("API_ID", "YOUR_API_ID"))
API_HASH = os.environ.get("API_HASH", "YOUR_API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN")
MONGO_URI = os.environ.get("MONGO_URI", "YOUR_MONGO_URI")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "YOUR_ADMIN_ID"))

# --- Learning Data Management Configuration ---
MAX_LEARNING_MESSAGES = int(os.environ.get("MAX_LEARNING_MESSAGES", 10000))
CLEANUP_THRESHOLD_PERCENT = 0.50

# --- Reply Delay Configuration ---
REPLY_DELAY_SECONDS = 3
REPLY_PROBABILITY = 0.15 # Probability of bot replying in a group after the delay (0.0 to 1.0)

# --- Specific Word Count for Replies ---
ALLOWED_REPLY_WORD_COUNTS = [2, 3, 5, 6, 7] 

# --- Global Buffers for delayed replies ---
chat_message_buffers = defaultdict(list) 
chat_reply_pending = defaultdict(bool)
chat_reply_locks = defaultdict(asyncio.Lock)


# --- Your Channel/Group Links ---
TELEGRAM_MAIN_CHANNEL = "t.me/asbhai_bsr"
TELEGRAM_CHAT_GROUP = "t.me/aschat_group" 
TELEGRAM_MOVIE_GROUP = "t.me/istreamx"

# Initialize Pyrogram Client
bot = Client(
    "self_learning_girl_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Initialize MongoDB
db_client = AsyncIOMotorClient(MONGO_URI)
db = db_client.self_learning_bot_db
chats_collection = db.chats
users_collection = db.users

# --- Helper Functions for MongoDB ---
async def save_message_for_learning(chat_id, user_id, message_text=None, sticker_file_id=None):
    """Saves a message or sticker for the bot to 'learn' from."""
    if message_text:
        message_text = re.sub(r'@\w+', '', message_text).strip()
        message_text = re.sub(r'https?://\S+', '', message_text).strip()
        if not message_text:
            return

    try:
        await chats_collection.insert_one({
            "chat_id": chat_id,
            "user_id": user_id,
            "message_text": message_text,
            "sticker_file_id": sticker_file_id,
            "timestamp": datetime.datetime.now(),
            "word_count": len(message_text.split()) if message_text else 0 # Store word count for easier filtering
        })
        logger.debug(f"Saved message from chat {chat_id}: text='{message_text}', sticker={sticker_file_id is not None}")
        await manage_learning_data_size()

    except Exception as e:
        logger.error(f"Error saving message to DB: {e}")

async def manage_learning_data_size():
    """Manages the size of the learning data by deleting oldest messages."""
    try:
        current_count = await chats_collection.count_documents({})
        if current_count > MAX_LEARNING_MESSAGES:
            logger.info(f"Learning data count ({current_count}) exceeded MAX_LEARNING_MESSAGES ({MAX_LEARNING_MESSAGES}). Initiating cleanup.")
            
            messages_to_delete_count = int(MAX_LEARNING_MESSAGES * CLEANUP_THRESHOLD_PERCENT)
            
            oldest_messages = await chats_collection.find({}) \
                                                    .sort("timestamp", 1) \
                                                    .limit(messages_to_delete_count) \
                                                    .to_list(None)

            if oldest_messages:
                oldest_ids = [doc["_id"] for doc in oldest_messages]
                delete_result = await chats_collection.delete_many({"_id": {"$in": oldest_ids}})
                logger.info(f"Deleted {delete_result.deleted_count} oldest learning messages.")
            else:
                logger.warning("No oldest messages found for deletion, even though count exceeded limit.")

    except Exception as e:
        logger.error(f"Error managing learning data size: {e}")


async def get_random_message_for_reply(chat_id=None):
    """
    Retrieves a random message (text or sticker) from the database for reply.
    Prioritizes text messages with specific word counts, then falls back to stickers.
    """
    query = {"$or": [{"message_text": {"$exists": True, "$ne": None, "$ne": ""}}, {"sticker_file_id": {"$exists": True, "$ne": None}}]}
    if chat_id:
        query["chat_id"] = chat_id
    
    # Try to find a text message with an allowed word count first
    
    # Randomly pick a target word count for this reply attempt
    target_word_count = random.choice(ALLOWED_REPLY_WORD_COUNTS)
    
    text_query = {**query, "message_text": {"$exists": True, "$ne": None, "$ne": ""}, "word_count": target_word_count}
    
    total_text_messages = await chats_collection.count_documents(text_query)
    if total_text_messages > 0:
        random_index = random.randint(0, total_text_messages - 1)
        random_text_doc = await chats_collection.find(text_query).skip(random_index).limit(1).to_list(1)
        if random_text_doc:
            logger.debug(f"Found text reply with {target_word_count} words.")
            return random_text_doc[0]

    # If no text message with the exact word count is found, try to find any sticker
    sticker_query = {**query, "sticker_file_id": {"$exists": True, "$ne": None}}
    total_stickers = await chats_collection.count_documents(sticker_query)
    if total_stickers > 0:
        random_index = random.randint(0, total_stickers - 1)
        random_sticker_doc = await chats_collection.find(sticker_query).skip(random_index).limit(1).to_list(1)
        if random_sticker_doc:
            logger.debug("Found sticker reply as fallback.")
            return random_sticker_doc[0]
            
    logger.debug("No suitable reply found (text or sticker).")
    return None # No text or sticker found

async def add_user_to_db(user_id, username, first_name):
    """Adds or updates user info for broadcast."""
    try:
        await users_collection.update_one(
            {"_id": user_id},
            {"$set": {
                "username": username,
                "first_name": first_name,
                "last_active": datetime.datetime.now()
            }},
            upsert=True
        )
    except Exception as e:
        logger.error(f"Error adding user to DB: {e}")

# --- Bot Commands ---
@bot.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    await add_user_to_db(message.from_user.id, message.from_user.username, message.from_user.first_name)
    await message.reply_text(
        "👋 हाय! मैं तुम्हारी दोस्त हूँ, जो ग्रुप्स से सीखती है और तुमसे बात करती है. "
        "मैं अभी सीख रही हूँ, इसलिए थोड़ी-थोड़ी गलतियाँ होंगी! 😊\n\n"
        "मेरे बारे में और जानने के लिए /help टाइप करो.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📚 मदद", callback_data="help_menu")],
            [InlineKeyboardButton("मेन चैनल", url=TELEGRAM_MAIN_CHANNEL)],
            [InlineKeyboardButton("चैट ग्रुप", url=TELEGRAM_CHAT_GROUP)],
            [InlineKeyboardButton("मूवी डाउनलोड ग्रुप", url=TELEGRAM_MOVIE_GROUP)]
        ])
    )

@bot.on_message(filters.command("help") & filters.private)
async def help_command(client, message):
    await message.reply_text(
        "💡 **मैं कैसे काम करती हूँ?**\n\n"
        "मैं ग्रुप चैट्स में लोगों की बातों को ध्यान से सुनती हूँ और उन्हें याद रखती हूँ. "
        "कभी-कभी मैं उन्हीं बातों का इस्तेमाल करके जवाब दूंगी या कोई प्यारा स्टिकर भेजूंगी.\n\n"
        "📚 **सीखना:** मैं आपके ग्रुप्स से सीख रही हूँ!\n"
        "💬 **बातचीत:** मैं सीखे हुए शब्दों और स्टिकर्स का इस्तेमाल करूंगी.\n\n"
        "मेरे एडमिन: @आपके_एडमिन_का_यूज़रनेम",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 वापस", callback_data="start_menu")]
        ])
    )

@bot.on_message(filters.command("broadcast") & filters.user(ADMIN_ID))
async def broadcast_command(client, message):
    if not message.reply_to_message:
        await message.reply_text("कृपया उस मैसेज को रिप्लाई करें जिसे आप ब्रॉडकास्ट करना चाहते हैं।")
        return

    broadcast_message = message.reply_to_message
    total_users = await users_collection.count_documents({})
    sent_count = 0
    failed_count = 0

    await message.reply_text(f"ब्रॉडकास्ट शुरू हो रहा है... कुल {total_users} उपयोगकर्ताओं को भेजा जाएगा।")

    async for user_doc in users_collection.find({}):
        try:
            await broadcast_message.copy(user_doc["_id"])
            sent_count += 1
            await asyncio.sleep(0.1)
        except Exception as e:
            failed_count += 1
            logger.error(f"Failed to send broadcast to {user_doc.get('username', user_doc['_id'])}: {e}")
            if "USER_IS_BLOCKED" in str(e) or "PEER_ID_INVALID" in str(e):
                await users_collection.delete_one({"_id": user_doc["_id"]})
                logger.info(f"Removed blocked user {user_doc['_id']} from DB.")

    await message.reply_text(
        f"ब्रॉडकास्ट पूरा हुआ!\n"
        f"✅ भेजा गया: {sent_count}\n"
        f"❌ विफल: {failed_count}"
    )

# --- Delayed Reply Handler ---
async def send_delayed_reply(chat_id):
    async with chat_reply_locks[chat_id]:
        chat_reply_pending[chat_id] = False 
        
        await asyncio.sleep(REPLY_DELAY_SECONDS)
        
        if chat_message_buffers[chat_id]:
            chat_message_buffers[chat_id].clear() 
            
            if random.random() < REPLY_PROBABILITY:
                random_reply = await get_random_message_for_reply(chat_id=chat_id)
                if random_reply:
                    try:
                        if random_reply.get("message_text"):
                            await bot.send_message(chat_id, random_reply["message_text"])
                            logger.info(f"Bot replied to chat {chat_id} with text: '{random_reply['message_text']}'")
                        elif random_reply.get("sticker_file_id"):
                            await bot.send_sticker(chat_id, random_reply["sticker_file_id"])
                            logger.info(f"Bot replied to chat {chat_id} with sticker.")
                    except Exception as e:
                        logger.error(f"Error sending random delayed reply in chat {chat_id}: {e}")
                else:
                    logger.info(f"No suitable text or sticker found for reply in chat {chat_id}.")
            else:
                logger.info(f"Bot decided NOT to reply in chat {chat_id} (probability check).")
        else:
            logger.info(f"No new messages in buffer for chat {chat_id} after delay.")


# --- Message Handlers for Learning and Triggering Delayed Replies ---
# CORRECTED LINE: Removed ~filters.edited and ~filters.via_bot
@bot.on_message(filters.group & (filters.text | filters.sticker))
async def group_message_handler(client, message):
    if message.from_user.id == client.me.id:
        return

    chat_id = message.chat.id

    # Store message for learning
    if message.text and not message.text.startswith('/'):
        await save_message_for_learning(chat_id, message.from_user.id, message_text=message.text)
    elif message.sticker:
        await save_message_for_learning(chat_id, message.from_user.id, sticker_file_id=message.sticker.file_id)

    chat_message_buffers[chat_id].append(message)

    if not chat_reply_pending[chat_id]:
        chat_reply_pending[chat_id] = True
        asyncio.create_task(send_delayed_reply(chat_id))
        logger.debug(f"Started delayed reply task for chat {chat_id}.")


# --- Callback Query Handler ---
@bot.on_callback_query()
async def callback_handler(client, callback_query):
    query = callback_query.data
    
    if query == "help_menu":
        await callback_query.message.edit_text(
            "💡 **मैं कैसे काम करती हूँ?**\n\n"
            "मैं ग्रुप चैट्स में लोगों की बातों को ध्यान से सुनती हूँ और उन्हें याद रखती हूँ. "
            "कभी-कभी मैं उन्हीं बातों का इस्तेमाल करके जवाब दूंगी या कोई प्यारा स्टिकर भेजूंगी.\n\n"
            "📚 **सीखना:** मैं आपके ग्रुप्स से सीख रही हूँ!\n"
            "💬 **बातचीत:** मैं सीखे हुए शब्दों और स्टिकर्स का इस्तेमाल करूंगी.\n\n"
            "मेरे एडमिन: @आपके_एडमिन_का_यूज़रनेम",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 वापस", callback_data="start_menu")]
            ])
        )
    elif query == "start_menu":
        await callback_query.message.edit_text(
            "👋 हाय! मैं तुम्हारी दोस्त हूँ, जो ग्रुप्स से सीखती है और तुमसे बात करती है. "
            "मैं अभी सीख रही हूँ, इसलिए थोड़ी-थोड़ी गलतियाँ होंगी! 😊\n\n"
            "मेरे बारे में और जानने के लिए /help टाइप करो.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📚 मदद", callback_data="help_menu")],
                [InlineKeyboardButton("मेन चैनल", url=TELEGRAM_MAIN_CHANNEL)],
                [InlineKeyboardButton("चैट ग्रुप", url=TELEGRAM_CHAT_GROUP)],
                [InlineKeyboardButton("मूवी डाउनलोड ग्रुप", url=TELEGRAM_MOVIE_GROUP)]
            ])
        )
    await callback_query.answer()

# --- Simple Health Check for Koyeb ---
async def health_check_ping():
    while True:
        logger.debug("Health check ping: Bot is active.")
        await asyncio.sleep(30) # Ping every 30 seconds to keep Koyeb happy.

# --- Main function to run the Bot ---
async def main():
    logger.info("Starting bot...")
    await bot.start()
    logger.info("Bot started! Waiting for messages...")

    # Start the simple health check task in the background
    asyncio.create_task(health_check_ping())
    logger.info("Health check ping task started.")

    await idle() # Keep the bot running indefinitely

    await bot.stop()
    logger.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())
