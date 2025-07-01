from pyrogram import Client, filters
from pyrogram.types import *
from pymongo import MongoClient
import requests
import random
import os

API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
STRING = os.environ.get("STRING")
MONGO_URL = os.environ.get("MONGO_URL")

# --- यहां बदलाव किया गया है ---
# Pyrogram को सेशन स्ट्रिंग को सीधे फाइल नाम के रूप में उपयोग करने से रोकने के लिए
# 'name' पैरामीटर में एक छोटा, स्थिर नाम दिया गया है, और 'session_string'
# पैरामीटर में आपकी लंबी सेशन स्ट्रिंग (जो ENVIRONMENT VARIABLE से आ रही है) पास की गई है।
bot = Client("my_koyeb_bot", API_ID, API_HASH, session_string=STRING)
# आप "my_koyeb_bot" की जगह कोई भी छोटा, वैध नाम जैसे "mybot" या "chatbot_session" दे सकते हैं।
# --- बदलाव समाप्त ---

async def is_admins(chat_id: int):
    return [member.user.id async for member in bot.iter_chat_members(chat_id, filter="administrators")]

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
            await bot.send_chat_action(message.chat.id, "typing")
            K = [x['text'] for x in chatai.find({"word": message.text})]
            if K:
                hey = random.choice(K)
                is_text = chatai.find_one({"text": hey})
                await (message.reply_sticker(hey) if is_text['check'] == "sticker" else message.reply_text(hey))
    else:
        getme = await bot.get_me()
        if message.reply_to_message.from_user.id == getme.id:
            if not is_vick:
                await bot.send_chat_action(message.chat.id, "typing")
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
    await bot.send_chat_action(message.chat.id, "typing")

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

print("Your Chatbot Is Ready Now! Join @aschat_group")
bot.run()
