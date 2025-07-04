import os
import asyncio
import threading # Flask को अलग थ्रेड में चलाने के लिए

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.raw.functions.messages import SetTyping
from pyrogram.raw.types import SendMessageTypingAction

from pymongo import MongoClient
from datetime import datetime, timedelta
import logging
import re
import random

# Flask imports
from flask import Flask, request, jsonify # Flask के लिए आवश्यक मॉड्यूल्स

# --- Logger Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Environment Variables ---
BOT_TOKEN = os.getenv("BOT_TOKEN")

MONGO_URI_MESSAGES = os.getenv("MONGO_URI_MESSAGES")
MONGO_URI_BUTTONS = os.getenv("MONGO_URI_BUTTONS")
MONGO_URI_TRACKING = os.getenv("MONGO_URI_TRACKING")

OWNER_ID = os.getenv("OWNER_ID") # Owner ki user ID (string format mein)

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

# --- Constants ---
MAX_MESSAGES_THRESHOLD = 100000
PRUNE_PERCENTAGE = 0.30
UPDATE_CHANNEL_USERNAME = "asbhai_bsr"

# --- MongoDB Setup ---
try:
    client_messages = MongoClient(MONGO_URI_MESSAGES)
    db_messages = client_messages.bot_database_messages
    messages_collection = db_messages.messages
    logger.info("MongoDB (Messages) connection successful.")

    client_buttons = MongoClient(MONGO_URI_BUTTONS)
    db_buttons = client_buttons.bot_button_data
    buttons_collection = db_buttons.button_interactions
    logger.info("MongoDB (Buttons) connection successful.")
    
    client_tracking = MongoClient(MONGO_URI_TRACKING)
    db_tracking = client_tracking.bot_tracking_data
    group_tracking_collection = db_tracking.groups_data
    user_tracking_collection = db_tracking.users_data
    logger.info("MongoDB (Tracking) connection successful.")

except Exception as e:
    logger.error(f"Failed to connect to one or more MongoDB instances: {e}")
    exit(1)

