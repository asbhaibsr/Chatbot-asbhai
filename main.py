import os
import asyncio
import threading
import logging
import re
import random
from datetime import datetime, timedelta

from pyrogram import Client, filters, idle # idle इम्पोर्ट करें
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.raw.functions.messages import SetTyping
from pyrogram.raw.types import SendMessageTypingAction

from pymongo import MongoClient

# Flask imports
from flask import Flask, request, jsonify

# --- Logger Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Configuration Class ---
class Config:
    """Stores all configuration variables."""
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    API_ID = int(os.getenv("API_ID"))
    API_HASH = os.getenv("API_HASH")
    OWNER_ID = int(os.getenv("OWNER_ID")) # OWNER_ID को int में बदल दिया गया

    MONGO_URI_MESSAGES = os.getenv("MONGO_URI_MESSAGES")
    MONGO_URI_BUTTONS = os.getenv("MONGO_URI_BUTTONS") # Buttons के लिए
    MONGO_URI_TRACKING = os.getenv("MONGO_URI_TRACKING") # Tracking के लिए

    MAX_MESSAGES_THRESHOLD = 100000
    PRUNE_PERCENTAGE = 0.30
    UPDATE_CHANNEL_USERNAME = "asbhai_bsr"
    FLASK_PORT = int(os.environ.get('PORT', 8000))

    # Validate essential environment variables
    @classmethod
    def validate(cls):
        required_vars = ["BOT_TOKEN", "API_ID", "API_HASH", "OWNER_ID", 
                         "MONGO_URI_MESSAGES", "MONGO_URI_BUTTONS", "MONGO_URI_TRACKING"]
        for var in required_vars:
            if getattr(cls, var) is None:
                logger.error(f"Missing essential environment variable: {var}. Please check your .env file or environment setup.")
                exit(1)

# Validate config on startup
Config.validate()

# --- MongoDB Setup ---
class MongoDB:
    """Handles all MongoDB connections and provides collection access."""
    def __init__(self):
        self.client_messages = None
        self.db_messages = None
        self.messages_collection = None

        self.client_buttons = None
        self.db_buttons = None
        self.button_interactions_collection = None # Renamed for clarity

        self.client_tracking = None
        self.db_tracking = None
        self.group_tracking_collection = None
        self.user_tracking_collection = None
        self.welcome_messages_collection = None # Welcome messages के लिए नया कलेक्शन
        self._connect()

    def _connect(self):
        try:
            self.client_messages = MongoClient(Config.MONGO_URI_MESSAGES)
            self.db_messages = self.client_messages.bot_database_messages
            self.messages_collection = self.db_messages.messages
            logger.info("MongoDB (Messages) connection successful.")

            self.client_buttons = MongoClient(Config.MONGO_URI_BUTTONS)
            self.db_buttons = self.client_buttons.bot_button_data
            self.button_interactions_collection = self.db_buttons.button_interactions
            logger.info("MongoDB (Buttons) connection successful.")
            
            self.client_tracking = MongoClient(Config.MONGO_URI_TRACKING)
            self.db_tracking = self.client_tracking.bot_tracking_data
            self.group_tracking_collection = self.db_tracking.groups_data
            self.user_tracking_collection = self.db_tracking.users_data
            self.welcome_messages_collection = self.db_tracking.welcome_messages # Same DB, new collection for welcome messages
            logger.info("MongoDB (Tracking) connection successful.")

        except Exception as e:
            logger.error(f"Failed to connect to one or more MongoDB instances: {e}")
            exit(1)

# Initialize MongoDB connections globally
mongo_db = MongoDB()

# --- Pyrogram Client ---
app = Client(
    "self_learning_bot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN
)

# --- Flask App Setup ---
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Bot is running!"

@flask_app.route('/health')
def health_check():
    return jsonify({"status": "ok", "message": "Bot is alive and healthy!"}), 200

def run_flask_app():
    flask_app.run(host='0.0.0.0', port=Config.FLASK_PORT, debug=False)

# --- Utility Functions ---
def extract_keywords(text):
    if not text:
        return []
    words = re.findall(r'\b\w+\b', text.lower())
    return list(set(words))

async def prune_old_messages(messages_collection):
    total_messages = messages_collection.count_documents({})
    logger.info(f"Current total messages in DB: {total_messages}")

    if total_messages > Config.MAX_MESSAGES_THRESHOLD:
        messages_to_delete_count = int(total_messages * Config.PRUNE_PERCENTAGE)
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

