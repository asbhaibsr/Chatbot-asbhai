# handlers/message_handlers.py

import asyncio
import re
from datetime import datetime

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.raw.functions.messages import SetTyping
from pyrogram.raw.types import SendMessageTypingAction
from pyrogram.enums import ChatType, ChatMemberStatus, ParseMode

from config import OWNER_ID, URL_PATTERN
from database.mongo_setup import (
    messages_collection, group_tracking_collection, user_tracking_collection,
    earning_tracking_collection, biolink_exceptions_collection
)
from utils.helpers import (
    logger, extract_keywords, prune_old_messages,
    update_group_info, update_user_info, is_admin_or_owner,
    contains_link, contains_mention, can_reply_to_chat,
    update_message_reply_cooldown, send_and_auto_delete_reply,
    delete_after_delay_for_message
)


async def store_message(message: Message):
    """Stores a message in the database and updates earning count."""
    try:
        # Avoid storing messages from bots
        if message.from_user and message.from_user.is_bot:
            logger.debug(f"Skipping storage for message from bot: {message.from_user.id}. (Code by @asbhaibsr)")
            return

        message_data = {
            "message_id": message.id,
            "user_id": message.from_user.id if message.from_user else None,
            "username": message.from_user.username if message.from_user else None,
            "first_name": message.from_user.first_name if message.from_user else None,
            "chat_id": message.chat.id,
            "chat_type": message.chat.type.name,
            "chat_title": message.chat.title if message.chat.type != ChatType.PRIVATE else None,
            "timestamp": datetime.now(),
            "is_bot_observed_pair": False,
            "credits": "Code by @asbhaibsr, Support: @aschat_group"
        }

        if message.text:
            message_data["type"] = "text"
            message_data["content"] = message.text
            message_data["keywords"] = extract_keywords(message.text)
            message_data["sticker_id"] = None
        elif message.sticker:
            message_data["type"] = "sticker"
            message_data["content"] = message.sticker.emoji if message.sticker.emoji else ""
            message_data["sticker_id"] = message.sticker.file_id
            message_data["keywords"] = extract_keywords(message.sticker.emoji)
        else:
            logger.debug(f"Unsupported message type for storage: {message.id}. (Code by @asbhaibsr)")
            return

        # Check if this message is a reply to a bot's message
        if message.reply_to_message:
            message_data["is_reply"] = True
            message_data["replied_to_message_id"] = message.reply_to_message.id
            message_data["replied_to_user_id"] = message.reply_to_message.from_user.id if message.reply_to_message.from_user else None

            # Extract content of the message being replied to
            replied_content = None
            if message.reply_to_message.text:
                replied_content = message.reply_to_message.text
            elif message.reply_to_message.sticker:
                replied_content = message.reply_to_message.sticker.emoji if message.reply_to_message.emoji else ""

            message_data["replied_to_content"] = replied_content

            # Check if the reply was to the bot itself
            if message.reply_to_message.from_user and message.reply_to_message.from_user.id == message.chat.app.me.id: # Use message.chat.app.me.id to get bot's ID
                message_data["is_bot_observed_pair"] = True
                original_bot_message_in_db = messages_collection.find_one({"chat_id": message.chat.id, "message_id": message.reply_to_message.id})
                if original_bot_message_in_db:
                    messages_collection.update_one(
                        {"_id": original_bot_message_in_db["_id"]},
                        {"$set": {"is_bot_observed_pair": True}}
                    )
                    logger.debug(f"Marked bot's original message {message.reply_to_message.id} as observed pair. (System by @asbhaibsr)")

        messages_collection.insert_one(message_data)
        logger.info(f"Message stored: {message.id} from {message.from_user.id if message.from_user else 'None'}. (Storage by @asbhaibsr)")

        logger.debug(f"DEBUG: Checking earning condition in store_message: chat_type={message.chat.type.name}, is_from_user={bool(message.from_user)}, is_not_bot={not message.from_user.is_bot if message.from_user else 'N/A'}")

        if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP] and message.from_user and not message.from_user.is_bot:
            user_id_to_track = message.from_user.id
            username_to_track = message.from_user.username
            first_name_to_track = message.from_user.first_name
            current_group_id = message.chat.id
            current_group_title = message.chat.title
            current_group_username = message.chat.username

            logger.info(f"DEBUG: Attempting to update earning count for user {user_id_to_track} ({first_name_to_track}) in chat {message.chat.id}.")

            try:
                earning_tracking_collection.update_one(
                    {"_id": user_id_to_track},
                    {"$inc": {"group_message_count": 1},
                     "$set": {"username": username_to_track,
                              "first_name": first_name_to_track,
                              "last_active_group_message": datetime.now(),
                              "last_active_group_id": current_group_id,
                              "last_active_group_title": current_group_title,
                              "last_active_group_username": current_group_username
                              },
                     "$setOnInsert": {"joined_earning_tracking": datetime.now(), "credit": "by @asbhaibsr"}},
                    upsert=True
                )
                updated_user_data = earning_tracking_collection.find_one({'_id': user_id_to_track})
                current_count = updated_user_data.get('group_message_count', 0) if updated_user_data else 0
                logger.info(f"Group message count updated for user {user_id_to_track} ({first_name_to_track}). Current count: {current_count}. (Earning tracking by @asbhaibsr)")
            except Exception as e:
                logger.error(f"ERROR: Failed to update earning count for user {user_id_to_track}: {e}. (Earning tracking error by @asbhaibsr)")


        await prune_old_messages()

    except Exception as e:
        logger.error(f"Error storing message {message.id}: {e}. (System by @asbhaibsr)")

