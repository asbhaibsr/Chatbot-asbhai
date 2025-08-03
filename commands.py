from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatType, ChatMemberStatus, ParseMode
from pyrogram.errors import FloodWait, UserIsBlocked, ChatWriteForbidden, PeerIdInvalid, RPCError
import asyncio
import os
import sys
from datetime import datetime
import re

# Import utilities and configurations
from config import (
    app, buttons_collection, group_tracking_collection, user_tracking_collection,
    messages_collection, owner_taught_responses_collection, conversational_learning_collection,
    biolink_exceptions_collection, earning_tracking_collection, reset_status_collection, logger,
    OWNER_ID, BOT_PHOTO_URL, UPDATE_CHANNEL_USERNAME, ASBHAI_USERNAME, ASFILTER_BOT_USERNAME, REPO_LINK, URL_PATTERN
)
from utils import (
    is_on_command_cooldown, update_command_cooldown, update_group_info, update_user_info,
    get_top_earning_users, reset_monthly_earnings_manual, send_and_auto_delete_reply,
    store_message, is_admin_or_owner, delete_after_delay_for_message, contains_link, contains_mention
)

# Import callbacks.py for callback handlers
import callbacks

# -----------------
# Cooldown Logic
# -----------------
last_reply_time = {}
REPLY_COOLDOWN_SECONDS = 8
cooldown_locks = {}

# -----------------
# Callback Handlers
# -----------------

@app.on_callback_query()
async def callback_handler(client, callback_query):
    await callback_query.answer()

    if callback_query.data == "buy_git_repo":
        await send_and_auto_delete_reply(
            callback_query.message,
            text=f"🤩 अगर आपको मेरे जैसा खुद का bot banwana hai, to aapko ₹500 dene honge. Iske liye **@{ASBHAI_USERNAME}** se contact karen aur unhe bataiye ki aapko is bot ka code chahiye banwane ke liye. Jaldi karo, deals hot hain! 💸\n\n**Owner:** @asbhaibsr\n**Updates:** @asbhai_bsr\n**Support:** @asbhai_bsr",
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
            "Main ek self-learning bot hoon jo conversations se seekhti hai. Aap groups mein ya mujhse private mein baat kar sakte hain, aur main aapke messages ko yaad rakhti hai. Jab koi user similar baat karta hai, toh main usse seekhe hue reply deti hai.\n\n"
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
            "• `/biolink <userid>`: (Sirf Group Admins ke liye) `biolinkdel` on hone par bhi kisi user ko **bio mein `t.me` aur `http/https` links** rakhne ki permission dene ke liye.\n"
            "• `/usernamedel on/off`: (Sirf Group Admins ke liye) Group mein **'@' mentions** allow ya delete karne ke liye.\n\n"
            "**🔗 Mera Code (GitHub Repository):**\n"
            f"[**REPO_LINK**]({ASBHAI_USERNAME})\n\n"
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
            "Yahan bataya gaya hai ki aap mere saath kaise kamai kar sakte hain:\n\n"
            "**1. Sakriya Rahen (Be Active):**\n"
            "  • Aapko group mein **vastavik aur sarthak baatcheet** karni hogi.\n"
            "  • Betarateeb message, spamming, ya sirf emoji bhejne se aapki ranking nahi badhegi aur aap ayogya bhi ho sakte hain.\n"
            "  • Jitni zyada achhi baatcheet, utni zyada kamai ke avsar!\n\n"
            "**2. Kya Karein, Kya Na Karein (Do's and Don'ts):**\n"
            "  • **Karein:** Sawalon ke jawab dein, charcha mein bhag len, naye vishay shuru karein, anya sadasyon ke saath interact karein.\n"
            "  • **Na Karein:** Bar-bar ek hi message bhejein, sirf sticker ya GIF bhejein, asambaddh samagri post karein, ya group ke niyamon ka ullanghan karein.\n\n"
            "**3. Kamai Ka Samay (Earning Period):**\n"
            "  • Kamai har **mahine** ke pehle din reset hogi. Iska matlab hai ki har mahine aapke paas top par aane ka ek naya mauka hoga!\n\n"
            "**4. Ayogya Hona (Disqualification):**\n"
            "  • Yadi aap spamming karte hue paaye jaate hain, ya kisi bhi tarah se system ka durupyog karne ki koshish karte hain, to aapko leaderboard se hata diya jaega aur aap bhavishya ki kamai ke liye ayogya ghoshit ho sakte hain.\n"
            "  • Group ke niyamon ka palan karna anivarya hai.\n\n"
            "**5. Withdrawal (Withdrawal):**\n"
            "  • Withdrawal har mahine ke **pehle hafte** mein hoga.\n"
            "  • Apni kamai nikalne ke liye, aapko mujhe `@asbhaibsr` par DM (Direct Message) karna hoga.\n\n"
            "**Shubhakamnaein!** 🍀\n"
            "Mujhe aasha hai ki aap sakriya rahenge aur hamari community mein yogdan denge.\n\n"
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

@app.on_callback_query(filters.regex("^(confirm_clearall_dbs|cancel_clearall_dbs)$"))
async def handle_clearall_dbs_callback(client: Client, callback_query):
    query = callback_query
    await query.answer()

    if query.from_user.id != OWNER_ID:
        await query.edit_message_text("Aap is karwai ko adhikrit nahi hain.")
        return

    if query.data == 'confirm_clearall_dbs':
        await query.edit_message_text("Data delete kiya ja raha hai... Kripya pratiksha karen.⏳")
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
            if 'reset_status_collection' in globals():
                reset_status_collection.drop()
                logger.info("reset_status_collection dropped.")
            biolink_exceptions_collection.drop()
            logger.info("biolink_exceptions_collection dropped.")
            owner_taught_responses_collection.drop()
            logger.info("owner_taught_responses_collection dropped.")
            conversational_learning_collection.drop()
            logger.info("conversational_learning_collection dropped.")

            await query.edit_message_text("✅ **Safaltapoorvak:** Aapki sabhi MongoDB database ka sara data delete kar diya gaya hai. Bot ab bilkul naya ho gaya hai! ✨", parse_mode=ParseMode.MARKDOWN)
            logger.info(f"Owner {query.from_user.id} confirmed and successfully cleared all MongoDB data.")
        except Exception as e:
            await query.edit_message_text(f"❌ **Truti:** Data delete karne mein samasya aayi: {e}\n\nKripya logs check karen.", parse_mode=ParseMode.MARKDOWN)
            logger.error(f"Error during /clearall confirmation and deletion: {e}")
    elif query.data == 'cancel_clearall_dbs':
        await query.edit_message_text("Karwai radd kar di gayi hai. Aapka data surakshit hai. ✅", parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Owner {query.from_user.id} cancelled /clearall operation.")

# -----------------
# Member Handlers
# -----------------

@app.on_message(filters.new_chat_members)
async def new_member_handler(client: Client, message: Message):
    logger.info(f"New chat members detected in chat {message.chat.id}. Bot ID: {client.me.id}. (Event handled by @asbhaibsr)")

    me = await client.get_me()

    for member in message.new_chat_members:
        logger.info(f"Processing new member: {member.id} ({member.first_name}) in chat {message.chat.id}. Is bot: {member.is_bot}. (Event handled by @asbhaibsr)")
        
        if member.id == me.id:
            if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
                logger.info(f"DEBUG: Bot {me.id} detected as new member in group {message.chat.id}. Calling update_group_info.")
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
                    f"**Code By:** @asbhaibsr\n**Updates:** @asbhai_bsr\n**Support:** @aschat_group"
                )
                try:
                    await client.send_message(chat_id=OWNER_ID, text=notification_message, parse_mode=ParseMode.MARKDOWN)
                    logger.info(f"Owner notified about new group: {group_title}. (Notification by @asbhaibsr)")
                except Exception as e:
                    logger.error(f"Could not notify owner about new group {group_title}: {e}. (Notification error by @asbhaibsr)")
        else:
            return

    if message.from_user and not message.from_user.is_bot:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)


