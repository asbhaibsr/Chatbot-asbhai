# commands.py

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
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
# --- 🟢 बदलाव 1: get_top_active_groups को जोड़ा गया 🟢 ---
from utils import (
    is_on_command_cooldown, update_command_cooldown, update_group_info, update_user_info,
    get_top_earning_users, reset_monthly_earnings_manual, delete_after_delay_for_message,
    store_message, is_admin_or_owner, get_top_active_groups # 🟢 यहाँ जोड़ा गया 🟢
)
# --- 🟢 बदलाव 1 का अंत 🟢 ---

import callbacks # <--- This line is essential for importing callbacks.py
import broadcast_handler # <--- 🌟 New broadcast file imported 🌟

# 🟢 Utility alias (kept for backward compatibility with the rest of the code)
send_and_auto_delete_reply = delete_after_delay_for_message 

# --- AI Modes Map for Display (Must match the one in callbacks.py) ---
AI_MODES_MAP = {
    "off": {"label": "❌ AI Mᴏᴅᴇ Oғғ", "display": "❌ Oғғ"},
    "realgirl": {"label": "👧 Rᴇᴀʟ Gɪʀʟ", "display": "👧 Rᴇᴀʟ"},
    "romanticgirl": {"label": "💖 Rᴏᴍᴀɴ𝘁𝗶𝗰 Gɪʀ𝗹", "display": "💖 Rᴏᴍ"},
    "motivationgirl": {"label": "💪 Mᴏ𝘁𝗶𝘃𝗮𝘁𝗶𝗼𝗻 Gɪʀ𝗹", "display": "💪 Mᴏᴛ𝗶"},
    "studygirl": {"label": "📚 S𝘁𝘂𝗱𝘆 Gɪʀ𝗹", "display": "📚 S𝘁𝘂𝗱𝘆"},
    "gemini": {"label": "✨ Gᴇ𝗺𝗶𝗻𝗶 (Sᴜ𝗽𝗲𝗿 AI)", "display": "✨ Gᴇ𝗺𝗶𝗻𝗶"},
}
# -----------------------------------------------------


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
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)
    logger.info(f"Private start command processed for user {message.from_user.id}.")

# --- 🟢 बदला हुआ: /topusers अब टॉप ग्रुप्स दिखाता है 🟢 ---
@app.on_message(filters.command("topusers") & (filters.private | filters.group))
async def top_users_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    # --- मॉडिफाइड: यूजर्स की जगह टॉप ग्रुप्स फ़ेच करें ---
    top_groups = await get_top_active_groups() 
    
    if not top_groups:
        await send_and_auto_delete_reply(message, text="😢 **कोई भी ग्रुप अभी लीडरबोर्ड पर नहीं है!**\n\n**Powered By:** @asbhaibsr", parse_mode=ParseMode.MARKDOWN)
        return

    earning_messages = ["👑 **Top 5 Active Groups - Monthly Leaderboard!** 👑\n\n"]
    
    # --- नया: ग्रुप्स के लिए प्राइज स्ट्रक्चर ---
    prizes = {
        1: "💰 ₹90", 2: "💸 ₹60", 3: "🎁 ₹30",
        4: "🏅 ₹10", 5: "🏅 ₹10"
    }

    for i, group in enumerate(top_groups[:5]):
        rank = i + 1
        group_title = group.get('title', 'Unknown Group')
        message_count = group.get('message_count', 0)
        prize_str = prizes.get(rank, "🏅 No Prize")
        
        # --- नया: ग्रुप और ओनर लिंक्स (ब्लू टेक्स्ट) ---
        group_link = f"**{group_title}**" # डिफ़ॉल्ट
        if group.get('username'):
            # ग्रुप नाम को ब्लू लिंक बनाएँ
            group_link = f"[{group_title}](https://t.me/{group.get('username')})"
        
        owner_name = group.get('owner_name', 'Unknown')
        owner_link = f"**{owner_name}**" # डिफ़ॉल्ट
        if group.get('owner_id'):
            # ओनर नाम को ब्लू लिंक बनाएँ
            owner_link = f"[{owner_name}](tg://user?id={group.get('owner_id')})"
        # --- नए का अंत ---

        earning_messages.append(
            f"**{rank}.** 🌟 **{group_link}** 🌟\n"
            f"   • **Owner:** {owner_link}\n"
            f"   • **Total Messages:** {message_count} 💬\n"
            f"   • **Prize:** **{prize_str}**\n"
        )
    
    earning_messages.append(
        "\n*यह सिस्टम हर महीने की पहली तारीख को ऑटोमैटिक रीसेट हो जाता है!*\n"
        "**Powered By:** @asbhaibsr"
    )
    
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("💰 Claim Prize", url=f"https://t.me/{ASBHAI_USERNAME}"),
                InlineKeyboardButton("❓ Support Group", url="https://t.me/aschat_group")
            ]
        ]
    )
    
    await send_and_auto_delete_reply(message, text="\n".join(earning_messages), reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
    
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await update_group_info(message.chat.id, message.chat.title, message.chat.username)
    logger.info(f"टॉप ग्रुप्स कमांड यूजर {message.from_user.id} द्वारा चैट {message.chat.id} में प्रोसेस की गई।")
# --- 🟢 बदले हुए फ़ंक्शन का अंत 🟢 ---


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

    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)


