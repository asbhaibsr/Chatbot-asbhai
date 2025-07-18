# main.py

import threading
import logging
from pyrogram import idle

# Import necessary components from other files
from config import app, logger, flask_app
from web import run_flask_app
# It's important to import commands and events so Pyrogram can register the handlers
import commands
import events

if __name__ == "__main__":
    logger.info("Starting Flask health check server in a separate thread...")
    flask_thread = threading.Thread(target=run_flask_app)
    flask_thread.start()

    logger.info("Starting Pyrogram bot...")
    app.run()
    
    # Keep the bot running indefinitely
    idle()

    # End of bot code. Thank you for using! Made with ❤️ by @asbhaibsr
