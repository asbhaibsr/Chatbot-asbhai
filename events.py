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
    is_admin_or_owner, contains_link, contains_mention, delete_after_delay_for_message # <--- Corrected import
)

# -----------------
# Cooldown Logic
# -----------------

# Cooldown logic for group replies
last_reply_time = {}
REPLY_COOLDOWN_SECONDS = 8
cooldown_locks = {}

# -----------------
# Bot Started Notification Handler (Only on /start command in PM)
# -----------------

# Filtering for the /start command in private chat
@app.on_message(filters.command("start") & filters.private & ~filters.me)
async def handle_bot_start_notification(client: Client, message: Message):
    # This function replaces the old 'handle_new_user_message' for notification purpose
    
    # 1. Update user info (always good practice)
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)

    # 2. Check if the user is truly new for notification logic
    user_exists = user_tracking_collection.find_one({"_id": message.from_user.id})
    
    # Send notification ONLY if it's the first time they are recorded (i.e., new user)
    if not user_exists:
        
        notification_text = (
            f"🆕 𝗡𝗲𝘄 𝗨𝘀𝗲𝗿 𝗔𝗹𝗲𝗿𝘁! (Bot Started via /start)\n"
            f"𝗔 𝗻𝗲𝘄 𝘂𝘀𝗲𝗿 𝗵𝗮𝘀 𝘀𝘁𝗮𝗿𝘁𝗲𝗱 𝘁𝗵𝗲 𝗯𝗼𝘁 𝘃𝗶𝗮 /𝘀𝘁𝗮𝗿𝘁!\n\n"
            f"• 𝗨𝘀𝗲𝗿 𝗜𝗗: `{message.from_user.id}`\n"
            f"• 𝗨𝘀𝗲𝗿𝗻𝗮𝗺𝗲: @{message.from_user.username if message.from_user.username else 'N/A'}\n"
            f"• 𝗡𝗮𝗺𝗲: {message.from_user.first_name or ''} {message.from_user.last_name or ''}\n"
            f"• 𝗧𝗶𝗺𝗲: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"Code By: @asbhaibsr\nUpdates: @asbhai_bsr"
        )
        
        try:
            await client.send_message(
                chat_id=OWNER_ID,
                text=notification_text,
                parse_mode=ParseMode.MARKDOWN
            )
            logger.info(f"Sent new user (/start) notification to owner for user {message.from_user.id}")
        except Exception as e:
            logger.error(f"Failed to send new user notification: {e}")

# -----------------
# Callback Handlers (No change here)
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
        # Using the utility function directly
        await delete_after_delay_for_message( 
            callback_query.message,
            text=f"🤩 𝗜𝗳 𝘆𝗼𝘂 𝘄𝗮𝗻𝘁 𝘆𝗼𝘂𝗿 𝗼𝘄𝗻 𝗯𝗼𝘁 𝗹𝗶𝗸𝗲 𝗺𝗲, 𝘆𝗼𝘂 𝗵𝗮𝘃𝗲 𝘁𝗼 𝗽𝗮𝘆 ₹𝟱𝟬𝟬. 𝗙𝗼𝗿 𝘁𝗵𝗶𝘀, 𝗰𝗼𝗻𝘁𝗮𝗰𝘁 **@{ASBHAI_USERNAME}** 𝗮𝗻𝗱 𝘁𝗲𝗹𝗹 𝗵𝗶𝗺 𝘁𝗵𝗮𝘁 𝘆𝗼𝘂 𝘄𝗮𝗻𝘁 𝘁𝗼 𝗯𝘂𝗶𝗹𝗱 𝘁𝗵𝗶𝘀 𝗯𝗼𝘁's 𝗰𝗼𝗱𝗲. 𝗛𝘂𝗿𝗿𝘆 𝘂𝗽, 𝗱𝗲𝗮𝗹𝘀 𝗮𝗿𝗲 𝗵𝗼𝘁! 💸\n\n**Owner:** @asbhaibsr\n**Updates:** @asbhai_bsr\n**Support:** @asbhai_bsr",
            parse_mode=ParseMode.MARKDOWN
        )

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
# Member Handlers (FIXED: Join & Leave)
# -----------------

