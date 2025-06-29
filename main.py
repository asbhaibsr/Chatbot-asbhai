# main.py

import os
import asyncio
import logging
import random
import re
import datetime
from collections import defaultdict
from pyrogram import Client, filters, idle
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from motor.motor_asyncio import AsyncIOMotorClient

# -------------------- Logging --------------------
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# -------------------- Environment Variables --------------------
API_ID = int(os.environ.get("API_ID", "123456"))
API_HASH = os.environ.get("API_HASH", "your_api_hash")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "your_bot_token")
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "123456789"))

# -------------------- Configuration --------------------
REPLY_DELAY_SECONDS = 3
REPLY_PROBABILITY = 0.15
MAX_LEARNING_MESSAGES = 10000
CLEANUP_THRESHOLD_PERCENT = 0.50
ALLOWED_REPLY_WORD_COUNTS = [2, 3, 5, 6, 7]

# -------------------- Telegram Links --------------------
TELEGRAM_MAIN_CHANNEL = "https://t.me/asbhai_bsr"
TELEGRAM_CHAT_GROUP = "https://t.me/aschat_group"
TELEGRAM_MOVIE_GROUP = "https://t.me/istreamx"

# -------------------- Global Variables --------------------
chat_message_buffers = defaultdict(list)
chat_reply_pending = defaultdict(bool)
chat_reply_locks = defaultdict(asyncio.Lock)

# -------------------- Pyrogram Client --------------------
bot = Client("as_ki_angel_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# -------------------- MongoDB Setup --------------------
mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client.self_learning_bot
users_collection = db.users
chats_collection = db.chats

# -------------------- Learning Save Function --------------------
async def save_message(chat_id, user_id, message_text=None, sticker_file_id=None):
    if message_text:
        message_text = re.sub(r'@\w+', '', message_text)
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
            "word_count": len(message_text.split()) if message_text else 0
        })
        await cleanup_old_data()
    except Exception as e:
        logger.error(f"Save error: {e}")

async def cleanup_old_data():
    total = await chats_collection.count_documents({})
    if total > MAX_LEARNING_MESSAGES:
        delete_count = int(MAX_LEARNING_MESSAGES * CLEANUP_THRESHOLD_PERCENT)
        old_msgs = await chats_collection.find().sort("timestamp", 1).limit(delete_count).to_list(length=None)
        if old_msgs:
            ids = [msg["_id"] for msg in old_msgs]
            await chats_collection.delete_many({"_id": {"$in": ids}})

# -------------------- Random Reply Selector --------------------
async def get_random_reply(chat_id=None):
    query = {
        "$or": [{"message_text": {"$exists": True}}, {"sticker_file_id": {"$exists": True}}]
    }
    if chat_id:
        query["chat_id"] = chat_id

    word_count = random.choice(ALLOWED_REPLY_WORD_COUNTS)
    text_query = {**query, "word_count": word_count}

    total_texts = await chats_collection.count_documents(text_query)
    if total_texts:
        idx = random.randint(0, total_texts - 1)
        doc = await chats_collection.find(text_query).skip(idx).limit(1).to_list(1)
        return doc[0] if doc else None

    sticker_query = {**query, "sticker_file_id": {"$exists": True}}
    total_stickers = await chats_collection.count_documents(sticker_query)
    if total_stickers:
        idx = random.randint(0, total_stickers - 1)
        doc = await chats_collection.find(sticker_query).skip(idx).limit(1).to_list(1)
        return doc[0] if doc else None
    return None

# -------------------- Command: /start --------------------
@bot.on_message(filters.command("start") & filters.private)
async def start(_, msg):
    await users_collection.update_one(
        {"_id": msg.from_user.id},
        {"$set": {
            "username": msg.from_user.username,
            "first_name": msg.from_user.first_name,
            "last_active": datetime.datetime.now()
        }},
        upsert=True
    )
    await msg.reply_text(
        "👋 हाय! मैं तुम्हारी दोस्त हूँ, जो ग्रुप्स से सीखती है और तुमसे बात करती है. "
        "मैं अभी सीख रही हूँ, इसलिए थोड़ी गलतियाँ हो सकती हैं! 😊",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📚 मदद", callback_data="help_menu")],
            [InlineKeyboardButton("📢 मेन चैनल", url=TELEGRAM_MAIN_CHANNEL)],
            [InlineKeyboardButton("💬 चैट ग्रुप", url=TELEGRAM_CHAT_GROUP)],
            [InlineKeyboardButton("🎬 मूवी ग्रुप", url=TELEGRAM_MOVIE_GROUP)],
        ])
    )

