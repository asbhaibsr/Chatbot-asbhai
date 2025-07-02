from pyrogram import Client, filters
from pyrogram.types import *
from pymongo import MongoClient
import requests
import random
import os

# Logging and Asyncio for debugging
import asyncio
import logging # <-- यह नई लाइन जोड़ी गई है
from pyrogram.enums import ChatAction

from aiohttp import web # <-- यह नई लाइन जोड़ी गई है (वेब सर्वर के लिए)

# Logging setup for debugging (यह अस्थायी है, समस्या हल होने पर हटा दें)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# एक्सेप्शन हैंडलर जोड़ें
def handle_exception(loop, context):
    msg = context.get("exception", context["message"])
    logger.error(f"Caught unhandled exception: {msg}")
    # यहां आप traceback को और अधिक विस्तृत रूप से लॉग कर सकते हैं यदि आवश्यक हो
    if "exception" in context:
        logger.error("Traceback:", exc_info=context["exception"])

loop = asyncio.get_event_loop()
loop.set_exception_handler(handle_exception)

API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
STRING = os.environ.get("STRING")
MONGO_URL = os.environ.get("MONGO_URL")

# Pyrogram को सेशन स्ट्रिंग को सीधे फाइल नाम के रूप में उपयोग करने से रोकने के लिए
# 'name' पैरामीटर में एक छोटा, स्थिर नाम दिया गया है, और 'session_string'
# पैरामीटर में आपकी लंबी सेशन स्ट्रिंग (जो ENVIRONMENT VARIABLE से आ रही है) पास की गई है।
bot = Client("my_koyeb_bot", API_ID, API_HASH, session_string=STRING)
# आप "my_koyeb_bot" की जगह कोई भी छोटा, वैध नाम जैसे "mybot" या "chatbot_session" दे सकते हैं।

async def is_admins(chat_id: int):
    # iter_chat_members को get_chat_members से बदला गया है
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

# हेल्थ चेक के लिए एक छोटा वेब सर्वर फंक्शन
async def health_check_route(request):
    return web.Response(text="Bot is alive!")

# Pyrogram बॉट और वेब सर्वर को एक साथ चलाने के लिए मुख्य फंक्शन
async def run_both():
    # aiohttp वेब सर्वर सेट करें
    app = web.Application()
    app.router.add_get('/', health_check_route)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080) # Koyeb के 8080 पोर्ट पर लिसन करें
    await site.start()
    logger.info("Web server started for health checks on port 8080")

    # Pyrogram बॉट को चलाएं (यह ब्लॉक होने वाला कॉल है, इसलिए इसे await करें)
    # Pyrogram का run() मेथड खुद ही asyncio इवेंट लूप को मैनेज करता है,
    # इसलिए इसे gather के साथ नहीं चलाया जा सकता अगर वह blocking हो।
    # Pyrogram 2.x के साथ, bot.run() blocking है।
    # हमें Pyrogram को अपना इवेंट लूप चलाने देना होगा, और वेब सर्वर को Pyrogram के लूप में जोड़ना होगा।
    # लेकिन bot.run() एक अलग थ्रेड में चलता है, इसलिए हमें सुनिश्चित करना होगा कि दोनों एक ही लूप में हों।

    # सरल समाधान के लिए, हम Pyrogram को अपने लूप को चलाने देंगे, और वेब सर्वर को उसके साथ इंटीग्रेट करेंगे।
    # Pyrogram 2.x के साथ bot.run() Blocking है, इसलिए हम इसे सीधे asyncio.gather() में नहीं डाल सकते।
    # इसके बजाय, हम bot.start() और bot.idle() का उपयोग करेंगे।

    logger.info("Starting Pyrogram Client...")
    await bot.start()
    logger.info("Pyrogram Client Started! Bot is ready.")
    await bot.idle() # यह बॉट को तब तक चलाता रहेगा जब तक उसे रोका न जाए

# बॉट और वेब सर्वर को शुरू करें
print("Your Chatbot Is Ready Now! Join @aschat_group")
try:
    asyncio.run(run_both()) # <-- यह main() की जगह run_both() को कॉल करेगा
except Exception as e:
    logger.error(f"An error occurred in main execution loop: {e}", exc_info=True)