@app.on_message(filters.left_chat_member)
async def left_member_handler(client: Client, message: Message):
    logger.info(f"Left chat member detected in chat {message.chat.id}. Left member ID: {message.left_chat_member.id}. Bot ID: {client.me.id}. (Event handled by @asbhaibsr)")

    me = await client.get_me()

    if message.left_chat_member and message.left_chat_member.id == me.id:
        if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
            group_tracking_collection.delete_one({"_id": message.chat.id})
            messages_collection.delete_many({"chat_id": message.chat.id})
            owner_taught_responses_collection.delete_many({"responses.chat_id": message.chat.id})
            conversational_learning_collection.delete_many({"responses.chat_id": message.chat.id})

            earning_tracking_collection.update_many(
                {},
                {"$pull": {"last_active_group_id": message.chat.id}}
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
                f"**Code By:** @asbhaibsr\n**Updates:** @asbhai_bsr\n**Support:** @aschat_group"
            )
            try:
                await client.send_message(chat_id=OWNER_ID, text=notification_message, parse_mode=ParseMode.MARKDOWN)
                logger.info(f"Owner notified about bot leaving group: {group_title}. (Notification by @asbhaibsr)")
            except Exception as e:
                logger.error(f"Could not notify owner about bot leaving group {group_title}: {e}. (Notification error by @asbhaibsr)")
            return

    if message.from_user and not message.from_user.is_bot:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)


# -----------------
# Main Message Handler
# -----------------

@app.on_message(filters.text | filters.sticker | filters.photo | filters.video | filters.document)
async def handle_message_and_reply(client: Client, message: Message):
    if message.from_user and message.from_user.is_bot:
        logger.debug(f"Skipping message from bot user: {message.from_user.id}.")
        return

    is_group_chat = message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]
    
    if is_group_chat:
        me = await client.get_me()
        try:
            member = await client.get_chat_member(message.chat.id, me.id)
            if member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                logger.info(f"Bot is not an admin in group {message.chat.id}. Skipping all actions for this group.")
                return
        except Exception as e:
            if "CHAT_ADMIN_REQUIRED" in str(e):
                logger.warning(f"Bot has no permission to check its own admin status in group {message.chat.id}. Skipping all actions.")
                return
            logger.error(f"Error checking bot's admin status in group {message.chat.id}: {e}")
            return

    if is_group_chat:
        group_status = group_tracking_collection.find_one({"_id": message.chat.id})
        if group_status and not group_status.get("bot_enabled", True):
            logger.info(f"Bot is disabled in group {message.chat.id}. Skipping message handling.")
            return

    if is_group_chat:
        logger.info(f"DEBUG: Message from group/supergroup {message.chat.id}. Calling update_group_info.")
        await update_group_info(message.chat.id, message.chat.title, message.chat.username)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)

    user_id = message.from_user.id if message.from_user else None
    is_sender_admin = False
    if user_id and is_group_chat:
        is_sender_admin = await is_admin_or_owner(client, message.chat.id, user_id)
    
    if is_group_chat and message.text:
        current_group_settings = group_tracking_collection.find_one({"_id": message.chat.id})
        if current_group_settings and current_group_settings.get("linkdel_enabled", False):
            if contains_link(message.text) and not is_sender_admin:
                try:
                    await message.delete()
                    sent_delete_alert = await message.reply_text(f"Oho, ye kya bhej diya {message.from_user.mention}? 🧐 Sorry-sorry, yahan **links allowed nahi hain!** 🚫 Aapka message to gaya!💨 Ab se dhyan rakhna, han?", quote=True, parse_mode=ParseMode.MARKDOWN)
                    asyncio.create_task(delete_after_delay_for_message(sent_delete_alert, 180))
                    logger.info(f"Deleted link message {message.id} from user {message.from_user.id} in chat {message.chat.id}.")
                    return
                except Exception as e:
                    logger.error(f"Error deleting link message {message.id}: {e}")
            elif contains_link(message.text) and is_sender_admin:
                logger.info(f"Admin's link message {message.id} was not deleted in chat {message.chat.id}.")

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
                                f"Are baba re {message.from_user.mention}! 😲 Aapki **bio mein link hai!** Isi liye aapka message gayab ho gaya!👻\n"
                                "Kripya apni bio se link hatayen. Yadi aapko yeh anumati chahiye, to kripya admin se sampark karen aur unhein `/biolink aapka_userid` command dene ko kahen.",
                                quote=True, parse_mode=ParseMode.MARKDOWN
                            )
                            asyncio.create_task(delete_after_delay_for_message(sent_delete_alert, 180))
                            logger.info(f"Deleted message {message.id} from user {user_id} due to link in bio in chat {message.chat.id}.")
                            return
                        except Exception as e:
                            logger.error(f"Error deleting message {message.id} due to bio link: {e}")
                elif (is_sender_admin or is_biolink_exception) and URL_PATTERN.search(user_bio):
                    logger.info(f"Admin's or excepted user's bio link was ignored for message {message.id} in chat {message.chat.id}.")
        except Exception as e:
            logger.error(f"Error checking user bio for user {user_id} in chat {message.chat.id}: {e}")

    if is_group_chat and message.text:
        current_group_settings = group_tracking_collection.find_one({"_id": message.chat.id})
        if current_group_settings and current_group_settings.get("usernamedel_enabled", False):
            if contains_mention(message.text) and not is_sender_admin:
                try:
                    await message.delete()
                    sent_delete_alert = await message.reply_text(f"Tuch-tuch {message.from_user.mention}! 😬 Aapne `@` ka istemal kiya! Sorry, woh message to chala gaya aasman mein! 🚀 Agli bar se dhyan rakhna, han? 😉", quote=True, parse_mode=ParseMode.MARKDOWN)
                    asyncio.create_task(delete_after_delay_for_message(sent_delete_alert, 180))
                    logger.info(f"Deleted username mention message {message.id} from user {message.from_user.id} in chat {message.chat.id}.")
                    return
                except Exception as e:
                    logger.error(f"Error deleting username message {message.id}: {e}")
            elif contains_mention(message.text) and is_sender_admin:
                logger.info(f"Admin's username mention message {message.id} was not deleted in chat {message.chat.id}.")

    is_command = message.text and message.text.startswith('/')

    if not is_command:
        chat_id = message.chat.id
        
        if chat_id not in cooldown_locks:
            cooldown_locks[chat_id] = asyncio.Lock()
            
        async with cooldown_locks[chat_id]:
            current_time = datetime.now()
            
            if chat_id in last_reply_time:
                time_since_last_reply = (current_time - last_reply_time[chat_id]).total_seconds()
                if time_since_last_reply < REPLY_COOLDOWN_SECONDS:
                    logger.info(f"Chat {chat_id} is in cooldown. Skipping reply for message {message.id}.")
                    return
            
            await store_message(client, message)

            logger.info(f"Message {message.id} from user {message.from_user.id if message.from_user else 'N/A'} in chat {message.chat.id} (type: {message.chat.type.name}) has been sent to store_message for general storage and earning tracking.")

            if message.from_user and message.from_user.id == OWNER_ID and message.reply_to_message:
                replied_to_msg = message.reply_to_message
                if replied_to_msg.from_user and replied_to_msg.from_user.is_self:
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
                        await message.reply_text("Maalik! 👑 Maine yeh baatcheet seekh li hai aur ab ise yaad rakhungi! 😉", parse_mode=ParseMode.MARKDOWN)
                        logger.info(f"Owner {OWNER_ID} taught a new pattern: '{trigger_content}' -> '{response_data.get('content') or response_data.get('sticker_id')}'")

            if message.reply_to_message and message.from_user and message.from_user.id != OWNER_ID:
                replied_to_msg = message.reply_to_message
                if replied_to_msg.from_user and (replied_to_msg.from_user.is_self or (not replied_to_msg.from_user.is_bot and replied_to_msg.from_user.id != message.from_user.id)):
                    trigger_content = replied_to_msg.text if replied_to_msg.text else (replied_to_msg.sticker.emoji if replied_to_msg.sticker else "")
                    
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
                    
                    last_reply_time[chat_id] = datetime.now()
                    logger.info(f"Reply sent to chat {chat_id}. Cooldown started for {REPLY_COOLDOWN_SECONDS} seconds.")
                    
                except Exception as e:
                    if "CHAT_WRITE_FORBIDDEN" in str(e):
                        logger.error(f"Permission error: Bot cannot send messages in chat {message.chat.id}. Leaving group.")
                        try:
                            await client.leave_chat(message.chat.id)
                            await client.send_message(OWNER_ID, f"**ALERT:** Bot was removed from group `{message.chat.id}` because it lost permission to send messages.")
                        except Exception as leave_e:
                            logger.error(f"Failed to leave chat {message.chat.id} after permission error: {leave_e}")
                    else:
                        logger.error(f"Error sending reply for message {message.id}: {e}.")
            else:
                logger.info("No suitable reply found.")

