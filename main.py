from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient
import random
import os

API_ID = 12345678  # Replace with your API ID
API_HASH = "your_api_hash"  # Replace with your API HASH
BOT_TOKEN = "your_bot_token"  # Replace with your bot token
MONGO_URI = "your_mongo_uri"  # Replace with your Mongo URI

app = Client("self_learning_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
mongo = MongoClient(MONGO_URI)
db = mongo["chatbot"]
collection = db["memory"]

@app.on_message(filters.command("start"))
async def start(client, message: Message):
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("➕ Add to Group", url=f"https://t.me/{client.me.username}?startgroup=true")],
            [InlineKeyboardButton("📢 Update Channel", url="https://t.me/asbhai_bsr")],
            [InlineKeyboardButton("💬 Chat Group", url="https://t.me/aschat_group")],
            [InlineKeyboardButton("🎬 Movie Group", url="https://t.me/istreamX")]
        ]
    )
    await message.reply(
        f"👋 Hello {message.from_user.first_name}!\n\nI'm a self-learning bot 🤖. Just talk to me or reply to me, and I'll learn from you.",
        reply_markup=keyboard
    )

@app.on_message(filters.text | filters.sticker)
async def handle_chat(client, message: Message):
    try:
        chat_id = str(message.chat.id)
        user_msg = message.text if message.text else f"sticker:{message.sticker.file_unique_id}"

        # Check for saved replies
        all_docs = list(collection.find({"q": user_msg, "a": {"$ne": None}}))
        if all_docs:
            response = random.choice(all_docs)["a"]
            if response.startswith("sticker:"):
                await message.reply_sticker(response.replace("sticker:", ""))
            else:
                await message.reply(response)

        # Save new learning
        entry = {"chat_id": chat_id, "q": user_msg, "a": None}
        if message.reply_to_message:
            if message.reply_to_message.text:
                entry["a"] = message.reply_to_message.text
            elif message.reply_to_message.sticker:
                entry["a"] = f"sticker:{message.reply_to_message.sticker.file_unique_id}"
        collection.insert_one(entry)
    except Exception as e:
        print("❌ Chat error:", e)

@app.on_message(filters.command("broadcast") & filters.private)
async def broadcast(client, message: Message):
    if str(message.from_user.id) != "your_telegram_id":
        return
    msg = message.text.split(" ", 1)
    if len(msg) < 2:
        await message.reply("❌ Use: /broadcast YourMessage")
        return
    text = msg[1]
    users = collection.distinct("chat_id")
    for uid in users:
        try:
            await client.send_message(int(uid), text)
        except:
            pass
    await message.reply("✅ Broadcast done!")

print("🤖 Bot is running...")
app.run()
