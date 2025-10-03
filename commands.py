# commands.py

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatType, ChatMemberStatus, ParseMode
from pyrogram.errors import FloodWait, UserIsBlocked, ChatWriteForbidden, PeerIdInvalid, RPCError
from datetime import datetime
import re 
import asyncio 

# Import utilities and configurations
from config import (
    app, buttons_collection, group_tracking_collection, user_tracking_collection,
    messages_collection, owner_taught_responses_collection, conversational_learning_collection,
    biolink_exceptions_collection, earning_tracking_collection, reset_status_collection, logger,
    OWNER_ID, BOT_PHOTO_URL, UPDATE_CHANNEL_USERNAME, ASBHAI_USERNAME, ASFILTER_BOT_USERNAME, REPO_LINK
)
from utils import (
    is_on_command_cooldown, update_command_cooldown, update_group_info, update_user_info,
    get_top_earning_users, reset_monthly_earnings_manual, delete_after_delay_for_message, # <--- 🟢 FIX: 'delete_after_delay_for_message' को सीधे आयात किया गया
    store_message, is_admin_or_owner
)

import callbacks # <--- This line is essential for importing callbacks.py
import broadcast_handler # <--- 🌟 New broadcast file imported 🌟

# 🔴 REMOVED: Alias the utility function to the expected name for cleaner code.
#             यह लाइन अब ज़रूरी नहीं है क्योंकि 'delete_after_delay_for_message'
#             को सीधे 'send_and_auto_delete_reply' के रूप में इस्तेमाल किया जा रहा है
#             या सीधे इंपोर्ट किया जा रहा है।
send_and_auto_delete_reply = delete_after_delay_for_message # <--- 🟢 FIX: अब यह केवल एक साधारण असाइनमेंट है

# -----------------------------------------------------
# PRIVATE CHAT COMMANDS
# -----------------------------------------------------

@app.on_message(filters.command("start") & filters.private)
async def start_private_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    user_name = message.from_user.first_name if message.from_user else "Friend"
    welcome_message = (
        f"🌟 𝗛𝗲𝘆 **{user_name}** 𝗱𝗲𝗮𝗿! 𝗪𝗲𝗹𝗰𝗼𝗺𝗲! 🌟\n\n"
        "𝗜'𝗺 𝗿𝗲𝗮𝗱𝘆 𝘁𝗼 𝗵𝗲𝗹𝗽 𝘆𝗼𝘂!\n"
        "𝗖𝗹𝗶𝗰𝗸 𝘁𝗵𝗲 '𝗛𝗲𝗹𝗽' 𝗯𝘂𝘁𝘁𝗼𝗻 𝗯𝗲𝗹𝗼𝘄 𝘁𝗼 𝘀𝗲𝗲 𝗮𝗹𝗹 𝗺𝘆 𝗰𝗼𝗺𝗺𝗮𝗻𝗱𝘀."
    )
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✙ꫝᴅᴅ мє ɪη уσυʀ ɢʀσυρ✙", url=f"https://t.me/{client.me.username}?startgroup=true")],
            [
                InlineKeyboardButton("📣 Uᴘᴅᴀᴛᴇꜱ Cʜᴀɴɴᴇʟ", url=f"https://t.me/{UPDATE_CHANNEL_USERNAME}"),
                InlineKeyboardButton("❓ Sᴜᴘᴘᴏʀᴛ Gʀᴏᴜᴘ", url="https://t.me/aschat_group")
            ],
            [
                InlineKeyboardButton("ℹ️ Hᴇʟᴘ ❓", callback_data="show_help_menu"),
                InlineKeyboardButton("💰 Eᴀʀɴɪɴɢ Lᴇ𝗮𝗱𝗲𝗿𝗯𝗼𝗮𝗿𝗱", callback_data="show_earning_leaderboard")
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
    # FIX: store_message removed to prevent it from blocking execution due to command filter.
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)
    logger.info(f"Private start command processed for user {message.from_user.id}.")