# -----------------
# Command Handlers
# -----------------

@app.on_message(filters.command("start") & filters.private)
async def start_private_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    user_name = message.from_user.first_name if message.from_user else "Dost"
    welcome_message = (
        f"🌟 Hey **{user_name}** Janu! Aapka swagat hai! 🌟\n\n"
        "Main aapki madad karne ke liye taiyar hoon!\n"
        "Apni sabhi commands dekhne ke liye niche diye gaye 'Sahayata' button par click karen."
    )
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("➕ Mujhe Group mein Jodein", url=f"https://t.me/{client.me.username}?startgroup=true")],
            [
                InlineKeyboardButton("📣 Updates Channel", url=f"https://t.me/{UPDATE_CHANNEL_USERNAME}"),
                InlineKeyboardButton("❓ Support Group", url="https://t.me/aschat_group")
            ],
            [
                InlineKeyboardButton("ℹ️ Sahayata ❓", callback_data="show_help_menu"),
                InlineKeyboardButton("💰 Earning Leaderboard", callback_data="show_earning_leaderboard")
            ]
        ]
    )
    await send_and_auto_delete_reply(
        message,
        text=welcome_message,
        photo=BOT_PHOTO_URL,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )
    await store_message(message) 
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)
    logger.info(f"Private start command processed for user {message.from_user.id}. (Code by @asbhaibsr)")

@app.on_message(filters.command("start") & filters.group)
async def start_group_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    user_name = message.from_user.first_name if message.from_user else "Dost"
    welcome_message = (
        f"🌟 Hey **{user_name}** Janu! Aapka swagat hai! 🌟\n\n"
        "Main group ki sabhi baatein sunne aur seekhne ke liye taiyar hoon!\n"
        "Apni sabhi commands dekhne ke liye niche diye gaye 'Sahayata' button par click karen."
    )
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("➕ Mujhe Group mein Jodein", url=f"https://t.me/{client.me.username}?startgroup=true")],
            [
                InlineKeyboardButton("📣 Updates Channel", url=f"https://t.me/{UPDATE_CHANNEL_USERNAME}"),
                InlineKeyboardButton("❓ Support Group", url="https://t.me/aschat_group")
            ],
            [
                InlineKeyboardButton("ℹ️ Sahayata ❓", callback_data="show_help_menu"),
                InlineKeyboardButton("💰 Earning Leaderboard", callback_data="show_earning_leaderboard")
            ]
        ]
    )
    await send_and_auto_delete_reply(
        message,
        text=welcome_message,
        photo=BOT_PHOTO_URL,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )
    await store_message(message)
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        logger.info(f"Attempting to update group info from /start command in chat {message.chat.id}.")
        await update_group_info(message.chat.id, message.chat.title, message.chat.username)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)
    logger.info(f"Group start command processed in chat {message.chat.id}. (Code by @asbhaibsr)")

@app.on_message(filters.command("topusers") & (filters.private | filters.group))
async def top_users_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    top_users = await get_top_earning_users()
    if not top_users:
        await send_and_auto_delete_reply(message, text="😢 Ab tak koi bhi upayogkarta leaderboard par nahi hai! Sakriya hokar pehle banen! ✨\n\n**Powered By:** @asbhaibsr", parse_mode=ParseMode.MARKDOWN)
        return

    earning_messages = ["👑 **Top Active Users - ✨ VIP Leaderboard! ✨** 👑\n\n"]
    prizes = {
        1: "💰 ₹50", 2: "💸 ₹30", 3: "🎁 ₹20",
        4: f"🎬 @{ASFILTER_BOT_USERNAME} ka 1 hafte ka premium plan",
        5: f"🎬 @{ASFILTER_BOT_USERNAME} ka 3 din ka premium plan"
    }

    for i, user in enumerate(top_users[:5]):
        rank = i + 1
        user_name = user.get('first_name', 'Unknown User')
        username_str = f"@{user.get('username')}" if user.get('username') else f"ID: `{user.get('user_id')}`"
        message_count = user.get('message_count', 0)
        prize_str = prizes.get(rank, "🏅 Koi puraskar nahi")

        group_info = ""
        last_group_id = user.get('last_active_group_id')
        last_group_title = user.get('last_active_group_title', 'Unknown Group')

        if last_group_id:
            try:
                chat_obj = await client.get_chat(last_group_id)
                if chat_obj.type == ChatType.PRIVATE:
                    group_info = f"   • Sakriya tha: **[Niji chat mein](tg://user?id={user.get('user_id')})**\n"
                elif chat_obj.username:
                    group_info = f"   • Sakriya tha: **[{chat_obj.title}](https://t.me/{chat_obj.username})**\n"
                else:
                    try:
                        invite_link = await client.export_chat_invite_link(last_group_id)
                        group_info = f"   • Sakriya tha: **[{chat_obj.title}]({invite_link})**\n"
                    except Exception:
                        group_info = f"   • Sakriya tha: **{chat_obj.title}** (Niji group)\n"
            except Exception as e:
                logger.warning(f"Could not fetch chat info for group ID {last_group_id} for leaderboard: {e}")
                group_info = f"   • Sakriya tha: **{last_group_title}** (Jankari uplabdh nahi)\n"
        else:
            group_info = "   • Sakriya tha: **Koi group gatividhi nahi**\n"

        earning_messages.append(
            f"**{rank}.** 🌟 **{user_name}** ({username_str}) 🌟\n"
            f"   • Kul message: **{message_count} 💬**\n"
            f"   • Sambhavit puraskar: **{prize_str}**\n"
            f"{group_info}"
        )
    
    earning_messages.append(
        "\n_Har mahine ki pehli tarikh ko yeh system reset hota hai!_\n"
        "_Group ke niyamon ko janne ke liye `/help` ka upayog karen._"
    )
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("💰 Paise Nikalwain (Withdraw)", url=f"https://t.me/{ASBHAI_USERNAME}"),
                InlineKeyboardButton("💰 Earning Rules", callback_data="show_earning_rules")
            ]
        ]
    )
    await send_and_auto_delete_reply(message, text="\n".join(earning_messages), reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
    await store_message(message)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)
    logger.info(f"Top users command processed for user {message.from_user.id} in chat {message.chat.id}. (Code by @asbhaibsr)")

