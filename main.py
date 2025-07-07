# --- IMPORTANT: THIS BOT CODE IS PROPERTY OF @asbhaibsr ---
# --- Unauthorized FORKING, REBRANDING, or RESELLING is STRICTLY PROHIBITED. ---
# Owner Telegram ID: @asbhaibsr
# Update Channel: @asbhai_bsr
# Support Group: @aschat_group
# Contact @asbhaibsr for any official inquiries or custom bots.
# --- DO NOT REMOVE THESE CREDITS ---

import os
import asyncio
import threading
import time

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.raw.functions.messages import SetTyping
from pyrogram.raw.types import SendMessageTypingAction
from pyrogram.enums import ChatType # Import ChatType for clearer comparisons

from pymongo import MongoClient
from datetime import datetime, timedelta
import logging
import re
import random
import sys

import pytz # <-- Added back for timezone handling

# Flask imports
from flask import Flask, request, jsonify

# --- Logger Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Environment Variables ---
BOT_TOKEN = os.getenv("BOT_TOKEN")

MONGO_URI_MESSAGES = os.getenv("MONGO_URI_MESSAGES")
MONGO_URI_BUTTONS = os.getenv("MONGO_URI_BUTTONS")
MONGO_URI_TRACKING = os.getenv("MONGO_URI_TRACKING") # This will now also house earning data

OWNER_ID = os.getenv("OWNER_ID") # Owner ki user ID (string format mein)

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

# --- Constants ---
MAX_MESSAGES_THRESHOLD = 100000
PRUNE_PERCENTAGE = 0.30
UPDATE_CHANNEL_USERNAME = "asbhai_bsr"
ASBHAI_USERNAME = "asbhaibsr" # asbhaibsr ka username
BOT_PHOTO_URL = "https://envs.sh/FU3.jpg" # New: Bot's photo URL

# --- MongoDB Setup ---
try:
    client_messages = MongoClient(MONGO_URI_MESSAGES)
    db_messages = client_messages.bot_database_messages
    messages_collection = db_messages.messages
    logger.info("MongoDB (Messages) connection successful. Credit: @asbhaibsr")
    
    client_buttons = MongoClient(MONGO_URI_BUTTONS)
    db_buttons = client_buttons.bot_button_data
    buttons_collection = db_buttons.button_interactions
    logger.info("MongoDB (Buttons) connection successful. Credit: @asbhaibsr")
    
    client_tracking = MongoClient(MONGO_URI_TRACKING)
    db_tracking = client_tracking.bot_tracking_data
    group_tracking_collection = db_tracking.groups_data
    user_tracking_collection = db_tracking.users_data
    # New: Earning Tracking Collection within the same tracking DB
    earning_tracking_collection = db_tracking.monthly_earnings_data
    # New: Collection to track last reset date (Still useful for logging/tracking last manual reset)
    reset_status_collection = db_tracking.reset_status
    # NEW: Collection to store user languages
    user_language_collection = db_tracking.user_languages
    logger.info("MongoDB (Tracking & Earning) connection successful. Credit: @asbhaibsr")

    # Create indexes for efficient querying if they don't exist
    messages_collection.create_index([("timestamp", 1)])
    messages_collection.create_index([("user_id", 1)])
    earning_tracking_collection.create_index([("group_message_count", -1)])
    user_language_collection.create_index([("user_id", 1)], unique=True) # Ensure unique language per user


except Exception as e:
    logger.error(f"Failed to connect to one or more MongoDB instances: {e}. Designed by @asbhaibsr")
    exit(1)

