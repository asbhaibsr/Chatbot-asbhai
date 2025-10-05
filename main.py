# main.py

import threading
import logging
from pyrogram import idle, Client, filters
from pyrogram.enums import ParseMode
import nltk
import os
import sys
from datetime import datetime

# NLTK data download check and setup
try:
    # Set the NLTK data path to a writeable directory within the workspace.
    # This is important for platforms like Koyeb where root access is limited.
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
# ✨ NEW: Bot Startup Notification (I am alive) ✨
# ----------------------------------------------------

@app.on_ready()
async def bot_is_alive(client: Client):
    """
    Sends a startup notification to the OWNER_ID when the bot successfully connects.
    """
    try:
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
        # Agar OWNER_ID galat hai ya owner ne bot ko block kar diya hai, toh message fail ho jayega.
        logger.error(f"Failed to send startup notification to owner: {e}")

# ----------------------------------------------------
# ----------------------------------------------------


if __name__ == "__main__":
    logger.info("Starting Flask health check server in a separate thread...")
    flask_thread = threading.Thread(target=run_flask_app)
    flask_thread.start()

    logger.info("Starting Pyrogram bot...")
    # client.run() ke bajaye app.run() use karen
    app.run()
    
    # Keep the bot running indefinitely
    idle()

    # End of bot code. Thank you for using! Made with ❤️ by @asbhaibsr
