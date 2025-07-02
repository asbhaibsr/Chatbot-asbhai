from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, Chat
from pymongo import MongoClient
import requests
import random
import os
from pyrogram.enums import ChatAction, ChatType

import asyncio
import logging
from aiohttp import web

# Logging setup for debugging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# एक्सेप्शन हैंडलर जोड़ें
def handle_exception(loop, context):
    msg = context.get("exception", context["message"])
    logger.error(f"Caught unhandled exception: {msg}")
    if "exception" in context:
        logger.error("Traceback:", exc_info=context["exception"])

# पर्यावरण चर (Environment Variables)
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
MONGO_URL = os.environ.get("MONGO_URL")
OWNER_ID = int(os.environ.get("OWNER_ID"))

# Pyrogram क्लाइंट को बॉट टोकन के साथ इनिशियलाइज़ करें
bot = Client("my_koyeb_bot", API_ID, API_HASH, bot_token=BOT_TOKEN)

# MongoDB क्लाइंट
mongo_client = MongoClient(MONGO_URL)
chat_db = mongo_client["Word"]["WordDb"] # AI सीखने के लिए
vick_db = mongo_client["VickDb"]["Vick"] # chatbot on/off स्थिति के लिए
user_chats_db = mongo_client["ChatbotDB"]["UserChats"] # ब्रॉडकास्ट के लिए

# मालिक के लिए फिल्टर
def is_owner_filter(_, __, message: Message):
    return message.from_user and message.from_user.id == OWNER_ID

owner_filter = filters.create(is_owner_filter)

# is_admins फंक्शन (अभी भी रखा गया है लेकिन कमांड में उपयोग नहीं किया गया)
async def is_admins(chat_id: int):
    try:
        return [member.user.id async for member in bot.get_chat_members(chat_id, filter="administrators")]
    except Exception as e:
        logger.error(f"Error getting chat members for {chat_id}: {e}", exc_info=True)
        return []

@bot.on_message(filters.command("start"))
async def start(client, message):
    # बॉट शुरू होने पर ग्रुप या यूजर ID को डेटाबेस में स्टोर करें (ब्रॉडकास्ट के लिए)
    chat_id = message.chat.id
    chat_type = message.chat.type

    # सुनिश्चित करें कि डुप्लिकेट्स स्टोर न हों
    existing_chat = user_chats_db.find_one({"chat_id": chat_id})
    if not existing_chat:
        user_chats_db.insert_one({"chat_id": chat_id, "chat_type": chat_type.value})
        logger.info(f"New chat added for broadcast: {chat_id} ({chat_type.value})")
    
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("📚 बॉट जानकारी", callback_data="bot_info"),
                InlineKeyboardButton("💡 AI सेटिंग्स", callback_data="ai_settings")
            ],
            [
                InlineKeyboardButton("🔗 हमारा ग्रुप", url="https://t.me/aschat_group")
            ]
        ]
    )
    await message.reply_text(
        "नमस्ते! मैं आपका उन्नत चैटबॉट हूँ। मैं यहाँ आपके प्रश्नों का उत्तर देने और आपके साथ बातचीत करने के लिए हूँ।\n\nनीचे दिए गए बटनों का उपयोग करें:",
        reply_markup=keyboard
    )

@bot.on_callback_query()
async def callback_handler(client, callback_query):
    data = callback_query.data
    user_id = callback_query.from_user.id
    chat_id = callback_query.message.chat.id

    if data == "ai_settings" and user_id != OWNER_ID:
        await callback_query.answer("क्षमा करें, केवल मालिक ही AI सेटिंग्स बदल सकते हैं।", show_alert=True)
        return

    await callback_query.answer() # कॉल बैक को तुरंत जवाब दें

    if data == "bot_info":
        await callback_query.message.edit_text(
            "मैं एक Pyrogram बॉट हूँ जिसे Google Gemini द्वारा बनाया गया है। मैं आपके साथ ग्रुप और निजी चैट दोनों में बातचीत कर सकता हूँ।",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 वापस", callback_data="back_to_start")]]
            )
        )
    elif data == "ai_settings":
        # AI सेटिंग्स के लिए सब-मेनू
        ai_settings_keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("चैटबॉट चालू करें", callback_data="ai_on"),
                    InlineKeyboardButton("चैटबॉट बंद करें", callback_data="ai_off")
                ],
                [
                    InlineKeyboardButton("🔙 वापस", callback_data="back_to_start")
                ]
            ]
        )
        await callback_query.message.edit_text(
            "AI सेटिंग्स मेनू:",
            reply_markup=ai_settings_keyboard
        )
    elif data == "ai_on":
        is_vick = vick_db.find_one({"chat_id": chat_id})
        if is_vick:
            vick_db.delete_one({"chat_id": chat_id})
            await callback_query.message.edit_text("चैटबॉट अब इस चैट में चालू है! 🎉")
        else:
            await callback_query.message.edit_text("चैटबॉट पहले से ही चालू है।")
    elif data == "ai_off":
        is_vick = vick_db.find_one({"chat_id": chat_id})
        if not is_vick:
            vick_db.insert_one({"chat_id": chat_id})
            await callback_query.message.edit_text("चैटबॉट अब इस चैट में बंद है। 🔇")
        else:
            await callback_query.message.edit_text("चैटबॉट पहले से ही बंद है।")
    elif data == "back_to_start":
        # /start कमांड से कीबोर्ड को फिर से दिखाएं
        await start(client, callback_query.message)
        
