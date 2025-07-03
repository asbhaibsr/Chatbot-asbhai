import os
import asyncio
import logging
import random
import re
from datetime import datetime, timedelta

from pyrogram import Client, filters, idle
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.raw.functions.messages import SetTyping
from pyrogram.raw.types import SendMessageTypingAction
from pymongo import MongoClient
from aiohttp import web

# --- Logger Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Environment Variables ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_DB_URI = os.getenv("MONGO_DB_URI")
OWNER_ID = os.getenv("OWNER_ID")

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")

# --- MongoDB Setup ---
try:
    client = MongoClient(MONGO_DB_URI)
    db = client.bot_database
    messages_collection = db.messages
except Exception as e:
    logger.error(f"MongoDB connection failed: {e}")
    messages_collection = None

# --- Telegram Bot Setup ---
bot = Client(
    "asbhai_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Example /start command
@bot.on_message(filters.command("start") & filters.private)
async def start_command(c, m: Message):
    await m.reply_text("Bot is working fine!", reply_markup=InlineKeyboardMarkup(
        [[InlineKeyboardButton("Update Channel", url="https://t.me/asbhai_bsr")]]
    ))

# --- Health Check Route ---
async def healthcheck(request):
    return web.Response(text="OK", status=200)

app = web.Application()
app.router.add_get("/", healthcheck)

# --- Start bot and health server ---
async def start_services():
    await bot.start()
    logger.info("Bot started")
    await idle()
    await bot.stop()
    logger.info("Bot stopped")

loop = asyncio.get_event_loop()
loop.create_task(start_services())
web.run_app(app, port=8080)
