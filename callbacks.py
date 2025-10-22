# callback.py

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode, ChatType
import asyncio
import re

# Import configurations
from config import (
    app, logger, ASBHAI_USERNAME, ASFILTER_BOT_USERNAME, OWNER_ID, UPDATE_CHANNEL_USERNAME,
    buttons_collection, group_tracking_collection, user_tracking_collection,
    messages_collection, owner_taught_responses_collection, conversational_learning_collection,
    biolink_exceptions_collection, earning_tracking_collection, reset_status_collection
)

# Import utils functions
from utils import (
    get_top_earning_users, delete_after_delay_for_message, store_message, 
    update_user_info, update_group_info, is_admin_or_owner
)

# -----------------------------------------------------
# AI MODES MAPPING
# -----------------------------------------------------
AI_MODES_MAP = {
    "off": {"label": "❌ AI Mode Off", "display": "❌ Off"},
    "realgirl": {"label": "👧 Real Girl", "display": "👧 Real"},
    "romanticgirl": {"label": "💖 Romantic Girl", "display": "💖 Rom"},
    "motivationgirl": {"label": "💪 Motivation Girl", "display": "💪 Moti"},
    "studygirl": {"label": "📚 Study Girl", "display": "📚 Study"},
    "gemini": {"label": "✨ Gemini (Super AI)", "display": "✨ Gemini"},
}

# -----------------------------------------------------
# SETTINGS MENU FUNCTIONS
# -----------------------------------------------------

async def refresh_settings_menu(client: Client, chat_id: int, message_id: int, user_id: int):
    """Fetches current settings and generates the settings keyboard."""
    
    if not await is_admin_or_owner(client, chat_id, user_id):
        try:
            await client.answer_callback_query(user_id, "⚠️ माफ़ करना, आप अब एडमिन नहीं हैं।", show_alert=True)
        except:
            pass
        return

    # Fetch current settings
    current_status_doc = group_tracking_collection.find_one({"_id": chat_id})
    
    # Default values
    bot_enabled = current_status_doc.get("bot_enabled", True) if current_status_doc else True
    linkdel_enabled = current_status_doc.get("linkdel_enabled", False) if current_status_doc else False
    biolinkdel_enabled = current_status_doc.get("biolinkdel_enabled", False) if current_status_doc else False
    usernamedel_enabled = current_status_doc.get("usernamedel_enabled", False) if current_status_doc else False
    ai_mode = current_status_doc.get("ai_mode", "off") if current_status_doc else "off"
    punishment = current_status_doc.get("default_punishment", "delete") if current_status_doc else "delete"
    
    # Status texts
    bot_status = "✅ ON" if bot_enabled else "❌ OFF"
    link_status = "✅ ON" if linkdel_enabled else "❌ OFF"
    biolink_status = "✅ ON" if biolinkdel_enabled else "❌ OFF"
    username_status = "✅ ON" if usernamedel_enabled else "❌ OFF"
    
    # Punishment text
    punishment_map = {
        "delete": "🗑️ Delete Message",
        "mute": "🔇 Mute User",
        "warn": "⚠️ Warn User",
        "ban": "⛔️ Ban User"
    }
    punishment_text = punishment_map.get(punishment, "🗑️ Delete Message")

    # AI Mode text
    ai_mode_text = AI_MODES_MAP.get(ai_mode, AI_MODES_MAP["off"])["display"]

    # Create the Main Settings Keyboard
    keyboard = InlineKeyboardMarkup(
        [
            # Module Toggles - Har setting ka alag button
            [
                InlineKeyboardButton(f"🤖 Bot Chatting: {bot_status}", callback_data="toggle_setting_bot_enabled"),
            ],
            [
                InlineKeyboardButton(f"🔗 Link Delete: {link_status}", callback_data="toggle_setting_linkdel_enabled"),
            ],
            [
                InlineKeyboardButton(f"👤 Bio Link Delete: {biolink_status}", callback_data="toggle_setting_biolinkdel_enabled"),
            ],
            [
                InlineKeyboardButton(f"🗣️ Username Delete: {username_status}", callback_data="toggle_setting_usernamedel_enabled"),
            ],
            # AI Mode Button
            [
                InlineKeyboardButton(f"✨ AI Mode: {ai_mode_text}", callback_data="open_ai_mode_settings"),
            ],
            # Punishment Button
            [
                InlineKeyboardButton(f"🔨 Default Punishment: {punishment_text}", callback_data="open_punishment_settings"),
            ],
            # Bio Link Exceptions
            [
                InlineKeyboardButton("👤 Bio Link Exceptions 📝", callback_data="open_biolink_exceptions")
            ],
            # Close Button
            [
                InlineKeyboardButton("❌ Close Settings", callback_data="close_settings")
            ]
        ]
    )
    
    # Get chat title safely
    try:
        chat_obj = await client.get_chat(chat_id)
        chat_title = chat_obj.title
    except Exception:
        chat_title = "Unknown Group"

    # Generate the Settings Message
    settings_message = (
        f"⚙️ **Group Settings: {chat_title}** 🛠️\n\n"
        "**Hello Boss! You can control the group rules and bot functions from the buttons below.**\n\n"
        f"**🤖 Bot Chatting:** {'Enabled' if bot_enabled else 'Disabled'}\n"
        f"**🔗 Link Delete:** {'Enabled' if linkdel_enabled else 'Disabled'}\n" 
        f"**👤 Bio Link Delete:** {'Enabled' if biolinkdel_enabled else 'Disabled'}\n"
        f"**🗣️ Username Delete:** {'Enabled' if usernamedel_enabled else 'Disabled'}\n"
        f"**✨ AI Mode:** {ai_mode_text}\n"
        f"**🔨 Default Punishment:** {punishment_text}\n\n"
        "_Users who break your filter settings will receive the **Default Punishment**._"
    )

    # Edit the message
    try:
        await client.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=settings_message,
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        logger.error(f"Failed to edit settings message in chat {chat_id}: {e}")

# -----------------------------------------------------
# MAIN SETTINGS HANDLERS
# -----------------------------------------------------

@app.on_callback_query(filters.regex("open_group_settings"))
@app.on_callback_query(filters.regex("settings_back_to_main"))
async def open_settings_from_callback(client: Client, callback_query: CallbackQuery):
    """Opens or returns to the main settings menu."""
    await callback_query.answer()
    if not await is_admin_or_owner(client, callback_query.message.chat.id, callback_query.from_user.id):
        await callback_query.answer("⚠️ माफ़ करना, आप अब एडमिन नहीं हैं।", show_alert=True)
        return

    await refresh_settings_menu(
        client,
        callback_query.message.chat.id,
        callback_query.message.id,
        callback_query.from_user.id
    )

@app.on_callback_query(filters.regex("^toggle_setting_"))
async def toggle_setting_callback(client: Client, callback_query: CallbackQuery):
    """Toggles a specific setting."""
    chat_id = callback_query.message.chat.id
    user_id = callback_query.from_user.id
    setting_key = callback_query.data.replace("toggle_setting_", "")
    
    if not await is_admin_or_owner(client, chat_id, user_id):
        await callback_query.answer("⚠️ माफ़ करना, आप अब एडमिन नहीं हैं।", show_alert=True)
        return

    # Fetch current status
    current_status_doc = group_tracking_collection.find_one({"_id": chat_id})
    default_value = True if setting_key == "bot_enabled" else False
    current_value = current_status_doc.get(setting_key, default_value) if current_status_doc else default_value
    
    # Calculate new value
    new_value = not current_value
    
    # Update database
    group_tracking_collection.update_one(
        {"_id": chat_id},
        {"$set": {setting_key: new_value}},
        upsert=True
    )
    
    # Refresh menu
    await refresh_settings_menu(client, chat_id, callback_query.message.id, user_id)
    
    # Answer query
    action_text = "चालू" if new_value else "बंद"
    setting_name_map = {
        "bot_enabled": "बॉट चैटिंग",
        "linkdel_enabled": "लिंक डिलीट",
        "biolinkdel_enabled": "बायो लिंक डिलीट",
        "usernamedel_enabled": "@यूज़रनेम डिलीट"
    }
    setting_name = setting_name_map.get(setting_key, setting_key)
    
    await callback_query.answer(f"{setting_name} {action_text} कर दिया गया है।")

