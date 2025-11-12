#  events.py

# Import necessary libraries
from pyrogram import Client, filters
from pyrogram.types import Message, ChatMemberUpdated, InlineKeyboardMarkup, InlineKeyboardButton
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
    is_admin_or_owner, contains_link, contains_mention, delete_after_delay_for_message,
    update_message_reply_cooldown 
)

# -----------------
# Cooldown Logic
# -----------------

# Cooldown logic for group replies
last_reply_time = {}
REPLY_COOLDOWN_SECONDS = 8
cooldown_locks = {}

# -----------------
# New User, Group Join/Left Handlers (FIXED SECTION)
# -----------------

@app.on_message(filters.private & filters.command("start"))
async def start_command_handler(client: Client, message: Message):
    """
    Handles the /start command and also checks if it's a new user.
    This ensures that the new user notification is always sent on the first start.
    """
    user_id = message.from_user.id
    user_exists = user_tracking_collection.find_one({"_id": user_id})

    # If the user is new, send a notification to the owner
    if not user_exists:
        logger.info(f"New user detected with /start command: {user_id}")
        await update_user_info(user_id, message.from_user.username, message.from_user.first_name)
        
        notification_text = (
            f"🆕 **New User Alert!**\n"
            f"A new user has started the bot!\n\n"
            f"• **User ID:** `{user_id}`\n"
            f"• **Username:** @{message.from_user.username or 'N/A'}\n"
            f"• **Name:** {message.from_user.first_name or ''} {message.from_user.last_name or ''}\n"
            f"• **Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"Powered by @asbhaibsr"
        )
        
        try:
            await client.send_message(
                chat_id=OWNER_ID,
                text=notification_text,
                parse_mode=ParseMode.MARKDOWN
            )
            logger.info(f"Sent new user notification to owner for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to send new user notification: {e}")
    
    # You can add your original /start message logic here if you have one.
    # For example:
    # await message.reply("Welcome to the bot!")