async def store_message(message: Message, messages_collection):
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
        
        await prune_old_messages(messages_collection)

    except Exception as e:
        logger.error(f"Error storing message {message.id}: {e}")

async def generate_reply(message: Message, messages_collection):
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

# --- Tracking Functions ---
async def update_group_info(chat_id: int, chat_title: str, group_tracking_collection):
    group_tracking_collection.update_one(
        {"_id": chat_id},
        {"$set": {"title": chat_title, "last_updated": datetime.now()},
         "$setOnInsert": {"added_on": datetime.now(), "member_count": 0}},
        upsert=True
    )
    logger.info(f"Group info updated for {chat_title} ({chat_id})")

async def update_user_info(user_id: int, username: str, first_name: str, user_tracking_collection):
    user_tracking_collection.update_one(
        {"_id": user_id},
        {"$set": {"username": username, "first_name": first_name, "last_active": datetime.now()},
         "$setOnInsert": {"joined_on": datetime.now()}},
        upsert=True
    )
    logger.info(f"User info updated for {first_name} ({user_id})")

# --- Admin/Owner Check Functions ---
async def is_admin_or_owner(client: Client, message: Message):
    if message.from_user.id == Config.OWNER_ID:
        return True
    if message.chat.type in ["group", "supergroup"]:
        member = await client.get_chat_member(message.chat.id, message.from_user.id)
        if member.status in ["creator", "administrator"]:
            return True
    return False

async def is_owner(user_id: int):
    return user_id == Config.OWNER_ID

# --- Pyrogram Event Handlers ---

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
                InlineKeyboardButton("📣 Updates Channel", url=f"https://t.me/{Config.UPDATE_CHANNEL_USERNAME}")
            ],
            [
                InlineKeyboardButton("⚙️ Bot Ka Code Chahiye?", callback_data="buy_repo")
            ]
        ]
    )

    await message.reply_text(random.choice(welcome_messages), reply_markup=keyboard)
    await store_message(message, mongo_db.messages_collection)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name, mongo_db.user_tracking_collection)

@app.on_callback_query(filters.regex("buy_repo"))
async def buy_repo_callback(client: Client, callback_query):
    await callback_query.answer("Arre waah! Aapko mera code pasand aaya? 😉\n\nAgar is bot ka GitHub repo chahiye, toh sirf ₹1500 dijiye. Humare @asbhaibsr par message bhejiye. Lekin haan, tabhi karna jab sach mein lena ho, aise hi mazak mein nahi! 😜", show_alert=True)
    # Button interaction ko store karne ke liye
    mongo_db.button_interactions_collection.insert_one({
        "user_id": callback_query.from_user.id,
        "username": callback_query.from_user.username,
        "first_name": callback_query.from_user.first_name,
        "chat_id": callback_query.message.chat.id,
        "callback_data": callback_query.data,
        "timestamp": datetime.now()
    })
    logger.info(f"Button interaction 'buy_repo' from user {callback_query.from_user.id}")

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
                InlineKeyboardButton("📣 Updates Channel", url=f"https://t.me/{Config.UPDATE_CHANNEL_USERNAME}")
            ],
            [
                InlineKeyboardButton("⚙️ Bot Ka Code Chahiye?", callback_data="buy_repo")
            ]
        ]
    )

    await message.reply_text(random.choice(welcome_messages), reply_markup=keyboard)
    await store_message(message, mongo_db.messages_collection)
    if message.chat.type in ["group", "supergroup"]:
        await update_group_info(message.chat.id, message.chat.title, mongo_db.group_tracking_collection)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name, mongo_db.user_tracking_collection)

@app.on_message(filters.command("stats"))
async def stats_command(client: Client, message: Message):
    # Admin/Owner check is not needed for stats, as it's general info
    total_messages = mongo_db.messages_collection.count_documents({})
    unique_group_ids = mongo_db.group_tracking_collection.count_documents({})
    num_users = mongo_db.user_tracking_collection.count_documents({})

    stats_text = (
        "📊 **Bot Statistics** 📊\n"
        f"• Jitne groups mein main hoon: **{unique_group_ids}**\n"
        f"• Total users jo maine observe kiye: **{num_users}**\n"
        f"• Total messages jo maine store kiye: **{total_messages}**\n\n"
        "Meri jaankari dekh kar mazaa aaya? 😉"
    )
    await message.reply_text(stats_text)
    await store_message(message, mongo_db.messages_collection)
    if message.chat.type in ["group", "supergroup"]:
        await update_group_info(message.chat.id, message.chat.title, mongo_db.group_tracking_collection)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name, mongo_db.user_tracking_collection)


