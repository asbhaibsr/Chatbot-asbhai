# events.py

# Import necessary libraries
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatType, ParseMode, ChatMemberStatus
import asyncio
from datetime import datetime, timedelta

# Import utilities and configurations
from config import (
    app, buttons_collection, group_tracking_collection, user_tracking_collection,
    messages_collection, owner_taught_responses_collection, conversational_learning_collection,
    biolink_exceptions_collection, earning_tracking_collection, logger, reset_status_collection,
    OWNER_ID, ASBHAI_USERNAME, URL_PATTERN
)
from utils import (
    update_group_info, update_user_info, store_message, generate_reply,
    is_admin_or_owner, contains_link, contains_mention, delete_after_delay_for_message
)

# -----------------
# Cooldown Logic
# -----------------

# Cooldown logic for group replies
last_reply_time = {}
REPLY_COOLDOWN_SECONDS = 8
cooldown_locks = {}

# -----------------
# Helper Function for Reply & Auto-Delete (kept for clarity)
# -----------------

async def send_and_auto_delete_reply(message, text, parse_mode=None, reply_markup=None, disable_web_page_preview=False, delay=180):
    sent_message = await message.reply_text(
        text=text,
        parse_mode=parse_mode,
        reply_markup=reply_markup,
        disable_web_page_preview=disable_web_page_preview
    )
    asyncio.create_task(delete_after_delay_for_message(sent_message, delay))

# -----------------
# New User Notification Handler
# -----------------

@app.on_message(filters.private & filters.incoming & ~filters.me)
async def handle_new_user_message(client: Client, message: Message):
    user_exists = user_tracking_collection.find_one({"_id": message.from_user.id})
    
    if not user_exists:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)
        
        notification_text = (
            f"🆕 𝗡𝗲𝘄 𝗨𝘀𝗲𝗿 𝗔𝗹𝗲𝗿𝘁!\n"
            f"𝗔 𝗻𝗲𝘄 𝘂𝘀𝗲𝗿 𝗵𝗮𝘀 𝗷𝗼𝗶𝗻𝗲𝗱 𝘁𝗵𝗲 𝗯𝗼𝘁!\n\n"
            f"• 𝗨𝘀𝗲𝗿 𝗜𝗗: `{message.from_user.id}`\n"
            f"• 𝗨𝘀𝗲𝗿𝗻𝗮𝗺𝗲: @{message.from_user.username if message.from_user.username else 'N/A'}\n"
            f"• 𝗡𝗮𝗺𝗲: {message.from_user.first_name or ''} {message.from_user.last_name or ''}\n"
            f"• 𝗙𝗶𝗿𝘀𝘁 𝗠𝗲𝘀𝘀𝗮𝗴𝗲: {message.text or 'N/A (media message)'}\n"
            f"• 𝗧𝗶𝗺𝗲: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"Code By: @asbhaibsr\nUpdates: @asbhai_bsr"
        )
        
        try:
            await client.send_message(
                chat_id=OWNER_ID,
                text=notification_text,
                parse_mode=ParseMode.MARKDOWN
            )
            logger.info(f"Sent new user notification to owner for user {message.from_user.id}")
        except Exception as e:
            logger.error(f"Failed to send new user notification: {e}")

# -----------------
# Callback Handlers (CLEANED: only keeping button logging and clearall confirm logic)
# -----------------

