# handlers/callback_handlers.py

from pyrogram import Client
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode

from config import ASBHAI_USERNAME, ASFILTER_BOT_USERNAME, REPO_LINK, OWNER_ID
from database.mongo_setup import buttons_collection, client_messages, client_buttons, client_tracking
from utils.helpers import logger, send_and_auto_delete_reply
from handlers.command_handlers import top_users_command # Import top_users_command to reuse logic

async def callback_handler(client: Client, callback_query: CallbackQuery):
    # Answer the callback query immediately to remove loading state
    await callback_query.answer()

    if callback_query.data == "buy_git_repo":
        await send_and_auto_delete_reply(
            callback_query.message,
            text=f"🤩 अगर आपको मेरे जैसा खुद का bot बनवाना है, तो आपको ₹500 देने होंगे. इसके लिए **@{ASBHAI_USERNAME}** से contact करें और unhe bataiye ki aapko is bot ka code chahiye banwane ke liye. Jaldi karo, deals hot hain! 💸\n\n**Owner:** @asbhaibsr\n**Updates:** @asbhai_bsr\n**Support:** @aschat_group",
            parse_mode=ParseMode.MARKDOWN
        )
        buttons_collection.insert_one({
            "user_id": callback_query.from_user.id,
            "username": callback_query.from_user.username,
            "first_name": callback_query.from_user.first_name,
            "button_data": callback_query.data,
            "timestamp": datetime.now(),
            "credit": "by @asbhaibsr"
        })
    elif callback_query.data == "show_earning_leaderboard":
        await top_users_command(client, callback_query.message) # Pass the original message object
        buttons_collection.insert_one({
            "user_id": callback_query.from_user.id,
            "username": callback_query.from_user.username,
            "first_name": callback_query.from_user.first_name,
            "button_data": callback_query.data,
            "timestamp": datetime.now(),
            "credit": "by @asbhaibsr"
        })
    elif callback_query.data == "show_help_menu":
        help_text = (
            "💡 **Main Kaise Kaam Karti Hoon?**\n\n"
            "Main ek self-learning bot hoon jo conversations se seekhti hai. Aap groups mein ya mujhse private mein baat kar sakte hain, aur main aapke messages ko yaad rakhti hoon. Jab koi user similar baat karta hai, toh main usse seekhe hue reply deti hoon.\n\n"
            "**✨ Meri Commands:**\n"
            "• `/start`: Mujhse baat shuru karne ke liye.\n"
            "• `/help`: Yeh menu dekhne ke liye (jo aap abhi dekh rahe hain!).\n"
            "• `/topusers`: Sabse active users ka leaderboard dekhne ke liye.\n"
            "• `/clearmydata`: Apni saari baatein (jo maine store ki hain) delete karne ke liye.\n"
            "• `/chat on/off`: (Sirf Group Admins ke liye) Group mein meri messages band/chalu karne ke liye.\n"
            "• `/groups`: (Sirf Owner ke liye) Jin groups mein main hoon, unki list dekhne ke liye.\n"
            "• `/stats check`: Bot ke statistics dekhne ke liye.\n"
            "• `/cleardata <percentage>`: (Sirf Owner ke liye) Database se data delete karne ke liye.\n"
            "• `/deletemessage <content/sticker_id>`: (Sirf Owner ke liye) Specific message ya sticker delete karne ke liye.\n" # Updated help text
            "• `/clearearning`: (Sirf Owner ke liye) Earning data reset karne ke liye.\n"
            "• `/clearall`: (Sirf Owner ke liye) Saara database (3 DBs) clear karne ke liye. **(Dhyan se!)**\n"
            "• `/leavegroup <group_id>`: (Sirf Owner ke liye) Kisi group ko chhodne ke liye.\n"
            "• `/broadcast <message>`: (Sirf Owner ke liye) Sabhi groups mein message bhejne ke liye.\n"
            "• `/restart`: (Sirf Owner ke liye) Bot ko restart karne ke liye.\n"
            "• `/linkdel on/off`: (Sirf Group Admins ke liye) Group mein **sabhi prakar ke links** delete/allow karne ke liye.\n"
            "• `/biolinkdel on/off`: (Sirf Group Admins ke liye) Group mein **users ke bio mein `t.me` aur `http/https` links** wale messages ko delete/allow karne ke liye.\n"
            "• `/biolink <userid>`: (Sirf Group Admins ke liye) `biolinkdel` on hone par bhi kisi user ko **bio mein `t.me` aur `http/https` links** रखने की permission dene ke liye.\n"
            "• `/usernamedel on/off`: (Sirf Group Admins ke liye) Group mein **'@' mentions** allow ya delete karne ke liye.\n\n"
            "**🔗 Mera Code (GitHub Repository):**\n"
            f"[**{REPO_LINK}**]({REPO_LINK})\n\n"
            "**Powered By:** @asbhaibsr\n**Updates:** @asbhai_bsr\n**Support:** @aschat_group"
        )
        await send_and_auto_delete_reply(callback_query.message, text=help_text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        buttons_collection.insert_one({
            "user_id": callback_query.from_user.id,
            "username": callback_query.from_user.username,
            "first_name": callback_query.from_user.first_name,
            "button_data": callback_query.data,
            "timestamp": datetime.now(),
            "credit": "by @asbhaibsr"
        })
    elif callback_query.data == "show_earning_rules":
        earning_rules_text = (
            "👑 **Earning Rules - VIP Guide!** 👑\n\n"
            "यहाँ बताया गया है कि आप मेरे साथ कैसे कमाई कर सकते हैं:\n\n"
            "**1. सक्रिय रहें (Be Active):**\n"
            "   • आपको ग्रुप में **वास्तविक और सार्थक बातचीत** करनी होगी।\n"
            "   • बेतरतीब मैसेज, स्पैमिंग, या सिर्फ़ इमोजी भेजने से आपकी रैंकिंग नहीं बढ़ेगी और आप अयोग्य भी हो सकते हैं।\n"
            "   • जितनी ज़्यादा अच्छी बातचीत, उतनी ज़्यादा कमाई के अवसर!\n\n"
            "**2. क्या करें, क्या न करें (Do's and Don'ts):**\n"
            "   • **करें:** सवालों के जवाब दें, चर्चा में भाग लें, नए विषय शुरू करें, अन्य सदस्यों के साथ इंटरैक्ट करें।\n"
            "   • **न करें:** बार-बार एक ही मैसेज भेजें, सिर्फ़ स्टिकर या GIF भेजें, असंबद्ध सामग्री पोस्ट करें, या ग्रुप के नियमों का उल्लंघन करें।\n\n"
            "**3. कमाई का समय (Earning Period):**\n"
            "   • कमाई हर **महीने** के पहले दिन रीसेट होगी। इसका मतलब है कि हर महीने आपके पास टॉप पर आने का एक नया मौका होगा!\n\n"
            "**4. अयोग्य होना (Disqualification):**\n"
            "   • यदि आप स्पैमिंग करते हुए पाए जाते हैं, या किसी भी तरह से सिस्टम का दुरुपयोग करने की कोशिश करते हैं, तो आपको लीडरबोर्ड से हटा दिया जाएगा और आप भविष्य की कमाई के लिए अयोग्य घोषित हो सकते हैं।\n"
            "   • ग्रुप के नियमों का पालन करना अनिवार्य है।\n\n"
            "**5. विथड्रावल (Withdrawal):**\n"
            "   • विथड्रावल हर महीने के **पहले हफ़्ते** में होगा।\n"
            "   • अपनी कमाई निकालने के लिए, आपको मुझे `@asbhaibsr` पर DM (डायरेक्ट मैसेज) करना होगा।\n\n"
            "**शुभकामनाएँ!** 🍀\n"
            "मुझे आशा है कि आप सक्रिय रहेंगे और हमारी कम्युनिटी में योगदान देंगे।\n\n"
            "**Powered By:** @asbhaibsr\n**Updates:** @asbhai_bsr\n**Support:** @aschat_group"
        )
        await send_and_auto_delete_reply(callback_query.message, text=earning_rules_text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        buttons_collection.insert_one({
            "user_id": callback_query.from_user.id,
            "username": callback_query.from_user.username,
            "first_name": callback_query.from_user.first_name,
            "button_data": callback_query.data,
            "timestamp": datetime.now(),
            "credit": "by @asbhaibsr"
        })

    logger.info(f"Callback query '{callback_query.data}' processed for user {callback_query.from_user.id}. (Code by @asbhaibsr)")


async def handle_clearall_dbs_callback(client: Client, callback_query: CallbackQuery):
    query = callback_query

    # Answer the callback query immediately to remove loading state
    await query.answer()

    if query.from_user.id != OWNER_ID:
        await query.edit_message_text("आप इस कार्रवाई को अधिकृत नहीं हैं।")
        return

    if query.data == 'confirm_clearall_dbs':
        await query.edit_message_text("डेटा डिलीट किया जा रहा है... कृपया प्रतीक्षा करें।⏳")
        try:
            # Drop all databases for client_messages
            for db_name in client_messages.list_database_names():
                if db_name not in ["admin", "local", "config"]: # Avoid dropping system databases
                    client_messages.drop_database(db_name)
                    logger.info(f"Dropped messages database: {db_name}.")
            
            # Drop all databases for client_buttons
            for db_name in client_buttons.list_database_names():
                if db_name not in ["admin", "local", "config"]:
                    client_buttons.drop_database(db_name)
                    logger.info(f"Dropped buttons database: {db_name}.")

            # Drop all databases for client_tracking
            for db_name in client_tracking.list_database_names():
                if db_name not in ["admin", "local", "config"]:
                    client_tracking.drop_database(db_name)
                    logger.info(f"Dropped tracking database: {db_name}.")


            await query.edit_message_text("✅ **सफलतापूर्वक:** आपकी सभी MongoDB डेटाबेस का सारा डेटा डिलीट कर दिया गया है। बॉट अब बिल्कुल नया हो गया है! ✨", parse_mode=ParseMode.MARKDOWN)
            logger.info(f"Owner {query.from_user.id} confirmed and successfully cleared all MongoDB databases.")
        except Exception as e:
            await query.edit_message_text(f"❌ **त्रुटि:** डेटा डिलीट करने में समस्या आई: {e}\n\nकृपया लॉग्स चेक करें।", parse_mode=ParseMode.MARKDOWN)
            logger.error(f"Error during /clearall confirmation and deletion: {e}")
    elif query.data == 'cancel_clearall_dbs':
        await query.edit_message_text("कार्यवाही रद्द कर दी गई है। आपका डेटा सुरक्षित है। ✅", parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Owner {query.from_user.id} cancelled /clearall operation.")