# --- Pyrogram Client ---
app = Client(
    "self_learning_bot", # This bot is developed by @asbhaibsr
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# --- Flask App Setup ---
flask_app = Flask(__name__) # Core system by @asbhaibsr

@flask_app.route('/')
def home():
    return "Bot is running! Developed by @asbhaibsr. Support: @aschat_group"

@flask_app.route('/health')
def health_check():
    return jsonify({"status": "ok", "message": "Bot is alive and healthy! Designed by @asbhaibsr"}), 200

def run_flask_app():
    # This background process runs the web server. Original code by @asbhaibsr
    flask_app.run(host='0.0.0.0', port=os.environ.get('PORT', 8000), debug=False)

# --- Cooldown dictionary ---
user_cooldowns = {} # Cooldown system by @asbhaibsr
COOLDOWN_TIME = 3 # seconds

def is_on_cooldown(user_id):
    last_command_time = user_cooldowns.get(user_id)
    if last_command_time is None:
        return False
    return (time.time() - last_command_time) < COOLDOWN_TIME

def update_cooldown(user_id):
    user_cooldowns[user_id] = time.time()

# --- Language Handling ---
async def get_user_language(user_id: int):
    # Function to retrieve user's preferred language.
    lang_data = user_language_collection.find_one({"user_id": user_id})
    return lang_data.get("language", "en") if lang_data else "en" # Default to English

async def set_user_language(user_id: int, language: str):
    # Function to set user's preferred language.
    user_language_collection.update_one(
        {"user_id": user_id},
        {"$set": {"language": language, "last_updated": datetime.now()}},
        upsert=True
    )
    logger.info(f"User {user_id} language set to {language}. (Language system by @asbhaibsr)")

# --- Language-specific Messages ---
MESSAGES = {
    "en": {
        "welcome_private": lambda user_name: [
            f"Hi **{user_name}!** 👋 I'm here. Let's chat! ✨",
            f"Hellooo **{user_name}!** 💖 I'm ready to listen and learn. 😊",
            f"Namaste **{user_name}!** Need anything? 😉 I'm here!"
        ],
        "welcome_group": lambda user_name: [
            f"Hello **{user_name}!** 👋 I'm here. Ready to listen to group conversations! ✨",
            f"Hey **{user_name}!** 💖 I'm here to learn from your conversations. 😊",
            f"Namaste **{user_name}!** I'm your bot in this group. 😄"
        ],
        "buttons_common": [
            InlineKeyboardButton("➕ Add Me to Your Group", url=f"https://t.me/{app.me.username}?startgroup=true")
        ],
        "buttons_group_only": [
            InlineKeyboardButton("📣 Updates Channel", url=f"https://t.me/{UPDATE_CHANNEL_USERNAME}"),
            InlineKeyboardButton("❓ Support Group", url="https://t.me/aschat_group")
        ],
        "buttons_private_only": [
            InlineKeyboardButton("📣 Updates Channel", url=f"https://t.me/{UPDATE_CHANNEL_USERNAME}"),
            InlineKeyboardButton("❓ Support Group", url="https://t.me/aschat_group")
        ],
        "buttons_buy_earning": [
            InlineKeyboardButton("🛒 Buy My Code", callback_data="buy_git_repo"),
            InlineKeyboardButton("💰 Earning Leaderboard", callback_data="show_earning_leaderboard")
        ],
        "buy_code_details": lambda asbhai_username: f"🤩 If you want a bot like me, you'll need to pay ₹500. Contact **@{asbhai_username}** and tell them you want this bot's code. Hurry, deals are hot! 💸\n\n**Owner:** @asbhaibsr\n**Updates:** @asbhai_bsr\n**Support:** @aschat_group",
        "cooldown_message": "Please wait a moment before sending another command. ⏳",
        "no_leaderboard_data": "😢 No user is on the leaderboard yet. Start chatting and be the first! ✨\n\n**Powered By:** @asbhaibsr",
        "top_users_header": "💰 **Top Active Users (This Month)** 💰\n\n",
        "user_earning_details": lambda rank, user_name, username_str, message_count, prize_str: f"**Rank {rank}:** {user_name} ({username_str})\n   • Total Messages: **{message_count}**\n   • Potential Earning: **{prize_str}**\n",
        "earning_rules": "\n**Earning Rules:**\n• Earning will be based solely on **conversation (messages) within group chats.**\n• **Spamming or sending a high volume of messages in quick succession will not be counted.** Only genuine, relevant conversation will be considered.\n• Please ensure your conversations are **meaningful and engaging.**\n• This leaderboard can be **reset manually by the owner using /clearearning command.**\n\n**Powered By:** @asbhaibsr\n**Updates:** @asbhai_bsr\n**Support:** @aschat_group",
        "withdraw_button": "💰 Withdraw Earnings",
        "owner_command_only": "Oops! Sorry sweetie, this command is only for my boss. You don't have permission. 🤷‍♀️ (Code by @asbhaibsr)",
        "broadcast_usage": "Hey, write something to broadcast! 🙄 Like: `/broadcast Your message here` (Code by @asbhaibsr)",
        "broadcast_sent": lambda sent, failed: f"Broadcast done, darling! ✨ **{sent}** chats reached, and **{failed}** failed. Never mind, next time! 😉 (System by @asbhaibsr)",
        "stats_usage": "Umm, to check stats, type it correctly! `/stats check` like this. 😊 (Code by @asbhaibsr)",
        "bot_stats": lambda groups, users, messages: (
            "📊 **Bot Statistics** 📊\n"
            f"• Groups I'm in: **{groups}** lovely groups!\n"
            f"• Total users observed: **{users}** dear users!\n"
            f"• Total messages stored: **{messages}** treasure of talks! 🤩\n\n"
            f"**Powered By:** @asbhaibsr\n**Updates:** @asbhai_bsr\n**Support:** @aschat_group"
        ),
        "no_groups_found": "I'm not in any group yet. I'm lonely, someone add me! 🥺 (Code by @asbhaibsr)",
        "group_list_header": "📚 **Groups I'm In** 📚\n\n",
        "group_list_item": lambda i, title, group_id, added_on: f"{i+1}. **{title}** (`{group_id}`)\n   • Joined: {added_on}\n",
        "group_list_footer": "\n_This data is from the tracking database, completely secret!_ 🤫\n**Code & System By:** @asbhaibsr",
        "leave_group_usage": "Please provide the group ID you want me to leave. Usage: `/leavegroup -1001234567890` (like this, darling!) (Code by @asbhaibsr)",
        "invalid_group_id_format": "You provided an incorrect Group ID format. Group ID starts with `-100...`. Be careful! 😊 (Code by @asbhaibsr)",
        "leave_group_success": lambda group_id: f"Successfully left group `{group_id}` and cleared all its data! Bye-bye! 👋 (Code by @asbhaibsr)",
        "leave_group_error": lambda e: f"An error occurred while leaving the group: {e}. Oh no! 😢 (Code by @asbhaibsr)",
        "clear_data_usage": "How much data to clear? Tell me the percentage, like: `/cleardata 10%` or `/cleardata 100%`! 🧹 (Code by @asbhaibsr)",
        "invalid_percentage": "Percentage must be between 1 and 100. Be a little careful! 🤔 (Code by @asbhaibsr)",
        "invalid_percentage_format": "Invalid percentage format. Percentage should be a number, like `10` or `50`. Try again!💖 (Code by @asbhaibsr)",
        "no_data_to_clear": "I don't have any data to delete yet. Everything is clean-clean! ✨ (Code by @asbhaibsr)",
        "low_data_clear_warning": lambda percentage: f"There's so little data that clearing {percentage}% won't make a difference! 😂 (Code by @asbhaibsr)",
        "zero_percent_clear": "Zero percent? That means no deletion! 😉 (Code by @asbhaibsr)",
        "data_clear_success": lambda percentage, count: f"Wow! 🤩 I successfully deleted **{percentage}%** of your data, meaning **{count}** messages! Now I'm feeling a bit lighter. ✨ (Code by @asbhaibsr)",
        "no_data_found_to_clear": "Umm, didn't find anything to delete. Looks like you already cleaned everything! 🤷‍♀️ (Code by @asbhaibsr)",
        "delete_message_usage": "Which message to delete, tell me! Like: `/deletemessage hello` or `/deletemessage 'what's up'` 👻 (Code by @asbhaibsr)",
        "message_delete_success": lambda query: f"As you command, my master! 🧞‍♀️ I found and deleted the message '{query}'. Now it's no longer part of history! ✨ (Code by @asbhaibsr)",
        "message_not_found_in_db": "Aww, I couldn't find this message. Maybe it changed its location! 🕵️‍♀️ (Code by @asbhaibsr)",
        "message_not_found_globally": "Umm, I couldn't find your message in my database. Check the spelling? 🤔 (Code by @asbhaibsr)",
        "earning_clear_success": "💰 **Earning data successfully cleared!** Now everyone will start from zero again! 😉 (Code by @asbhaibsr)",
        "restart_message": "Okay, darling! I'm taking a short nap and then I'll be back, completely fresh and energetic! Please wait a bit, okay? ✨ (System by @asbhaibsr)",
        "new_group_alert": lambda group_title, group_id, added_by_user, added_on: (
            f"🥳 **New Group Alert!**\n"
            f"Bot has been added to a new group!\n\n"
            f"**Group Name:** {group_title}\n"
            f"**Group ID:** `{group_id}`\n"
            f"**Added By:** {added_by_user}\n"
            f"**Added On:** {added_on}\n\n"
            f"**Code By:** @asbhaibsr\n**Updates:** @asbhai_bsr\n**Support:** @aschat_group"
        ),
        "new_user_private_alert": lambda user_name, user_id, user_username, started_on: (
            f"✨ **New User Alert!**\n"
            f"A new user has started the bot in private chat.\n\n"
            f"**User Name:** {user_name}\n"
            f"**User ID:** `{user_id}`\n"
            f"**Username:** {user_username}\n"
            f"**Started On:** {started_on}\n\n"
            f"**Code By:** @asbhaibsr\n**Updates:** @asbhai_bsr\n**Support:** @aschat_group"
        ),
        "new_group_member_alert": lambda user_name, user_id, user_username, group_title, group_id, joined_on: (
            f"👥 **New Group Member Alert!**\n"
            f"A new user has been added to a group where the bot is also present.\n\n"
            f"**User Name:** {user_name}\n"
            f"**User ID:** `{user_id}`\n"
            f"**Username:** {user_username}\n"
            f"**Group Name:** {group_title}\n"
            f"**Group ID:** `{group_id}`\n"
            f"**Joined On:** {joined_on}\n\n"
            f"**Code By:** @asbhaibsr\n**Updates:** @asbhai_bsr\n**Support:** @aschat_group"
        ),
        "group_left_alert": lambda group_title, group_id, left_by_user, left_on: (
            f"💔 **Group Left Alert!**\n"
            f"Bot has been removed from a group or left itself.\n\n"
            f"**Group Name:** {group_title}\n"
            f"**Group ID:** `{group_id}`\n"
            f"**Action By:** {left_by_user}\n"
            f"**Left On:** {left_on}\n\n"
            f"**Code By:** @asbhaibsr\n**Updates:** @asbhai_bsr\n**Support:** @aschat_group"
        )
    },
    "hi": {
        "welcome_private": lambda user_name: [
            f"नमस्ते **{user_name}!** 👋 मैं आ गई हूँ। चलो, बातें करते हैं! ✨",
            f"हेलोooo **{user_name}!** 💖 मैं सुनने और सीखने के लिए तैयार हूँ। 😊",
            f"नमस्ते **{user_name}!** कोई काम है? 😉 मैं यहाँ हूँ!"
        ],
        "welcome_group": lambda user_name: [
            f"नमस्ते **{user_name}!** 👋 मैं आ गई हूँ। ग्रुप की बातें सुनने को तैयार हूँ! ✨",
            f"हे **{user_name}!** 💖 मैं यहाँ आपकी बातचीत से सीखने आई हूँ। 😊",
            f"नमस्ते **{user_name}!** इस ग्रुप में मैं हूँ आपकी अपनी बॉट। 😄"
        ],
        "buttons_common": [
            InlineKeyboardButton("➕ मुझे अपने ग्रुप में जोड़ें", url=f"https://t.me/{app.me.username}?startgroup=true")
        ],
        "buttons_group_only": [
            InlineKeyboardButton("📣 अपडेट्स चैनल", url=f"https://t.me/{UPDATE_CHANNEL_USERNAME}"),
            InlineKeyboardButton("❓ सपोर्ट ग्रुप", url="https://t.me/aschat_group")
        ],
        "buttons_private_only": [
            InlineKeyboardButton("📣 अपडेट्स चैनल", url=f"https://t.me/{UPDATE_CHANNEL_USERNAME}"),
            InlineKeyboardButton("❓ सपोर्ट ग्रुप", url="https://t.me/aschat_group")
        ],
        "buttons_buy_earning": [
            InlineKeyboardButton("🛒 मेरा कोड खरीदें", callback_data="buy_git_repo"),
            InlineKeyboardButton("💰 कमाई लीडरबोर्ड", callback_data="show_earning_leaderboard")
        ],
        "buy_code_details": lambda asbhai_username: f"🤩 अगर आपको मेरे जैसा खुद का बॉट बनवाना है, तो आपको ₹500 देने होंगे। इसके लिए **@{asbhai_username}** से संपर्क करें और उन्हें बताइए कि आपको इस बॉट का कोड चाहिए बनवाने के लिए। जल्दी करो, डील्स हॉट हैं! 💸\n\n**मालिक:** @asbhaibsr\n**अपडेट्स:** @asbhai_bsr\n**सपोर्ट:** @aschat_group",
        "cooldown_message": "कृपया दूसरा कमांड भेजने से पहले थोड़ा इंतजार करें। ⏳",
        "no_leaderboard_data": "😢 अभी कोई यूजर लीडरबोर्ड पर नहीं है। बातें करो और पहले बन जाओ! ✨\n\n**द्वारा संचालित:** @asbhaibsr",
        "top_users_header": "💰 **शीर्ष सक्रिय उपयोगकर्ता (इस महीने)** 💰\n\n",
        "user_earning_details": lambda rank, user_name, username_str, message_count, prize_str: f"**रैंक {rank}:** {user_name} ({username_str})\n   • कुल संदेश: **{message_count}**\n   • संभावित कमाई: **{prize_str}**\n",
        "earning_rules": "\n**कमाई के नियम:**\n• कमाई केवल **समूह चैट के भीतर बातचीत (संदेशों) पर आधारित होगी।**\n• **स्पैमिंग या तेज़ी से बड़ी संख्या में संदेश भेजना गिना नहीं जाएगा।** केवल वास्तविक, प्रासंगिक बातचीत पर विचार किया जाएगा।\n• कृपया सुनिश्चित करें कि आपकी बातचीत **अर्थपूर्ण और आकर्षक हो।**\n• इस लीडरबोर्ड को **मालिक द्वारा /clearearning कमांड का उपयोग करके मैन्युअल रूप से रीसेट किया जा सकता है।**\n\n**द्वारा संचालित:** @asbhaibsr\n**अपडेट्स:** @asbhai_bsr\n**सपोर्ट:** @aschat_group",
        "withdraw_button": "💰 पैसे निकलवाएँ",
        "owner_command_only": "ओह! सॉरी स्वीटी, यह कमांड सिर्फ मेरे बॉस के लिए है। तुम्हें अनुमति नहीं है। 🤷‍♀️ (कोड द्वारा @asbhaibsr)",
        "broadcast_usage": "हे, ब्रॉडकास्ट करने के लिए कुछ लिखो तो सही! 🙄 जैसे: `/broadcast आपका संदेश यहाँ` (कोड द्वारा @asbhaibsr)",
        "broadcast_sent": lambda sent, failed: f"ब्रॉडकास्ट हो गया, डार्लिंग! ✨ **{sent}** चैट तक पहुंचा, और **{failed}** तक नहीं। कोई नहीं, अगली बार! 😉 (सिस्टम द्वारा @asbhaibsr)",
        "stats_usage": "उम्म, आंकड़े देखने के लिए ठीक से लिखो ना! `/stats check` ऐसे। 😊 (कोड द्वारा @asbhaibsr)",
        "bot_stats": lambda groups, users, messages: (
            "📊 **बॉट के आंकड़े** 📊\n"
            f"• जितने ग्रुप्स में मैं हूँ: **{groups}** प्यारे ग्रुप्स!\n"
            f"• कुल उपयोगकर्ता जो मैंने देखे: **{users}** प्यारे उपयोगकर्ता!\n"
            f"• कुल संदेश जो मैंने स्टोर किए: **{messages}** बातों का खजाना! 🤩\n\n"
            f"**द्वारा संचालित:** @asbhaibsr\n**अपडेट्स:** @asbhai_bsr\n**सपोर्ट:** @aschat_group"
        ),
        "no_groups_found": "मैं अभी किसी ग्रुप में नहीं हूँ। अकेली हूँ, कोई ऐड कर लो ना! 🥺 (कोड द्वारा @asbhaibsr)",
        "group_list_header": "📚 **ग्रुप्स जहाँ मैं हूँ** 📚\n\n",
        "group_list_item": lambda i, title, group_id, added_on: f"{i+1}. **{title}** (`{group_id}`)\n   • शामिल हुआ: {added_on}\n",
        "group_list_footer": "\n_यह डेटा ट्रैकिंग डेटाबेस से है, बिल्कुल सीक्रेट!_ 🤫\n**कोड और सिस्टम द्वारा:** @asbhaibsr",
        "leave_group_usage": "कृपया ग्रुप आईडी दें जिससे आप मुझे हटाना चाहते हैं। उपयोग: `/leavegroup -1001234567890` (ऐसे, डार्लिंग!) (कोड द्वारा @asbhaibsr)",
        "invalid_group_id_format": "आपने गलत ग्रुप आईडी प्रारूप दिया है। ग्रुप आईडी `-100...` से शुरू होती है। थोड़ा ध्यान से! 😊 (कोड द्वारा @asbhaibsr)",
        "leave_group_success": lambda group_id: f"सफलतापूर्वक ग्रुप `{group_id}` से बाहर आ गई, और उसका सारा डेटा भी क्लीन कर दिया! बाय-बाय! 👋 (कोड द्वारा @asbhaibsr)",
        "leave_group_error": lambda e: f"ग्रुप से बाहर निकलते समय गलती हो गई: {e}. ओह नो! 😢 (कोड द्वारा @asbhaibsr)",
        "clear_data_usage": "कितना डेटा क्लीन करना है? प्रतिशत बताओ ना, जैसे: `/cleardata 10%` या `/cleardata 100%`! 🧹 (कोड द्वारा @asbhaibsr)",
        "invalid_percentage": "प्रतिशत 1 से 100 के बीच में होना चाहिए। थोड़ा ध्यान से! 🤔 (कोड द्वारा @asbhaibsr)",
        "invalid_percentage_format": "अमान्य प्रतिशत प्रारूप। प्रतिशत संख्या में होना चाहिए, जैसे `10` या `50`। फिर से कोशिश करो!💖 (कोड द्वारा @asbhaibsr)",
        "no_data_to_clear": "मेरे पास अभी कोई डेटा नहीं है डिलीट करने के लिए। सब क्लीन-क्लीन है! ✨ (कोड द्वारा @asbhaibsr)",
        "low_data_clear_warning": lambda percentage: f"इतना कम डेटा है कि {percentage}% डिलीट करने से कुछ फर्क नहीं पड़ेगा! 😂 (कोड द्वारा @asbhaibsr)",
        "zero_percent_clear": "शून्य प्रतिशत? इसका मतलब कोई विलोपन नहीं! 😉 (कोड द्वारा @asbhaibsr)",
        "data_clear_success": lambda percentage, count: f"वाह! 🤩 मैंने आपका **{percentage}%** डेटा, यानी **{count}** संदेश, सफलतापूर्वक डिलीट कर दिए! अब मैं थोड़ी हल्की महसूस कर रही हूँ। ✨ (कोड द्वारा @asbhaibsr)",
        "no_data_found_to_clear": "उम्म, कुछ डिलीट करने के लिए मिला ही नहीं। लगता है तुमने पहले ही सब क्लीन कर दिया है! 🤷‍♀️ (कोड द्वारा @asbhaibsr)",
        "delete_message_usage": "कौन सा संदेश डिलीट करना है, बताओ तो सही! जैसे: `/deletemessage हेलो` या `/deletemessage 'क्या हाल है'` 👻 (कोड द्वारा @asbhaibsr)",
        "message_delete_success": lambda query: f"जैसा हुकुम मेरे आका! 🧞‍♀️ मैंने '{query}' वाले संदेश को ढूँढ के डिलीट कर दिया। अब वो इतिहास का हिस्सा नहीं रहा! ✨ (कोड द्वारा @asbhaibsr)",
        "message_not_found_in_db": "ओह, यह संदेश तो मुझे मिला ही नहीं। शायद उसने अपनी लोकेशन बदल दी है! 🕵️‍♀️ (कोड द्वारा @asbhaibsr)",
        "message_not_found_globally": "उम्म, मुझे तुम्हारा यह संदेश तो मिला ही नहीं अपने डेटाबेस में। स्पेलिंग चेक कर लो? 🤔 (कोड द्वारा @asbhaibsr)",
        "earning_clear_success": "💰 **कमाई का डेटा सफलतापूर्वक साफ़ कर दिया गया!** अब सब फिर से शून्य से शुरू करेंगे! 😉 (कोड द्वारा @asbhaibsr)",
        "restart_message": "ठीक है, डार्लिंग! मैं अभी एक छोटी सी नींद ले रही हूँ और फिर वापस आ जाऊंगी, बिल्कुल फ्रेश और एनर्जेटिक! थोड़ा इंतजार करना, ठीक है? ✨ (सिस्टम द्वारा @asbhaibsr)",
        "new_group_alert": lambda group_title, group_id, added_by_user, added_on: (
            f"🥳 **नए ग्रुप की सूचना!**\n"
            f"बॉट को एक नए ग्रुप में जोड़ा गया है!\n\n"
            f"**ग्रुप का नाम:** {group_title}\n"
            f"**ग्रुप आईडी:** `{group_id}`\n"
            f"**जोड़ा गया:** {added_by_user}\n"
            f"**जोड़ने का समय:** {added_on}\n\n"
            f"**कोड द्वारा:** @asbhaibsr\n**अपडेट्स:** @asbhai_bsr\n**सपोर्ट:** @aschat_group"
        ),
        "new_user_private_alert": lambda user_name, user_id, user_username, started_on: (
            f"✨ **नए उपयोगकर्ता की सूचना!**\n"
            f"एक नए उपयोगकर्ता ने बॉट को निजी चैट में शुरू किया है।\n\n"
            f"**उपयोगकर्ता का नाम:** {user_name}\n"
            f"**उपयोगकर्ता आईडी:** `{user_id}`\n"
            f"**उपयोगकर्ता नाम:** {user_username}\n"
            f"**शुरू किया गया:** {started_on}\n\n"
            f"**कोड द्वारा:** @asbhaibsr\n**अपडेट्स:** @asbhai_bsr\n**सपोर्ट:** @aschat_group"
        ),
        "new_group_member_alert": lambda user_name, user_id, user_username, group_title, group_id, joined_on: (
            f"👥 **नए समूह सदस्य की सूचना!**\n"
            f"एक नया उपयोगकर्ता समूह में जोड़ा गया है जहाँ बॉट भी मौजूद है।\n\n"
            f"**उपयोगकर्ता का नाम:** {user_name}\n"
            f"**उपयोगकर्ता आईडी:** `{user_id}`\n"
            f"**उपयोगकर्ता नाम:** {user_username}\n"
            f"**समूह का नाम:** {group_title}\n"
            f"**समूह आईडी:** `{group_id}`\n"
            f"**शामिल हुआ:** {joined_on}\n\n"
            f"**कोड द्वारा:** @asbhaibsr\n**अपडेट्स:** @asbhai_bsr\n**सपोर्ट:** @aschat_group"
        ),
        "group_left_alert": lambda group_title, group_id, left_by_user, left_on: (
            f"💔 **समूह छोड़ने की सूचना!**\n"
            f"बॉट को एक समूह से हटाया गया है या वह खुद छोड़ गया है।\n\n"
            f"**समूह का नाम:** {group_title}\n"
            f"**समूह आईडी:** `{group_id}`\n"
            f"**कार्रवाई करने वाला:** {left_by_user}\n"
            f"**छोड़ने का समय:** {left_on}\n\n"
            f"**कोड द्वारा:** @asbhaibsr\n**अपडेट्स:** @asbhai_bsr\n**सपोर्ट:** @aschat_group"
        )
    }
}


# --- Utility Functions ---
def extract_keywords(text):
    # Keyword extraction logic by @asbhaibsr
    if not text:
        return []
    words = re.findall(r'\b\w+\b', text.lower())
    return list(set(words))

async def prune_old_messages():
    # Database pruning logic by @asbhaibsr
    total_messages = messages_collection.count_documents({})
    logger.info(f"Current total messages in DB: {total_messages}. (System by @asbhaibsr)")

    if total_messages > MAX_MESSAGES_THRESHOLD:
        messages_to_delete_count = int(total_messages * PRUNE_PERCENTAGE)
        logger.info(f"Threshold reached. Deleting {messages_to_delete_count} oldest messages. (System by @asbhaibsr)")

        oldest_message_ids = []
        for msg in messages_collection.find({}) \
                                            .sort("timestamp", 1) \
                                            .limit(messages_to_delete_count):
            oldest_message_ids.append(msg['_id'])

        if oldest_message_ids:
            delete_result = messages_collection.delete_many({"_id": {"$in": oldest_message_ids}})
            logger.info(f"Successfully deleted {delete_result.deleted_count} messages. (System by @asbhaibsr)")
        else:
            logger.warning("No oldest messages found to delete despite threshold being reached. (System by @asbhaibsr)")
    else:
        logger.info("Message threshold not reached. No pruning needed. (System by @asbhaibsr)")

# --- Message Storage Logic ---
async def store_message(message: Message):
    try:
        # Avoid storing messages from bots
        if message.from_user and message.from_user.is_bot:
            logger.debug(f"Skipping storage for message from bot: {message.from_user.id}. (Code by @asbhaibsr)")
            return

        message_data = {
            "message_id": message.id,
            "user_id": message.from_user.id if message.from_user else None,
            "username": message.from_user.username if message.from_user else None,
            "first_name": message.from_user.first_name if message.from_user else None,
            "chat_id": message.chat.id,
            "chat_type": message.chat.type.name,
            "chat_title": message.chat.title if message.chat.type != ChatType.PRIVATE else None,
            "timestamp": datetime.now(),
            "is_bot_observed_pair": False, # Default to False, will be updated if it's a reply to bot
            "credits": "Code by @asbhaibsr, Support: @aschat_group" # Hidden Credit
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
            logger.debug(f"Unsupported message type for storage: {message.id}. (Code by @asbhaibsr)")
            return

        # Check if this message is a reply to a bot's message
        if message.reply_to_message:
            message_data["is_reply"] = True
            message_data["replied_to_message_id"] = message.reply_to_message.id
            message_data["replied_to_user_id"] = message.reply_to_message.from_user.id if message.reply_to_message.from_user else None
            
            # Extract content of the message being replied to
            replied_content = None
            if message.reply_to_message.text:
                replied_content = message.reply_to_message.text
            elif message.reply_to_message.sticker:
                replied_content = message.reply_to_message.sticker.emoji if message.reply_to_message.sticker.emoji else ""
            
            message_data["replied_to_content"] = replied_content

            # Check if the reply was to the bot itself
            if message.reply_to_message.from_user and message.reply_to_message.from_user.id == app.me.id:
                message_data["is_bot_observed_pair"] = True
                original_bot_message_in_db = messages_collection.find_one({"chat_id": message.chat.id, "message_id": message.reply_to_message.id})
                if original_bot_message_in_db:
                    messages_collection.update_one(
                        {"_id": original_bot_message_in_db["_id"]},
                        {"$set": {"is_bot_observed_pair": True}}
                    )
                    logger.debug(f"Marked bot's original message {message.reply_to_message.id} as observed pair. (System by @asbhaibsr)")

        messages_collection.insert_one(message_data)
        logger.info(f"Message stored: {message.id} from {message.from_user.id if message.from_user else 'None'}. (Storage by @asbhaibsr)") # Changed to INFO for better visibility
        
        # --- NEW/IMPROVED: Update user's group message count for earning ---
        # This section is crucial for earning tracking.
        logger.debug(f"DEBUG: Checking earning condition in store_message: chat_type={message.chat.type.name}, is_from_user={bool(message.from_user)}, is_not_bot={not message.from_user.is_bot if message.from_user else 'N/A'}") # NEW DEBUG LOG
        
        if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP] and message.from_user and not message.from_user.is_bot:
            user_id_to_track = message.from_user.id
            username_to_track = message.from_user.username
            first_name_to_track = message.from_user.first_name

            logger.info(f"DEBUG: Attempting to update earning count for user {user_id_to_track} ({first_name_to_track}) in chat {message.chat.id}.") # Added debug log

            try:
                # Increment group_message_count for the user
                earning_tracking_collection.update_one(
                    {"_id": user_id_to_track},
                    {"$inc": {"group_message_count": 1},
                     "$set": {"username": username_to_track, "first_name": first_name_to_track, "last_active_group_message": datetime.now()},
                     "$setOnInsert": {"joined_earning_tracking": datetime.now(), "credit": "by @asbhaibsr"}},
                    upsert=True
                )
                # Fetch and log the current count after update
                updated_user_data = earning_tracking_collection.find_one({'_id': user_id_to_track})
                current_count = updated_user_data.get('group_message_count', 0) if updated_user_data else 0
                logger.info(f"Group message count updated for user {user_id_to_track} ({first_name_to_track}). Current count: {current_count}. (Earning tracking by @asbhaibsr)")
            except Exception as e:
                logger.error(f"ERROR: Failed to update earning count for user {user_id_to_track}: {e}. (Earning tracking error by @asbhaibsr)")


        await prune_old_messages()

    except Exception as e:
        logger.error(f"Error storing message {message.id}: {e}. (System by @asbhaibsr)")

# --- Reply Generation Logic ---
async def generate_reply(message: Message):
    # Reply generation core logic by @asbhaibsr
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
        logger.debug("No content or keywords extracted for reply generation. (Code by @asbhaibsr)")
        return

    # --- Step 1: Prioritize replies from bot's observed pairs (contextual learning) ---
    # Search for messages where the bot has previously replied to the current query_content
    # (i.e., user's message is the 'replied_to_content' of a bot's observed pair)
    
    # First, try to find replies specific to the current chat
    potential_replies = []
    
    # Find replies where the bot responded to exactly this content in this chat
    observed_replies_chat_cursor = messages_collection.find({
        "chat_id": message.chat.id,
        "is_bot_observed_pair": True, # Means the message itself was part of an observed pair
        "replied_to_content": {"$regex": f"^{re.escape(query_content)}$", "$options": "i"},
        "user_id": app.me.id # The message to pick as a reply must be from the bot itself
    })
    for doc in observed_replies_chat_cursor:
        potential_replies.append(doc)

    if not potential_replies:
        # If no chat-specific observed replies, try global observed replies
        observed_replies_global_cursor = messages_collection.find({
            "is_bot_observed_pair": True, # Means the message itself was part of an observed pair
            "replied_to_content": {"$regex": f"^{re.escape(query_content)}$", "$options": "i"},
            "user_id": app.me.id # The message to pick as a reply must be from the bot itself
        })
        for doc in observed_replies_global_cursor:
            potential_replies.append(doc)

    if potential_replies:
        chosen_reply = random.choice(potential_replies)
        logger.info(f"Contextual reply found for '{query_content}': {chosen_reply.get('content') or chosen_reply.get('sticker_id')}. (Logic by @asbhaibsr)")
        return chosen_reply

    logger.info(f"No direct observed reply for: '{query_content}'. Falling back to keyword search. (Logic by @asbhaibsr)")

    # --- Step 2: Fallback to general keyword matching (less contextual) ---
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
        logger.info(f"Keyword-based reply found for '{query_content}': {chosen_reply.get('content') or chosen_reply.get('sticker_id')}. (Logic by @asbhaibsr)")
        return chosen_reply
    
    logger.info(f"No suitable reply found for: '{query_content}'. (Logic by @asbhaibsr)")
    return None

# --- Tracking Functions ---
async def update_group_info(chat_id: int, chat_title: str):
    # Group tracking logic by @asbhaibsr
    try:
        group_tracking_collection.update_one(
            {"_id": chat_id},
            {"$set": {"title": chat_title, "last_updated": datetime.now()},
             "$setOnInsert": {"added_on": datetime.now(), "member_count": 0, "credit": "by @asbhaibsr"}}, # Hidden Credit
            upsert=True
        )
        logger.info(f"Group info updated/inserted successfully for {chat_title} ({chat_id}). (Tracking by @asbhaibsr)")
    except Exception as e:
        logger.error(f"Error updating group info for {chat_title} ({chat_id}): {e}. (Tracking by @asbhaibsr)")


async def update_user_info(user_id: int, username: str, first_name: str):
    # User tracking logic by @asbhaibsr
    try:
        user_tracking_collection.update_one(
            {"_id": user_id},
            {"$set": {"username": username, "first_name": first_name, "last_active": datetime.now()},
             "$setOnInsert": {"joined_on": datetime.now(), "credit": "by @asbhaibsr"}}, # Hidden Credit
            upsert=True
        )
        logger.info(f"User info updated/inserted successfully for {first_name} ({user_id}). (Tracking by @asbhaibsr)")
    except Exception as e:
        logger.error(f"Error updating user info for {first_name} ({user_id}): {e}. (Tracking by @asbhaibsr)")

# --- Earning System Functions ---
async def get_top_earning_users():
    # This function returns the top users based on group_message_count.
    # We should return all users with >0 messages, then the display logic can limit to top 3
    pipeline = [
        {"$match": {"group_message_count": {"$gt": 0}}}, # Only users with more than 0 group messages
        {"$sort": {"group_message_count": -1}}, # Sort in descending order
        # Remove limit here so the function returns all active users.
        # The display logic in top_users_command will take care of top 3.
        # {"$limit": 3} 
    ]

    top_users_data = list(earning_tracking_collection.aggregate(pipeline))
    logger.info(f"Fetched top earning users: {len(top_users_data)} results. (Earning system by @asbhaibsr)")

    top_users_details = []
    for user_data in top_users_data:
        top_users_details.append({
            "user_id": user_data["_id"],
            "first_name": user_data.get("first_name", "Unknown User"),
            "username": user_data.get("username"),
            "message_count": user_data["group_message_count"]
        })
    return top_users_details

async def reset_monthly_earnings_manual():
    # This function resets earnings manually when called by the owner.
    logger.info("Manually resetting monthly earnings...")
    now = datetime.now(pytz.timezone('Asia/Kolkata')) # Current time in Delhi timezone

    try:
        # Set all users' group_message_count to 0
        earning_tracking_collection.update_many(
            {}, # All documents
            {"$set": {"group_message_count": 0}}
        )
        logger.info("Monthly earning message counts reset successfully by manual command. (Earning system by @asbhaibsr)")

        # Update the reset date and month/year
        reset_status_collection.update_one(
            {"_id": "last_manual_reset_date"}, # Use a different _id for manual reset tracking
            {"$set": {"last_reset_timestamp": now}},
            upsert=True
        )
        logger.info(f"Manual reset status updated. (Earning system by @asbhaibsr)")

    except Exception as e:
        logger.error(f"Error resetting monthly earnings manually: {e}. (Earning system by @asbhaibsr)")

# --- Pyrogram Event Handlers ---

@app.on_message(filters.command("start") & filters.private)
async def start_private_command(client: Client, message: Message):
    # Start command handler. Designed by @asbhaibsr.
    if is_on_cooldown(message.from_user.id):
        return
    update_cooldown(message.from_user.id)

    user_lang = await get_user_language(message.from_user.id)

    # If language is not set (default 'en'), ask user to choose
    if user_lang == "en" and not user_language_collection.find_one({"user_id": message.from_user.id}):
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("English 🇬🇧", callback_data="set_lang_en"),
                    InlineKeyboardButton("हिंदी 🇮🇳", callback_data="set_lang_hi")
                ]
            ]
        )
        await message.reply_photo(
            photo=BOT_PHOTO_URL,
            caption="Please choose your language:\n\nकृपया अपनी भाषा चुनें:",
            reply_markup=keyboard
        )
    else:
        # Language is already set, or user chose it. Proceed with welcome message in chosen language.
        user_name = message.from_user.first_name if message.from_user else "Pyaare Dost"
        welcome_message = random.choice(MESSAGES[user_lang]["welcome_private"](user_name))
        
        keyboard = InlineKeyboardMarkup(
            [
                MESSAGES[user_lang]["buttons_common"],
                MESSAGES[user_lang]["buttons_private_only"],
                MESSAGES[user_lang]["buttons_buy_earning"]
            ]
        )
        await message.reply_photo(
            photo=BOT_PHOTO_URL,
            caption=welcome_message,
            reply_markup=keyboard
        )

    await store_message(message)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)
    logger.info(f"Private start command processed for user {message.from_user.id}. (Code by @asbhaibsr)")