@app.on_message(filters.command("topusers") & (filters.private | filters.group))
async def top_users_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    top_users = await get_top_earning_users()
    if not top_users:
        await send_and_auto_delete_reply(message, text="😢 𝗡𝗼 𝘂𝘀𝗲𝗿𝘀 𝗮𝗿𝗲 𝗼𝗻 𝘁𝗵𝗲 𝗹𝗲𝗮𝗱𝗲𝗿𝗯𝗼𝗮𝗿𝗱 𝘆𝗲𝘁! 𝗕𝗲 𝘁𝗵𝗲 𝗳𝗶𝗿𝘀𝘁 𝗯𝘆 𝗯𝗲𝗶𝗻𝗴 𝗮𝗰𝘁𝗶𝘃𝗲! ✨\n\n**Powered By:** @asbhaibsr", parse_mode=ParseMode.MARKDOWN)
        return

    earning_messages = ["👑 **𝗧𝗼𝗽 𝗔𝗰𝘁𝗶𝘃𝗲 𝗨𝘀𝗲𝗿𝘀 - ✨ 𝗩𝗜𝗣 𝗟𝗲𝗮𝗱𝗲𝗿𝗯𝗼𝗮𝗮𝗿𝗱! ✨** 👑\n\n"]
    prizes = {
        1: "💰 ₹50", 2: "💸 ₹30", 3: "🎁 ₹20",
        4: f"🎬 1 𝗪𝗲𝗲𝗸 𝗣𝗿𝗲𝗺𝗶𝘂𝗺 𝗣𝗹𝗮𝗻 𝗼𝗳 @{ASFILTER_BOT_USERNAME}",
        5: f"🎬 3 𝗗𝗮𝘆𝘀 𝗣𝗿𝗲𝗺𝗶𝘂𝗺 𝗣𝗹𝗮𝗻 𝗼𝗳 @{ASFILTER_BOT_USERNAME}"
    }

    for i, user in enumerate(top_users[:5]):
        rank = i + 1
        user_name = user.get('first_name', 'Unknown User')
        username_str = f"@{user.get('username')}" if user.get('username') else f"𝗜𝗗: `{user.get('user_id')}`"
        message_count = user.get('message_count', 0)
        prize_str = prizes.get(rank, "🏅 𝗡𝗼 𝗣𝗿𝗶𝘇𝗲")

        group_info = ""
        last_group_id = user.get('last_active_group_id')
        last_group_title = user.get('last_active_group_title', '𝗨𝗻𝗸𝗻𝗼𝘄𝗻 𝗚𝗿𝗼𝘂𝗽')

        if last_group_id:
            try:
                chat_obj = await client.get_chat(last_group_id)
                if chat_obj.type == ChatType.PRIVATE:
                    group_info = f"   • 𝗔𝗰𝘁𝗶𝘃𝗲 𝗶𝗻: **[𝗣𝗿𝗶𝘃𝗮𝘁𝗲 𝗖𝗵𝗮𝘁](tg://user?id={user.get('user_id')})**\n"
                elif chat_obj.username:
                    group_info = f"   • 𝗔𝗰𝘁𝗶𝘃𝗲 𝗶𝗻: **[{chat_obj.title}](https://t.me/{chat_obj.username})**\n"
                else:
                    try:
                        invite_link = await client.export_chat_invite_link(last_group_id)
                        group_info = f"   • 𝗔𝗰𝘁𝗶𝘃𝗲 𝗶𝗻: **[{chat_obj.title}]({invite_link})**\n"
                    except Exception:
                        group_info = f"   • 𝗔𝗰𝘁𝗶𝘃𝗲 𝗶𝗻: **{chat_obj.title}** (𝗣𝗿𝗶𝘃𝗮𝘁𝗲 𝗚𝗿𝗼𝘂𝗽)\n"
            except Exception as e:
                logger.warning(f"Could not fetch chat info for group ID {last_group_id} for leaderboard: {e}")
                group_info = f"   • 𝗔𝗰𝘁𝗶𝘃𝗲 𝗶𝗻: **{last_group_title}** (𝗜𝗻𝗳𝗼 𝗡𝗼𝘁 𝗔𝘃𝗮𝗶𝗹𝗮𝗯𝗹𝗲)\n"
        else:
            group_info = "   • 𝗔𝗰𝘁𝗶𝘃𝗲 𝗶𝗻: **𝗡𝗼 𝗚𝗿𝗼𝘂𝗽 𝗔𝗰𝘁𝗶𝘃𝗶𝘁𝘆**\n"

        earning_messages.append(
            f"**{rank}.** 🌟 **{user_name}** ({username_str}) 🌟\n"
            f"   • 𝗧𝗼𝘁𝗮𝗹 𝗠𝗲𝘀𝘀𝗮𝗴𝗲𝘀: **{message_count} 💬**\n"
            f"   • 𝗣𝗼𝘁𝗲𝗻𝘁𝗶𝗮𝗹 𝗣𝗿𝗶𝘇𝗲: **{prize_str}**\n"
            f"{group_info}"
        )
    
    earning_messages.append(
        "\n𝗧𝗵𝗶𝘀 𝘀𝘆𝘀𝘁𝗲𝗺 𝗿𝗲𝘀𝗲𝘁𝘀 𝗼𝗻 𝘁𝗵𝗲 𝗳𝗶𝗿𝘀𝘁 𝗼𝗳 𝗲𝘃𝗲𝗿𝘆 𝗺𝗼𝗻𝘁𝗵!\n"
        "𝗨𝘀𝗲 `/help` 𝘁𝗼 𝗸𝗻𝗼𝘄 𝘁𝗵𝗲 𝗚𝗿𝗼𝘂𝗽 𝗿𝘂𝗹𝗲𝘀."
    )
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("💰 Wɪᴛʜᴅʀᴀᴡ", url=f"https://t.me/{ASBHAI_USERNAME}"),
                InlineKeyboardButton("💰 E𝗮𝗿𝗻𝗶𝗻𝗴 Rᴜ𝗹𝗲ꜱ", callback_data="show_earning_rules")
            ]
        ]
    )
    await send_and_auto_delete_reply(message, text="\n".join(earning_messages), reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
    # FIX: store_message removed
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await update_group_info(message.chat.id, message.chat.title, message.chat.username)
    logger.info(f"Top users command processed for user {message.from_user.id} in chat {message.chat.id}.")


@app.on_message(filters.command("stats") & filters.private)
async def stats_private_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    if len(message.command) < 2 or message.command[1].lower() != "check":
        await send_and_auto_delete_reply(message, text="𝗨𝗺𝗺, 𝘁𝗼 𝗰𝗵𝗲𝗰𝗸 𝘀𝘁𝗮𝘁𝘀, 𝗽𝗹𝗲𝗮𝘀𝗲 𝘁𝘆𝗽𝗲 𝗰𝗼𝗿𝗿𝗲𝗰𝘁𝗹𝘆! 𝗟𝗶𝗸𝗲 𝘁𝗵𝗶𝘀: `/stats check`. 😊", parse_mode=ParseMode.MARKDOWN)
        return

    total_messages = messages_collection.count_documents({})
    unique_group_ids = group_tracking_collection.count_documents({})
    num_users = user_tracking_collection.count_documents({})
    total_owner_taught = owner_taught_responses_collection.count_documents({})
    total_conversational_learned = conversational_learning_collection.count_documents({})

    stats_text = (
        "📊 **𝗕𝗼𝘁 𝗦𝘁𝗮𝘁𝗶𝘀𝘁𝗶𝗰𝘀** 📊\n"
        f"• 𝗡𝘂𝗺𝗯𝗲𝗿 𝗼𝗳 𝗴𝗿𝗼𝘂𝗽𝘀 𝗜'𝗺 𝗶𝗻: **{unique_group_ids}** 𝗹𝗼𝘃𝗲𝗹𝘆 𝗴𝗿𝗼𝘂𝗽𝘀!\n"
        f"• 𝗧𝗼𝘁𝗮𝗹 𝘂𝘀𝗲𝗿𝘀 𝗜 𝗼𝗯𝘀𝗲𝗿𝘃𝗲𝗱: **{num_users}** 𝘀𝘄𝗲𝗲𝘁 𝘂𝘀𝗲𝗿𝘀!\n"
        f"• 𝗧𝗼𝘁𝗮𝗹 𝗺𝗲𝘀𝘀𝗮𝗴𝗲𝘀 𝗜 𝘀𝘁𝗼𝗿𝗲𝗱 (𝗢𝗹𝗱 𝗟𝗲𝗮𝗿𝗻𝗶𝗻𝗴): **{total_messages}** 𝘁𝗿𝗲𝗮𝘀𝘂𝗿𝗲 𝗼𝗳 𝗰𝗼𝗻𝘃𝗲𝗿𝘀𝗮𝘁𝗶𝗼𝗻𝘀! 🤩\n"
        f"• 𝗢𝘄𝗻𝗲𝗿-𝘁𝗮𝘂𝗴𝗵𝘁 𝗽𝗮𝘁𝘁𝗲𝗿𝗻𝘀: **{total_owner_taught}** 𝘂𝗻𝗶𝗾𝘂𝗲 𝗽𝗮𝘁𝘁𝗲𝗿𝗻𝘀!\n"
        f"• 𝗖𝗼𝗻𝘃𝗲𝗿𝘀𝗮𝘁𝗶𝗼𝗻𝗮𝗹 𝗽𝗮𝘁𝘁𝗲𝗿𝗻𝘀 𝗹𝗲𝗮𝗿𝗻𝗲𝗱: **{total_conversational_learned}** 𝘂𝗻𝗶𝗾𝘂𝗲 𝗽𝗮𝘁𝘁𝗲𝗿𝗻𝘀!\n\n"
        f"**Powered By:** @asbhaibsr\n**Updates:** @asbhai_bsr\n**Support:** @aschat_group"
    )
    await send_and_auto_delete_reply(message, text=stats_text, parse_mode=ParseMode.MARKDOWN)
    # FIX: store_message removed
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)
    logger.info(f"Private stats command processed for user {message.from_user.id}.")