# --- Pyrogram Client ---
app = Client(
    "self_learning_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# --- Flask App Setup ---
# Flask एप्लीकेशन को इनिशियलाइज़ करें
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Bot is running!"

@flask_app.route('/health')
def health_check():
    # यह एंडपॉइंट Koyeb के हेल्थ चेक के लिए है।
    # यह सिर्फ़ 200 OK स्टेटस रिटर्न करेगा, यह दर्शाता है कि सर्वर चालू है।
    return jsonify({"status": "ok", "message": "Bot is alive and healthy!"}), 200

def run_flask_app():
    # Flask ऐप को पोर्ट 8000 पर चलाएँ। Koyeb डिफ़ॉल्ट रूप से पोर्ट 8000 पर सुनता है।
    # debug=False रखें प्रोडक्शन के लिए।
    flask_app.run(host='0.0.0.0', port=os.environ.get('PORT', 8000), debug=False)

# --- Utility Functions (Same as before) ---
def extract_keywords(text):
    if not text:
        return []
    words = re.findall(r'\b\w+\b', text.lower())
    return list(set(words))

async def prune_old_messages():
    total_messages = messages_collection.count_documents({})
    logger.info(f"Current total messages in DB: {total_messages}")

    if total_messages > MAX_MESSAGES_THRESHOLD:
        messages_to_delete_count = int(total_messages * PRUNE_PERCENTAGE)
        logger.info(f"Threshold reached. Deleting {messages_to_delete_count} oldest messages.")

        oldest_message_ids = []
        for msg in messages_collection.find({}) \
                                            .sort("timestamp", 1) \
                                            .limit(messages_to_delete_count):
            oldest_message_ids.append(msg['_id'])

        if oldest_message_ids:
            delete_result = messages_collection.delete_many({"_id": {"$in": oldest_message_ids}})
            logger.info(f"Successfully deleted {delete_result.deleted_count} messages.")
        else:
            logger.warning("No oldest messages found to delete despite threshold being reached.")
    else:
        logger.info("Message threshold not reached. No pruning needed.")

# --- Message Storage Logic (Same as before) ---
async def store_message(message: Message):
    try:
        message_data = {
            "message_id": message.id,
            "user_id": message.from_user.id if message.from_user else None,
            "username": message.from_user.username if message.from_user else None,
            "first_name": message.from_user.first_name if message.from_user else None,
            "chat_id": message.chat.id,
            "chat_type": message.chat.type.name,
            "chat_title": message.chat.title if message.chat.type != "private" else None,
            "timestamp": datetime.now(),
            "is_bot_observed_pair": False,
        }

        if message.text:
            message_data["type"] = "text"
            message_data["content"] = message.text
            message_data["keywords"] = extract_keywords(message.text)
            message_data["sticker_id"] = None
        elif message.sticker:
            message_data["type"] = "sticker"
            message_data["content"] = message.sticker.emoji if message.sticker.emoji else ""
            message_data["sticker_id"] = message.sticker.file_id
            message_data["keywords"] = extract_keywords(message.sticker.emoji)
        else:
            logger.debug(f"Unsupported message type for storage: {message.id}")
            return

        if message.reply_to_message:
            message_data["is_reply"] = True
            message_data["replied_to_message_id"] = message.reply_to_message.id
            message_data["replied_to_user_id"] = message.reply_to_message.from_user.id if message.reply_to_message.from_user else None
            
            replied_content = None
            if message.reply_to_message.text:
                replied_content = message.reply_to_message.text
            elif message.reply_to_message.sticker:
                replied_content = message.reply_to_message.sticker.emoji if message.reply_to_message.sticker.emoji else ""
            
            message_data["replied_to_content"] = replied_content

            original_msg_in_db = messages_collection.find_one({"chat_id": message.chat.id, "message_id": message.reply_to_message.id})
            if original_msg_in_db:
                messages_collection.update_one(
                    {"_id": original_msg_in_db["_id"]},
                    {"$set": {"is_bot_observed_pair": True}}
                )
                message_data["is_bot_observed_pair"] = True

        messages_collection.insert_one(message_data)
        logger.debug(f"Message stored: {message.id} from {message.from_user.id if message.from_user else 'None'}")
        
        await prune_old_messages()

    except Exception as e:
        logger.error(f"Error storing message {message.id}: {e}")

# --- Reply Generation Logic (Same as before) ---
async def generate_reply(message: Message):
    await app.invoke(
        SetTyping(
            peer=await app.resolve_peer(message.chat.id),
            action=SendMessageTypingAction()
        )
    )
    await asyncio.sleep(0.5)

    if not message.text and not message.sticker:
        return

    query_content = message.text if message.text else (message.sticker.emoji if message.sticker else "")
    query_keywords = extract_keywords(query_content)

    if not query_keywords and not query_content:
        logger.debug("No content or keywords extracted for reply generation.")
        return

    learned_replies_group_cursor = messages_collection.find({
        "chat_id": message.chat.id,
        "is_bot_observed_pair": True,
        "replied_to_content": {"$regex": f"^{re.escape(query_content)}$", "$options": "i"}
    })
    
    potential_replies = []
    for doc in learned_replies_group_cursor:
        potential_replies.append(doc)

    if not potential_replies:
        learned_replies_global_cursor = messages_collection.find({
            "is_bot_observed_pair": True,
            "replied_to_content": {"$regex": f"^{re.escape(query_content)}$", "$options": "i"}
        })
        for doc in learned_replies_global_cursor:
            potential_replies.append(doc)

    if potential_replies:
        chosen_reply = random.choice(potential_replies)
        return chosen_reply

    logger.info(f"No direct observed reply for: '{query_content}'. Falling back to keyword search.")

    keyword_regex = "|".join([re.escape(kw) for kw in query_keywords])
    
    general_replies_group_cursor = messages_collection.find({
        "chat_id": message.chat.id,
        "type": {"$in": ["text", "sticker"]},
        "content": {"$regex": f".*({keyword_regex}).*", "$options": "i"} if keyword_regex else {"$exists": True}
    })

    potential_replies = []
    for doc in general_replies_group_cursor:
        potential_replies.append(doc)

    if not potential_replies:
        general_replies_global_cursor = messages_collection.find({
            "type": {"$in": ["text", "sticker"]},
            "content": {"$regex": f".*({keyword_regex}).*", "$options": "i"} if keyword_regex else {"$exists": True}
        })
        for doc in general_replies_global_cursor:
            potential_replies.append(doc)

    if potential_replies:
        chosen_reply = random.choice(potential_replies)
        return chosen_reply
    
    logger.info(f"No general keyword reply found for: '{query_content}'.")
    return None

# --- Tracking Functions (Same as before) ---
async def update_group_info(chat_id: int, chat_title: str):
    group_tracking_collection.update_one(
        {"_id": chat_id},
        {"$set": {"title": chat_title, "last_updated": datetime.now()},
         "$setOnInsert": {"added_on": datetime.now(), "member_count": 0}},
        upsert=True
    )
    logger.info(f"Group info updated for {chat_title} ({chat_id})")

async def update_user_info(user_id: int, username: str, first_name: str):
    user_tracking_collection.update_one(
        {"_id": user_id},
        {"$set": {"username": username, "first_name": first_name, "last_active": datetime.now()},
         "$setOnInsert": {"joined_on": datetime.now()}},
        upsert=True
    )
    logger.info(f"User info updated for {first_name} ({user_id})")

# --- Pyrogram Event Handlers (Same as before) ---

@app.on_message(filters.command("start") & filters.private)
async def start_private_command(client: Client, message: Message):
    welcome_messages = [
        "Hi there! 👋 Main aa gayi hoon aapki baaton ka hissa banne. Chalo, kuch mithaas bhari baatein karte hain!",
        "Helloooo! 💖 Main sunne aur seekhne ke liye taiyar hoon. Aapki har baat mere liye khaas hai!",
        "Namaste, pyaare dost! ✨ Main yahan aapke shabdon ko sametne aur unhe naya roop dene aayi hoon. Kaisi ho/ho tum?",
        "Hey cutie! Main aa gayi hoon aapke sath baatein karne. Ready to chat? 😉",
        "Koshish karne walon ki kabhi haar nahi hoti! Main bhi aapki baaton se seekhne ki koshish kar rahi hoon. Aao, baat karein!",
        "Hello! Main ek bot hoon jo aapki baaton ko samajhta aur unse seekhta hai. Aao, baat karte hain, theek hai?"
    ]
    
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("➕ Add Me to Your Group", url=f"https://t.me/{client.me.username}?startgroup=true")
            ],
            [
                InlineKeyboardButton("📣 Updates Channel", url=f"https://t.me/{UPDATE_CHANNEL_USERNAME}")
            ]
        ]
    )

    await message.reply_text(random.choice(welcome_messages), reply_markup=keyboard)
    await store_message(message)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)