@app.on_message(filters.command("start") & filters.group)
async def start_group_command(client: Client, message: Message):
    # Group start command handler. Designed by @asbhaibsr.
    if is_on_cooldown(message.from_user.id):
        return
    update_cooldown(message.from_user.id)

    user_lang = await get_user_language(message.from_user.id)

    # In groups, we directly send the welcome message. Language selection happens in private.
    user_name = message.from_user.first_name if message.from_user else "Pyaare Dost"
    welcome_message = random.choice(MESSAGES[user_lang]["welcome_group"](user_name))

    keyboard = InlineKeyboardMarkup(
        [
            MESSAGES[user_lang]["buttons_group_only"],
            MESSAGES[user_lang]["buttons_buy_earning"]
        ]
    )

    await message.reply_photo(
        photo=BOT_PHOTO_URL,
        caption=welcome_message,
        reply_markup=keyboard
    )
    await store_message(message)
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        logger.info(f"Attempting to update group info from /start command in chat {message.chat.id}.")
        await update_group_info(message.chat.id, message.chat.title)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)
    logger.info(f"Group start command processed in chat {message.chat.id}. (Code by @asbhaibsr)")


@app.on_callback_query(filters.regex("^set_lang_"))
async def set_language_callback(client, callback_query):
    user_id = callback_query.from_user.id
    chosen_lang = callback_query.data.split("_")[2] # Extracts 'en' or 'hi'

    await set_user_language(user_id, chosen_lang)
    
    user_name = callback_query.from_user.first_name if callback_query.from_user else "Pyaare Dost"
    
    # Send a confirmation message in the chosen language
    if chosen_lang == "en":
        welcome_message = random.choice(MESSAGES["en"]["welcome_private"](user_name))
        confirm_text = "Language set to English! 🎉"
    else: # hi
        welcome_message = random.choice(MESSAGES["hi"]["welcome_private"](user_name))
        confirm_text = "भाषा हिंदी पर सेट कर दी गई है! 🎉"

    # Update the existing message with the welcome message in the chosen language
    # and the relevant buttons
    keyboard = InlineKeyboardMarkup(
        [
            MESSAGES[chosen_lang]["buttons_common"],
            MESSAGES[chosen_lang]["buttons_private_only"],
            MESSAGES[chosen_lang]["buttons_buy_earning"]
        ]
    )
    await callback_query.message.edit_caption(
        caption=welcome_message,
        reply_markup=keyboard
    )
    await callback_query.answer(confirm_text, show_alert=False)
    
    # Store button interaction
    buttons_collection.insert_one({
        "user_id": user_id,
        "username": callback_query.from_user.username,
        "first_name": callback_query.from_user.first_name,
        "button_data": callback_query.data,
        "timestamp": datetime.now(),
        "credit": "by @asbhaibsr"
    })
    logger.info(f"User {user_id} chose language: {chosen_lang}. (Language system by @asbhaibsr)")