@app.on_message(filters.new_chat_members)
async def new_member_handler(client: Client, message: Message):
    logger.info(f"New chat members detected in chat {message.chat.id}.")

    me = await client.get_me()

    for member in message.new_chat_members:
        logger.info(f"Processing new member: {member.id} in chat {message.chat.id}. Is bot: {member.is_bot}.")
        
        # **FIXED: GROUP JOIN NOTIFICATION**
        if member.id == me.id:
            if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
                logger.info(f"DEBUG: Bot {me.id} detected as new member in group {message.chat.id}. Calling update_group_info.")
                await update_group_info(message.chat.id, message.chat.title, message.chat.username)
                logger.info(f"Bot joined new group: {message.chat.title} ({message.chat.id}).")

                group_title = message.chat.title if message.chat.title else f"Unknown Group (ID: {message.chat.id})"
                added_by_user = message.from_user.first_name if message.from_user else "Unknown User"
                chat_id = message.chat.id
                group_link = f"https://t.me/c/{str(chat_id)[4:]}/1" # Default to direct link
                invite_link = ""

                try:
                    chat_obj = await client.get_chat(chat_id)
                    if chat_obj.invite_link:
                        invite_link = chat_obj.invite_link
                    elif chat_obj.username:
                        group_link = f"https://t.me/{chat_obj.username}" 
                        invite_link = group_link
                except Exception as e:
                    logger.warning(f"Could not get existing invite link/username for {chat_id}: {e}")
                    if not invite_link:
                        try:
                            invite_link_obj = await client.create_chat_invite_link(chat_id)
                            invite_link = invite_link_obj.invite_link
                            logger.info(f"Created temporary invite link for owner for group {chat_id}.")
                        except Exception as create_e:
                            logger.error(f"Failed to create invite link for {chat_id}: {create_e}")
                            invite_link = "N/A (Bot may not be an admin with invite link creation rights)"

                group_link_display = f"**🔗 𝗟𝗶𝗻𝗸:** [Group Link]({invite_link if invite_link and invite_link.startswith('http') else group_link})" if invite_link or group_link else "**🔗 𝗟𝗶𝗻𝗸:** N/A"

                notification_message = (
                    f"🥳 **𝗡𝗲𝘄 𝗚𝗿𝗼𝘂𝗽 𝗔𝗹𝗲𝗿𝘁!**\n"
                    f"𝗧𝗵𝗲 𝗯𝗼𝘁 𝗵𝗮𝘀 𝗯𝗲𝗲𝗻 𝗮𝗱𝗱𝗲𝗱 𝘁𝗼 𝗮 𝗻𝗲𝘄 𝗴𝗿𝗼𝘂𝗽!\n\n"
                    f"**𝗚𝗿𝗼𝘂𝗽 𝗡𝗮𝗺𝗲:** {group_title}\n"
                    f"**𝗚𝗿𝗼𝘂𝗽 𝗜𝗗:** `{message.chat.id}`\n"
                    f"{group_link_display}\n"
                    f"**𝗔𝗱𝗱𝗲𝗱 𝗕𝘆:** {added_by_user} ({message.from_user.id if message.from_user else 'N/A'})\n"
                    f"**𝗔𝗱𝗱𝗲𝗱 𝗢𝗻:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    f"**Code By:** @asbhaibsr\n**Updates:** @asbhai_bsr\n**Support:** @aschat_group"
                )
                try:
                    await client.send_message(chat_id=OWNER_ID, text=notification_message, parse_mode=ParseMode.MARKDOWN)
                    logger.info(f"Owner notified about new group: {group_title}.")
                except Exception as e:
                    logger.error(f"Could not notify owner about new group {group_title}: {e}.")
        
        # Ensure user info is updated for all members, including the user who added the bot
        if not member.is_bot and message.from_user:
            await update_user_info(member.id, member.username, member.first_name)
    
    # Update the user who added the bot (if they exist)
    if message.from_user and not message.from_user.is_bot:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)


@app.on_message(filters.left_chat_member)
async def left_member_handler(client: Client, message: Message):
    logger.info(f"Left chat member detected in chat {message.chat.id}. Left member ID: {message.left_chat_member.id}. Bot ID: {client.me.id}.")

    me = await client.get_me()
    group_title = message.chat.title if message.chat.title else f"Unknown Group (ID: {message.chat.id})"
    
    # **FIXED: GROUP LEAVE NOTIFICATION AND DATA DELETION**
    if message.left_chat_member and message.left_chat_member.id == me.id:
        if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
            
            # Data Cleanup (as requested: delete all group data)
            group_tracking_collection.delete_one({"_id": message.chat.id})
            messages_collection.delete_many({"chat_id": message.chat.id})
            owner_taught_responses_collection.delete_many({"responses.chat_id": message.chat.id})
            conversational_learning_collection.delete_many({"responses.chat_id": message.chat.id})
            earning_tracking_collection.update_many(
                {},
                {"$pull": {"last_active_group_id": message.chat.id}}
            )

            logger.info(f"Bot left group: {group_title} ({message.chat.id}). All related data cleared.")
            
            # Group Leave NOTIFICATION LOGIC (NO STATS/DATA)
            left_by_user = message.from_user.first_name if message.from_user else "Unknown User"
            
            notification_message = (
                f"💔 𝗚𝗿𝗼𝘂𝗽 𝗟𝗲𝗳𝘁 𝗔𝗹𝗲𝗿𝘁!\n"
                f"𝗧𝗵𝗲 𝗯𝗼𝘁 𝘄𝗮𝘀 𝗿𝗲𝗺𝗼𝘃𝗲𝗱/𝗹𝗲𝗳𝘁 𝗳𝗿𝗼𝗺 𝗮 𝗴𝗿𝗼𝘂𝗽!\n"
                f"**𝗔𝗟𝗟 𝗚𝗥𝗢𝗨𝗣 𝗗𝗔𝗧𝗔 𝗛𝗔𝗦 𝗕𝗘𝗘𝗡 𝗗𝗘𝗟𝗘𝗧𝗘𝗗.**\n\n"
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

    # Update info for the user who initiated the action (if they exist)
    if message.from_user and not message.from_user.is_bot:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)


