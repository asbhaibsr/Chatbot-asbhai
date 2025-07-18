import os
import asyncio
import sys
import re
import random
import logging

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatType, ChatMemberStatus, ParseMode

from datetime import datetime, timedelta

# Assume these are passed or imported from main
# For a standalone file, you'd need to pass these or re-import/re-initialize
# For simplicity, we'll assume they are available or passed as arguments.
messages_collection = None
buttons_collection = None
group_tracking_collection = None
user_tracking_collection = None
earning_tracking_collection = None
reset_status_collection = None
biolink_exceptions_collection = None
owner_taught_responses_collection = None
conversational_learning_collection = None

OWNER_ID = None
UPDATE_CHANNEL_USERNAME = None
ASBHAI_USERNAME = None
ASFILTER_BOT_USERNAME = None
BOT_PHOTO_URL = None
REPO_LINK = None
URL_PATTERN = None # from main for link detection regex

# Cooldown dictionaries and functions from main
user_cooldowns = {}
COMMAND_COOLDOWN_TIME = 3 # seconds (for commands like /start, /topusers)

# Logger for this module
logger = logging.getLogger(__name__)

def initialize_bot_commands(
    msg_coll, btn_coll, grp_track_coll, user_track_coll, earn_track_coll,
    reset_stat_coll, biolink_exc_coll, owner_taught_coll, conv_learn_coll,
    owner_id, update_channel, asbhai_username, asfilter_username, bot_photo, repo_link, url_pattern_obj
):
    """Initializes collections and constants for this module."""
    global messages_collection, buttons_collection, group_tracking_collection, user_tracking_collection, \
           earning_tracking_collection, reset_status_collection, biolink_exceptions_collection, \
           owner_taught_responses_collection, conversational_learning_collection, \
           OWNER_ID, UPDATE_CHANNEL_USERNAME, ASBHAI_USERNAME, ASFILTER_BOT_USERNAME, \
           BOT_PHOTO_URL, REPO_LINK, URL_PATTERN

    messages_collection = msg_coll
    buttons_collection = btn_coll
    group_tracking_collection = grp_track_coll
    user_tracking_collection = user_track_coll
    earning_tracking_collection = earn_track_coll
    reset_status_collection = reset_stat_coll
    biolink_exceptions_collection = biolink_exc_coll
    owner_taught_responses_collection = owner_taught_coll
    conversational_learning_collection = conv_learn_coll

    OWNER_ID = owner_id
    UPDATE_CHANNEL_USERNAME = update_channel
    ASBHAI_USERNAME = asbhai_username
    ASFILTER_BOT_USERNAME = asfilter_username
    BOT_PHOTO_URL = bot_photo
    REPO_LINK = repo_link
    URL_PATTERN = url_pattern_obj

# Import utility functions from main (or redefine them if truly standalone)
# For this structure, we'll assume they are globally available or properly imported/passed.
# These functions would ideally be in a `utils.py` file and imported into both `main.py` and `bot_commands.py`
from main import is_on_command_cooldown, update_command_cooldown, send_and_auto_delete_reply, \
                   store_message, update_group_info, update_user_info, is_admin_or_owner, \
                   delete_after_delay_for_message
from earning_system import get_top_earning_users, reset_monthly_earnings_manual


@Client.on_message(filters.command("start") & filters.private)
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
    # Store command usage, not for learning
    await store_message(message)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)
    logger.info(f"Private start command processed for user {message.from_user.id}. (Code by @asbhaibsr)")

@Client.on_message(filters.command("start") & filters.group)
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
    # Store command usage, not for learning
    await store_message(message)
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        logger.info(f"Attempting to update group info from /start command in chat {message.chat.id}.")
        await update_group_info(message.chat.id, message.chat.title, message.chat.username)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)
    logger.info(f"Group start command processed in chat {message.chat.id}. (Code by @asbhaibsr)")