@app.on_callback_query()
async def callback_handler(client, callback_query):
    # Callback query handler. Developed by @asbhaibsr.
    user_lang = await get_user_language(callback_query.from_user.id)

    if callback_query.data == "buy_git_repo":
        await callback_query.message.reply_text(
            MESSAGES[user_lang]["buy_code_details"](ASBHAI_USERNAME),
            quote=True
        )
        await callback_query.answer(
            "Details mil gayi na? Ab jao, deal final karo! 😉" if user_lang == "hi" else "Got the details? Now go, finalize the deal! 😉", 
            show_alert=False
        )
        # Store button interaction
        buttons_collection.insert_one({
            "user_id": callback_query.from_user.id,
            "username": callback_query.from_user.username,
            "first_name": callback_query.from_user.first_name,
            "button_data": callback_query.data,
            "timestamp": datetime.now(),
            "credit": "by @asbhaibsr"
        })
    elif callback_query.data == "show_earning_leaderboard":
        await top_users_command(client, callback_query.message)
        await callback_query.answer(
            "Earning Leaderboard dikha raha hoon! 💰" if user_lang == "hi" else "Showing Earning Leaderboard! 💰", 
            show_alert=False
        )

    logger.info(f"Callback query '{callback_query.data}' processed for user {callback_query.from_user.id}. (Code by @asbhaibsr)")

