import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatType, ChatMemberStatus

logger = logging.getLogger(__name__)

# Global variables (will be passed from main.py or accessed if truly global)
# Similar to clone_bot_handler, these should ideally be passed as arguments.
# For now, we'll assume they are imported or globally available from main.py's context.

OWNER_ID = None
group_configs_collection = None
store_message = None # This will be passed from main.py

def set_global_vars(owner_id, group_configs_col, sm_func):
    global OWNER_ID, group_configs_collection, store_message
    OWNER_ID = owner_id
    group_configs_collection = group_configs_col
    store_message = sm_func


# Helper function to check if user is owner
def is_owner(user_id):
    return str(user_id) == str(OWNER_ID)

# New decorator for group admins (including owner)
async def group_admin_filter(_, client: Client, message: Message):
    if not message.from_user:
        return False

    user_id = message.from_user.id
    chat_id = message.chat.id

    if is_owner(user_id):
        return True

    if message.chat.type == ChatType.PRIVATE:
        return False

    try:
        member = await client.get_chat_member(chat_id, user_id)
        if member.status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
            return True
        else:
            return False
    except Exception as e:
        logger.error(f"Error checking admin status for user {user_id} in chat {chat_id}: {e}")
        return False

# GROUP ADMIN COMMANDS (BAN, UNBAN, KICK, PIN, UNPIN)
async def perform_chat_action(client: Client, message: Message, action_type: str):
    if not message.reply_to_message and len(message.command) < 2:
        await message.reply_text(f"Malik, kripya us user ko reply karein jise {action_type} karna hai, ya user ID/username dein.\nUpyog: `/{action_type} <user_id_or_username>` ya message ko reply karein. Jaldi karo, mujhe masti karni hai! 💃")
        if message.from_user and store_message:
            await store_message(message, is_bot_sent=False)
        return

    target_user_id = None
    if message.reply_to_message and message.reply_to_message.from_user:
        target_user_id = message.reply_to_message.from_user.id
    elif len(message.command) >= 2:
        try:
            target_user_id = int(message.command[1])
        except ValueError:
            target_user_id = message.command[1]

    if not target_user_id:
        await message.reply_text("Malik, main us user ko dhundh nahi pa rahi hoon! Kya tumne sahi ID ya username diya? 🤔")
        if message.from_user and store_message:
            await store_message(message, is_bot_sent=False)
        return

    try:
        me_in_chat = await client.get_chat_member(message.chat.id, client.me.id)
        if not me_in_chat.privileges or (
            (not me_in_chat.privileges.can_restrict_members) and action_type in ["ban", "unban", "kick"]
        ) or (
            (not me_in_chat.privileges.can_pin_messages) and action_type in ["pin", "unpin"]
        ):
            await message.reply_text(f"Malik, mujhe {action_type} karne ke liye zaroori permissions ki zaroorat hai. Please de do na! 🙏")
            if message.from_user and store_message:
                await store_message(message, is_bot_sent=False)
            return
    except Exception as e:
        logger.error(f"Error checking bot permissions in chat {message.chat.id}: {e}", exc_info=True)
        await message.reply_text("Malik, permissions check karte samay error aaya. Kripya सुनिश्चित करें ki bot ko sahi permissions hain. 🥺")
        if message.from_user and store_message:
            await store_message(message, is_bot_sent=False)
        return

    try:
        if action_type == "ban":
            await client.ban_chat_member(message.chat.id, target_user_id)
            await message.reply_text(f"User {target_user_id} ko ban kar diya gaya, Malik! Ab koi shor nahi! 🤫")
        elif action_type == "unban":
            await client.unban_chat_member(message.chat.id, target_user_id)
            await message.reply_text(f"User {target_user_id} ko unban kar diya gaya, Malik! Shayad usne sabak seekh liya hoga! 😉")
        elif action_type == "kick":
            await client.kick_chat_member(message.chat.id, target_user_id)
            await message.reply_text(f"User {target_user_id} ko kick kar diya gaya, Malik! Tata bye bye! 👋")
        elif action_type == "pin":
            if not message.reply_to_message:
                await message.reply_text("Malik, pin karne ke liye kripya ek message ko reply karein. Main confusion mein pad jaungi! 😵‍💫")
                if message.from_user and store_message:
                    await store_message(message, is_bot_sent=False)
                return
            await client.pin_chat_message(message.chat.id, message.reply_to_message.id)
            await message.reply_text("Message pin kar diya gaya, Malik! Ab sabko dikhega! ✨")
        elif action_type == "unpin":
            await client.unpin_chat_messages(message.chat.id)
            await message.reply_text("Sabhi pinned messages unpin kar diye gaye, Malik! Ab group free hai! 🥳")
    except Exception as e:
        await message.reply_text(f"Malik, {action_type} karte samay error aaya: {e}. Mujhse ho nahi pa raha! 😭")
        logger.error(f"Error performing {action_type} by user {message.from_user.id if message.from_user else 'None'}: {e}", exc_info=True)
    if message.from_user and store_message:
        await store_message(message, is_bot_sent=False)

