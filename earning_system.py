import logging
from datetime import datetime
import pytz

# Assuming these are imported from main.py's global scope or passed
# For a standalone file, you'd need to pass these or re-import/re-initialize
# For simplicity, we'll assume they are available or passed as arguments.
# In a real setup, you might pass `db_tracking` or `earning_tracking_collection`
# to these functions if they are in a separate module.

# Placeholder for collections if this file is run standalone, normally passed from main
earning_tracking_collection = None
group_tracking_collection = None
user_tracking_collection = None
reset_status_collection = None
app = None # Placeholder for Pyrogram client

# Logger for this module
logger = logging.getLogger(__name__)

def initialize_earning_system(earning_coll, group_coll, user_coll, reset_coll, pyrogram_app):
    """Initializes collections and app object for this module."""
    global earning_tracking_collection, group_tracking_collection, user_tracking_collection, reset_status_collection, app
    earning_tracking_collection = earning_coll
    group_tracking_collection = group_coll
    user_tracking_collection = user_coll
    reset_status_collection = reset_coll
    app = pyrogram_app

async def get_top_earning_users():
    pipeline = [
        {"$match": {"group_message_count": {"$gt": 0}}},
        {"$sort": {"group_message_count": -1}},
    ]

    top_users_data = list(earning_tracking_collection.aggregate(pipeline))
    logger.info(f"Fetched top earning users: {len(top_users_data)} results. (Earning system by @asbhaibsr)")

    top_users_details = []
    for user_data in top_users_data:
        top_users_details.append({
            "user_id": user_data["_id"],
            "first_name": user_data.get("first_name", "Unknown User"),
            "username": user_data.get("username"),
            "message_count": user_data["group_message_count"],
            "last_active_group_id": user_data.get("last_active_group_id"),
            "last_active_group_title": user_data.get("last_active_group_title"),
            "last_active_group_username": user_data.get("last_active_group_username")
        })
    return top_users_details

async def reset_monthly_earnings_manual():
    logger.info("Manually resetting monthly earnings...")
    now = datetime.now(pytz.timezone('Asia/Kolkata'))

    try:
        earning_tracking_collection.update_many(
            {},
            {"$set": {"group_message_count": 0}}
        )
        logger.info("Monthly earning message counts reset successfully by manual command. (Earning system by @asbhaibsr)")

        reset_status_collection.update_one(
            {"_id": "last_manual_reset_date"},
            {"$set": {"last_reset_timestamp": now}},
            upsert=True
        )
        logger.info(f"Manual reset status updated. (Earning system by @asbhaibsr)")

    except Exception as e:
        logger.error(f"Error resetting monthly earnings manually: {e}. (Earning system by @asbhaibsr)")

