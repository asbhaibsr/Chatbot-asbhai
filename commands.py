from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatType, ChatMemberStatus, ParseMode
from pyrogram.errors import FloodWait, UserIsBlocked, ChatWriteForbidden, PeerIdInvalid, RPCError
from datetime import datetime
import re 

# Import utilities and configurations
from config import (
    app, buttons_collection, group_tracking_collection, user_tracking_collection,
    messages_collection, owner_taught_responses_collection, conversational_learning_collection,
    biolink_exceptions_collection, earning_tracking_collection, reset_status_collection, logger,
    OWNER_ID, BOT_PHOTO_URL, UPDATE_CHANNEL_USERNAME, ASBHAI_USERNAME, ASFILTER_BOT_USERNAME, REPO_LINK
)
from utils import (
    is_on_command_cooldown, update_command_cooldown, update_group_info, update_user_info,
    get_top_earning_users, reset_monthly_earnings_manual, send_and_auto_delete_reply,
    store_message, is_admin_or_owner
)

import callbacks # <--- यह बहुत ज़रूरी लाइन है, जो callbacks.py को इम्पोर्ट करेगी
import broadcast_handler # <--- 🌟 नई ब्रॉडकास्ट फ़ाइल इम्पोर्ट की गई 🌟

# -----------------------------------------------------
# PRIVATE CHAT COMMANDS (Unchanged, /broadcast removed)
# -----------------------------------------------------

@app.on_message(filters.command("start") & filters.private)
async def start_private_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    user_name = message.from_user.first_name if message.from_user else "Dost"
    welcome_message = (
        f"🌟 𝙷𝚎𝚢 **{user_name}** 𝚍𝚎𝚊𝚛! 𝚆𝚎𝚕𝚌𝚘𝚖𝚎! 🌟\n\n"
        "𝙸'𝚖 𝚛𝚎𝚊𝚍𝚢 𝚝𝚘 𝚑𝚎𝚕𝚙 𝚢𝚘𝚞!\n"
        "𝙲𝚕𝚒𝚌𝚔 𝚝𝚑𝚎 '𝙷𝚎𝚕𝚙' 𝚋𝚞𝚝𝚝𝚘𝚗 𝚋𝚎𝚕𝚘𝚠 𝚝𝚘 𝚜𝚎𝚎 𝚊𝚕𝚕 𝚖𝚢 𝚌𝚘𝚖𝚖𝚊𝚗𝚍𝚜."
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
                InlineKeyboardButton("💰 Eᴀʀɴɪɴɢ Lᴇᴀᴅᴇʀʙᴏᴀʀᴅ", callback_data="show_earning_leaderboard")
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
    await store_message(client, message) 
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)
    logger.info(f"Private start command processed for user {message.from_user.id}. (Code by @asbhaibsr)")

@app.on_message(filters.command("topusers") & (filters.private | filters.group))
async def top_users_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    top_users = await get_top_earning_users()
    if not top_users:
        await send_and_auto_delete_reply(message, text="😢 𝙽𝚘 𝚞𝚜𝚎𝚛𝚜 𝚊𝚛𝚎 𝚘𝚗 𝚝𝚑𝚎 𝚕𝚎𝚊𝚍𝚎𝚛𝚋𝚘𝚊𝚛𝚍 𝚢𝚎𝚝! 𝙱𝚎 𝚝𝚑𝚎 𝚏𝚒𝚛𝚜𝚝 𝚋𝚢 𝚋𝚎𝚒𝚗𝚐 𝚊𝚌𝚝𝚒𝚟𝚎! ✨\n\n**Powered By:** @asbhaibsr", parse_mode=ParseMode.MARKDOWN)
        return

    earning_messages = ["👑 **𝚃𝚘𝚙 𝙰𝚌𝚝𝚒𝚟𝚎 𝚄𝚜𝚎𝚛𝚜 - ✨ 𝚅𝙸𝙿 𝙻𝚎𝚊𝚍𝚎𝚛𝚋𝚘𝚊𝚛𝚍! ✨** 👑\n\n"]
    prizes = {
        1: "💰 ₹50", 2: "💸 ₹30", 3: "🎁 ₹20",
        4: f"🎬 1 𝚆𝚎𝚎𝚔 𝙿𝚛𝚎𝚖𝚒𝚞𝚖 𝙿𝚕𝚊𝚗 𝚘𝚏 @{ASFILTER_BOT_USERNAME}",
        5: f"🎬 3 𝙳𝚊𝚢𝚜 𝙿𝚛𝚎𝚖𝚒𝚞𝚖 𝙿𝚕𝚊𝚗 𝚘𝚏 @{ASFILTER_BOT_USERNAME}"
    }

    for i, user in enumerate(top_users[:5]):
        rank = i + 1
        user_name = user.get('first_name', 'Unknown User')
        username_str = f"@{user.get('username')}" if user.get('username') else f"𝙸𝙳: `{user.get('user_id')}`"
        message_count = user.get('message_count', 0)
        prize_str = prizes.get(rank, "🏅 𝙽𝚘 𝙿𝚛𝚒𝚣𝚎")

        group_info = ""
        last_group_id = user.get('last_active_group_id')
        last_group_title = user.get('last_active_group_title', '𝚄𝚗𝚔𝚗𝚘𝚠𝚗 𝙶𝚛𝚘𝚞𝚙')

        if last_group_id:
            try:
                chat_obj = await client.get_chat(last_group_id)
                if chat_obj.type == ChatType.PRIVATE:
                    group_info = f"   • 𝙰𝚌𝚝𝚒𝚟𝚎 𝚒𝚗: **[𝙿𝚛𝚒𝚟𝚊𝚝𝚎 𝙲𝚑𝚊𝚝](tg://user?id={user.get('user_id')})**\n"
                elif chat_obj.username:
                    group_info = f"   • 𝙰𝚌𝚝𝚒𝚟𝚎 𝚒𝚗: **[{chat_obj.title}](https://t.me/{chat_obj.username})**\n"
                else:
                    try:
                        invite_link = await client.export_chat_invite_link(last_group_id)
                        group_info = f"   • 𝙰𝚌𝚝𝚒𝚟𝚎 𝚒𝚗: **[{chat_obj.title}]({invite_link})**\n"
                    except Exception:
                        group_info = f"   • 𝙰𝚌𝚝𝚒𝚟𝚎 𝚒𝚗: **{chat_obj.title}** (𝙿𝚛𝚒𝚟𝚊𝚝𝚎 𝙶𝚛𝚘𝚞𝚙)\n"
            except Exception as e:
                logger.warning(f"Could not fetch chat info for group ID {last_group_id} for leaderboard: {e}")
                group_info = f"   • 𝙰𝚌𝚝𝚒𝚟𝚎 𝚒𝚗: **{last_group_title}** (𝙸𝚗𝚏𝚘 𝙽𝚘𝚝 𝙰𝚟𝚊𝚒𝚕𝚊𝚋𝚕𝚎)\n"
        else:
            group_info = "   • 𝙰𝚌𝚝𝚒𝚟𝚎 𝚒𝚗: **𝙽𝚘 𝙶𝚛𝚘𝚞𝚙 𝙰𝚌𝚝𝚒𝚟𝚒𝚝𝚢**\n"

        earning_messages.append(
            f"**{rank}.** 🌟 **{user_name}** ({username_str}) 🌟\n"
            f"   • 𝚃𝚘𝚝𝚊𝚕 𝙼𝚎𝚜𝚜𝚊𝚐𝚎𝚜: **{message_count} 💬**\n"
            f"   • 𝙿𝚘𝚝𝚎𝚗𝚝𝚒𝚊𝚕 𝙿𝚛𝚒𝚣𝚎: **{prize_str}**\n"
            f"{group_info}"
        )
    
    earning_messages.append(
        "\n_𝚃𝚑𝚒𝚜 𝚜𝚢𝚜𝚝𝚎𝚖 𝚛𝚎𝚜𝚎𝚝𝚜 𝚘𝚗 𝚝𝚑𝚎 𝚏𝚒𝚛𝚜𝚝 𝚘𝚏 𝚎𝚟𝚎𝚛𝚢 𝚖𝚘𝚗𝚝𝚑!_\n"
        "_𝚄𝚜𝚎 `/help` 𝚝𝚘 𝚔𝚗𝚘𝚠 𝚝𝚑𝚎 𝙶𝚛𝚘𝚞𝚙 𝚛𝚞𝚕𝚎𝚜._"
    )
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("💰 Wɪᴛʜᴅʀᴀᴡ", url=f"https://t.me/{ASBHAI_USERNAME}"),
                InlineKeyboardButton("💰 Eᴀʀ𝚗ɪ𝚗g Rᴜʟᴇꜱ", callback_data="show_earning_rules")
            ]
        ]
    )
    await send_and_auto_delete_reply(message, text="\n".join(earning_messages), reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
    await store_message(message)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)
    logger.info(f"Top users command processed for user {message.from_user.id} in chat {message.chat.id}. (Code by @asbhaibsr)")


