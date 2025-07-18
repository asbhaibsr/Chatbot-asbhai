# config.py

import os
import asyncio
import threading
import time
import logging
import re
import random
import sys
from datetime import datetime, timedelta

import pytz
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.raw.functions.messages import SetTyping
from pyrogram.raw.types import SendMessageTypingAction
from pyrogram.enums import ChatType, ChatMemberStatus, ParseMode

from pymongo import MongoClient
from flask import Flask, request, jsonify

# --- Logger Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Environment Variables ---
BOT_TOKEN = os.getenv("BOT_TOKEN")

MONGO_URI_MESSAGES = os.getenv("MONGO_URI_MESSAGES")
MONGO_URI_BUTTONS = os.getenv("MONGO_URI_BUTTONS")
MONGO_URI_TRACKING = os.getenv("MONGO_URI_TRACKING")

OWNER_ID = int(os.getenv("OWNER_ID")) # Ensure OWNER_ID is an integer for comparison

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

# --- Constants ---
MAX_MESSAGES_THRESHOLD = 100000
PRUNE_PERCENTAGE = 0.30
UPDATE_CHANNEL_USERNAME = "earntalkchatcash"
ASBHAI_USERNAME = "asbhaibsr" # Owner's username for contact
ASFILTER_BOT_USERNAME = "asfilter_bot" # The bot for premium rewards
BOT_PHOTO_URL = "https://envs.sh/FU3.jpg" # Consider updating this URL if it's generic
REPO_LINK = "https://github.com/asbhaibsr/Chatbot-asbhai.git"

# Regex for common URL patterns including t.me and typical link formats
URL_PATTERN = re.compile(r"(?:https?://|www\.|t\.me/)[^\s/$.?#].[^\s]*", re.IGNORECASE)

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
    earning_tracking_collection = db_tracking.monthly_earnings_data
    reset_status_collection = db_tracking.reset_status
    biolink_exceptions_collection = db_tracking.biolink_exceptions # For biolink deletion exceptions
    owner_taught_responses_collection = db_tracking.owner_taught_responses 
    conversational_learning_collection = db_tracking.conversational_learning 
    
    logger.info("MongoDB (Tracking, Earning, Biolink Exceptions, Learning Data) connection successful. Credit: @asbhaibsr")

    # Create indexes for efficient querying if they don't exist
    messages_collection.create_index([("timestamp", 1)])
    messages_collection.create_index([("user_id", 1)])
    earning_tracking_collection.create_index([("group_message_count", -1)])
    # Ensure bot_enabled field exists for all groups, default to True
    group_tracking_collection.update_many(
        {"bot_enabled": {"$exists": False}},
        {"$set": {"bot_enabled": True}}
    )
    # Ensure new flags exist for all groups, default to False
    group_tracking_collection.update_many(
        {"linkdel_enabled": {"$exists": False}},
        {"$set": {"linkdel_enabled": False}}
    )
    group_tracking_collection.update_many(
        {"biolinkdel_enabled": {"$exists": False}},
        {"$set": {"biolinkdel_enabled": False}}
    )
    group_tracking_collection.update_many(
        {"usernamedel_enabled": {"$exists": False}},
        {"$set": {"usernamedel_enabled": False}}
    )

    # NEW: Create indexes for learning collections
    owner_taught_responses_collection.create_index([("trigger", 1)])
    conversational_learning_collection.create_index([("trigger", 1)])


except Exception as e:
    logger.error(f"Failed to connect to one or more MongoDB instances: {e}. Designed by @asbhaibsr")
    exit(1)

# --- Pyrogram Client ---
app = Client(
    "self_learning_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# --- Cooldown dictionary (for commands) ---
user_cooldowns = {}
COMMAND_COOLDOWN_TIME = 3 # seconds (for commands like /start, /topusers)

# --- Message Reply Cooldown (for general messages) ---
chat_message_cooldowns = {}
MESSAGE_REPLY_COOLDOWN_TIME = 8 # seconds (8 seconds)

# --- Flask App Setup ---
flask_app = Flask(__name__)