@app.on_message(filters.command("start") & filters.group)
async def start_group_command(client: Client, message: Message):
    welcome_messages = [
        "Hello, my lovely group! 👋 Main aa gayi hoon aapki conversations mein shamil hone. Kya chal raha hai sabke beech?",
        "Hey everyone! 💖 Main sun rahi hoon aap sab ki baatein. Chalo, kuch interesting discussions karte hain!",
        "Is group ki conversations ko samajhne aayi hoon! ✨ Aap sab ki baaton se seekhna kitna mazedaar hai. Shuru ho jao!",
        "Namaste to all the amazing people here! Let's create some beautiful memories (aur data) together. 😄",
        "Duniya gol hai, aur baatein anmol! Main bhi yahan aapki anmol baaton ko store karne aayi hoon. Sunane ko taiyar hoon! 📚"
    ]

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("📣 Updates Channel", url=f"https://t.me/{UPDATE_CHANNEL_USERNAME}")
            ]
        ]
    )

    await message.reply_text(random.choice(welcome_messages), reply_markup=keyboard)
    await store_message(message)
    if message.chat.type in ["group", "supergroup"]:
        await update_group_info(message.chat.id, message.chat.title)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)

@app.on_message(filters.command("broadcast") & filters.private)
async def broadcast_command(client: Client, message: Message):
    if str(message.from_user.id) != OWNER_ID:
        await message.reply_text("Sorry, aapko yeh command use karne ki anumati nahi hai.")
        return

    if len(message.command) < 2:
        await message.reply_text("Kripya broadcast karne ke liye ek message dein. Upyog: `/broadcast Aapka message yahan`")
        return

    broadcast_text = " ".join(message.command[1:])
    
    unique_chat_ids = messages_collection.distinct("chat_id")

    sent_count = 0
    failed_count = 0
    for chat_id in unique_chat_ids:
        try:
            if chat_id == message.chat.id and message.chat.type == "private":
                continue 
            
            await client.send_message(chat_id, broadcast_text)
            sent_count += 1
            await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"Failed to send broadcast to chat {chat_id}: {e}")
            failed_count += 1
    
    await message.reply_text(f"Broadcast poora hua! {sent_count} chats ko bheja, {failed_count} chats ke liye asafal raha.")
    await store_message(message)

