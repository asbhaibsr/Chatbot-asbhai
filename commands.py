# commands.py

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatType, ChatMemberStatus, ParseMode
from pyrogram.errors import FloodWait, UserIsBlocked, ChatWriteForbidden, PeerIdInvalid, RPCError
import asyncio
import os
import re
import sys
from datetime import datetime

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

@app.on_message(filters.command("start") & filters.private)
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
            [InlineKeyboardButton("➕ मुझे ग्रुप में जोड़ें", url=f"https://t.me/{client.me.username}?startgroup=true")],
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

@app.on_message(filters.command("start") & filters.group)
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
            [InlineKeyboardButton("➕ मुझे ग्रुप में जोड़ें", url=f"https://t.me/{client.me.username}?startgroup=true")],
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
        await send_and_auto_delete_reply(message, text="😢 अब तक कोई भी उपयोगकर्ता लीडरबोर्ड पर नहीं है! सक्रिय होकर पहले बनें! ✨\n\n**Powered By:** @asbhaibsr", parse_mode=ParseMode.MARKDOWN)
        return

    earning_messages = ["👑 **Top Active Users - ✨ VIP Leaderboard! ✨** 👑\n\n"]
    prizes = {
        1: "💰 ₹50", 2: "💸 ₹30", 3: "🎁 ₹20",
        4: f"🎬 @{ASFILTER_BOT_USERNAME} का 1 हफ़्ते का प्रीमियम प्लान",
        5: f"🎬 @{ASFILTER_BOT_USERNAME} का 3 दिन का प्रीमियम प्लान"
    }

    for i, user in enumerate(top_users[:5]):
        rank = i + 1
        user_name = user.get('first_name', 'Unknown User')
        username_str = f"@{user.get('username')}" if user.get('username') else f"ID: `{user.get('user_id')}`"
        message_count = user.get('message_count', 0)
        prize_str = prizes.get(rank, "🏅 कोई पुरस्कार नहीं")

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
                    try:
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
            await asyncio.sleep(0.1)
        except (UserIsBlocked, ChatWriteForbidden, PeerIdInvalid) as client_error:
            failed_count += 1
            logger.warning(f"Skipping broadcast to {chat_id} due to client error (blocked/forbidden/invalid): {client_error}")
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
            await send_and_auto_delete_reply(message, text="Aapne galat Group ID format diya hai. Group ID `-100...` se shuru hoti hai. Thoda dhyaan se! 😊 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
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
        await send_and_auto_delete_reply(message, text=f"Jaisa hukum mere aaka! 🧞‍♀️ Maine '{search_query}' se milte-julte **{deleted_count}** **text messages** ko dhoondh ke delete kar diya. Ab woh history ka हिस्सा nahi raha! ✨ (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
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
        await send_and_auto_delete_reply(message, text=f"Jaisa hukum mere aaka! 🧞‍♀️ Maine **{percentage}%** stickers ko dhoondh ke delete kar diya. Total **{deleted_count}** stickers removed. Ab woh history ka हिस्सा नहीं रहा! ✨ (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Deleted {deleted_count} stickers based on {percentage}% request. (Code by @asbhaibsr)")
    else:
        await send_and_auto_delete_reply(message, text="Umm, mujhe tumhare is query se koi **sticker** mila hi nahi apne database mein. Ya toh sticker ही nahi hai, ya percentage bahot kam hai! 🤔 (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)

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
        await send_and_auto_delete_reply(message, text="माफ़ करना, ये कमांड सिर्फ़ मेरे बॉस (एडमिन) ही यूज़ कर सकते हैं! 🤷‍♀️", parse_mode=ParseMode.MARKDOWN)
        return

    if len(message.command) < 2:
        current_status_doc = group_tracking_collection.find_one({"_id": message.chat.id})
        current_status = current_status_doc.get("linkdel_enabled", False) if current_status_doc else False
        status_text = "चालू है (ON)" if current_status else "बंद है (OFF)"
        await send_and_auto_delete_reply(message, text=f"मेरी 'लिंक जादू' की छड़ी अभी **{status_text}** है. इसे कंट्रोल करने के लिए `/linkdel on` या `/linkdel off` यूज़ करो. 😉", parse_mode=ParseMode.MARKDOWN)
        return

    action = message.command[1].lower()
    if action == "on":
        group_tracking_collection.update_one({"_id": message.chat.id}, {"$set": {"linkdel_enabled": True}}, upsert=True)
        await send_and_auto_delete_reply(message, text="ही ही ही! 🤭 अब कोई भी शरारती लिंक भेजेगा, तो मैं उसे जादू से गायब कर दूंगी! 🪄 ग्रुप को एकदम साफ़-सुथरा रखना है न! 😉", parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Link deletion enabled in group {message.chat.id} by admin {message.from_user.id}.")
    elif action == "off":
        group_tracking_collection.update_one({"_id": message.chat.id}, {"$set": {"linkdel_enabled": False}}, upsert=True)
        await send_and_auto_delete_reply(message, text="ठीक है, ठीक है! मैंने अपनी 'लिंक जादू' की छड़ी रख दी है! 😇 अब आप जो चाहे लिंक भेज सकते हैं! पर ध्यान से, ओके?", parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Link deletion disabled in group {message.chat.id} by admin {message.from_user.id}.")
    else:
        await send_and_auto_delete_reply(message, text="उम्म... मुझे समझ नहीं आया! 😕 `/linkdel on` या `/linkdel off` यूज़ करो, प्लीज़! ✨", parse_mode=ParseMode.MARKDOWN)
    await store_message(message)

@app.on_message(filters.command("biolinkdel") & filters.group)
async def toggle_biolinkdel_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    if not await is_admin_or_owner(client, message.chat.id, message.from_user.id):
        await send_and_auto_delete_reply(message, text="माफ़ करना, ये कमांड सिर्फ़ मेरे बॉस (एडमिन) ही यूज़ कर सकते हैं! 🤷‍♀️", parse_mode=ParseMode.MARKDOWN)
        return

    if len(message.command) < 2:
        current_status_doc = group_tracking_collection.find_one({"_id": message.chat.id})
        current_status = current_status_doc.get("biolinkdel_enabled", False) if current_status_doc else False
        status_text = "चालू है (ON)" if current_status else "बंद है (OFF)"
        await send_and_auto_delete_reply(message, text=f"मेरी 'बायो-लिंक पुलिस' अभी **{status_text}** है. इसे कंट्रोल करने के लिए `/biolinkdel on` या `/biolinkdel off` यूज़ करो. 👮‍♀️", parse_mode=ParseMode.MARKDOWN)
        return

    action = message.command[1].lower()
    if action == "on":
        group_tracking_collection.update_one({"_id": message.chat.id}, {"$set": {"biolinkdel_enabled": True}}, upsert=True)
        await send_and_auto_delete_reply(message, text="हम्म... 😼 अब से जो भी **यूज़र अपनी बायो में `t.me` या `http/https` लिंक रखेगा**, मैं उसके **मैसेज को चुपचाप हटा दूंगी!** (अगर उसे `/biolink` से छूट नहीं मिली है). ग्रुप में कोई मस्ती नहीं!🤫", parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Biolink deletion enabled in group {message.chat.id} by admin {message.from_user.id}.")
    elif action == "off":
        group_tracking_collection.update_one({"_id": message.chat.id}, {"$set": {"biolinkdel_enabled": False}}, upsert=True)
        await send_and_auto_delete_reply(message, text="ओके डार्लिंग्स! 😇 अब मैं यूज़र्स की बायो में `t.me` और `http/https` लिंक्स को चेक करना बंद कर रही हूँ! सब फ्री-फ्री! 🎉", parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Biolink deletion disabled in group {message.chat.id} by admin {message.from_user.id}.")
    else:
        await send_and_auto_delete_reply(message, text="उम्म... मुझे समझ नहीं आया! 😕 `/biolinkdel on` या `/biolinkdel off` यूज़ करो, प्लीज़! ✨", parse_mode=ParseMode.MARKDOWN)
    await store_message(message)

@app.on_message(filters.command("biolink") & filters.group)
async def allow_biolink_user_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    if not await is_admin_or_owner(client, message.chat.id, message.from_user.id):
        await send_and_auto_delete_reply(message, text="माफ़ करना, ये कमांड सिर्फ़ मेरे बॉस (एडमिन) ही यूज़ कर सकते हैं! 🤷‍♀️", parse_mode=ParseMode.MARKDOWN)
        return

    if len(message.command) < 2:
        await send_and_auto_delete_reply(message, text="किस यूज़र को बायो-लिंक की छूट देनी है? मुझे उसकी User ID दो ना, जैसे: `/biolink 123456789` या `/biolink remove 123456789`! 😉", parse_mode=ParseMode.MARKDOWN)
        return

    action_or_user_id = message.command[1].lower()
    target_user_id = None

    if action_or_user_id == "remove" and len(message.command) > 2:
        try:
            target_user_id = int(message.command[2])
            biolink_exceptions_collection.delete_one({"_id": target_user_id})
            await send_and_auto_delete_reply(message, text=f"ओके! ✨ यूज़र `{target_user_id}` को अब बायो में लिंक रखने की छूट नहीं मिलेगी! बाय-बाय परमिशन! 👋", parse_mode=ParseMode.MARKDOWN)
            logger.info(f"Removed user {target_user_id} from biolink exceptions in group {message.chat.id}.")
        except ValueError:
            await send_and_auto_delete_reply(message, text="उम्म, गलत यूज़रआईडी! 🧐 यूज़रआईडी एक नंबर होती है. फिर से ट्राई करो, प्लीज़! 😉", parse_mode=ParseMode.MARKDOWN)
    else:
        try:
            target_user_id = int(action_or_user_id)
            biolink_exceptions_collection.update_one(
                {"_id": target_user_id},
                {"$set": {"allowed_by_admin": True, "added_on": datetime.now(), "credit": "by @asbhaibsr"}},
                upsert=True
            )
            await send_and_auto_delete_reply(message, text=f"याय! 🎉 मैंने यूज़र `{target_user_id}` को स्पेशल परमिशन दे दी है! अब ये **अपनी बायो में `t.me` या `http/https` लिंक्स** रख पाएंगे और उनके मैसेज डिलीट नहीं होंगे! क्यूंकि एडमिन ने बोला, तो बोला!👑", parse_mode=ParseMode.MARKDOWN)
            logger.info(f"Added user {target_user_id} to biolink exceptions in group {message.chat.id}.")
        except ValueError:
            await send_and_auto_delete_reply(message, text="उम्म, गलत यूज़रआईडी! 🧐 यूज़रआईडी एक नंबर होती है. फिर से ट्राई करो, प्लीज़! 😉", parse_mode=ParseMode.MARKDOWN)
    await store_message(message)

@app.on_message(filters.command("usernamedel") & filters.group)
async def toggle_usernamedel_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    if not await is_admin_or_owner(client, message.chat.id, message.from_user.id):
        await send_and_auto_delete_reply(message, text="माफ़ करना, ये कमांड सिर्फ़ मेरे बॉस (एडमिन) ही यूज़ कर सकते हैं! 🤷‍♀️", parse_mode=ParseMode.MARKDOWN)
        return

    if len(message.command) < 2:
        current_status_doc = group_tracking_collection.find_one({"_id": message.chat.id})
        current_status = current_status_doc.get("usernamedel_enabled", False) if current_status_doc else False
        status_text = "चालू है (ON)" if current_status else "बंद है (OFF)"
        await send_and_auto_delete_reply(message, text=f"मेरी '@' टैग पुलिस अभी **{status_text}** है. इसे कंट्रोल करने के लिए `/usernamedel on` या `/usernamedel off` यूज़ करो.🚨", parse_mode=ParseMode.MARKDOWN)
        return

    action = message.command[1].lower()
    if action == "on":
        group_tracking_collection.update_one({"_id": message.chat.id}, {"$set": {"usernamedel_enabled": True}}, upsert=True)
        await send_and_auto_delete_reply(message, text="चीं-चीं! 🐦 अब से कोई भी `@` करके किसी को भी परेशान नहीं कर पाएगा! जो करेगा, उसका मैसेज मैं फट से उड़ा दूंगी!💨 मुझे डिस्टर्बेंस पसंद नहीं! 😠", parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Username deletion enabled in group {message.chat.id} by admin {message.from_user.id}.")
    elif action == "off":
        group_tracking_collection.update_one({"_id": message.chat.id}, {"$set": {"usernamedel_enabled": False}}, upsert=True)
        await send_and_auto_delete_reply(message, text="ठीक है! आज से मेरी @ वाली आंखें बंद! 😴 अब आप जो चाहे @ करो! पर ज़्यादा तंग मत करना किसी को! 🥺", parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Username deletion disabled in group {message.chat.id} by admin {message.from_user.id}.")
    else:
        await send_and_auto_delete_reply(message, text="उम्म... मुझे समझ नहीं आया! 😕 `/usernamedel on` या `/usernamedel off` यूज़ करो, प्लीज़! ✨", parse_mode=ParseMode.MARKDOWN)
    await store_message(message)

@app.on_message(filters.command("clearall") & filters.private)
async def clear_all_dbs_command(client: Client, message: Message):
    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    if message.from_user.id != OWNER_ID:
        await send_and_auto_delete_reply(message, text="माफ़ करना, ये कमांड सिर्फ़ मेरे बॉस के लिए है। 🚫", parse_mode=ParseMode.MARKDOWN)
        return

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("हाँ, डिलीट करें ⚠️", callback_data='confirm_clearall_dbs'),
                InlineKeyboardButton("नहीं, रहने दें ✅", callback_data='cancel_clearall_dbs')
            ]
        ]
    )

    await send_and_auto_delete_reply(
        message,
        text="⚠️ **चेतावनी:** क्या आप वाकई अपनी सभी MongoDB डेटाबेस (Messages, Buttons, Tracking) का **सारा डेटा** डिलीट करना चाहते हैं?\n\n"
             "यह कार्रवाई **अपरिवर्तनीय (irreversible)** है और आपका सारा डेटा हमेशा के लिए हट जाएगा।\n\n"
             "सोच समझकर चुनें!",
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
        await send_and_auto_delete_reply(message, text="मुझे पता नहीं चल रहा कि किसका डेटा डिलीet करना है। 😕", parse_mode=ParseMode.MARKDOWN)
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
                await send_and_auto_delete_reply(message, text=f"वाह! ✨ मैंने आपकी `{deleted_messages_count}` बातचीत के मैसेज और अर्निंग डेटा डिलीट कर दिए हैं। अब आप बिल्कुल फ्रेश हो! 😊", parse_mode=ParseMode.MARKDOWN)
                logger.info(f"User {target_user_id} successfully cleared their data.")
            else:
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
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.id)