@app.on_message(filters.command("stats") & filters.group)
async def stats_group_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    if len(message.command) < 2 or message.command[1].lower() != "check":
        await send_and_auto_delete_reply(message, text="𝗨𝗺𝗺, 𝘁𝗼 𝗰𝗵𝗲𝗰𝗸 𝘀𝘁𝗮𝘁𝘀, 𝗽𝗹𝗲𝗮𝘀𝗲 𝘁𝘆𝗽𝗲 𝗰𝗼𝗿𝗿𝗲𝗰𝘁𝗹𝘆! 𝗟𝗶𝗸𝗲 𝘁𝗵𝗶𝘀: `/stats check`. 😊", parse_mode=ParseMode.MARKDOWN)
        return

    total_messages = messages_collection.count_documents({})
    unique_group_ids = group_tracking_collection.count_documents({})
    num_users = user_tracking_collection.count_documents({})
    total_owner_taught = owner_taught_responses_collection.count_documents({})
    total_conversational_learned = conversational_learning_collection.count_documents({})

    stats_text = (
        "📊 **𝗕𝗼𝘁 𝗦𝘁𝗮𝘁𝗶𝘀𝘁𝗶𝗰𝘀** 📊\n"
        f"• 𝗡𝘂𝗺𝗯𝗲𝗿 𝗼𝗳 𝗴𝗿𝗼𝘂𝗽𝘀 𝗜'𝗺 𝗶𝗻: **{unique_group_ids}** 𝗹𝗼𝘃𝗲𝗹𝘆 𝗴𝗿𝗼𝘂𝗽𝘀!\n"
        f"• 𝗧𝗼𝘁𝗮𝗹 𝘂𝘀𝗲𝗿𝘀 𝗜 𝗼𝗯𝘀𝗲𝗿𝘃𝗲𝗱: **{num_users}** 𝘀𝘄𝗲𝗲𝘁 𝘂𝘀𝗲𝗿𝘀!\n"
        f"• 𝗧𝗼𝘁𝗮𝗹 𝗺𝗲𝘀𝘀𝗮𝗴𝗲𝘀 𝗜 𝘀𝘁𝗼𝗿𝗲𝗱 (𝗢𝗹𝗱 𝗟𝗲𝗮𝗿𝗻𝗶𝗻𝗴): **{total_messages}** 𝘁𝗿𝗲𝗮𝘀𝘂𝗿𝗲 𝗼𝗳 𝗰𝗼𝗻𝘃𝗲𝗿𝘀𝗮𝘁𝗶𝗼𝗻𝘀! 🤩\n"
        f"• 𝗢𝘄𝗻𝗲𝗿-𝘁𝗮𝘂𝗴𝗵𝘁 𝗽𝗮𝘁𝘁𝗲𝗿𝗻𝘀: **{total_owner_taught}** 𝘂𝗻𝗶𝗾𝘂𝗲 𝗽𝗮𝘁𝘁𝗲𝗿𝗻𝘀!\n"
        f"• 𝗖𝗼𝗻𝘃𝗲𝗿𝘀𝗮𝘁𝗶𝗼𝗻𝗮𝗹 𝗽𝗮𝘁𝘁𝗲𝗿𝗻𝘀 𝗹𝗲𝗮𝗿𝗻𝗲𝗱: **{total_conversational_learned}** 𝘂𝗻𝗶𝗾𝘂𝗲 𝗽𝗮𝘁𝘁𝗲𝗿𝗻𝘀!\n\n"
        f"**Powered By:** @asbhaibsr\n**Updates:** @asbhai_bsr\n**Support:** @aschat_group"
    )
    await send_and_auto_delete_reply(message, text=stats_text, parse_mode=ParseMode.MARKDOWN)
    # FIX: store_message removed
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
        await send_and_auto_delete_reply(message, text="𝗢𝗼𝗽𝘀! 𝗦𝗼𝗿𝗿𝘆 𝘀𝘄𝗲𝗲𝘁𝗶𝗲, 𝘁𝗵𝗶𝘀 𝗰𝗼𝗺𝗺𝗮𝗻𝗱 𝗶𝘀 𝗼𝗻𝗹𝘆 𝗳𝗼𝗿 𝗺𝘆 𝗯𝗼𝘀𝘀. 𝗬𝗼𝘂 𝗱𝗼𝗻'𝘁 𝗵𝗮𝘃𝗲 𝗽𝗲𝗿𝗺𝗶𝘀𝘀𝗶𝗼𝗻. 🤷‍♀️", parse_mode=ParseMode.MARKDOWN)
        return

    groups = list(group_tracking_collection.find({}))
    if not groups:
        await send_and_auto_delete_reply(message, text="𝗜'𝗺 𝗻𝗼𝘁 𝗶𝗻 𝗮𝗻𝘆 𝗴𝗿𝗼𝘂𝗽 𝗿𝗶𝗴𝗵𝘁 𝗻𝗼𝘄. 𝗜'𝗺 𝗹𝗼𝗻𝗲𝗹𝘆, 𝗽𝗹𝗲𝗮𝘀𝗲 𝗮𝗱𝗱 𝗺𝗲! 🥺", parse_mode=ParseMode.MARKDOWN)
        return

    group_list_text = "📚 **𝗚𝗿𝗼𝘂𝗽𝘀 𝗜'𝗺 𝗜𝗻** 📚\n\n"
    for i, group in enumerate(groups):
        title = group.get("title", "𝗨𝗻𝗸𝗻𝗼𝘄𝗻 𝗚𝗿𝗼𝘂𝗽")
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
                    group_link_display = f" ([𝗜𝗻𝘃𝗶𝘁𝗲 𝗟𝗶𝗻𝗸]({invite_link}))"
                except Exception:
                    group_link_display = " (𝗣𝗿𝗶𝘃𝗮𝘁𝗲 𝗚𝗿𝗼𝘂𝗽)"
        except Exception as e:
            logger.warning(f"Could not fetch chat info for group {group_id}: {e}")
            group_link_display = " (𝗜𝗻𝗳𝗼 𝗡/𝗔)"

        group_list_text += (
            f"{i+1}. **{title}** (`{group_id}`){group_link_display}\n"
            f"   • 𝗝𝗼𝗶𝗻𝗲𝗱: {added_on}\n"
            f"   • 𝗠𝗲𝗺𝗯𝗲𝗿𝘀: {member_count}\n"
        )

    group_list_text += "\n𝗧𝗵𝗶𝘀 𝗱𝗮𝘁𝗮 𝗶𝘀 𝗳𝗿𝗼𝗺 𝘁𝗵𝗲 𝘁𝗿𝗮𝗰𝗸𝗶𝗻𝗴 𝗱𝗮𝘁𝗮𝗯𝗮𝘀𝗲, 𝗶𝘁'𝘀 𝗮 𝘀𝗲𝗰𝗿𝗲𝘁! 🤫\n**Powered By:** @asbhaibsr"
    await send_and_auto_delete_reply(message, text=group_list_text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
    # FIX: store_message removed
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)
    logger.info(f"Groups list command processed by owner {message.from_user.id}.")