# --- CUSTOM WELCOME MESSAGE ---
async def set_welcome_command(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("Malik, kripya welcome message dein.\nUpyog: `/setwelcome Aapka naya welcome message {user} {chat_title}`. Naye members ko surprise karte hain! 🥳")
        if message.from_user and store_message:
            await store_message(message, is_bot_sent=False)
        return
    welcome_msg_text = " ".join(message.command[1:])
    if group_configs_collection is None:
        await message.reply_text("Maaf karna, welcome message set nahi kar payi. Database (Commands/Settings DB) connect nahi ho paya hai. 🥺")
        if message.from_user and store_message:
            await store_message(message, is_bot_sent=False)
        return

    group_configs_collection.update_one(
        {"chat_id": message.chat.id},
        {"$set": {"welcome_message": welcome_msg_text}},
        upsert=True
    )
    await message.reply_text("Naya welcome message set kar diya gaya hai, Malik! Jab naya member aayega, toh main yahi pyaara message bhejoongi! 🥰")
    if message.from_user and store_message:
        await store_message(message, is_bot_sent=False)

async def get_welcome_command(client: Client, message: Message):
    config = None
    if group_configs_collection is not None:
        config = group_configs_collection.find_one({"chat_id": message.chat.id})

    if config and "welcome_message" in config:
        await message.reply_text(f"Malik, current welcome message:\n`{config['welcome_message']}`. Pasand aaya? 😉")
    else:
        await message.reply_text("Malik, is group ke liye koi custom welcome message set nahi hai. Kya set karna chahte ho? 🥺")
    if message.from_user and store_message:
        await store_message(message, is_bot_sent=False)

async def clear_welcome_command(client: Client, message: Message):
    if group_configs_collection is None:
        await message.reply_text("Maaf karna, welcome message clear nahi kar payi. Database (Commands/Settings DB) connect nahi ho paya hai. 🥺")
        if message.from_user and store_message:
            await store_message(message, is_bot_sent=False)
        return

    group_configs_collection.update_one(
        {"chat_id": message.chat.id},
        {"$unset": {"welcome_message": ""}}
    )
    await message.reply_text("Malik, custom welcome message hata diya gaya hai. Ab main default welcome message bhejoongi. Kya main bori...ng ho gayi? 😔")
    if message.from_user and store_message:
        await store_message(message, is_bot_sent=False)

# Handle new chat members for welcome message
async def new_member_welcome(client: Client, message: Message):
    config = None
    if group_configs_collection is not None:
        config = group_configs_collection.find_one({"chat_id": message.chat.id})

    # Default welcome message (you might want to make this configurable in main.py)
    default_welcome_text = "Hello {user}, welcome to {chat_title}! Main yahan aapka swagat karti hoon! 🥰"
    welcome_text = default_welcome_text
    if config and "welcome_message" in config:
        welcome_text = config["welcome_message"]

    for user in message.new_chat_members:
        if user.is_self:
            # If the bot itself is added to the group, call the start_group_command from main.py
            # This requires a way to call `start_group_command` from main.py.
            # For simplicity, we'll assume `main.start_group_command` can be imported and called,
            # or handle it differently if direct import creates circular dependencies.
            # For this setup, the `main.py` will have the handler for `filters.new_chat_members`
            # and call this function, passing `start_group_command` as an argument if needed.
            # For now, let's keep it simple and assume main.py handles its own bot-added event.
            continue

        final_welcome_text = welcome_text.replace("{user}", user.mention)
        final_welcome_text = final_welcome_text.replace("{chat_title}", message.chat.title if message.chat.title else "this group")

        await client.send_message(message.chat.id, final_welcome_text)
    if message.from_user and store_message:
        await store_message(message, is_bot_sent=False)