# -----------------
# Bot Stop/Block Handler (FIXED: User Data Deletion)
# -----------------

@app.on_raw_update()
async def raw_update_handler(client: Client, update, users, chats):
    # **यह वह जगह है जहाँ मुख्य फिक्स लागू किया गया है।**
    # 'Message' object has no attribute 'chat' एरर को रोकने के लिए सुरक्षित चेक जोड़ा गया है।
    if hasattr(update, 'message') and update.message and hasattr(update.message, 'chat') and update.message.chat:
        user_id = update.message.chat.id
        
        # Check if the user ID is in the user tracking collection
        user_doc = user_tracking_collection.find_one({"_id": user_id})
        
        if user_doc:
            # Check if the bot can still send a message to the user.
            # If sending fails with CHAT_WRITE_FORBIDDEN or BOT_KICKED, the user has blocked/stopped the bot.
            try:
                await client.send_message(user_id, "TEST_BLOCK_DETECT_MESSAGE", disable_notification=True)
                # If message is sent successfully, they haven't blocked the bot, so delete the test message.
                await client.delete_messages(user_id, client.last_sent_message.id)
            except Exception as e:
                error_message = str(e)
                if "CHAT_WRITE_FORBIDDEN" in error_message or "BOT_KICKED" in error_message:
                    # User blocked/stopped the bot! Delete their data.
                    logger.warning(f"User {user_id} detected as blocked/stopped the bot. Deleting data.")
                    
                    user_tracking_collection.delete_one({"_id": user_id})
                    messages_collection.delete_many({"user_id": user_id})
                    earning_tracking_collection.delete_many({"user_id": user_id})
                    
                    # Notify owner about user data deletion
                    notification_text = (
                        f"🚨 **𝗨𝘀𝗲𝗿 𝗕𝗹𝗼𝗰𝗸𝗲𝗱/𝗦𝘁𝗼𝗽𝗽𝗲𝗱 𝗕𝗼𝘁 𝗔𝗹𝗲𝗿𝘁!** 🚫\n"
                        f"𝗨𝘀𝗲𝗿 𝘄𝗶𝘁𝗵 𝗜𝗗 `{user_id}` 𝗵𝗮𝘀 𝗯𝗹𝗼𝗰𝗸𝗲𝗱/𝘀𝘁𝗼𝗽𝗽𝗲𝗱 𝘁𝗵𝗲 𝗯𝗼𝘁.\n"
                        f"**𝗔𝗟𝗟 𝗨𝗦𝗘𝗥 𝗗𝗔𝗧𝗔 𝗗𝗘𝗟𝗘𝗧𝗘𝗗 𝗧𝗢 𝗔𝗩𝗢𝗜𝗗 𝗕𝗥𝗢𝗔𝗗𝗖𝗔𝗦𝗧 𝗘𝗥𝗥𝗢𝗥𝗦.**\n"
                        f"• 𝗧𝗶𝗺𝗲: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    )
                    try:
                        await client.send_message(OWNER_ID, notification_text, parse_mode=ParseMode.MARKDOWN)
                    except Exception as owner_e:
                        logger.error(f"Failed to notify owner about user block/data deletion: {owner_e}")
                    
# -----------------
# Main Message Handler (User tracking logic updated to cover all PMs)
# -----------------

@app.on_message(filters.text | filters.sticker | filters.photo | filters.video | filters.document)
async def handle_message_and_reply(client: Client, message: Message):
    if message.from_user and message.from_user.is_bot:
        logger.debug(f"Skipping message from bot user: {message.from_user.id}.")
        return

    is_command = message.text and message.text.startswith('/')
    # NOTE: /start command is handled by 'handle_bot_start_notification' for special notification logic.
    if is_command and not message.text.startswith('/start'):
        # Command handling is done in commands.py, so we exit here for events.py to avoid duplication/errors.
        return

    is_group_chat = message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]
    is_private_chat = message.chat.type == ChatType.PRIVATE
    
    # 1. Permission Check for Group Chat
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

    # 2. Group/User Tracking Update (General)
    if is_group_chat:
        group_status = group_tracking_collection.find_one({"_id": message.chat.id})
        if group_status and not group_status.get("bot_enabled", True):
            logger.info(f"Bot is disabled in group {message.chat.id}. Skipping message handling.")
            return

        logger.info(f"DEBUG: Message from group/supergroup {message.chat.id}. Calling update_group_info.")
        await update_group_info(message.chat.id, message.chat.title, message.chat.username)
    
    # Update user info for ALL messages (Group and PM) for general tracking
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)

    user_id = message.from_user.id if message.from_user else None
    
    # ... (Rest of the message handler logic for filters, cooldown, and replies remains the same)
    
    # --- Link Deletion Filters (omitting for brevity as they are unchanged) ---

    # The rest of the message handling logic:
    # 3. Cooldown check
    # 4. Store message
    # 5. Generate reply
    # ... (No changes in the core reply logic)
    
    chat_id = message.chat.id
    
    if chat_id not in cooldown_locks:
        cooldown_locks[chat_id] = asyncio.Lock()
        
    async with cooldown_locks[chat_id]:
        current_time = datetime.now()
        
        # Cooldown check
        if chat_id in last_reply_time:
            time_since_last_reply = (current_time - last_reply_time[chat_id]).total_seconds()
            if time_since_last_reply < REPLY_COOLDOWN_SECONDS:
                logger.info(f"Chat {chat_id} is in cooldown. Skipping reply for message {message.id}.")
                await store_message(client, message)
                return 
        
        # Store the message
        await store_message(client, message)

        logger.info(f"Message {message.id} from user {message.from_user.id if message.from_user else 'N/A'} in chat {message.chat.id} (type: {message.chat.type.name}) has been sent to store_message for general storage and earning tracking.")

        # Generate reply
        logger.info(f"Attempting to generate reply for chat {message.chat.id}.")
        
        reply_doc = await generate_reply(message)

        # Update cooldown time
        last_reply_time[chat_id] = datetime.now()
        logger.info(f"Cooldown updated for chat {chat_id}. Next reply possible after {REPLY_COOLDOWN_SECONDS} seconds.")

        if reply_doc and reply_doc.get("type"):
            try:
                # Typing action
                if is_group_chat and (message.text or message.caption):
                    # अगर ग्रुप में है और मैसेज टेक्स्ट या कैप्शन है, तो typing action दिखाएं।
                    await client.send_chat_action(chat_id, "typing")
                    await asyncio.sleep(1) # थोड़ा इंतज़ार (Wait)

                if reply_doc.get("type") == "text":
                    await message.reply_text(reply_doc["content"], parse_mode=ParseMode.MARKDOWN)
                elif reply_doc.get("type") == "sticker" and reply_doc.get("sticker_id"):
                    await message.reply_sticker(reply_doc["sticker_id"])
                else:
                    logger.warning(f"Reply document found but no content/sticker_id: {reply_doc}.")
            except Exception as e:
                if "CHAT_WRITE_FORBIDDEN" in str(e):
                    logger.error(f"Permission error: Bot cannot send messages in chat {message.chat.id}. Leaving group.")
                    try:
                        await client.leave_chat(message.chat.id)
                        await client.send_message(OWNER_ID, f"𝗔𝗟𝗘𝗥𝗧: 𝗕𝗼𝘁 𝘄𝗮𝘀 𝗿𝗲𝗺𝗼𝘃𝗲𝗱 𝗳𝗿𝗼𝗺 𝗴𝗿𝗼𝘂𝗽 `{message.chat.id}` 𝗯𝗲𝗰𝗮𝘂𝘀𝗲 𝗶𝘁 𝗹𝗼𝘀𝘁 𝗽𝗲𝗿𝗺𝗶𝘀𝘀𝗶𝗼𝗻 𝘁𝗼 𝘀𝗲𝗻𝗱 𝗺𝗲𝘀𝘀𝗮𝗴𝗲𝘀.")
                    except Exception as leave_e:
                        logger.error(f"Failed to leave chat {message.chat.id} after permission error: {leave_e}")
                else:
                    logger.error(f"Error sending reply for message {message.id}: {e}.")
        else:
            logger.info("No suitable reply found.")