# -----------------------------------------------------
# PUNISHMENT SETTINGS HANDLERS
# -----------------------------------------------------

@app.on_callback_query(filters.regex("open_punishment_settings"))
async def open_punishment_settings_callback(client: Client, callback_query: CallbackQuery):
    """Opens the punishment settings submenu."""
    chat_id = callback_query.message.chat.id
    user_id = callback_query.from_user.id

    if not await is_admin_or_owner(client, chat_id, user_id):
        await callback_query.answer("⚠️ माफ़ करना, आप अब एडमिन नहीं हैं।", show_alert=True)
        return

    current_status_doc = group_tracking_collection.find_one({"_id": chat_id})
    current_punishment = current_status_doc.get("default_punishment", "delete") if current_status_doc else "delete"
    
    def get_punishment_button(action, label):
        checkmark = "✅ " if action == current_punishment else ""
        return InlineKeyboardButton(f"{checkmark}{label}", callback_data=f"set_punishment_{action}")

    keyboard = InlineKeyboardMarkup(
        [
            [
                get_punishment_button("delete", "🗑️ Delete Message"),
                get_punishment_button("mute", "🔇 Mute User")
            ],
            [
                get_punishment_button("warn", "⚠️ Warn User"),
                get_punishment_button("ban", "⛔️ Ban User")
            ],
            [
                InlineKeyboardButton("🔙 Settings Menu", callback_data="settings_back_to_main")
            ]
        ]
    )
    
    punishment_message = (
        "🔨 **Default Punishment Settings** 🔨\n\n"
        "Choose the action that bot will apply to users when they violate any filter rules.\n\n"
        f"**Current Punishment:** **{current_punishment.upper()}**"
    )

    try:
        await client.edit_message_text(
            chat_id=chat_id,
            message_id=callback_query.message.id,
            text=punishment_message,
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        logger.error(f"Failed to edit punishment settings message: {e}")

    await callback_query.answer()

@app.on_callback_query(filters.regex("^set_punishment_"))
async def set_punishment_callback(client: Client, callback_query: CallbackQuery):
    """Sets the new default punishment."""
    chat_id = callback_query.message.chat.id
    user_id = callback_query.from_user.id
    new_punishment = callback_query.data.replace("set_punishment_", "")
    
    if not await is_admin_or_owner(client, chat_id, user_id):
        await callback_query.answer("⚠️ माफ़ करना, आप अब एडमिन नहीं हैं।", show_alert=True)
        return

    # Validate punishment
    valid_punishments = ["delete", "mute", "warn", "ban"]
    if new_punishment not in valid_punishments:
        await callback_query.answer("Invalid punishment option.", show_alert=True)
        return

    # Update database
    group_tracking_collection.update_one(
        {"_id": chat_id},
        {"$set": {"default_punishment": new_punishment}},
        upsert=True
    )
    
    # Refresh menu
    await refresh_settings_menu(client, chat_id, callback_query.message.id, user_id)
    
    # Answer query
    punishment_map = {
        "delete": "Delete Message",
        "mute": "Mute",
        "warn": "Warn",
        "ban": "Ban"
    }
    action_text = punishment_map.get(new_punishment, new_punishment)
    await callback_query.answer(f"Default punishment set to {action_text}")

# -----------------------------------------------------
# AI MODE SETTINGS HANDLERS
# -----------------------------------------------------

@app.on_callback_query(filters.regex("open_ai_mode_settings"))
async def open_ai_mode_settings_callback(client: Client, callback_query: CallbackQuery):
    """Opens the AI mode settings submenu."""
    chat_id = callback_query.message.chat.id
    user_id = callback_query.from_user.id

    if not await is_admin_or_owner(client, chat_id, user_id):
        await callback_query.answer("⚠️ माफ़ करना, आप अब एडमिन नहीं हैं।", show_alert=True)
        return

    current_status_doc = group_tracking_collection.find_one({"_id": chat_id})
    current_ai_mode = current_status_doc.get("ai_mode", "off") if current_status_doc else "off"
    
    # AI Mode buttons
    keyboard_buttons = []
    
    # Off Button
    status_off = "✅ " if current_ai_mode == "off" else ""
    keyboard_buttons.append([InlineKeyboardButton(f"{status_off}{AI_MODES_MAP['off']['label']}", callback_data="set_ai_mode_off")])

    # Other AI Modes in 2 columns
    current_row = []
    for mode_key, mode_data in AI_MODES_MAP.items():
        if mode_key != "off":
            status = "✅ " if current_ai_mode == mode_key else ""
            button = InlineKeyboardButton(f"{status}{mode_data['label']}", callback_data=f"set_ai_mode_{mode_key}")
            current_row.append(button)
            if len(current_row) == 2:
                keyboard_buttons.append(current_row)
                current_row = []
    
    if current_row:
        keyboard_buttons.append(current_row)

    # Back Button
    keyboard_buttons.append([InlineKeyboardButton("🔙 Settings Menu", callback_data="settings_back_to_main")])
    
    keyboard = InlineKeyboardMarkup(keyboard_buttons)

    current_mode_display = AI_MODES_MAP.get(current_ai_mode, AI_MODES_MAP["off"])["label"]
    
    ai_mode_message = (
        "✨ **AI Mode Settings** ✨\n\n"
        "Choose the AI personality mode for the bot.\n\n"
        f"**Current AI Mode:** **{current_mode_display}**"
    )

    await client.edit_message_text(
        chat_id=chat_id,
        message_id=callback_query.message.id,
        text=ai_mode_message,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )
    await callback_query.answer()

@app.on_callback_query(filters.regex("^set_ai_mode_"))
async def set_ai_mode_callback(client: Client, callback_query: CallbackQuery):
    """Sets the new AI mode."""
    chat_id = callback_query.message.chat.id
    user_id = callback_query.from_user.id
    new_ai_mode = callback_query.data.replace("set_ai_mode_", "")
    
    if not await is_admin_or_owner(client, chat_id, user_id):
        await callback_query.answer("⚠️ माफ़ करना, आप अब एडमिन नहीं हैं।", show_alert=True)
        return

    # Validate AI Mode
    if new_ai_mode not in AI_MODES_MAP:
        await callback_query.answer("Invalid AI mode option.", show_alert=True)
        return

    # Update database
    group_tracking_collection.update_one(
        {"_id": chat_id},
        {"$set": {"ai_mode": new_ai_mode}},
        upsert=True
    )
    
    # Refresh menu
    await refresh_settings_menu(client, chat_id, callback_query.message.id, user_id)
    
    # Answer query
    action_text = AI_MODES_MAP.get(new_ai_mode, AI_MODES_MAP["off"])["display"]
    await callback_query.answer(f"AI mode set to {action_text}")

# -----------------------------------------------------
# BIOLINK EXCEPTIONS HANDLERS
# -----------------------------------------------------

@app.on_callback_query(filters.regex("open_biolink_exceptions"))
async def open_biolink_exceptions_callback(client: Client, callback_query: CallbackQuery):
    """Displays the biolink exception menu."""
    chat_id = callback_query.message.chat.id
    user_id = callback_query.from_user.id
    
    if not await is_admin_or_owner(client, chat_id, user_id):
        await callback_query.answer("⚠️ माफ़ करना, आप अब एडमिन नहीं हैं।", show_alert=True)
        return

    # Fetch current exceptions
    exceptions = biolink_exceptions_collection.find_one({"_id": chat_id})
    exception_users = exceptions.get("user_ids", []) if exceptions else []
    
    # Prepare user list
    list_text = "No exceptions added yet. 🤷‍♀️"
    if exception_users:
        list_text = "\n".join([f"• `{uid}`" for uid in exception_users])

    message_text = (
        "📝 **Bio Link Exceptions** 📝\n\n"
        "Users who are allowed to have links in their bio:\n\n"
        f"**Current Exceptions:**\n{list_text}\n\n"
        "**Usage:**\n"
        "• Add exception: `/addbiolink <user_id>`\n"
        "• Remove exception: `/rembiolink <user_id>`\n\n"
        "_Type these commands in the group._"
    )

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔙 Settings Menu", callback_data="settings_back_to_main")]
        ]
    )

    try:
        await client.edit_message_text(
            chat_id=chat_id,
            message_id=callback_query.message.id,
            text=message_text,
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        logger.error(f"Failed to edit biolink exceptions message: {e}")
        
    await callback_query.answer()

# -----------------------------------------------------
# CLOSE SETTINGS HANDLER
# -----------------------------------------------------

@app.on_callback_query(filters.regex("close_settings"))
async def close_settings_callback(client: Client, callback_query: CallbackQuery):
    """Closes the settings menu."""
    chat_id = callback_query.message.chat.id
    user_id = callback_query.from_user.id

    if not await is_admin_or_owner(client, chat_id, user_id):
        await callback_query.answer("⚠️ माफ़ करना, आप अब एडमिन नहीं हैं।", show_alert=True)
        return

    try:
        await client.delete_messages(
            chat_id=chat_id,
            message_ids=callback_query.message.id
        )
        await callback_query.answer("Settings menu closed.")
    except Exception as e:
        await callback_query.message.edit_text(
            "❌ **Settings Closed** ❌\n\n_This message will be deleted in 5 seconds._",
            reply_markup=None,
            parse_mode=ParseMode.MARKDOWN
        )
        await callback_query.answer("Settings closed.")
        await asyncio.sleep(5)
        try:
            await client.delete_messages(chat_id, callback_query.message.id)
        except:
            pass

# -----------------------------------------------------
# OTHER CALLBACK HANDLERS (HELP, LEADERBOARD, etc.)
# -----------------------------------------------------

@app.on_callback_query(filters.regex("show_help_menu"))
async def show_help_menu_callback(client: Client, callback_query: CallbackQuery):
    logger.info(f"Help menu callback by user {callback_query.from_user.id}")
    
    help_message = (
        "Here's your help, darling! 🥰\n\n"
        "**👥 Group Commands (Admins only):**\n"
        "• `/settings` - **Open menu to manage all group settings.**\n"
        "• `/setaimode` - **Set AI personality mode.**\n"
        "• `/addbiolink <user_id>` - Add user to bio link exceptions.\n"
        "• `/rembiolink <user_id>` - Remove user from bio link exceptions.\n\n"
        "**👤 General & Private Commands:**\n"
        "• `/start` - Start the bot\n"
        "• `/help` - Show this help menu\n"
        "• `/topusers` - Top active users leaderboard\n"
        "• `/stats check` - Check bot statistics (private chat)\n"
        "• `/clearmydata` - Delete your data\n\n"
        "If you need more help, just ask! 😊"
    )

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("💰 Earning Rules", callback_data="show_earning_rules")],
            [InlineKeyboardButton("🔙 Back", callback_data="start_menu_from_help")]
        ]
    )

    await callback_query.message.edit_text(
        text=help_message,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True 
    )
    await callback_query.answer()