@Client.on_callback_query()
async def callback_handler(client, callback_query):
    # Answer the callback query immediately to remove loading state
    await callback_query.answer()

    if callback_query.data == "buy_git_repo":
        await send_and_auto_delete_reply(
            callback_query.message,
            text=f"🤩 अगर आपको मेरे जैसा खुद का bot बनवाना है, तो आपको ₹500 देने होंगे. इसके लिए **@{ASBHAI_USERNAME}** से contact करें और unhe bataiye ki aapko is bot ka code chahiye banwane ke liye. Jaldi karo, deals hot hain! 💸\n\n**Owner:** @asbhaibsr\n**Updates:** @asbhai_bsr\n**Support:** @aschat_group",
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
        await top_users_command(client, callback_query.message) # Pass the original message object
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
            "Main ek self-learning bot hoon jo conversations se seekhti hai. Aap groups mein ya mujhse private mein baat kar sakte hain, aur main aapke messages ko yaad rakhti hoon. Jab koi user similar baat karta hai, toh main usse seekhe hue reply deti hoon.\n\n"
            "**✨ Meri Commands:**\n"
            "• `/start`: Mujhse baat shuru karne ke liye.\n"
            "• `/help`: Yeh menu dekhne ke liye (jo aap abhi dekh rahe hain!).\n"
            "• `/topusers`: Sabse active users ka leaderboard dekhne ke liye.\n"
            "• `/clearmydata`: Apni saari baatein (jo maine store ki hain) delete karne ke liye.\n"
            "• `/chat on/off`: (Sirf Group Admins ke liye) Group mein meri messages band/chalu karne ke liye.\n"
            "• `/groups`: (Sirf Owner ke liye) Jin groups mein main hoon, unki list dekhne ke liye.\n"
            "• `/stats check`: Bot ke statistics dekhne ke liye.\n"
            "• `/cleardata <percentage>`: (Sirf Owner ke liye) Database se data delete karne ke liye.\n"
            "• `/deletemessage <content>`: (Sirf Owner ke liye) Specific **text message** delete karne ke liye.\n" # UPDATED HELP TEXT
            "• `/delsticker <percentage>`: (Sirf Owner ke liye) Database se **stickers** delete karne ke liye (e.g., `10%`, `20%`, `40%`).\n" # NEW HELP TEXT
            "• `/clearearning`: (Sirf Owner ke liye) Earning data reset karne ke liye.\n"
            "• `/clearall`: (Sirf Owner ke liye) Saara database (3 DBs) clear karne ke liye. **(Dhyan se!)**\n"
            "• `/leavegroup <group_id>`: (Sirf Owner ke liye) Kisi group ko chhodne ke liye.\n"
            "• `/broadcast <message>`: (Sirf Owner ke liye) Sabhi groups mein message bhejne ke liye.\n"
            "• `/restart`: (Sirf Owner ke liye) Bot ko restart karne ke liye.\n"
            "• `/linkdel on/off`: (Sirf Group Admins ke liye) Group mein **sabhi prakar ke links** delete/allow karne ke liye.\n"
            "• `/biolinkdel on/off`: (Sirf Group Admins ke liye) Group mein **users ke bio mein `t.me` aur `http/https` links** wale messages ko delete/allow karne ke liye.\n"
            "• `/biolink <userid>`: (Sirf Group Admins ke liye) `biolinkdel` on hone par bhi kisi user ko **bio mein `t.me` aur `http/https` links** रखने की permission dene ke liye.\n"
            "• `/usernamedel on/off`: (Sirf Group Admins ke liye) Group mein **'@' mentions** allow ya delete karne ke liye.\n\n"
            "**🔗 Mera Code (GitHub Repository):**\n"
            f"[**{REPO_LINK}**]({REPO_LINK})\n\n"
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
            "यहाँ बताया गया है कि आप मेरे साथ कैसे कमाई कर सकते हैं:\n\n"
            "**1. सक्रिय रहें (Be Active):**\n"
            "   • आपको ग्रुप में **वास्तविक और सार्थक बातचीत** करनी होगी।\n"
            "   • बेतरतीब मैसेज, स्पैमिंग, या सिर्फ़ इमोजी भेजने से आपकी रैंकिंग नहीं बढ़ेगी और आप अयोग्य भी हो सकते हैं।\n"
            "   • जितनी ज़्यादा अच्छी बातचीत, उतनी ज़्यादा कमाई के अवसर!\n\n"
            "**2. क्या करें, क्या न करें (Do's and Don'ts):**\n"
            "   • **करें:** सवालों के जवाब दें, चर्चा में भाग लें, नए विषय शुरू करें, अन्य सदस्यों के साथ इंटरैक्ट करें।\n"
            "   • **न करें:** बार-बार एक ही मैसेज भेजें, सिर्फ़ स्टिकर या GIF भेजें, असंबद्ध सामग्री पोस्ट करें, या ग्रुप के नियमों का उल्लंघन करें।\n\n"
            "**3. कमाई का समय (Earning Period):**\n"
            "   • कमाई हर **महीने** के पहले दिन रीसेट होगी। इसका मतलब है कि हर महीने आपके पास टॉप पर आने का एक नया मौका होगा!\n\n"
            "**4. अयोग्य होना (Disqualification):**\n"
            "   • यदि आप स्पैमिंग करते हुए पाए जाते हैं, या किसी भी तरह से सिस्टम का दुरुपयोग करने की कोशिश करते हैं, तो आपको लीडरबोर्ड से हटा दिया जाएगा और आप भविष्य की कमाई के लिए अयोग्य घोषित हो सकते हैं।\n"
            "   • ग्रुप के नियमों का पालन करना अनिवार्य है।\n\n"
            "**5. विथड्रावल (Withdrawal):**\n"
            "   • विथड्रावल हर महीने के **पहले हफ़्ते** में होगा।\n"
            "   • अपनी कमाई निकालने के लिए, आपको मुझे `@asbhaibsr` पर DM (डायरेक्ट मैसेज) करना होगा।\n\n"
            "**शुभकामनाएँ!** 🍀\n"
            "मुझे आशा है कि आप सक्रिय रहेंगे और हमारी कम्युनिटी में योगदान देंगे।\n\n"
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

@Client.on_message(filters.command("topusers") & (filters.private | filters.group))
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
    # Store command usage, not for learning
    await store_message(message)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)
    logger.info(f"Top users command processed for user {message.from_user.id} in chat {message.chat.id}. (Code by @asbhaibsr)")

