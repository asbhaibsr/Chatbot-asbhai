import asyncio
from pyrogram import Client, filters, types
from pymongo import MongoClient
from random import choice
from bson.objectid import ObjectId
import os

# ---------------- CONFIG ----------------
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
MONGO_URL = os.environ.get("MONGO_URL")
OWNER_ID = int(os.environ.get("OWNER_ID", 123456789))  # your telegram id

bot = Client("selflearn-bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
mongo = MongoClient(MONGO_URL)
db = mongo["chatdb"]
chats = db["messages"]

MAX_LIMIT = 5000  # Max messages before cleaning

# --------------- CLEANER ----------------
async def auto_clean():
    while True:
        total = chats.count_documents({})
        if total >= MAX_LIMIT:
            to_delete = int(total * 0.2)
            old_docs = chats.find().sort("_id", 1).limit(to_delete)
            for doc in old_docs:
                chats.delete_one({"_id": ObjectId(doc["_id"])})
        await asyncio.sleep(3600)

# --------------- /START ----------------
@bot.on_message(filters.command("start"))
async def start_handler(c, m):
    await m.reply(
        f"👋 Hello {m.from_user.first_name}!\n\n"
        "I'm a self-learning chat bot. Talk to me and I’ll learn from you!",
        reply_markup=types.InlineKeyboardMarkup(
            [
                [types.InlineKeyboardButton("➕ Add Me To Group", url=f"https://t.me/{c.me.username}?startgroup=true")],
                [
                    types.InlineKeyboardButton("📢 Update Channel", url="https://t.me/asbhai_bsr"),
                    types.InlineKeyboardButton("💬 Chat Group", url="https://t.me/aschat_group"),
                ],
                [types.InlineKeyboardButton("🎬 Movie Group", url="https://t.me/istreamX")],
            ]
        )
    )

# ------------- /BROADCAST ---------------
@bot.on_message(filters.command("broadcast") & filters.user(OWNER_ID))
async def broadcast(c, m):
    if not m.reply_to_message:
        return await m.reply("Reply to a message to broadcast.")
    success = fail = 0
    async for user in db["users"].find({}, {"_id": 0, "chat_id": 1}):
        try:
            await m.reply_to_message.copy(chat_id=user["chat_id"])
            success += 1
        except:
            fail += 1
    await m.reply(f"✅ Sent: {success}\n❌ Failed: {fail}")

# ----------- LEARN & REPLY --------------
@bot.on_message(filters.text | filters.sticker)
async def learn_and_reply(c, m):
    if m.from_user.is_bot: return

    # Store chat for learning
    chats.insert_one({
        "chat_id": m.chat.id,
        "user_id": m.from_user.id,
        "type": m.media if m.sticker else "text",
        "text": m.text or "",
        "sticker": m.sticker.file_id if m.sticker else None,
    })

    # Save user chat ID for broadcast
    db["users"].update_one({"chat_id": m.chat.id}, {"$set": {"chat_id": m.chat.id}}, upsert=True)

    # Random reply from database
    random_doc = chats.aggregate([{"$sample": {"size": 1}}])
    for doc in random_doc:
        if doc.get("text"):
            await m.reply(doc["text"])
        elif doc.get("sticker"):
            await m.reply_sticker(doc["sticker"])

# ---------- RUN BOT + CLEAN TASK --------
async def main():
    await bot.start()
    print("🤖 Bot is running...")
    await auto_clean()

if __name__ == "__main__":
    asyncio.run(main())