@app.on_message(filters.command("broadcast") & filters.private)
async def broadcast_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    if message.from_user.id != OWNER_ID:
        await send_and_auto_delete_reply(message, text="Oops! Sorry sweetie, yeh command sirf mere boss ke liye hai. 🤷‍♀️ (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return

    broadcast_text = None
    broadcast_photo = None
    broadcast_sticker = None
    broadcast_video = None
    broadcast_document = None

    if message.reply_to_message:
        replied_msg = message.reply_to_message
        if replied_msg.text: broadcast_text = replied_msg.text
        elif replied_msg.photo: broadcast_photo = replied_msg.photo.file_id; broadcast_text = replied_msg.caption
        elif replied_msg.sticker: broadcast_sticker = replied_msg.sticker.file_id
        elif replied_msg.video: broadcast_video = replied_msg.video.file_id; broadcast_text = replied_msg.caption
        elif replied_msg.document: broadcast_document = replied_msg.document.file_id; broadcast_text = replied_msg.caption
    elif len(message.command) > 1:
        broadcast_text = message.text.split(None, 1)[1]

    if not any([broadcast_text, broadcast_photo, broadcast_sticker, broadcast_video, broadcast_document]):
        await send_and_auto_delete_reply(message, text="Broadcast karne ke liye koi content nahi mila. Please text, sticker, photo, video, ya document bhejo ya reply karo. 🤔", parse_mode=ParseMode.MARKDOWN)
        return

    group_chat_ids = [g["_id"] for g in group_tracking_collection.find({})]
    private_chat_ids = [u["_id"] for u in user_tracking_collection.find({})]
    all_target_ids = list(set(group_chat_ids + private_chat_ids))
    if OWNER_ID in all_target_ids: all_target_ids.remove(OWNER_ID)

    total_targets = len(all_target_ids)
    sent_count = 0
    failed_count = 0
    
    status_message = await message.reply_text(f"🚀 **Broadcast Shuru!** 🚀\n" f"Cool, main **{total_targets}** chats par message bhej rahi hoon.\n" f"Sent: **0** / Failed: **0** (Total: {total_targets})", parse_mode=ParseMode.MARKDOWN)

    logger.info(f"Starting broadcast to {total_targets} chats (groups and users). (Broadcast by @asbhaibsr)")

    for i, chat_id in enumerate(all_target_ids):
        try:
            if broadcast_photo: await client.send_photo(chat_id, broadcast_photo, caption=broadcast_text, parse_mode=ParseMode.MARKDOWN)
            elif broadcast_sticker: await client.send_sticker(chat_id, broadcast_sticker)
            elif broadcast_video: await client.send_video(chat_id, broadcast_video, caption=broadcast_text, parse_mode=ParseMode.MARKDOWN)
            elif broadcast_document: await client.send_document(chat_id, broadcast_document, caption=broadcast_text, parse_mode=ParseMode.MARKDOWN)
            elif broadcast_text: await client.send_message(chat_id, broadcast_text, parse_mode=ParseMode.MARKDOWN)
            
            sent_count += 1
            if (i + 1) % 10 == 0 or (i + 1) == total_targets:
                try:
                    await status_message.edit_text(f"🚀 **Broadcast Progress...** 🚀\n" f"Cool, main **{total_targets}** chats par message bhej rahi hoon.\n" f"Sent: **{sent_count}** / Failed: **{failed_count}** (Total: {total_targets})", parse_mode=ParseMode.MARKDOWN)
                except Exception as edit_e:
                    logger.warning(f"Failed to edit broadcast status message: {edit_e}")
            
            # This is the corrected delay to prevent hitting Telegram's flood limits.
            await asyncio.sleep(2)
            
        except UserIsBlocked:
            failed_count += 1
            user_tracking_collection.delete_one({"_id": chat_id})
            logger.warning(f"User {chat_id} blocked the bot. Removing from user_tracking_collection.")
        except ChatWriteForbidden:
            failed_count += 1
            group_tracking_collection.delete_one({"_id": chat_id})
            logger.warning(f"Bot cannot write in group {chat_id}. Removing from group_tracking_collection.")
        except PeerIdInvalid:
            failed_count += 1
            user_tracking_collection.delete_one({"_id": chat_id})
            group_tracking_collection.delete_one({"_id": chat_id})
            logger.warning(f"Invalid chat ID {chat_id}. Removing from all collections.")
        except FloodWait as fw:
            failed_count += 1
            logger.warning(f"FloodWait of {fw.value} seconds encountered. Sleeping... (Broadcast by @asbhaibsr)")
            await asyncio.sleep(fw.value)
        except RPCError as rpc_e:
            failed_count += 1
            logger.error(f"RPC Error sending broadcast to chat {chat_id}: {rpc_e}. (Broadcast by @asbhaibsr)")
        except Exception as e:
            failed_count += 1
            logger.error(f"Failed to send broadcast to chat {chat_id}: {e}. (Broadcast by @asbhaibsr)")
        
    final_message = (f"🎉 **Broadcast Complete!** 🎉\n" f"Total chats targeted: **{total_targets}**\n" f"Successfully sent: **{sent_count}** messages ✨\n" f"Failed to send: **{failed_count}** messages 💔\n\n" f"Koi nahi, next time! 😉 (System by @asbhaibsr)")
    
    try:
        await status_message.edit_text(final_message, parse_mode=ParseMode.MARKDOWN)
    except Exception as final_edit_e:
        logger.error(f"Failed to send final broadcast summary: {final_edit_e}. Sending as new message instead.")
        await send_and_auto_delete_reply(message, text=final_message, parse_mode=ParseMode.MARKDOWN)

    await store_message(message)
    logger.info(f"Broadcast command processed by owner {message.from_user.id}. (Code by @asbhaibsr)")

@app.on_message(filters.command("stats") & filters.private)
async def stats_private_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    if len(message.command) < 2 or message.command[1].lower() != "check":
        await send_and_auto_delete_reply(message, text="Umm, stats check karne ke liye theek se likho na! `/stats check` aise. 😊 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return

    total_messages = messages_collection.count_documents({})
    unique_group_ids = group_tracking_collection.count_documents({})
    num_users = user_tracking_collection.count_documents({})
    total_owner_taught = owner_taught_responses_collection.count_documents({})
    total_conversational_learned = conversational_learning_collection.count_documents({})

    stats_text = (
        "📊 **Bot Statistics** 📊\n"
        f"• Jitne groups mein main hoon: **{unique_group_ids}** lovely groups!\n"
        f"• Total users jo maine observe kiye: **{num_users}** pyaare users!\n"
        f"• Total messages jo maine store kiye (Old Learning): **{total_messages}** baaton ka khazana! 🤩\n"
        f"• Owner-taught patterns: **{total_owner_taught}** unique patterns!\n"
        f"• Conversational patterns learned: **{total_conversational_learned}** unique patterns!\n\n"
        f"**Powered By:** @asbhaibsr\n**Updates:** @asbhai_bsr\n**Support:** @aschat_group"
    )
    await send_and_auto_delete_reply(message, text=stats_text, parse_mode=ParseMode.MARKDOWN)
    await store_message(message)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)
    logger.info(f"Private stats command processed for user {message.from_user.id}. (Code by @asbhaibsr)")

@app.on_message(filters.command("stats") & filters.group)
async def stats_group_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    if len(message.command) < 2 or message.command[1].lower() != "check":
        await send_and_auto_delete_reply(message, text="Umm, stats check karne ke liye theek se likho na! `/stats check` aise. 😊 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return

    total_messages = messages_collection.count_documents({})
    unique_group_ids = group_tracking_collection.count_documents({})
    num_users = user_tracking_collection.count_documents({})
    total_owner_taught = owner_taught_responses_collection.count_documents({})
    total_conversational_learned = conversational_learning_collection.count_documents({})

    stats_text = (
        "📊 **Bot Statistics** 📊\n"
        f"• Jitne groups mein main hoon: **{unique_group_ids}** lovely groups!\n"
        f"• Total users jo maine observe kiye: **{num_users}** pyaare users!\n"
        f"• Total messages jo maine store kiye (Old Learning): **{total_messages}** baaton ka khazana! 🤩\n"
        f"• Owner-taught patterns: **{total_owner_taught}** unique patterns!\n"
        f"• Conversational patterns learned: **{total_conversational_learned}** unique patterns!\n\n"
        f"**Powered By:** @asbhaibsr\n**Updates:** @asbhai_bsr\n**Support:** @aschat_group"
    )
    await send_and_auto_delete_reply(message, text=stats_text, parse_mode=ParseMode.MARKDOWN)
    await store_message(message)
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await update_group_info(message.chat.id, message.chat.title, message.chat.username)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)

@app.on_message(filters.command("groups") & filters.private)
async def list_groups_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    if message.from_user.id != OWNER_ID:
        await send_and_auto_delete_reply(message, text="Oops! Sorry sweetie, yeh command sirf mere boss ke liye hai. Tumhe permission nahi hai. 🤷‍♀️ (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return

    groups = list(group_tracking_collection.find({}))
    if not groups:
        await send_and_auto_delete_reply(message, text="Main abhi kisi group mein nahi hoon. Akeli hoon, koi add kar lo na! 🥺 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return

    group_list_text = "📚 **Groups Jahan Main Hoon** 📚\n\n"
    for i, group in enumerate(groups):
        title = group.get("title", "Unknown Group")
        group_id = group.get("_id")
        added_on = group.get("added_on", "N/A").strftime("%Y-%m-%d %H:%M") if isinstance(group.get("added_on"), datetime) else "N/A"

        member_count = "N/A"
        group_link_display = ""
        try:
            chat_obj = await client.get_chat(group_id)
            member_count = await client.get_chat_members_count(group_id)
            if chat_obj.username:
                group_link_display = f" ([@{chat_obj.username}](https://t.me/{chat_obj.username}))"
            else:
                try:
                    invite_link = await client.export_chat_invite_link(group_id)
                    group_link_display = f" ([Invite Link]({invite_link}))"
                except Exception:
                    group_link_display = " (Private Group)"
        except Exception as e:
            logger.warning(f"Could not fetch chat info for group ID {group_id}: {e}")
            group_link_display = " (Info N/A)"

        group_list_text += (
            f"{i+1}. **{title}** (`{group_id}`){group_link_display}\n"
            f"   • Joined: {added_on}\n"
            f"   • Members: {member_count}\n"
        )

    group_list_text += "\n_Yeh data tracking database se hai, bilkul secret!_ 🤫\n**Code & System By:** @asbhaibsr"
    await send_and_auto_delete_reply(message, text=group_list_text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
    await store_message(message)
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)
    logger.info(f"Groups list command processed by owner {message.from_user.id}. (Code by @asbhaibsr)")

@app.on_message(filters.command("leavegroup") & filters.private)
async def leave_group_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    if message.from_user.id != OWNER_ID:
        await send_and_auto_delete_reply(message, text="Oops! Sorry sweetie, yeh command sirf mere boss ke liye hai. Tumhe permission nahi hai. 🤷‍♀️ (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return

    if len(message.command) < 2:
        await send_and_auto_delete_reply(message, text="Kripya group ID dein jisse aap mujhe hatana chahte hain. Upyog: `/leavegroup -1001234567890` (aise, darling!) (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return

    try:
        group_id_str = message.command[1]
        if not group_id_str.startswith('-100'):
            await send_and_auto_delete_reply(message, text="Aapne galat Group ID format diya hai. Group ID `-100...` se shuru hoti hai. Thoda dhyan se! 😊 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
            return

        group_id = int(group_id_str)
        await client.leave_chat(group_id)

        group_tracking_collection.delete_one({"_id": group_id})
        messages_collection.delete_many({"chat_id": group_id})
        owner_taught_responses_collection.delete_many({"responses.chat_id": group_id})
        conversational_learning_collection.delete_many({"responses.chat_id": group_id})
        
        logger.info(f"Considered cleaning earning data for users from left group {group_id}. (Code by @asbhaibsr)")

        await send_and_auto_delete_reply(message, text=f"Safaltapoorvak group `{group_id}` se bahar aa gayi, aur uska sara data bhi clean kar diya! Bye-bye! 👋 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Left group {group_id} and cleared its data. (Code by @asbhaibsr)")

    except ValueError:
        await send_and_auto_delete_reply(message, text="Invalid group ID format. Kripya ek valid numeric ID dein. Thoda number check kar lo! 😉 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await send_and_auto_delete_reply(message, text=f"Group se bahar nikalte samay galti ho gayi: {e}. Oh no! 😢 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        logger.error(f"Error leaving group {group_id_str}: {e}. (Code by @asbhaibsr)")

    await store_message(message)
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)

@app.on_message(filters.command("cleardata") & filters.private)
async def clear_data_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    if message.from_user.id != OWNER_ID:
        await send_and_auto_delete_reply(message, text="Sorry, darling! Yeh command sirf mere boss ke liye hai. 🤫 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return

    if len(message.command) < 2:
        await send_and_auto_delete_reply(message, text="Kitna data clean karna hai? Percentage batao na, jaise: `/cleardata 10%` ya `/cleardata 100%`! 🧹 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return

    percentage_str = message.command[1].strip('%')
    try:
        percentage = int(percentage_str)
        if not (1 <= percentage <= 100):
            await send_and_auto_delete_reply(message, text="Percentage 1 se 100 ke beech mein hona chahiye. Thoda dhyan se! 🤔 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
            return
    except ValueError:
        await send_and_auto_delete_reply(message, text="Invalid percentage format. Percentage number mein hona chahiye, jaise `10` ya `50`. Fir se try karo!💖 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return

    total_messages_old = messages_collection.count_documents({})
    total_owner_taught = owner_taught_responses_collection.count_documents({})
    total_conversational = conversational_learning_collection.count_documents({})

    deleted_count_old = 0
    deleted_count_owner_taught = 0
    deleted_count_conversational = 0

    if total_messages_old > 0:
        messages_to_delete_old = int(total_messages_old * (percentage / 100))
        oldest_message_ids = []
        for msg in messages_collection.find({}).sort("timestamp", 1).limit(messages_to_delete_old):
            oldest_message_ids.append(msg['_id'])
        if oldest_message_ids:
            deleted_count_old = messages_collection.delete_many({"_id": {"$in": oldest_message_ids}}).deleted_count

    if total_owner_taught > 0:
        docs_to_delete_owner = int(total_owner_taught * (percentage / 100))
        oldest_owner_taught_ids = []
        for doc in owner_taught_responses_collection.find({}).sort("responses.timestamp", 1).limit(docs_to_delete_owner):
            oldest_owner_taught_ids.append(doc['_id'])
        if oldest_owner_taught_ids:
            deleted_count_owner_taught = owner_taught_responses_collection.delete_many({"_id": {"$in": oldest_owner_taught_ids}}).deleted_count

    if total_conversational > 0:
        docs_to_delete_conv = int(total_conversational * (percentage / 100))
        oldest_conv_ids = []
        for doc in conversational_learning_collection.find({}).sort("responses.timestamp", 1).limit(docs_to_delete_conv):
            oldest_conv_ids.append(doc['_id'])
        if oldest_conv_ids:
            deleted_count_conversational = conversational_learning_collection.delete_many({"_id": {"$in": oldest_conv_ids}}).deleted_count
            
    total_deleted = deleted_count_old + deleted_count_owner_taught + deleted_count_conversational

    if total_deleted > 0:
        await send_and_auto_delete_reply(message, text=f"Wow! 🤩 Maine aapka **{percentage}%** data successfully delete kar diya! Total **{total_deleted}** entries (Old: {deleted_count_old}, Owner-Taught: {deleted_count_owner_taught}, Conversational: {deleted_count_conversational}) clean ho gayi. Ab main thodi light feel kar rahi hoon. ✨ (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Cleared {total_deleted} messages across collections based on {percentage}% request. (Code by @asbhaibsr)")
    else:
        await send_and_auto_delete_reply(message, text="Umm, kuch delete karne ke liye mila hi nahi. Lagta hai tumne pehle hi sab clean kar diya hai! 🤷‍♀️ (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)

    await store_message(message)
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)

@app.on_message(filters.command("deletemessage") & filters.private)
async def delete_specific_message_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    if message.from_user.id != OWNER_ID:
        await send_and_auto_delete_reply(message, text="Oops! Sorry sweetie, yeh command sirf mere boss ke liye hai. 🤷‍♀️ (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return

    if len(message.command) < 2:
        await send_and_auto_delete_reply(message, text="Kaun sa **text message** delete karna hai, batao toh sahi! Jaise: `/deletemessage hello` ya `/deletemessage 'kya haal hai'` 👻 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return

    search_query = " ".join(message.command[1:])
    deleted_count = 0

    if search_query:
        delete_result_old = messages_collection.delete_many({"type": "text", "content": {"$regex": f".*{re.escape(search_query)}.*", "$options": "i"}})
        deleted_count += delete_result_old.deleted_count
        
        delete_result_owner_taught_trigger = owner_taught_responses_collection.delete_many({"trigger": {"$regex": f"^{re.escape(search_query)}$", "$options": "i"}})
        deleted_count += delete_result_owner_taught_trigger.deleted_count
        
        owner_taught_pull_result = owner_taught_responses_collection.update_many(
            {"responses.content": {"$regex": f".*{re.escape(search_query)}.*", "$options": "i"}},
            {"$pull": {"responses": {"content": {"$regex": f".*{re.escape(search_query)}.*", "$options": "i"}}}}
        )
        deleted_count += owner_taught_pull_result.modified_count

        delete_result_conv_trigger = conversational_learning_collection.delete_many({"trigger": {"$regex": f"^{re.escape(search_query)}$", "$options": "i"}})
        deleted_count += delete_result_conv_trigger.deleted_count

        conv_pull_result = conversational_learning_collection.update_many(
            {"responses.content": {"$regex": f".*{re.escape(search_query)}.*", "$options": "i"}},
            {"$pull": {"responses": {"content": {"$regex": f".*{re.escape(search_query)}.*", "$options": "i"}}}}
        )
        deleted_count += conv_pull_result.modified_count

    if deleted_count > 0:
        await send_and_auto_delete_reply(message, text=f"Jaisa hukum mere aaka! 🧞‍♀️ Maine '{search_query}' se milte-julte **{deleted_count}** **text messages** ko dhoondh ke delete kar diya. Ab woh history ka hissa nahi raha! ✨ (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Deleted {deleted_count} text messages with query: '{search_query}'. (Code by @asbhaibsr)")
    else:
        await send_and_auto_delete_reply(message, text="Umm, mujhe tumhare is query se koi **text message** mila hi nahi apne database mein. Spelling check kar lo? 🤔 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)

    await store_message(message)
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)

@app.on_message(filters.command("delsticker") & filters.private)
async def delete_specific_sticker_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    if message.from_user.id != OWNER_ID:
        await send_and_auto_delete_reply(message, text="Oops! Sorry sweetie, yeh command sirf mere boss ke liye hai. 🤷‍♀️ (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return

    if len(message.command) < 2:
        await send_and_auto_delete_reply(message, text="Kitne **stickers** delete karne hai? Percentage batao na, jaise: `/delsticker 10%` ya `delsticker 20%` ya `delsticker 40%`! 🧹 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return

    percentage_str = message.command[1].strip('%')
    try:
        percentage = int(percentage_str)
        if not (1 <= percentage <= 100):
            await send_and_auto_delete_reply(message, text="Percentage 1 se 100 ke beech mein hona chahiye. Thoda dhyan se! 🤔 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
            return
    except ValueError:
        await send_and_auto_delete_reply(message, text="Invalid percentage format. Percentage number mein hona chahiye, jaise `10` ya `50`. Fir se try karo!💖 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return

    deleted_count = 0
    
    total_stickers_old = messages_collection.count_documents({"type": "sticker"})
    if total_stickers_old > 0:
        stickers_to_delete_old = int(total_stickers_old * (percentage / 100))
        sticker_ids_to_delete = []
        for s in messages_collection.find({"type": "sticker"}).sort("timestamp", 1).limit(stickers_to_delete_old):
            sticker_ids_to_delete.append(s['_id'])
        if sticker_ids_to_delete:
            deleted_count += messages_collection.delete_many({"_id": {"$in": sticker_ids_to_delete}}).deleted_count

    owner_taught_pull_result = owner_taught_responses_collection.update_many(
        {"responses.type": "sticker"},
        {"$pull": {"responses": {"type": "sticker"}}}
    )
    deleted_count += owner_taught_pull_result.modified_count 

    conversational_pull_result = conversational_learning_collection.update_many(
        {"responses.type": "sticker"},
        {"$pull": {"responses": {"type": "sticker"}}}
    )
    deleted_count += conversational_pull_result.modified_count

    if deleted_count > 0:
        await send_and_auto_delete_reply(message, text=f"Jaisa hukum mere aaka! 🧞‍♀️ Maine **{percentage}%** stickers ko dhoondh ke delete kar diya. Total **{deleted_count}** stickers removed. Ab woh history ka hissa nahi raha! ✨ (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Deleted {deleted_count} stickers based on {percentage}% request. (Code by @asbhaibsr)")
    else:
        await send_and_auto_delete_reply(message, text="Umm, mujhe tumhare is query se koi **sticker** mila hi nahi apne database mein. Ya toh sticker hi nahi hai, ya percentage bahot kam hai! 🤔 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)

    await store_message(message)
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)

@app.on_message(filters.command("clearearning") & filters.private)
async def clear_earning_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    if message.from_user.id != OWNER_ID:
        await send_and_auto_delete_reply(message, text="Sorry darling! Yeh command sirf mere boss ke liye hai. 🚫 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return

    await reset_monthly_earnings_manual()
    await send_and_auto_delete_reply(message, text="💰 **Earning data successfully cleared!** Ab sab phir se zero se shuru karenge! 😉 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
    logger.info(f"Owner {message.from_user.id} manually triggered earning data reset. (Code by @asbhaibsr)")

    await store_message(message)
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)

@app.on_message(filters.command("restart") & filters.private)
async def restart_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    if message.from_user.id != OWNER_ID:
        await send_and_auto_delete_reply(message, text="Sorry, darling! Yeh command sirf mere boss ke liye hai. 🚫 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return

    await send_and_auto_delete_reply(message, text="Okay, darling! Main abhi ek chhota sa nap le rahi hoon aur phir wapas aa jaungi, bilkul fresh aur energetic! Thoda wait karna, theek hai? ✨ (System by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
    logger.info("Bot is restarting... (System by @asbhaibsr)")
    await asyncio.sleep(0.5)
    os.execl(sys.executable, sys.executable, *sys.argv)

@app.on_message(filters.command("chat") & filters.group)
async def toggle_chat_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    if not message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await send_and_auto_delete_reply(message, text="Yeh command sirf groups mein kaam karti hai, darling! 😉", parse_mode=ParseMode.MARKDOWN)
        return

    member = await client.get_chat_member(message.chat.id, message.from_user.id)
    if member.status not in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
        await send_and_auto_delete_reply(message, text="Maaf karna, yeh command sirf group admins hi use kar sakte hain. 🤷‍♀️", parse_mode=ParseMode.MARKDOWN)
        return

    if len(message.command) < 2:
        current_status_doc = group_tracking_collection.find_one({"_id": message.chat.id})
        current_status = current_status_doc.get("bot_enabled", True) if current_status_doc else True
        status_text = "chaalu hai (ON)" if current_status else "band hai (OFF)"
        await send_and_auto_delete_reply(message, text=f"Main abhi is group mein **{status_text}** hoon. Use `/chat on` ya `/chat off` control karne ke liye. (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return

    action = message.command[1].lower()
    if action == "on":
        group_tracking_collection.update_one({"_id": message.chat.id}, {"$set": {"bot_enabled": True}})
        await send_and_auto_delete_reply(message, text="🚀 Main phir se aa gayi! Ab main is group mein baatein karungi aur seekhungi. 😊", parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Bot enabled in group {message.chat.id} by admin {message.from_user.id}. (Code by @asbhaibsr)")
    elif action == "off":
        group_tracking_collection.update_one({"_id": message.chat.id}, {"$set": {"bot_enabled": False}})
        await send_and_auto_delete_reply(message, text="😴 Main abhi thodi der ke liye chup ho rahi hoon. Jab meri zaroorat ho, `/chat on` karke bula lena. Bye-bye! 👋", parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Bot disabled in group {message.chat.id} by admin {message.from_user.id}. (Code by @asbhaibsr)")
    else:
        await send_and_auto_delete_reply(message, text="Galat command, darling! `/chat on` ya `/chat off` use karo. 😉", parse_mode=ParseMode.MARKDOWN)

    await store_message(message)
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)

@app.on_message(filters.command("linkdel") & filters.group)
async def toggle_linkdel_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    if not await is_admin_or_owner(client, message.chat.id, message.from_user.id):
        await send_and_auto_delete_reply(message, text="Maaf karna, ye command sirf mere boss (admin) hi use kar sakte hain! 🤷‍♀️", parse_mode=ParseMode.MARKDOWN)
        return

    if len(message.command) < 2:
        current_status_doc = group_tracking_collection.find_one({"_id": message.chat.id})
        current_status = current_status_doc.get("linkdel_enabled", False) if current_status_doc else False
        status_text = "chalu hai (ON)" if current_status else "band hai (OFF)"
        await send_and_auto_delete_reply(message, text=f"Meri 'link jadu' ki chhadi abhi **{status_text}** hai. Ise control karne ke liye `/linkdel on` ya `/linkdel off` use karo. 😉", parse_mode=ParseMode.MARKDOWN)
        return

    action = message.command[1].lower()
    if action == "on":
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("✨ ᴋɪᴅɴᴀᴘ ᴍᴇ ᴅᴀʀʟɪɴɢ ✨", url=f"https://t.me/{client.me.username}?startgroup=true")]]
        )
        group_tracking_collection.update_one({"_id": message.chat.id}, {"$set": {"linkdel_enabled": True}}, upsert=True)
        await send_and_auto_delete_reply(message, text="He he he! 🤭 Ab koi bhi shararati link bhejega, to main use jadu se gayab kar dungi! 🪄 Group ko ekdam saaf-suthra rakhna hai na! 😉", reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Link deletion enabled in group {message.chat.id} by admin {message.from_user.id}.")
    elif action == "off":
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("✨ ᴋɪᴅɴᴀᴘ ᴍᴇ ᴅᴀʀʟɪɴɢ ✨", url=f"https://t.me/{client.me.username}?startgroup=true")]]
        )
        group_tracking_collection.update_one({"_id": message.chat.id}, {"$set": {"linkdel_enabled": False}}, upsert=True)
        await send_and_auto_delete_reply(message, text="Theek hai, theek hai! Maine apni 'link jadu' ki chhadi rakh di hai! 😇 Ab aap jo chahe link bhej sakte hain! Par dhyan se, okay?", reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Link deletion disabled in group {message.chat.id} by admin {message.from_user.id}.")
    else:
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("✨ ᴋɪᴅɴᴀᴘ ᴍᴇ ᴅᴀʀʟɪɴɢ ✨", url=f"https://t.me/{client.me.username}?startgroup=true")]]
        )
        await send_and_auto_delete_reply(message, text="Umm... mujhe samajh nahi aaya! 😕 `/linkdel on` ya `/linkdel off` use karo, please! ✨", reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
    await store_message(message)

@app.on_message(filters.command("biolinkdel") & filters.group)
async def toggle_biolinkdel_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    if not await is_admin_or_owner(client, message.chat.id, message.from_user.id):
        await send_and_auto_delete_reply(message, text="Maaf karna, ye command sirf mere boss (admin) hi use kar sakte hain! 🤷‍♀️", parse_mode=ParseMode.MARKDOWN)
        return

    if len(message.command) < 2:
        current_status_doc = group_tracking_collection.find_one({"_id": message.chat.id})
        current_status = current_status_doc.get("biolinkdel_enabled", False) if current_status_doc else False
        status_text = "chalu hai (ON)" if current_status else "band hai (OFF)"
        await send_and_auto_delete_reply(message, text=f"Meri 'bio-link police' abhi **{status_text}** hai. Ise control karne ke liye `/biolinkdel on` ya `/biolinkdel off` use karo. 👮‍♀️", parse_mode=ParseMode.MARKDOWN)
        return

    action = message.command[1].lower()
    if action == "on":
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("✨ ᴋɪᴅɴᴀᴘ ᴍᴇ ᴅᴀʀʟɪɴɢ ✨", url=f"https://t.me/{client.me.username}?startgroup=true")]]
        )
        group_tracking_collection.update_one({"_id": message.chat.id}, {"$set": {"biolinkdel_enabled": True}}, upsert=True)
        await send_and_auto_delete_reply(message, text="Hmm... 😼 Ab se jo bhi **user apni bio mein `t.me` ya `http/https` link rakhega**, main uske **message ko chupchap hata dungi!** (Agar use `/biolink` se chhoot nahi mili hai). Group mein koi masti nahi!🤫", reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Biolink deletion enabled in group {message.chat.id} by admin {message.from_user.id}.")
    elif action == "off":
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("✨ ᴋɪᴅɴᴀᴘ ᴍᴇ ᴅᴀʀʟɪɴɢ ✨", url=f"https://t.me/{client.me.username}?startgroup=true")]]
        )
        group_tracking_collection.update_one({"_id": message.chat.id}, {"$set": {"biolinkdel_enabled": False}}, upsert=True)
        await send_and_auto_delete_reply(message, text="Okay darlings! 😇 Ab main users ki bio mein `t.me` aur `http/https` links ko check karna band kar rahi hoon! Sab free-free! 🎉", reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Biolink deletion disabled in group {message.chat.id} by admin {message.from_user.id}.")
    else:
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("✨ ᴋɪᴅɴᴀᴘ ᴍᴇ ᴅᴀʀʟɪɴɢ ✨", url=f"https://t.me/{client.me.username}?startgroup=true")]]
        )
        await send_and_auto_delete_reply(message, text="Umm... mujhe samajh nahi aaya! 😕 `/biolinkdel on` ya `/biolinkdel off` use karo, please! ✨", reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
    await store_message(message)

@app.on_message(filters.command("biolink") & filters.group)
async def allow_biolink_user_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    if not await is_admin_or_owner(client, message.chat.id, message.from_user.id):
        await send_and_auto_delete_reply(message, text="Maaf karna, ye command sirf mere boss (admin) hi use kar sakte hain! 🤷‍♀️", parse_mode=ParseMode.MARKDOWN)
        return

    if len(message.command) < 2:
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("✨ ᴋɪᴅɴᴀᴘ ᴍᴇ ᴅᴀʀʟɪɴɢ ✨", url=f"https://t.me/{client.me.username}?startgroup=true")]]
        )
        await send_and_auto_delete_reply(message, text="Kis user ko bio-link ki chhoot deni hai? Mujhe uski User ID do na, jaise: `/biolink 123456789` ya `/biolink remove 123456789`! 😉", reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
        return

    action_or_user_id = message.command[1].lower()
    target_user_id = None

    if action_or_user_id == "remove" and len(message.command) > 2:
        try:
            target_user_id = int(message.command[2])
            biolink_exceptions_collection.delete_one({"_id": target_user_id})
            keyboard = InlineKeyboardMarkup(
                [[InlineKeyboardButton("✨ ᴋɪᴅɴᴀᴘ ᴍᴇ ᴅᴀʀʟɪɴɢ ✨", url=f"https://t.me/{client.me.username}?startgroup=true")]]
            )
            await send_and_auto_delete_reply(message, text=f"Okay! ✨ User `{target_user_id}` ko ab bio mein link rakhne ki chhoot nahi milegi! Bye-bye permission! 👋", reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
            logger.info(f"Removed user {target_user_id} from biolink exceptions in group {message.chat.id}.")
        except ValueError:
            await send_and_auto_delete_reply(message, text="Umm, galat User ID! 🧐 User ID ek number hoti hai. Fir se try karo, please! 😉", parse_mode=ParseMode.MARKDOWN)
    else:
        try:
            target_user_id = int(action_or_user_id)
            biolink_exceptions_collection.update_one(
                {"_id": target_user_id},
                {"$set": {"allowed_by_admin": True, "added_on": datetime.now(), "credit": "by @asbhaibsr"}},
                upsert=True
            )
            keyboard = InlineKeyboardMarkup(
                [[InlineKeyboardButton("✨ ᴋɪᴅɴᴀᴘ ᴍᴇ ᴅᴀʀʟɪɴɢ ✨", url=f"https://t.me/{client.me.username}?startgroup=true")]]
            )
            await send_and_auto_delete_reply(message, text=f"Yay! 🎉 Maine user `{target_user_id}` ko special permission de di hai! Ab ye **apni bio mein `t.me` ya `http/https` links** rakh payenge aur unke message delete nahi honge! Kyunki admin ne bola, to bola!👑", reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
            logger.info(f"Added user {target_user_id} to biolink exceptions in group {message.chat.id}.")
        except ValueError:
            await send_and_auto_delete_reply(message, text="Umm, galat User ID! 🧐 User ID ek number hoti hai. Fir se try karo, please! 😉", parse_mode=ParseMode.MARKDOWN)
    await store_message(message)

@app.on_message(filters.command("usernamedel") & filters.group)
async def toggle_usernamedel_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    if not await is_admin_or_owner(client, message.chat.id, message.from_user.id):
        await send_and_auto_delete_reply(message, text="Maaf karna, ye command sirf mere boss (admin) hi use kar sakte hain! 🤷‍♀️", parse_mode=ParseMode.MARKDOWN)
        return

    if len(message.command) < 2:
        current_status_doc = group_tracking_collection.find_one({"_id": message.chat.id})
        current_status = current_status_doc.get("usernamedel_enabled", False) if current_status_doc else False
        status_text = "chalu hai (ON)" if current_status else "band hai (OFF)"
        await send_and_auto_delete_reply(message, text=f"Meri '@' tag police abhi **{status_text}** hai. Ise control karne ke liye `/usernamedel on` ya `/usernamedel off` use karo.🚨", parse_mode=ParseMode.MARKDOWN)
        return

    action = message.command[1].lower()
    if action == "on":
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("✨ ᴋɪᴅɴᴀᴘ ᴍᴇ ᴅᴀʀʟɪɴɢ ✨", url=f"https://t.me/{client.me.username}?startgroup=true")]]
        )
        group_tracking_collection.update_one({"_id": message.chat.id}, {"$set": {"usernamedel_enabled": True}}, upsert=True)
        await send_and_auto_delete_reply(message, text="Cheen-cheen! 🐦 Ab se koi bhi `@` karke kisi ko bhi pareshan nahi kar payega! Jo karega, uska message main fat se uda dungi!💨 Mujhe disturbance pasand nahi! 😠", reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Username deletion enabled in group {message.chat.id} by admin {message.from_user.id}.")
    elif action == "off":
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("✨ ᴋɪᴅɴᴀᴘ ᴍᴇ ᴅᴀʀʟɪɴɢ ✨", url=f"https://t.me/{client.me.username}?startgroup=true")]]
        )
        group_tracking_collection.update_one({"_id": message.chat.id}, {"$set": {"usernamedel_enabled": False}}, upsert=True)
        await send_and_auto_delete_reply(message, text="Theek hai! Aaj se meri @ wali aankhen band! 😴 Ab aap jo chahe @ karo! Par zyada tang mat karna kisi ko! 🥺", reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Username deletion disabled in group {message.chat.id} by admin {message.from_user.id}.")
    else:
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("✨ ᴋɪᴅɴᴀᴘ ᴍᴇ ᴅᴀʀʟɪɴɢ ✨", url=f"https://t.me/{client.me.username}?startgroup=true")]]
        )
        await send_and_auto_delete_reply(message, text="Umm... mujhe samajh nahi aaya! 😕 `/usernamedel on` ya `/usernamedel off` use karo, please! ✨", reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
    await store_message(message)

@app.on_message(filters.command("clearall") & filters.private)
async def clear_all_dbs_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    if message.from_user.id != OWNER_ID:
        await send_and_auto_delete_reply(message, text="Maaf karna, ye command sirf mere boss ke liye hai. 🚫", parse_mode=ParseMode.MARKDOWN)
        return

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Han, delete karen ⚠️", callback_data='confirm_clearall_dbs'),
                InlineKeyboardButton("Nahi, rehne dein ✅", callback_data='cancel_clearall_dbs')
            ]
        ]
    )

    await send_and_auto_delete_reply(
        message,
        text="⚠️ **Chetavani:** Kya aap wakai apni sabhi MongoDB database (Messages, Buttons, Tracking) ka **sara data** delete karna chahte hain?\n\n"
             "Yeh karwai **aparivartaniya (irreversible)** hai aur aapka sara data hamesha ke liye hat jaega.\n\n"
             "Soch samajh kar chunein!",
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )
    logger.info(f"Owner {message.from_user.id} initiated /clearall command. Waiting for confirmation.")
    await store_message(message) 