async def generate_reply(message: Message):
    """Generates a reply based on stored messages."""
    await message.chat.app.invoke( # Use message.chat.app to access the Pyrogram client instance
        SetTyping(
            peer=await message.chat.app.resolve_peer(message.chat.id),
            action=SendMessageTypingAction()
        )
    )
    await asyncio.sleep(0.5)

    if not message.text and not message.sticker:
        return

    query_content = message.text if message.text else (message.sticker.emoji if message.sticker else "")
    query_keywords = extract_keywords(query_content)

    if not query_keywords and not query_content:
        logger.debug("No content or keywords extracted for reply generation. (Code by @asbhaibsr)")
        return

    potential_replies = []

    # Prioritize replies where bot observed a pair (user replied to bot's specific content)
    # Changed to find exact match for replied_to_content
    observed_replies_cursor = messages_collection.find({
        "is_bot_observed_pair": True,
        "replied_to_content": {"$regex": f"^{re.escape(query_content)}$", "$options": "i"},
        "user_id": {"$ne": message.chat.app.me.id} # Ensure the reply is not from the bot itself
    })
    for doc in observed_replies_cursor:
        potential_replies.append(doc)

    if potential_replies:
        chosen_reply = random.choice(potential_replies)
        logger.info(f"Contextual reply found for '{query_content}': {chosen_reply.get('content') or chosen_reply.get('sticker_id')}. (Logic by @asbhaibsr)")
        return chosen_reply

    logger.info(f"No direct observed reply for: '{query_content}'. Falling back to keyword search. (Logic by @asbhaibsr)")

    # Fallback to general keyword search
    # Ensure keywords are not empty before creating regex
    if query_keywords:
        keyword_regex = "|".join([re.escape(kw) for kw in query_keywords])
        general_replies_cursor = messages_collection.find({
            "type": {"$in": ["text", "sticker"]},
            "content": {"$regex": f".*({keyword_regex}).*", "$options": "i"},
            "user_id": {"$ne": message.chat.app.me.id} # Exclude bot's own messages from general replies
        })
    else:
        # If no keywords, fall back to any random message (less ideal but prevents crash)
        general_replies_cursor = messages_collection.find({
            "type": {"$in": ["text", "sticker"]},
            "user_id": {"$ne": message.chat.app.me.id}
        })

    potential_replies = []
    for doc in general_replies_cursor:
        potential_replies.append(doc)

    if potential_replies:
        chosen_reply = random.choice(potential_replies)
        logger.info(f"Keyword-based reply found for '{query_content}': {chosen_reply.get('content') or chosen_reply.get('sticker_id')}. (Logic by @asbhaibsr)")
        return chosen_reply

    logger.info(f"No suitable reply found for: '{query_content}'. (Logic by @asbhaibsr)")
    return None