@app.on_callback_query(filters.regex("show_earning_rules"))
async def show_earning_rules_callback(client: Client, callback_query: CallbackQuery):
    logger.info(f"Earning rules callback by user {callback_query.from_user.id}")
    
    earning_rules_message = (
        "💰 **Earning Rules!** 💰\n\n"
        "Here's how you can earn with me:\n"
        "1. **Be Active:** Send more messages and participate in group conversations.\n"
        "2. **Be Fun:** Send good quality and fun messages. Avoid spamming!\n"
        "3. **Monthly Reset:** Leaderboard resets on the first of every month.\n"
        "4. **Prizes:** Top users get cash prizes or premium subscriptions every month.\n\n"
        f"Contact @{ASBHAI_USERNAME} for more information.\n\n"
        "Start chatting and win! 🚀"
    )

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔙 Earning Leaderboard", callback_data="show_earning_leaderboard")]
        ]
    )

    await callback_query.message.edit_text(
        text=earning_rules_message,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True 
    )
    await callback_query.answer()

@app.on_callback_query(filters.regex("start_menu_from_help"))
async def back_to_start_from_help(client: Client, callback_query: CallbackQuery):
    logger.info(f"Back to start menu from help by user {callback_query.from_user.id}")
    
    user_name = callback_query.from_user.first_name if callback_query.from_user else "Friend"
    welcome_message = (
        f"🌟 Hey **{user_name}**! Welcome! 🌟\n\n"
        "I'm ready to help you!\n"
        "Click the 'Help' button below to see all my commands."
    )
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("➕ Add Me to Group", url=f"https://t.me/{client.me.username}?startgroup=true")],
            [
                InlineKeyboardButton("📣 Updates Channel", url=f"https://t.me/{UPDATE_CHANNEL_USERNAME}"),
                InlineKeyboardButton("❓ Support Group", url="https://t.me/aschat_group")
            ],
            [
                InlineKeyboardButton("ℹ️ Help ❓", callback_data="show_help_menu"),
                InlineKeyboardButton("💰 Earning Leaderboard", callback_data="show_earning_leaderboard")
            ]
        ]
    )
    
    await callback_query.message.edit_text(
        text=welcome_message,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True 
    )
    await callback_query.answer()

@app.on_callback_query(filters.regex("show_earning_leaderboard"))
async def show_earning_leaderboard_callback(client: Client, callback_query: CallbackQuery):
    logger.info(f"Earning leaderboard callback by user {callback_query.from_user.id}")
    
    top_users = await get_top_earning_users()
    if not top_users:
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔙 Main Menu", callback_data="start_menu_from_help")]]
        )
        await callback_query.message.edit_text(
            text="😢 No users are on the leaderboard yet! Be the first by being active! ✨\n\n**Powered By:** @asbhaibsr", 
            parse_mode=ParseMode.MARKDOWN, 
            reply_markup=keyboard, 
            disable_web_page_preview=True
        )
        await callback_query.answer()
        return

    earning_messages = ["👑 **Top Active Users - ✨ VIP Leaderboard! ✨** 👑\n\n"]
    prizes = {
        1: "💰 ₹50", 2: "💸 ₹30", 3: "🎁 ₹20",
        4: f"🎬 1 Week Premium Plan of @{ASFILTER_BOT_USERNAME}",
        5: f"🎬 3 Days Premium Plan of @{ASFILTER_BOT_USERNAME}"
    }

    for i, user in enumerate(top_users[:5]):
        rank = i + 1
        user_name = user.get('first_name', 'Unknown User')
        username_str = f"@{user.get('username')}" if user.get('username') else f"ID: `{user.get('user_id')}`"
        message_count = user.get('message_count', 0)
        prize_str = prizes.get(rank, "🏅 No Prize")

        group_info = ""
        last_group_id = user.get('last_active_group_id')
        last_group_title = user.get('last_active_group_title', 'Unknown Group')

        if last_group_id:
            try:
                chat_obj = await client.get_chat(last_group_id)
                if chat_obj.type == ChatType.PRIVATE:
                    group_info = f"   • Active in: **[Private Chat](tg://user?id={user.get('user_id')})**\n"
                elif chat_obj.username:
                    group_info = f"   • Active in: **[{chat_obj.title}](https://t.me/{chat_obj.username})**\n"
                else:
                    try:
                        invite_link = await client.export_chat_invite_link(last_group_id)
                        group_info = f"   • Active in: **[{chat_obj.title}]({invite_link})**\n"
                    except Exception:
                        group_info = f"   • Active in: **{chat_obj.title}** (Private Group)\n"
            except Exception as e:
                logger.warning(f"Could not fetch chat info for group ID {last_group_id}: {e}")
                group_info = f"   • Active in: **{last_group_title}** (Info Not Available)\n"
        else:
            group_info = "   • Active in: **No Group Activity**\n"

        earning_messages.append(
            f"**{rank}.** 🌟 **{user_name}** ({username_str}) 🌟\n"
            f"   • Total Messages: **{message_count} 💬**\n"
            f"   • Potential Prize: **{prize_str}**\n"
            f"{group_info}"
        )
    
    earning_messages.append(
        "\n_This system resets on the first of every month!_\n"
        "_Use `/help` to know the Group rules._"
    )
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("💰 Withdraw", url=f"https://t.me/{ASBHAI_USERNAME}"),
                InlineKeyboardButton("💰 Earning Rules", callback_data="show_earning_rules")
            ]
        ]
    )
    await callback_query.message.edit_text(
        text="\n".join(earning_messages), 
        reply_markup=keyboard, 
        parse_mode=ParseMode.MARKDOWN, 
        disable_web_page_preview=True
    )
    await callback_query.answer()