@Client.on_message(filters.command("broadcast") & filters.private)
async def broadcast_command(client: Client, message: Message):
    from pyrogram.errors import FloodWait, UserIsBlocked, ChatWriteForbidden, PeerIdInvalid, RPCError

    if is_on_command_cooldown(message.from_user.id):
        return
    update_command_cooldown(message.from_user.id)

    if message.from_user.id != OWNER_ID:
        await send_and_auto_delete_reply(message, text="Oops! Sorry sweetie, yeh command sirf mere boss ke liye hai. 🤷‍♀️ (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return

    # Check if a reply is present (for sticker/photo broadcast) or text is present
    if not message.reply_to_message and not (len(message.command) > 1):
        await send_and_auto_delete_reply(message, text="Hey, broadcast karne ke liye kuch likho ya kisi message/sticker/photo ko reply karo toh sahi! 🙄 Jaise: `/broadcast Aapka message yahan` (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        return

    broadcast_text = None
    broadcast_photo = None
    broadcast_sticker = None
    broadcast_video = None
    broadcast_document = None

    if message.reply_to_message:
        replied_msg = message.reply_to_message
        if replied_msg.text:
            broadcast_text = replied_msg.text
        elif replied_msg.photo:
            broadcast_photo = replied_msg.photo.file_id
            broadcast_text = replied_msg.caption # Include caption if available
        elif replied_msg.sticker:
            broadcast_sticker = replied_msg.sticker.file_id
        elif replied_msg.video:
            broadcast_video = replied_msg.video.file_id
            broadcast_text = replied_msg.caption
        elif replied_msg.document:
            broadcast_document = replied_msg.document.file_id
            broadcast_text = replied_msg.caption
    elif len(message.command) > 1:
        # Use the raw text after the command to preserve newlines
        broadcast_text = message.text.split(None, 1)[1]

    if not any([broadcast_text, broadcast_photo, broadcast_sticker, broadcast_video, broadcast_document]):
        await send_and_auto_delete_reply(message, text="Broadcast karne ke liye koi content nahi mila. Please text, sticker, photo, video, ya document bhejo ya reply karo. 🤔", parse_mode=ParseMode.MARKDOWN)
        return

    group_chat_ids = [g["_id"] for g in group_tracking_collection.find({})]
    private_chat_ids = [u["_id"] for u in user_tracking_collection.find({})]

    all_target_ids = list(set(group_chat_ids + private_chat_ids))

    # Remove the owner's private chat from the broadcast targets to avoid sending twice
    if OWNER_ID in all_target_ids:
        all_target_ids.remove(OWNER_ID)

    total_targets = len(all_target_ids)
    sent_count = 0
    failed_count = 0

    status_message = await message.reply_text(f"🚀 **Broadcast Shuru!** 🚀\n"
                                             f"Cool, main **{total_targets}** chats par message bhej rahi hoon.\n"
                                             f"Sent: **0** / Failed: **0** (Total: {total_targets})",
                                             parse_mode=ParseMode.MARKDOWN)

    logger.info(f"Starting broadcast to {total_targets} chats (groups and users). (Broadcast by @asbhaibsr)")

    for i, chat_id in enumerate(all_target_ids):
        try:
            if broadcast_photo:
                await client.send_photo(chat_id, broadcast_photo, caption=broadcast_text, parse_mode=ParseMode.MARKDOWN)
            elif broadcast_sticker:
                await client.send_sticker(chat_id, broadcast_sticker)
            elif broadcast_video:
                await client.send_video(chat_id, broadcast_video, caption=broadcast_text, parse_mode=ParseMode.MARKDOWN)
            elif broadcast_document:
                await client.send_document(chat_id, broadcast_document, caption=broadcast_text, parse_mode=ParseMode.MARKDOWN)
            elif broadcast_text:
                await client.send_message(chat_id, broadcast_text, parse_mode=ParseMode.MARKDOWN)

            sent_count += 1
            # Update status message every 10 messages or at the end
            if (i + 1) % 10 == 0 or (i + 1) == total_targets:
                try:
                    await status_message.edit_text(f"🚀 **Broadcast Progress...** 🚀\n"
                                                  f"Cool, main **{total_targets}** chats par message bhej rahi hoon.\n"
                                                  f"Sent: **{sent_count}** / Failed: **{failed_count}** (Total: {total_targets})",
                                                  parse_mode=ParseMode.MARKDOWN)
                except Exception as edit_e:
                    logger.warning(f"Failed to edit broadcast status message: {edit_e}")
            await asyncio.sleep(0.1) # Small delay to avoid flood waits
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

    final_message = (f"🎉 **Broadcast Complete!** 🎉\n"
                     f"Total chats targeted: **{total_targets}**\n"
                     f"Successfully sent: **{sent_count}** messages ✨\n"
                     f"Failed to send: **{failed_count}** messages 💔\n\n"
                     f"Koi nahi, next time! 😉 (System by @asbhaibsr)")

    try:
        await status_message.edit_text(final_message, parse_mode=ParseMode.MARKDOWN)
    except Exception as final_edit_e:
        logger.error(f"Failed to send final broadcast summary: {final_edit_e}. Sending as new message instead.")
        await send_and_auto_delete_reply(message, text=final_message, parse_mode=ParseMode.MARKDOWN)

    # Store command usage, not for learning
    await store_message(message)
    logger.info(f"Broadcast command processed by owner {message.from_user.id}. (Code by @asbhaibsr)")

@Client.on_message(filters.command("stats") & filters.private)
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
        f"• Owner-taught patterns: **{total_owner_taught}** unique patterns!\n" # NEW STAT
        f"• Conversational patterns learned: **{total_conversational_learned}** unique patterns!\n\n" # NEW STAT
        f"**Powered By:** @asbhaibsr\n**Updates:** @asbhai_bsr\n**Support:** @aschat_group"
    )
    await send_and_auto_delete_reply(message, text=stats_text, parse_mode=ParseMode.MARKDOWN)
    # Store command usage, not for learning
    await store_message(message)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)
    logger.info(f"Private stats command processed for user {message.from_user.id}. (Code by @asbhaibsr)")