@app.on_message(filters.command("leavegroup") & filters.private)
async def leave_group_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    if message.from_user.id != OWNER_ID:
        await send_and_auto_delete_reply(message, text="𝗢𝗼𝗽𝘀! 𝗦𝗼𝗿𝗿𝘆 𝘀𝘄𝗲𝗲𝘁𝗶𝗲, 𝘁𝗵𝗶𝘀 𝗰𝗼𝗺𝗺𝗮𝗻𝗱 𝗶𝘀 𝗼𝗻𝗹𝘆 𝗳𝗼𝗿 𝗺𝘆 𝗯𝗼𝘀𝘀. 𝗬𝗼𝘂 𝗱𝗼𝗻'𝘁 𝗵𝗮𝘃𝗲 𝗽𝗲𝗿𝗺𝗶𝘀𝘀𝗶𝗼𝗻. 🤷‍♀️", parse_mode=ParseMode.MARKDOWN)
        return

    if len(message.command) < 2:
        await send_and_auto_delete_reply(message, text="𝗣𝗹𝗲𝗮𝘀𝗲 𝗽𝗿𝗼𝘃𝗶𝗱𝗲 𝘁𝗵𝗲 𝗚𝗿𝗼𝘂𝗽 𝗜𝗗 𝘆𝗼𝘂 𝘄𝗮𝗻𝘁 𝗺𝗲 𝘁𝗼 𝗹𝗲𝗮𝘃𝗲. 𝗨𝘀𝗮𝗴𝗲: `/leavegroup -1001234567890` (𝗹𝗶𝗸𝗲 𝘁𝗵𝗶𝘀, 𝗱𝗮𝗿𝗹𝗶𝗻𝗴!)", parse_mode=ParseMode.MARKDOWN)
        return

    try:
        group_id_str = message.command[1]
        if not group_id_str.startswith('-100'):
            await send_and_auto_delete_reply(message, text="𝗳𝗬𝗼𝘂 𝗽𝗿𝗼𝘃𝗶𝗱𝗲𝗱 𝘁𝗵𝗲 𝘄𝗿𝗼𝗻𝗴 𝗚𝗿𝗼𝘂𝗽 𝗜𝗗 𝗳𝗼𝗿𝗺𝗮𝘁. 𝗚𝗿𝗼𝘂𝗽 𝗜𝗗 𝘀𝘁𝗮𝗿𝘁𝘀 𝘄𝗶𝘁𝗵 `-100...` 𝗕𝗲 𝗮 𝗹𝗶𝘁𝘁𝗹𝗲 𝗺𝗼𝗿𝗲 𝗰𝗮𝗿𝗲𝗳𝘂𝗹! 😊", parse_mode=ParseMode.MARKDOWN)
            return

        group_id = int(group_id_str)
        await client.leave_chat(group_id)

        group_tracking_collection.delete_one({"_id": group_id})
        messages_collection.delete_many({"chat_id": group_id})
        owner_taught_responses_collection.delete_many({"responses.chat_id": group_id})
        conversational_learning_collection.delete_many({"responses.chat_id": group_id})
        
        logger.info(f"Considered cleaning earning data for users from left group {group_id}.")

        await send_and_auto_delete_reply(message, text=f"𝗦𝘂𝗰𝗰𝗲𝘀𝘀𝗳𝘂𝗹𝗹𝘆 𝗹𝗲𝗳𝘁 𝗴𝗿𝗼𝘂𝗽 `{group_id}`, 𝗮𝗻𝗱 𝗮𝗹𝘀𝗼 𝗰𝗹𝗲𝗮𝗻𝗲𝗱 𝗮𝗹𝗹 𝗶𝘁𝘀 𝗱𝗮𝘁𝗮! 𝗕𝘆𝗲-𝗯𝘆𝗲! 👋", parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Left group {group_id} and cleared its data.")

    except ValueError:
        await send_and_auto_delete_reply(message, text="𝗜𝗻𝘃𝗮𝗹𝗶𝗱 𝗴𝗿𝗼𝘂𝗽 𝗜𝗗 𝗳𝗼𝗿𝗺𝗮𝘁. 𝗣𝗹𝗲𝗮𝘀𝗲 𝗽𝗿𝗼𝘃𝗶𝗱𝗲 𝗮 𝘃𝗮𝗹𝗶𝗱 𝗻𝘂𝗺𝗲𝗿𝗶𝗰 𝗜𝗗. 𝗖𝗵𝗲𝗰𝗸 𝘁𝗵𝗲 𝗻𝘂𝗺𝗯𝗲𝗿𝘀! 😉", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await send_and_auto_delete_reply(message, text=f"𝗔𝗻 𝗲𝗿𝗿𝗼𝗿 𝗼𝗰𝗰𝘂𝗿𝗿𝗲𝗱 𝘄𝗵𝗶𝗹𝗲 𝗹𝗲𝗮𝘃𝗶𝗻𝗴 𝘁𝗵𝗲 𝗴𝗿𝗼𝘂𝗽: {e}. 𝗢𝗵 𝗻𝗼! 😢", parse_mode=ParseMode.MARKDOWN)
        logger.error(f"Error leaving group {group_id_str}: {e}.")

    # FIX: store_message removed
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)


@app.on_message(filters.command("cleardata") & filters.private)
async def clear_data_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    if message.from_user.id != OWNER_ID:
        await send_and_auto_delete_reply(message, text="𝗦𝗼𝗿𝗿𝘆, 𝗱𝗮𝗿𝗹𝗶𝗻𝗴! 𝗧𝗵𝗶𝘀 𝗰𝗼𝗺𝗺𝗮𝗻𝗱 𝗶𝘀 𝗼𝗻𝗹𝘆 𝗳𝗼𝗿 𝗺𝘆 𝗯𝗼𝘀𝘀. 🤫", parse_mode=ParseMode.MARKDOWN)
        return

    if len(message.command) < 2:
        await send_and_auto_delete_reply(message, text="𝗛𝗼𝘄 𝗺𝘂𝗰𝗵 𝗱𝗮𝘁𝗮 𝘁𝗼 𝗰𝗹𝗲𝗮𝗻? 𝗧𝗲𝗹𝗹 𝗺𝗲 𝘁𝗵𝗲 𝗽𝗲𝗿𝗰𝗲𝗻𝘁𝗮𝗴𝗲, 𝗹𝗶𝗸𝗲: `/cleardata 10%` 𝗼𝗿 `/cleardata 100%`! 🧹", parse_mode=ParseMode.MARKDOWN)
        return

    percentage_str = message.command[1].strip('%')
    try:
        percentage = int(percentage_str)
        if not (1 <= percentage <= 100):
            await send_and_auto_delete_reply(message, text="𝗣𝗲𝗿𝗰𝗲𝗻𝘁𝗮𝗴𝗲 𝘀𝗵𝗼𝘂𝗹𝗱 𝗯𝗲 𝗯𝗲𝘁𝘄𝗲𝗲𝗻 1 𝗮𝗻𝗱 100. 𝗕𝗲 𝗮 𝗹𝗶𝘁𝘁𝗹𝗲 𝗰𝗮𝗿𝗲𝗳𝘂𝗹! 🤔", parse_mode=ParseMode.MARKDOWN)
            return
    except ValueError:
        await send_and_auto_delete_reply(message, text="𝗜𝗻𝘃𝗮𝗹𝗶𝗱 𝗽𝗲𝗿𝗰𝗲𝗻𝘁𝗮𝗴𝗲 𝗳𝗼𝗿𝗺𝗮𝘁. 𝗣𝗲𝗿𝗰𝗲𝗻𝘁𝗮𝗴𝗲 𝘀𝗵𝗼𝘂𝗹𝗱 𝗯𝗲 𝗶𝗻 𝗻𝘂𝗺𝗯𝗲𝗿𝘀, 𝗹𝗶𝗸𝗲 `10` 𝗼𝗿 `50`. 𝗧𝗿𝘆 𝗮𝗴𝗮𝗶𝗻!💖", parse_mode=ParseMode.MARKDOWN)
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
        # FIX: The field 'responses.timestamp' might not be indexed correctly for sorting. Using 'responses.0.timestamp' might be more accurate if responses is an array.
        # But for now, keeping original logic and trusting the DB design.
        for doc in owner_taught_responses_collection.find({}).sort("responses.timestamp", 1).limit(docs_to_delete_owner):
            oldest_owner_taught_ids.append(doc['_id'])
        if oldest_owner_taught_ids:
            deleted_count_owner_taught = owner_taught_responses_collection.delete_many({"_id": {"$in": oldest_owner_taught_ids}}).deleted_count

    if total_conversational > 0:
        docs_to_delete_conv = int(total_conversational * (percentage / 100))
        oldest_conv_ids = []
        # FIX: The field 'responses.timestamp' might not be indexed correctly for sorting. Using 'responses.0.timestamp' might be more accurate if responses is an array.
        # But for now, keeping original logic and trusting the DB design.
        for doc in conversational_learning_collection.find({}).sort("responses.timestamp", 1).limit(docs_to_delete_conv):
            oldest_conv_ids.append(doc['_id'])
        if oldest_conv_ids:
            deleted_count_conversational = conversational_learning_collection.delete_many({"_id": {"$in": oldest_conv_ids}}).deleted_count
            
    total_deleted = deleted_count_old + deleted_count_owner_taught + deleted_count_conversational

    if total_deleted > 0:
        await send_and_auto_delete_reply(message, text=f"𝗪𝗼𝘄! 🤩 𝗜 𝗵𝗮𝘃𝗲 𝘀𝘂𝗰𝗰𝗲𝘀𝘀𝗳𝘂𝗹𝗹𝘆 𝗱𝗲𝗹𝗲𝘁𝗲𝗱 𝘆𝗼𝘂𝗿 **{percentage}%** 𝗱𝗮𝘁𝗮! 𝗔 𝘁𝗼𝘁𝗮𝗹 𝗼𝗳 **{total_deleted}** 𝗲𝗻𝘁𝗿𝗶𝗲𝘀 (𝗢𝗹𝗱: {deleted_count_old}, 𝗢𝘄𝗻𝗲𝗿-𝗧𝗮𝘂𝗴𝗵𝘁: {deleted_count_owner_taught}, 𝗖𝗼𝗻𝘃𝗲𝗿𝘀𝗮𝘁𝗶𝗼𝗻𝗮𝗹: {deleted_count_conversational}) 𝗮𝗿𝗲 𝗰𝗹𝗲𝗮𝗻𝗲𝗱. 𝗜 𝗳𝗲𝗲𝗹 𝗮 b𝗶𝘁 𝗹𝗶𝗴𝗵𝘁𝗲𝗿 𝗻𝗼𝘄. ✨", parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Cleared {total_deleted} messages across collections based on {percentage}% request.")
    else:
        await send_and_auto_delete_reply(message, text="𝗨𝗺𝗺, 𝗜 𝗱𝗶𝗱𝗻't 𝗳𝗶𝗻𝗱 𝗮𝗻𝘆𝘁𝗵𝗶𝗻𝗴 𝘁𝗼 𝗱𝗲𝗹𝗲𝘁𝗲. 𝗜𝘁 𝘀𝗲𝗲𝗺𝘀 𝘆𝗼𝘂'𝘃𝗲 𝗮𝗹𝗿𝗲𝗮𝗱𝘆 𝗰𝗹𝗲𝗮𝗻𝗲𝗱 𝗲𝘃𝗲𝗿𝘆𝘁𝗵𝗶𝗻𝗴! 🤷‍♀️", parse_mode=ParseMode.MARKDOWN)

    # FIX: store_message removed
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)


@app.on_message(filters.command("deletemessage") & filters.private)
async def delete_specific_message_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    if message.from_user.id != OWNER_ID:
        await send_and_auto_delete_reply(message, text="𝗢𝗼𝗽𝘀! 𝗦𝗼𝗿𝗿𝘆 𝘀𝘄𝗲𝗲𝘁𝗶𝗲, 𝘁𝗵𝗶𝘀 𝗰𝗼𝗺𝗺𝗮𝗻𝗱 𝗶𝘀 𝗼𝗻𝗹𝘆 𝗳𝗼𝗿 𝗺𝘆 𝗯𝗼𝘀𝘀. 🤷‍♀️", parse_mode=ParseMode.MARKDOWN)
        return

    if len(message.command) < 2:
        await send_and_auto_delete_reply(message, text="𝗪𝗵𝗶𝗰𝗵 **𝘁𝗲𝘅𝘁 𝗺𝗲𝘀𝘀𝗮𝗴𝗲** 𝘁𝗼 𝗱𝗲𝗹𝗲𝘁𝗲, 𝗽𝗹𝗲𝗮𝘀𝗲 𝘁𝗲𝗹𝗹 𝗺𝗲! 𝗟𝗶𝗸𝗲: `/deletemessage hello` 𝗼𝗿 `/deletemessage '𝗵𝗼𝘄 𝗮𝗿𝗲 𝘆𝗼𝘂'` 👻", parse_mode=ParseMode.MARKDOWN)
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
        await send_and_auto_delete_reply(message, text=f"𝗔𝘀 𝘆𝗼𝘂 𝗰𝗼𝗺𝗺𝗮𝗻𝗱, 𝗺𝘆 𝗺𝗮𝘀𝘁𝗲𝗿! 🧞‍♀️ 𝗜 𝗳𝗼𝘂𝗻𝗱 𝗮𝗻𝗱 𝗱𝗲𝗹𝗲𝘁𝗲𝗱 **{deleted_count}** **𝘁𝗲𝘅𝘁 𝗺𝗲𝘀𝘀𝗮𝗴𝗲𝘀** 𝗿𝗲𝗹𝗮𝘁𝗲𝗱 𝘁𝗼 '{search_query}'. 𝗡𝗼𝘄 𝘁𝗵𝗮𝘁 𝗶𝘀𝗻'𝘁 𝗽𝗮𝗿𝘁 𝗼𝗳 𝗵𝗶𝘀𝘁𝗼𝗿𝘆 𝗮𝗻𝘆𝗺𝗼𝗿𝗲! ✨", parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Deleted {deleted_count} text messages with query: '{search_query}'.")
    else:
        await send_and_auto_delete_reply(message, text="𝗨𝗺𝗺, 𝗜 𝗱𝗶𝗱𝗻't 𝗳𝗶𝗻𝗱 𝗮𝗻𝘆 **𝘁𝗲𝘅𝘁 𝗺𝗲𝘀𝘀𝗮𝗴𝗲** 𝗶𝗻 𝗺𝘆 𝗱𝗮𝘁𝗮𝗯𝗮𝘀𝗲 𝘄𝗶𝘁𝗵 𝘆𝗼𝘂𝗿 𝗾𝘂𝗲𝗿𝘆. 𝗖𝗵𝗲𝗰𝗸 𝘁𝗵𝗲 𝘀𝗽𝗲𝗹𝗹𝗶𝗻𝗴? 🤔", parse_mode=ParseMode.MARKDOWN)

    # FIX: store_message removed
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)


@app.on_message(filters.command("delsticker") & filters.private)
async def delete_specific_sticker_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    if message.from_user.id != OWNER_ID:
        await send_and_auto_delete_reply(message, text="𝗢𝗼𝗽𝘀! 𝗦𝗼𝗿𝗿𝘆 𝘀𝘄𝗲𝗲𝘁𝗶𝗲, 𝘁𝗵𝗶𝘀 𝗰𝗼𝗺𝗺𝗮𝗻𝗱 𝗶𝘀 𝗼𝗻𝗹𝘆 𝗳𝗼𝗿 𝗺𝘆 𝗯𝗼𝘀𝘀. 🤷‍♀️", parse_mode=ParseMode.MARKDOWN)
        return

    if len(message.command) < 2:
        await send_and_auto_delete_reply(message, text="𝗛𝗼𝘄 𝗺𝗮𝗻𝘆 **𝘀𝘁𝗶𝗰𝗸𝗲𝗿𝘀** 𝘁𝗼 𝗱𝗲𝗹𝗲𝘁𝗲? 𝗧𝗲𝗹𝗹 𝗺𝗲 𝘁𝗵𝗲 𝗽𝗲𝗿𝗰𝗲𝗻𝘁𝗮𝗴𝗲, 𝗹𝗶𝗸𝗲: `/delsticker 10%` 𝗼𝗿 `delsticker 20%` 𝗼𝗿 `delsticker 40%`! 🧹", parse_mode=ParseMode.MARKDOWN)
        return

    percentage_str = message.command[1].strip('%')
    try:
        percentage = int(percentage_str)
        if not (1 <= percentage <= 100):
            await send_and_auto_delete_reply(message, text="𝗣𝗲𝗿𝗰𝗲𝗻𝘁𝗮𝗴𝗲 𝘀𝗵𝗼𝘂𝗹𝗱 𝗯𝗲 𝗯𝗲𝘁𝘄𝗲𝗲𝗻 1 𝗮𝗻𝗱 100. 𝗕𝗲 𝗮 𝗹𝗶𝘁𝘁𝗹𝗲 𝗰𝗮𝗿𝗲𝗳𝘂𝗹! 🤔", parse_mode=ParseMode.MARKDOWN)
            return
    except ValueError:
        await send_and_auto_delete_reply(message, text="𝗜𝗻𝘃𝗮𝗹𝗶𝗱 𝗽𝗲𝗿𝗰𝗲𝗻𝘁𝗮𝗴𝗲 𝗳𝗼𝗿𝗺𝗮𝘁. 𝗣𝗲𝗿𝗰𝗲𝗻𝘁𝗮𝗴𝗲 𝘀𝗵𝗼𝘂𝗹𝗱 𝗯𝗲 𝗶𝗻 𝗻𝘂𝗺𝗯𝗲𝗿𝘀, 𝗹𝗶𝗸𝗲 `10` 𝗼𝗿 `50`. 𝗧𝗿𝘆 𝗮𝗴𝗮𝗶𝗻!💖", parse_mode=ParseMode.MARKDOWN)
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
        await send_and_auto_delete_reply(message, text=f"𝗔𝘀 𝘆𝗼𝘂 𝗰𝗼𝗺𝗺𝗮𝗻𝗱, 𝗺𝘆 𝗺𝗮𝘀𝘁𝗲𝗿! 🧞‍♀️ 𝗜 𝗳𝗼𝘂𝗻𝗱 𝗮𝗻𝗱 𝗱𝗲𝗹𝗲𝘁𝗲𝗱 **{percentage}%** 𝘀𝘁𝗶𝗰𝗸𝗲𝗿𝘀. 𝗔 𝘁𝗼𝘁𝗮𝗹 𝗼𝗳 **{deleted_count}** 𝘀𝘁𝗶𝗰𝗸𝗲𝗿𝘀 𝗿𝗲𝗺𝗼𝘃𝗲𝗱. 𝗡𝗼𝘄 𝘁𝗵𝗮𝘁 𝗶𝘀𝗻'𝘁 𝗽𝗮𝗿𝘁 𝗼𝗳 𝗵𝗶𝘀𝘁𝗼𝗿𝘆 𝗮𝗻𝘆𝗺𝗼𝗿𝗲! ✨", parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Deleted {deleted_count} stickers based on {percentage}% request.")
    else:
        await send_and_auto_delete_reply(message, text="𝗨𝗺𝗺, 𝗜 𝗱𝗶𝗱𝗻't 𝗳𝗶𝗻𝗱 𝗮𝗻𝘆 **𝘀𝘁𝗶𝗰𝗸𝗲𝗿** 𝗶𝗻 𝗺𝘆 𝗱𝗮𝘁𝗮𝗯𝗮𝘀𝗲. 𝗘𝗶𝘁𝗵𝗲𝗿 𝘁𝗵𝗲𝗿𝗲 𝗮𝗿𝗲 𝗻𝗼 𝘀𝘁𝗶𝗰𝗸𝗲𝗿𝘀, 𝗼𝗿 𝘁𝗵𝗲 𝗽𝗲𝗿𝗰𝗲𝗻𝘁𝗮𝗴𝗲 𝗶𝘀 𝘁𝗼𝗼 𝗹𝗼𝘄! 🤔", parse_mode=ParseMode.MARKDOWN)

    # FIX: store_message removed
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)


@app.on_message(filters.command("clearearning") & filters.private)
async def clear_earning_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    if message.from_user.id != OWNER_ID:
        await send_and_auto_delete_reply(message, text="𝗦𝗼𝗿𝗿𝘆 𝗱𝗮𝗿𝗹𝗶𝗻𝗴! 𝗧𝗵𝗶𝘀 𝗰𝗼𝗺𝗺𝗮𝗻𝗱 𝗶𝘀 𝗼𝗻𝗹𝘆 𝗳𝗼𝗿 𝗺𝘆 𝗯𝗼𝘀𝘀. 🚫", parse_mode=ParseMode.MARKDOWN)
        return

    await reset_monthly_earnings_manual()
    await send_and_auto_delete_reply(message, text="💰 **𝗘𝗮𝗿𝗻𝗶𝗻𝗴 𝗱𝗮𝘁𝗮 𝘀𝘂𝗰𝗰𝗲𝘀𝘀𝗳𝘂𝗹𝗹𝘆 𝗰𝗹𝗲𝗮𝗿𝗲𝗱!** 𝗡𝗼𝘄 𝗲𝘃𝗲𝗿𝘆𝗼𝗻𝗲 𝘄𝗶𝗹𝗹 𝘀𝘁𝗮𝗿𝘁 𝗳𝗿𝗼𝗺 𝘇𝗲𝗿𝗼 𝗮𝗴𝗮𝗶𝗻! 😉", parse_mode=ParseMode.MARKDOWN)
    logger.info(f"Owner {message.from_user.id} manually triggered earning data reset.")

    # FIX: store_message removed
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)


