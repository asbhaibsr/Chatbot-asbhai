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
from utils import get_top_earning_users, send_and_auto_delete_reply, store_message, update_user_info, update_group_info, is_admin_or_owner


# -----------------------------------------------------
# UTILITY FUNCTIONS FOR SETTINGS
# -----------------------------------------------------

# यह फ़ंक्शन सेटिंग्स मैसेज को री-जनरेट और एडिट करने के लिए है
async def refresh_settings_menu(client: Client, chat_id: int, message_id: int, user_id: int):
    """Fetches current settings, generates the settings keyboard, and edits the message."""
    
    # Check Admin/Owner status again (in case an old button is pressed)
    if not await is_admin_or_owner(client, chat_id, user_id):
        return  # Do nothing if the user is no longer an admin

    # 1. Fetch current settings and default punishment
    current_status_doc = group_tracking_collection.find_one({"_id": chat_id})
    
    # Default values if not found
    bot_enabled = current_status_doc.get("bot_enabled", True) if current_status_doc else True
    linkdel_enabled = current_status_doc.get("linkdel_enabled", False) if current_status_doc else False
    biolinkdel_enabled = current_status_doc.get("biolinkdel_enabled", False) if current_status_doc else False
    usernamedel_enabled = current_status_doc.get("usernamedel_enabled", False) if current_status_doc else False
    
    punishment = current_status_doc.get("default_punishment", "delete") if current_status_doc else "delete"
    
    # Status texts
    bot_status = "✅ चालू (ON)" if bot_enabled else "❌ बंद (OFF)"
    link_status = "✅ चालू (ON)" if linkdel_enabled else "❌ बंद (OFF)"
    biolink_status = "✅ चालू (ON)" if biolinkdel_enabled else "❌ बंद (OFF)"
    username_status = "✅ चालू (ON)" if usernamedel_enabled else "❌ बंद (OFF)"
    
    # Punishment text
    punishment_map = {
        "delete": "🗑️ डिलीट मैसेज",
        "mute": "🔇 म्यूट करें",
        "warn": "⚠️ वार्न करें",
        "ban": "⛔️ बैन करें"
    }
    punishment_text = punishment_map.get(punishment, "🗑️ डिलीट मैसेज")

    # 2. Create the Main Settings Keyboard
    keyboard = InlineKeyboardMarkup(
        [
            # Module Toggles
            [
                InlineKeyboardButton(f"🤖 बॉट चैटिंग: {bot_status}", callback_data="toggle_setting_bot_enabled"),
            ],
            [
                InlineKeyboardButton(f"🔗 लिंक डिलीट: {link_status}", callback_data="toggle_setting_linkdel_enabled"),
            ],
            [
                InlineKeyboardButton(f"👤 बायो लिंक डिलीट: {biolink_status}", callback_data="toggle_setting_biolinkdel_enabled"),
            ],
            [
                InlineKeyboardButton(f"🗣️ @यूज़रनेम डिलीट: {username_status}", callback_data="toggle_setting_usernamedel_enabled"),
            ],
            # Punishment and Biolink Exception
            [
                InlineKeyboardButton(f"🔨 डिफ़ॉल्ट सज़ा: {punishment_text}", callback_data="open_punishment_settings"),
            ],
            [
                 InlineKeyboardButton("👤 बायो लिंक छूट (Exceptions) 📝", callback_data="open_biolink_exceptions")
            ],
            # Close Button
            [
                InlineKeyboardButton("❌ सेटिंग्स बंद करें", callback_data="close_settings")
            ]
        ]
    )

    # 3. Generate the Settings Message
    settings_message = (
        f"⚙️ **ग्रुप सेटिंग्स** 🛠️\n\n"
        "नमस्ते, बॉस! आप नीचे दिए गए बटनों से ग्रुप के नियम और बॉट के फ़ंक्शंस कंट्रोल कर सकते हैं।\n"
        "आपके सभी फ़िल्टर सेटिंग्स को तोड़ने पर यूज़र्स को **डिफ़ॉल्ट सज़ा** मिलेगी।\n\n"
        f"**डिफ़ॉल्ट सज़ा:** {punishment_text}\n"
        "__नियमों को तोड़ने वाले को कौनसी सज़ा देनी है, वो 'डिफ़ॉल्ट सज़ा' से चुनें।__"
    )

    # 4. Edit the message
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
# NEW SETTINGS HANDLERS
# -----------------------------------------------------

@app.on_callback_query(filters.regex("open_group_settings"))
@app.on_callback_query(filters.regex("settings_back_to_main"))
async def open_settings_from_callback(client: Client, callback_query: CallbackQuery):
    """Opens or returns to the main settings menu."""
    if not await is_admin_or_owner(client, callback_query.message.chat.id, callback_query.from_user.id):
        await callback_query.answer("माफ़ करना, आप अब एडमिन नहीं हैं।", show_alert=True)
        return

    # Call the refresh function to display the main settings
    await refresh_settings_menu(
        client,
        callback_query.message.chat.id,
        callback_query.message.id,
        callback_query.from_user.id
    )
    await callback_query.answer()