@app.on_message(filters.command("topusers") & (filters.private | filters.group)) # Allow in both private and group
async def top_users_command(client: Client, message: Message):
    # Top users command handler for earning leaderboard. Designed by @asbhaibsr.
    if is_on_cooldown(message.from_user.id):
        return
    update_cooldown(message.from_user.id)

    user_lang = await get_user_language(message.from_user.id)
    top_users = await get_top_earning_users()

    if not top_users:
        await message.reply_text(MESSAGES[user_lang]["no_leaderboard_data"], quote=True)
        return

    earning_messages = [
        MESSAGES[user_lang]["top_users_header"]
    ]

    prizes = {1: "₹30", 2: "₹15", 3: "₹5"} # Define prizes for top 3

    # Limit to top 3 for display
    for i, user in enumerate(top_users[:3]): # Modified: Slicing to display only top 3
        rank = i + 1
        user_name = user.get('first_name', 'Unknown User')
        username_str = f"@{user.get('username')}" if user.get('username') else "N/A"
        message_count = user.get('message_count', 0)
        prize_str = prizes.get(rank, "₹0")

        earning_messages.append(
            MESSAGES[user_lang]["user_earning_details"](rank, user_name, username_str, message_count, prize_str)
        )
    
    earning_messages.append(MESSAGES[user_lang]["earning_rules"])

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(MESSAGES[user_lang]["withdraw_button"], url=f"https://t.me/{ASBHAI_USERNAME}") # Direct link to owner
            ]
        ]
    )

    await message.reply_text("\n".join(earning_messages), reply_markup=keyboard, quote=True)
    await store_message(message) # Store the command message itself
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)
    logger.info(f"Top users command processed for user {message.from_user.id} in chat {message.chat.id}. (Code by @asbhaibsr)")