@app.on_message(filters.command("restart") & filters.private)
async def restart_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    if message.from_user.id != OWNER_ID:
        await send_and_auto_delete_reply(message, text="𝗦𝗼𝗿𝗿𝘆, 𝗱𝗮𝗿𝗹𝗶𝗻𝗴! 𝗧𝗵𝗶𝘀 𝗰𝗼𝗺𝗺𝗮𝗻𝗱 𝗶𝘀 𝗼𝗻𝗹𝘆 𝗳𝗼𝗿 𝗺𝘆 𝗯𝗼𝘀𝘀. 🚫", parse_mode=ParseMode.MARKDOWN)
        return

    await send_and_auto_delete_reply(message, text="𝗢𝗸𝗮𝘆, 𝗱𝗮𝗿𝗹𝗶𝗻𝗴! 𝗜'𝗺 𝘁𝗮𝗸𝗶𝗻𝗴 𝗮 𝘀𝗵𝗼𝗿𝘁 𝗻𝗮𝗽 𝗻𝗼𝘄 𝗮𝗻𝗱 𝘁𝗵𝗲𝗻 𝗜'𝗹𝗹 𝗯𝗲 𝗯𝗮𝗰𝗸, 𝗰𝗼𝗺𝗽𝗹𝗲𝘁𝗲𝗹𝘆 𝗳𝗿𝗲𝘀𝗵 𝗮𝗻𝗱 𝗲𝗻𝗲𝗿𝗴𝗲𝘁𝗶𝗰! 𝗣𝗹𝗲𝗮𝘀𝗲 𝘄𝗮𝗶𝘁 𝗮 𝗹𝗶𝘁𝘁𝗹𝗲, 𝗼𝗸𝗮𝘆? ✨", parse_mode=ParseMode.MARKDOWN)
    logger.info("Bot is restarting...")
    import os
    import sys
    # FIX: store_message removed
    await asyncio.sleep(0.5)
    os.execl(sys.executable, sys.executable, *sys.argv)

