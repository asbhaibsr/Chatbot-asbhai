from telegram.ext import Application, CommandHandler
from bot_handlers import start, help_command
from config import TELEGRAM_TOKEN
from keep_alive import keep_alive  # optional for hosting

def main():
    keep_alive()
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    print("Bot is running...")
    app.run_polling()

if __name__ == '__main__':
    main()