@app.on_message(filters.command("cleardata") & filters.private)
async def clear_data_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    if message.from_user.id != OWNER_ID:
        await send_and_auto_delete_reply(message, text="𝗦𝗼𝗿𝗿𝘆, 𝗱𝗮𝗿𝗹𝗶𝗻𝗴! 𝗧𝗵𝗶𝘀 𝗰𝗼𝗺𝗺𝗮𝗻𝗱 𝗶𝘀 𝗼𝗻𝗹𝘆 𝗳𝗼𝗿 𝗺𝘆 𝗯𝗼𝘀𝘀. 🤫", parse_mode=ParseMode.MARKDOWN)
        return

    # --- 🟢 बदलाव 2: /cleardata (बिना आर्ग्युमेंट) लॉजिक 🟢 ---
    if len(message.command) < 2:
        # यूजर ने /cleardata बिना परसेंटेज के चलाया
        try:
            logger.info("जंक यूजर डेटा क्लीनअप चलाया जा रहा है...")
            
            # user_tracking में उन यूजर्स को ढूँढें जो earning_tracking में नहीं हैं
            # इसका मतलब है कि वे जुड़े लेकिन कभी कोई ट्रैक किया गया मैसेज नहीं भेजा
            users_pipeline = [
                {
                    '$lookup': {
                        'from': 'monthly_earnings_data',
                        'localField': '_id',
                        'foreignField': '_id',
                        'as': 'earnings'
                    }
                }, {
                    '$match': {
                        'earnings': { '$eq': [] }
                    }
                }
            ]
            
            junk_users = list(user_tracking_collection.aggregate(users_pipeline))
            # ओनर को छोड़कर सभी जंक यूजर IDs
            junk_user_ids = [user['_id'] for user in junk_users if user['_id'] != OWNER_ID]
            
            deleted_count = 0
            if junk_user_ids:
                result = user_tracking_collection.delete_many({"_id": {"$in": junk_user_ids}})
                deleted_count = result.deleted_count
                
            await send_and_auto_delete_reply(message, text=f"🧹 **जंक डेटा क्लीनअप पूरा हुआ!**\n\nमैंने **{deleted_count}** जंक यूजर एंट्री (वे यूजर्स जो जुड़े लेकिन कभी कोई ट्रैक किया गया मैसेज नहीं भेजा) को ढूँढ कर डिलीट कर दिया है।\n\n*नोट: ब्लॉक किए गए यूजर्स ब्रॉडकास्ट के दौरान ऑटोमैटिकली क्लीन हो जाते हैं।*", parse_mode=ParseMode.MARKDOWN)
            logger.info(f"जंक क्लीनअप चला, {deleted_count} यूजर्स डिलीट हुए।")
        
        except Exception as e:
             await send_and_auto_delete_reply(message, text=f"❌ **जंक क्लीनअप के दौरान एरर:** {e}", parse_mode=ParseMode.MARKDOWN)
             logger.error(f"Error during /cleardata junk cleanup: {e}")
        
        return # फ़ंक्शन को रोकें
    # --- 🟢 बदलाव 2 का अंत 🟢 ---


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
        await send_and_auto_delete_reply(message, text=f"𝗪𝗼𝘄! 🤩 𝗜 𝗵𝗮𝘃𝗲 𝘀𝘂𝗰𝗰𝗲𝘀𝘀𝗳𝘂𝗹𝗹𝘆 𝗱𝗲𝗹𝗲𝘁𝗲𝗱 𝘆𝗼𝘂𝗿 **{percentage}%** 𝗱𝗮𝘁𝗮! 𝗔 𝘁𝗼𝘁𝗮𝗹 𝗼𝗳 **{total_deleted}** 𝗲𝗻𝘁𝗿𝗶𝗲𝘀 (𝗢𝗹𝗱: {deleted_count_old}, 𝗢𝘄𝗻𝗲𝗿-𝗧𝗮𝘂𝗴𝗵𝘁: {deleted_count_owner_taught}, 𝗖𝗼𝗻𝘃𝗲𝗿𝘀𝗮𝘁𝗶𝗼𝗻𝗮𝗹: {deleted_count_conversational}) 𝗮𝗿𝗲 𝗰𝗹𝗲𝗮𝗻𝗲𝗱. 𝗜 𝗳𝗲𝗲𝗹 𝗮 b𝗶𝘁 𝗹𝗶𝗴𝗵𝘁𝗲𝗿 𝗻𝗼𝘄. ✨", parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Cleared {total_deleted} messages across collections based on {percentage}% request.")
    else:
        await send_and_auto_delete_reply(message, text="𝗨𝗺𝗺, 𝗜 𝗱𝗶𝗱𝗻't 𝗳𝗶𝗻𝗱 𝗮𝗻𝘆𝘁𝗵𝗶𝗻𝗴 𝘁𝗼 𝗱𝗲𝗹𝗲𝘁𝗲. 𝗜𝘁 𝘀𝗲𝗲𝗺𝘀 𝘆𝗼𝘂'𝘃𝗲 𝗮𝗹𝗿𝗲𝗮𝗱𝘆 𝗰𝗹𝗲𝗮𝗻𝗲𝗱 𝗲𝘃𝗲𝗿𝘆𝘁𝗵𝗶𝗻𝗴! 🤷‍♀️", parse_mode=ParseMode.MARKDOWN)

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
                InlineKeyboardButton("Yᴇꜱ, Dᴇ𝗹𝗲𝘁𝗲 ⚠️", callback_data='confirm_clearall_dbs'),
                InlineKeyboardButton("Nᴏ, Kᴇ𝗲𝗽 I𝘁 ✅", callback_data='cancel_clearall_dbs')
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
    
    # FIX: Corrected update_user_info arguments
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)


