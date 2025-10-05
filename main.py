# main.py

import threading
import logging
from pyrogram import idle, Client
from pyrogram.enums import ParseMode
import nltk
import os
import sys
import asyncio 
from datetime import datetime

# NLTK data download check and setup
try:
    # Set the NLTK data path to a writeable directory within the workspace.
    data_dir = os.path.join(os.getcwd(), '.nltk_data')
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    nltk.data.path.append(data_dir)

    # First, try to find the lexicon. This will raise a LookupError if not found.
    nltk.data.find('sentiment/vader_lexicon.zip')
    print("vader_lexicon is already downloaded.")
except LookupError:
    # If a LookupError occurs, it means the data needs to be downloaded.
    print("vader_lexicon not found. Downloading now...")
    
    # Set the NLTK data path and then download the lexicon.
    nltk.download('vader_lexicon', download_dir=data_dir)
    print("Download complete.")
except Exception as e:
    # Handle any other unexpected errors gracefully.
    print(f"An unexpected error occurred during NLTK setup: {e}", file=sys.stderr)
    sys.exit(1)

# Import necessary components from other files
# Note: Handlers are automatically registered upon these imports.
from config import app, logger, flask_app, OWNER_ID
from web import run_flask_app

# It's important to import commands and events so Pyrogram can register the handlers
# 💡 NOTE: The handlers are registered when these modules are imported!
import commands
import events
import broadcast_handler 

# ----------------------------------------------------
# ✨ Bot Startup Notification Function ✨
# ----------------------------------------------------

async def send_startup_notification(client: Client):
    """
    Sends a startup notification to the OWNER_ID.
    """
    try:
        # Get bot's own information
        me = await client.get_me()
        
        notification_text = (
            f"🟢 **BOT ALIVE!** 🤖\n"
            f"The bot has been successfully deployed and is now fully operational!\n\n"
            f"• **Bot Name:** {me.first_name}\n"
            f"• **Username:** @{me.username}\n"
            f"• **Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        )
        
        await client.send_message(
            chat_id=OWNER_ID,
            text=notification_text,
            parse_mode=ParseMode.MARKDOWN
        )
        logger.info("Sent 'I am alive' message to owner.")

    except Exception as e:
        logger.error(f"Failed to send startup notification to owner: {e}")

# ----------------------------------------------------
# ✨ Main Execution Function to Handle Async Startup ✨
# ----------------------------------------------------

async def main_bot_runner():
    """
    Handles the entire asynchronous lifecycle: startup, notification, and idling.
    """
    logger.info("Starting Pyrogram bot and connecting to Telegram...")
    
    # 1. Start the client and connect to Telegram. 
    # This also activates the handlers imported from commands, events, etc.
    await app.start()
    logger.info("Pyrogram client successfully connected.")

    # 2. Run the startup notification logic immediately after connection
    await send_startup_notification(app)
    
    # 3. Keep the bot running indefinitely, allowing it to process commands and messages
    logger.info("Bot is now running and awaiting commands/messages.")
    await idle()
    
    # 4. Stop the client gracefully when idle() is interrupted
    logger.info("Stopping Pyrogram client.")
    await app.stop()


if __name__ == "__main__":
    logger.info("Starting Flask health check server in a separate thread...")
    flask_thread = threading.Thread(target=run_flask_app)
    flask_thread.start()

    # The main logic is encapsulated in the async main_bot_runner()
    # Use asyncio.run() to launch the single main coroutine.
    try:
        asyncio.run(main_bot_runner())
    except KeyboardInterrupt:
        logger.info("Bot manually stopped via KeyboardInterrupt.")
    except Exception as e:
        logger.error(f"An unhandled error occurred in the main execution: {e}")

    logger.info("Bot execution finished. Thank you for using! Made with ❤️ by @asbhaibsr")