@app.on_message(filters.command("clearall") & filters.private)
async def clear_all_dbs_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    if message.from_user.id != OWNER_ID:
        await send_and_auto_delete_reply(message, text="𝗧𝗵𝗶𝘀 𝗰𝗼𝗺𝗺𝗮𝗻𝗱 𝗶𝘀 𝗼𝗻𝗹𝘆 𝗳𝗼𝗿 𝗺𝘆 𝗯𝗼𝘀𝘀. 🚫", parse_mode=ParseMode.MARKDOWN)
        return

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Yᴇꜱ, Dᴇʟᴇ𝘁𝗲 ⚠️", callback_data='confirm_clearall_dbs'),
                InlineKeyboardButton("Nᴏ, Kᴇᴇᴘ I𝘁 ✅", callback_data='cancel_clearall_dbs')
            ]
        ]
    )

    await send_and_auto_delete_reply(
        message,
        text="⚠️ **𝗪𝗔𝗥𝗡𝗜𝗡𝗚:** 𝗔𝗿𝗲 𝘆𝗼𝘂 𝘀𝘂𝗿𝗲 𝘆𝗼𝘂 𝘄𝗮𝗻𝘁 𝘁𝗼 𝗱𝗲𝗹𝗲𝘁𝗲 **𝗮𝗹𝗹 𝗱𝗮𝘁𝗮** 𝗳𝗿𝗼𝗺 𝘆𝗼𝘂𝗿 𝗠𝗼𝗻𝗴𝗼𝗗𝗕 𝗗𝗮𝘁𝗮𝗯𝗮𝘀𝗲𝘀 (𝗠𝗲𝘀𝘀𝗮𝗴𝗲𝘀, 𝗕𝘂𝘁𝘁𝗼𝗻𝘀, 𝗧𝗿𝗮𝗰𝗸𝗶𝗻𝗴)?\n\n"
             "𝗧𝗵𝗶𝘀 𝗮𝗰𝘁𝗶𝗼𝗻 𝗶𝘀 **𝗶𝗿𝗿𝗲𝘃𝗲𝗿𝘀𝗶𝗯𝗹𝗲** 𝗮𝗻𝗱 𝗮𝗹𝗹 𝘆𝗼𝘂𝗿 𝗱𝗮𝘁𝗮 𝘄𝗶𝗹𝗹 𝗯𝗲 𝗹𝗼𝘀𝘁 𝗳𝗼𝗿𝗲𝘃𝗲𝗿.\n\n"
             "𝗖𝗵𝗼𝗼𝘀𝗲 𝗰𝗮𝗿𝗲𝗳𝘂𝗹𝗹𝘆!",
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )
    logger.info(f"Owner {message.from_user.id} initiated /clearall command. Waiting for confirmation.")
    # FIX: store_message removed

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
                await send_and_auto_delete_reply(message, text="𝗬𝗼𝘂 𝗰𝗮𝗻't 𝗱𝗲𝗹𝗲𝘁𝗲 𝗺𝘆 𝗱𝗮𝘁𝗮, 𝗯𝗼𝘀𝘀! 😅", parse_mode=ParseMode.MARKDOWN)
                return
        except ValueError:
            await send_and_auto_delete_reply(message, text="𝗪𝗿𝗼𝗻𝗴 𝗨𝘀𝗲𝗿 𝗜𝗗 𝗳𝗼𝗿𝗺𝗮𝘁. 𝗣𝗹𝗲𝗮𝘀𝗲 𝗽𝗿𝗼𝘃𝗶𝗱𝗲 𝗮 𝘃𝗮𝗹𝗶𝗱 𝗻𝘂𝗺𝗲𝗿𝗶𝗰 𝗜𝗗.", parse_mode=ParseMode.MARKDOWN)
            return
    elif len(message.command) > 1 and message.from_user.id != OWNER_ID:
        await send_and_auto_delete_reply(message, text="𝗬𝗼𝘂 𝗮𝗿𝗲 𝗻𝗼𝘁 𝗮𝘂𝘁𝗵𝗼𝗿𝗶𝘇𝗲𝗱 𝘁𝗼 𝘂𝘀𝗲 𝘁𝗵𝗶𝘀 𝗰𝗼𝗺𝗺𝗮𝗻𝗱 𝘁𝗵𝗶𝘀 𝘄𝗮𝘆. 𝗧𝗵𝗶𝘀 𝗳𝗲𝗮𝘁𝘂𝗿𝗲 𝗶𝘀 𝗼𝗻𝗹𝘆 𝗳𝗼𝗿 𝗺𝘆 𝗯𝗼𝘀𝘀.", parse_mode=ParseMode.MARKDOWN)
        return
    else:
        target_user_id = message.from_user.id

    if not target_user_id:
        await send_and_auto_delete_reply(message, text="𝗳𝗜 𝗰𝗮𝗻't 𝗳𝗶𝗴𝘂𝗿𝗲 𝗼𝘂𝘁 𝘄𝗵𝗼𝘀𝗲 𝗱𝗮𝘁𝗮 𝘁𝗼 𝗱𝗲𝗹𝗲𝘁𝗲. 😕", parse_mode=ParseMode.MARKDOWN)
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
                await send_and_auto_delete_reply(message, text=f"𝗪𝗼𝘄! ✨ 𝗜 𝗵𝗮𝘃𝗲 𝗱𝗲𝗹𝗲𝘁𝗲𝗱 𝘆𝗼𝘂𝗿 `{deleted_messages_count}` 𝗰𝗼𝗻𝘃𝗲𝗿𝘀𝗮𝘁𝗶𝗼𝗻 𝗺𝗲𝘀𝘀𝗮𝗴𝗲𝘀 𝗮𝗻𝗱 𝗲𝗮𝗿𝗻𝗶𝗻𝗴 𝗱𝗮𝘁𝗮. 𝗬𝗼𝘂 𝗮𝗿𝗲 𝗰𝗼𝗺𝗽𝗹𝗲𝘁𝗲𝗹𝘆 𝗳𝗿𝗲𝘀𝗵 𝗻𝗼𝘄! 😊", parse_mode=ParseMode.MARKDOWN)
                logger.info(f"User {target_user_id} successfully cleared their data.")
            else:
                await send_and_auto_delete_reply(message, text=f"𝗕𝗼𝘀𝘀's 𝗼𝗿𝗱𝗲𝗿! 👑 𝗜 𝗵𝗮𝘃𝗲 𝗱𝗲𝗹𝗲𝘁𝗲𝗱 `{deleted_messages_count}` 𝗰𝗼𝗻𝘃𝗲𝗿𝘀𝗮𝘁𝗶𝗼𝗻 𝗺𝗲𝘀𝘀𝗮𝗴𝗲𝘀 𝗮𝗻𝗱 𝗲𝗮𝗿𝗻𝗶𝗻𝗴 𝗱𝗮𝘁𝗮 𝗳𝗼𝗿 𝘂𝘀𝗲𝗿 `{target_user_id}`. 😉", parse_mode=ParseMode.MARKDOWN)
                logger.info(f"Owner {message.from_user.id} cleared data for user {target_user_id}.")
        else:
            if target_user_id == message.from_user.id:
                await send_and_auto_delete_reply(message, text="𝗬𝗼𝘂 𝗱𝗼𝗻't 𝗵𝗮𝘃𝗲 𝗮𝗻𝘆 𝗱𝗮𝘁𝗮 𝘀𝘁𝗼𝗿𝗲𝗱 𝘁𝗼 𝗱𝗲𝗹𝗲𝘁𝗲. 𝗠𝘆 𝗱𝗮𝘁𝗮𝗯𝗮𝘀𝗲 𝗶𝘀 𝗰𝗼𝗺𝗽𝗹𝗲𝘁𝗲𝗹𝘆 𝗲𝗺𝗽𝘁𝘆 𝗳𝗼𝗿 𝘆𝗼𝘂! 🤷‍♀️", parse_mode=ParseMode.MARKDOWN)
            else:
                await send_and_auto_delete_reply(message, text=f"𝗡𝗼 𝗱𝗮𝘁𝗮 𝗳𝗼𝘂𝗻𝗱 𝗳𝗼𝗿 𝘂𝘀𝗲𝗿 `{target_user_id}` 𝘁𝗼 𝗱𝗲𝗹𝗲𝘁𝗲.", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await send_and_auto_delete_reply(message, text=f"𝗦𝗼𝗺𝗲𝘁𝗵𝗶𝗻𝗴 𝘄𝗲𝗻𝘁 𝘄𝗿𝗼𝗻𝗴 𝘄𝗵𝗶𝗹𝗲 𝗱𝗲𝗹𝗲𝘁𝗶𝗻𝗴 𝗱𝗮𝘁𝗮: {e}. 𝗢𝗵 𝗻𝗼! 😱", parse_mode=ParseMode.MARKDOWN)
        logger.error(f"Error clearing data for user {target_user_id}: {e}")
    
    # FIX: store_message removed
    
    # FIX: Corrected update_user_info arguments
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)