# -------------------- Command: /help --------------------
@bot.on_message(filters.command("help") & filters.private)
async def help(_, msg):
    await msg.reply_text(
        "💡 **मैं कैसे काम करती हूँ?**\n\n"
        "मैं ग्रुप्स में लोगों की बातों को सुनकर उन्हें याद रखती हूँ और कभी-कभी जवाब देती हूँ।",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 वापस", callback_data="start_menu")]
        ])
    )

# -------------------- Broadcast (Admin Only) --------------------
@bot.on_message(filters.command("broadcast") & filters.user(ADMIN_ID))
async def broadcast(_, msg):
    if not msg.reply_to_message:
        await msg.reply_text("कृपया ब्रॉडकास्ट करने वाले मैसेज को रिप्लाई करें।")
        return

    count = 0
    async for user in users_collection.find():
        try:
            await msg.reply_to_message.copy(user["_id"])
            count += 1
        except:
            pass
    await msg.reply_text(f"✅ ब्रॉडकास्ट पूरा हुआ: {count} users")

# -------------------- Callback Button Handler --------------------
@bot.on_callback_query()
async def callback(_, cb):
    if cb.data == "help_menu":
        await cb.message.edit_text(
            "📚 मैं ग्रुप से बाते सीखती हूँ और जवाब देती हूँ।",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 वापस", callback_data="start_menu")]
            ])
        )
    elif cb.data == "start_menu":
        await cb.message.edit_text(
            "👋 हाय! मैं तुम्हारी दोस्त हूँ, जो ग्रुप्स से सीखती है और तुमसे बात करती है.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📚 मदद", callback_data="help_menu")],
                [InlineKeyboardButton("📢 मेन चैनल", url=TELEGRAM_MAIN_CHANNEL)],
                [InlineKeyboardButton("💬 चैट ग्रुप", url=TELEGRAM_CHAT_GROUP)],
                [InlineKeyboardButton("🎬 मूवी ग्रुप", url=TELEGRAM_MOVIE_GROUP)],
            ])
        )
    await cb.answer()

# -------------------- Group Message Listener --------------------
@bot.on_message(filters.group & (filters.text | filters.sticker))
async def group_listener(_, msg):
    if msg.from_user and msg.from_user.is_bot:
        return
    if msg.text and not msg.text.startswith("/"):
        await save_message(msg.chat.id, msg.from_user.id, msg.text)
    elif msg.sticker:
        await save_message(msg.chat.id, msg.from_user.id, sticker_file_id=msg.sticker.file_id)

    chat_id = msg.chat.id
    chat_message_buffers[chat_id].append(msg)

    if not chat_reply_pending[chat_id]:
        chat_reply_pending[chat_id] = True
        asyncio.create_task(delayed_reply(chat_id))

# -------------------- Delayed Random Reply --------------------
async def delayed_reply(chat_id):
    async with chat_reply_locks[chat_id]:
        await asyncio.sleep(REPLY_DELAY_SECONDS)
        chat_reply_pending[chat_id] = False
        if random.random() < REPLY_PROBABILITY:
            reply = await get_random_reply(chat_id)
            if reply:
                try:
                    if reply.get("message_text"):
                        await bot.send_message(chat_id, reply["message_text"])
                    elif reply.get("sticker_file_id"):
                        await bot.send_sticker(chat_id, reply["sticker_file_id"])
                except Exception as e:
                    logger.error(f"Reply failed: {e}")
        chat_message_buffers[chat_id].clear()

# -------------------- Health Ping --------------------
async def health_check():
    while True:
        logger.info("✅ Health check ping - Bot is alive.")
        await asyncio.sleep(30)

# -------------------- Main --------------------
async def main():
    await bot.start()
    logger.info("🤖 Bot started!")
    asyncio.create_task(health_check())
    await idle()

if __name__ == "__main__":
    asyncio.run(main())
