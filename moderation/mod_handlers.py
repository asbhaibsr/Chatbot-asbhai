# moderation/mod_handlers.py

import asyncio
from datetime import datetime
import pytz

from pyrogram import Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatType, ChatMemberStatus, ParseMode

from config import OWNER_ID, URL_PATTERN
from database.mongo_setup import (
    group_tracking_collection, messages_collection,
    biolink_exceptions_collection, earning_tracking_collection,
    client_messages, client_buttons, client_tracking,
    user_tracking_collection # Added for clearall functionality
)
from utils.helpers import (
    logger, is_on_command_cooldown, update_command_cooldown,
    is_admin_or_owner, send_and_auto_delete_reply, store_message
)

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

    await store_message(message)
    await update_user_info(message.from_user.id, message.from_user.username, message.from_user.first_name)


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

    await store_message(message)


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
        await send_and_auto_delete_reply(message, text="हम्म... 😼 अब से जो भी **यूज़र अपनी बायो में `t.me` या `http/https` लिंक रखेगा**, मैं उसके **मैसेज को चुपचाप हटा दूंगी!** (अगर उसे `/biolink` से छूट नहीं मिली है). ग्रुप में कोई मस्ती नहीं! 🤫", parse_mode=ParseMode.MARKDOWN)
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

    await store_message(message)


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
        await send_and_auto_delete_reply(message, text="उmm... मुझे समझ नहीं आया! 😕 `/usernamedel on` या `/usernamedel off` यूज़ करो, प्लीज़! ✨", parse_mode=ParseMode.MARKDOWN)

    await store_message(message)


async def clear_all_dbs_command_initiate(client: Client, message: Message):
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
    await store_message(message) # Store the command itself