@app.on_message(filters.command("stats") & filters.private)
async def stats_private_command(client: Client, message: Message):
    if len(message.command) < 2 or message.command[1].lower() != "check":
        await message.reply_text("Upyog: `/stats check`")
        return

    total_messages = messages_collection.count_documents({})
    unique_group_ids = group_tracking_collection.count_documents({})
    num_users = user_tracking_collection.count_documents({})

    stats_text = (
        "📊 **Bot Statistics** 📊\n"
        f"• Jitne groups mein main hoon: **{unique_group_ids}**\n"
        f"• Total users jo maine observe kiye: **{num_users}**\n"
        f"• Total messages jo maine store kiye: **{total_messages}**"
    )
    await message.reply_text(stats_text)
    await store_message(message)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)

@app.on_message(filters.command("stats") & filters.group)
async def stats_group_command(client: Client, message: Message):
    if len(message.command) < 2 or message.command[1].lower() != "check":
        await message.reply_text("Upyog: `/stats check`")
        return

    total_messages = messages_collection.count_documents({})
    unique_group_ids = group_tracking_collection.count_documents({})
    num_users = user_tracking_collection.count_documents({})

    stats_text = (
        "📊 **Bot Statistics** 📊\n"
        f"• Jitne groups mein main hoon: **{unique_group_ids}**\n"
        f"• Total users jo maine observe kiye: **{num_users}**\n"
        f"• Total messages jo maine store kiye: **{total_messages}**"
    )
    await message.reply_text(stats_text)
    await store_message(message)
    if message.chat.type in ["group", "supergroup"]:
        await update_group_info(message.chat.id, message.chat.title)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)

# --- Group Management Commands ---

@app.on_message(filters.command("groups") & filters.private)
async def list_groups_command(client: Client, message: Message):
    if str(message.from_user.id) != OWNER_ID:
        await message.reply_text("Sorry, aapko yeh command use karne ki anumati nahi hai.")
        return

    groups = list(group_tracking_collection.find({}))
    if not groups:
        await message.reply_text("Main abhi kisi group mein nahi hoon.")
        return

    group_list_text = "📚 **Groups Jahan Main Hoon** 📚\n\n"
    for i, group in enumerate(groups):
        title = group.get("title", "Unknown Group")
        group_id = group.get("_id")
        added_on = group.get("added_on", "N/A").strftime("%Y-%m-%d %H:%M") if isinstance(group.get("added_on"), datetime) else "N/A"
        
        group_list_text += f"{i+1}. **{title}** (`{group_id}`)\n"
        group_list_text += f"   • Joined: {added_on}\n"
        
    group_list_text += "\n_Yeh data tracking database se hai._"
    await message.reply_text(group_list_text)
    await store_message(message)
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)