@app.on_chat_member_updated()
async def chat_member_updated_handler(client: Client, update: ChatMemberUpdated):
    """
    A more reliable handler for detecting when the bot is added to or removed from a group,
    and when a user blocks/unblocks the bot in private chat.
    """
    me = await client.get_me()

    # 1. --- Handle Bot Join/Left/Ban/Block Updates (Bot-specific updates) ---
    if update.new_chat_member and update.new_chat_member.user.id == me.id:
        
        # Bot was added to a new group
        if update.new_chat_member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR]:
            logger.info(f"Bot was added to chat {update.chat.id}. Updating info and notifying owner.")
            await update_group_info(update.chat.id, update.chat.title, update.chat.username)

            group_title = update.chat.title or f"Unknown Group (ID: {update.chat.id})"
            added_by_user = update.from_user.first_name if update.from_user else "Unknown User"
            added_by_user_id = update.from_user.id if update.from_user else "N/A"

            # --- Invite Link Logic ---
            invite_link = "N/A (Bot may not have admin rights or chat is too restricted)"
            try:
                link = await client.export_chat_invite_link(chat_id=update.chat.id)
                invite_link = f"**[Join Group]({link})**"
            except Exception as e:
                if update.chat.username:
                    invite_link = f"**[Group Link](https://t.me/{update.chat.username})**"
                else:
                    logger.warning(f"Could not get invite link for {update.chat.id}. Error: {e}")
            # --- Invite Link Logic End ---

            notification_message = (
                f"🥳 **New Group Alert!**\n"
                f"The bot has been added to a new group!\n\n"
                f"• **Group Name:** {group_title}\n"
                f"• **Group Link:** {invite_link}\n"
                f"• **Group ID:** `{update.chat.id}`\n"
                f"• **Added By:** {added_by_user} (`{added_by_user_id}`)\n"
                f"• **Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"Powered by @asbhaibsr"
            )
            try:
                await client.send_message(chat_id=OWNER_ID, text=notification_message, parse_mode=ParseMode.MARKDOWN)
                logger.info(f"Owner notified about new group: {group_title} with invite link.")
            except Exception as e:
                logger.error(f"Could not notify owner about new group {group_title}: {e}.")

        # Bot was removed from a group (The requested fix + Data Cleanup)
        # FIX: Added update.old_chat_member check for reliability
        elif update.new_chat_member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED] and \
             update.old_chat_member and update.old_chat_member.status not in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]:
            
            logger.info(f"Bot was removed from chat {update.chat.id}. Cleaning data and notifying owner.")
            
            # --- Data Cleanup for Group Left (Delete group data, keep user messages) ---
            group_tracking_collection.delete_one({"_id": update.chat.id})
            # messages_collection.delete_many({"chat_id": update.chat.id}) <-- NOT DELETING user messages as requested.
            # Add other cleanup logic for group-specific collections if needed...

            # FIX: Ensure we have a valid group title and action-by user
            group_title = update.chat.title or f"Unknown Group (ID: {update.chat.id})"
            if update.from_user and update.from_user.id != me.id:
                removed_by_user = update.from_user.first_name
                removed_by_user_id = update.from_user.id
            else:
                removed_by_user = "Unknown User/Telegram System"
                removed_by_user_id = "N/A"

            notification_message = (
                f"💔 **Group Left Alert!**\n"
                f"The bot was removed from a group!\n\n"
                f"• **Group Name:** {group_title}\n"
                f"• **Group ID:** `{update.chat.id}`\n"
                f"• **Action By:** {removed_by_user} (`{removed_by_user_id}`)\n"
                f"• **Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"Powered by @asbhaibsr"
            )
            try:
                await client.send_message(chat_id=OWNER_ID, text=notification_message, parse_mode=ParseMode.MARKDOWN)
                logger.info(f"Owner notified about bot leaving group: {group_title}.")
            except Exception as e:
                logger.error(f"Could not notify owner about bot leaving group {group_title}: {e}. Check if owner blocked the bot.")

        # Bot was blocked by user (Private Chat, status changes to KICKED/BANNED) (Data Cleanup Added)
        elif update.chat.type == ChatType.PRIVATE and update.new_chat_member.status in [ChatMemberStatus.KICKED, ChatMemberStatus.BANNED]:
            user_id = update.chat.id
            user_name = update.chat.first_name or f"User ID: {user_id}"
            
            logger.info(f"Bot was blocked by user {user_id}. Deleting all user data.")

            # --- Data Cleanup for User Block (Delete all user data) ---
            user_tracking_collection.delete_one({"_id": user_id})
            messages_collection.delete_many({"user_id": user_id})
            conversational_learning_collection.delete_many({"user_id": user_id})
            biolink_exceptions_collection.delete_one({"_id": user_id})
            earning_tracking_collection.delete_one({"user_id": user_id})
            reset_status_collection.delete_one({"user_id": user_id})
            # Add other cleanup logic for user-specific collections if needed...

            notification_message = (
                f"🚫 **User Blocked Alert!**\n"
                f"The bot has been blocked by a user in private chat.\n\n"
                f"• **User:** {user_name} (`{user_id}`)\n"
                f"• **Status:** BLOCKED (Data Deleted)\n"
                f"• **Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"Powered by @asbhaibsr"
            )
            try:
                await client.send_message(chat_id=OWNER_ID, text=notification_message, parse_mode=ParseMode.MARKDOWN)
                logger.info(f"Owner notified about user {user_id} blocking the bot.")
            except Exception as e:
                logger.error(f"Could not notify owner about user blocking bot: {e}.")
    
    # 2. --- Handle Regular Member Left/Kick Updates (Existing Logic - Now with better check) ---
    if update.new_chat_member and update.old_chat_member:
        user_id = update.new_chat_member.user.id
        
        # We only care about regular members leaving/being kicked, not the bot itself
        if user_id != me.id:
            
            # Check if the member's status changed TO LEFT or BANNED 
            # AND the previous status was NOT LEFT/BANNED. This is the robust way.
            if update.new_chat_member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED] and \
               update.old_chat_member.status not in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]:
                
                # Check if the action was performed by an admin/owner (meaning a kick/ban)
                action_by_user_id = update.from_user.id if update.from_user else None
                # If the user leaving is NOT the same as the user taking the action, it's an admin action (kick/ban)
                is_admin_action = (action_by_user_id is not None) and (action_by_user_id != user_id)
                
                member_name = update.new_chat_member.user.first_name or f"User ID: {user_id}"
                group_title = update.chat.title or f"Unknown Group (ID: {update.chat.id})"

                if is_admin_action:
                    # User was KICKED or BANNED by an admin/owner
                    action_taker = update.from_user.first_name if update.from_user else "Unknown Admin"
                    notification_text = (
                        f"🚨 **Member Kicked/Banned!**\n"
                        f"A member was removed from a group.\n\n"
                        f"• **Group Name:** {group_title}\n"
                        f"• **Group ID:** `{update.chat.id}`\n"
                        f"• **Member:** {member_name} (`{user_id}`)\n"
                        f"• **Action By:** {action_taker} (`{action_by_user_id}`)\n"
                        f"• **Status:** **{update.new_chat_member.status.name}**\n"
                        f"• **Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                        f"Powered by @asbhaibsr"
                    )
                else:
                    # User LEFT the group (Self-removed)
                    notification_text = (
                        f"🚪 **Member Left Group!**\n"
                        f"A member has voluntarily left the group.\n\n"
                        f"• **Group Name:** {group_title}\n"
                        f"• **Group ID:** `{update.chat.id}`\n"
                        f"• **Member:** {member_name} (`{user_id}`)\n"
                        f"• **Status:** **LEFT**\n"
                        f"• **Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                        f"Powered by @asbhaibsr"
                    )
                
                try:
                    await client.send_message(chat_id=OWNER_ID, text=notification_text, parse_mode=ParseMode.MARKDOWN)
                    logger.info(f"Owner notified about member {user_id} leaving/being removed from group {update.chat.id}.")
                except Exception as e:
                    logger.error(f"Could not notify owner about member leaving/being removed from group {update.chat.id}: {e}.")