async def new_member_handler(client: Client, message: Message):
    logger.info(f"New chat members detected in chat {message.chat.id}. Bot ID: {client.me.id}. (Event handled by @asbhaibsr)")

    for member in message.new_chat_members:
        logger.info(f"Processing new member: {member.id} ({member.first_name}) in chat {message.chat.id}. Is bot: {member.is_bot}. (Event handled by @asbhaibsr)")
        
        # Scenario 1: The bot itself joins a new group
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
                    f"**Code By:** @asbhaibsr\n**Updates:** @asbhai_bsr\n**Support:** @aschat_group"
                )
                try:
                    await client.send_message(chat_id=OWNER_ID, text=notification_message, parse_mode=ParseMode.MARKDOWN)
                    logger.info(f"Owner notified about new group: {group_title}. (Notification by @asbhaibsr)")
                except Exception as e:
                    logger.error(f"Could not notify owner about new group {group_title}: {e}. (Notification error by @asbhaibsr)")
            return # Exit function if the member is the bot itself

        # Scenario 2: A new (non-bot) user starts the bot in private
        # Per user's clarification: ONLY notify owner if a NEW user starts the bot in private,
        # NOT when a new user joins a group where the bot is present.
        if not member.is_bot and message.chat.type == ChatType.PRIVATE and member.id == message.from_user.id:
            user_exists = user_tracking_collection.find_one({"_id": member.id})
            if not user_exists: # Only send notification if it's genuinely a new user to the bot's private chat
                user_name = member.first_name if member.first_name else "Naya User"
                user_username = f"@{member.username}" if member.username else "N/A"
                notification_message = (
                    f"✨ **New User Alert! (Private Chat)**\n"
                    f"Ek naye user ne bot ko private mein start kiya hai.\n\n"
                    f"**User Name:** {user_name}\n"
                    f"**User ID:** `{member.id}`\n"
                    f"**Username:** {user_username}\n"
                    f"**Started On:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    f"**Code By:** @asbhaibsr\n**Updates:** @asbhai_bsr\n**Support:** @aschat_group"
                )
                try:
                    await client.send_message(chat_id=OWNER_ID, text=notification_message, parse_mode=ParseMode.MARKDOWN)
                    logger.info(f"Owner notified about new private user: {user_name}. (Notification by @asbhaibsr)")
                except Exception as e:
                    logger.error(f"Could not notify owner about new private user {user_name}: {e}. (Notification error by @asbhaibsr)")

    await store_message(message)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)


async def left_member_handler(client: Client, message: Message):
    logger.info(f"Left chat member detected in chat {message.chat.id}. Left member ID: {message.left_chat_member.id}. Bot ID: {client.me.id}. (Event handled by @asbhaibsr)")

    if message.left_chat_member and message.left_chat_member.id == client.me.id:
        if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
            group_tracking_collection.delete_one({"_id": message.chat.id})
            messages_collection.delete_many({"chat_id": message.chat.id})
            # This part below to update user's group list is not strictly necessary for earning,
            # as earning is based on message count not group membership, but keeping for completeness
            # if `groups` array was used in user_tracking_collection
            earning_tracking_collection.update_many(
                {}, # All users
                {"$pull": {"last_active_group_id": message.chat.id}} # If it was tracking last group specifically
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

    await store_message(message)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)