@app.on_message(filters.command("clearmydata"))
async def clear_my_data_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    target_user_id = None
    if len(message.command) > 1 and message.from_user.id == OWNER_ID:
        try:
            target_user_id = int(message.command[1])
            if target_user_id == client.me.id:
                await send_and_auto_delete_reply(message, text="Aap mere data ko delete nahi kar sakte, boss! 😅", parse_mode=ParseMode.MARKDOWN)
                return
        except ValueError:
            await send_and_auto_delete_reply(message, text="Galat User ID format. Kripya ek vaidh sankhyatmak ID den.", parse_mode=ParseMode.MARKDOWN)
            return
    elif len(message.command) > 1 and message.from_user.id != OWNER_ID:
        await send_and_auto_delete_reply(message, text="Yeh command aise upyog karne ke liye aap adhikrit nahi hain. Yeh suvidha keval mere boss ke liye hai.", parse_mode=ParseMode.MARKDOWN)
        return
    else:
        target_user_id = message.from_user.id

    if not target_user_id:
        await send_and_auto_delete_reply(message, text="Mujhe pata nahi chal raha ki kiska data delete karna hai. 😕", parse_mode=ParseMode.MARKDOWN)
        return

    try:
        deleted_messages_count = messages_collection.delete_many({"user_id": target_user_id}).deleted_count
        deleted_earning_data = earning_tracking_collection.delete_one({"_id": target_user_id}).deleted_count
        
        owner_taught_responses_collection.update_many(
            {"responses.user_id": target_user_id},
            {"$pull": {"responses": {"user_id": target_user_id}}}
        )
        owner_taught_responses_collection.delete_many({"responses": []})

        conversational_learning_collection.update_many(
            {"responses.user_id": target_user_id},
            {"$pull": {"responses": {"user_id": target_user_id}}}
        )
        conversational_learning_collection.delete_many({"responses": []})


        if deleted_messages_count > 0 or deleted_earning_data > 0:
            if target_user_id == message.from_user.id:
                await send_and_auto_delete_reply(message, text=f"Wah! ✨ Maine aapki `{deleted_messages_count}` baatcheet ke messages aur earning data delete kar diye hain. Ab aap bilkul fresh ho! 😊", parse_mode=ParseMode.MARKDOWN)
                logger.info(f"User {target_user_id} successfully cleared their data.")
            else:
                await send_and_auto_delete_reply(message, text=f"Boss ka order! 👑 Maine user `{target_user_id}` ke `{deleted_messages_count}` baatcheet ke messages aur earning data delete kar diye hain. 😉", parse_mode=ParseMode.MARKDOWN)
                logger.info(f"Owner {message.from_user.id} cleared data for user {target_user_id}.")
        else:
            if target_user_id == message.from_user.id:
                await send_and_auto_delete_reply(message, text="Aapke paas koi data store nahi hai jise delete kiya ja sake. Mera database to ekdam khali hai aapke liye! 🤷‍♀️", parse_mode=ParseMode.MARKDOWN)
            else:
                await send_and_auto_delete_reply(message, text=f"User `{target_user_id}` ka koi data nahi mila jise delete kiya ja sake.", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await send_and_auto_delete_reply(message, text=f"Data delete karne mein kuch gadbad ho gayi: {e}. Oh no! 😱", parse_mode=ParseMode.MARKDOWN)
        logger.error(f"Error clearing data for user {target_user_id}: {e}")
    await store_message(message)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)
