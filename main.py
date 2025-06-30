from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient
import random

# ==== CONFIGURATION ====
API_ID = 29970536            # 🔁 Replace with your API ID
API_HASH = "f4bfdcdd4a5c1b7328a7e4f25f024a09"
BOT_TOKEN = "7467073514:AAFQ3vCZXTdee9McGkgvgZky70GsDjahcAA"
OWNER_ID = 7315805581       # 🔁 Replace with your Telegram user ID
MONGO_URL = "mongodb+srv://xonide3955:U9C9hrp7yABlbUeq@cluster0.nscd3zg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# ==== INIT ====
app = Client("self_learning_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
client = MongoClient(MONGO_URL)
db = client["self_learning_bot"]
collection = db["memory"]

# ==== AUTO CLEAN MONGO ====
def auto_clean_mongo():
    max_docs = 100000
    total_docs = collection.count_documents({})
    if total_docs > max_docs:
        delete_count = int(total_docs * 0.2)
        old_docs = collection.find().sort("_id", 1).limit(delete_count)
        ids_to_delete = [doc["_id"] for doc in old_docs]
        collection.delete_many({"_id": {"$in": ids_to_delete}})

auto_clean_mongo()

# ==== /START COMMAND ====
@app.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message: Message):
    buttons = [
        [InlineKeyboardButton("➕ Add to Group", url=f"https://t.me/{client.me.username}?startgroup=true")],
        [
            InlineKeyboardButton("📢 Update Channel", url="https://t.me/asbhai_bsr"),
            InlineKeyboardButton("💬 Chat Group", url="https://t.me/aschat_group"),
        ],
        [InlineKeyboardButton("🎬 Movie Group", url="https://t.me/istreamX")]
    ]
    await message.reply_text(
        f"👋 Hello {message.from_user.first_name}!\n\n"
        "I'm a self-learning bot 🤖. I remember what people say and reuse that to reply — in all chats!",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# ==== /BROADCAST COMMAND ====
@app.on_message(filters.command("broadcast") & filters.user(OWNER_ID))
async def broadcast_cmd(client, message: Message):
    if len(message.command) < 2:
        return await message.reply("Usage: /broadcast <message>")
    msg = message.text.split(" ", 1)[1]
    chat_ids = collection.distinct("chat_id")
    sent = 0
    for cid in chat_ids:
        try:
            await client.send_message(int(cid), msg)
            sent += 1
        except:
            continue
    await message.reply(f"✅ Broadcast sent to {sent} chats.")

# ==== SELF-LEARNING REPLY ====
@app.on_message(filters.text | filters.sticker)
async def handle_chat(client, message: Message):
    chat_id = message.chat.id
    user_msg = message.text if message.text else f"sticker:{message.sticker.file_unique_id}"

    # Try to reply
    all_docs = list(collection.find({"q": user_msg, "a": {"$ne": None}}))
    if all_docs:
        response = random.choice(all_docs)["a"]
        if response.startswith("sticker:"):
            await message.reply_sticker(response.replace("sticker:", ""))
        else:
            await message.reply(response)

    # Save to memory
    entry = {"chat_id": str(chat_id), "q": user_msg, "a": None}
    if message.reply_to_message:
        if message.reply_to_message.text:
            entry["a"] = message.reply_to_message.text
        elif message.reply_to_message.sticker:
            entry["a"] = f"sticker:{message.reply_to_message.sticker.file_unique_id}"
    collection.insert_one(entry)

# ==== RUN ====
print("🤖 Bot is running...")
app.run()
