# main.py

import threading
import logging
from pyrogram import idle
import nltk
import os
import sys

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
    print(f"An unexpected error occurred: {e}", file=sys.stderr)
    sys.exit(1)

# Import necessary components from other files
from config import app, logger, flask_app
from web import run_flask_app
from utils import check_and_perform_monthly_reset # 🟢 नया इम्पोर्ट 🟢

# It's important to import commands and events so Pyrogram can register the handlers
import commands
import events
import broadcast_handler # 🌟 नई ब्रॉडकास्ट फ़ाइल इम्पोर्ट की गई 🌟

if __name__ == "__main__":
    
    # --- 🟢 नया: स्टार्टअप टास्क चलाने के लिए async main 🟢 ---
    async def main():
        global app
        async with app:
            logger.info("Bot started. Running startup tasks...")
            # ऑटो-रीसेट चेक चलाएँ
            await check_and_perform_monthly_reset(app)
            logger.info("Startup tasks complete. Bot is now idle.")
            await idle()
    # --- 🟢 नए कोड का अंत 🟢 ---

    logger.info("Starting Flask health check server in a separate thread...")
    flask_thread = threading.Thread(target=run_flask_app)
    flask_thread.start()

    logger.info("Starting Pyrogram bot and running startup tasks...")
    # app.run() # <-- इसे हटा दिया गया है
    
    # --- 🟢 नया: async main फ़ंक्शन चलाएँ 🟢 ---
    app.run(main())
    
    # idle() # <-- यह अब main() के अंदर है, इसलिए यहाँ से हटा दें

    # End of bot code. Thank you for using! Made with ❤️ by @asbhaibsr