@Client.on_message(filters.command("stats") & filters.group)
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
        f"• Owner-taught patterns: **{total_owner_taught}** unique patterns!\n" # NEW STAT
        f"• Conversational patterns learned: **{total_conversational_learned}** unique patterns!\n\n" # NEW STAT
        f"**Powered By:** @asbhaibsr\n**Updates:** @asbhai_bsr\n**Support:** @aschat_group"
    )
    await send_and_auto_delete_reply(message, text=stats_text, parse_mode=ParseMode.MARKDOWN)
    # Store command usage, not for learning
    await store_message(message)
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await update_group_info(message.chat.id, message.chat.title, message.chat.username)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)

# --- Group Management Commands ---

@Client.on_message(filters.command("groups") & filters.private)
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
    # Store command usage, not for learning
    await store_message(message)
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)
    logger.info(f"Groups list command processed by owner {message.from_user.id}. (Code by @asbhaibsr)")

@Client.on_message(filters.command("leavegroup") & filters.private)
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
        messages_collection.delete_many({"chat_id": group_id}) # Clear old general messages
        # NEW: Clear learning data associated with this group
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

    # Store command usage, not for learning
    await store_message(message)
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)

# --- New Commands ---

@Client.on_message(filters.command("cleardata") & filters.private)
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

    # NEW: Prune ALL learning collections by percentage
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
        # Find _id of documents to delete based on oldest timestamp
        for doc in owner_taught_responses_collection.find({}).sort("responses.timestamp", 1).limit(docs_to_delete_owner): # Sort by nested timestamp
            oldest_owner_taught_ids.append(doc['_id'])
        if oldest_owner_taught_ids:
            deleted_count_owner_taught = owner_taught_responses_collection.delete_many({"_id": {"$in": oldest_owner_taught_ids}}).deleted_count


    if total_conversational > 0:
        docs_to_delete_conv = int(total_conversational * (percentage / 100))
        oldest_conv_ids = []
        # Find _id of documents to delete based on oldest timestamp
        for doc in conversational_learning_collection.find({}).sort("responses.timestamp", 1).limit(docs_to_delete_conv): # Sort by nested timestamp
            oldest_conv_ids.append(doc['_id'])
        if oldest_conv_ids:
            deleted_count_conversational = conversational_learning_collection.delete_many({"_id": {"$in": oldest_conv_ids}}).deleted_count

    total_deleted = deleted_count_old + deleted_count_owner_taught + deleted_count_conversational

    if total_deleted > 0:
        await send_and_auto_delete_reply(message, text=f"Wow! 🤩 Maine aapka **{percentage}%** data successfully delete kar diya! Total **{total_deleted}** entries (Old: {deleted_count_old}, Owner-Taught: {deleted_count_owner_taught}, Conversational: {deleted_count_conversational}) clean ho gayi. Ab main thodi light feel kar rahi hoon. ✨ (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Cleared {total_deleted} messages across collections based on {percentage}% request. (Code by @asbhaibsr)")
    else:
        await send_and_auto_delete_reply(message, text="Umm, kuch delete karne ke liye mila hi nahi. Lagta hai tumne pehle hi sab clean kar diya hai! 🤷‍♀️ (Code by @asbhaibsr)", parse_mode=ParseMode.MARKDOWN)

    # Store command usage, not for learning
    await store_message(message)
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)

