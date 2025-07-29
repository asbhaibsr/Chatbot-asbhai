# events.py

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatType, ParseMode
import asyncio
from datetime import datetime

# Import utilities and configurations
from config import (
    app, buttons_collection, group_tracking_collection, user_tracking_collection,
    messages_collection, owner_taught_responses_collection, conversational_learning_collection,
    biolink_exceptions_collection, earning_tracking_collection, logger,
    OWNER_ID, ASBHAI_USERNAME, URL_PATTERN
)
from utils import (
    update_group_info, update_user_info, store_message, generate_reply,
    can_reply_to_chat, update_message_reply_cooldown, delete_after_delay_for_message,
    is_admin_or_owner, contains_link, contains_mention
)

@app.on_callback_query()
async def callback_handler(client, callback_query):
    await callback_query.answer()

    if callback_query.data == "buy_git_repo":
        await send_and_auto_delete_reply(
            callback_query.message,
            text=f"🤩 अगर आपको मेरे जैसा खुद का bot बनवाना है, तो आपको ₹500 देने होंगे. इसके लिए **@{ASBHAI_USERNAME}** से contact करें और unhe bataiye ki aapko is bot ka code chahiye banwane ke liye. Jaldi karo, deals hot hain! 💸\n\n**Owner:** @asbhaibsr\n**Updates:** @asbhai_bsr\n**Support:** @asbhai_bsr", # Fixed support group username
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
        # Import top_users_command dynamically to avoid circular dependency
        from commands import top_users_command 
        await top_users_command(client, callback_query.message)
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
            "• `/deletemessage <content>`: (Sirf Owner ke liye) Specific **text message** delete karne ke liye.\n"
            "• `/delsticker <percentage>`: (Sirf Owner ke liye) Database se **stickers** delete karne ke liye (e.g., `10%`, `20%`, `40%`).\n"
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
            f"[**REPO_LINK**]({ASBHAI_USERNAME})\n\n" # Assuming REPO_LINK is defined in config.py or elsewhere, if not, remove or replace with actual link
            "**Powered By:** @asbhaibsr\n**Updates:** @asbhai_bsr\n**Support:** @aschat_group" # Fixed support group username
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
            "**Powered By:** @asbhaibsr\n**Updates:** @asbhai_bsr\n**Support:** @aschat_group" # Fixed support group username
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

@app.on_callback_query(filters.regex("^(confirm_clearall_dbs|cancel_clearall_dbs)$"))
async def handle_clearall_dbs_callback(client: Client, callback_query):
    query = callback_query
    await query.answer()

    if query.from_user.id != OWNER_ID:
        await query.edit_message_text("आप इस कार्रवाई को अधिकृत नहीं हैं।")
        return

    if query.data == 'confirm_clearall_dbs':
        await query.edit_message_text("डेटा डिलीट किया जा रहा है... कृपया प्रतीक्षा करें।⏳")
        try:
            messages_collection.drop()
            logger.info("messages_collection dropped.")
            buttons_collection.drop()
            logger.info("buttons_collection dropped.")
            group_tracking_collection.drop()
            logger.info("group_tracking_collection dropped.")
            user_tracking_collection.drop()
            logger.info("user_tracking_collection dropped.")
            earning_tracking_collection.drop()
            logger.info("earning_tracking_collection dropped.")
            # Assuming reset_status_collection is defined in config.py
            # If not, you might need to import it or define it.
            # If it's not used, you can remove this line.
            if 'reset_status_collection' in globals(): # Check if it's defined
                reset_status_collection.drop()
                logger.info("reset_status_collection dropped.")
            biolink_exceptions_collection.drop()
            logger.info("biolink_exceptions_collection dropped.")
            owner_taught_responses_collection.drop()
            logger.info("owner_taught_responses_collection dropped.")
            conversational_learning_collection.drop()
            logger.info("conversational_learning_collection dropped.")

            await query.edit_message_text("✅ **सफलतापूर्वक:** आपकी सभी MongoDB डेटाबेस का सारा डेटा डिलीट कर दिया गया है। बॉट अब बिल्कुल नया हो गया है! ✨", parse_mode=ParseMode.MARKDOWN)
            logger.info(f"Owner {query.from_user.id} confirmed and successfully cleared all MongoDB data.")
        except Exception as e:
            await query.edit_message_text(f"❌ **त्रुटि:** डेटा डिलीट करने में समस्या आई: {e}\n\nकृपया लॉग्स चेक करें।", parse_mode=ParseMode.MARKDOWN)
            logger.error(f"Error during /clearall confirmation and deletion: {e}")
    elif query.data == 'cancel_clearall_dbs':
        await query.edit_message_text("कार्यवाही रद्द कर दी गई है। आपका डेटा सुरक्षित है। ✅", parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Owner {query.from_user.id} cancelled /clearall operation.")

@app.on_message(filters.new_chat_members)
async def new_member_handler(client: Client, message: Message):
    logger.info(f"New chat members detected in chat {message.chat.id}. Bot ID: {client.me.id}. (Event handled by @asbhaibsr)")

    for member in message.new_chat_members:
        logger.info(f"Processing new member: {member.id} ({member.first_name}) in chat {message.chat.id}. Is bot: {member.is_bot}. (Event handled by @asbhaibsr)")
        
        if member.id == client.me.id:
            if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
                logger.info(f"DEBUG: Bot {client.me.id} detected as new member in group {message.chat.id}. Calling update_group_info.")
                await update_group_info(message.chat.id, message.chat.title, message.chat.username)
                logger.info(f"Bot joined new group: {message.chat.title} ({message.chat.id}). (Event handled by @asbhaibsr)")

                group_title = message.chat.title if message.chat.title else f"Unknown Group (ID: {message.chat.id})"
                added_by_user = message.from_user.first_name if message.from_user else "Unknown User"
                notification_message = (
                    f"🥳 **New Group Alert!**\n"
                    f"Bot ko ek naye group mein add kiya gaya hai!\n\n"
                    f"**Group Name:** {group_title}\n"
                    f"**Group ID:** `{message.chat.id}`\n"
                    f"**Added By:** {added_by_user} ({message.from_user.id if message.from_user else 'N/A'})\n"
                    f"**Added On:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    f"**Code By:** @asbhaibsr\n**Updates:** @asbhai_bsr\n**Support:** @aschat_group" # Fixed support group username
                )
                try:
                    await client.send_message(chat_id=OWNER_ID, text=notification_message, parse_mode=ParseMode.MARKDOWN)
                    logger.info(f"Owner notified about new group: {group_title}. (Notification by @asbhaibsr)")
                except Exception as e:
                    logger.error(f"Could not notify owner about new group {group_title}: {e}. (Notification error by @asbhaibsr)")
            return

        if not member.is_bot and message.chat.type == ChatType.PRIVATE and member.id == message.from_user.id:
            user_exists = user_tracking_collection.find_one({"_id": member.id})
            if not user_exists:
                user_name = member.first_name if member.first_name else "Naya User"
                user_username = f"@{member.username}" if member.username else "N/A"
                notification_message = (
                    f"✨ **New User Alert! (Private Chat)**\n"
                    f"Ek naye user ne bot ko private mein start kiya hai.\n\n"
                    f"**User Name:** {user_name}\n"
                    f"**User ID:** `{member.id}`\n"
                    f"**Username:** {user_username}\n"
                    f"**Started On:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    f"**Code By:** @asbhaibsr\n**Updates:** @asbhai_bsr\n**Support:** @aschat_group" # Fixed support group username
                )
                try:
                    await client.send_message(chat_id=OWNER_ID, text=notification_message, parse_mode=ParseMode.MARKDOWN)
                    logger.info(f"Owner notified about new private user: {user_name}. (Notification by @asbhaibsr)")
                except Exception as e:
                    logger.error(f"Could not notify owner about new private user {user_name}: {e}. (Notification error by @asbhaibsr)")

    # Call store_message for new members as well, but only if they are not bots and are actual users
    # This also helps in updating user_tracking_collection and potentially earning if it's a group
    if message.from_user and not message.from_user.is_bot:
        # NOTE: store_message will now be called conditionally based on cooldown in handle_message_and_reply
        # For new_chat_members, we want to ensure user info is updated regardless of cooldown.
        # So update_user_info is called directly here.
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name) # Ensure user info is updated

@app.on_message(filters.left_chat_member)
async def left_member_handler(client: Client, message: Message):
    logger.info(f"Left chat member detected in chat {message.chat.id}. Left member ID: {message.left_chat_member.id}. Bot ID: {client.me.id}. (Event handled by @asbhaibsr)")

    if message.left_chat_member and message.left_chat_member.id == client.me.id:
        if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
            group_tracking_collection.delete_one({"_id": message.chat.id})
            messages_collection.delete_many({"chat_id": message.chat.id})
            owner_taught_responses_collection.delete_many({"responses.chat_id": message.chat.id})
            conversational_learning_collection.delete_many({"responses.chat_id": message.chat.id})

            earning_tracking_collection.update_many(
                {},
                {"$pull": {"last_active_group_id": message.chat.id}} # Using $pull to remove group_id from array
            )

            logger.info(f"Bot left group: {message.chat.title} ({message.chat.id}). Data cleared. (Code by @asbhaibsr)")
            group_title = message.chat.title if message.chat.title else f"Unknown Group (ID: {message.chat.id})"
            left_by_user = message.from_user.first_name if message.from_user else "Unknown User"
            notification_message = (
                f"💔 **Group Left Alert!**\n"
                f"Bot ko ek group se remove kiya gaya hai ya woh khud leave kar gaya.\n\n"
                f"**Group Name:** {group_title}\n"
                f"**Group ID:** `{message.chat.id}`\n"
                f"**Action By:** {left_by_user} ({message.from_user.id if message.from_user else 'N/A'})\n"
                f"**Left On:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"**Code By:** @asbhaibsr\n**Updates:** @asbhai_bsr\n**Support:** @aschat_group" # Fixed support group username
            )
            try:
                await client.send_message(chat_id=OWNER_ID, text=notification_message, parse_mode=ParseMode.MARKDOWN)
                logger.info(f"Owner notified about bot leaving group: {group_title}. (Notification by @asbhaibsr)")
            except Exception as e:
                logger.error(f"Could not notify owner about bot leaving group {group_title}: {e}. (Notification error by @asbhaibsr)")
            return

    # Store message for left member (if it's a user leaving, not the bot)
    if message.from_user and not message.from_user.is_bot:
        # NOTE: store_message will now be called conditionally based on cooldown in handle_message_and_reply
        # For left_chat_member, we want to ensure user info is updated regardless of cooldown.
        # So update_user_info is called directly here.
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)