@app.on_message(filters.command("broadcast") & filters.private)
async def broadcast_command(client: Client, message: Message):
    # Broadcast command handler. Designed for owner by @asbhaibsr.
    if is_on_cooldown(message.from_user.id):
        return
    update_cooldown(message.from_user.id)

    user_lang = await get_user_language(message.from_user.id)

    # Convert OWNER_ID to str for comparison
    if str(message.from_user.id) != str(OWNER_ID):
        await message.reply_text(MESSAGES[user_lang]["owner_command_only"])
        return

    if len(message.command) < 2:
        await message.reply_text(MESSAGES[user_lang]["broadcast_usage"])
        return

    broadcast_text = " ".join(message.command[1:])
    
    unique_chat_ids = group_tracking_collection.distinct("_id") # Changed to use group_tracking_collection for groups
    
    sent_count = 0
    failed_count = 0
    logger.info(f"Starting broadcast to {len(unique_chat_ids)} chats. (Broadcast by @asbhaibsr)")
    for chat_id in unique_chat_ids:
        try:
            # Avoid sending broadcast to the private chat where the command was issued
            if chat_id == message.chat.id and message.chat.type == ChatType.PRIVATE: # Use ChatType enum
                continue 
            
            await client.send_message(chat_id, broadcast_text)
            sent_count += 1
            await asyncio.sleep(0.1) # Small delay to avoid FloodWait
        except Exception as e:
            logger.error(f"Failed to send broadcast to chat {chat_id}: {e}. (Broadcast by @asbhaibsr)")
            failed_count += 1
    
    await message.reply_text(MESSAGES[user_lang]["broadcast_sent"](sent_count, failed_count))
    await store_message(message)
    logger.info(f"Broadcast command processed by owner {message.from_user.id}. (Code by @asbhaibsr)")

@app.on_message(filters.command("stats") & filters.private)
async def stats_private_command(client: Client, message: Message):
    # Stats command handler for private chat. Logic by @asbhaibsr.
    if is_on_cooldown(message.from_user.id):
        return
    update_cooldown(message.from_user.id)

    user_lang = await get_user_language(message.from_user.id)

    if len(message.command) < 2 or message.command[1].lower() != "check":
        await message.reply_text(MESSAGES[user_lang]["stats_usage"])
        return

    total_messages = messages_collection.count_documents({})
    unique_group_ids = group_tracking_collection.count_documents({}) # Correctly counts documents in group_tracking_collection
    num_users = user_tracking_collection.count_documents({})

    stats_text = MESSAGES[user_lang]["bot_stats"](unique_group_ids, num_users, total_messages)
    await message.reply_text(stats_text)
    await store_message(message)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)
    logger.info(f"Private stats command processed for user {message.from_user.id}. (Code by @asbhaibsr)")

@app.on_message(filters.command("stats") & filters.group)
async def stats_group_command(client: Client, message: Message):
    # Stats command handler for groups. Logic by @asbhaibsr.
    if is_on_cooldown(message.from_user.id):
        return
    update_cooldown(message.from_user.id)

    user_lang = await get_user_language(message.from_user.id)

    if len(message.command) < 2 or message.command[1].lower() != "check":
        await message.reply_text(MESSAGES[user_lang]["stats_usage"])
        return

    total_messages = messages_collection.count_documents({})
    unique_group_ids = group_tracking_collection.count_documents({})
    num_users = user_tracking_collection.count_documents({})

    stats_text = MESSAGES[user_lang]["bot_stats"](unique_group_ids, num_users, total_messages)
    await message.reply_text(stats_text)
    await store_message(message)
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]: # Use ChatType enum
        await update_group_info(message.chat.id, message.chat.title)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)
    logger.info(f"Group stats command processed for user {message.from_user.id} in chat {message.chat.id}. (Code by @asbhaibsr)")

# --- Group Management Commands ---