@Client.on_message(filters.command("deletemessage") & filters.private)
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

    # NEW: Only delete TEXT messages based on content from all learning collections
    if search_query:
        # Delete from old messages collection
        delete_result_old = messages_collection.delete_many({"type": "text", "content": {"$regex": f".*{re.escape(search_query)}.*", "$options": "i"}})
        deleted_count += delete_result_old.deleted_count

        # Delete from owner_taught_responses collection (both trigger and specific responses)
        # Delete entire documents where the trigger matches
        delete_result_owner_taught_trigger = owner_taught_responses_collection.delete_many({"trigger": {"$regex": f"^{re.escape(search_query)}$", "$options": "i"}})
        deleted_count += delete_result_owner_taught_trigger.deleted_count

        # Pull responses where content matches (leaving the trigger if other responses exist)
        owner_taught_pull_result = owner_taught_responses_collection.update_many(
            {"responses.content": {"$regex": f".*{re.escape(search_query)}.*", "$options": "i"}},
            {"$pull": {"responses": {"content": {"$regex": f".*{re.escape(search_query)}.*", "$options": "i"}}}}
        )
        deleted_count += owner_taught_pull_result.modified_count

        # Delete from conversational_learning collection (both trigger and specific responses)
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

    # Store command usage, not for learning
    await store_message(message)
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)