@app.on_message(filters.command("help"))
async def help_command(client: Client, message: Message):
    help_text = (
        "❓ **Mujhe madad chahiye? Main yahan hoon!** ❓\n\n"
        "Dekho, yeh sab commands hain jo main jaanti hoon:\n\n"
        "**General Commands:**\n"
        "• `/start` - 🚀 Bot ko shuru karein, aur mujhse milo!\n"
        "• `/stats` - 📊 Meri saari jaankari dekho, kitni mehnat karti hoon main! 😉\n"
        "• `/help` - ❓ Yeh list dobara dekho, kahin bhool na jao! \n"
        "• `/myid` - 🆔 Apni Telegram ID pata karo, secret! \n"
        "• `/chatid` - 💬 Is chat ki ID dekho, pata hai na, har chat ki apni ID hoti hai! \n\n"
        "**Admin Commands (Sirf Admins ke liye, shararat mat karna!):**\n"
        "• `/broadcast <message>` - 📢 Sabko ek message bhejo, jaise main Miss India! \n"
        "• `/resetdata` - 🧹 Bot ka thoda data mitao, safai bhi zaroori hai! \n"
        "• `/deletemessage` - 🗑️ Reply karke kisi message ko delete karo, oops! \n"
        "• `/ban <user>` - 🚫 Kisi ko group se bahar karo, taaki shanti bani rahe! \n"
        "• `/unban <user>` - ✅ Kisi ko wapas aane do, maaf kiya ja! \n"
        "• `/kick <user>` - 👋 Kisi ko thodi der ke liye nikalo, bas zara sa time out! \n"
        "• `/pin` - 📌 Reply karke message pin karo, important hai na! \n"
        "• `/unpin` - 📍 Pin hataya, ab zaroorat nahi! \n"
        "• `/setwelcome <message>` - ✨ Group ke liye welcome message set karo, naye dosto ke liye! \n"
        "• `/getwelcome` - 📜 Apna welcome message dekho, kaisa lag raha hai? \n"
        "• `/clearwelcome` - ❌ Welcome message hatao, naya kuch try karein? \n\n"
        "**Owner Commands (Sirf mere Malikin ke liye, please don't touch!):**\n"
        "• `/restart` - 🔄 Bot ko restart karo, thoda aaram chahiye mujhe! \n"
        "• `/resetall` - 💥 Sara data mitaiye, yeh toh bahut serious hai, soch samajh kar karna! \n\n"
        "Kuch aur chahiye? Mujhse puchho, main smart hoon! 😉"
    )
    await message.reply_text(help_text)
    await store_message(message, mongo_db.messages_collection)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name, mongo_db.user_tracking_collection)


@app.on_message(filters.command("myid"))
async def myid_command(client: Client, message: Message):
    user_id = message.from_user.id
    await message.reply_text(f"Hey cutie! Tumhari Telegram ID hai: `{user_id}`. Kya karoge is secret ka? 😉")
    await store_message(message, mongo_db.messages_collection)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name, mongo_db.user_tracking_collection)


@app.on_message(filters.command("chatid"))
async def chatid_command(client: Client, message: Message):
    chat_id = message.chat.id
    if message.chat.type == "private":
        await message.reply_text(f"Hmm, yeh toh private chat hai! Tumhari aur meri ID same hi toh hogi: `{chat_id}`. Aisa nahi lagta? 🥰")
    else:
        await message.reply_text(f"Oh la la! Is group ki chat ID hai: `{chat_id}`. Ab kya planning hai? 😉")
        await update_group_info(message.chat.id, message.chat.title, mongo_db.group_tracking_collection)
    await store_message(message, mongo_db.messages_collection)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name, mongo_db.user_tracking_collection)