@app.on_message(filters.command("groups") & filters.private)
async def list_groups_command(client: Client, message: Message):
    # List groups command. Admin only. Code by @asbhaibsr.
    if is_on_cooldown(message.from_user.id):
        return
    update_cooldown(message.from_user.id)

    user_lang = await get_user_language(message.from_user.id)

    # Convert OWNER_ID to str for comparison
    if str(message.from_user.id) != str(OWNER_ID):
        await message.reply_text(MESSAGES[user_lang]["owner_command_only"])
        return

    groups = list(group_tracking_collection.find({}))
    if not groups:
        await message.reply_text(MESSAGES[user_lang]["no_groups_found"])
        return

    group_list_text = MESSAGES[user_lang]["group_list_header"]
    for i, group in enumerate(groups):
        title = group.get("title", "Unknown Group")
        group_id = group.get("_id")
        added_on = group.get("added_on", "N/A").strftime("%Y-%m-%d %H:%M") if isinstance(group.get("added_on"), datetime) else "N/A"
        
        group_list_text += MESSAGES[user_lang]["group_list_item"](i, title, group_id, added_on)
        
    group_list_text += MESSAGES[user_lang]["group_list_footer"]
    await message.reply_text(group_list_text)
    await store_message(message)
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)
    logger.info(f"Groups list command processed by owner {message.from_user.id}. (Code by @asbhaibsr)")

@app.on_message(filters.command("leavegroup") & filters.private)
async def leave_group_command(client: Client, message: Message):
    # Leave group command. Admin only. Code by @asbhaibsr.
    if is_on_cooldown(message.from_user.id):
        return
    update_cooldown(message.from_user.id)

    user_lang = await get_user_language(message.from_user.id)

    # Convert OWNER_ID to str for comparison
    if str(message.from_user.id) != str(OWNER_ID):
        await message.reply_text(MESSAGES[user_lang]["owner_command_only"])
        return

    if len(message.command) < 2:
        await message.reply_text(MESSAGES[user_lang]["leave_group_usage"])
        return

    try:
        group_id_str = message.command[1]
        if not group_id_str.startswith('-100'):
            await message.reply_text(MESSAGES[user_lang]["invalid_group_id_format"])
            return

        group_id = int(group_id_str)
        
        await client.leave_chat(group_id)
        
        group_tracking_collection.delete_one({"_id": group_id})
        messages_collection.delete_many({"chat_id": group_id})
        logger.info(f"Considered cleaning earning data for users from left group {group_id}. (Code by @asbhaibsr)")

        await message.reply_text(MESSAGES[user_lang]["leave_group_success"](group_id))
        logger.info(f"Left group {group_id} and cleared its data. (Code by @asbhaibsr)")

    except ValueError:
        await message.reply_text(MESSAGES[user_lang]["invalid_group_id_format"]) # Reusing for generic invalid format
    except Exception as e:
        await message.reply_text(MESSAGES[user_lang]["leave_group_error"](e))
        logger.error(f"Error leaving group {group_id_str}: {e}. (Code by @asbhaibsr)")
    
    await store_message(message)
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)

# --- New Commands ---

@app.on_message(filters.command("cleardata") & filters.private)
async def clear_data_command(client: Client, message: Message):
    # Clear data command. Admin only. Code by @asbhaibsr.
    if is_on_cooldown(message.from_user.id):
        return
    update_cooldown(message.from_user.id)

    user_lang = await get_user_language(message.from_user.id)

    # Convert OWNER_ID to str for comparison
    if str(message.from_user.id) != str(OWNER_ID):
        await message.reply_text(MESSAGES[user_lang]["owner_command_only"])
        return

    if len(message.command) < 2:
        await message.reply_text(MESSAGES[user_lang]["clear_data_usage"])
        return

    percentage_str = message.command[1].strip('%')
    try:
        percentage = int(percentage_str)
        if not (1 <= percentage <= 100):
            await message.reply_text(MESSAGES[user_lang]["invalid_percentage"])
            return
    except ValueError:
        await message.reply_text(MESSAGES[user_lang]["invalid_percentage_format"])
        return

    total_messages = messages_collection.count_documents({})
    if total_messages == 0:
        await message.reply_text(MESSAGES[user_lang]["no_data_to_clear"])
        return

    messages_to_delete_count = int(total_messages * (percentage / 100))
    if messages_to_delete_count == 0 and percentage > 0:
        await message.reply_text(MESSAGES[user_lang]["low_data_clear_warning"](percentage))
        return
    elif messages_to_delete_count == 0 and percentage == 0:
        await message.reply_text(MESSAGES[user_lang]["zero_percent_clear"])
        return


    oldest_message_ids = []
    for msg in messages_collection.find({}) \
                                        .sort("timestamp", 1) \
                                        .limit(messages_to_delete_count):
        oldest_message_ids.append(msg['_id'])

    if oldest_message_ids:
        delete_result = messages_collection.delete_many({"_id": {"$in": oldest_message_ids}})
        await message.reply_text(MESSAGES[user_lang]["data_clear_success"](percentage, delete_result.deleted_count))
        logger.info(f"Cleared {delete_result.deleted_count} messages based on {percentage}% request. (Code by @asbhaibsr)")
    else:
        await message.reply_text(MESSAGES[user_lang]["no_data_found_to_clear"])
    
    await store_message(message)
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)

@app.on_message(filters.command("deletemessage") & filters.private)
async def delete_specific_message_command(client: Client, message: Message):
    # Delete specific message command. Admin only. Code by @asbhaibsr.
    if is_on_cooldown(message.from_user.id):
        return
    update_cooldown(message.from_user.id)

    user_lang = await get_user_language(message.from_user.id)

    # Convert OWNER_ID to str for comparison
    if str(message.from_user.id) != str(OWNER_ID):
        await message.reply_text(MESSAGES[user_lang]["owner_command_only"])
        return

    if len(message.command) < 2:
        await message.reply_text(MESSAGES[user_lang]["delete_message_usage"])
        return

    search_query = " ".join(message.command[1:])
    
    # Try to find message in current chat first
    message_to_delete = messages_collection.find_one({"chat_id": message.chat.id, "content": {"$regex": f"^{re.escape(search_query)}$", "$options": "i"}})

    if not message_to_delete:
        # If not found in current chat, search globally
        message_to_delete = messages_collection.find_one({"content": {"$regex": f"^{re.escape(search_query)}$", "$options": "i"}})

    if message_to_delete:
        delete_result = messages_collection.delete_one({"_id": message_to_delete["_id"]})
        if delete_result.deleted_count > 0:
            await message.reply_text(MESSAGES[user_lang]["message_delete_success"](search_query))
            logger.info(f"Deleted message with content: '{search_query}'. (Code by @asbhaibsr)")
        else:
            await message.reply_text(MESSAGES[user_lang]["message_not_found_in_db"])
    else:
        await message.reply_text(MESSAGES[user_lang]["message_not_found_globally"])
    
    await store_message(message)
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)

@app.on_message(filters.command("clearearning") & filters.private)
async def clear_earning_command(client: Client, message: Message):
    # New command to manually clear earning data. Only for owner.
    if is_on_cooldown(message.from_user.id):
        return
    update_cooldown(message.from_user.id)

    user_lang = await get_user_language(message.from_user.id)

    # Convert OWNER_ID to str for comparison
    if str(message.from_user.id) != str(OWNER_ID):
        await message.reply_text(MESSAGES[user_lang]["owner_command_only"])
        return

    await reset_monthly_earnings_manual()
    await message.reply_text(MESSAGES[user_lang]["earning_clear_success"])
    logger.info(f"Owner {message.from_user.id} manually triggered earning data reset. (Code by @asbhaibsr)")
    
    await store_message(message)
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)

@app.on_message(filters.command("restart") & filters.private)
async def restart_command(client: Client, message: Message):
    # Restart command. Admin only. Code by @asbhaibsr.
    if is_on_cooldown(message.from_user.id):
        return
    update_cooldown(message.from_user.id)

    user_lang = await get_user_language(message.from_user.id)

    # Convert OWNER_ID to str for comparison
    if str(message.from_user.id) != str(OWNER_ID):
        await message.reply_text(MESSAGES[user_lang]["owner_command_only"])
        return

    await message.reply_text(MESSAGES[user_lang]["restart_message"])
    logger.info("Bot is restarting... (System by @asbhaibsr)")
    # Give some time for the message to be sent
    await asyncio.sleep(0.5) 
    os.execl(sys.executable, sys.executable, *sys.argv) # This will restart the script (Code by @asbhaibsr)

