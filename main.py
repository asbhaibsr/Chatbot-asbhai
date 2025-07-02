from pyrogram import Client, filters
from pyrogram.types import *
from pymongo import MongoClient
import requests
import random
import os

import asyncio
import logging # Logging को वापस सक्रिय रखें, यह debugging के लिए महत्वपूर्ण है
from pyrogram.enums import ChatAction

from aiohttp import web # यह वेब सर्वर के लिए रखना है

# Logging setup for debugging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# एक्सेप्शन हैंडलर (इसे रखें)
def handle_exception(loop, context):
    msg = context.get("exception", context["message"])
    logger.error(f"Caught unhandled exception: {msg}")
    if "exception" in context:
        logger.error("Traceback:", exc_info=context["exception"])

loop = asyncio.get_event_loop()
loop.set_exception_handler(handle_exception)

API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
STRING = os.environ.get("STRING")
MONGO_URL = os.environ.get("MONGO_URL")

bot = Client("my_koyeb_bot", API_ID, API_HASH, session_string=STRING)

async def is_admins(chat_id: int):
    return [member.user.id async for member in bot.get_chat_members(chat_id, filter="administrators")]

@bot.on_message(filters.command("start"))
async def start(client, message):
    await bot.join_chat("@aschat_group")

@bot.on_message(filters.command("chatbot off", prefixes=["/", ".", "?", "-"]) & ~filters.private)
async def chatbotofd(client, message):
    vickdb = MongoClient(MONGO_URL)
    vick = vickdb["VickDb"]["Vick"]
    if message.from_user:
        user = message.from_user.id
        chat_id = message.chat.id
        if user not in await is_admins(chat_id):
            return await message.reply_text("You are not admin")
    is_vick = vick.find_one({"chat_id": message.chat.id})
    if not is_vick:
        vick.insert_one({"chat_id": message.chat.id})
        await message.reply_text("Chatbot Disabled!")
    else:
        await message.reply_text("ChatBot Is Already Disabled")

@bot.on_message(filters.command("chatbot on", prefixes=["/", ".", "?", "-"]) & ~filters.private)
async def chatboton(client, message):
    vickdb = MongoClient(MONGO_URL)
    vick = vickdb["VickDb"]["Vick"]
    if message.from_user:
        user = message.from_user.id
        chat_id = message.chat.id
        if user not in await is_admins(chat_id):
            return await message.reply_text("You are not admin")
    is_vick = vick.find_one({"chat_id": message.chat.id})
    if not is_vick:
        await message.reply_text("Chatbot Is Already Enabled")
    else:
        vick.delete_one({"chat_id": message.chat.id})
        await message.reply_text("ChatBot Is Enable!")

@bot.on_message(filters.command("chatbot", prefixes=["/", ".", "?", "-"]) & ~filters.private)
async def chatbot(client, message):
    await message.reply_text("**Usage:**\n/chatbot [on|off] only group")

@bot.on_message((filters.text | filters.sticker) & ~filters.private & ~filters.bot)
async def vickai(client: Client, message: Message):
    chatdb = MongoClient(MONGO_URL)
    chatai = chatdb["Word"]["WordDb"]
    vickdb = MongoClient(MONGO_URL)
    vick = vickdb["VickDb"]["Vick"]
    is_vick = vick.find_one({"chat_id": message.chat.id})

    if not message.reply_to_message:
        if not is_vick:
            await bot.send_chat_action(message.chat.id, ChatAction.TYPING)
            K = [x['text'] for x in chatai.find({"word": message.text})]
            if K:
                hey = random.choice(K)
                is_text = chatai.find_one({"text": hey})
                await (message.reply_sticker(hey) if is_text['check'] == "sticker" else message.reply_text(hey))
    else:
        getme = await bot.get_me()
        if message.reply_to_message.from_user.id == getme.id:
            if not is_vick:
                await bot.send_chat_action(message.chat.id, ChatAction.TYPING)
                K = [x['text'] for x in chatai.find({"word": message.text})]
                if K:
                    hey = random.choice(K)
                    is_text = chatai.find_one({"text": hey})
                    await (message.reply_sticker(hey) if is_text['check'] == "sticker" else message.reply_text(hey))
        else:
            if message.sticker:
                chatai.update_one({"word": message.reply_to_message.text, "id": message.sticker.file_unique_id}, {"$setOnInsert": {"text": message.sticker.file_id, "check": "sticker", "id": message.sticker.file_unique_id}}, upsert=True)
            elif message.text:
                chatai.update_one({"word": message.reply_to_message.text, "text": message.text}, {"$setOnInsert": {"check": "none"}}, upsert=True)

@bot.on_message((filters.text | filters.sticker) & filters.private & ~filters.bot)
async def vickprivate(client: Client, message: Message):
    chatdb = MongoClient(MONGO_URL)
    chatai = chatdb["Word"]["WordDb"]
    await bot.send_chat_action(message.chat.id, ChatAction.TYPING)

    if not message.reply_to_message:
        K = [x['text'] for x in chatai.find({"word": message.text})]
        if K:
            hey = random.choice(K)
            is_text = chatai.find_one({"text": hey})
            await (message.reply_sticker(hey) if is_text['check'] == "sticker" else message.reply_text(hey))
    else:
        getme = await bot.get_me()
        if message.reply_to_message.from_user.id == getme.id:
            K = [x['text'] for x in chatai.find({"word": message.text})]
            if K:
                hey = random.choice(K)
                is_text = chatai.find_one({"text": hey})
                await (message.reply_sticker(hey) if is_text['check'] == "sticker" else message.reply_text(hey))

# हेल्थ चेक के लिए वेब सर्वर
async def health_check_route(request):
    return web.Response(text="Bot is alive!")

# मुख्य रनर जो वेब सर्वर और बॉट दोनों को शुरू करता है
async def main_startup():
    # aiohttp वेब सर्वर सेट करें
    app = web.Application()
    app.router.add_get('/', health_check_route)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080) # Koyeb के 8080 पोर्ट पर लिसन करें
    await site.start()
    logger.info("Web server started for health checks on port 8080")

    # Pyrogram क्लाइंट शुरू करें
    logger.info("Starting Pyrogram Client...")
    await bot.start()
    logger.info("Pyrogram Client Started! Bot is ready.")

    # दोनों को एक साथ चलने दें
    try:
        # Pyrogram को अनिश्चित काल तक चलाने के लिए एक Future बनाएं
        # और aiohttp वेब सर्वर को पृष्ठभूमि में चलते रहने दें
        # bot.idle() Pyrogram 2.x में काम नहीं करता है, इसलिए हम asyncio.Future() का उपयोग करते हैं
        await asyncio.Future() # यह इस टास्क को तब तक चालू रखेगा जब तक इसे Cancelled न किया जाए
    except asyncio.CancelledError:
        logger.info("Main loop cancelled (expected during shutdown).")
    finally:
        # एप्लिकेशन बंद होने पर दोनों को ठीक से बंद करें
        logger.info("Shutting down Pyrogram client...")
        await bot.stop()
        logger.info("Pyrogram client stopped.")
        
        logger.info("Shutting down web server...")
        await runner.cleanup()
        logger.info("Web server shut down.")

# बॉट और वेब सर्वर को शुरू करें
if __name__ == "__main__":
    print("Your Chatbot Is Ready Now! Join @aschat_group")
    try:
        asyncio.run(main_startup()) # main_startup को asyncio.run() के अंदर चलाएं
    except Exception as e:
        logger.error(f"An error occurred in main execution loop: {e}", exc_info=True)