@Client.on_message(filters.command("delsticker") & filters.private) # NEW COMMAND
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

    # Delete from old messages collection
    total_stickers_old = messages_collection.count_documents({"type": "sticker"})
    if total_stickers_old > 0:
        stickers_to_delete_old = int(total_stickers_old * (percentage / 100))
        sticker_ids_to_delete = []
        for s in messages_collection.find({"type": "sticker"}).sort("timestamp", 1).limit(stickers_to_delete_old):
            sticker_ids_to_delete.append(s['_id'])
        if sticker_ids_to_delete:
            deleted_count += messages_collection.delete_many({"_id": {"$in": sticker_ids_to_delete}}).deleted_count

    # Delete from owner_taught_responses (if any response is a sticker)
    # Pull only the sticker responses, don't delete the whole pattern if other responses exist
    owner_taught_pull_result = owner_taught_responses_collection.update_many(
        {"responses.type": "sticker"},
        {"$pull": {"responses": {"type": "sticker"}}}
    )
    # Count how many individual stickers were removed across all matching documents
    # This is an approximation as modified_count only tells how many documents were updated.
    # To get exact number of stickers, we'd need to manually count before and after for each document.
    # For now, let's just count modified documents.
    deleted_count += owner_taught_pull_result.modified_count

    # Delete from conversational_learning (if any response is a sticker)
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

    # Store command usage, not for learning
    await store_message(message)
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)


@Client.on_message(filters.command("clearearning") & filters.private)
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

    # Store command usage, not for learning
    await store_message(message)
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)

@Client.on_message(filters.command("restart") & filters.private)
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

