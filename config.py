# config.py

import os
import re
import logging

# --- Logger Setup ---
# Logger will be configured once in utils/helpers.py, but defined here for global access if needed
# For now, just importing logger setup from helpers.py to ensure it's initialized correctly there.

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
UPDATE_CHANNEL_USERNAME = "asbhai_bsr"
ASBHAI_USERNAME = "asbhaibsr" # Owner's username for contact
ASFILTER_BOT_USERNAME = "asfilter_bot" # The bot for premium rewards
BOT_PHOTO_URL = "https://envs.sh/FU3.jpg" # Consider updating this URL if it's generic
REPO_LINK = "https://github.com/asbhaibsr/Chatbot-asbhai.git"

# Regex for common URL patterns including t.me and typical link formats
URL_PATTERN = re.compile(r"(?:https?://|www\.|t\.me/)[^\s/$.?#].[^\s]*", re.IGNORECASE)

# Cooldown time for commands (seconds)
COMMAND_COOLDOWN_TIME = 3

# Cooldown time for general message replies (seconds)
MESSAGE_REPLY_COOLDOWN_TIME = 8
