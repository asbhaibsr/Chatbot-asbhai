# main.py

import threading
import logging
from pyrogram import idle
import nltk # NLTK library import kiya
import os # OS library import kiya

# NLTK data download check
# Agar 'vader_lexicon' pehle se downloaded nahi hai, toh download karega.
# Yeh step aapke bot ko kisi bhi naye environment mein chalne ke liye aasan banata hai.
try:
    nltk.data.find('sentiment/vader_lexicon.zip')
except nltk.downloader.DownloadError:
    print("vader_lexicon not found, downloading now...")
    # NLTK data ke liye ek path set karein taaki woh usko sahi jagah par store kare.
    nltk.download('vader_lexicon', download_dir='/usr/share/nltk_data')
    os.environ['NLTK_DATA'] = '/usr/share/nltk_data'
    print("Download complete.")

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