@app.on_message(filters.command("broadcast") & filters.private)
async def broadcast_command(client: Client, message: Message):
    if not await is_owner(message.from_user.id): # Owner check for private broadcast
        await message.reply_text("Sorry darling, yeh command sirf mere Malik ke liye hai! 😉")
        return

    if len(message.command) < 2:
        await message.reply_text("Arre, message toh likho! Kaise bhejungi sabko?\nUpyog: `/broadcast Aapka message yahan`")
        return

    broadcast_text = " ".join(message.command[1:])
    
    unique_chat_ids = mongo_db.group_tracking_collection.distinct("_id") # Only send to groups the bot is in
    unique_user_ids = mongo_db.user_tracking_collection.distinct("_id") # Also send to private users who interacted

    all_target_ids = list(set(unique_chat_ids + unique_user_ids)) # Combine and remove duplicates

    sent_count = 0
    failed_count = 0
    for chat_id in all_target_ids:
        try:
            if chat_id == message.chat.id and message.chat.type == "private":
                continue # Don't send to self in private chat
            
            await client.send_message(chat_id, broadcast_text)
            sent_count += 1
            await asyncio.sleep(0.1) # Small delay to avoid flood waits
        except Exception as e:
            logger.error(f"Failed to send broadcast to chat/user {chat_id}: {e}")
            failed_count += 1
    
    await message.reply_text(f"Broadcast ho gaya, jaaneman! {sent_count} chats ko bheja, aur {failed_count} chats tak nahi pahunch paya. Kabhi-kabhi aisa ho jaata hai! 🤷‍♀️")
    await store_message(message, mongo_db.messages_collection)
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name, mongo_db.user_tracking_collection)

@app.on_message(filters.command("resetdata") & filters.private)
async def reset_data_command(client: Client, message: Message):
    if not await is_owner(message.from_user.id):
        await message.reply_text("Sorry darling, yeh command sirf mere Malik ke liye hai! 😉")
        return
    
    # Example: Clear only messages, not tracking data
    # Kripya dhyaan rakhein: yeh command sirf owner ke liye hai aur kuch data ko hi saaf karega.
    # Agar aapko poora data reset karna hai, toh /resetall command dekhen.
    try:
        mongo_db.messages_collection.delete_many({})
        await message.reply_text("Mera kuch data clean ho gaya hai, jaise maine naha liya ho! 🛀 Kuch naya seekhne ke liye taiyaar hoon! 🥰")
        logger.info(f"Owner {message.from_user.id} initiated partial data reset.")
    except Exception as e:
        await message.reply_text(f"Uff! Kuch error ho gaya, mera data saaf nahi ho paya: {e}")
        logger.error(f"Error resetting data by {message.from_user.id}: {e}")
    await store_message(message, mongo_db.messages_collection)
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name, mongo_db.user_tracking_collection)


@app.on_message(filters.command("deletemessage") & filters.group)
async def delete_message_command(client: Client, message: Message):
    if not await is_admin_or_owner(client, message):
        await message.reply_text("Arre, darling! Yeh command sirf admins ya mere Malik ke liye hai. Tum mat chhedo! 😉")
        return

    if not message.reply_to_message:
        await message.reply_text("Kis message ko delete karna hai? Reply toh karo us message par, aise kaise pata chalega? 🤔")
        return

    try:
        await client.delete_messages(message.chat.id, message.reply_to_message.id)
        await message.delete() # Command message ko bhi delete karein
        logger.info(f"Message {message.reply_to_message.id} deleted by admin/owner in chat {message.chat.id}")
    except Exception as e:
        await message.reply_text(f"Uff! Main us message ko delete nahi kar payi: {e}. Shayad mere paas permission nahi hai? 😟")
        logger.error(f"Error deleting message in chat {message.chat.id}: {e}")
    await store_message(message, mongo_db.messages_collection)
    if message.chat.type in ["group", "supergroup"]:
        await update_group_info(message.chat.id, message.chat.title, mongo_db.group_tracking_collection)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name, mongo_db.user_tracking_collection)