# -----------------------------------------------------
# OWNER-ONLY CALLBACK HANDLERS
# -----------------------------------------------------

@app.on_callback_query(filters.regex("confirm_clearall_dbs"))
async def confirm_clearall_dbs_callback(client: Client, callback_query: CallbackQuery):
    logger.info(f"Clear All DBs confirmation from owner {callback_query.from_user.id}")
    if callback_query.from_user.id != OWNER_ID:
        await callback_query.answer("⚠️ You are not authorized.", show_alert=True)
        return

    try:
        messages_collection.drop()
        buttons_collection.drop()
        group_tracking_collection.drop()
        user_tracking_collection.drop()
        owner_taught_responses_collection.drop()
        conversational_learning_collection.drop()
        biolink_exceptions_collection.drop()
        earning_tracking_collection.drop()
        reset_status_collection.drop()

        await callback_query.message.edit_text(
            "🎉 **All databases cleared successfully!** ✨\n"
            "All collections have been deleted successfully.\n"
            "Fresh start! 🚀",
            parse_mode=ParseMode.MARKDOWN
        )
        logger.info(f"Owner {callback_query.from_user.id} successfully cleared all MongoDB collections.")
    except Exception as e:
        await callback_query.message.edit_text(
            f"Error clearing databases: {e}",
            parse_mode=ParseMode.MARKDOWN
        )
        logger.error(f"Error clearing all databases: {e}")
    
    await callback_query.answer("Databases cleared!", show_alert=True)

@app.on_callback_query(filters.regex("cancel_clearall_dbs"))
async def cancel_clearall_dbs_callback(client: Client, callback_query: CallbackQuery):
    logger.info(f"Clear All DBs cancellation from owner {callback_query.from_user.id}")
    if callback_query.from_user.id != OWNER_ID:
        await callback_query.answer("⚠️ You are not authorized.", show_alert=True)
        return
    
    await callback_query.message.edit_text(
        "Okay! ✅ Database clearing cancelled.\n"
        "Your data is safe. 😉",
        parse_mode=ParseMode.MARKDOWN
    )
    await callback_query.answer("Cancelled!", show_alert=True)# callbacks.py 

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode, ChatType
import asyncio
import re

# आपको यहां 'app' और 'logger' और अन्य CONFIG वेरिएबल्स को इम्पोर्ट करना होगा
# सुनिश्चित करें कि आपकी 'config.py' से ये सही ढंग से इम्पोर्ट हो रहे हैं।
from config import (
    app, logger, ASBHAI_USERNAME, ASFILTER_BOT_USERNAME, OWNER_ID, UPDATE_CHANNEL_USERNAME,
    buttons_collection, group_tracking_collection, user_tracking_collection,
    messages_collection, owner_taught_responses_collection, conversational_learning_collection,
    biolink_exceptions_collection, earning_tracking_collection, reset_status_collection
)

# utils.py से आवश्यक फ़ंक्शन इम्पोर्ट करें
from utils import (
    get_top_earning_users, delete_after_delay_for_message, store_message, 
    update_user_info, update_group_info, is_admin_or_owner
)


# -----------------------------------------------------
# UTILITY FUNCTIONS FOR SETTINGS
# -----------------------------------------------------

# AI Modes की मैपिंग (AI Mode Settings के लिए)
AI_MODES_MAP = {
    "off": {"label": "❌ AI Mᴏᴅᴇ Oғғ", "display": "❌ Oғғ"},
    "realgirl": {"label": "👧 Rᴇᴀʟ Gɪʀʟ", "display": "👧 Rᴇᴀʟ"},
    "romanticgirl": {"label": "💖 Rᴏᴍᴀɴᴛɪᴄ Gɪʀʟ", "display": "💖 Rᴏᴍ"},
    "motivationgirl": {"label": "💪 Mᴏᴛɪᴠᴀᴛɪᴏɴ Gɪʀʟ", "display": "💪 Mᴏᴛɪ"},
    "studygirl": {"label": "📚 Sᴛᴜᴅʏ Gɪʀʟ", "display": "📚 Sᴛᴜᴅʏ"},
    # 🟢 FIX: Added Gemini mode
    "gemini": {"label": "✨ Gᴇᴍɪɴɪ (Sᴜᴘᴇʀ AI)", "display": "✨ Gᴇᴍɪɴɪ"},
}