# -----------------------------------------------------
# GROUP COMMANDS
# -----------------------------------------------------

@app.on_message(filters.command("start") & filters.group)
async def start_group_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    user_name = message.from_user.first_name if message.from_user else "Friend"
    welcome_message = (
        f"🌟 𝗛𝗲𝘆 **{user_name}** 𝗱𝗲𝗮𝗿! 𝗪𝗲𝗹𝗰𝗼𝗺𝗲! 🌟\n\n"
        "𝗜'𝗺 𝗿𝗲𝗮𝗱𝘆 𝘁𝗼 𝗹𝗶𝘀𝘁𝗲𝗻 𝗮𝗻𝗱 𝗹𝗲𝗮𝗿𝗻 𝗮𝗹𝗹 𝘁𝗵𝗲 𝗴𝗿𝗼𝘂𝗽 𝗰𝗼𝗻𝘃𝗲𝗿𝘀𝗮𝘁𝗶𝗼𝗻𝘀!\n"
        "𝗨𝘀𝗲 𝘁𝗵𝗲 `/settings` 𝗰𝗼𝗺𝗺𝗮𝗻𝗱 𝘁𝗼 𝗺𝗮𝗻𝗮𝗴𝗲 𝗮𝗹𝗹 𝗴𝗿𝗼𝘂𝗽 𝘀𝗲𝘁𝘁𝗶𝗻𝗴𝘀."
    )
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✙ꫝᴅᴅ мє ɪη уσυʀ ɢʀσυρ✙", url=f"https://t.me/{client.me.username}?startgroup=true")],
            [
                InlineKeyboardButton("📣 Uᴘᴅᴀᴛᴇꜱ Cʜᴀɴɴᴇʟ", url=f"https://t.me/{UPDATE_CHANNEL_USERNAME}"),
                InlineKeyboardButton("❓ Sᴜᴘᴘᴏʀᴛ Gʀᴏᴜᴘ", url="https://t.me/aschat_group")
            ],
            [
                InlineKeyboardButton("⚙️ Gʀᴏᴜᴘ Sᴇᴛᴛɪɴɢꜱ 🛠️", callback_data="open_group_settings"), 
                InlineKeyboardButton("💰 Eᴀʀɴɪɴɢ Lᴇ𝗮𝗱𝗲𝗿𝗯𝗼𝗮𝗿𝗱", callback_data="show_earning_leaderboard")
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
    # FIX: store_message removed
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        logger.info(f"Attempting to update group info from /start command in chat {message.chat.id}.")
        await update_group_info(message.chat.id, message.chat.title, message.chat.username)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)
    logger.info(f"Group start command processed in chat {message.chat.id}.")


# --- NEW: AI MODE COMMAND ---
@app.on_message(filters.command("setaimode") & filters.group)
async def set_ai_mode_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    # 1. Check for Admin/Owner status
    if not await is_admin_or_owner(client, message.chat.id, message.from_user.id):
        await send_and_auto_delete_reply(message, text="⚠️ 𝗬𝗲 𝗰𝗼𝗺𝗺𝗮𝗻𝗱 𝘀𝗶𝗿𝗳 𝗚𝗿𝗼𝘂𝗽 𝗔𝗱𝗺𝗶𝗻/𝗢𝘄𝗻𝗲𝗿 𝗵𝗶 𝘂𝘀𝗲 𝗸𝗮𝗿 𝘀𝗮𝗸𝘁𝗲 𝗵𝗮𝗶𝗻! 🤷‍♀️", parse_mode=ParseMode.MARKDOWN)
        return

    # 2. Fetch current AI mode
    current_status_doc = group_tracking_collection.find_one({"_id": message.chat.id})
    current_ai_mode = current_status_doc.get("ai_mode", "off") if current_status_doc else "off"
    
    # 3. Define AI Modes (Hindi/Hinglish Friendly)
    ai_modes = {
        "off": "❌ Oғғ",
        "realgirl": "👧 Rᴇᴀʟ Gɪʀʟ",
        "romanticgirl": "💖 Rᴏᴍᴀɴᴛɪᴄ Gɪʀʟ",
        "motivationgirl": "💪 Mᴏᴛɪᴠᴀᴛɪᴏɴ Gɪʀʟ",
        "studygirl": "📚 Sᴛᴜᴅʏ Gɪʀʟ",
        "gemini": "✨ Gᴇᴍɪɴɪ (Sᴜᴘᴇʀ AI)", # New mode as requested
    }
    
    # 4. Create Buttons
    keyboard_buttons = []
    current_row = []
    
    # Off/Default Button
    status_off = "✅ " if current_ai_mode == "off" else ""
    keyboard_buttons.append([InlineKeyboardButton(f"{status_off}❌ AI Mᴏᴅᴇ Oғғ", callback_data="set_ai_mode_off")])

    # Dynamic Mode Buttons
    for mode_key, mode_name in ai_modes.items():
        if mode_key != "off":
            status = "✅ " if current_ai_mode == mode_key else ""
            button = InlineKeyboardButton(f"{status}{mode_name}", callback_data=f"set_ai_mode_{mode_key}")
            current_row.append(button)
            if len(current_row) == 2:
                keyboard_buttons.append(current_row)
                current_row = []
    
    if current_row:
        keyboard_buttons.append(current_row)

    # Close Button (UI Suggestion Fix: Changed to Back to Settings)
    keyboard_buttons.append([InlineKeyboardButton("🔙 Sᴇᴛᴛɪɴɢꜱ Mᴇɴᴜ", callback_data="settings_back_to_main")]) # 🟢 FIX: Back to Main Setting
    
    keyboard = InlineKeyboardMarkup(keyboard_buttons)

    # 5. Send Message
    mode_display = ai_modes.get(current_ai_mode, "❌ Oғғ")
    settings_message = (
        f"👑 **AI Mᴏᴅᴇ Sᴇᴛᴛɪɴɢꜱ 👑**\n\n"
        "𝗛𝗲𝗹𝗹𝗼 𝗕𝗼𝘀𝘀, 𝘆𝗲𝗵𝗮𝗻 𝘀𝗲 𝗮𝗽𝗽𝗮𝗻𝗮 **AI 𝗽𝗲𝗿𝘀𝗼𝗻𝗮𝗹𝗶𝘁𝘆** 𝘀𝗲𝘁 𝗸𝗮𝗿𝗼.\n"
        "𝗕𝗼𝘁 𝘂𝘀 𝗵𝗶 𝗮𝗻𝗱𝗮𝗮𝘇 𝗺𝗮𝗶𝗻, 𝗯𝗶𝗸𝘂𝗹 𝗿𝗲𝗮𝗹 𝗹𝗮𝗱𝗸𝗶 𝗷𝗮𝗶𝘀𝗲, 𝗯𝗮𝗮𝘁 𝗸𝗮𝗿𝗲𝗴𝗶! 🤩\n\n"
        f"**Cᴜʀʀ𝗲𝗻𝘁 AI Mᴏ𝗱𝗲:** **{mode_display}**"
    )

    await send_and_auto_delete_reply(
        message,
        text=settings_message,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

    # FIX: store_message removed
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await update_group_info(message.chat.id, message.chat.title, message.chat.username)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)
    logger.info(f"Group /setaimode command processed in chat {message.chat.id} by admin {message.from_user.id}.")