# ब्रॉडकास्ट कमांड (केवल मालिक के लिए)
@bot.on_message(filters.command("broadcast") & owner_filter)
async def broadcast_message(client, message):
    if not message.reply_to_message:
        await message.reply_text("कृपया उस मैसेज का रिप्लाई करें जिसे आप ब्रॉडकास्ट करना चाहते हैं।")
        return

    broadcast_msg = message.reply_to_message
    
    total_chats = user_chats_db.count_documents({})
    success_count = 0
    fail_count = 0

    await message.reply_text(f"ब्रॉडकास्टिंग शुरू हो रही है... कुल {total_chats} चैट।")

    for chat_data in user_chats_db.find({}):
        chat_id = chat_data["chat_id"]
        try:
            # मैसेज के प्रकार के आधार पर भेजें (टेक्स्ट, फोटो, स्टिकर, आदि)
            if broadcast_msg.text:
                await client.send_message(chat_id, broadcast_msg.text)
            elif broadcast_msg.photo:
                await client.send_photo(chat_id, broadcast_msg.photo.file_id, caption=broadcast_msg.caption)
            elif broadcast_msg.sticker:
                await client.send_sticker(chat_id, broadcast_msg.sticker.file_id)
            elif broadcast_msg.animation: # GIF के लिए
                await client.send_animation(chat_id, broadcast_msg.animation.file_id, caption=broadcast_msg.caption)
            elif broadcast_msg.video:
                await client.send_video(chat_id, broadcast_msg.video.file_id, caption=broadcast_msg.caption)
            elif broadcast_msg.document:
                await client.send_document(chat_id, broadcast_msg.document.file_id, caption=broadcast_msg.caption)
            else:
                logger.warning(f"Unsupported message type for broadcast from chat {message.chat.id}: {broadcast_msg.media}")
                fail_count += 1
                continue
            success_count += 1
            await asyncio.sleep(0.1) # Flood wait से बचने के लिए छोटा सा डिले
        except Exception as e:
            logger.error(f"Failed to send broadcast to chat {chat_id}: {e}", exc_info=True)
            fail_count += 1
            await asyncio.sleep(0.5) # एरर पर थोड़ा ज़्यादा डिले

    await message.reply_text(f"ब्रॉडकास्ट पूरा हुआ!\nसफलतापूर्वक भेजा: {success_count}\nभेजने में विफल: {fail_count}")