# यह फ़ंक्शन सेटिंग्स मैसेज को री-जनरेट और एडिट करने के लिए है
async def refresh_settings_menu(client: Client, chat_id: int, message_id: int, user_id: int):
    """Fetches current settings, generates the settings keyboard, and edits the message."""
    
    # Check Admin/Owner status again (in case an old button is pressed)
    if not await is_admin_or_owner(client, chat_id, user_id):
        # Admin check failed, but we shouldn't fail silently if the message still exists
        try:
            await client.answer_callback_query(user_id, "माफ़ करना, आप अब एडमिन नहीं हैं।", show_alert=True)
        except:
            pass
        return  

    # 1. Fetch current settings and default punishment
    current_status_doc = group_tracking_collection.find_one({"_id": chat_id})
    
    # Default values if not found
    bot_enabled = current_status_doc.get("bot_enabled", True) if current_status_doc else True
    linkdel_enabled = current_status_doc.get("linkdel_enabled", False) if current_status_doc else False
    biolinkdel_enabled = current_status_doc.get("biolinkdel_enabled", False) if current_status_doc else False
    usernamedel_enabled = current_status_doc.get("usernamedel_enabled", False) if current_status_doc else False
    ai_mode = current_status_doc.get("ai_mode", "off") if current_status_doc else "off" # New AI Mode
    punishment = current_status_doc.get("default_punishment", "delete") if current_status_doc else "delete"
    
    # Status texts (English-Hindi mix for styling as per commands.py)
    bot_status = "✅ O𝙽" if bot_enabled else "❌ O𝙵𝙵"
    link_status = "✅ O𝙽" if linkdel_enabled else "❌ O𝙵𝙵"
    biolink_status = "✅ O𝙽" if biolinkdel_enabled else "❌ O𝙵𝙵"
    username_status = "✅ O𝙽" if usernamedel_enabled else "❌ O𝙵𝙵"
    
    # Punishment text (English-Hindi mix for styling as per commands.py)
    punishment_map = {
        "delete": "🗑️ Dᴇʟᴇᴛᴇ Mᴇꜱꜱᴀɢᴇ",
        "mute": "🔇 Mᴜᴛᴇ Uꜱᴇʀ",
        "warn": "⚠️ Wᴀʀɴ Uꜱᴇʀ",
        "ban": "⛔️ Bᴀɴ Uꜱᴇʀ"
    }
    punishment_text = punishment_map.get(punishment, "🗑️ Dᴇʟᴇᴛᴇ Mᴇꜱꜱᴀɢᴇ")

    # 🟢 FIX: Use AI_MODES_MAP for consistent display
    ai_mode_text = AI_MODES_MAP.get(ai_mode, AI_MODES_MAP["off"])["display"]


    # 2. Create the Main Settings Keyboard
    keyboard = InlineKeyboardMarkup(
        [
            # Module Toggles
            [
                InlineKeyboardButton(f"🤖 Bᴏᴛ Cʜᴀᴛᴛɪɴɢ: {bot_status}", callback_data="toggle_setting_bot_enabled"),
            ],
            [
                InlineKeyboardButton(f"🔗 Lɪɴᴋ Dᴇ𝗹𝗲𝘁𝗲: {link_status}", callback_data="toggle_setting_linkdel_enabled"),
            ],
            [
                InlineKeyboardButton(f"👤 Bɪᴏ Lɪɴᴋ D𝗲𝗹𝗲𝘁𝗲: {biolink_status}", callback_data="toggle_setting_biolinkdel_enabled"),
            ],
            [
                InlineKeyboardButton(f"🗣️ @Uꜱᴇ𝗿𝗻𝗮𝗺𝗲 D𝗲𝗹𝗲𝘁𝗲: {username_status}", callback_data="toggle_setting_usernamedel_enabled"),
            ],
            # NEW AI MODE BUTTON
            [
                InlineKeyboardButton(f"✨ AI Mᴏᴅ𝗲: {ai_mode_text}", callback_data="open_ai_mode_settings"),
            ],
            # Punishment and Biolink Exception
            [
                InlineKeyboardButton(f"🔨 Dᴇ𝗳𝗮𝘂𝗹𝘁 Pᴜ𝗻𝗶𝘀𝗵𝗺𝗲𝗻𝘁: {punishment_text}", callback_data="open_punishment_settings"),
            ],
            [
                 InlineKeyboardButton("👤 Bɪ𝗼 L𝗶𝗻𝗸 Exᴄᴇᴘᴛɪᴏ𝗻ꜱ 📝", callback_data="open_biolink_exceptions")
            ],
            # Close Button
            [
                InlineKeyboardButton("❌ Cʟ𝗼𝘀𝗲 S𝗲𝘁𝘁𝗶𝗻gꜱ", callback_data="close_settings")
            ]
        ]
    )
    
    # 🟢 FIX: Get chat title safely
    try:
        chat_obj = await client.get_chat(chat_id)
        chat_title = chat_obj.title
    except Exception:
        chat_title = "Unknown Group"


    # 3. Generate the Settings Message
    settings_message = (
        f"⚙️ **𝗚𝗿𝗼𝘂𝗽 𝗦𝗲𝘁𝘁𝗶𝗻𝗴𝘀: {chat_title}** 🛠️\n\n"
        "𝗛𝗲𝗹𝗹𝗼, 𝗕𝗼𝘀𝘀! 𝗬𝗼𝘂 𝗰𝗮𝗻 𝗰𝗼𝗻𝘁𝗿𝗼𝗹 𝘁𝗵𝗲 𝗴𝗿𝗼𝘂𝗽 𝗿𝘂𝗹𝗲𝘀 𝗮𝗻𝗱 𝗯𝗼𝘁 𝗳𝘂𝗻𝗰𝘁𝗶𝗼𝗻𝘀 𝗳𝗿𝗼𝗺 𝘁𝗵𝗲 𝗯𝘂𝘁𝘁𝗼𝗻𝘀 𝗯𝗲𝗹𝗼𝘄.\n"
        "**AI Mᴏᴅ𝗲:** Bᴏᴛ ᴋɪ ᴘᴇʀsᴏɴᴀʟɪᴛʏ ᴀᴜʀ ᴊ𝗮𝘄𝗮𝗯 ᴅᴇɴᴇ ᴋᴀ 𝘁𝗮𝗿𝗶𝗸𝗮 𝗶𝘀 𝘀𝗲 𝘀𝗲𝘁 𝗵𝗼𝗴𝗮. **Cᴜʀʀ𝗲𝗻𝘁: {ai_mode_text}**\n\n"
        "𝗨𝘀𝗲𝗿𝘀 𝘄𝗵𝗼 𝗯𝗿𝗲𝗮𝗸 𝘆𝗼𝘂𝗿 𝗳𝗶𝗹𝘁𝗲𝗿 𝘀𝗲𝘁𝘁𝗶𝗻𝗴𝘀 𝘄𝗶𝗹𝗹 𝗿𝗲𝗰𝗲𝗶𝘃𝗲 𝘁𝗵𝗲 **𝗗𝗲𝗳𝗮𝘂𝗹𝘁 𝗣𝘂𝗻𝗶𝘀𝗵𝗺𝗲𝗻𝘁**.\n\n"
        f"**𝗗𝗲𝗳𝗮𝘂𝗹𝘁 𝗣𝘂𝗻𝗶𝘀𝗵𝗺𝗲𝗻𝘁:** {punishment_text}\n"
        "__𝗖𝗵𝗼𝗼𝘀𝗲 𝘄𝗵𝗮𝘁 𝗽𝘂𝗻𝗶𝘀𝗵𝗺𝗲𝗻𝘁 𝘁𝗼 𝗴𝗶𝘃𝗲 𝘁𝗼 𝗿𝘂𝗹𝗲-𝗯𝗿𝗲𝗮𝗸𝗲𝗿𝘀 𝗳𝗿𝗼𝗺 '𝗗𝗲𝗳𝗮𝘂𝗹𝘁 𝗣𝘂𝗻𝗶𝘀𝗵𝗺𝗲𝗻𝘁'.__"
    )

    # 4. Edit the message
    try:
        await client.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=settings_message.format(ai_mode_text=ai_mode_text), # 🟢 FIX: Added .format() for AI Mode Text
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        logger.error(f"Failed to edit settings message in chat {chat_id}: {e}")

# -----------------------------------------------------
# AI MODE SUB-MENU HANDLERS
# -----------------------------------------------------

@app.on_callback_query(filters.regex("open_ai_mode_settings"))
async def open_ai_mode_settings_callback(client: Client, callback_query: CallbackQuery):
    """Opens the submenu to select the default punishment."""
    chat_id = callback_query.message.chat.id
    user_id = callback_query.from_user.id

    if not await is_admin_or_owner(client, chat_id, user_id):
        await callback_query.answer("⚠️ माफ़ करना, आप अब एडमिन नहीं हैं।", show_alert=True)
        return

    current_status_doc = group_tracking_collection.find_one({"_id": chat_id})
    current_ai_mode = current_status_doc.get("ai_mode", "off") if current_status_doc else "off"
    
    # AI Mode buttons with checkmark for current selection
    keyboard_buttons = []
    current_row = []

    # Off/Default Button
    # 🟢 FIX: Use AI_MODES_MAP for the label
    status_off = "✅ " if current_ai_mode == "off" else ""
    keyboard_buttons.append([InlineKeyboardButton(f"{status_off}{AI_MODES_MAP['off']['label']}", callback_data="set_ai_mode_off")])

    # Dynamic Mode Buttons
    for mode_key, mode_data in AI_MODES_MAP.items():
        if mode_key != "off":
            status = "✅ " if current_ai_mode == mode_key else ""
            button = InlineKeyboardButton(f"{status}{mode_data['label']}", callback_data=f"set_ai_mode_{mode_key}")
            current_row.append(button)
            if len(current_row) == 2:
                keyboard_buttons.append(current_row)
                current_row = []
    
    if current_row:
        keyboard_buttons.append(current_row)

    # Back Button
    keyboard_buttons.append([InlineKeyboardButton("🔙 Sᴇᴛᴛɪɴɢꜱ Mᴇɴᴜ", callback_data="settings_back_to_main")])
    
    keyboard = InlineKeyboardMarkup(keyboard_buttons)

    # 🟢 FIX: Used 'label' for better display in the title, 'display' for main settings
    current_mode_display = AI_MODES_MAP.get(current_ai_mode, AI_MODES_MAP["off"])["label"] 
    
    ai_mode_message = (
        "👑 **AI Mᴏᴅᴇ Sᴇᴛᴛɪɴɢꜱ 👑**\n\n"
        "𝗛𝗲𝗹𝗹𝗼 𝗕𝗼𝘀𝘀, 𝘆𝗲𝗵𝗮𝗻 𝘀𝗲 𝗮𝗽𝗻𝗮 **AI 𝗽𝗲𝗿𝘀𝗼𝗻𝗮𝗹𝗶𝘁𝘆** 𝘀𝗲𝘁 𝗸𝗮𝗿𝗼.\n"
        "𝗕𝗼𝘁 𝘂𝘀 𝗵𝗶 𝗮𝗻𝗱𝗮𝗮𝘇 𝗺𝗮𝗶𝗻, 𝗯𝗶𝗸𝘂𝗹 𝗿𝗲𝗮𝗹 𝗹𝗮𝗱𝗸𝗶 𝗷𝗮𝗶𝘀𝗲, 𝗯𝗮𝗮𝘁 𝗸𝗮𝗿𝗲गी! 🤩\n\n"
        f"**Cᴜʀ𝗿𝗲𝗻𝘁 AI Mᴏ𝗱𝗲:** **{current_mode_display}**"
    )

    await client.edit_message_text(
        chat_id=chat_id,
        message_id=callback_query.message.id,
        text=ai_mode_message,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )
    await callback_query.answer()