async def handle_message_and_reply(client: Client, message: Message):
    # Ignore messages from bots
    if message.from_user and message.from_user.is_bot:
        logger.debug(f"Skipping message from bot user: {message.from_user.id}. (Handle message by @asbhaibsr)")
        return

    is_group_chat = message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]

    # Check if bot is enabled in group chats
    if is_group_chat:
        group_status = group_tracking_collection.find_one({"_id": message.chat.id})
        if group_status and not group_status.get("bot_enabled", True):
            logger.info(f"Bot is disabled in group {message.chat.id}. Skipping message handling. (Code by @asbhaibsr)")
            return

    # Apply cooldown for general messages (not commands)
    if message.from_user and not (message.text and message.text.startswith('/')): # Only apply to non-command messages
        chat_id_for_cooldown = message.chat.id
        if not await can_reply_to_chat(chat_id_for_cooldown): # Check cooldown for the specific chat
            logger.info(f"Chat {chat_id_for_cooldown} is on message reply cooldown. Skipping message {message.id}.")
            return # Skip processing and replying to this message

    logger.info(f"Processing message {message.id} from user {message.from_user.id if message.from_user else 'N/A'} in chat {message.chat.id} (type: {message.chat.type.name}). (Handle message by @asbhaibsr)")

    if is_group_chat:
        logger.info(f"DEBUG: Message from group/supergroup {message.chat.id}. Calling update_group_info.")
        await update_group_info(message.chat.id, message.chat.title, message.chat.username)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)

    # --- Check for /linkdel, /biolinkdel, /usernamedel conditions ---
    if is_group_chat:
        current_group_settings = group_tracking_collection.find_one({"_id": message.chat.id})
        user_id = message.from_user.id if message.from_user else None

        is_sender_admin = False
        if user_id:
            is_sender_admin = await is_admin_or_owner(client, message.chat.id, user_id)

        # 1. Link Deletion Check (any link in message content)
        if current_group_settings and current_group_settings.get("linkdel_enabled", False) and message.text:
            if contains_link(message.text) and not is_sender_admin:
                try:
                    await message.delete()
                    sent_delete_alert = await message.reply_text(f"ओहो, ये क्या भेज दिया {message.from_user.mention}? 🧐 सॉरी-सॉरी, यहाँ **लिंक्स अलाउड नहीं हैं!** 🚫 आपका मैसेज तो गया! 💨 अब से ध्यान रखना, हाँ?", quote=True, parse_mode=ParseMode.MARKDOWN)
                    # Schedule deletion of the bot's alert message
                    asyncio.create_task(delete_after_delay_for_message(sent_delete_alert, 180)) # 3 minutes
                    logger.info(f"Deleted link message {message.id} from user {message.from_user.id} in chat {message.chat.id}.")
                    return # Stop processing this message further
                except Exception as e:
                    logger.error(f"Error deleting link message {message.id}: {e}")
            elif contains_link(message.text) and is_sender_admin:
                logger.info(f"Admin's link message {message.id} was not deleted in chat {message.chat.id}.")

        # 2. Biolink Deletion Check (links in user's BIO)
        # This check is only performed if the message has not already been deleted by the linkdel rule
        if current_group_settings and current_group_settings.get("biolinkdel_enabled", False) and user_id:
            try:
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
                            # Schedule deletion of the bot's alert message
                            asyncio.create_task(delete_after_delay_for_message(sent_delete_alert, 180)) # 3 minutes
                            logger.info(f"Deleted message {message.id} from user {user_id} due to link in bio in chat {message.chat.id}.")
                            return # Stop processing this message further
                        except Exception as e:
                            logger.error(f"Error deleting message {message.id} due to bio link: {e}")
                elif (is_sender_admin or is_biolink_exception) and URL_PATTERN.search(user_bio):
                    logger.info(f"Admin's or excepted user's bio link was ignored for message {message.id} in chat {message.chat.id}.")

            except Exception as e:
                logger.error(f"Error checking user bio for user {user_id} in chat {message.chat.id}: {e}")

        # 3. Username Deletion Check (@mentions in message content)
        # This check is only performed if the message has not already been deleted by the above rules
        if current_group_settings and current_group_settings.get("usernamedel_enabled", False) and message.text:
            if contains_mention(message.text) and not is_sender_admin:
                try:
                    await message.delete()
                    sent_delete_alert = await message.reply_text(f"टच-टच {message.from_user.mention}! 😬 आपने `@` का इस्तेमाल किया! सॉरी, वो मैसेज तो चला गया आसमान में! 🚀 अगली बार से ध्यान रखना, हाँ? 😉", quote=True, parse_mode=ParseMode.MARKDOWN)
                    # Schedule deletion of the bot's alert message
                    asyncio.create_task(delete_after_delay_for_message(sent_delete_alert, 180)) # 3 minutes
                    logger.info(f"Deleted username mention message {message.id} from user {message.from_user.id} in chat {message.chat.id}.")
                    return # Stop processing this message further
                except Exception as e:
                    logger.error(f"Error deleting username message {message.id}: {e}")
            elif contains_mention(message.text) and is_sender_admin:
                logger.info(f"Admin's username mention message {message.id} was not deleted in chat {message.chat.id}.")
    # --- END NEW CHECKS ---

    # Only store message and generate reply if it wasn't deleted by any of the above checks AND it's not a command
    if not (message.text and message.text.startswith('/')):
        await store_message(message)

        logger.info(f"Attempting to generate reply for chat {message.chat.id}. (Logic by @asbhaibsr)")
        reply_doc = await generate_reply(message)

        if reply_doc:
            try:
                if reply_doc.get("type") == "text":
                    await message.reply_text(reply_doc["content"], parse_mode=ParseMode.MARKDOWN)
                    logger.info(f"Replied with text: {reply_doc['content']}. (System by @asbhaibsr)")
                elif reply_doc.get("type") == "sticker" and reply_doc.get("sticker_id"):
                    await message.reply_sticker(reply_doc["sticker_id"])
                    logger.info(f"Replied with sticker: {reply_doc['sticker_id']}. (System by @asbhaibsr)")
                else:
                    logger.warning(f"Reply document found but no content/sticker_id: {reply_doc}. (System by @asbhaibsr)")
            except Exception as e:
                logger.error(f"Error sending reply for message {message.id}: {e}. (System by @asbhaibsr)")
            finally:
                # Set cooldown AFTER a reply is sent
                update_message_reply_cooldown(message.chat.id)
        else:
            logger.info("No suitable reply found. (System by @asbhaibsr)")