@app.on_message(filters.command("setcommands") & filters.private)
async def set_commands_command(client: Client, message: Message):
    """Set bot commands automatically (OWNER ONLY - NEW FIX)"""
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    if message.from_user.id != OWNER_ID:
        await send_and_auto_delete_reply(message, text="❌ **This command is only for the bot owner!**")
        return

    try:
        # --- 🟢 बदलाव 3: नई: एक्सपैंडेड कमांड लिस्ट 🟢 ---
        commands = [
            # यूजर-फेसिंग कमांड्स
            BotCommand("start", "Start the bot"),
            BotCommand("help", "Show help menu"),
            BotCommand("topusers", "Show earning leaderboard"),
            BotCommand("clearmydata", "Delete all your data"),
            
            # ग्रुप एडमिन कमांड्स
            BotCommand("settings", "Open group settings menu"),
            BotCommand("setaimode", "Set AI personality mode"),
            BotCommand("addbiolink", "Allow a user's bio link"),
            BotCommand("rembiolink", "Remove a user's bio link"),
            
            # ओनर-ओनली कमांड्स (पब्लिक विजिबल)
            BotCommand("stats", "Check bot statistics (Owner)"),
            BotCommand("broadcast", "Send broadcast to users (Owner)"),
            BotCommand("grp_broadcast", "Send broadcast to groups (Owner)")
        ]
        # --- 🟢 बदलाव 3 का अंत 🟢 ---
        
        await client.set_bot_commands(commands)
        await send_and_auto_delete_reply(message, text="✅ **All bot commands have been set successfully!**")
        logger.info("Bot commands set successfully by owner")
        
    except Exception as e:
        await send_and_auto_delete_reply(message, text=f"❌ **Error setting commands:** {e}")
        logger.error(f"Error setting bot commands: {e}")
    
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
                InlineKeyboardButton("💰 Eᴀ𝗿𝗻𝗶𝗻𝗴 L𝗲𝗮𝗱𝗲𝗿𝗯𝗼𝗮𝗿d", callback_data="show_earning_leaderboard")
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
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        logger.info(f"Attempting to update group info from /start command in chat {message.chat.id}.")
        await update_group_info(message.chat.id, message.chat.title, message.chat.username)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)
    logger.info(f"Group start command processed in chat {message.chat.id}.")