# --- /chat on/off command ---
@Client.on_message(filters.command("chat") & filters.group)
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
        group_tracking_collection.update_one(
            {"_id": message.chat.id},
            {"$set": {"bot_enabled": True}}
        )
        await send_and_auto_delete_reply(message, text="🚀 Main phir se aa gayi! Ab main is group mein baatein karungi aur seekhungi. 😊", parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Bot enabled in group {message.chat.id} by admin {message.from_user.id}. (Code by @asbhaibsr)")
    elif action == "off":
        group_tracking_collection.update_one(
            {"_id": message.chat.id},
            {"$set": {"bot_enabled": False}}
        )
        await send_and_auto_delete_reply(message, text="😴 Main abhi thodi der ke liye chup ho rahi hoon. Jab meri zaroorat ho, `/chat on` karke bula lena. Bye-bye! 👋", parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Bot disabled in group {message.chat.id} by admin {message.from_user.id}. (Code by @asbhaibsr)")
    else:
        await send_and_auto_delete_reply(message, text="Galat command, darling! `/chat on` ya `/chat off` use karo. 😉", parse_mode=ParseMode.MARKDOWN)

    # Store command usage, not for learning
    await store_message(message)
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)


# --- NEW: Group Moderation Commands ---

@Client.on_message(filters.command("linkdel") & filters.group)
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
        group_tracking_collection.update_one(
            {"_id": message.chat.id},
            {"$set": {"linkdel_enabled": True}},
            upsert=True
        )
        await send_and_auto_delete_reply(message, text="ही ही ही! 🤭 अब कोई भी शरारती लिंक भेजेगा, तो मैं उसे जादू से गायब कर दूंगी! 🪄 ग्रुप को एकदम साफ़-सुथरा रखना है न! 😉", parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Link deletion enabled in group {message.chat.id} by admin {message.from_user.id}.")
    elif action == "off":
        group_tracking_collection.update_one(
            {"_id": message.chat.id},
            {"$set": {"linkdel_enabled": False}},
            upsert=True
        )
        await send_and_auto_delete_reply(message, text="ठीक है, ठीक है! मैंने अपनी 'लिंक जादू' की छड़ी रख दी है! 😇 अब आप जो चाहे लिंक भेज सकते हैं! पर ध्यान से, ओके?", parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Link deletion disabled in group {message.chat.id} by admin {message.from_user.id}.")
    else:
        await send_and_auto_delete_reply(message, text="उम्म... मुझे समझ नहीं आया! 😕 `/linkdel on` या `/linkdel off` यूज़ करो, प्लीज़! ✨", parse_mode=ParseMode.MARKDOWN)

    # Store command usage, not for learning
    await store_message(message)


@Client.on_message(filters.command("biolinkdel") & filters.group)
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
        group_tracking_collection.update_one(
            {"_id": message.chat.id},
            {"$set": {"biolinkdel_enabled": True}},
            upsert=True
        )
        await send_and_auto_delete_reply(message, text="हम्म... 😼 अब से जो भी **यूज़र अपनी बायो में `t.me` या `http/https` लिंक रखेगा**, मैं उसके **मैसेज को चुपचाप हटा दूंगी!** (अगर उसे `/biolink` से छूट नहीं मिली है). ग्रुप में कोई मस्ती नहीं!🤫", parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Biolink deletion enabled in group {message.chat.id} by admin {message.from_user.id}.")
    elif action == "off":
        group_tracking_collection.update_one(
            {"_id": message.chat.id},
            {"$set": {"biolinkdel_enabled": False}},
            upsert=True
        )
        await send_and_auto_delete_reply(message, text="ओके डार्लिंग्स! 😇 अब मैं यूज़र्स की बायो में `t.me` और `http/https` लिंक्स को चेक करना बंद कर रही हूँ! सब फ्री-फ्री! 🎉", parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Biolink deletion disabled in group {message.chat.id} by admin {message.from_user.id}.")
    else:
        await send_and_auto_delete_reply(message, text="उम्म... मुझे समझ नहीं आया! 😕 `/biolinkdel on` या `/biolinkdel off` यूज़ करो, प्लीज़! ✨", parse_mode=ParseMode.MARKDOWN)

    # Store command usage, not for learning
    await store_message(message)


@Client.on_message(filters.command("biolink") & filters.group)
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

    # Store command usage, not for learning
    await store_message(message)


@Client.on_message(filters.command("usernamedel") & filters.group)
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
        group_tracking_collection.update_one(
            {"_id": message.chat.id},
            {"$set": {"usernamedel_enabled": True}},
            upsert=True
        )
        await send_and_auto_delete_reply(message, text="चीं-चीं! 🐦 अब से कोई भी `@` करके किसी को भी परेशान नहीं कर पाएगा! जो करेगा, उसका मैसेज मैं फट से उड़ा दूंगी!💨 मुझे डिस्टर्बेंस पसंद नहीं! 😠", parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Username deletion enabled in group {message.chat.id} by admin {message.from_user.id}.")
    elif action == "off":
        group_tracking_collection.update_one(
            {"_id": message.chat.id},
            {"$set": {"usernamedel_enabled": False}},
            upsert=True
        )
        await send_and_auto_delete_reply(message, text="ठीक है! आज से मेरी @ वाली आंखें बंद! 😴 अब आप जो चाहे @ करो! पर ज़्यादा तंग मत करना किसी को! 🥺", parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Username deletion disabled in group {message.chat.id} by admin {message.from_user.id}.")
    else:
        await send_and_auto_delete_reply(message, text="उम्म... मुझे समझ नहीं आया! 😕 `/usernamedel on` या `/usernamedel off` यूज़ करो, प्लीज़! ✨", parse_mode=ParseMode.MARKDOWN)

    # Store command usage, not for learning
    await store_message(message)

# --- NEW: /clearall command (Owner-Only, with confirmation) ---
@Client.on_message(filters.command("clearall") & filters.private)
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
    # Store command usage, not for learning
    await store_message(message)

@Client.on_callback_query(filters.regex("^(confirm_clearall_dbs|cancel_clearall_dbs)$"))
async def handle_clearall_dbs_callback(client: Client, callback_query):
    query = callback_query

    # Answer the callback query immediately to remove loading state
    await query.answer()

    if query.from_user.id != OWNER_ID:
        await query.edit_message_text("आप इस कार्रवाई को अधिकृत नहीं हैं।")
        return

    if query.data == 'confirm_clearall_dbs':
        await query.edit_message_text("डेटा डिलीट किया जा रहा है... कृपया प्रतीक्षा करें।⏳")
        try:
            # Drop all collections within their respective databases.
            # This is safer than dropping the entire database which might delete other dbs if the URI is for a cluster.
            # Drop messages_collection
            messages_collection.drop()
            logger.info("messages_collection dropped.")

            # Drop buttons_collection
            buttons_collection.drop()
            logger.info("buttons_collection dropped.")

            # Drop all collections in the tracking database
            group_tracking_collection.drop()
            logger.info("group_tracking_collection dropped.")
            user_tracking_collection.drop()
            logger.info("user_tracking_collection dropped.")
            earning_tracking_collection.drop()
            logger.info("earning_tracking_collection dropped.")
            reset_status_collection.drop()
            logger.info("reset_status_collection dropped.")
            biolink_exceptions_collection.drop()
            logger.info("biolink_exceptions_collection dropped.")
            owner_taught_responses_collection.drop() # NEW: Drop owner-taught collection
            logger.info("owner_taught_responses_collection dropped.")
            conversational_learning_collection.drop() # NEW: Drop conversational learning collection
            logger.info("conversational_learning_collection dropped.")


            await query.edit_message_text("✅ **सफलतापूर्वक:** आपकी सभी MongoDB डेटाबेस का सारा डेटा डिलीट कर दिया गया है। बॉट अब बिल्कुल नया हो गया है! ✨", parse_mode=ParseMode.MARKDOWN)
            logger.info(f"Owner {query.from_user.id} confirmed and successfully cleared all MongoDB data.")
        except Exception as e:
            await query.edit_message_text(f"❌ **त्रुटि:** डेटा डिलीट करने में समस्या आई: {e}\n\nकृपया लॉग्स चेक करें।", parse_mode=ParseMode.MARKDOWN)
            logger.error(f"Error during /clearall confirmation and deletion: {e}")
    elif query.data == 'cancel_clearall_dbs':
        await query.edit_message_text("कार्यवाही रद्द कर दी गई है। आपका डेटा सुरक्षित है। ✅", parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Owner {query.from_user.id} cancelled /clearall operation.")

# --- NEW: /clearmydata command ---
@Client.on_message(filters.command("clearmydata"))
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
        await send_and_auto_delete_reply(message, text="मुझे पता नहीं चल रहा कि किसका डेटा डिलीet करना है। 😕", parse_mode=ParseMode.MARKDOWN)
        return

    try:
        deleted_messages_count = messages_collection.delete_many({"user_id": target_user_id}).deleted_count
        deleted_earning_data = earning_tracking_collection.delete_one({"_id": target_user_id}).deleted_count # Also clear earning data for that user

        # NEW: Also clear user's entries from learning collections if they contributed
        owner_taught_responses_collection.update_many(
            {"responses.user_id": target_user_id},
            {"$pull": {"responses": {"user_id": target_user_id}}}
        )
        # If a trigger was taught by this user and has no other responses left, delete the trigger
        owner_taught_responses_collection.delete_many({"responses": []})

        conversational_learning_collection.update_many(
            {"responses.user_id": target_user_id},
            {"$pull": {"responses": {"user_id": target_user_id}}}
        )
        # If a trigger was taught by this user and has no other responses left, delete the trigger
        conversational_learning_collection.delete_many({"responses": []})


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
    # Store command usage, not for learning
    await store_message(message)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)


# --- New chat members and left chat members ---
@Client.on_message(filters.new_chat_members)
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

    # Store command usage, not for learning
    await store_message(message)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)


@Client.on_message(filters.left_chat_member)
async def left_member_handler(client: Client, message: Message):
    logger.info(f"Left chat member detected in chat {message.chat.id}. Left member ID: {message.left_chat_member.id}. Bot ID: {client.me.id}. (Event handled by @asbhaibsr)")

    if message.left_chat_member and message.left_chat_member.id == client.me.id:
        if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
            group_tracking_collection.delete_one({"_id": message.chat.id})
            messages_collection.delete_many({"chat_id": message.chat.id})
            # NEW: Clear learning data associated with this group
            owner_taught_responses_collection.delete_many({"responses.chat_id": message.chat.id})
            conversational_learning_collection.delete_many({"responses.chat_id": message.chat.id})

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

    # Store command usage, not for learning
    await store_message(message)
    if message.from_user:
        await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)