# --------------------------------------------------------------------------------------
# NOTE: /broadcast command has been completely removed and is now in broadcast_handler.py
# --------------------------------------------------------------------------------------


@app.on_message(filters.command("stats") & filters.private)
async def stats_private_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    if len(message.command) < 2 or message.command[1].lower() != "check":
        await send_and_auto_delete_reply(message, text="𝚄𝚖𝚖, 𝚝𝚘 𝚌𝚑𝚎𝚌𝚔 𝚜𝚝𝚊𝚝𝚜, 𝚙𝚕𝚎𝚊𝚜𝚎 𝚝𝚢𝚙𝚎 𝚌𝚘𝚛𝚛𝚎𝚌𝚝𝚕𝚢! 𝙻𝚒𝚔𝚎 𝚝𝚑𝚒𝚜: `/stats check`. 😊 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return

    total_messages = messages_collection.count_documents({})
    unique_group_ids = group_tracking_collection.count_documents({})
    num_users = user_tracking_collection.count_documents({})
    total_owner_taught = owner_taught_responses_collection.count_documents({})
    total_conversational_learned = conversational_learning_collection.count_documents({})

    stats_text = (
        "📊 **𝙱𝚘𝚝 𝚂𝚝𝚊𝚝𝚒𝚜𝚝𝚒𝚌𝚜** 📊\n"
        f"• 𝙽𝚞𝚖𝚋𝚎𝚛 𝚘𝚏 𝚐𝚛𝚘𝚞𝚙𝚜 𝙸'𝚖 𝚒𝚗: **{unique_group_ids}** 𝚕𝚘𝚟𝚎𝚕𝚢 𝚐𝚛𝚘𝚞𝚙𝚜!\n"
        f"• 𝚃𝚘𝚝𝚊𝚕 𝚞𝚜𝚎𝚛𝚜 𝙸 𝚘𝚋𝚜𝚎𝚛𝚟𝚎𝚍: **{num_users}** 𝚜𝚠𝚎𝚎𝚝 𝚞𝚜𝚎𝚛𝚜!\n"
        f"• 𝚃𝚘𝚝𝚊𝚕 𝚖𝚎𝚜𝚜𝚊𝚐𝚎𝚜 𝙸 𝚜𝚝𝚘𝚛𝚎𝚍 (𝙾𝚕𝚍 𝙻𝚎𝚊𝚛𝚗𝚒𝚗𝚐): **{total_messages}** 𝚝𝚛𝚎𝚊𝚜𝚞𝚛𝚎 𝚘𝚏 𝚌𝚘𝚗𝚟𝚎𝚛𝚜𝚊𝚝𝚒𝚘𝚗𝚜! 🤩\n"
        f"• 𝙾𝚠𝚗𝚎𝚛-𝚝𝚊𝚞𝚐𝚑𝚝 𝚙𝚊𝚝𝚝𝚎𝚛𝚗𝚜: **{total_owner_taught}** 𝚞𝚗𝚒𝚚𝚞𝚎 𝚙𝚊𝚝𝚝𝚎𝚛𝚗𝚜!\n"
        f"• 𝙲𝚘𝚗𝚟𝚎𝚛𝚜𝚊𝚝𝚒𝚘𝚗𝚊𝚕 𝚙𝚊𝚝𝚝𝚎𝚛𝚗𝚜 𝚕𝚎𝚊𝚛𝚗𝚎𝚍: **{total_conversational_learned}** 𝚞𝚗𝚒𝚚𝚞𝚎 𝚙𝚊𝚝𝚝𝚎𝚛𝚗𝚜!\n\n"
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
        await send_and_auto_delete_reply(message, text="𝚄𝚖𝚖, 𝚝𝚘 𝚌𝚑𝚎𝚌𝚔 𝚜𝚝𝚊𝚝𝚜, 𝚙𝚕𝚎𝚊𝚜𝚎 𝚝𝚢𝚙𝚎 𝚌𝚘𝚛𝚛𝚎𝚌𝚝𝚕𝚢! 𝙻𝚒𝚔𝚎 𝚝𝚑𝚒𝚜: `/stats check`. 😊 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return

    total_messages = messages_collection.count_documents({})
    unique_group_ids = group_tracking_collection.count_documents({})
    num_users = user_tracking_collection.count_documents({})
    total_owner_taught = owner_taught_responses_collection.count_documents({})
    total_conversational_learned = conversational_learning_collection.count_documents({})

    stats_text = (
        "📊 **𝙱𝚘𝚝 𝚂𝚝𝚊𝚝𝚒𝚜𝚝𝚒𝚌𝚜** 📊\n"
        f"• 𝙽𝚞𝚖𝚋𝚎𝚛 𝚘𝚏 𝚐𝚛𝚘𝚞𝚙𝚜 𝙸'𝚖 𝚒𝚗: **{unique_group_ids}** 𝚕𝚘𝚟𝚎𝚕𝚢 𝚐𝚛𝚘𝚞𝚙𝚜!\n"
        f"• 𝚃𝚘𝚝𝚊𝚕 𝚞𝚜𝚎𝚛𝚜 𝙸 𝚘𝚋𝚜𝚎𝚛𝚟𝚎𝚍: **{num_users}** 𝚜𝚠𝚎𝚎𝚝 𝚞𝚜𝚎𝚛𝚜!\n"
        f"• 𝚃𝚘𝚝𝚊𝚕 𝚖𝚎𝚜𝚜𝚊𝚐𝚎𝚜 𝙸 𝚜𝚝𝚘𝚛𝚎𝚍 (𝙾𝚕𝚍 𝙻𝚎𝚊𝚛𝚗𝚒𝚗𝚐): **{total_messages}** 𝚝𝚛𝚎𝚊𝚜𝚞𝚛𝚎 𝚘𝚏 𝚌𝚘𝚗𝚟𝚎𝚛𝚜𝚊𝚝𝚒𝚘𝚗𝚜! 🤩\n"
        f"• 𝙾𝚠𝚗𝚎𝚛-𝚝𝚊𝚞𝚐𝚑𝚝 𝚙𝚊𝚝𝚝𝚎𝚛𝚗𝚜: **{total_owner_taught}** 𝚞𝚗𝚒𝚚𝚞𝚎 𝚙𝚊𝚝𝚝𝚎𝚛𝚗𝚜!\n"
        f"• 𝙲𝚘𝚗𝚟𝚎𝚛𝚜𝚊𝚝𝚒𝚘𝚗𝚊𝚕 𝚙𝚊𝚝𝚝𝚎𝚛𝚗𝚜 𝚕𝚎𝚊𝚛𝚗𝚎𝚍: **{total_conversational_learned}** 𝚞𝚗𝚒𝚚𝚞𝚎 𝚙𝚊𝚝𝚝𝚎𝚛𝚗𝚜!\n\n"
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
        await send_and_auto_delete_reply(message, text="𝙾𝚘𝚙𝚜! 𝚂𝚘𝚛𝚛𝚢 𝚜𝚠𝚎𝚎𝚝𝚒𝚎, 𝚝𝚑𝚒𝚜 𝚌𝚘𝚖𝚖𝚊𝚗𝚍 𝚒𝚜 𝚘𝚗𝚕𝚢 𝚏𝚘𝚛 𝚖𝚢 𝚋𝚘𝚜𝚜. 𝚈𝚘𝚞 𝚍𝚘𝚗'𝚝 𝚑𝚊𝚟𝚎 𝚙𝚎𝚛𝚖𝚒𝚜𝚜𝚒𝚘𝚗. 🤷‍♀️ (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return

    groups = list(group_tracking_collection.find({}))
    if not groups:
        await send_and_auto_delete_reply(message, text="𝙸'𝚖 𝚗𝚘𝚝 𝚒𝚗 𝚊𝚗𝚢 𝚐𝚛𝚘𝚞𝚙 𝚛𝚒𝚐𝚑𝚝 𝚗𝚘𝚠. 𝙸'𝚖 𝚕𝚘𝚗𝚎𝚕𝚢, 𝚙𝚕𝚎𝚊𝚜𝚎 𝚊𝚍𝚍 𝚖𝚎! 🥺 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return

    group_list_text = "📚 **𝙶𝚛𝚘𝚞𝚙𝚜 𝙸'𝚖 𝙸𝚗** 📚\n\n"
    for i, group in enumerate(groups):
        title = group.get("title", "𝚄𝚗𝚔𝚗𝚘𝚠𝚗 𝙶𝚛𝚘𝚞𝚙")
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
                    group_link_display = f" ([𝙸𝚗𝚟𝚒𝚝𝚎 𝙻𝚒𝚗𝚔]({invite_link}))"
                except Exception:
                    group_link_display = " (𝙿𝚛𝚒𝚟𝚊𝚝𝚎 𝙶𝚛𝚘𝚞𝚙)"
        except Exception as e:
            logger.warning(f"Could not fetch chat info for group {group_id}: {e}")
            group_link_display = " (𝙸𝚗𝚏𝚘 𝙽/𝙰)"

        group_list_text += (
            f"{i+1}. **{title}** (`{group_id}`){group_link_display}\n"
            f"   • 𝙹𝚘𝚒𝚗𝚎𝚍: {added_on}\n"
            f"   • 𝙼𝚎𝚖𝚋𝚎𝚛𝚜: {member_count}\n"
        )

    group_list_text += "\n_𝚃𝚑𝚒𝚜 𝚍𝚊𝚝𝚊 𝚒𝚜 𝚏𝚛𝚘𝚖 𝚝𝚑𝚎 𝚝𝚛𝚊𝚌𝚔𝚒𝚗𝚐 𝚍𝚊𝚝𝚊𝚋𝚊𝚜𝚎, 𝚒𝚝'𝚜 𝚊 𝚜𝚎𝚌𝚛𝚎𝚝!_ 🤫\n**𝙲𝚘𝚍𝚎 & 𝚂𝚢𝚜𝚝𝚎𝚖 𝙱𝚢:** @asbhaibsr"
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
        await send_and_auto_delete_reply(message, text="𝙾𝚘𝚙𝚜! 𝚂𝚘𝚛𝚛𝚢 𝚜𝚠𝚎𝚎𝚝𝚒𝚎, 𝚝𝚑𝚒𝚜 𝚌𝚘𝚖𝚖𝚊𝚗𝚍 𝚒𝚜 𝚘𝚗𝚕𝚢 𝚏𝚘𝚛 𝚖𝚢 𝚋𝚘𝚜𝚜. 𝚈𝚘𝚞 𝚍𝚘𝚗'𝚝 𝚑𝚊𝚟𝚎 𝚙𝚎𝚛𝚖𝚒𝚜𝚜𝚒𝚘𝚗. 🤷‍♀️ (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return

    if len(message.command) < 2:
        await send_and_auto_delete_reply(message, text="𝙿𝚕𝚎𝚊𝚜𝚎 𝚙𝚛𝚘𝚟𝚒𝚍𝚎 𝚝𝚑𝚎 𝙶𝚛𝚘𝚞𝚙 𝙸𝙳 𝚢𝚘𝚞 𝚠𝚊𝚗𝚝 𝚖𝚎 𝚝𝚘 𝚕𝚎𝚊𝚟𝚎. 𝚄𝚜𝚊𝚐𝚎: `/leavegroup -1001234567890` (𝚕𝚒𝚔𝚎 𝚝𝚑𝚒𝚜, 𝚍𝚊𝚛𝚕𝚒𝚗𝚐!) (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return

    try:
        group_id_str = message.command[1]
        if not group_id_str.startswith('-100'):
            await send_and_auto_delete_reply(message, text="𝚈𝚘𝚞 𝚙𝚛𝚘𝚟𝚒𝚍𝚎𝚍 𝚝𝚑𝚎 𝚠𝚛𝚘𝚗𝚐 𝙶𝚛𝚘𝚞𝚙 𝙸𝙳 𝚏𝚘𝚛𝚖𝚊𝚝. 𝙶𝚛𝚘𝚞𝚙 𝙸𝙳 𝚜𝚝𝚊𝚛𝚝𝚜 𝚠𝚒𝚝𝚑 `-100...` 𝙱𝚎 𝚊 𝚕𝚒𝚝𝚝𝚕𝚎 𝚖𝚘𝚛𝚎 𝚌𝚊𝚛𝚎𝚏𝚞𝚕! 😊 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
            return

        group_id = int(group_id_str)
        await client.leave_chat(group_id)

        group_tracking_collection.delete_one({"_id": group_id})
        messages_collection.delete_many({"chat_id": group_id})
        owner_taught_responses_collection.delete_many({"responses.chat_id": group_id})
        conversational_learning_collection.delete_many({"responses.chat_id": group_id})
        
        logger.info(f"Considered cleaning earning data for users from left group {group_id}. (Code by @asbhaibsr)")

        await send_and_auto_delete_reply(message, text=f"𝚂𝚞𝚌𝚌𝚎𝚜𝚜𝚏𝚞𝚕𝚕𝚢 𝚕𝚎𝚏𝚝 𝚐𝚛𝚘𝚞𝚙 `{group_id}`, 𝚊𝚗𝚍 𝚊𝚕𝚜𝚘 𝚌𝚕𝚎𝚊𝚗𝚎𝚍 𝚊𝚕𝚕 𝚒𝚝𝚜 𝚍𝚊𝚝𝚊! 𝙱𝚢𝚎-𝚋𝚢𝚎! 👋 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Left group {group_id} and cleared its data. (Code by @asbhaibsr)")

    except ValueError:
        await send_and_auto_delete_reply(message, text="𝙸𝚗𝚟𝚊𝚕𝚒𝚍 𝚐𝚛𝚘𝚞𝚙 𝙸𝙳 𝚏𝚘𝚛𝚖𝚊𝚝. 𝙿𝚕𝚎𝚊𝚜𝚎 𝚙𝚛𝚘𝚟𝚒𝚍𝚎 𝚊 𝚟𝚊𝚕𝚒𝚍 𝚗𝚞𝚖𝚎𝚛𝚒𝚌 𝙸𝙳. 𝙲𝚑𝚎𝚌𝚔 𝚝𝚑𝚎 𝚗𝚞𝚖𝚋𝚎𝚛𝚜! 😉 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await send_and_auto_delete_reply(message, text=f"𝙰𝚗 𝚎𝚛𝚛𝚘𝚛 𝚘𝚌𝚌𝚞𝚛𝚛𝚎𝚍 𝚠𝚑𝚒𝚕𝚎 𝚕𝚎𝚊𝚟𝚒𝚗𝚐 𝚝𝚑𝚎 𝚐𝚛𝚘𝚞𝚙: {e}. 𝙾𝚑 𝚗𝚘! 😢 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        logger.error(f"Error leaving group {group_id_str}: {e}. (Code by @asbhaibsr)")

    await store_message(message)
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)


@app.on_message(filters.command("cleardata") & filters.private)
async def clear_data_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    if message.from_user.id != OWNER_ID:
        await send_and_auto_delete_reply(message, text="𝚂𝚘𝚛𝚛𝚢, 𝚍𝚊𝚛𝚕𝚒𝚗𝚐! 𝚃𝚑𝚒𝚜 𝚌𝚘𝚖𝚖𝚊𝚗𝚍 𝚒𝚜 𝚘𝚗𝚕𝚢 𝚏𝚘𝚛 𝚖𝚢 𝚋𝚘𝚜𝚜. 🤫 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return

    if len(message.command) < 2:
        await send_and_auto_delete_reply(message, text="𝙷𝚘𝚠 𝚖𝚞𝚌𝚑 𝚍𝚊𝚝𝚊 𝚝𝚘 𝚌𝚕𝚎𝚊𝚗? 𝚃𝚎𝚕𝚕 𝚖𝚎 𝚝𝚑𝚎 𝚙𝚎𝚛𝚌𝚎𝚗𝚝𝚊𝚐𝚎, 𝚕𝚒𝚔𝚎: `/cleardata 10%` 𝚘𝚛 `/cleardata 100%`! 🧹 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return

    percentage_str = message.command[1].strip('%')
    try:
        percentage = int(percentage_str)
        if not (1 <= percentage <= 100):
            await send_and_auto_delete_reply(message, text="𝙿𝚎𝚛𝚌𝚎𝚗𝚝𝚊𝚐𝚎 𝚜𝚑𝚘𝚞𝚕𝚍 𝚋𝚎 𝚋𝚎𝚝𝚠𝚎𝚎𝚗 1 𝚊𝚗𝚍 100. 𝙱𝚎 𝚊 𝚕𝚒𝚝𝚝𝚕𝚎 𝚌𝚊𝚛𝚎𝚏𝚞𝚕! 🤔 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
            return
    except ValueError:
        await send_and_auto_delete_reply(message, text="𝙸𝚗𝚟𝚊𝚕𝚒𝚍 𝚙𝚎𝚛𝚌𝚎𝚗𝚝𝚊𝚐𝚎 𝚏𝚘𝚛𝚖𝚊𝚝. 𝙿𝚎𝚛𝚌𝚎𝚗𝚝𝚊𝚐𝚎 𝚜𝚑𝚘𝚞𝚕𝚍 𝚋𝚎 𝚒𝚗 𝚗𝚞𝚖𝚋𝚎𝚛𝚜, 𝚕𝚒𝚔𝚎 `10` 𝚘𝚛 `50`. 𝚃𝚛𝚢 𝚊𝚐𝚊𝚒𝚗!💖 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
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
        await send_and_auto_delete_reply(message, text=f"𝚆𝚘𝚠! 🤩 𝙸 𝚑𝚊𝚟𝚎 𝚜𝚞𝚌𝚌𝚎𝚜𝚜𝚏𝚞𝚕𝚕𝚢 𝚍𝚎𝚕𝚎𝚝𝚎𝚍 𝚢𝚘𝚞𝚛 **{percentage}%** 𝚍𝚊𝚝𝚊! 𝙰 𝚝𝚘𝚝𝚊𝚕 𝚘𝚏 **{total_deleted}** 𝚎𝚗𝚝𝚛𝚒𝚎𝚜 (𝙾𝚕𝚍: {deleted_count_old}, 𝙾𝚠𝚗𝚎𝚛-𝚃𝚊𝚞𝚐𝚑𝚝: {deleted_count_owner_taught}, 𝙲𝚘𝚗𝚟𝚎𝚛𝚜𝚊𝚝𝚒𝚘𝚗𝚊𝚕: {deleted_count_conversational}) 𝚊𝚛𝚎 𝚌𝚕𝚎𝚊𝚗𝚎𝚍. 𝙸 𝚏𝚎𝚎𝚕 𝚊 𝚋𝚒𝚝 𝚕𝚒𝚐𝚑𝚝𝚎𝚛 𝚗𝚘𝚠. ✨ (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Cleared {total_deleted} messages across collections based on {percentage}% request. (Code by @asbhaibsr)")
    else:
        await send_and_auto_delete_reply(message, text="𝚄𝚖𝚖, 𝙸 𝚍𝚒𝚍𝚗'𝚝 𝚏𝚒𝚗𝚍 𝚊𝚗𝚢𝚝𝚑𝚒𝚗𝚐 𝚝𝚘 𝚍𝚎𝚕𝚎𝚝𝚎. 𝙸𝚝 𝚜𝚎𝚎𝚖𝚜 𝚢𝚘𝚞'𝚟𝚎 𝚊𝚕𝚛𝚎𝚊𝚍𝚢 𝚌𝚕𝚎𝚊𝚗𝚎𝚍 𝚎𝚟𝚎𝚛𝚢𝚝𝚑𝚒𝚗𝚐! 🤷‍♀️ (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)

    await store_message(message)
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)


@app.on_message(filters.command("deletemessage") & filters.private)
async def delete_specific_message_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    if message.from_user.id != OWNER_ID:
        await send_and_auto_delete_reply(message, text="𝙾𝚘𝚙𝚜! 𝚂𝚘𝚛𝚛𝚢 𝚜𝚠𝚎𝚎𝚝𝚒𝚎, 𝚝𝚑𝚒𝚜 𝚌𝚘𝚖𝚖𝚊𝚗𝚍 𝚒𝚜 𝚘𝚗𝚕𝚢 𝚏𝚘𝚛 𝚖𝚢 𝚋𝚘𝚜𝚜. 🤷‍♀️ (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return

    if len(message.command) < 2:
        await send_and_auto_delete_reply(message, text="𝚆𝚑𝚒𝚌𝚑 **𝚝𝚎𝚡𝚝 𝚖𝚎𝚜𝚜𝚊𝚐𝚎** 𝚝𝚘 𝚍𝚎𝚕𝚎𝚝𝚎, 𝚙𝚕𝚎𝚊𝚜𝚎 𝚝𝚎𝚕𝚕 𝚖𝚎! 𝙻𝚒𝚔𝚎: `/deletemessage hello` 𝚘𝚛 `/deletemessage '𝚑𝚘𝚠 𝚊𝚛𝚎 𝚢𝚘𝚞'` 👻 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
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
        await send_and_auto_delete_reply(message, text=f"𝙰𝚜 𝚢𝚘𝚞 𝚌𝚘𝚖𝚖𝚊𝚗𝚍, 𝚖𝚢 𝚖𝚊𝚜𝚝𝚎𝚛! 🧞‍♀️ 𝙸 𝚏𝚘𝚞𝚗𝚍 𝚊𝚗𝚍 𝚍𝚎𝚕𝚎𝚝𝚎𝚍 **{deleted_count}** **𝚝𝚎𝚡𝚝 𝚖𝚎𝚜𝚜𝚊𝚐𝚎𝚜** 𝚛𝚎𝚕𝚊𝚝𝚎𝚍 𝚝𝚘 '{search_query}'. 𝙽𝚘𝚠 𝚝𝚑𝚊𝚝 𝚒𝚜𝚗'𝚝 𝚙𝚊𝚛𝚝 𝚘𝚏 𝚑𝚒𝚜𝚝𝚘𝚛𝚢 𝚊𝚗𝚢𝚖𝚘𝚛𝚎! ✨ (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Deleted {deleted_count} text messages with query: '{search_query}'. (Code by @asbhaibsr)")
    else:
        await send_and_auto_delete_reply(message, text="𝚄𝚖𝚖, 𝙸 𝚍𝚒𝚍𝚗'𝚝 𝚏𝚒𝚗𝚍 𝚊𝚗𝚢 **𝚝𝚎𝚡𝚝 𝚖𝚎𝚜𝚜𝚊𝚐𝚎** 𝚒𝚗 𝚖𝚢 𝚍𝚊𝚝𝚊𝚋𝚊𝚜𝚎 𝚠𝚒𝚝𝚑 𝚢𝚘𝚞𝚛 𝚚𝚞𝚎𝚛𝚢. 𝙲𝚑𝚎𝚌𝚔 𝚝𝚑𝚎 𝚜𝚙𝚎𝚕𝚕𝚒𝚗𝚐? 🤔 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)

    await store_message(message)
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)


@app.on_message(filters.command("delsticker") & filters.private)
async def delete_specific_sticker_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    if message.from_user.id != OWNER_ID:
        await send_and_auto_delete_reply(message, text="𝙾𝚘𝚙𝚜! 𝚂𝚘𝚛𝚛𝚢 𝚜𝚠𝚎𝚎𝚝𝚒𝚎, 𝚝𝚑𝚒𝚜 𝚌𝚘𝚖𝚖𝚊𝚗𝚍 𝚒𝚜 𝚘𝚗𝚕𝚢 𝚏𝚘𝚛 𝚖𝚢 𝚋𝚘𝚜𝚜. 🤷‍♀️ (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return

    if len(message.command) < 2:
        await send_and_auto_delete_reply(message, text="𝙷𝚘𝚠 𝚖𝚊𝚗𝚢 **𝚜𝚝𝚒𝚌𝚔𝚎𝚛𝚜** 𝚝𝚘 𝚍𝚎𝚕𝚎𝚝𝚎? 𝚃𝚎𝚕𝚕 𝚖𝚎 𝚝𝚑𝚎 𝚙𝚎𝚛𝚌𝚎𝚗𝚝𝚊𝚐𝚎, 𝚕𝚒𝚔𝚎: `/delsticker 10%` 𝚘𝚛 `delsticker 20%` 𝚘𝚛 `delsticker 40%`! 🧹 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return

    percentage_str = message.command[1].strip('%')
    try:
        percentage = int(percentage_str)
        if not (1 <= percentage <= 100):
            await send_and_auto_delete_reply(message, text="𝙿𝚎𝚛𝚌𝚎𝚗𝚝𝚊𝚐𝚎 𝚜𝚑𝚘𝚞𝚕𝚍 𝚋𝚎 𝚋𝚎𝚝𝚠𝚎𝚎𝚗 1 𝚊𝚗𝚍 100. 𝙱𝚎 𝚊 𝚕𝚒𝚝𝚝𝚕𝚎 𝚌𝚊𝚛𝚎𝚏𝚞𝚕! 🤔 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
            return
    except ValueError:
        await send_and_auto_delete_reply(message, text="𝙸𝚗𝚟𝚊𝚕𝚒𝚍 𝚙𝚎𝚛𝚌𝚎𝚗𝚝𝚊𝚐𝚎 𝚏𝚘𝚛𝚖𝚊𝚝. 𝙿𝚎𝚛𝚌𝚎𝚗𝚝𝚊𝚐𝚎 𝚜𝚑𝚘𝚞𝚕𝚍 𝚋𝚎 𝚒𝚗 𝚗𝚞𝚖𝚋𝚎𝚛𝚜, 𝚕𝚒𝚔𝚎 `10` 𝚘𝚛 `50`. 𝚃𝚛𝚢 𝚊𝚐𝚊𝚒𝚗!💖 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
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
        await send_and_auto_delete_reply(message, text=f"𝙰𝚜 𝚢𝚘𝚞 𝚌𝚘𝚖𝚖𝚊𝚗𝚍, 𝚖𝚢 𝚖𝚊𝚜𝚝𝚎𝚛! 🧞‍♀️ 𝙸 𝚏𝚘𝚞𝚗𝚍 𝚊𝚗𝚍 𝚍𝚎𝚕𝚎𝚝𝚎𝚍 **{percentage}%** 𝚜𝚝𝚒𝚌𝚔𝚎𝚛𝚜. 𝙰 𝚝𝚘𝚝𝚊𝚕 𝚘𝚏 **{deleted_count}** 𝚜𝚝𝚒𝚌𝚔𝚎𝚛𝚜 𝚛𝚎𝚖𝚘𝚟𝚎𝚍. 𝙽𝚘𝚠 𝚝𝚑𝚊𝚝 𝚒𝚜𝚗'𝚝 𝚙𝚊𝚛𝚝 𝚘𝚏 𝚑𝚒𝚜𝚝𝚘𝚛𝚢 𝚊𝚗𝚢𝚖𝚘𝚛𝚎! ✨ (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Deleted {deleted_count} stickers based on {percentage}% request. (Code by @asbhaibsr)")
    else:
        await send_and_auto_delete_reply(message, text="𝚄𝚖𝚖, 𝙸 𝚍𝚒𝚍𝚗'𝚝 𝚏𝚒𝚗𝚍 𝚊𝚗𝚢 **𝚜𝚝𝚒𝚌𝚔𝚎𝚛** 𝚒𝚗 𝚖𝚢 𝚍𝚊𝚝𝚊𝚋𝚊𝚜𝚎 𝚠𝚒𝚝𝚑 𝚢𝚘𝚞𝚛 𝚚𝚞𝚎𝚛𝚢. 𝙴𝚒𝚝𝚑𝚎𝚛 𝚝𝚑𝚎𝚛𝚎 𝚊𝚛𝚎 𝚗𝚘 𝚜𝚝𝚒𝚌𝚔𝚎𝚛𝚜, 𝚘𝚛 𝚝𝚑𝚎 𝚙𝚎𝚛𝚌𝚎𝚗𝚝𝚊𝚐𝚎 𝚒𝚜 𝚝𝚘𝚘 𝚕𝚘𝚠! 🤔 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)

    await store_message(message)
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)


@app.on_message(filters.command("clearearning") & filters.private)
async def clear_earning_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    if message.from_user.id != OWNER_ID:
        await send_and_auto_delete_reply(message, text="𝚂𝚘𝚛𝚛𝚢 𝚍𝚊𝚛𝚕𝚒𝚗𝚐! 𝚃𝚑𝚒𝚜 𝚌𝚘𝚖𝚖𝚊𝚗𝚍 𝚒𝚜 𝚘𝚗𝚕𝚢 𝚏𝚘𝚛 𝚖𝚢 𝚋𝚘𝚜𝚜. 🚫 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return

    await reset_monthly_earnings_manual()
    await send_and_auto_delete_reply(message, text="💰 **𝙴𝚊𝚛𝚗𝚒𝚗𝚐 𝚍𝚊𝚝𝚊 𝚜𝚞𝚌𝚌𝚎𝚜𝚜𝚏𝚞𝚕𝚕𝚢 𝚌𝚕𝚎𝚊𝚛𝚎𝚍!** 𝙽𝚘𝚠 𝚎𝚟𝚎𝚛𝚢𝚘𝚗𝚎 𝚠𝚒𝚕𝚕 𝚜𝚝𝚊𝚛𝚝 𝚏𝚛𝚘𝚖 𝚣𝚎𝚛𝚘 𝚊𝚐𝚊𝚒𝚗! 😉 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
    logger.info(f"Owner {message.from_user.id} manually triggered earning data reset. (Code by @asbhaibsr)")

    await store_message(message)
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)


@app.on_message(filters.command("restart") & filters.private)
async def restart_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    if message.from_user.id != OWNER_ID:
        await send_and_auto_delete_reply(message, text="𝚂𝚘𝚛𝚛𝚢, 𝚍𝚊𝚛𝚕𝚒𝚗𝚐! 𝚃𝚑𝚒𝚜 𝚌𝚘𝚖𝚖𝚊𝚗𝚍 𝚒𝚜 𝚘𝚗𝚕𝚢 𝚏𝚘𝚛 𝚖𝚢 𝚋𝚘𝚜𝚜. 🚫 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return

    await send_and_auto_delete_reply(message, text="𝙾𝚔𝚊𝚢, 𝚍𝚊𝚛𝚕𝚒𝚗𝚐! 𝙸'𝚖 𝚝𝚊𝚔𝚒𝚗𝚐 𝚊 𝚜𝚑𝚘𝚛𝚝 𝚗𝚊𝚙 𝚗𝚘𝚠 𝚊𝚗𝚍 𝚝𝚑𝚎𝚗 𝙸'𝚕𝚕 𝚋𝚎 𝚋𝚊𝚌𝚔, 𝚌𝚘𝚖𝚙𝚕𝚎𝚝𝚎𝚕𝚢 𝚏𝚛𝚎𝚜𝚑 𝚊𝚗𝚍 𝚎𝚗𝚎𝚛𝚐𝚎𝚝𝚒𝚌! 𝙿𝚕𝚎𝚊𝚜𝚎 𝚠𝚊𝚒𝚝 𝚊 𝚕𝚒𝚝𝚝𝚕𝚎, 𝚘𝚔𝚊𝚢? ✨ (System by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
    logger.info("Bot is restarting... (System by @asbhaibsr)")
    import asyncio
    import os
    import sys
    await asyncio.sleep(0.5)
    os.execl(sys.executable, sys.executable, *sys.argv)

@app.on_message(filters.command("clearall") & filters.private)
async def clear_all_dbs_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    if message.from_user.id != OWNER_ID:
        await send_and_auto_delete_reply(message, text="𝙵𝚘𝚗𝚝, 𝚝𝚑𝚒𝚜 𝚌𝚘𝚖𝚖𝚊𝚗𝚍 𝚒𝚜 𝚘𝚗𝚕𝚢 𝚏𝚘𝚛 𝚖𝚢 𝚋𝚘𝚜𝚜. 🚫", parse_mode=ParseMode.MARKDOWN)
        return

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Yᴇꜱ, Dᴇʟᴇᴛᴇ ⚠️", callback_data='confirm_clearall_dbs'),
                InlineKeyboardButton("Nᴏ, Kᴇᴇᴘ Iᴛ ✅", callback_data='cancel_clearall_dbs')
            ]
        ]
    )

    await send_and_auto_delete_reply(
        message,
        text="⚠️ **𝚆𝙰𝚁𝙽𝙸𝙽𝙶:** 𝙰𝚛𝚎 𝚢𝚘𝚞 𝚜𝚞𝚛𝚎 𝚢𝚘𝚞 𝚠𝚊𝚗𝚝 𝚝𝚘 𝚍𝚎𝚕𝚎𝚝𝚎 **𝚊𝚕𝚕 𝚍𝚊𝚝𝚊** 𝚏𝚛𝚘𝚖 𝚢𝚘𝚞𝚛 𝙼𝚘𝚗𝚐𝚘𝙳𝙱 𝙳𝚊𝚝𝚊𝚋𝚊𝚜𝚎𝚜 (𝙼𝚎𝚜𝚜𝚊𝚐𝚎𝚜, 𝙱𝚞𝚝𝚝𝚘𝚗𝚜, 𝚃𝚛𝚊𝚌𝚔𝚒𝚗𝚐)?\n\n"
             "𝚃𝚑𝚒𝚜 𝚊𝚌𝚝𝚒𝚘𝚗 𝚒𝚜 **𝚒𝚛𝚛𝚎𝚟𝚎𝚛𝚜𝚒𝚋𝚕𝚎** 𝚊𝚗𝚍 𝚊𝚕𝚕 𝚢𝚘𝚞𝚛 𝚍𝚊𝚝𝚊 𝚠𝚒𝚕𝚕 𝚋𝚎 𝚕𝚘𝚜𝚝 𝚏𝚘𝚛𝚎𝚟𝚎𝚛.\n\n"
             "𝙲𝚑𝚘𝚘𝚜𝚎 𝚌𝚊𝚛𝚎𝚏𝚞𝚕𝚕𝚢!",
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
                await send_and_auto_delete_reply(message, text="𝚈𝚘𝚞 𝚌𝚊𝚗'𝚝 𝚍𝚎𝚕𝚎𝚝𝚎 𝚖𝚢 𝚍𝚊𝚝𝚊, 𝚋𝚘𝚜𝚜! 😅", parse_mode=ParseMode.MARKDOWN)
                return
        except ValueError:
            await send_and_auto_delete_reply(message, text="𝚆𝚛𝚘𝚗𝚐 𝚄𝚜𝚎𝚛 𝙸𝙳 𝚏𝚘𝚛𝚖𝚊𝚝. 𝙿𝚕𝚎𝚊𝚜𝚎 𝚙𝚛𝚘𝚟𝚒𝚍𝚎 𝚊 𝚟𝚊𝚕𝚒𝚍 𝚗𝚞𝚖𝚎𝚛𝚒𝚌 𝙸𝙳.", parse_mode=ParseMode.MARKDOWN)
            return
    elif len(message.command) > 1 and message.from_user.id != OWNER_ID:
        await send_and_auto_delete_reply(message, text="𝚈𝚘𝚞 𝚊𝚛𝚎 𝚗𝚘𝚝 𝚊𝚞𝚝𝚑𝚘𝚛𝚒𝚣𝚎𝚍 𝚝𝚘 𝚞𝚜𝚎 𝚝𝚑𝚒𝚜 𝚌𝚘𝚖𝚖𝚊𝚗𝚍 𝚝𝚑𝚒𝚜 𝚠𝚊𝚢. 𝚃𝚑𝚒𝚜 𝚏𝚎𝚊𝚝𝚞𝚛𝚎 𝚒𝚜 𝚘𝚗𝚕𝚢 𝚏𝚘𝚛 𝚖𝚢 𝚋𝚘𝚜𝚜.", parse_mode=ParseMode.MARKDOWN)
        return
    else:
        target_user_id = message.from_user.id

    if not target_user_id:
        await send_and_auto_delete_reply(message, text="𝙸 𝚌𝚊𝚗'𝚝 𝚏𝚒𝚐𝚞𝚛𝚎 𝚘𝚞𝚝 𝚠𝚑𝚘𝚜𝚎 𝚍𝚊𝚝𝚊 𝚝𝚘 𝚍𝚎𝚕𝚎𝚝𝚎. 😕", parse_mode=ParseMode.MARKDOWN)
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
                await send_and_auto_delete_reply(message, text=f"𝚆𝚘𝚠! ✨ 𝙸 𝚑𝚊𝚟𝚎 𝚍𝚎𝚕𝚎𝚝𝚎𝚍 𝚢𝚘𝚞𝚛 `{deleted_messages_count}` 𝚌𝚘𝚗𝚟𝚎𝚛𝚜𝚊𝚝𝚒𝚘𝚗 𝚖𝚎𝚜𝚜𝚊𝚐𝚎𝚜 𝚊𝚗𝚍 𝚎𝚊𝚛𝚗𝚒𝚗𝚐 𝚍𝚊𝚝𝚊. 𝚈𝚘𝚞 𝚊𝚛𝚎 𝚌𝚘𝚖𝚙𝚕𝚎𝚝𝚎𝚕𝚢 𝚏𝚛𝚎𝚜𝚑 𝚗𝚘𝚠! 😊", parse_mode=ParseMode.MARKDOWN)
                logger.info(f"User {target_user_id} successfully cleared their data.")
            else:
                await send_and_auto_delete_reply(message, text=f"𝙱𝚘𝚜𝚜'𝚜 𝚘𝚛𝚍𝚎𝚛! 👑 𝙸 𝚑𝚊𝚟𝚎 𝚍𝚎𝚕𝚎𝚝𝚎𝚍 `{deleted_messages_count}` 𝚌𝚘𝚗𝚟𝚎𝚛𝚜𝚊𝚝𝚒𝚘𝚗 𝚖𝚎𝚜𝚜𝚊𝚐𝚎𝚜 𝚊𝚗𝚍 𝚎𝚊𝚛𝚗𝚒𝚗𝚐 𝚍𝚊𝚝𝚊 𝚏𝚘𝚛 𝚞𝚜𝚎𝚛 `{target_user_id}`. 😉", parse_mode=ParseMode.MARKDOWN)
                logger.info(f"Owner {message.from_user.id} cleared data for user {target_user_id}.")
        else:
            if target_user_id == message.from_user.id:
                await send_and_auto_delete_reply(message, text="𝚈𝚘𝚞 𝚍𝚘𝚗'𝚝 𝚑𝚊𝚟𝚎 𝚊𝚗𝚢 𝚍𝚊𝚝𝚊 𝚜𝚝𝚘𝚛𝚎𝚍 𝚝𝚘 𝚍𝚎𝚕𝚎𝚝𝚎. 𝙼𝚢 𝚍𝚊𝚝𝚊𝚋𝚊𝚜𝚎 𝚒𝚜 𝚌𝚘𝚖𝚙𝚕𝚎𝚝𝚎𝚕𝚢 𝚎𝚖𝚙𝚝𝚢 𝚏𝚘𝚛 𝚢𝚘𝚞! 🤷‍♀️", parse_mode=ParseMode.MARKDOWN)
            else:
                await send_and_auto_delete_reply(message, text=f"𝙽𝚘 𝚍𝚊𝚝𝚊 𝚏𝚘𝚞𝚗𝚍 𝚏𝚘𝚛 𝚞𝚜𝚎𝚛 `{target_user_id}` 𝚝𝚘 𝚍𝚎𝚕𝚎𝚝𝚎.", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await send_and_auto_delete_reply(message, text=f"𝚂𝚘𝚖𝚎𝚝𝚑𝚒𝚗𝚐 𝚠𝚎𝚗𝚝 𝚠𝚛𝚘𝚗𝚐 𝚠𝚑𝚒𝚕𝚎 𝚍𝚎𝚕𝚎𝚝𝚒𝚗𝚐 𝚍𝚊𝚝𝚊: {e}. 𝙾𝚑 𝚗𝚘! 😱", parse_mode=ParseMode.MARKDOWN)
        logger.error(f"Error clearing data for user {target_user_id}: {e}")
    await store_message(message)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.id)


# -----------------------------------------------------
# GROUP COMMANDS
# -----------------------------------------------------

@app.on_message(filters.command("start") & filters.group)
async def start_group_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    user_name = message.from_user.first_name if message.from_user else "Dost"
    welcome_message = (
        f"🌟 𝙷𝚎𝚢 **{user_name}** 𝚍𝚎𝚊𝚛! 𝚆𝚎𝚕𝚌𝚘𝚖𝚎! 🌟\n\n"
        "𝙸'𝚖 𝚛𝚎𝚊𝚍𝚢 𝚝𝚘 𝚕𝚒𝚜𝚝𝚎𝚗 𝚊𝚗𝚍 𝚕𝚎𝚊𝚛𝚗 𝚊𝚕𝚕 𝚝𝚑𝚎 𝚐𝚛𝚘𝚞𝚙 𝚌𝚘𝚗𝚟𝚎𝚛𝚜𝚊𝚝𝚒𝚘𝚗𝚜!\n"
        "𝚄𝚜𝚎 𝚝𝚑𝚎 `/settings` 𝚌𝚘𝚖𝚖𝚊𝚗𝚍 𝚝𝚘 𝚖𝚊𝚗𝚊𝚐𝚎 𝚊𝚕𝚕 𝚐𝚛𝚘𝚞𝚙 𝚜𝚎𝚝𝚝𝚒𝚗𝚐𝚜."
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
                InlineKeyboardButton("💰 Eᴀʀɴɪɴɢ Lᴇᴀᴅᴇʀʙᴏᴀʀᴅ", callback_data="show_earning_leaderboard")
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


@app.on_message(filters.command("settings") & filters.group)
async def open_settings_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    # 1. Check for Admin/Owner status
    if not await is_admin_or_owner(client, message.chat.id, message.from_user.id):
        await send_and_auto_delete_reply(message, text="𝙵𝚘𝚗𝚝, 𝚝𝚑𝚒𝚜 𝚌𝚘𝚖𝚖𝚊𝚗𝚍 𝚌𝚊𝚗 𝚘𝚗𝚕𝚢 𝚋𝚎 𝚞𝚜𝚎𝚍 𝚋𝚢 𝚖𝚢 𝚋𝚘𝚜𝚜 (𝙰𝚍𝚖𝚒𝚗/𝙾𝚠𝚗𝚎𝚛)! 🤷‍♀️", parse_mode=ParseMode.MARKDOWN)
        return

    # 2. Fetch current settings and default punishment
    current_status_doc = group_tracking_collection.find_one({"_id": message.chat.id})
    
    # Default values if not found
    bot_enabled = current_status_doc.get("bot_enabled", True) if current_status_doc else True
    linkdel_enabled = current_status_doc.get("linkdel_enabled", False) if current_status_doc else False
    biolinkdel_enabled = current_status_doc.get("biolinkdel_enabled", False) if current_status_doc else False
    usernamedel_enabled = current_status_doc.get("usernamedel_enabled", False) if current_status_doc else False
    
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

    # 3. Create the Main Settings Keyboard (Styled Buttons)
    keyboard = InlineKeyboardMarkup(
        [
            # Module Toggles
            [
                InlineKeyboardButton(f"🤖 Bᴏᴛ Cʜᴀᴛᴛɪɴɢ: {bot_status}", callback_data="toggle_setting_bot_enabled"),
            ],
            [
                InlineKeyboardButton(f"🔗 Lɪɴᴋ Dᴇʟᴇᴛᴇ: {link_status}", callback_data="toggle_setting_linkdel_enabled"),
            ],
            [
                InlineKeyboardButton(f"👤 Bɪᴏ Lɪɴᴋ Dᴇʟᴇᴛᴇ: {biolink_status}", callback_data="toggle_setting_biolinkdel_enabled"),
            ],
            [
                InlineKeyboardButton(f"🗣️ @Uꜱᴇʀɴᴀᴍᴇ Dᴇʟᴇᴛᴇ: {username_status}", callback_data="toggle_setting_usernamedel_enabled"),
            ],
            # Punishment and Biolink Exception
            [
                InlineKeyboardButton(f"🔨 Dᴇꜰᴀᴜʟᴛ Pᴜɴɪꜱʜᴍᴇɴᴛ: {punishment_text}", callback_data="open_punishment_settings"),
            ],
            [
                 InlineKeyboardButton("👤 Bɪᴏ Lɪɴᴋ Exᴄᴇᴘᴛɪᴏɴꜱ 📝", callback_data="open_biolink_exceptions")
            ],
            # Close Button
            [
                InlineKeyboardButton("❌ Cʟᴏꜱᴇ Sᴇᴛᴛɪɴɢꜱ", callback_data="close_settings")
            ]
        ]
    )

    # 4. Send the Settings Message (Translated and styled)
    settings_message = (
        f"⚙️ **𝙶𝚛𝚘𝚞𝚙 𝚂𝚎𝚝𝚝𝚒𝚗𝚐𝚜: {message.chat.title}** 🛠️\n\n"
        "𝙷𝚎𝚕𝚕𝚘, 𝙱𝚘𝚜𝚜! 𝚈𝚘𝚞 𝚌𝚊𝚗 𝚌𝚘𝚗𝚝𝚛𝚘𝚕 𝚝𝚑𝚎 𝚐𝚛𝚘𝚞𝚙 𝚛𝚞𝚕𝚎𝚜 𝚊𝚗𝚍 𝚋𝚘𝚝 𝚏𝚞𝚗𝚌𝚝𝚒𝚘𝚗𝚜 𝚏𝚛𝚘𝚖 𝚝𝚑𝚎 𝚋𝚞𝚝𝚝𝚘𝚗𝚜 𝚋𝚎𝚕𝚘𝚠.\n"
        "𝚄𝚜𝚎𝚛𝚜 𝚠𝚑𝚘 𝚋𝚛𝚎𝚊𝚔 𝚢𝚘𝚞𝚛 𝚏𝚒𝚕𝚝𝚎𝚛 𝚜𝚎𝚝𝚝𝚒𝚗𝚐𝚜 𝚠𝚒𝚕𝚕 𝚛𝚎𝚌𝚎𝚒𝚟𝚎 𝚝𝚑𝚎 **𝙳𝚎𝚏𝚊𝚞𝚕𝚝 𝙿𝚞𝚗𝚒𝚜𝚑𝚖𝚎𝚗𝚝**.\n\n"
        f"**𝙳𝚎𝚏𝚊𝚞𝚕𝚝 𝙿𝚞𝚗𝚒𝚜𝚑𝚖𝚎𝚗𝚝:** {punishment_text}\n"
        "__𝙲𝚑𝚘𝚘𝚜𝚎 𝚠𝚑𝚊𝚝 𝚙𝚞𝚗𝚒𝚜𝚑𝚖𝚎𝚗𝚝 𝚝𝚘 𝚐𝚒𝚟𝚎 𝚝𝚘 𝚛𝚞𝚕𝚎-𝚋𝚛𝚎𝚊𝚔𝚎𝚛𝚜 𝚏𝚛𝚘𝚖 '𝙳𝚎𝚏𝚊𝚞𝚕𝚝 𝙿𝚞𝚗𝚒𝚜𝚑𝚖𝚎𝚗𝚝'.__"
    )

    await send_and_auto_delete_reply(
        message,
        text=settings_message,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )
    await store_message(message)
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await update_group_info(message.chat.id, message.chat.title, message.chat.username)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)
    logger.info(f"Group settings command processed in chat {message.chat.id} by admin {message.from_user.id}. (Code by @asbhaibsr)")


# -----------------------------------------------------
# DELETED/REMOVED COMMANDS 
# -----------------------------------------------------

# @app.on_message(filters.command("chat") & filters.group)
# @app.on_message(filters.command("linkdel") & filters.group)
# @app.on_message(filters.command("biolinkdel") & filters.group)
# @app.on_message(filters.command("biolink") & filters.group)
# @app.on_message(filters.command("usernamedel") & filters.group)
#
# **उपरोक्त सभी कमांड्स को हटा दिया गया है और अब वे /settings मेनू से मैनेज होंगी।**
# **`/biolink` का कार्य अब `open_biolink_exceptions` कॉलबैक में चला जाएगा।**