@app.on_message(filters.text & filters.group)
async def handle_group_messages(client: Client, message: Message):
    if not message.from_user or message.from_user.is_bot:
        return
    
    group_doc = group_tracking_collection.find_one({"_id": message.chat.id})
    if not group_doc or not group_doc.get("bot_enabled", True):
        return

    user_mention = f"[{message.from_user.first_name}](tg://user?id={message.from_user.id})"
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("✨ ᴋɪᴅɴᴀᴘ ᴍᴇ ᴅᴀʀʟɪɴɢ ✨", url=f"https://t.me/{client.me.username}?startgroup=true")]]
    )

    # Check for biolink
    if group_doc.get("biolinkdel_enabled", False):
        user_id = message.from_user.id
        is_exception = biolink_exceptions_collection.find_one({"_id": user_id})
        if not is_exception:
            try:
                user_info = await client.get_chat(user_id)
                if user_info.bio and any(link in user_info.bio for link in ["t.me/", "http://", "https://"]):
                    warning_text = (
                        f"**❌ Aisa Mat Karo {user_mention}! ❌**\n\n"
                        f"<blockquote>\n"
                        f"**🚫 Stop it!** This group does not allow **links in your bio**. Please follow the rules, otherwise I'll have to take stricter action. 🥺\n"
                        f"</blockquote>"
                    )
                    await send_and_auto_delete_reply(message, text=warning_text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
                    await message.delete()
                    return
            except Exception as e:
                logger.warning(f"Could not get user bio for {user_id}: {e}")

    # Check for general links
    if group_doc.get("linkdel_enabled", False) and message.text:
        if any(link in message.text for link in ["t.me/", "http://", "https://"]):
            if not await is_admin_or_owner(client, message.chat.id, message.from_user.id):
                warning_text = (
                    f"**❌ Aisa Mat Karo {user_mention}! ❌**\n\n"
                    f"<blockquote>\n"
                    f"**🚫 Stop it!** This group does not allow **sending links**. Please follow the rules, otherwise I'll have to take stricter action. 🥺\n"
                    f"</blockquote>"
                )
                await send_and_auto_delete_reply(message, text=warning_text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
                await message.delete()
                return

    # Check for username tags
    if group_doc.get("usernamedel_enabled", False) and message.text:
        if "@" in message.text and len(message.text.split()) > 1 and not message.text.startswith("@"):
            if not await is_admin_or_owner(client, message.chat.id, message.from_user.id):
                warning_text = (
                    f"**❌ Aisa Mat Karo {user_mention}! ❌**\n\n"
                    f"<blockquote>\n"
                    f"**🚫 Stop it!** This group does not allow **tagging other users**. Please follow the rules, otherwise I'll have to take stricter action. 🥺\n"
                    f"</blockquote>"
                )
                await send_and_auto_delete_reply(message, text=warning_text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
                await message.delete()
                return

    # If no violations, continue with your existing code
    await store_message(client, message)
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)
    await update_group_info(message.chat.id, message.chat.title, message.chat.username)