@app.on_callback_query(filters.regex("^set_ai_mode_"))
async def set_ai_mode_callback(client: Client, callback_query: CallbackQuery):
    """Sets the new AI mode and returns to the main settings."""
    chat_id = callback_query.message.chat.id
    user_id = callback_query.from_user.id
    new_ai_mode = callback_query.data.replace("set_ai_mode_", "")
    
    if not await is_admin_or_owner(client, chat_id, user_id):
        await callback_query.answer("⚠️ माफ़ करना, आप अब एडमिन नहीं हैं।", show_alert=True)
        return

    # 1. Validate AI Mode
    if new_ai_mode not in AI_MODES_MAP:
        await callback_query.answer("अमान्य AI मोड विकल्प।", show_alert=True)
        return

    # 2. Update the database
    group_tracking_collection.update_one(
        {"_id": chat_id},
        {"$set": {"ai_mode": new_ai_mode}},
        upsert=True
    )
    
    # 3. Refresh the main menu
    await refresh_settings_menu(client, chat_id, callback_query.message.id, user_id)
    
    # 4. Answer the query
    # 🟢 FIX: Use 'display' for the answer text, as it's shorter
    action_text = AI_MODES_MAP.get(new_ai_mode, AI_MODES_MAP["off"])["display"]
    await callback_query.answer(f"✨ AI मोड अब **{action_text}** पर सेट कर दिया गया है।", show_alert=True)


# -----------------------------------------------------
# GROUP SETTINGS HANDLERS (GROUP & PUNISHMENT)
# -----------------------------------------------------

@app.on_callback_query(filters.regex("open_group_settings"))
@app.on_callback_query(filters.regex("settings_back_to_main"))
async def open_settings_from_callback(client: Client, callback_query: CallbackQuery):
    """Opens or returns to the main settings menu."""
    await callback_query.answer() # Answer early for speed
    if not await is_admin_or_owner(client, callback_query.message.chat.id, callback_query.from_user.id):
        await callback_query.answer("⚠️ माफ़ करना, आप अब एडमिन नहीं हैं।", show_alert=True)
        return

    # Call the refresh function to display the main settings
    await refresh_settings_menu(
        client,
        callback_query.message.chat.id,
        callback_query.message.id,
        callback_query.from_user.id
    )


@app.on_callback_query(filters.regex("^toggle_setting_"))
async def toggle_setting_callback(client: Client, callback_query: CallbackQuery):
    """Toggles a specific setting (bot_enabled, linkdel_enabled, etc.)."""
    chat_id = callback_query.message.chat.id
    user_id = callback_query.from_user.id
    setting_key = callback_query.data.replace("toggle_setting_", "")
    
    if not await is_admin_or_owner(client, chat_id, user_id):
        await callback_query.answer("⚠️ माफ़ करना, आप अब एडमिन नहीं हैं।", show_alert=True)
        return

    # 1. Fetch current status
    current_status_doc = group_tracking_collection.find_one({"_id": chat_id})
    # Get the current value, defaulting to False for filters and True for bot_enabled
    default_value = True if setting_key == "bot_enabled" else False
    current_value = current_status_doc.get(setting_key, default_value) if current_status_doc else default_value
    
    # 2. Calculate the new value
    new_value = not current_value
    
    # 3. Update the database
    group_tracking_collection.update_one(
        {"_id": chat_id},
        {"$set": {setting_key: new_value}},
        upsert=True
    )
    
    # 4. Refresh the menu
    await refresh_settings_menu(client, chat_id, callback_query.message.id, user_id)
    
    # 5. Answer the query
    action_text = "चालू" if new_value else "बंद"
    setting_name_map = {
        "bot_enabled": "बॉट चैटिंग",
        "linkdel_enabled": "लिंक डिलीट",
        "biolinkdel_enabled": "बायो लिंक डिलीट",
        "usernamedel_enabled": "@यूज़रनेम डिलीट"
    }
    setting_name = setting_name_map.get(setting_key, setting_key)
    
    await callback_query.answer(f"{setting_name} सफलतापूर्वक {action_text} कर दिया गया है।", show_alert=False)