@bot.on_message((filters.text | filters.sticker) & ~filters.private & ~filters.bot)
async def vickai(client: Client, message: Message):
    # बॉट शुरू होने पर ग्रुप या यूजर ID को डेटाबेस में स्टोर करें (ब्रॉडकास्ट के लिए)
    chat_id = message.chat.id
    chat_type = message.chat.type

    # सुनिश्चित करें कि डुप्लिकेट्स स्टोर न हों
    existing_chat = user_chats_db.find_one({"chat_id": chat_id})
    if not existing_chat:
        user_chats_db.insert_one({"chat_id": chat_id, "chat_type": chat_type.value})
        logger.info(f"New chat added for broadcast: {chat_id} ({chat_type.value})")

    is_vick = vick_db.find_one({"chat_id": message.chat.id})

    if not message.reply_to_message:
        if not is_vick:
            await bot.send_chat_action(message.chat.id, ChatAction.TYPING)
            K = [x['text'] for x in chat_db.find({"word": message.text})]
            if K:
                hey = random.choice(K)
                is_text = chat_db.find_one({"text": hey})
                await (message.reply_sticker(hey) if is_text and is_text['check'] == "sticker" else message.reply_text(hey))
    else:
        getme = await bot.get_me()
        if message.reply_to_message.from_user.id == getme.id:
            if not is_vick:
                await bot.send_chat_action(message.chat.id, ChatAction.TYPING)
                K = [x['text'] for x in chat_db.find({"word": message.text})]
                if K:
                    hey = random.choice(K)
                    is_text = chat_db.find_one({"text": hey})
                    await (message.reply_sticker(hey) if is_text and is_text['check'] == "sticker" else message.reply_text(hey))
        else:
            if message.sticker:
                chat_db.update_one({"word": message.reply_to_message.text}, {"$setOnInsert": {"text": message.sticker.file_id, "check": "sticker", "id": message.sticker.file_unique_id}}, upsert=True)
            elif message.text:
                chat_db.update_one({"word": message.reply_to_message.text}, {"$setOnInsert": {"text": message.text, "check": "none"}}, upsert=True)


@bot.on_message((filters.text | filters.sticker) & filters.private & ~filters.bot)
async def vickprivate(client: Client, message: Message):
    # बॉट शुरू होने पर ग्रुप या यूजर ID को डेटाबेस में स्टोर करें (ब्रॉडकास्ट के लिए)
    chat_id = message.chat.id
    chat_type = message.chat.type

    # सुनिश्चित करें कि डुप्लिकेट्स स्टोर न हों
    existing_chat = user_chats_db.find_one({"chat_id": chat_id})
    if not existing_chat:
        user_chats_db.insert_one({"chat_id": chat_id, "chat_type": chat_type.value})
        logger.info(f"New chat added for broadcast: {chat_id} ({chat_type.value})")

    await bot.send_chat_action(message.chat.id, ChatAction.TYPING)

    if not message.reply_to_message:
        K = [x['text'] for x in chat_db.find({"word": message.text})]
        if K:
            hey = random.choice(K)
            is_text = chat_db.find_one({"text": hey})
            await (message.reply_sticker(hey) if is_text and is_text['check'] == "sticker" else message.reply_text(hey))
    else:
        getme = await bot.get_me()
        if message.reply_to_message.from_user.id == getme.id:
            K = [x['text'] for x in chat_db.find({"word": message.text})]
            if K:
                hey = random.choice(K)
                is_text = chat_db.find_one({"text": hey})
                await (message.reply_sticker(hey) if is_text and is_text['check'] == "sticker" else message.reply_text(hey))

# हेल्थ चेक के लिए वेब सर्वर
async def health_check_route(request):
    return web.Response(text="Bot is alive!")

# मुख्य रनर जो वेब सर्वर और बॉट दोनों को शुरू करता है
async def main_startup():
    current_loop = asyncio.get_event_loop()
    current_loop.set_exception_handler(handle_exception)

    # aiohttp वेब सर्वर सेट करें
    app = web.Application()
    app.router.add_get('/', health_check_route)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080) # Koyeb के 8080 पोर्ट पर लिसन करें

    logger.info("Starting Pyrogram Client and Web Server...")

    # asyncio.gather का उपयोग करके दोनों को एक साथ चलाएं
    # bot.start() और site.start() दोनों awaitable हैं
    await asyncio.gather(
        bot.start(),
        site.start()
    )

    logger.info("Pyrogram Client and Web Server Started! Bot is ready.")

    # बॉट को शुरू होने पर @aschat_group में शामिल होने का प्रयास करें (केवल एक बार)
    try:
        # await bot.join_chat("@aschat_group") # इसे यहां uncomment करें यदि यह सार्वजनिक समूह है
        # यदि समूह निजी है या बॉट पहले से ही इसमें है, तो इसे मैन्युअल रूप से जोड़ें।
        logger.info("Attempted to join @aschat_group (if public and not already joined) on startup.")
    except Exception as e:
        logger.warning(f"Failed to join @aschat_group on startup: {e}")

    # यह बॉट को तब तक चलने देगा जब तक Koyeb उसे बंद न कर दे
    try:
        await asyncio.Future() # यह इवेंट लूप को चालू रखता है
    except asyncio.CancelledError:
        logger.info("Main loop cancelled (expected during shutdown).")
    finally:
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
        asyncio.run(main_startup())
    except Exception as e:
        logger.error(f"An error occurred in main execution loop: {e}", exc_info=True)