@app.on_callback_query(filters.regex("^toggle_setting_"))
async def toggle_setting_callback(client: Client, callback_query: CallbackQuery):
    """Toggles a specific setting (bot_enabled, linkdel_enabled, etc.)."""
    chat_id = callback_query.message.chat.id
    user_id = callback_query.from_user.id
    setting_key = callback_query.data.replace("toggle_setting_", "")
    
    if not await is_admin_or_owner(client, chat_id, user_id):
        await callback_query.answer("माफ़ करना, आप अब एडमिन नहीं हैं।", show_alert=True)
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
        await callback_query.answer("माफ़ करना, आप अब एडमिन नहीं हैं।", show_alert=True)
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
                get_punishment_button("delete", "🗑️ डिलीट मैसेज"),
                get_punishment_button("mute", "🔇 म्यूट करें")
            ],
            [
                get_punishment_button("warn", "⚠️ वार्न करें"),
                get_punishment_button("ban", "⛔️ बैन करें")
            ],
            [
                InlineKeyboardButton("🔙 सेटिंग्स मेन्यू", callback_data="settings_back_to_main")
            ]
        ]
    )
    
    punishment_message = (
        "🔨 **डिफ़ॉल्ट सज़ा सेटिंग्स** 🔨\n\n"
        "वह कार्रवाई चुनें जो बॉट यूज़र्स पर लागू करेगा जब वे किसी भी **फ़िल्टर नियम** (लिंक, बायो लिंक, यूज़रनेम) का उल्लंघन करेंगे।\n\n"
        f"**वर्तमान सज़ा:** **{current_punishment.upper()}**"
    )

    await client.edit_message_text(
        chat_id=chat_id,
        message_id=callback_query.message.id,
        text=punishment_message,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )
    await callback_query.answer()


@app.on_callback_query(filters.regex("^set_punishment_"))
async def set_punishment_callback(client: Client, callback_query: CallbackQuery):
    """Sets the new default punishment and returns to the main settings."""
    chat_id = callback_query.message.chat.id
    user_id = callback_query.from_user.id
    new_punishment = callback_query.data.replace("set_punishment_", "")
    
    if not await is_admin_or_owner(client, chat_id, user_id):
        await callback_query.answer("माफ़ करना, आप अब एडमिन नहीं हैं।", show_alert=True)
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
        await callback_query.answer("माफ़ करना, आप अब एडमिन नहीं हैं।", show_alert=True)
        return

    # 1. Fetch current exceptions for this chat
    exceptions = biolink_exceptions_collection.find_one({"_id": chat_id})
    exception_users = exceptions.get("user_ids", []) if exceptions else []
    
    # 2. Prepare the list of users (fetching usernames/first names is tricky here, so we show IDs for simplicity)
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
            [InlineKeyboardButton("🔙 सेटिंग्स मेन्यू", callback_data="settings_back_to_main")]
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
        await callback_query.answer("माफ़ करना, आप अब एडमिन नहीं हैं।", show_alert=True)
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
# EXISTING HANDLERS (UPDATED /HELP)
# -----------------------------------------------------

@app.on_callback_query(filters.regex("show_help_menu"))
async def show_help_menu_callback(client: Client, callback_query: CallbackQuery):
    logger.info(f"Help menu callback triggered by user {callback_query.from_user.id} in chat {callback_query.message.chat.id}")
    
    help_message = (
        "यह रही आपकी मदद, डार्लिंग! 🥰\n\n"
        "**👥 ग्रुप कमांड्स (एडमिन के लिए):**\n"
        "• `/settings` - **सभी ग्रुप सेटिंग्स (चैटिंग, लिंक्स, यूज़रनेम फ़िल्टर और सज़ा) मैनेज करने के लिए मेन्यू खोलें।** (नया!)\n"
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
        parse_mode=ParseMode.MARKDOWN
    )
    await callback_query.answer() 

# -----------------------------------------------------
# UNCHANGED EXISTING HANDLERS
# -----------------------------------------------------

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
        parse_mode=ParseMode.MARKDOWN
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
        await callback_query.message.edit_text(text="😢 अब तक कोई भी उपयोगकर्ता लीडरबोर्ड पर नहीं है! सक्रिय होकर पहले बनें! ✨\n\n**Powered By:** @asbhaibsr", parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
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

# --- clearall_dbs के लिए कॉलबैक हैंडलर (UNCHANGED) ---
@app.on_callback_query(filters.regex("confirm_clearall_dbs"))
async def confirm_clearall_dbs_callback(client: Client, callback_query: CallbackQuery):
    logger.info(f"Clear All DBs confirmation received from owner {callback_query.from_user.id}")
    if callback_query.from_user.id != OWNER_ID:
        await callback_query.answer("आप अधिकृत नहीं हैं।", show_alert=True)
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
        await callback_query.answer("आप अधिकृत नहीं हैं।", show_alert=True)
        return
    
    await callback_query.message.edit_text(
        "ठीक है! ✅ डेटाबेस की सफ़ाई रद्द कर दी गई है।\n"
        "आपका डेटा सुरक्षित है। 😉",
        parse_mode=ParseMode.MARKDOWN
    )
    await callback_query.answer("रद्द किया गया!", show_alert=True)
