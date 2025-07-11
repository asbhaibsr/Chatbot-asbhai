# handlers/command_handlers.py

import asyncio
import time
import sys
import os
import pytz
from datetime import datetime, timedelta
import re

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatType, ChatMemberStatus, ParseMode

from config import (
    OWNER_ID, UPDATE_CHANNEL_USERNAME, ASBHAI_USERNAME, ASFILTER_BOT_USERNAME,
    BOT_PHOTO_URL, REPO_LINK, COMMAND_COOLDOWN_TIME, MAX_MESSAGES_THRESHOLD, PRUNE_PERCENTAGE
)
from database.mongo_setup import (
    messages_collection, buttons_collection, group_tracking_collection,
    user_tracking_collection, earning_tracking_collection, reset_status_collection
)
from utils.helpers import (
    logger, is_on_command_cooldown, update_command_cooldown,
    store_message, update_group_info, update_user_info,
    get_top_earning_users, reset_monthly_earnings_manual,
    send_and_auto_delete_reply, prune_old_messages
)

# NOTE: Pyrogram Client (app) will be passed from main.py at runtime
# so it's not defined here, but functions will use it.

async def start_private_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    user_name = message.from_user.first_name if message.from_user else "Dost"

    welcome_message = (
        f"🌟 हे **{user_name}** जानू! आपका स्वागत है! 🌟\n\n"
        "मैं आपकी मदद करने के लिए तैयार हूँ!\n"
        "अपनी सभी कमांड्स देखने के लिए नीचे दिए गए 'सहायता' बटन पर क्लिक करें।"
    )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("➕ मुझे ग्रुप में जोड़ें", url=f"https://t.me/{client.me.username}?startgroup=true")
            ],
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

