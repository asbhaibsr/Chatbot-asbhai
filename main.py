import threading
import logging
from pyrogram import idle
import nltk
import os
import sys
import asyncio # New import for async functionality

# NLTK data download check and setup
try:
    data_dir = os.path.join(os.getcwd(), '.nltk_data')
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    nltk.data.path.append(data_dir)

    nltk.data.find('sentiment/vader_lexicon.zip')
    print("vader_lexicon is already downloaded.")
except LookupError:
    print("vader_lexicon not found. Downloading now...")
    
    nltk.download('vader_lexicon', download_dir=data_dir)
    print("Download complete.")
except Exception as e:
    print(f"An unexpected error occurred: {e}", file=sys.stderr)
    sys.exit(1)

# Import necessary components from other files
from config import app, logger, flask_app
from web import run_flask_app
from utils import initialize_bot_id # 🌟 New import for Bot ID initialization

# It's important to import commands and events so Pyrogram can register the handlers
import commands
import events
import broadcast_handler 

# 🌟 FIX 3: Pyrogram client start logic for Bot ID initialization
async def start_bot_and_idle():
    """Starts the bot, initializes the Bot ID, and keeps the bot running."""
    await app.start()
    
    # Bot ID initialize करें क्लाइंट शुरू होने के बाद
    await initialize_bot_id()
    
    logger.info("Pyrogram bot started successfully. Entering idle mode...")
    await idle()
    
    await app.stop()
    logger.info("Pyrogram bot stopped.")


if __name__ == "__main__":
    logger.info("Starting Flask health check server in a separate thread...")
    flask_thread = threading.Thread(target=run_flask_app)
    flask_thread.start()

    logger.info("Starting Pyrogram bot...")
    
    # 🌟 FIX 4: Use asyncio.run to execute the async startup function
    try:
        # Check if an event loop is already running (usually only matters in complex environments)
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(start_bot_and_idle())
        else:
            loop.run_until_complete(start_bot_and_idle())
    except Exception as e:
        logger.error(f"Fatal error during bot startup: {e}")
        
    # End of bot code. Thank you for using! Made with ❤️ by @asbhaibsr
