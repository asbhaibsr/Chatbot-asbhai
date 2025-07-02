import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pymongo import MongoClient
from datetime import datetime, timedelta
import logging
import re
import random

# --- Logger Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Environment Variables ---
# Inhe Koyeb par environment variables ke roop mein set karein.
# .env.example file mein references ke liye hain.
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_DB_URI = os.getenv("MONGO_DB_URI")
OWNER_ID = os.getenv("OWNER_ID") # Owner ki user ID (string format mein)

# --- Constants ---
MAX_MESSAGES_THRESHOLD = 100000 # Jab database mein itne messages ho jayein
PRUNE_PERCENTAGE = 0.30          # Kitna data delete karna hai (30%)

# --- MongoDB Setup ---
try:
    client = MongoClient(MONGO_DB_URI)
    db = client.bot_database # Aap apne database ka naam badal sakte hain
    messages_collection = db.messages
    logger.info("MongoDB connection successful.")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {e}")
    # Bot exit kar jayega agar DB connect nahi hua
    exit(1)

# --- Pyrogram Client ---
app = Client(
    "self_learning_bot", # Session name
    bot_token=BOT_TOKEN
)

# --- Utility Functions ---
def extract_keywords(text):
    """
    Message se basic keywords extract karta hai.
    Advanced NLP ke liye yahan improvements ki ja sakti hain.
    """
    if not text:
        return []
    # Sirf alphanumeric words ko keywords maanein
    words = re.findall(r'\b\w+\b', text.lower())
    # Common stopwords hata sakte hain, lekin abhi simple rakhte hain
    return list(set(words)) # Duplicate keywords hatane ke liye

async def prune_old_messages():
    """
    Database se purane messages ko remove karta hai jab threshold cross ho jaye.
    """
    total_messages = await messages_collection.count_documents({})
    logger.info(f"Current total messages in DB: {total_messages}")

    if total_messages > MAX_MESSAGES_THRESHOLD:
        messages_to_delete_count = int(total_messages * PRUNE_PERCENTAGE)
        logger.info(f"Threshold reached. Deleting {messages_to_delete_count} oldest messages.")

        # Oldest messages ko timestamp ke hisaab se sort karke delete karein
        oldest_message_ids = []
        async for msg in messages_collection.find({}) \
                                            .sort("timestamp", 1) \
                                            .limit(messages_to_delete_count):
            oldest_message_ids.append(msg['_id'])

        if oldest_message_ids:
            delete_result = await messages_collection.delete_many({"_id": {"$in": oldest_message_ids}})
            logger.info(f"Successfully deleted {delete_result.deleted_count} messages.")
        else:
            logger.warning("No oldest messages found to delete despite threshold being reached.")
    else:
        logger.info("Message threshold not reached. No pruning needed.")

# --- Message Storage Logic ---
async def store_message(message: Message):
    """
    Incoming message ko database mein store karta hai.
    Contextual information bhi add karta hai.
    """
    try:
        message_data = {
            "message_id": message.id,
            "user_id": message.from_user.id if message.from_user else None,
            "username": message.from_user.username if message.from_user else None,
            "first_name": message.from_user.first_name if message.from_user else None,
            "chat_id": message.chat.id,
            "chat_type": message.chat.type.name, # private, group, supergroup, channel
            "chat_title": message.chat.title if message.chat.type != "private" else None,
            "timestamp": datetime.now(),
            "is_bot_observed_pair": False, # Default to False, will be set true if it's a learned pair
        }

        # Text message handling
        if message.text:
            message_data["type"] = "text"
            message_data["content"] = message.text
            message_data["keywords"] = extract_keywords(message.text)
            message_data["sticker_id"] = None
        # Sticker message handling
        elif message.sticker:
            message_data["type"] = "sticker"
            message_data["content"] = message.sticker.emoji if message.sticker.emoji else "" # Store emoji as content
            message_data["sticker_id"] = message.sticker.file_id
            message_data["keywords"] = extract_keywords(message.sticker.emoji) # Stickers se bhi keywords (emoji)

        # Reply to message context (very important for learning)
        if message.reply_to_message:
            message_data["is_reply"] = True
            message_data["replied_to_message_id"] = message.reply_to_message.id
            message_data["replied_to_user_id"] = message.reply_to_message.from_user.id if message.reply_to_message.from_user else None
            message_data["replied_to_content"] = message.reply_to_message.text if message.reply_to_message.text else \
                                                (message.reply_to_message.sticker.emoji if message.reply_to_message.sticker else "")
            # If this message is a reply, we can mark the original message (if found in DB)
            # as part of a learned pair
            original_msg_in_db = await messages_collection.find_one({"chat_id": message.chat.id, "message_id": message.reply_to_message.id})
            if original_msg_in_db:
                # Mark the original message as part of an observed pair
                # This helps in giving higher priority to actual user conversations
                await messages_collection.update_one(
                    {"_id": original_msg_in_db["_id"]},
                    {"$set": {"is_bot_observed_pair": True}}
                )
                # Also mark the current message (the reply) as part of an observed pair
                message_data["is_bot_observed_pair"] = True


        await messages_collection.insert_one(message_data)
        logger.debug(f"Message stored: {message.id} from {message.from_user.id if message.from_user else 'None'}")
        
        # Pruning check after storing a message
        await prune_old_messages()

    except Exception as e:
        logger.error(f"Error storing message {message.id}: {e}")