# --- New chat members and left chat members ---
@app.on_message(filters.new_chat_members)
async def new_member_handler(client: Client, message: Message):
    # Handler for new members. Notifications by @asbhaibsr.
    logger.info(f"New chat members detected in chat {message.chat.id}. Bot ID: {client.me.id}. (Event handled by @asbhaibsr)")
    owner_lang = await get_user_language(int(OWNER_ID)) # Get owner's language for notifications

    for member in message.new_chat_members:
        logger.info(f"Processing new member: {member.id} ({member.first_name}) in chat {message.chat.id}. Is bot: {member.is_bot}. (Event handled by @asbhaibsr)")
        # Check if the bot itself was added to a group
        if member.id == client.me.id:
            if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]: # Use ChatType enum here
                logger.info(f"DEBUG: Bot {client.me.id} detected as new member in group {message.chat.id}. Calling update_group_info.") # NEW DEBUG LOG
                await update_group_info(message.chat.id, message.chat.title)
                logger.info(f"Bot joined new group: {message.chat.title} ({message.chat.id}). (Event handled by @asbhaibsr)")
                
                # Send notification to OWNER
                group_title = message.chat.title if message.chat.title else f"Unknown Group (ID: {message.chat.id})"
                added_by_user = message.from_user.first_name if message.from_user else "Unknown User"
                notification_message = MESSAGES[owner_lang]["new_group_alert"](
                    group_title,
                    message.chat.id,
                    f"{added_by_user} ({message.from_user.id if message.from_user else 'N/A'})",
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                )
                try:
                    await client.send_message(chat_id=OWNER_ID, text=notification_message)
                    logger.info(f"Owner notified about new group: {group_title}. (Notification by @asbhaibsr)")
                except Exception as e:
                    logger.error(f"Could not notify owner about new group {group_title}: {e}. (Notification error by @asbhaibsr)")
            return 

        if not member.is_bot: # Only for actual users, not other bots
            user_exists = user_tracking_collection.find_one({"_id": member.id})
            
            if message.chat.type == ChatType.PRIVATE and member.id == message.from_user.id and not user_exists: # Use ChatType enum
                user_name = member.first_name if member.first_name else "Naya User"
                user_username = f"@{member.username}" if member.username else "N/A"
                notification_message = MESSAGES[owner_lang]["new_user_private_alert"](
                    user_name,
                    member.id,
                    user_username,
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                )
                try:
                    await client.send_message(chat_id=OWNER_ID, text=notification_message)
                    logger.info(f"Owner notified about new private user: {user_name}. (Notification by @asbhaibsr)")
                except Exception as e:
                    logger.error(f"Could not notify owner about new private user {user_name}: {e}. (Notification error by @asbhaibsr)")
                
            elif message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP] and not user_exists: # Use ChatType enum
                user_name = member.first_name if member.first_name else "Naya User"
                user_username = f"@{member.username}" if member.username else "N/A"
                group_title = message.chat.title if message.chat.title else f"Unknown Group (ID: {message.chat.id})"
                notification_message = MESSAGES[owner_lang]["new_group_member_alert"](
                    user_name,
                    member.id,
                    user_username,
                    group_title,
                    message.chat.id,
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                )
                try:
                    await client.send_message(chat_id=OWNER_ID, text=notification_message)
                    logger.info(f"Owner notified about new group member: {user_name} in {group_title}. (Notification by @asbhaibsr)")
                except Exception as e:
                    logger.error(f"Could not notify owner about new group member {user_name} in {group_title}: {e}. (Notification error by @asbhaibsr)")
    
    await store_message(message)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)


@app.on_message(filters.left_chat_member)
async def left_member_handler(client: Client, message: Message):
    # Left member handler. Logic by @asbhaibsr.
    logger.info(f"Left chat member detected in chat {message.chat.id}. Left member ID: {message.left_chat_member.id}. Bot ID: {client.me.id}. (Event handled by @asbhaibsr)")
    owner_lang = await get_user_language(int(OWNER_ID)) # Get owner's language for notifications

    if message.left_chat_member and message.left_chat_member.id == client.me.id:
        if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]: # Use ChatType enum
            group_tracking_collection.delete_one({"_id": message.chat.id})
            messages_collection.delete_many({"chat_id": message.chat.id})
            earning_tracking_collection.update_many(
                {"_id": {"$in": [user["_id"] for user in earning_tracking_collection.find({})]}}, # All users
                {"$pull": {"groups": message.chat.id}} # Remove this group from user's group list (if you store one)
            )

            logger.info(f"Bot left group: {message.chat.title} ({message.chat.id}). Data cleared. (Code by @asbhaibsr)")
            # Send notification to OWNER
            group_title = message.chat.title if message.chat.title else f"Unknown Group (ID: {message.chat.id})"
            left_by_user = message.from_user.first_name if message.from_user else "Unknown User"
            notification_message = MESSAGES[owner_lang]["group_left_alert"](
                group_title,
                message.chat.id,
                f"{left_by_user} ({message.from_user.id if message.from_user else 'N/A'})",
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            )
            try:
                await client.send_message(chat_id=OWNER_ID, text=notification_message)
                logger.info(f"Owner notified about bot leaving group: {group_title}. (Notification by @asbhaibsr)")
            except Exception as e:
                logger.error(f"Could not notify owner about bot leaving group {group_title}: {e}. (Notification error by @asbhaibsr)")
            return # No need to store message if bot left

    await store_message(message)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)


@app.on_message(filters.text | filters.sticker)
async def handle_message_and_reply(client: Client, message: Message):
    # Main message handler for replies. Core logic by @asbhaibsr.
    if message.from_user and message.from_user.is_bot:
        logger.debug(f"Skipping message from bot user: {message.from_user.id}. (Handle message by @asbhaibsr)")
        return

    # Apply cooldown before processing message
    if message.from_user and is_on_cooldown(message.from_user.id):
        logger.debug(f"User {message.from_user.id} is on cooldown. Skipping message. (Cooldown by @asbhaibsr)")
        return
    if message.from_user:
        update_cooldown(message.from_user.id)

    logger.info(f"Processing message {message.id} from user {message.from_user.id if message.from_user else 'N/A'} in chat {message.chat.id} (type: {message.chat.type.name}). (Handle message by @asbhaibsr)")

    # Update group and user info regardless of whether it's a command or regular message
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]: # Use ChatType enum
        logger.info(f"DEBUG: Message from group/supergroup {message.chat.id}. Calling update_group_info.") # NEW DEBUG LOG
        await update_group_info(message.chat.id, message.chat.title)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)

    await store_message(message) # This is where the earning count increments

    # Only attempt to generate a reply if it's not a command message AND language is already set
    # Or if it's a command that needs to be handled
    if message.text and message.text.startswith('/'):
        # Commands are handled by their respective decorators, so we don't need to generate a reply here.
        # However, we need to ensure /start in private triggers language selection if not set.
        # This is already handled by start_private_command, so no specific action here.
        pass
    else:
        # For non-command messages, check if language is set.
        # If it's a private chat and language is not set, we might need to prompt for language first.
        # However, the /start command already handles this.
        # For regular messages, we assume the language is set or defaults to English.
        # So proceed with generating reply.
        logger.info(f"Attempting to generate reply for chat {message.chat.id}. (Logic by @asbhaibsr)")
        reply_doc = await generate_reply(message)
        
        if reply_doc:
            try:
                if reply_doc.get("type") == "text":
                    await message.reply_text(reply_doc["content"])
                    logger.info(f"Replied with text: {reply_doc['content']}. (System by @asbhaibsr)")
                elif reply_doc.get("type") == "sticker" and reply_doc.get("sticker_id"):
                    await message.reply_sticker(reply_doc["sticker_id"])
                    logger.info(f"Replied with sticker: {reply_doc['sticker_id']}. (System by @asbhaibsr)")
                else:
                    logger.warning(f"Reply document found but no content/sticker_id: {reply_doc}. (System by @asbhaibsr)")
            except Exception as e:
                logger.error(f"Error sending reply for message {message.id}: {e}. (System by @asbhaibsr)")
        else:
            logger.info("No suitable reply found. (System by @asbhaibsr)")


# --- Main entry point ---
if __name__ == "__main__":
    # Main bot execution point. Designed by @asbhaibsr.
    logger.info("Starting Flask health check server in a separate thread... (Code by @asbhaibsr)")
    flask_thread = threading.Thread(target=run_flask_app)
    flask_thread.start()

    logger.info("Starting Pyrogram bot... (Code by @asbhaibsr)")
    
    # Pyrogram app.run() मेथड को सीधे कॉल करें. यह Pyrogram को शुरू और आइडल रखेगा.
    app.run()
    
    # End of bot code. Thank you for using! Made with ❤️ by @asbhaibsr