# --- NEW: AI MODE COMMAND (FIXED) ---
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
    
    # 3. Create Buttons
    keyboard_buttons = []
    current_row = []
    
    # Off/Default Button (FIXED)
    status_off = "✅ " if current_ai_mode == "off" else ""
    keyboard_buttons.append([InlineKeyboardButton(f"{status_off}{AI_MODES_MAP['off']['label']}", callback_data="set_ai_mode_off")])

    # Dynamic Mode Buttons (FIXED)
    mode_keys = list(AI_MODES_MAP.keys())
    for mode_key in mode_keys:
        if mode_key != "off":
            mode_data = AI_MODES_MAP[mode_key]
            status = "✅ " if current_ai_mode == mode_key else ""
            button = InlineKeyboardButton(f"{status}{mode_data['label']}", callback_data=f"set_ai_mode_{mode_key}")
            current_row.append(button)
            if len(current_row) == 2:
                keyboard_buttons.append(current_row)
                current_row = []
    
    if current_row:
        keyboard_buttons.append(current_row)

    # Back Button (FIXED to point to main settings)
    keyboard_buttons.append([InlineKeyboardButton("🔙 Sᴇᴛ𝘁𝗶𝗻gꜱ Mᴇ𝗻𝘂", callback_data="settings_back_to_main")]) 
    
    keyboard = InlineKeyboardMarkup(keyboard_buttons)

    # 5. Send Message
    mode_display = AI_MODES_MAP.get(current_ai_mode, AI_MODES_MAP["off"])["label"]
    settings_message = (
        f"👑 **AI Mᴏᴅᴇ Sᴇ𝘁𝘁𝗶𝗻𝗴ꜱ 👑**\n\n"
        "𝗛𝗲𝗹𝗹𝗼 𝗕𝗼𝘀𝘀, 𝘆𝗲𝗵𝗮𝗻 𝘀𝗲 𝗮𝗽𝗽𝗮𝗻𝗮 **AI 𝗽𝗲𝗿𝘀𝗼𝗻𝗮𝗹𝗶𝘁𝘆** 𝘀𝗲𝘁 𝗸𝗮𝗿𝗼.\n"
        "𝗕𝗼𝘁 𝘂𝘀 𝗵𝗶 𝗮𝗻𝗱𝗮𝗮𝘇 𝗺𝗮𝗶𝗻, 𝗯𝗶𝗸𝘂𝗹 𝗿𝗲𝗮𝗹 𝗹𝗮𝗱𝗸𝗶 𝗷𝗮𝗶𝘀𝗲, 𝗯𝗮𝗮𝘁 𝗸𝗮𝗿𝗲𝗴𝗶! 🤩\n\n"
        f"**Cᴜ𝗿𝗿𝗲𝗻𝘁 AI Mᴏ𝗱𝗲:** **{mode_display}**"
    )

    await send_and_auto_delete_reply(
        message,
        text=settings_message,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

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
    punishment_text = punishment_map.get(punishment, "🗑️ Dᴇ𝗹𝗲𝘁𝗲 Mᴇꜱꜱᴀɢᴇ")

    # FIX: Use AI_MODES_MAP for consistent display
    ai_mode_text = AI_MODES_MAP.get(ai_mode, AI_MODES_MAP["off"])["display"]


    # 3. Create the Main Settings Keyboard (Styled Buttons)
    keyboard = InlineKeyboardMarkup(
        [
            # Module Toggles
            [
                InlineKeyboardButton(f"🤖 Bᴏᴛ Cʜᴀ𝘁𝘁𝗶𝗻g: {bot_status}", callback_data="toggle_setting_bot_enabled"),
            ],
            [
                InlineKeyboardButton(f"🔗 L𝗶𝗻𝗸 D𝗲𝗹𝗲𝘁𝗲: {link_status}", callback_data="toggle_setting_linkdel_enabled"),
            ],
            [
                InlineKeyboardButton(f"👤 B𝗶𝗼 L𝗶𝗻𝗸 D𝗲𝗹𝗲𝘁𝗲: {biolink_status}", callback_data="toggle_setting_biolinkdel_enabled"),
            ],
            [
                InlineKeyboardButton(f"🗣️ @Uꜱ𝗲𝗿𝗻𝗮𝗺𝗲 D𝗲𝗹𝗲𝘁𝗲: {username_status}", callback_data="toggle_setting_usernamedel_enabled"),
            ],
            # NEW AI MODE BUTTON
            [
                # FIX: Use the correct callback to open the AI Mode settings
                InlineKeyboardButton(f"✨ AI Mᴏᴅᴇ: {ai_mode_text}", callback_data="open_ai_mode_settings"),
            ],
            # Punishment and Biolink Exception
            [
                InlineKeyboardButton(f"🔨 Dᴇ𝗳𝗮𝘂𝗹𝘁 Pᴜ𝗻𝗶𝘀𝗵𝗺𝗲𝗻𝘁: {punishment_text}", callback_data="open_punishment_settings"),
            ],
            [
                 InlineKeyboardButton("👤 B𝗶𝗼 L𝗶𝗻ᴋ Exᴄᴇᴘᴛ𝗶𝗼𝗻ꜱ 📝", callback_data="open_biolink_exceptions")
            ],
            # Close Button
            [
                InlineKeyboardButton("❌ C𝗹𝗼𝘀𝗲 S𝗲𝘁𝘁𝗶𝗻gꜱ", callback_data="close_settings")
            ]
        ]
    )

    # 4. Send the Settings Message (Translated and styled)
    settings_message = (
        f"⚙️ **𝗚𝗿𝗼𝘂𝗽 𝗦𝗲𝘁𝘁𝗶𝗻𝗴𝘀: {message.chat.title}** 🛠️\n\n"
        "𝗛𝗲𝗹𝗹𝗼, 𝗕𝗼𝘀𝘀! 𝗬𝗼𝘂 𝗰𝗮𝗻 𝗰𝗼𝗻𝘁𝗿𝗼𝗹 𝘁𝗵𝗲 𝗴𝗿𝗼𝘂𝗽 𝗿𝘂𝗹𝗲𝘀 𝗮𝗻𝗱 𝗯𝗼𝘁 𝗳𝘂𝗻𝗰𝘁𝗶𝗼𝗻𝘀 𝗳𝗿𝗼𝗺 𝘁𝗵𝗲 𝗯𝘂𝘁𝘁𝗼𝗻𝘀 𝗯𝗲𝗹𝗼𝘄.\n"
        "**AI Mᴏᴅᴇ:** Bᴏᴛ ᴋɪ ᴘᴇʀsᴏɴᴀʟɪᴛʏ 𝗮𝘂𝗿 𝗷𝗮𝘄𝗮𝗯 ᴅᴇɴᴇ ᴋᴀ 𝘁𝗮𝗿𝗶𝗸𝗮 𝗶𝘀 𝘀𝗲 𝘀𝗲𝘁 𝗵𝗼𝗴𝗮. **Cᴜʀʀ𝗲𝗻𝘁: {ai_mode_text}**\n\n"
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
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await update_group_info(message.chat.id, message.chat.title, message.chat.username)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)
    logger.info(f"Group settings command processed in chat {message.chat.id} by admin {message.from_user.id}.")

@app.on_message(filters.command("addbiolink") & filters.group)
async def add_biolink_command(client: Client, message: Message):
    """Add user to biolink exceptions (NEW FIX)"""
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    # Check admin permission
    if not await is_admin_or_owner(client, message.chat.id, message.from_user.id):
        await send_and_auto_delete_reply(message, text="❌ **Only admins can use this command!**")
        return

    if len(message.command) < 2:
        await send_and_auto_delete_reply(message, text="❌ **Usage:** `/addbiolink <user_id>`")
        return

    try:
        user_id = int(message.command[1])
        
        # Add to biolink exceptions
        biolink_exceptions_collection.update_one(
            {"_id": message.chat.id},
            {"$addToSet": {"user_ids": user_id}},
            upsert=True
        )
        
        await send_and_auto_delete_reply(message, text=f"✅ **User `{user_id}` added to biolink exceptions!**")
        logger.info(f"User {user_id} added to biolink exceptions in chat {message.chat.id}")
        
    except ValueError:
        await send_and_auto_delete_reply(message, text="❌ **Invalid user ID!** Please provide a numeric user ID.")
    except Exception as e:
        await send_and_auto_delete_reply(message, text=f"❌ **Error:** {e}")
        logger.error(f"Error adding biolink exception: {e}")
    
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await update_group_info(message.chat.id, message.chat.title, message.chat.username)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)