async def start_group_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    user_name = message.from_user.first_name if message.from_user else "Dost"

    welcome_message = (
        f"🌟 हे **{user_name}** जानू! आपका स्वागत है! 🌟\n\n"
        "मैं ग्रुप की सभी बातें सुनने और सीखने के लिए तैयार हूँ!\n"
        "अपनी सभी कमांड्स देखने के लिए नीचे दिए गए 'सहायता' बटन पर क्लिक करें।"
    )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("➕ मुझे ग्रुप में जोड़ें", url=f"https://t.me/{client.me.username}?startgroup=true")
            ],
            [
                InlineKeyboardButton("📣 Updates Channel", url=f"https://t.me/{UPDATE_CHANNEL_USERNAME}"),
                InlineKeyboardButton("❓ Support Group", url="https://t.me/aschat_group")
            ]
            ,
            [
                InlineKeyboardButton("ℹ️ सहायता ❓", callback_data="show_help_menu"),
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


async def top_users_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    top_users = await get_top_earning_users()

    if not top_users:
        await send_and_auto_delete_reply(message, text="😢 अब तक कोई भी उपयोगकर्ता लीडरबोर्ड पर नहीं है! सक्रिय होकर पहले बनें! ✨\n\n**Powered By:** @asbhaibsr", parse_mode=ParseMode.MARKDOWN)
        return

    earning_messages = [
        "👑 **Top Active Users - ✨ VIP Leaderboard! ✨** 👑\n\n"
    ]

    prizes = {
        1: "💰 ₹50",
        2: "💸 ₹30",
        3: "🎁 ₹20",
        4: f"🎬 @{ASFILTER_BOT_USERNAME} का 1 हफ़्ते का प्रीमियम प्लान", # Updated prize for 4th rank
        5: f"🎬 @{ASFILTER_BOT_USERNAME} का 3 दिन का प्रीमियम प्लान"  # New prize for 5th rank
    }

    for i, user in enumerate(top_users[:5]): # Display top 5 users
        rank = i + 1
        user_name = user.get('first_name', 'Unknown User')
        username_str = f"@{user.get('username')}" if user.get('username') else f"ID: `{user.get('user_id')}`"
        message_count = user.get('message_count', 0)
        
        # Determine prize string
        prize_str = prizes.get(rank, "🏅 कोई पुरस्कार नहीं") # Default for ranks > 5

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
                    # If no public username, try to get an invite link (only for supergroups/channels)
                    try:
                        # Note: export_chat_invite_link might not work if bot is not admin or for basic groups
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

    await send_and_auto_delete_reply(message, text="\n".join(earning_messages), reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
    await store_message(message)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)
    logger.info(f"Top users command processed for user {message.from_user.id} in chat {message.chat.id}. (Code by @asbhaibsr)")

async def broadcast_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    if message.from_user.id != OWNER_ID:
        await send_and_auto_delete_reply(message, text="Oops! Sorry sweetie, yeh command sirf mere boss ke liye hai. 🤷‍♀️ (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return

    if len(message.command) < 2:
        await send_and_auto_delete_reply(message, text="Hey, broadcast karne ke liye kuch likho toh sahi! 🙄 Jaise: `/broadcast Aapka message yahan` (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return

    broadcast_text = " ".join(message.command[1:])

    group_chat_ids = group_tracking_collection.distinct("_id")
    private_chat_ids = user_tracking_collection.distinct("_id")

    all_target_ids = list(set(group_chat_ids + private_chat_ids))

    sent_count = 0
    failed_count = 0
    logger.info(f"Starting broadcast to {len(all_target_ids)} chats (groups and users). (Broadcast by @asbhaibsr)")

    for chat_id in all_target_ids:
        try:
            if chat_id == message.chat.id and message.chat.type == ChatType.PRIVATE:
                continue

            await client.send_message(chat_id, broadcast_text)
            sent_count += 1
            await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"Failed to send broadcast to chat {chat_id}: {e}. (Broadcast by @asbhaibsr)")
            failed_count += 1

    await send_and_auto_delete_reply(message, text=f"Broadcast ho gaya, darling! ✨ **{sent_count}** chats tak pahunchi, aur **{failed_count}** tak nahi. Koi nahi, next time! 😉 (System by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
    await store_message(message)
    logger.info(f"Broadcast command processed by owner {message.from_user.id}. (Code by @asbhaibsr)")

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

    stats_text = (
        "📊 **Bot Statistics** 📊\n"
        f"• Jitne groups mein main hoon: **{unique_group_ids}** lovely groups!\n"
        f"• Total users jo maine observe kiye: **{num_users}** pyaare users!\n"
        f"• Total messages jo maine store kiye: **{total_messages}** baaton ka khazana! 🤩\n\n"
        f"**Powered By:** @asbhaibsr\n**Updates:** @asbhai_bsr\n**Support:** @aschat_group"
    )
    await send_and_auto_delete_reply(message, text=stats_text, parse_mode=ParseMode.MARKDOWN)
    await store_message(message)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)
    logger.info(f"Private stats command processed for user {message.from_user.id}. (Code by @asbhaibsr)")

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

    stats_text = (
        "📊 **Bot Statistics** 📊\n"
        f"• Jitne groups mein main hoon: **{unique_group_ids}** lovely groups!\n"
        f"• Total users jo maine observe kiye: **{num_users}** pyaare users!\n"
        f"• Total messages jo maine store kiye: **{total_messages}** baaton ka khazana! 🤩\n\n"
        f"**Powered By:** @asbhaibsr\n**Updates:** @asbhai_bsr\n**Support:** @aschat_group"
    )
    await send_and_auto_delete_reply(message, text=stats_text, parse_mode=ParseMode.MARKDOWN)
    await store_message(message)
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await update_group_info(message.chat.id, message.chat.title, message.chat.username)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)

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
        group_username_from_db = group.get("username")
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
                except Exception as e:
                    logger.warning(f"Could not get invite link for private group {group_id}: {e}")
                    group_link_display = " (Private Group)"
        except Exception as e:
            logger.warning(f"Could not fetch chat info for group {group_id}: {e}")
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
            await send_and_auto_delete_reply(message, text="Aapne galat Group ID format diya hai. Group ID `-100...` se shuru hoti hai. Thoda dhyaan se! 😊 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
            return

        group_id = int(group_id_str)

        await client.leave_chat(group_id)

        group_tracking_collection.delete_one({"_id": group_id})
        messages_collection.delete_many({"chat_id": group_id})
        # Note: Earning data associated with users in this group is not directly tied to group_id in a way that needs pruning here.
        # It's user-centric. If a user's count reduces, it's handled implicitly by them not messaging anymore.
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

    total_messages = messages_collection.count_documents({})
    if total_messages == 0:
        await send_and_auto_delete_reply(message, text="Mere paas abhi koi data nahi hai delete karne ke liye. Sab clean-clean hai! ✨ (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return

    messages_to_delete_count = int(total_messages * (percentage / 100))
    if messages_to_delete_count == 0 and percentage > 0:
        await send_and_auto_delete_reply(message, text=f"Itna kam data hai ki {percentage}% delete karne se kuch fark nahi padega! 😂 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return
    elif messages_to_delete_count == 0 and percentage == 0:
        await send_and_auto_delete_reply(message, text="Zero percent? That means no deletion! 😉 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return


    oldest_message_ids = []
    for msg in messages_collection.find({}) \
                                        .sort("timestamp", 1) \
                                        .limit(messages_to_delete_count):
        oldest_message_ids.append(msg['_id'])

    if oldest_message_ids:
        delete_result = messages_collection.delete_many({"_id": {"$in": oldest_message_ids}})
        await send_and_auto_delete_reply(message, text=f"Wow! 🤩 Maine aapka **{percentage}%** data, yaani **{delete_result.deleted_count}** messages, successfully delete kar diye! Ab main thodi light feel kar rahi hoon. ✨ (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Cleared {delete_result.deleted_count} messages based on {percentage}% request. (Code by @asbhaibsr)")
    else:
        await send_and_auto_delete_reply(message, text="Umm, kuch delete karne ke liye mila hi nahi. Lagta hai tumne pehle hi sab clean kar diya hai! 🤷‍♀️ (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)

    await store_message(message)
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)

async def delete_specific_message_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    if message.from_user.id != OWNER_ID:
        await send_and_auto_delete_reply(message, text="Oops! Sorry sweetie, yeh command sirf mere boss ke liye hai. 🤷‍♀️ (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return

    if len(message.command) < 2:
        await send_and_auto_delete_reply(message, text="Kaun sa message delete karna hai, batao toh sahi! Jaise: `/deletemessage hello` ya `/deletemessage 'kya haal hai'` ya `deletemessage <sticker_file_id>` 👻 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return

    search_query = " ".join(message.command[1:])
    deleted_count = 0

    # Try to delete by exact content or partial content
    # First, try to match content (text or emoji for sticker)
    if search_query:
        # Check for sticker ID first (starts with BQAD, CAAD, etc.)
        if re.match(r'^(BQAD|CAAD|AgAD|CgAD)', search_query):
            delete_result = messages_collection.delete_many({"sticker_id": search_query})
            deleted_count += delete_result.deleted_count
        else:
            # If not a sticker ID, treat as text content
            # Using $regex with .* to allow partial matches as requested
            delete_result = messages_collection.delete_many({"content": {"$regex": f".*{re.escape(search_query)}.*", "$options": "i"}})
            deleted_count += delete_result.deleted_count

    if deleted_count > 0:
        await send_and_auto_delete_reply(message, text=f"Jaisa hukum mere aaka! 🧞‍♀️ Maine '{search_query}' se milte-julte **{deleted_count}** messages/stickers ko dhoondh ke delete kar diya. Ab woh history ka हिस्सा nahi raha! ✨ (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Deleted {deleted_count} messages/stickers with query: '{search_query}'. (Code by @asbhaibsr)")
    else:
        await send_and_auto_delete_reply(message, text="Umm, mujhe tumhare is query se koi message ya sticker mila hi nahi apne database mein. Spelling/ID check kar lo? 🤔 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)

    await store_message(message)
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)

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

async def clear_my_data_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    target_user_id = None
    if len(message.command) > 1 and message.from_user.id == OWNER_ID:
        try:
            target_user_id = int(message.command[1])
            # Ensure owner is not trying to delete bot's own data or system data
            if target_user_id == client.me.id:
                await send_and_auto_delete_reply(message, text="आप मेरे डेटा को डिलीट नहीं कर सकते, बॉस! 😅", parse_mode=ParseMode.MARKDOWN)
                return
        except ValueError:
            await send_and_auto_delete_reply(message, text="गलत User ID फ़ॉर्मेट। कृपया एक वैध संख्यात्मक ID दें।", parse_mode=ParseMode.MARKDOWN)
            return
    elif len(message.command) > 1 and message.from_user.id != OWNER_ID:
        await send_and_auto_delete_reply(message, text="यह कमांड ऐसे उपयोग करने के लिए आप अधिकृत नहीं हैं। यह सुविधा केवल मेरे बॉस के लिए है।", parse_mode=ParseMode.MARKDOWN)
        return
    else:
        target_user_id = message.from_user.id

    if not target_user_id:
        await send_and_auto_delete_reply(message, text="मुझे पता नहीं चल रहा कि किसका डेटा डिलीट करना है। 😕", parse_mode=ParseMode.MARKDOWN)
        return

    try:
        deleted_messages_count = messages_collection.delete_many({"user_id": target_user_id}).deleted_count
        deleted_earning_data = earning_tracking_collection.delete_one({"_id": target_user_id}).deleted_count # Also clear earning data for that user

        if deleted_messages_count > 0 or deleted_earning_data > 0:
            if target_user_id == message.from_user.id:
                await send_and_auto_delete_reply(message, text=f"वाह! ✨ मैंने आपकी `{deleted_messages_count}` बातचीत के मैसेज और अर्निंग डेटा डिलीट कर दिए हैं। अब आप बिल्कुल फ्रेश हो! 😊", parse_mode=ParseMode.MARKDOWN)
                logger.info(f"User {target_user_id} successfully cleared their data.")
            else: # Owner deleting another user's data
                await send_and_auto_delete_reply(message, text=f"बॉस का ऑर्डर! 👑 मैंने यूजर `{target_user_id}` के `{deleted_messages_count}` बातचीत के मैसेज और अर्निंग डेटा डिलीट कर दिए हैं। 😉", parse_mode=ParseMode.MARKDOWN)
                logger.info(f"Owner {message.from_user.id} cleared data for user {target_user_id}.")
        else:
            if target_user_id == message.from_user.id:
                await send_and_auto_delete_reply(message, text="आपके पास कोई डेटा स्टोर नहीं है जिसे डिलीट किया जा सके। मेरा डेटाबेस तो एकदम खाली है आपके लिए! 🤷‍♀️", parse_mode=ParseMode.MARKDOWN)
            else:
                await send_and_auto_delete_reply(message, text=f"यूजर `{target_user_id}` का कोई डेटा नहीं मिला जिसे डिलीट किया जा सके।", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await send_and_auto_delete_reply(message, text=f"डेटा डिलीट करने में कुछ गड़बड़ हो गई: {e}. ओह नो! 😱", parse_mode=ParseMode.MARKDOWN)
        logger.error(f"Error clearing data for user {target_user_id}: {e}")
    await store_message(message)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)