@app.on_message(filters.command("ban") & filters.group)
async def ban_command(client: Client, message: Message):
    if not await is_admin_or_owner(client, message):
        await message.reply_text("Arre, darling! Yeh command sirf admins ya mere Malik ke liye hai. Tum mat chhedo! 😉")
        return

    if not message.reply_to_message and len(message.command) < 2:
        await message.reply_text("Kis user ko ban karna hai? Reply karo ya uska username/ID do.\nUpyog: `/ban @username` or `/ban 123456789`")
        return

    target_user_id = None
    if message.reply_to_message:
        target_user_id = message.reply_to_message.from_user.id
    elif len(message.command) > 1:
        try:
            target_user_id = int(message.command[1])
        except ValueError:
            # Try to resolve username
            try:
                user = await client.get_users(message.command[1])
                target_user_id = user.id
            except Exception:
                await message.reply_text("Yeh user toh mujhe mila hi nahi! Sahi username ya ID do na, jaan! 😕")
                return

    if target_user_id is None:
        await message.reply_text("User ko dhoond nahi payi, phir se koshish karo na. 🕵️‍♀️")
        return
    
    if target_user_id == client.me.id:
        await message.reply_text("Arre! Mujhe hi ban karoge? Main toh tumhari bot hoon! 🥺")
        return

    if target_user_id == Config.OWNER_ID:
        await message.reply_text("Mere Malik ko ban karna? Impossible! Main aisa hone nahi dungi! 😠")
        return

    try:
        await client.ban_chat_member(message.chat.id, target_user_id)
        await message.reply_text(f"Uff! Maine us naughty user ({target_user_id}) ko group se bahar nikaal diya hai. Ab group mein shaanti rahegi! 🤫")
        logger.info(f"User {target_user_id} banned by admin/owner in chat {message.chat.id}")
    except Exception as e:
        await message.reply_text(f"Hayee! Main ban nahi kar payi: {e}. Shayad uske paas powers hain ya meri permission kam hai! 😔")
        logger.error(f"Error banning user {target_user_id} in chat {message.chat.id}: {e}")
    await store_message(message, mongo_db.messages_collection)
    if message.chat.type in ["group", "supergroup"]:
        await update_group_info(message.chat.id, message.chat.title, mongo_db.group_tracking_collection)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name, mongo_db.user_tracking_collection)


@app.on_message(filters.command("unban") & filters.group)
async def unban_command(client: Client, message: Message):
    if not await is_admin_or_owner(client, message):
        await message.reply_text("Arre, darling! Yeh command sirf admins ya mere Malik ke liye hai. Tum mat chhedo! 😉")
        return

    if len(message.command) < 2:
        await message.reply_text("Kis user ko unban karna hai? Uska username/ID do na.\nUpyog: `/unban @username` or `/unban 123456789`")
        return

    target_user_id = None
    try:
        target_user_id = int(message.command[1])
    except ValueError:
        try:
            user = await client.get_users(message.command[1])
            target_user_id = user.id
        except Exception:
            await message.reply_text("Yeh user toh mujhe mila hi nahi! Sahi username ya ID do na, jaan! 😕")
            return

    if target_user_id is None:
        await message.reply_text("User ko dhoond nahi payi, phir se koshish karo na. 🕵️‍♀️")
        return
    
    try:
        await client.unban_chat_member(message.chat.id, target_user_id)
        await message.reply_text(f"Aww! Maine us user ({target_user_id}) ko maaf kar diya hai. Ab woh group mein wapas aa sakta hai! 🤗")
        logger.info(f"User {target_user_id} unbanned by admin/owner in chat {message.chat.id}")
    except Exception as e:
        await message.reply_text(f"Uff! Main unban nahi kar payi: {e}. Lagta hai woh pehle se hi unbanned hai ya kuch gadbad hai! 🤷‍♀️")
        logger.error(f"Error unbanning user {target_user_id} in chat {message.chat.id}: {e}")
    await store_message(message, mongo_db.messages_collection)
    if message.chat.type in ["group", "supergroup"]:
        await update_group_info(message.chat.id, message.chat.title, mongo_db.group_tracking_collection)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name, mongo_db.user_tracking_collection)


