from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode, ChatType
import asyncio

# आपको यहां 'app' और 'logger' और अन्य CONFIG वेरिएबल्स को इम्पोर्ट करना होगा
# सुनिश्चित करें कि आपकी 'config.py' से ये सही ढंग से इम्पोर्ट हो रहे हैं।
from config import (
    app, logger, ASBHAI_USERNAME, ASFILTER_BOT_USERNAME, OWNER_ID, UPDATE_CHANNEL_USERNAME,
    buttons_collection, group_tracking_collection, user_tracking_collection,
    messages_collection, owner_taught_responses_collection, conversational_learning_collection,
    biolink_exceptions_collection, earning_tracking_collection, reset_status_collection
)

# utils.py से आवश्यक फ़ंक्शन इम्पोर्ट करें
from utils import get_top_earning_users, send_and_auto_delete_reply, store_message, update_user_info, update_group_info

@app.on_callback_query(filters.regex("show_help_menu"))
async def show_help_menu_callback(client: Client, callback_query: CallbackQuery):
    logger.info(f"Help menu callback triggered by user {callback_query.from_user.id} in chat {callback_query.message.chat.id}")
    
    help_message = (
        "यह रही आपकी मदद, डार्लिंग! 🥰\n\n"
        "मेरे कुछ कमांड्स:\n"
        "• `/start` - मुझे शुरू करो!\n"
        "• `/help` - यह हेल्प मेन्यू दिखाओ!\n"
        "• `/topusers` - सबसे ज़्यादा बातें करने वाले यूज़र्स!\n"
        "• `/stats check` - मेरी परफॉर्मेंस देखो!\n"
        "• `/chat on/off` - ग्रुप में मुझे चालू/बंद करो (एडमिन के लिए)\n"
        "• `/linkdel on/off` - लिंक्स डिलीट करने का फीचर ऑन/ऑफ करो (एडमिन के लिए)\n"
        "• `/biolinkdel on/off` - बायो-लिंक्स डिलीट करने का फीचर ऑन/ऑफ करो (एडमिन के लिए)\n"
        "• `/biolink <user_id>` / `/biolink remove <user_id>` - किसी यूज़र को बायो-लिंक से छूट दो/हटाओ (एडमिन के लिए)\n"
        "• `/usernamedel on/off` - @usernames डिलीट करने का फीचर ऑन/ऑफ करो (एडमिन के लिए)\n"
        "• `/clearmydata` - अपना सारा डेटा डिलीट करो (बॉस के लिए `clearmydata <user_id>`)\n\n"
        "अगर कोई और मदद चाहिए, तो बस पूछो! 😊"
    )

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("💰 Earning Rules", callback_data="show_earning_rules")],
            [InlineKeyboardButton("🔙 वापस जाएँ", callback_data="start_menu_from_help")] # 'वापस जाएँ' बटन जोड़ा
        ]
    )

    # callback_query.message.edit_text का उपयोग करें क्योंकि यह एक मौजूदा मैसेज को एडिट कर रहा है
    await callback_query.message.edit_text(
        text=help_message,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )
    await callback_query.answer() # कॉलबैक क्वेरी को स्वीकार करें

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
            [InlineKeyboardButton("🔙 Earning Leaderboard", callback_data="show_earning_leaderboard")] # Earning Leaderboard पर वापस जाने के लिए
        ]
    )

    await callback_query.message.edit_text(
        text=earning_rules_message,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )
    await callback_query.answer() # कॉलबैक क्वेरी को स्वीकार करें

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
    # यहां send_and_auto_delete_reply की जगह edit_message_text का उपयोग करें
    await callback_query.message.edit_text(
        text=welcome_message,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True # अगर इसमें कोई लिंक है तो उसका प्रीव्यू डिसेबल करें
    )
    await callback_query.answer()

@app.on_callback_query(filters.regex("show_earning_leaderboard"))
async def show_earning_leaderboard_callback(client: Client, callback_query: CallbackQuery):
    logger.info(f"Earning leaderboard callback triggered by user {callback_query.from_user.id} in chat {callback_query.message.chat.id}")
    
    top_users = await get_top_earning_users()
    if not top_users:
        await callback_query.message.edit_text(text="😢 अब तक कोई भी उपयोगकर्ता लीडरबोर्ड पर नहीं है! सक्रिय होकर पहले बनें! ✨\n\n**Powered By:** @asbhaibsr", parse_mode=ParseMode.MARKDOWN)
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

# --- clearall_dbs के लिए कॉलबैक हैंडलर ---
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
