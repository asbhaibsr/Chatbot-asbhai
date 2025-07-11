# database/mongo_setup.py

from pymongo import MongoClient
from datetime import datetime, timedelta
import logging

from config import MONGO_URI_MESSAGES, MONGO_URI_BUTTONS, MONGO_URI_TRACKING
from utils.helpers import logger # Import the configured logger

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
    logger.info("MongoDB (Tracking, Earning & Biolink Exceptions) connection successful. Credit: @asbhaibsr")

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

except Exception as e:
    logger.error(f"Failed to connect to one or more MongoDB instances: {e}. Designed by @asbhaibsr")
    exit(1)

# You can add a function here to close connections if needed on graceful shutdown
def close_mongo_connections():
    if client_messages:
        client_messages.close()
        logger.info("MongoDB (Messages) connection closed.")
    if client_buttons:
        client_buttons.close()
        logger.info("MongoDB (Buttons) connection closed.")
    if client_tracking:
        client_tracking.close()
        logger.info("MongoDB (Tracking) connection closed.")