# --- Reply Generation Logic ---
async def generate_reply(message: Message):
    """
    Bot ke liye reply generate karta hai.
    Priority: Explicitly learned > Group-specific observed > Global observed > General.
    """
    if not message.text and not message.sticker: # Agar message mein text ya sticker nahi hai to reply nahi
        return

    query_content = message.text if message.text else (message.sticker.emoji if message.sticker else "")
    query_keywords = extract_keywords(query_content)

    if not query_keywords:
        logger.debug("No keywords extracted for reply generation.")
        return

    # 1. Search for Direct Contextual Matches (is_bot_observed_pair=True)
    #    Preference: Reply to content (replied_to_content) matches query, and it's a learned pair.
    
    # Try group-specific first
    learned_replies_group = messages_collection.find({
        "chat_id": message.chat.id,
        "is_bot_observed_pair": True,
        "replied_to_content": {"$regex": f".*{re.escape(query_content)}.*", "$options": "i"}
    })
    
    # Fallback to global if no group-specific direct match
    learned_replies_global = messages_collection.find({
        "is_bot_observed_pair": True,
        "replied_to_content": {"$regex": f".*{re.escape(query_content)}.*", "$options": "i"}
    })

    potential_replies = []
    async for doc in learned_replies_group:
        potential_replies.append(doc)
    if not potential_replies: # Agar group mein nahi mila, toh global mein dekho
        async for doc in learned_replies_global:
            potential_replies.append(doc)

    if potential_replies:
        chosen_reply = random.choice(potential_replies)
        return chosen_reply # Return the chosen document, handler will send it

    logger.info(f"No direct observed reply for: '{query_content}'. Falling back to keyword search.")

    # 2. Fallback to General Keyword Matching (any stored message)
    #    Prioritize content that contains any of the keywords
    
    # Construct regex for keywords
    keyword_regex = "|".join([re.escape(kw) for kw in query_keywords])
    
    # Try group-specific general messages first
    general_replies_group = messages_collection.find({
        "chat_id": message.chat.id,
        "type": {"$in": ["text", "sticker"]}, # Reply with either text or sticker
        "content": {"$regex": f".*({keyword_regex}).*", "$options": "i"}
    })

    # Fallback to global general messages
    general_replies_global = messages_collection.find({
        "type": {"$in": ["text", "sticker"]},
        "content": {"$regex": f".*({keyword_regex}).*", "$options": "i"}
    })

    potential_replies = []
    async for doc in general_replies_group:
        potential_replies.append(doc)
    if not potential_replies:
        async for doc in general_replies_global:
            potential_replies.append(doc)

    if potential_replies:
        chosen_reply = random.choice(potential_replies)
        return chosen_reply
    
    logger.info(f"No general keyword reply found for: '{query_content}'.")
    return None # Koi suitable reply nahi mila

# --- Pyrogram Event Handlers ---

@app.on_message(filters.command("start") & filters.private)
async def start_private_command(client: Client, message: Message):
    """
    Private chat mein /start command ka handler.
    Stylish aur funny welcome message.
    """
    welcome_messages = [
        "Namaste, duniya! 👋 Mai aa gaya hoon, aapki baaton ka jaadu dekhne. Chalo, kuch chat-pata karte hain!",
        "Hey there, human! 🤖 Ready to spill some digital tea? I'm all ears... err, circuits!",
        "Bonjour, conversation connoisseur! ✨ Mai yahan aapke shabdon ko sametne aur unhe naya roop dene aaya hoon. Kya haal chaal?",
        "Greetings, fellow data provider! I'm here to listen, learn, and maybe even surprise you. Start typing!",
        "Koshish karne walon ki kabhi haar nahi hoti! Main bhi aapki baaton se seekhne ki koshish kar raha hoon. Shuru ho jao!",
        "Hello! Main ek bot hoon jo aapki baaton ko samajhta aur unse seekhta hai. Aao, baat karte hain."
    ]
    await message.reply_text(random.choice(welcome_messages))
    await store_message(message) # Store the /start command message

