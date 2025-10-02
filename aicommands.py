# commands.py

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatType
import logging

# Ensure these imports are correct based on your project structure
from config import app, group_tracking_collection, OWNER_ID
from utils import is_admin_or_owner, send_and_auto_delete_reply, update_command_cooldown, is_on_command_cooldown

logger = logging.getLogger(__name__)

# --- AI Mode Configuration ---
AI_MODES = {
    "default": "Default AI Mode (Balanced)",
    "realgirl": "Real Girl Mode (Casual Hinglish)",
    "romanticgirl": "Romantic Girl Mode (Loving Hinglish)",
    "study": "Study Mode (Motivational & Educational)"
}

# --- Utility function to update AI Mode in DB ---
async def set_ai_mode_in_db(chat_id: int, mode: str):
    try:
        await group_tracking_collection.update_one(
            {"_id": chat_id},
            {"$set": {"ai_mode": mode}},
            upsert=True
        )
        return True
    except Exception as e:
        logger.error(f"Error setting AI mode for chat {chat_id}: {e}")
        return False

# --- Helper to create AI Mode buttons ---
def ai_mode_buttons(current_mode):
    buttons = []
    # Real Girl, Romantic Girl, Study
    modes_to_show = ["realgirl", "romanticgirl", "study"]
    
    row = []
    for mode in modes_to_show:
        desc = AI_MODES[mode]
        text = f"✅ {desc}" if mode == current_mode else desc
        row.append(InlineKeyboardButton(text, callback_data=f"set_ai_mode_{mode}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    
    # Default mode button in a new row
    default_text = f"✅ {AI_MODES['default']}" if current_mode == 'default' else AI_MODES['default']
    buttons.append([InlineKeyboardButton(default_text, callback_data="set_ai_mode_default")])
    
    return InlineKeyboardMarkup(buttons)

# --- Button Callback Handler (for /aimode) ---
@app.on_callback_query(filters.regex("^set_ai_mode_"))
async def handle_ai_mode_callback(client: Client, callback_query):
    # Only allow chat admins or owner to change the mode
    if not await is_admin_or_owner(client, callback_query.message.chat.id, callback_query.from_user.id):
        return await callback_query.answer("Only admins can change the AI mode.", show_alert=True)

    try:
        # data format: set_ai_mode_MODE_NAME
        new_mode = callback_query.data.split("_")[-1]
        
        if new_mode not in AI_MODES:
            return await callback_query.answer("Invalid mode selected.", show_alert=True)

        if await set_ai_mode_in_db(callback_query.message.chat.id, new_mode):
            await callback_query.answer(f"AI Mode set to: {AI_MODES[new_mode]}", show_alert=True)
            
            # Edit the message to show the new status
            await callback_query.message.edit_text(
                f"**⚙️ AI Mode Updated!**\n\n**Current Mode:** `{AI_MODES[new_mode]}`\n\nNiche diye gaye buttons se mode change karein:",
                reply_markup=ai_mode_buttons(new_mode)
            )
        else:
            await callback_query.answer("Failed to update AI mode in database.", show_alert=True)
            
    except Exception as e:
        logger.error(f"Error handling AI mode callback: {e}")
        await callback_query.answer(f"Error: {e}", show_alert=True)


# --- /aimode Command Handler (For Buttons) ---
@app.on_message(filters.command("aimode") & filters.group)
async def aimode_command_handler(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)
    
    if not await is_admin_or_owner(client, message.chat.id, message.from_user.id):
        return await message.reply_text("⛔ **Permission Denied!**\n\nAI mode sirf **Admins** hi change kar sakte hain.")

    group_data = group_tracking_collection.find_one({"_id": message.chat.id})
    current_mode = group_data.get("ai_mode", "default") if group_data else "default"

    await send_and_auto_delete_reply(
        message, 
        text=f"**⚙️ AI Mode Control**\n\n**Current Mode:** `{AI_MODES[current_mode]}`\n\nNiche diye gaye buttons se mode change karein:",
        reply_markup=ai_mode_buttons(current_mode)
    )

# --- /mode on/off Command Handler (Unified) ---
@app.on_message(filters.regex(r"^/(realgirl|romanticgirl|study)\s+(on|off)$") & filters.group)
async def mode_on_off_command_handler(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)
    
    if not await is_admin_or_owner(client, message.chat.id, message.from_user.id):
        return await message.reply_text("⛔ **Permission Denied!**\n\nAI mode sirf **Admins** hi control kar sakte hain.")

    # Parse command
    match = filters.regex(r"^/(realgirl|romanticgirl|study)\s+(on|off)$").match(message.text)
    if not match: return # Should not happen with filters.regex

    command_mode = match.group(1)
    command_state = match.group(2)
    
    group_data = group_tracking_collection.find_one({"_id": message.chat.id})
    current_mode = group_data.get("ai_mode", "default") if group_data else "default"
    
    new_mode = "default"
    if command_state == "on":
        new_mode = command_mode
    elif command_state == "off" and current_mode == command_mode:
        # If the currently active mode is being turned off, switch to default
        new_mode = "default"
    elif command_state == "off" and current_mode != command_mode:
        # If user turns off a mode that is not currently active
        await send_and_auto_delete_reply(
            message, 
            text=f"**ℹ️ AI Mode Status**\n\n`/{command_mode} off` command ka asar nahi hoga kyunki **Current Mode** already `{AI_MODES[current_mode]}` hai."
        )
        return
    
    if new_mode == current_mode:
        await send_and_auto_delete_reply(
            message, 
            text=f"**ℹ️ AI Mode Status**\n\nMode already set to **{AI_MODES[current_mode]}**."
        )
        return

    if await set_ai_mode_in_db(message.chat.id, new_mode):
        await send_and_auto_delete_reply(
            message, 
            text=f"**✅ AI Mode Changed!**\n\nBot ka naya mode ab **`{AI_MODES[new_mode]}`** hai.\n({AI_MODES[new_mode]})"
        )