@app.on_callback_query()
async def callback_handler(client, callback_query):
    await callback_query.answer()

    # Log button presses (retaining original data for tracking)
    buttons_collection.insert_one({
        "user_id": callback_query.from_user.id,
        "username": callback_query.from_user.username,
        "first_name": callback_query.from_user.first_name,
        "button_data": callback_query.data,
        "timestamp": datetime.now(),
        "credit": "by @asbhaibsr"
    })

    if callback_query.data == "buy_git_repo":
        await send_and_auto_delete_reply(
            callback_query.message,
            text=f"🤩 𝗜𝗳 𝘆𝗼𝘂 𝘄𝗮𝗻𝘁 𝘆𝗼𝘂𝗿 𝗼𝘄𝗻 𝗯𝗼𝘁 𝗹𝗶𝗸𝗲 𝗺𝗲, 𝘆𝗼𝘂 𝗵𝗮𝘃𝗲 𝘁𝗼 𝗽𝗮𝘆 ₹𝟱𝟬𝟬. 𝗙𝗼𝗿 𝘁𝗵𝗶𝘀, 𝗰𝗼𝗻𝘁𝗮𝗰𝘁 **@{ASBHAI_USERNAME}** 𝗮𝗻𝗱 𝘁𝗲𝗹𝗹 𝗵𝗶𝗺 𝘁𝗵𝗮𝘁 𝘆𝗼𝘂 𝘄𝗮𝗻𝘁 𝘁𝗼 𝗯𝘂𝗶𝗹𝗱 𝘁𝗵𝗶𝘀 𝗯𝗼𝘁'𝘀 𝗰𝗼𝗱𝗲. 𝗛𝘂𝗿𝗿𝘆 𝘂𝗽, 𝗱𝗲𝗮𝗹𝘀 𝗮𝗿𝗲 𝗵𝗼𝘁! 💸\n\n**Owner:** @asbhaibsr\n**Updates:** @asbhai_bsr\n**Support:** @asbhai_bsr",
            parse_mode=ParseMode.MARKDOWN
        )
    # The actual logic for show_earning_leaderboard, show_help_menu, show_earning_rules 
    # should be placed in callbacks.py (which you import) 
    # to avoid duplicating the command logic in event.py.
    # The logging is handled above.

    logger.info(f"Callback query '{callback_query.data}' processed for user {callback_query.from_user.id}.")