@app.on_message(filters.command("start") & filters.group)
async def start_group_command(client: Client, message: Message):
    """
    Group mein /start command ka handler.
    Stylish aur funny welcome message.
    """
    welcome_messages = [
        "Hello, group chat adventurers! 👋 Mai aa gaya hoon aapki conversations mein rang bharne. Kya chal raha hai?",
        "Hey everyone! 🤖 Ready for some group wisdom? I'm listening to learn from all of you!",
        "Is group ki baaton ka mahir banne aaya hoon! Chalo, shuru karte hain iss safar ko. ✨",
        "Namaste to all the wonderful talkers here! Let's make some interesting data together. 😄",
        "Duniya gol hai, aur baatein anmol! Main bhi yahan aapki anmol baaton ko store karne aaya hoon. 📚"
    ]
    await message.reply_text(random.choice(welcome_messages))
    await store_message(message) # Store the /start command message

@app.on_message(filters.command("broadcast") & filters.private)
async def broadcast_command(client: Client, message: Message):
    """
    /broadcast command handler (only for OWNER_ID).
    """
    if str(message.from_user.id) != OWNER_ID:
        await message.reply_text("Sorry, you are not authorized to use this command.")
        return

    if len(message.command) < 2:
        await message.reply_text("Please provide a message to broadcast. Usage: `/broadcast Your message here`")
        return

    broadcast_text = " ".join(message.command[1:])
    
    # Find all unique chat IDs where the bot has seen messages
    unique_chat_ids = await messages_collection.distinct("chat_id")

    sent_count = 0
    failed_count = 0
    for chat_id in unique_chat_ids:
        try:
            # Avoid sending broadcast to the owner's private chat again if they initiated it there
            if chat_id == message.chat.id and message.chat.type == "private":
                continue 
            
            await client.send_message(chat_id, broadcast_text)
            sent_count += 1
            await asyncio.sleep(0.1) # Small delay to avoid flood waits
        except Exception as e:
            logger.error(f"Failed to send broadcast to chat {chat_id}: {e}")
            failed_count += 1
    
    await message.reply_text(f"Broadcast complete! Sent to {sent_count} chats, failed for {failed_count} chats.")
    await store_message(message) # Store the broadcast command message

@app.on_message(filters.command("stats") & filters.private)
async def stats_private_command(client: Client, message: Message):
    """
    Private chat mein /stats check command ka handler.
    """
    if len(message.command) < 2 or message.command[1].lower() != "check":
        await message.reply_text("Usage: `/stats check`")
        return

    total_messages = await messages_collection.count_documents({})
    unique_group_ids = await messages_collection.distinct("chat_id", {"chat_type": {"$in": ["group", "supergroup"]}})
    num_groups = len(unique_group_ids)

    stats_text = (
        "📊 **Bot Statistics** 📊\n"
        f"• Groups I'm in: **{num_groups}**\n"
        f"• Total messages stored: **{total_messages}**"
    )
    await message.reply_text(stats_text)
    await store_message(message) # Store the stats command message

@app.on_message(filters.command("stats") & filters.group)
async def stats_group_command(client: Client, message: Message):
    """
    Group chat mein /stats check command ka handler.
    """
    # Just forward to private stats for simplicity or provide limited info in group
    # For now, let's keep it same as private or you can restrict it.
    if len(message.command) < 2 or message.command[1].lower() != "check":
        await message.reply_text("Usage: `/stats check`")
        return

    total_messages = await messages_collection.count_documents({})
    unique_group_ids = await messages_collection.distinct("chat_id", {"chat_type": {"$in": ["group", "supergroup"]}})
    num_groups = len(unique_group_ids)

    stats_text = (
        "📊 **Bot Statistics** 📊\n"
        f"• Groups I'm in: **{num_groups}**\n"
        f"• Total messages stored: **{total_messages}**"
    )
    await message.reply_text(stats_text)
    await store_message(message) # Store the stats command message

@app.on_message(filters.text | filters.sticker)
async def handle_message_and_reply(client: Client, message: Message):
    """
    Sabhi incoming text aur sticker messages ko handle karta hai.
    Store karta hai aur relevant reply generate karta hai.
    """
    # Bot ke khud ke messages ko store ya process na karein
    if message.from_user and message.from_user.is_bot:
        return

    # Store the incoming message first
    await store_message(message)

    # Bot ko @mention kiya gaya ho ya private chat ho tabhi reply karein
    if message.chat.type == "private" or (message.text and f"@{client.me.username}" in message.text):
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
    logger.info("Starting bot...")
    app.run()