@app.on_message(filters.command("kick") & filters.group)
async def kick_command(client: Client, message: Message):
    if not await is_admin_or_owner(client, message):
        await message.reply_text("Arre, darling! Yeh command sirf admins ya mere Malik ke liye hai. Tum mat chhedo! 😉")
        return

    if not message.reply_to_message and len(message.command) < 2:
        await message.reply_text("Kis user ko kick karna hai? Reply karo ya uska username/ID do.\nUpyog: `/kick @username` or `/kick 123456789`")
        return

    target_user_id = None
    if message.reply_to_message:
        target_user_id = message.reply_to_message.from_user.id
    elif len(message.command) > 1:
        try:
            target_user_id = int(message.command[1])
        except ValueError:
            try:
                user = await client.get_users(message.command[1])
                target_user_id = user.id
            except Exception:
                await message.reply_text("Yeh user toh mujhe mila hi nahi! Sahi username ya ID do na, jaan! 😕")
                return

    if target_user_id is None:
        await message.reply_text("User ko dhoond nahi payi, phir se koshish karo na. 🕵️‍♀️")
        return

    if target_user_id == client.me.id:
        await message.reply_text("Arre! Mujhe hi kick karoge? Main toh tumhari bot hoon! 🥺")
        return

    if target_user_id == Config.OWNER_ID:
        await message.reply_text("Mere Malik ko kick karna? Impossible! Main aisa hone nahi dungi! 😠")
        return
    
    try:
        await client.kick_chat_member(message.chat.id, target_user_id)
        await message.reply_text(f"Uff! Maine us user ({target_user_id}) ko thodi der ke liye group se nikaal diya hai. Ab woh turant wapas aa sakta hai, par sharaarat nahi! 😜")
        logger.info(f"User {target_user_id} kicked by admin/owner in chat {message.chat.id}")
    except Exception as e:
        await message.reply_text(f"Hayee! Main kick nahi kar payi: {e}. Shayad uske paas powers hain ya meri permission kam hai! 😔")
        logger.error(f"Error kicking user {target_user_id} in chat {message.chat.id}: {e}")
    await store_message(message, mongo_db.messages_collection)
    if message.chat.type in ["group", "supergroup"]:
        await update_group_info(message.chat.id, message.chat.title, mongo_db.group_tracking_collection)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name, mongo_db.user_tracking_collection)


@app.on_message(filters.command("pin") & filters.group)
async def pin_command(client: Client, message: Message):
    if not await is_admin_or_owner(client, message):
        await message.reply_text("Arre, darling! Yeh command sirf admins ya mere Malik ke liye hai. Tum mat chhedo! 😉")
        return

    if not message.reply_to_message:
        await message.reply_text("Kis message ko pin karna hai? Reply toh karo us message par, aise kaise pata chalega? 🤔")
        return
    
    try:
        await client.pin_chat_message(message.chat.id, message.reply_to_message.id)
        await message.reply_text("Lo ho gaya pin! Ab yeh message sabko dikhega, jaise main Miss Important! 💅")
        logger.info(f"Message {message.reply_to_message.id} pinned by admin/owner in chat {message.chat.id}")
    except Exception as e:
        await message.reply_text(f"Uff! Main pin nahi kar payi: {e}. Meri powers kam pad rahi hain! 😔")
        logger.error(f"Error pinning message in chat {message.chat.id}: {e}")
    await store_message(message, mongo_db.messages_collection)
    if message.chat.type in ["group", "supergroup"]:
        await update_group_info(message.chat.id, message.chat.title, mongo_db.group_tracking_collection)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name, mongo_db.user_tracking_collection)


@app.on_message(filters.command("unpin") & filters.group)
async def unpin_command(client: Client, message: Message):
    if not await is_admin_or_owner(client, message):
        await message.reply_text("Arre, darling! Yeh command sirf admins ya mere Malik ke liye hai. Tum mat chhedo! 😉")
        return

    if not message.reply_to_message:
        await message.reply_text("Kis message ko unpin karna hai? Reply toh karo us message par, aise kaise pata chalega? 🤔")
        return

    try:
        await client.unpin_chat_message(message.chat.id, message.reply_to_message.id)
        await message.reply_text("Pin hata diya! Ab woh message thoda rest karega. 😌")
        logger.info(f"Message {message.reply_to_message.id} unpinned by admin/owner in chat {message.chat.id}")
    except Exception as e:
        await message.reply_text(f"Uff! Main unpin nahi kar payi: {e}. Shayad pin tha hi nahi? 🤷‍♀️")
        logger.error(f"Error unpinning message in chat {message.chat.id}: {e}")
    await store_message(message, mongo_db.messages_collection)
    if message.chat.type in ["group", "supergroup"]:
        await update_group_info(message.chat.id, message.chat.title, mongo_db.group_tracking_collection)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name, mongo_db.user_tracking_collection)