@app.on_callback_query(filters.regex("^(confirm_clearall_dbs|cancel_clearall_dbs)$"))
async def handle_clearall_dbs_callback(client: Client, callback_query):
    query = callback_query
    await query.answer()

    if query.from_user.id != OWNER_ID:
        await query.edit_message_text("𝗬𝗼𝘂 𝗮𝗿𝗲 𝗻𝗼𝘁 𝗮𝘂𝘁𝗵𝗼𝗿𝗶𝘇𝗲𝗱 𝘁𝗼 𝗽𝗲𝗿𝗳𝗼𝗿𝗺 𝘁𝗵𝗶𝘀 𝗮𝗰𝘁𝗶𝗼𝗻.")
        return

    if query.data == 'confirm_clearall_dbs':
        await query.edit_message_text("𝗗𝗲𝗹𝗲𝘁𝗶𝗻𝗴 𝗱𝗮𝘁𝗮... 𝗣𝗹𝗲𝗮𝘀𝗲 𝘄𝗮𝗶𝘁.⏳")
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

            await query.edit_message_text("✅ **𝗦𝘂𝗰𝗰𝗲𝘀𝘀:** 𝗔𝗹𝗹 𝗱𝗮𝘁𝗮 𝗳𝗿𝗼𝗺 𝘆𝗼𝘂𝗿 𝗠𝗼𝗻𝗴𝗼𝗗𝗕 𝗗𝗮𝘁𝗮𝗯𝗮𝘀𝗲𝘀 𝗵𝗮𝘀 𝗯𝗲𝗲𝗻 𝘀𝘂𝗰𝗰𝗲𝘀𝘀𝗳𝘂𝗹𝗹𝘆 𝗱𝗲𝗹𝗲𝘁𝗲𝗱. 𝗧𝗵𝗲 𝗯𝗼𝘁 𝗶𝘀 𝗻𝗼𝘄 𝗰𝗼𝗺𝗽𝗹𝗲𝘁𝗲𝗹𝘆 𝗳𝗿𝗲𝘀𝗵! ✨", parse_mode=ParseMode.MARKDOWN)
            logger.info(f"Owner {query.from_user.id} confirmed and successfully cleared all MongoDB data.")
        except Exception as e:
            await query.edit_message_text(f"❌ **𝗘𝗿𝗿𝗼𝗿:** 𝗔 𝗽𝗿𝗼𝗯𝗹𝗲𝗺 𝗼𝗰𝗰𝘂𝗿𝗿𝗲𝗱 𝘄𝗵𝗶𝗹𝗲 𝗱𝗲𝗹𝗲𝘁𝗶𝗻𝗴 𝗱𝗮𝘁𝗮: {e}\n\n𝗳𝗣𝗹𝗲𝗮𝘀𝗲 𝗰𝗵𝗲𝗰𝗸 𝘁𝗵𝗲 𝗹𝗼𝗴𝘀.", parse_mode=ParseMode.MARKDOWN)
            logger.error(f"Error during /clearall confirmation and deletion: {e}")
    elif query.data == 'cancel_clearall_dbs':
        await query.edit_message_text("𝗔𝗰𝘁𝗶𝗼𝗻 𝗰𝗮𝗻𝗰𝗲𝗹𝗹𝗲𝗱. 𝗬𝗼𝘂𝗿 𝗱𝗮𝘁𝗮 𝗶𝘀 𝘀𝗮𝗳𝗲. ✅", parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Owner {query.from_user.id} cancelled /clearall operation.")

# -----------------
# Member Handlers
# -----------------

@app.on_message(filters.new_chat_members)
async def new_member_handler(client: Client, message: Message):
    logger.info(f"New chat members detected in chat {message.chat.id}. Bot ID: {client.me.id}.")

    me = await client.get_me()

    for member in message.new_chat_members:
        logger.info(f"Processing new member: {member.id} ({member.first_name}) in chat {message.chat.id}. Is bot: {member.is_bot}.")
        
        if member.id == me.id:
            if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
                logger.info(f"DEBUG: Bot {me.id} detected as new member in group {message.chat.id}. Calling update_group_info.")
                await update_group_info(message.chat.id, message.chat.title, message.chat.username)
                logger.info(f"Bot joined new group: {message.chat.title} ({message.chat.id}).")

                group_title = message.chat.title if message.chat.title else f"Unknown Group (ID: {message.chat.id})"
                added_by_user = message.from_user.first_name if message.from_user else "Unknown User"
                notification_message = (
                    f"🥳 **𝗡𝗲𝘄 𝗚𝗿𝗼𝘂𝗽 𝗔𝗹𝗲𝗿𝘁!**\n"
                    f"𝗧𝗵𝗲 𝗯𝗼𝘁 𝗵𝗮𝘀 𝗯𝗲𝗲𝗻 𝗮𝗱𝗱𝗲𝗱 𝘁𝗼 𝗮 𝗻𝗲𝘄 𝗴𝗿𝗼𝘂𝗽!\n\n"
                    f"**𝗚𝗿𝗼𝘂𝗽 𝗡𝗮𝗺𝗲:** {group_title}\n"
                    f"**𝗚𝗿𝗼𝘂𝗽 𝗜𝗗:** `{message.chat.id}`\n"
                    f"**𝗔𝗱𝗱𝗲𝗱 𝗕𝘆:** {added_by_user} ({message.from_user.id if message.from_user else 'N/A'})\n"
                    f"**𝗔𝗱𝗱𝗲𝗱 𝗢𝗻:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    f"**Code By:** @asbhaibsr\n**Updates:** @asbhai_bsr\n**Support:** @aschat_group"
                )
                try:
                    await client.send_message(chat_id=OWNER_ID, text=notification_message, parse_mode=ParseMode.MARKDOWN)
                    logger.info(f"Owner notified about new group: {group_title}.")
                except Exception as e:
                    logger.error(f"Could not notify owner about new group {group_title}: {e}.")
        else: # Handle any other new user
            return

    if message.from_user and not message.from_user.is_bot:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)


