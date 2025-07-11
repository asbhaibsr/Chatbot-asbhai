# main.py

import os
import asyncio
import threading
import time
import logging
import sys

from pyrogram import Client, filters
from pyrogram.enums import ChatType, ParseMode

from flask import Flask, request, jsonify

# Import configurations and database setups
from config import (
    API_ID, API_HASH, BOT_TOKEN, OWNER_ID, UPDATE_CHANNEL_USERNAME,
    ASBHAI_USERNAME, ASFILTER_BOT_USERNAME, BOT_PHOTO_URL, REPO_LINK
)
from database.mongo_setup import (
    messages_collection, buttons_collection, group_tracking_collection,
    user_tracking_collection, earning_tracking_collection, reset_status_collection,
    biolink_exceptions_collection,
    client_messages, client_buttons, client_tracking
)
from utils.helpers import (
    logger, is_on_command_cooldown, update_command_cooldown,
    can_reply_to_chat, update_message_reply_cooldown,
    send_and_auto_delete_reply, delete_after_delay_for_message
)

# Import all handlers
from handlers.command_handlers import (
    start_private_command, start_group_command, top_users_command,
    broadcast_command, stats_private_command, stats_group_command,
    list_groups_command, leave_group_command, clear_data_command,
    delete_specific_message_command, clear_earning_command,
    restart_command, clear_my_data_command
)
from handlers.callback_handlers import callback_handler, handle_clearall_dbs_callback
from handlers.message_handlers import (
    handle_message_and_reply, new_member_handler, left_member_handler
)
from moderation.mod_handlers import (
    toggle_chat_command, toggle_linkdel_command,
    toggle_biolinkdel_command, allow_biolink_user_command,
    toggle_usernamedel_command, clear_all_dbs_command_initiate
)


# --- Pyrogram Client ---
app = Client(
    "self_learning_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# --- Flask App Setup ---
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Bot is running! Developed by @asbhaibsr. Support: @aschat_group"

@flask_app.route('/health')
def health_check():
    return jsonify({"status": "ok", "message": "Bot is alive and healthy! Designed by @asbhaibsr"}), 200

def run_flask_app():
    flask_app.run(host='0.0.0.0', port=os.environ.get('PORT', 8000), debug=False)


# --- Register Pyrogram Event Handlers ---
# Commands
app.on_message(filters.command("start") & filters.private)(start_private_command)
app.on_message(filters.command("start") & filters.group)(start_group_command)
app.on_message(filters.command("topusers") & (filters.private | filters.group))(top_users_command)
app.on_message(filters.command("broadcast") & filters.private)(broadcast_command)
app.on_message(filters.command("stats") & filters.private)(stats_private_command)
app.on_message(filters.command("stats") & filters.group)(stats_group_command)
app.on_message(filters.command("groups") & filters.private)(list_groups_command)
app.on_message(filters.command("leavegroup") & filters.private)(leave_group_command)
app.on_message(filters.command("cleardata") & filters.private)(clear_data_command)
app.on_message(filters.command("deletemessage") & filters.private)(delete_specific_message_command)
app.on_message(filters.command("clearearning") & filters.private)(clear_earning_command)
app.on_message(filters.command("restart") & filters.private)(restart_command)
app.on_message(filters.command("chat") & filters.group)(toggle_chat_command)
app.on_message(filters.command("linkdel") & filters.group)(toggle_linkdel_command)
app.on_message(filters.command("biolinkdel") & filters.group)(toggle_biolinkdel_command)
app.on_message(filters.command("biolink") & filters.group)(allow_biolink_user_command)
app.on_message(filters.command("usernamedel") & filters.group)(toggle_usernamedel_command)
app.on_message(filters.command("clearall") & filters.private)(clear_all_dbs_command_initiate)
app.on_message(filters.command("clearmydata"))(clear_my_data_command)


# Callback Queries
app.on_callback_query(filters.regex("^(buy_git_repo|show_earning_leaderboard|show_help_menu|show_earning_rules)$"))(callback_handler)
app.on_callback_query(filters.regex("^(confirm_clearall_dbs|cancel_clearall_dbs)$"))(handle_clearall_dbs_callback)

# General Message Handling and New/Left Members
app.on_message(filters.new_chat_members)(new_member_handler)
app.on_message(filters.left_chat_member)(left_member_handler)
app.on_message(filters.text | filters.sticker | filters.photo | filters.video | filters.document)(handle_message_and_reply)


# --- Main entry point ---
if __name__ == "__main__":
    logger.info("Starting Flask health check server in a separate thread... (Code by @asbhaibsr)")
    flask_thread = threading.Thread(target=run_flask_app)
    flask_thread.start()

    logger.info("Starting Pyrogram bot... (Code by @asbhaibsr)")

    app.run()

    # End of bot code. Thank you for using! Made with ❤️ by @asbhaibsr
