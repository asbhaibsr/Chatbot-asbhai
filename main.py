# main.py

import threading
import logging
from pyrogram import idle
import nltk
import os
import sys

# NLTK data download check and setup
try:
    # First, try to find the lexicon. This will raise a LookupError if not found.
    nltk.data.find('sentiment/vader_lexicon.zip')
    print("vader_lexicon is already downloaded.")
except LookupError:
    # If a LookupError occurs, it means the data needs to be downloaded.
    print("vader_lexicon not found. Downloading now...")

    # Set the NLTK data path to a writeable directory before downloading.
    # This is important for platforms like Koyeb.
    data_dir = '/usr/share/nltk_data'
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    nltk.data.path.append(data_dir)
    
    # Download the lexicon to the specified path.
    nltk.download('vader_lexicon', download_dir=data_dir)
    print("Download complete.")
except Exception as e:
    # Handle any other unexpected errors gracefully.
    print(f"An unexpected error occurred: {e}", file=sys.stderr)
    sys.exit(1)

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