@app.on_callback_query(filters.regex("open_punishment_settings"))
async def open_punishment_settings_callback(client: Client, callback_query: CallbackQuery):
    """Opens the submenu to select the default punishment."""
    chat_id = callback_query.message.chat.id
    user_id = callback_query.from_user.id

    if not await is_admin_or_owner(client, chat_id, user_id):
        await callback_query.answer("⚠️ माफ़ करना, आप अब एडमिन नहीं हैं।", show_alert=True)
        return

    current_status_doc = group_tracking_collection.find_one({"_id": chat_id})
    current_punishment = current_status_doc.get("default_punishment", "delete") if current_status_doc else "delete"
    
    # Punishment buttons with checkmark for current selection
    def get_punishment_button(action, label):
        checkmark = "✅ " if action == current_punishment else ""
        return InlineKeyboardButton(f"{checkmark}{label}", callback_data=f"set_punishment_{action}")

    keyboard = InlineKeyboardMarkup(
        [
            [
                get_punishment_button("delete", "🗑️ Dᴇʟᴇᴛᴇ Mᴇꜱꜱᴀɢᴇ"),
                get_punishment_button("mute", "🔇 Mᴜᴛᴇ Uꜱᴇʀ")
            ],
            [
                get_punishment_button("warn", "⚠️ Wᴀʀɴ Uꜱᴇʀ"),
                get_punishment_button("ban", "⛔️ Bᴀɴ Uꜱᴇʀ")
            ],
            [
                InlineKeyboardButton("🔙 Sᴇᴛᴛ𝗶𝗻𝗴ꜱ Mᴇɴᴜ", callback_data="settings_back_to_main")
            ]
        ]
    )
    
    punishment_message = (
        "🔨 **Dᴇ𝗳𝗮𝘂𝗹𝘁 Pᴜ𝗻𝗶𝘀𝗵𝗺𝗲𝗻𝘁 Sᴇ𝘁𝘁𝗶𝗻𝗴ꜱ** 🔨\n\n"
        "वह कार्रवाई चुनें जो बॉट यूज़र्स पर लागू करेगा जब वे किसी भी **फ़िल्टर नियम** (लिंक, बायो लिंक, यूज़रनेम) का उल्लंघन करेंगे।\n\n"
        f"**Cᴜʀ𝗿𝗲𝗻𝘁 Pᴜ𝗻𝗶𝘀𝗵𝗺𝗲𝗻𝘁:** **{current_punishment.upper()}**"
    )

    try:
        await client.edit_message_text(
            chat_id=chat_id,
            message_id=callback_query.message.id,
            text=punishment_message,
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        logger.error(f"Failed to edit punishment settings message in chat {chat_id}: {e}")

    await callback_query.answer()


@app.on_callback_query(filters.regex("^set_punishment_"))
async def set_punishment_callback(client: Client, callback_query: CallbackQuery):
    """Sets the new default punishment and returns to the main settings."""
    chat_id = callback_query.message.chat.id
    user_id = callback_query.from_user.id
    new_punishment = callback_query.data.replace("set_punishment_", "")
    
    if not await is_admin_or_owner(client, chat_id, user_id):
        await callback_query.answer("⚠️ माफ़ करना, आप अब एडमिन नहीं हैं।", show_alert=True)
        return

    # 1. Validate punishment
    valid_punishments = ["delete", "mute", "warn", "ban"]
    if new_punishment not in valid_punishments:
        await callback_query.answer("अमान्य सज़ा विकल्प।", show_alert=True)
        return

    # 2. Update the database
    group_tracking_collection.update_one(
        {"_id": chat_id},
        {"$set": {"default_punishment": new_punishment}},
        upsert=True
    )
    
    # 3. Refresh the main menu
    await refresh_settings_menu(client, chat_id, callback_query.message.id, user_id)
    
    # 4. Answer the query
    punishment_map = {
        "delete": "डिलीट मैसेज",
        "mute": "म्यूट",
        "warn": "वार्न",
        "ban": "बैन"
    }
    action_text = punishment_map.get(new_punishment, new_punishment).upper()
    await callback_query.answer(f"डिफ़ॉल्ट सज़ा अब **{action_text}** है।", show_alert=True)


@app.on_callback_query(filters.regex("open_biolink_exceptions"))
async def open_biolink_exceptions_callback(client: Client, callback_query: CallbackQuery):
    """Displays the biolink exception menu."""
    chat_id = callback_query.message.chat.id
    user_id = callback_query.from_user.id
    
    if not await is_admin_or_owner(client, chat_id, user_id):
        await callback_query.answer("⚠️ माफ़ करना, आप अब एडमिन नहीं हैं।", show_alert=True)
        return

    # 1. Fetch current exceptions for this chat
    exceptions = biolink_exceptions_collection.find_one({"_id": chat_id})
    exception_users = exceptions.get("user_ids", []) if exceptions else []
    
    # 2. Prepare the list of users
    list_text = "कोई छूट नहीं दी गई है। 🤷‍♀️"
    if exception_users:
        list_text = "\n".join([f"• `{uid}`" for uid in exception_users])

    message_text = (
        "📝 **बायो लिंक छूट (Exceptions)** 📝\n\n"
        "जिन यूज़र्स को आप उनके बायो में लिंक रखने की छूट देना चाहते हैं, उन्हें यहां जोड़ें। \n"
        "छूट देने या हटाने के लिए उनके **यूज़र ID** का उपयोग करें।\n\n"
        "**वर्तमान छूट वाले यूज़र्स:**\n"
        f"{list_text}\n\n"
        "**उपयोग:**\n"
        "• छूट देने के लिए: `/addbiolink <user_id>`\n"
        "• छूट हटाने के लिए: `/rembiolink <user_id>`\n\n"
        "_यह कमांड ग्रुप में ही टाइप करें।_"
    )

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔙 Sᴇᴛᴛ𝗶𝗻𝗴ꜱ Mᴇɴᴜ", callback_data="settings_back_to_main")]
        ]
    )

    try:
        await client.edit_message_text(
            chat_id=chat_id,
            message_id=callback_query.message.id,
            text=message_text,
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        logger.error(f"Failed to edit biolink exceptions message in chat {chat_id}: {e}")
        
    await callback_query.answer()


@app.on_callback_query(filters.regex("close_settings"))
async def close_settings_callback(client: Client, callback_query: CallbackQuery):
    """Closes and deletes the settings message."""
    chat_id = callback_query.message.chat.id
    user_id = callback_query.from_user.id

    if not await is_admin_or_owner(client, chat_id, user_id):
        await callback_query.answer("⚠️ माफ़ करना, आप अब एडमिन नहीं हैं।", show_alert=True)
        return

    try:
        await client.delete_messages(
            chat_id=chat_id,
            message_ids=callback_query.message.id
        )
        await callback_query.answer("सेटिंग्स मेन्यू बंद कर दिया गया।", show_alert=False)
    except Exception as e:
        # If deletion fails (e.g., bot not admin with delete rights)
        await callback_query.message.edit_text(
            "❌ **सेटिंग्स बंद** ❌\n\n_यह मैसेज 5 सेकंड में डिलीट हो जाएगा (अगर बॉट के पास परमिशन है)।_",
            reply_markup=None,
            parse_mode=ParseMode.MARKDOWN
        )
        await callback_query.answer("सेटिंग्स बंद हो गई है।", show_alert=False)
        await asyncio.sleep(5)
        try:
            await client.delete_messages(chat_id, callback_query.message.id)
        except:
            pass # Ignore final failure

# -----------------------------------------------------
# MAIN MENU / HELP / LEADERBOARD HANDLERS
# -----------------------------------------------------

@app.on_callback_query(filters.regex("show_help_menu"))
async def show_help_menu_callback(client: Client, callback_query: CallbackQuery):
    logger.info(f"Help menu callback triggered by user {callback_query.from_user.id} in chat {callback_query.message.chat.id}")
    
    help_message = (
        "यह रही आपकी मदद, डार्लिंग! 🥰\n\n"
        "**👥 ग्रुप कमांड्स (एडमिन के लिए):**\n"
        "• `/settings` - **सभी ग्रुप सेटिंग्स (चैटिंग, लिंक्स, यूज़रनेम फ़िल्टर, AI Mode और सज़ा) मैनेज करने के लिए मेन्यू खोलें।** (नया!)\n"
        "• `/setaimode` - **AI Bot की पर्सनालिटी सेट करें (e.g., Real Girl, Gemini)।** (नया!)\n"
        "• `/addbiolink <user_id>` - बायो लिंक फ़िल्टर से यूज़र को छूट दें।\n"
        "• `/rembiolink <user_id>` - बायो लिंक फ़िल्टर से यूज़र की छूट हटाएँ।\n\n"
        "**👤 सामान्य और निजी कमांड्स:**\n"
        "• `/start` - मुझे शुरू करो!\n"
        "• `/help` - यह हेल्प मेन्यू दिखाओ!\n"
        "• `/topusers` - सबसे ज़्यादा बातें करने वाले यूज़र्स!\n"
        "• `/stats check` - मेरी परफॉर्मेंस देखो! (निजी चैट में)\n"
        "• `/clearmydata` - अपना सारा डेटा डिलीट करो!\n\n"
        "अगर कोई और मदद चाहिए, तो बस पूछो! 😊"
    )

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("💰 Earning Rules", callback_data="show_earning_rules")],
            [InlineKeyboardButton("🔙 वापस जाएँ", callback_data="start_menu_from_help")]
        ]
    )

    await callback_query.message.edit_text(
        text=help_message,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True 
    )
    await callback_query.answer() 

@app.on_callback_query(filters.regex("show_earning_rules"))
async def show_earning_rules_callback(client: Client, callback_query: CallbackQuery):
    logger.info(f"Earning rules callback triggered by user {callback_query.from_user.id} in chat {callback_query.message.chat.id}")
    
    earning_rules_message = (
        "💰 **पैसे कमाने के नियम!** 💰\n\n"
        "यहां बताया गया है कि आप मेरे साथ कैसे कमा सकते हैं:\n"
        "1. **सक्रिय रहें:** ग्रुप में ज़्यादा से ज़्यादा मैसेज करें और बातचीत में हिस्सा लें।\n"
        "2. **मजेदार बनें:** अच्छे, क्वालिटी वाले और मजेदार मैसेज करें। स्पैमिंग से बचें!\n"
        "3. **हर महीने रीसेट:** हर महीने की पहली तारीख को लीडरबोर्ड रीसेट हो जाता है, ताकि सबको मौका मिले!\n"
        "4. **पुरस्कार:** टॉप यूज़र्स को हर महीने नकद पुरस्कार या प्रीमियम सब्सक्रिप्शन मिलते हैं।\n\n"
        f"ज़्यादा जानकारी के लिए मेरे मालिक @{ASBHAI_USERNAME} से संपर्क करें।\n\n"
        "चलो, अब बातें करो और जीतो! 🚀"
    )

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔙 Earning Leaderboard", callback_data="show_earning_leaderboard")]
        ]
    )

    await callback_query.message.edit_text(
        text=earning_rules_message,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True 
    )
    await callback_query.answer()

