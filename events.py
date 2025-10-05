# main.py

import threading
import logging
from pyrogram import idle, Client
from pyrogram.enums import ParseMode
import nltk
import os
import sys
import asyncio # New import for running async code
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
# OWNER_ID ko configuration se import karna zaruri hai.
from config import app, logger, flask_app, OWNER_ID
from web import run_flask_app

# It's important to import commands and events so Pyrogram can register the handlers
import commands
import events
import broadcast_handler # 🌟 नई ब्रॉडकास्ट फ़ाइल इम्पोर्ट की गई 🌟

# ----------------------------------------------------
# ✨ NEW: Bot Startup Notification Function (Replaced @app.on_ready) ✨
# ----------------------------------------------------

async def send_startup_notification(client: Client):
    """
    Sends a startup notification to the OWNER_ID after the client starts.
    This function will be run manually after app.start().
    """
    try:
        # Start the client manually to perform the action
        await client.start() 
        logger.info("Pyrogram client manually started for startup action.")

        # Get bot's own information
        me = await client.get_me()
        
        notification_text = (
            f"🟢 **BOT ALIVE!** 🤖\n"
            f"The bot has been successfully deployed and is now live!\n\n"
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
    finally:
        # Stop the client manually if we started it manually.
        # However, since app.run() will manage the lifecycle,
        # we let app.run() handle the continuous running part. 
        # The main app.run() call handles the continuous event loop.
        pass # We rely on app.run() below to keep it running.

# ----------------------------------------------------
# ----------------------------------------------------


if __name__ == "__main__":
    logger.info("Starting Flask health check server in a separate thread...")
    flask_thread = threading.Thread(target=run_flask_app)
    flask_thread.start()

    logger.info("Starting Pyrogram bot...")
    
    # Run the startup notification function *before* app.run()
    # We use a separate event loop run_until_complete to execute the async function
    # inside the synchronous __main__ block, then app.run() takes over.
    try:
        # Using a quick manual start/stop cycle inside the main loop to send the message
        # app.run() is the Pyrogram v2 way to start the bot and its handlers.
        # We will use asyncio.run to execute the async notification logic.
        asyncio.run(send_startup_notification(app))
        
    except Exception as e:
        # Ignore error if the bot is already running or start/stop fails, and proceed with app.run()
        logger.warning(f"Startup notification setup failed (expected if bot runs immediately): {e}. Proceeding with app.run().")


    # This is the main blocking call that keeps the bot running
    app.run() 
    
    # Keep the bot running indefinitely
    idle()

    # End of bot code. Thank you for using! Made with ❤️ by @asbhaibsr