@app.on_message(filters.text | filters.sticker | filters.photo | filters.video | filters.document)
async def handle_message_and_reply(client: Client, message: Message):
    if message.from_user and message.from_user.is_bot:
        logger.debug(f"Skipping message from bot user: {message.from_user.id}.")
        return

    is_group_chat = message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]

    # Bot disabled in group check
    if is_group_chat:
        group_status = group_tracking_collection.find_one({"_id": message.chat.id})
        if group_status and not group_status.get("bot_enabled", True):
            logger.info(f"Bot is disabled in group {message.chat.id}. Skipping message handling.")
            return

    # Update user and group info regardless (important for tracking last active)
    # यह सामान्य ट्रैकिंग के लिए है, बॉट की प्रतिक्रिया/लर्निंग से संबंधित नहीं है
    if is_group_chat:
        logger.info(f"DEBUG: Message from group/supergroup {message.chat.id}. Calling update_group_info.")
        await update_group_info(message.chat.id, message.chat.title, message.chat.username)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)

    # --- Handle message deletion logic first (अगर मैसेज डिलीट करना है तो यहीं रुक जाएं) ---
    # डिलीशन लॉजिक सभी मैसेजों के लिए चलना चाहिए, भले ही बॉट कूलडाउन पर हो, क्योंकि यह एक मॉडरेशन फ़ंक्शन है।
    user_id = message.from_user.id if message.from_user else None
    is_sender_admin = False
    if user_id and is_group_chat:
        is_sender_admin = await is_admin_or_owner(client, message.chat.id, user_id)
    
    # Link deletion
    if is_group_chat and message.text:
        current_group_settings = group_tracking_collection.find_one({"_id": message.chat.id})
        if current_group_settings and current_group_settings.get("linkdel_enabled", False):
            if contains_link(message.text) and not is_sender_admin:
                try:
                    await message.delete()
                    sent_delete_alert = await message.reply_text(f"ओहो, ये क्या भेज दिया {message.from_user.mention}? 🧐 सॉरी-सॉरी, यहाँ **लिंक्स अलाउड नहीं हैं!** 🚫 आपका मैसेज तो गया!💨 अब से ध्यान रखना, हाँ?", quote=True, parse_mode=ParseMode.MARKDOWN)
                    asyncio.create_task(delete_after_delay_for_message(sent_delete_alert, 180))
                    logger.info(f"Deleted link message {message.id} from user {message.from_user.id} in chat {message.chat.id}.")
                    return # मैसेज डिलीट हो गया, आगे प्रोसेस न करें
                except Exception as e:
                    logger.error(f"Error deleting link message {message.id}: {e}")
            elif contains_link(message.text) and is_sender_admin:
                logger.info(f"Admin's link message {message.id} was not deleted in chat {message.chat.id}.")

    # Bio link deletion
    if is_group_chat and user_id:
        try:
            current_group_settings = group_tracking_collection.find_one({"_id": message.chat.id})
            if current_group_settings and current_group_settings.get("biolinkdel_enabled", False):
                user_chat_obj = await client.get_chat(user_id)
                user_bio = user_chat_obj.bio or ""
                is_biolink_exception = biolink_exceptions_collection.find_one({"_id": user_id})
                if not is_sender_admin and not is_biolink_exception:
                    if URL_PATTERN.search(user_bio):
                        try:
                            await message.delete()
                            sent_delete_alert = await message.reply_text(
                                f"अरे बाबा रे {message.from_user.mention}! 😲 आपकी **बायो में लिंक है!** इसीलिए आपका मैसेज गायब हो गया!👻\n"
                                "कृपया अपनी बायो से लिंक हटाएँ। यदि आपको यह अनुमति चाहिए, तो कृपया एडमिन से संपर्क करें और उन्हें `/biolink आपका_यूजरआईडी` कमांड देने को कहें।",
                                quote=True, parse_mode=ParseMode.MARKDOWN
                            )
                            asyncio.create_task(delete_after_delay_for_message(sent_delete_alert, 180))
                            logger.info(f"Deleted message {message.id} from user {user_id} due to link in bio in chat {message.chat.id}.")
                            return # मैसेज डिलीट हो गया, आगे प्रोसेस न करें
                        except Exception as e:
                            logger.error(f"Error deleting message {message.id} due to bio link: {e}")
                elif (is_sender_admin or is_biolink_exception) and URL_PATTERN.search(user_bio):
                    logger.info(f"Admin's or excepted user's bio link was ignored for message {message.id} in chat {message.chat.id}.")
        except Exception as e:
            logger.error(f"Error checking user bio for user {user_id} in chat {message.chat.id}: {e}")

    # Username mention deletion
    if is_group_chat and message.text:
        current_group_settings = group_tracking_collection.find_one({"_id": message.chat.id})
        if current_group_settings and current_group_settings.get("usernamedel_enabled", False):
            if contains_mention(message.text) and not is_sender_admin:
                try:
                    await message.delete()
                    sent_delete_alert = await message.reply_text(f"टच-टच {message.from_user.mention}! 😬 आपने `@` का इस्तेमाल किया! सॉरी, वो मैसेज तो चला गया आसमान में! 🚀 अगली बार से ध्यान रखना, हाँ? 😉", quote=True, parse_mode=ParseMode.MARKDOWN)
                    asyncio.create_task(delete_after_delay_for_message(sent_delete_alert, 180))
                    logger.info(f"Deleted username mention message {message.id} from user {message.from_user.id} in chat {message.chat.id}.")
                    return # मैसेज डिलीट हो गया, आगे प्रोसेस न करें
                except Exception as e:
                    logger.error(f"Error deleting username message {message.id}: {e}")
            elif contains_mention(message.text) and is_sender_admin:
                logger.info(f"Admin's username mention message {message.id} was not deleted in chat {message.chat.id}.")

    # --- मैसेज डिलीशन लॉजिक समाप्त ---

    # चेक करें कि क्या मैसेज कोई कमांड है
    is_command = message.text and message.text.startswith('/')

    # केवल गैर-कमांड मैसेजों के लिए कूलडाउन लॉजिक लागू करें
    if not is_command:
        chat_id_for_cooldown = message.chat.id
        if not await can_reply_to_chat(chat_id_for_cooldown):
            logger.info(f"Chat {chat_id_for_cooldown} is on message reply cooldown. Skipping message {message.id} reply generation, storage, and learning.")
            return # अगर कूलडाउन पर है, तो जवाब न दें, स्टोर न करें और सीखें भी नहीं

        # अगर कूलडाउन पर नहीं है, तो स्टोर करने, सीखने और जवाब देने के लिए आगे बढ़ें
        await store_message(message) # केवल तभी स्टोर करें जब कूलडाउन पर न हो
        logger.info(f"Message {message.id} from user {message.from_user.id if message.from_user else 'N/A'} in chat {message.chat.id} (type: {message.chat.type.name}) has been sent to store_message for general storage and earning tracking.")

        # मालिक द्वारा सिखाई गई बातचीत का लॉजिक
        if message.from_user and message.from_user.id == OWNER_ID and message.reply_to_message:
            replied_to_msg = message.reply_to_message
            if replied_to_msg.from_user and replied_to_msg.from_user.id == OWNER_ID:
                trigger_content = replied_to_msg.text if replied_to_msg.text else (replied_to_msg.sticker.emoji if replied_to_msg.sticker else None)
                
                if trigger_content:
                    response_data = {
                        "message_id": message.id, "user_id": message.from_user.id,
                        "username": message.from_user.username, "first_name": message.from_user.first_name,
                        "chat_id": message.chat.id, "chat_type": message.chat.type.name,
                        "chat_title": message.chat.title if message.chat.type != ChatType.PRIVATE else None,
                        "timestamp": datetime.now(), "credits": "Code by @asbhaibsr"
                    }
                    if message.text: response_data["type"] = "text"; response_data["content"] = message.text
                    elif message.sticker: response_data["type"] = "sticker"; response_data["content"] = message.sticker.emoji if message.sticker.emoji else ""; response_data["sticker_id"] = message.sticker.file_id
                    
                    owner_taught_responses_collection.update_one(
                        {"trigger": trigger_content}, {"$addToSet": {"responses": response_data}}, upsert=True
                    )
                    await message.reply_text("मालिक! 👑 मैंने यह बातचीत सीख ली है और अब इसे याद रखूंगी! 😉", parse_mode=ParseMode.MARKDOWN)
                    logger.info(f"Owner {OWNER_ID} taught a new pattern: '{trigger_content}' -> '{response_data.get('content') or response_data.get('sticker_id')}'")

        # सामान्य बातचीत लर्निंग लॉजिक
        if message.reply_to_message and message.from_user and message.from_user.id != OWNER_ID:
            replied_to_msg = message.reply_to_message
            if replied_to_msg.from_user and (replied_to_msg.from_user.is_self or (not replied_to_msg.from_user.is_bot and replied_to_msg.from_user.id != message.from_user.id)):
                trigger_content = replied_to_msg.text if replied_to_msg.text else (replied_to_msg.sticker.emoji if replied_to_msg.sticker else None)
                
                if trigger_content:
                    response_data = {
                        "message_id": message.id, "user_id": message.from_user.id,
                        "username": message.from_user.username, "first_name": message.from_user.first_name,
                        "chat_id": message.chat.id, "chat_type": message.chat.type.name,
                        "chat_title": message.chat.title if message.chat.type != ChatType.PRIVATE else None,
                        "timestamp": datetime.now(), "credits": "Code by @asbhaibsr"
                    }
                    if message.text: response_data["type"] = "text"; response_data["content"] = message.text
                    elif message.sticker: response_data["type"] = "sticker"; response_data["content"] = message.sticker.emoji if message.sticker.emoji else ""; response_data["sticker_id"] = message.sticker.file_id
                    
                    conversational_learning_collection.update_one(
                        {"trigger": trigger_content}, {"$addToSet": {"responses": response_data}}, upsert=True
                    )
                    logger.info(f"Learned conversational pattern: '{trigger_content}' -> '{response_data.get('content') or response_data.get('sticker_id')}'")

        # बॉट के जवाब उत्पन्न करें
        logger.info(f"Attempting to generate reply for chat {message.chat.id}.")
        reply_doc = await generate_reply(message)

        if reply_doc:
            try:
                if reply_doc.get("type") == "text":
                    await message.reply_text(reply_doc["content"], parse_mode=ParseMode.MARKDOWN)
                    logger.info(f"Replied with text: {reply_doc['content']}.")
                elif reply_doc.get("type") == "sticker" and reply_doc.get("sticker_id"):
                    await message.reply_sticker(reply_doc["sticker_id"])
                    logger.info(f"Replied with sticker: {reply_doc['sticker_id']}.")
                else:
                    logger.warning(f"Reply document found but no content/sticker_id: {reply_doc}.")
            except Exception as e:
                logger.error(f"Error sending reply for message {message.id}: {e}.")
            finally:
                update_message_reply_cooldown(message.chat.id)
        else:
            logger.info("No suitable reply found.")