@app.on_message(filters.left_chat_member)
async def left_member_handler(client: Client, message: Message):
    logger.info(f"Left chat member detected in chat {message.chat.id}. Left member ID: {message.left_chat_member.id}. Bot ID: {client.me.id}.")

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

            logger.info(f"Bot left group: {message.chat.title} ({message.chat.id}). Data cleared.")
            group_title = message.chat.title if message.chat.title else f"Unknown Group (ID: {message.chat.id})"
            left_by_user = message.from_user.first_name if message.from_user else "Unknown User"
            notification_message = (
                f"💔 𝗚𝗿𝗼𝘂𝗽 𝗟𝗲𝗳𝘁 𝗔𝗹𝗲𝗿𝘁!\n"
                f"𝗧𝗵𝗲 𝗯𝗼𝘁 𝘄𝗮𝘀 𝗿𝗲𝗺𝗼𝘃𝗲𝗱 𝗳𝗿𝗼𝗺 𝗮 𝗴𝗿𝗼𝘂𝗽!\n\n"
                f"**𝗚𝗿𝗼𝘂𝗽 𝗡𝗮𝗺𝗲:** {group_title}\n"
                f"**𝗚𝗿𝗼𝘂𝗽 𝗜𝗗:** `{message.chat.id}`\n"
                f"**𝗔𝗰𝘁𝗶𝗼𝗻 𝗕𝘆:** {left_by_user} ({message.from_user.id if message.from_user else 'N/A'})\n"
                f"**𝗟𝗲𝗳𝘁 𝗢𝗻:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"**Code By:** @asbhaibsr\n**Updates:** @asbhai_bsr\n**Support:** @aschat_group"
            )
            try:
                await client.send_message(chat_id=OWNER_ID, text=notification_message, parse_mode=ParseMode.MARKDOWN)
                logger.info(f"Owner notified about bot leaving group: {group_title}.")
            except Exception as e:
                logger.error(f"Could not notify owner about bot leaving group {group_title}: {e}.")
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
    
    # --- Link Deletion Filter ---
    if is_group_chat and message.text:
        current_group_settings = group_tracking_collection.find_one({"_id": message.chat.id})
        if current_group_settings and current_group_settings.get("linkdel_enabled", False):
            if contains_link(message.text) and not is_sender_admin:
                try:
                    await message.delete()
                    sent_delete_alert = await message.reply_text(f"𝗳𝗢𝗵 𝗱𝗲𝗮𝗿! 🧐 𝗦𝗼𝗿𝗿𝘆-𝘀𝗼𝗿𝗿𝘆, **𝗹𝗶𝗻𝗸𝘀 𝗮𝗿𝗲 𝗻𝗼𝘁 𝗮𝗹𝗹𝗼𝘄𝗲𝗱 𝗵𝗲𝗿𝗲!** 🚫 𝗬𝗼𝘂𝗿 𝗺𝗲𝘀𝘀𝗮𝗴𝗲 𝗶𝘀 𝗴𝗼𝗻𝗲!💨 𝗣𝗹𝗲𝗮𝘀𝗲 𝗯𝗲 𝗰𝗮𝗿𝗲𝗳𝘂𝗹 𝗻𝗲𝘅𝘁 𝘁𝗶𝗺𝗲.", quote=True, parse_mode=ParseMode.MARKDOWN)
                    asyncio.create_task(delete_after_delay_for_message(sent_delete_alert, 180))
                    logger.info(f"Deleted link message {message.id} from user {message.from_user.id} in chat {message.chat.id}.")
                    return
                except Exception as e:
                    logger.error(f"Error deleting link message {message.id}: {e}")
            elif contains_link(message.text) and is_sender_admin:
                logger.info(f"Admin's link message {message.id} was not deleted in chat {message.chat.id}.")

    # --- Bio Link Deletion Filter ---
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
                                f"𝗢𝗵 𝗻𝗼! 😲 𝗬𝗼𝘂 𝗵𝗮𝘃𝗲 𝗮 **𝗹𝗶𝗻𝗸 𝗶𝗻 𝘆𝗼𝘂𝗿 𝗯𝗶𝗼!** 𝗧𝗵𝗮𝘁'𝘀 𝘄𝗵𝘆 𝘆𝗼𝘂𝗿 𝗺𝗲𝘀𝘀𝗮𝗴𝗲 𝗱𝗶𝘀𝗮𝗽𝗽𝗲𝗮𝗿𝗲𝗱!👻\n"
                                "𝗣𝗹𝗲𝗮𝘀𝗲 𝗿𝗲𝗺𝗼𝘃𝗲 𝘁𝗵𝗲 𝗹𝗶𝗻𝗸 𝗳𝗿𝗼𝗺 𝘆𝗼𝘂𝗿 𝗯𝗶𝗼. 𝗜𝗳 𝘆𝗼𝘂 𝗿𝗲𝗾𝘂𝗶𝗿𝗲 𝗽𝗲𝗿𝗺𝗶𝘀𝘀𝗶𝗼𝗻, 𝗽𝗹𝗲𝗮𝘀𝗲 𝗰𝗼𝗻𝘁𝗮𝗰𝘁 𝗮𝗻 𝗮𝗱𝗺𝗶𝗻 𝗮𝗻𝗱 𝗮𝘀𝗸 𝘁𝗵𝗲𝗺 𝘁𝗼 𝘂𝘀𝗲 𝘁𝗵𝗲 `/biolink your_userid` 𝗰𝗼𝗺𝗺𝗮𝗻𝗱.",
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

    # --- Username Mention Deletion Filter ---
    if is_group_chat and message.text:
        current_group_settings = group_tracking_collection.find_one({"_id": message.chat.id})
        if current_group_settings and current_group_settings.get("usernamedel_enabled", False):
            if contains_mention(message.text) and not is_sender_admin:
                try:
                    await message.delete()
                    sent_delete_alert = await message.reply_text(f"𝗳𝗧𝘂𝘁-𝘁𝘂𝘁! 😬 𝗬𝗼𝘂 𝘂𝘀𝗲𝗱 `@`! 𝗦𝗼𝗿𝗿𝘆, 𝘁𝗵𝗮𝘁 𝗺𝗲𝘀𝘀𝗮𝗴𝗲 𝗶𝘀 𝗴𝗼𝗻𝗲 𝘁𝗼 𝘁𝗵𝗲 𝘀𝗸𝘆! 🚀 𝗕𝗲 𝗰𝗮𝗿𝗲𝗳𝘂𝗹 𝗻𝗲𝘅𝘁 𝘁𝗶𝗺𝗲, 𝗼𝗸𝗮𝘆? 😉", quote=True, parse_mode=ParseMode.MARKDOWN)
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
            
            # Cooldown check: check if the chat is currently on cooldown
            if chat_id in last_reply_time:
                time_since_last_reply = (current_time - last_reply_time[chat_id]).total_seconds()
                if time_since_last_reply < REPLY_COOLDOWN_SECONDS:
                    logger.info(f"Chat {chat_id} is in cooldown. Skipping reply for message {message.id}.")
                    # Store the message, but don't send a reply
                    await store_message(client, message)
                    return # Exit the function due to cooldown
            
            # Store the message
            await store_message(client, message)

            logger.info(f"Message {message.id} from user {message.from_user.id if message.from_user else 'N/A'} in chat {message.chat.id} (type: {message.chat.type.name}) has been sent to store_message for general storage and earning tracking.")

            # Generate reply from the centralized learning system in util.py
            logger.info(f"Attempting to generate reply for chat {message.chat.id}.")
            
            reply_doc = await generate_reply(message)

            # Update cooldown time, regardless of whether a reply was generated
            last_reply_time[chat_id] = datetime.now()
            logger.info(f"Cooldown updated for chat {chat_id}. Next reply possible after {REPLY_COOLDOWN_SECONDS} seconds.")

            if reply_doc and reply_doc.get("type"):
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
                    if "CHAT_WRITE_FORBIDDEN" in str(e):
                        logger.error(f"Permission error: Bot cannot send messages in chat {message.chat.id}. Leaving group.")
                        try:
                            await client.leave_chat(message.chat.id)
                            await client.send_message(OWNER_ID, f"**𝗔𝗟𝗘𝗥𝗧:** 𝗕𝗼𝘁 𝘄𝗮𝘀 𝗿𝗲𝗺𝗼𝘃𝗲𝗱 𝗳𝗿𝗼𝗺 𝗴𝗿𝗼𝘂𝗽 `{message.chat.id}` 𝗯𝗲𝗰𝗮𝘂𝘀𝗲 𝗶𝘁 𝗹𝗼𝘀𝘁 𝗽𝗲𝗿𝗺𝗶𝘀𝘀𝗶𝗼𝗻 𝘁𝗼 𝘀𝗲𝗻𝗱 𝗺𝗲𝘀𝘀𝗮𝗴𝗲𝘀.")
                        except Exception as leave_e:
                            logger.error(f"Failed to leave chat {message.chat.id} after permission error: {leave_e}")
                    else:
                        logger.error(f"Error sending reply for message {message.id}: {e}.")
            else:
                logger.info("No suitable reply found.")