@app.on_message(filters.command("setwelcome") & filters.group)
async def set_welcome_command(client: Client, message: Message):
    if not await is_admin_or_owner(client, message):
        await message.reply_text("Arre, darling! Yeh command sirf admins ya mere Malik ke liye hai. Tum mat chhedo! 😉")
        return

    if len(message.command) < 2:
        await message.reply_text("Naye dosto ka welcome kaise karogi? Welcome message toh likho! \nUpyog: `/setwelcome Hello <name>! Welcome to our awesome group!`")
        return

    welcome_msg = " ".join(message.command[1:])
    try:
        mongo_db.welcome_messages_collection.update_one(
            {"_id": message.chat.id},
            {"$set": {"message": welcome_msg}},
            upsert=True
        )
        await message.reply_text("Aww! Maine naye dosto ke liye welcome message set kar diya hai. Ab sabko special feel hoga! 🥰")
        logger.info(f"Welcome message set for chat {message.chat.id}")
    except Exception as e:
        await message.reply_text(f"Uff! Welcome message set nahi ho paya: {e}. Kuch gadbad hai! 😔")
        logger.error(f"Error setting welcome message for chat {message.chat.id}: {e}")
    await store_message(message, mongo_db.messages_collection)
    if message.chat.type in ["group", "supergroup"]:
        await update_group_info(message.chat.id, message.chat.title, mongo_db.group_tracking_collection)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name, mongo_db.user_tracking_collection)


@app.on_message(filters.command("getwelcome") & filters.group)
async def get_welcome_command(client: Client, message: Message):
    if not await is_admin_or_owner(client, message):
        await message.reply_text("Arre, darling! Yeh command sirf admins ya mere Malik ke liye hai. Tum mat chhedo! 😉")
        return

    try:
        welcome_data = mongo_db.welcome_messages_collection.find_one({"_id": message.chat.id})
        if welcome_data and welcome_data.get("message"):
            await message.reply_text(f"Tumhare group ka current welcome message hai:\n\n`{welcome_data['message']}`\n\nPasand aaya? 😊")
        else:
            await message.reply_text("Abhi tak koi welcome message set nahi kiya gaya hai, meri jaan! ✨ `/setwelcome` use karo na!")
    except Exception as e:
        await message.reply_text(f"Uff! Welcome message retrieve nahi ho paya: {e}. Kuch gadbad hai! 😔")
        logger.error(f"Error getting welcome message for chat {message.chat.id}: {e}")
    await store_message(message, mongo_db.messages_collection)
    if message.chat.type in ["group", "supergroup"]:
        await update_group_info(message.chat.id, message.chat.title, mongo_db.group_tracking_collection)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name, mongo_db.user_tracking_collection)


@app.on_message(filters.command("clearwelcome") & filters.group)
async def clear_welcome_command(client: Client, message: Message):
    if not await is_admin_or_owner(client, message):
        await message.reply_text("Arre, darling! Yeh command sirf admins ya mere Malik ke liye hai. Tum mat chhedo! 😉")
        return

    try:
        result = mongo_db.welcome_messages_collection.delete_one({"_id": message.chat.id})
        if result.deleted_count > 0:
            await message.reply_text("Lo, tumhare group ka welcome message saaf kar diya! Ab naya welcome message banao, main help karungi! 😉")
        else:
            await message.reply_text("Yahan toh koi welcome message tha hi nahi, mera pyara! Kya saaf karti main? 🤷‍♀️")
    except Exception as e:
        await message.reply_text(f"Uff! Welcome message clear nahi ho paya: {e}. Kuch gadbad hai! 😔")
        logger.error(f"Error clearing welcome message for chat {message.chat.id}: {e}")
    await store_message(message, mongo_db.messages_collection)
    if message.chat.type in ["group", "supergroup"]:
        await update_group_info(message.chat.id, message.chat.title, mongo_db.group_tracking_collection)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name, mongo_db.user_tracking_collection)


@app.on_message(filters.new_chat_members)
async def new_member_handler(client: Client, message: Message):
    for member in message.new_chat_members:
        if member.id == client.me.id:
            if message.chat.type in ["group", "supergroup"]:
                await update_group_info(message.chat.id, message.chat.title, mongo_db.group_tracking_collection)
                logger.info(f"Bot joined new group: {message.chat.title} ({message.chat.id})")
                await message.reply_text(f"Hello everyone! 🎉 Thank you for adding me to **{message.chat.title}**! I'm here to learn from your conversations. Type /start to know more.")
            break
        else: # For other new members
            if message.chat.type in ["group", "supergroup"]:
                welcome_data = mongo_db.welcome_messages_collection.find_one({"_id": message.chat.id})
                if welcome_data and welcome_data.get("message"):
                    welcome_msg = welcome_data['message']
                    # Placeholder for new member's name
                    if "{name}" in welcome_msg:
                        welcome_msg = welcome_msg.replace("{name}", member.mention)
                    await message.reply_text(welcome_msg)
    await store_message(message, mongo_db.messages_collection)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name, mongo_db.user_tracking_collection)