@app.on_message(filters.command("leavegroup") & filters.private)
async def leave_group_command(client: Client, message: Message):
    if str(message.from_user.id) != OWNER_ID:
        await message.reply_text("Sorry, aapko yeh command use karne ki anumati nahi hai.")
        return

    if len(message.command) < 2:
        await message.reply_text("Kripya group ID dein jisse aap mujhe hatana chahte hain. Upyog: `/leavegroup -1001234567890`")
        return

    try:
        group_id_str = message.command[1]
        if not group_id_str.startswith('-100'):
            await message.reply_text("Aapne galat Group ID format diya hai. Group ID `-100...` se shuru hoti hai.")
            return

        group_id = int(group_id_str)
        
        await client.leave_chat(group_id)
        
        group_tracking_collection.delete_one({"_id": group_id})
        messages_collection.delete_many({"chat_id": group_id})
        
        await message.reply_text(f"Safaltapoorvak group `{group_id}` se bahar aa gaya aur uska data clear kar diya.")
        logger.info(f"Left group {group_id} and cleared its data.")

    except ValueError:
        await message.reply_text("Invalid group ID format. Kripya ek valid numeric ID dein.")
    except Exception as e:
        await message.reply_text(f"Group se bahar nikalte samay galti hui: {e}")
        logger.error(f"Error leaving group {group_id_str}: {e}")
    
    await store_message(message)
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)

@app.on_message(filters.new_chat_members)
async def new_member_handler(client: Client, message: Message):
    for member in message.new_chat_members:
        if member.id == client.me.id:
            if message.chat.type in ["group", "supergroup"]:
                await update_group_info(message.chat.id, message.chat.title)
                logger.info(f"Bot joined new group: {message.chat.title} ({message.chat.id})")
                await message.reply_text(f"Hello everyone! 🎉 Thank you for adding me to **{message.chat.title}**! I'm here to learn from your conversations. Type /start to know more.")
            break
    await store_message(message)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)

@app.on_message(filters.left_chat_member)
async def left_member_handler(client: Client, message: Message):
    if message.left_chat_member and message.left_chat_member.id == client.me.id:
        if message.chat.type in ["group", "supergroup"]:
            group_tracking_collection.delete_one({"_id": message.chat.id})
            messages_collection.delete_many({"chat_id": message.chat.id})
            logger.info(f"Bot left group: {message.chat.title} ({message.chat.id}). Data cleared.")
    await store_message(message)

@app.on_message(filters.text | filters.sticker)
async def handle_message_and_reply(client: Client, message: Message):
    if message.from_user and message.from_user.is_bot:
        return

    if message.chat.type in ["group", "supergroup"]:
        await update_group_info(message.chat.id, message.chat.title)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)

    await store_message(message)

    logger.info(f"Attempting to generate reply for chat {message.chat.id}")
    reply_doc = await generate_reply(message)
    
    if reply_doc:
        try:
            if reply_doc.get("type") == "text":
                await message.reply_text(reply_doc["content"])
                logger.info(f"Replied with text: {reply_doc['content']}")
            elif reply_doc.get("type") == "sticker" and reply_doc.get("sticker_id"):
                await message.reply_sticker(reply_doc["sticker_id"])
                logger.info(f"Replied with sticker: {reply_doc['sticker_id']}")
            else:
                logger.warning(f"Reply document found but no content/sticker_id: {reply_doc}")
        except Exception as e:
            logger.error(f"Error sending reply for message {message.id}: {e}")
    else:
        logger.info("No suitable reply found.")

# --- Main entry point ---
if __name__ == "__main__":
    # Flask ऐप को एक अलग थ्रेड में चलाएँ
    logger.info("Starting Flask health check server in a separate thread...")
    flask_thread = threading.Thread(target=run_flask_app)
    flask_thread.start()

    logger.info("Starting Pyrogram bot...")
    app.run() # Pyrogram bot को चलाएँ