@app.on_callback_query(filters.regex("start_menu_from_help"))
async def back_to_start_from_help(client: Client, callback_query: CallbackQuery):
    logger.info(f"Back to start menu from help triggered by user {callback_query.from_user.id} in chat {callback_query.message.chat.id}")
    
    user_name = callback_query.from_user.first_name if callback_query.from_user else "Dost"
    welcome_message = (
        f"🌟 हे **{user_name}** जानू! आपका स्वागत है! 🌟\n\n"
        "मैं आपकी मदद करने के लिए तैयार हूँ!\n"
        "अपनी सभी कमांड्स देखने के लिए नीचे दिए गए 'सहायता' बटन पर क्लिक करें।"
    )
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("➕ मुझे ग्रुप में जोड़ें", url=f"https://t.me/{client.me.username}?startgroup=true")],
            [
                InlineKeyboardButton("📣 Updates Channel", url=f"https://t.me/{UPDATE_CHANNEL_USERNAME}"),
                InlineKeyboardButton("❓ Support Group", url="https://t.me/aschat_group")
            ],
            [
                InlineKeyboardButton("ℹ️ सहायता ❓", callback_data="show_help_menu"),
                InlineKeyboardButton("💰 Earning Leaderboard", callback_data="show_earning_leaderboard")
            ]
        ]
    )
    # फोटो हटाने के लिए edit_message_text का उपयोग करें
    await callback_query.message.edit_text(
        text=welcome_message,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True 
    )
    await callback_query.answer()

@app.on_callback_query(filters.regex("show_earning_leaderboard"))
async def show_earning_leaderboard_callback(client: Client, callback_query: CallbackQuery):
    logger.info(f"Earning leaderboard callback triggered by user {callback_query.from_user.id} in chat {callback_query.message.chat.id}")
    
    top_users = await get_top_earning_users()
    if not top_users:
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔙 मुख्य मेन्यू", callback_data="start_menu_from_help")]]
        )
        await callback_query.message.edit_text(text="😢 अब तक कोई भी उपयोगकर्ता लीडरबोर्ड पर नहीं है! सक्रिय होकर पहले बनें! ✨\n\n**Powered By:** @asbhaibsr", parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard, disable_web_page_preview=True)
        await callback_query.answer()
        return

    earning_messages = ["👑 **Top Active Users - ✨ VIP Leaderboard! ✨** 👑\n\n"]
    prizes = {
        1: "💰 ₹50", 2: "💸 ₹30", 3: "🎁 ₹20",
        4: f"🎬 @{ASFILTER_BOT_USERNAME} का 1 हफ़्ते का प्रीमियम प्लान",
        5: f"🎬 @{ASFILTER_BOT_USERNAME} का 3 दिन का प्रीमियम प्लान"
    }

    for i, user in enumerate(top_users[:5]):
        rank = i + 1
        user_name = user.get('first_name', 'Unknown User')
        username_str = f"@{user.get('username')}" if user.get('username') else f"ID: `{user.get('user_id')}`"
        message_count = user.get('message_count', 0)
        prize_str = prizes.get(rank, "🏅 कोई पुरस्कार नहीं")

        group_info = ""
        last_group_id = user.get('last_active_group_id')
        last_group_title = user.get('last_active_group_title', 'Unknown Group')

        if last_group_id:
            try:
                chat_obj = await client.get_chat(last_group_id)
                if chat_obj.type == ChatType.PRIVATE:
                    group_info = f"   • सक्रिय था: **[निजी चैट में](tg://user?id={user.get('user_id')})**\n"
                elif chat_obj.username:
                    group_info = f"   • सक्रिय था: **[{chat_obj.title}](https://t.me/{chat_obj.username})**\n"
                else:
                    try:
                        invite_link = await client.export_chat_invite_link(last_group_id)
                        group_info = f"   • सक्रिय था: **[{chat_obj.title}]({invite_link})**\n"
                    except Exception:
                        group_info = f"   • सक्रिय था: **{chat_obj.title}** (निजी ग्रुप)\n"
            except Exception as e:
                logger.warning(f"Could not fetch chat info for group ID {last_group_id} for leaderboard: {e}")
                group_info = f"   • सक्रिय था: **{last_group_title}** (जानकारी उपलब्ध नहीं)\n"
        else:
            group_info = "   • सक्रिय था: **कोई ग्रुप गतिविधि नहीं**\n"

        earning_messages.append(
            f"**{rank}.** 🌟 **{user_name}** ({username_str}) 🌟\n"
            f"   • कुल मैसेज: **{message_count} 💬**\n"
            f"   • संभावित पुरस्कार: **{prize_str}**\n"
            f"{group_info}"
        )
    
    earning_messages.append(
        "\n_हर महीने की पहली तारीख को यह सिस्टम रीसेट होता है!_\n"
        "_ग्रुप के नियमों को जानने के लिए `/help` का उपयोग करें।_"
    )
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("💰 पैसे निकलवाएँ (Withdraw)", url=f"https://t.me/{ASBHAI_USERNAME}"),
                InlineKeyboardButton("💰 Earning Rules", callback_data="show_earning_rules")
            ]
        ]
    )
    await callback_query.message.edit_text(text="\n".join(earning_messages), reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
    await callback_query.answer()

# -----------------------------------------------------
# OWNER-ONLY CALLBACK HANDLERS
# -----------------------------------------------------

@app.on_callback_query(filters.regex("confirm_clearall_dbs"))
async def confirm_clearall_dbs_callback(client: Client, callback_query: CallbackQuery):
    logger.info(f"Clear All DBs confirmation received from owner {callback_query.from_user.id}")
    if callback_query.from_user.id != OWNER_ID:
        await callback_query.answer("⚠️ आप अधिकृत नहीं हैं।", show_alert=True)
        return

    try:
        messages_collection.drop()
        buttons_collection.drop()
        group_tracking_collection.drop()
        user_tracking_collection.drop()
        owner_taught_responses_collection.drop()
        conversational_learning_collection.drop()
        biolink_exceptions_collection.drop()
        earning_tracking_collection.drop()
        reset_status_collection.drop()

        await callback_query.message.edit_text(
            "🎉 **बॉस! आपका पूरा डेटाबेस सफ़ाई से चमक रहा है!** ✨\n"
            "सभी संग्रह (collections) सफलतापूर्वक हटा दिए गए हैं।\n"
            "एकदम नया स्टार्ट! 🚀",
            parse_mode=ParseMode.MARKDOWN
        )
        logger.info(f"Owner {callback_query.from_user.id} successfully cleared all MongoDB collections.")
    except Exception as e:
        await callback_query.message.edit_text(
            f"डेटाबेस साफ़ करते समय एरर: {e}. ओह नो! 😱",
            parse_mode=ParseMode.MARKDOWN
        )
        logger.error(f"Error clearing all databases: {e}")
    
    await callback_query.answer("डेटाबेस साफ़ किया गया!", show_alert=True)

@app.on_callback_query(filters.regex("cancel_clearall_dbs"))
async def cancel_clearall_dbs_callback(client: Client, callback_query: CallbackQuery):
    logger.info(f"Clear All DBs cancellation received from owner {callback_query.from_user.id}")
    if callback_query.from_user.id != OWNER_ID:
        await callback_query.answer("⚠️ आप अधिकृत नहीं हैं।", show_alert=True)
        return
    
    await callback_query.message.edit_text(
        "ठीक है! ✅ डेटाबेस की सफ़ाई रद्द कर दी गई है।\n"
        "आपका डेटा सुरक्षित है। 😉",
        parse_mode=ParseMode.MARKDOWN
    )
    await callback_query.answer("रद्द किया गया!", show_alert=True)