@app.on_message(filters.command("rembiolink") & filters.group)
async def remove_biolink_command(client: Client, message: Message):
    """Remove user from biolink exceptions (NEW FIX)"""
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    # Check admin permission
    if not await is_admin_or_owner(client, message.chat.id, message.from_user.id):
        await send_and_auto_delete_reply(message, text="❌ **Only admins can use this command!**")
        return

    if len(message.command) < 2:
        await send_and_auto_delete_reply(message, text="❌ **Usage:** `/rembiolink <user_id>`")
        return

    try:
        user_id = int(message.command[1])
        
        # Remove from biolink exceptions
        result = biolink_exceptions_collection.update_one(
            {"_id": message.chat.id},
            {"$pull": {"user_ids": user_id}}
        )

        if result.modified_count > 0:
            await send_and_auto_delete_reply(message, text=f"✅ **User `{user_id}` removed from biolink exceptions!**")
            logger.info(f"User {user_id} removed from biolink exceptions in chat {message.chat.id}")
        else:
            await send_and_auto_delete_reply(message, text=f"❌ **User `{user_id}` was not found in biolink exceptions!**")
        
    except ValueError:
        await send_and_auto_delete_reply(message, text="❌ **Invalid user ID!** Please provide a numeric user ID.")
    except Exception as e:
        await send_and_auto_delete_reply(message, text=f"❌ **Error:** {e}")
        logger.error(f"Error removing biolink exception: {e}")

    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await update_group_info(message.chat.id, message.chat.title, message.chat.username)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)