# --- END NEW AI MODE COMMAND ---


@app.on_message(filters.command("settings") & filters.group)
async def open_settings_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    # 1. Check for Admin/Owner status
    if not await is_admin_or_owner(client, message.chat.id, message.from_user.id):
        await send_and_auto_delete_reply(message, text="𝗧𝗵𝗶𝘀 𝗰𝗼𝗺𝗺𝗮𝗻𝗱 𝗰𝗮𝗻 𝗼𝗻𝗹𝘆 𝗯𝗲 𝘂𝘀𝗲𝗱 𝗯𝘆 𝗺𝘆 𝗯𝗼𝘀𝘀 (𝗔𝗱𝗺𝗶𝗻/𝗢𝘄𝗻𝗲𝗿)! 🤷‍♀️", parse_mode=ParseMode.MARKDOWN)
        return

    # 2. Fetch current settings and default punishment
    current_status_doc = group_tracking_collection.find_one({"_id": message.chat.id})
    
    # Default values if not found
    bot_enabled = current_status_doc.get("bot_enabled", True) if current_status_doc else True
    linkdel_enabled = current_status_doc.get("linkdel_enabled", False) if current_status_doc else False
    biolinkdel_enabled = current_status_doc.get("biolinkdel_enabled", False) if current_status_doc else False
    usernamedel_enabled = current_status_doc.get("usernamedel_enabled", False) if current_status_doc else False
    ai_mode = current_status_doc.get("ai_mode", "off") if current_status_doc else "off" # New AI Mode
    
    punishment = current_status_doc.get("default_punishment", "delete") if current_status_doc else "delete"
    
    # Status texts (Translated and styled)
    bot_status = "✅ O𝙽" if bot_enabled else "❌ O𝙵𝙵"
    link_status = "✅ O𝙽" if linkdel_enabled else "❌ O𝙵𝙵"
    biolink_status = "✅ O𝙽" if biolinkdel_enabled else "❌ O𝙵𝙵"
    username_status = "✅ O𝙽" if usernamedel_enabled else "❌ O𝙵𝙵"
    
    # Punishment text (Translated and styled)
    punishment_map = {
        "delete": "🗑️ Dᴇʟᴇᴛᴇ Mᴇꜱꜱᴀɢᴇ",
        "mute": "🔇 Mᴜᴛᴇ Uꜱᴇʀ",
        "warn": "⚠️ Wᴀʀɴ Uꜱᴇʀ",
        "ban": "⛔️ Bᴀɴ Uꜱᴇʀ"
    }
    punishment_text = punishment_map.get(punishment, "🗑️ Dᴇʟᴇᴛᴇ Mᴇꜱꜱᴀɢᴇ")

    # AI Mode Text
    ai_modes_display = {
        "off": "❌ Oғғ", "realgirl": "👧 Rᴇᴀʟ", "romanticgirl": "💖 Rᴏᴍ", 
        "motivationgirl": "💪 Mᴏᴛɪ", "studygirl": "📚 Sᴛᴜᴅʏ", "gemini": "✨ Gᴇᴍɪɴɪ"
    }
    ai_mode_text = ai_modes_display.get(ai_mode, "❌ Oғғ")


    # 3. Create the Main Settings Keyboard (Styled Buttons)
    keyboard = InlineKeyboardMarkup(
        [
            # Module Toggles
            [
                InlineKeyboardButton(f"🤖 Bᴏᴛ Cʜᴀᴛᴛɪɴɢ: {bot_status}", callback_data="toggle_setting_bot_enabled"),
            ],
            [
                InlineKeyboardButton(f"🔗 Lɪɴᴋ Dᴇ𝗹𝗲𝘁𝗲: {link_status}", callback_data="toggle_setting_linkdel_enabled"),
            ],
            [
                InlineKeyboardButton(f"👤 Bɪᴏ Lɪɴᴋ D𝗲𝗹𝗲𝘁𝗲: {biolink_status}", callback_data="toggle_setting_biolinkdel_enabled"),
            ],
            [
                InlineKeyboardButton(f"🗣️ @Uꜱᴇ𝗿𝗻𝗮𝗺𝗲 D𝗲𝗹𝗲𝘁𝗲: {username_status}", callback_data="toggle_setting_usernamedel_enabled"),
            ],
            # NEW AI MODE BUTTON
            [
                InlineKeyboardButton(f"✨ AI Mᴏᴅᴇ: {ai_mode_text}", callback_data="open_ai_mode_settings"),
            ],
            # Punishment and Biolink Exception
            [
                InlineKeyboardButton(f"🔨 Dᴇ𝗳𝗮𝘂𝗹𝘁 Pᴜ𝗻𝗶𝘀𝗵𝗺𝗲𝗻𝘁: {punishment_text}", callback_data="open_punishment_settings"),
            ],
            [
                 InlineKeyboardButton("👤 Bɪ𝗼 L𝗶𝗻𝗸 Exᴄᴇᴘᴛɪᴏ𝗻ꜱ 📝", callback_data="open_biolink_exceptions")
            ],
            # Close Button
            [
                InlineKeyboardButton("❌ Cʟ𝗼𝘀𝗲 S𝗲𝘁𝘁𝗶𝗻𝗴ꜱ", callback_data="close_settings")
            ]
        ]
    )

    # 4. Send the Settings Message (Translated and styled)
    settings_message = (
        f"⚙️ **𝗚𝗿𝗼𝘂𝗽 𝗦𝗲𝘁𝘁𝗶𝗻𝗴𝘀: {message.chat.title}** 🛠️\n\n"
        "𝗛𝗲𝗹𝗹𝗼, 𝗕𝗼𝘀𝘀! 𝗬𝗼𝘂 𝗰𝗮𝗻 𝗰𝗼𝗻𝘁𝗿𝗼𝗹 𝘁𝗵𝗲 𝗴𝗿𝗼𝘂𝗽 𝗿𝘂𝗹𝗲𝘀 𝗮𝗻𝗱 𝗯𝗼𝘁 𝗳𝘂𝗻𝗰𝘁𝗶𝗼𝗻𝘀 𝗳𝗿𝗼𝗺 𝘁𝗵𝗲 𝗯𝘂𝘁𝘁𝗼𝗻𝘀 𝗯𝗲𝗹𝗼𝘄.\n"
        "**AI Mᴏᴅᴇ:** Bᴏᴛ ᴋɪ ᴘᴇʀsᴏɴᴀʟɪᴛʏ ᴀᴜʀ ᴊᴀ𝘄𝗮𝗯 ᴅᴇɴᴇ ᴋᴀ 𝘁𝗮𝗿𝗶𝗸𝗮 𝗶𝘀 𝘀𝗲 𝘀𝗲𝘁 𝗵𝗼𝗴𝗮. **Cᴜʀʀ𝗲𝗻𝘁: {ai_mode_text}**\n\n"
        "𝗨𝘀𝗲𝗿𝘀 𝘄𝗵𝗼 𝗯𝗿𝗲𝗮𝗸 𝘆𝗼𝘂𝗿 𝗳𝗶𝗹𝘁𝗲𝗿 𝘀𝗲𝘁𝘁𝗶𝗻𝗴𝘀 𝘄𝗶𝗹𝗹 𝗿𝗲𝗰𝗲𝗶𝘃𝗲 𝘁𝗵𝗲 **𝗗𝗲𝗳𝗮𝘂𝗹𝘁 𝗣𝘂𝗻𝗶𝘀𝗵𝗺𝗲𝗻𝘁**.\n\n"
        f"**𝗗𝗲𝗳𝗮𝘂𝗹𝘁 𝗣𝘂𝗻𝗶𝘀𝗵𝗺𝗲𝗻𝘁:** {punishment_text}\n"
        "__𝗖𝗵𝗼𝗼𝘀𝗲 𝘄𝗵𝗮𝘁 𝗽𝘂𝗻𝗶𝘀𝗵𝗺𝗲𝗻𝘁 𝘁𝗼 𝗴𝗶𝘃𝗲 𝘁𝗼 𝗿𝘂𝗹𝗲-𝗯𝗿𝗲𝗮𝗸𝗲𝗿𝘀 𝗳𝗿𝗼𝗺 '𝗗𝗲𝗳𝗮𝘂𝗹𝘁 𝗣𝘂𝗻𝗶𝘀𝗵𝗺𝗲𝗻𝘁'.__"
    )

    await send_and_auto_delete_reply(
        message,
        text=settings_message.format(ai_mode_text=ai_mode_text), # .format() added for clean variable insertion
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )
    # FIX: store_message removed
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await update_group_info(message.chat.id, message.chat.title, message.chat.username)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)
    logger.info(f"Group settings command processed in chat {message.chat.id} by admin {message.from_user.id}.")