# -----------------
# Callback Handlers
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
# Main Message Handler
# -----------------

@app.on_message(filters.text | filters.sticker | filters.photo | filters.video | filters.document)
async def handle_message_and_reply(client: Client, message: Message):
    if message.from_user and message.from_user.is_bot:
        logger.debug(f"Skipping message from bot user: {message.from_user.id}.")
        return

    is_command = message.text and message.text.startswith('/')
    if is_command:
        # Command handling is done in commands.py, so we exit here for events.py to avoid duplication/errors.
        return

    is_group_chat = message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]
    
    # -----------------------------------------------------
    # FIX: Check if bot is admin (This is CRITICAL for chat)
    # -----------------------------------------------------
    if is_group_chat:
        me = await client.get_me()
        try:
            member = await client.get_chat_member(message.chat.id, me.id)
            if member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                logger.info(f"Bot is not an admin in group {message.chat.id}. Skipping all actions for this group.")
                return 
        except Exception as e:
            # If bot cannot check its status (e.g., no 'manage group' permission)
            if "CHAT_ADMIN_REQUIRED" in str(e) or "USER_NOT_PARTICIPANT" in str(e):
                logger.warning(f"Bot has no permission to check its own admin status in group {message.chat.id}. Skipping all actions.")
                # IMPORTANT: If the bot is not an admin, it may not be able to delete links or reply,
                # but if it has basic read/write access, it might still reply. 
                # We'll allow processing below this if it's not strictly for admin tasks.
                # However, for safety, keeping this 'return' is typical for such a complex bot.
                return 
            logger.error(f"Error checking bot's admin status in group {message.chat.id}: {e}")
            return # Exit the function if checking the bot's status failed

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
            # --- 🟢 बदला हुआ: बेहतर लिंक डिलीशन नोटिफिकेशन 🟢 ---
            if contains_link(message.text) and not is_sender_admin:
                try:
                    await message.delete()
                    # यूजर का नाम ब्लू लिंक में
                    user_mention = message.from_user.mention(style='md')
                    me = await client.get_me()
                    
                    # आपका "kidneep me" (Invite Me) बटन
                    keyboard = InlineKeyboardMarkup(
                        [[InlineKeyboardButton("➕ Invite Me", url=f"https://t.me/{me.username}?startgroup=true")]]
                    )
                    
                    # टेलीग्राम कोट के साथ नया टेक्स्ट
                    alert_text = (
                        f"{user_mention}\n\n"
                        f"> 🤫 **Links are not allowed here!**\n"
                        f"> Your message was automatically deleted."
                    )
                    
                    sent_delete_alert = await delete_after_delay_for_message(
                        message, 
                        text=alert_text, 
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=keyboard
                    )
                    logger.info(f"Deleted link message {message.id} from user {message.from_user.id} in chat {message.chat.id}.")
                    return
                except Exception as e:
                    logger.error(f"Error deleting link message {message.id}: {e}")
            # --- 🟢 बदले हुए का अंत 🟢 ---
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
                    # --- 🟢 बदला हुआ: बेहतर बायो लिंक नोटिफिकेशन 🟢 ---
                    if URL_PATTERN.search(user_bio):
                        try:
                            await message.delete()
                            user_mention = message.from_user.mention(style='md')
                            me = await client.get_me()
                            
                            keyboard = InlineKeyboardMarkup(
                                [[InlineKeyboardButton("➕ Invite Me", url=f"https://t.me/{me.username}?startgroup=true")]]
                            )
                            
                            alert_text = (
                                f"{user_mention}\n\n"
                                f"> 😲 **You have a link in your bio!**\n"
                                f"> Your message was deleted. Please remove the link or ask an admin for an exception (`/addbiolink {user_id}`)."
                            )
                            
                            sent_delete_alert = await delete_after_delay_for_message(
                                message,
                                text=alert_text,
                                parse_mode=ParseMode.MARKDOWN,
                                reply_markup=keyboard
                            )
                            logger.info(f"Deleted message {message.id} from user {user_id} due to link in bio in chat {message.chat.id}.")
                            return
                        except Exception as e:
                            logger.error(f"Error deleting message {message.id} due to bio link: {e}")
                    # --- 🟢 बदले हुए का अंत 🟢 ---
                elif (is_sender_admin or is_biolink_exception) and URL_PATTERN.search(user_bio):
                    logger.info(f"Admin's or excepted user's bio link was ignored for message {message.id} in chat {message.chat.id}.")
        except Exception as e:
            logger.error(f"Error checking user bio for user {user_id} in chat {message.chat.id}: {e}")

    # --- Username Mention Deletion Filter ---
    if is_group_chat and message.text:
        current_group_settings = group_tracking_collection.find_one({"_id": message.chat.id})
        if current_group_settings and current_group_settings.get("usernamedel_enabled", False):
            # --- 🟢 बदला हुआ: बेहतर यूजरनेम नोटिफिकेशन 🟢 ---
            if contains_mention(message.text) and not is_sender_admin:
                try:
                    await message.delete()
                    user_mention = message.from_user.mention(style='md')
                    me = await client.get_me()
                    
                    keyboard = InlineKeyboardMarkup(
                        [[InlineKeyboardButton("➕ Invite Me", url=f"https://t.me/{me.username}?startgroup=true")]]
                    )
                    
                    alert_text = (
                        f"{user_mention}\n\n"
                        f"> 😬 **Usernames (@) are not allowed here!**\n"
                        f"> Your message was automatically deleted."
                    )
                    
                    sent_delete_alert = await delete_after_delay_for_message(
                        message, 
                        text=alert_text, 
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=keyboard
                    )
                    logger.info(f"Deleted username mention message {message.id} from user {message.from_user.id} in chat {message.chat.id}.")
                    return
                except Exception as e:
                    logger.error(f"Error deleting username message {message.id}: {e}")
            # --- 🟢 बदले हुए का अंत 🟢 ---
            elif contains_mention(message.text) and is_sender_admin:
                logger.info(f"Admin's username mention message {message.id} was not deleted in chat {message.chat.id}.")

    # Message is not a command, proceed with AI/Learning logic
    chat_id = message.chat.id
    
    if chat_id not in cooldown_locks:
        cooldown_locks[chat_id] = asyncio.Lock()
        
    async with cooldown_locks[chat_id]:
        current_time = datetime.now()
        
        # Cooldown check: check if the chat is currently on cooldown (using local dict)
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

        # Generate reply from AI/Learning Tiers
        reply_data = await generate_reply(message)

        if reply_data and reply_data.get("type"):
            reply_type = reply_data["type"]
            reply_content = reply_data.get("content")
            
            # --- CRITICAL: Update Cooldown AFTER successful reply ---
            last_reply_time[chat_id] = current_time # Update local cooldown dict
            update_message_reply_cooldown(chat_id) # Update global cooldown in utils.py
            
            if reply_type == "text" and reply_content:
                await message.reply_text(reply_content, parse_mode=ParseMode.MARKDOWN)
            # Add logic for other reply types (photo, sticker, etc.) if needed here.
            
            logger.info(f"Successfully sent TIER {reply_data.get('tier', 'N/A')} reply to chat {chat_id}.")
        else:
            logger.info(f"No reply generated for message {message.id} in chat {chat_id}.")