@app.on_message(filters.left_chat_member)
async def left_member_handler(client: Client, message: Message):
    if message.left_chat_member and message.left_chat_member.id == client.me.id:
        if message.chat.type in ["group", "supergroup"]:
            mongo_db.group_tracking_collection.delete_one({"_id": message.chat.id})
            mongo_db.messages_collection.delete_many({"chat_id": message.chat.id})
            mongo_db.welcome_messages_collection.delete_one({"_id": message.chat.id}) # Welcome message bhi clear karein
            logger.info(f"Bot left group: {message.chat.title} ({message.chat.id}). Data cleared.")
    await store_message(message, mongo_db.messages_collection)

@app.on_message((filters.text | filters.sticker) & ~filters.me & ~filters.bot)
async def handle_message_and_reply(client: Client, message: Message):
    """Handles incoming text and sticker messages, stores them, and attempts to generate a reply."""
    if message.chat.type in ["group", "supergroup"]:
        await update_group_info(message.chat.id, message.chat.title, mongo_db.group_tracking_collection)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name, mongo_db.user_tracking_collection)

    await store_message(message, mongo_db.messages_collection)

    logger.info(f"Attempting to generate reply for chat {message.chat.id}")
    reply_doc = await generate_reply(message, mongo_db.messages_collection)
    
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


# --- Owner Only Commands ---
@app.on_message(filters.command("restart") & filters.private)
async def restart_bot_command(client: Client, message: Message):
    if not await is_owner(message.from_user.id):
        await message.reply_text("Arre, darling! Yeh command sirf mere Malik ke liye hai. Tum mat chhedo! 😉")
        return
    
    await message.reply_text("Awww, mujhe restart karna pad raha hai! Ek min, main abhi wapas aati hoon, fresh hokar! 😘")
    logger.info(f"Bot restart initiated by owner {message.from_user.id}")
    await store_message(message, mongo_db.messages_collection)
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name, mongo_db.user_tracking_collection)
    os.execl(sys.executable, sys.executable, *sys.argv) # Restart the bot process

@app.on_message(filters.command("resetall") & filters.private)
async def reset_all_data_command(client: Client, message: Message):
    if not await is_owner(message.from_user.id):
        await message.reply_text("Arre, darling! Yeh command sirf mere Malik ke liye hai. Tum mat chhedo! 😉")
        return

    # Confirmation step
    if len(message.command) < 2 or message.command[1].lower() != "confirm":
        await message.reply_text("Kya tum sach mein mera **saara data** delete karna chahte ho? 😱 Yeh wapas nahi aayega, bilkul nahi! Agar sure ho, toh `/resetall confirm` likho. Soch lo phir! 😬")
        return

    try:
        mongo_db.messages_collection.delete_many({})
        mongo_db.button_interactions_collection.delete_many({})
        mongo_db.group_tracking_collection.delete_many({})
        mongo_db.user_tracking_collection.delete_many({})
        mongo_db.welcome_messages_collection.delete_many({})

        await message.reply_text("Uff! Maine apna **saara data** erase kar diya hai! 🗑️ Ab main ekdum nayi-nayi hoon, jaise abhi-abhi paida hui! 👶 Chalo, ab naye se baatein karte hain! 😉")
        logger.warning(f"Owner {message.from_user.id} initiated full data reset.")
    except Exception as e:
        await message.reply_text(f"Hayee! Saara data delete nahi ho paya: {e}. Lagta hai kuch rukawat aa gayi! 😫")
        logger.error(f"Error resetting all data by {message.from_user.id}: {e}")
    await store_message(message, mongo_db.messages_collection)
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name, mongo_db.user_tracking_collection)


# --- Main entry point ---
async def main():
    logger.info("Starting Flask health check server in a separate thread...")
    flask_thread = threading.Thread(target=run_flask_app)
    flask_thread.start()

    logger.info("Starting Pyrogram bot...")
    await app.start()
    logger.info("Pyrogram bot started.")
    await idle() # Keep the bot running until interrupted
    logger.info("Pyrogram bot stopping.")
    await app.stop()

if __name__ == "__main__":
    import sys # For restarting the bot
    asyncio.run(main())
