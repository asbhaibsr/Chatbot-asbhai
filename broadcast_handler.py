#broadcast_handler.py

import asyncio
import time
import datetime
from pyrogram import Client, filters
# 🌟 FIX 1: StopPropagation को pyrogram.errors से हटाकर सीधे pyrogram से इम्पोर्ट किया गया।
from pyrogram import StopPropagation
from pyrogram.types import Message
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait, UserIsBlocked, ChatWriteForbidden, PeerIdInvalid, RPCError 

# 'config' और 'utils' से आवश्यक चीज़ें इम्पोर्ट करें
from config import (
    app, group_tracking_collection, user_tracking_collection,
    logger, OWNER_ID
)
from utils import (
    delete_after_delay_for_message,
    store_message 
)

# --- ब्रॉडकास्ट के लिए नया और बेहतर सिस्टम ---

# यह डिक्शनरी बताएगी कि बॉट किस यूजर के मैसेज का इंतजार कर रहा है
waiting_for_reply = {}

# यह लिस्नर सिर्फ ओनर के मैसेज को सुनेगा जब बॉट इंतजार कर रहा हो
# 🌟 FIX 2: TypeError को ठीक करने के लिए filters.command() में एक डमी आर्गुमेंट जोड़ा गया।
@app.on_message(filters.private & filters.user(OWNER_ID) & ~filters.command("dummy_cmd_to_ignore"), group=-1)
async def message_waiter_handler(client, message: Message):
    user_id = message.from_user.id
    # चेक करें कि क्या बॉट इस यूजर के जवाब का इंतजार कर रहा है
    future = waiting_for_reply.pop(user_id, None)
    if future:
        # अगर हाँ, तो मैसेज को ब्रॉडकास्ट फंक्शन तक पहुँचाएँ
        future.set_result(message)
        # और इस मैसेज को आगे किसी और फंक्शन (जैसे AI चैट) तक जाने से रोकें
        # StopPropagation अब सही तरह से इम्पोर्ट हो रहा है।
        raise StopPropagation

async def ask_for_message(client, chat_id, text, timeout=600):
    """
    यह फंक्शन यूजर को एक मैसेज भेजता है और उनके अगले मैसेज का इंतजार करता है।
    """
    await client.send_message(chat_id, text)
    # यूजर के अगले मैसेज के लिए एक फ्यूचर ऑब्जेक्ट बनाएँ
    future = asyncio.get_event_loop().create_future()
    waiting_for_reply[chat_id] = future
    try:
        # दिए गए टाइमआउट तक मैसेज का इंतजार करें
        return await asyncio.wait_for(future, timeout=timeout)
    except asyncio.TimeoutError:
        # टाइमआउट होने पर डिक्शनरी से यूजर को हटा दें
        waiting_for_reply.pop(chat_id, None)
        return None

# --- ब्रॉडकास्ट भेजने वाला लॉजिक ---
async def send_broadcast_message(client: Client, chat_id: int, message: Message):
    try:
        # ParseMode.MARKDOWN का इस्तेमाल करके मैसेज को कॉपी करें
        await message.copy(chat_id, parse_mode=ParseMode.MARKDOWN)
        return (True, "Success")
    except UserIsBlocked: return (False, "Blocked")
    except ChatWriteForbidden: return (False, "Blocked")
    except PeerIdInvalid: return (False, "Deleted/Invalid")
    except RPCError as rpc_e:
        if "USER_DEACTIVATED" in str(rpc_e): return (False, "Deleted/Deactivated")
        logger.error(f"RPC Error sending broadcast to chat {chat_id}: {rpc_e}")
        return (False, "Error")
    except FloodWait as fw:
        logger.warning(f"FloodWait of {fw.value}s encountered. Sleeping...")
        await asyncio.sleep(fw.value)
        return await send_broadcast_message(client, chat_id, message)
    except Exception as e:
        logger.error(f"General Error sending broadcast to chat {chat_id}: {e}")
        return (False, "Error")

# -----------------------------------------------------
# 1. PRIVATE CHAT BROADCAST (/broadcast)
# -----------------------------------------------------
@app.on_message(filters.command("broadcast") & filters.private & filters.user(OWNER_ID))
async def pm_broadcast(client: Client, message: Message):
    # ब्रॉडकास्ट करने के लिए मैसेज मांगें
    b_msg = await ask_for_message(
        client,
        message.chat.id,
        "**🚀 Private Broadcast:**\nअब मुझे वह मैसेज भेजें जिसे आप सभी यूजर्स को भेजना चाहते हैं। (फोटो, वीडियो, टेक्स्ट कुछ भी)"
    )

    if b_msg is None:
        await message.reply_text("⏰ समय समाप्त। ब्रॉडकास्ट रद्द किया गया।")
        return

    # यूजर्स की लिस्ट निकालें
    all_target_ids = [u["_id"] for u in user_tracking_collection.find({}) if u["_id"] != OWNER_ID]
    total_targets = len(all_target_ids)
    
    if total_targets == 0:
        await message.reply_text("🤷‍♀️ ब्रॉडकास्ट करने के लिए कोई यूजर नहीं मिला।")
        return

    sts = await message.reply_text(f"🚀 **Private Broadcast Shuru!**\nमैं **{total_targets}** प्राइवेट यूजर्स को मैसेज भेज रही हूँ...", parse_mode=ParseMode.MARKDOWN)
    
    start_time = time.time()
    done, success, blocked, deleted, failed = 0, 0, 0, 0, 0
    
    for chat_id in all_target_ids:
        pti, sh = await send_broadcast_message(client, chat_id, b_msg)
        if pti: success += 1
        else:
            if sh == "Blocked": blocked += 1
            elif "Deleted" in sh: deleted += 1
            else: failed += 1
        done += 1
        
        if done % 20 == 0 or done == total_targets:
            try:
                await sts.edit_text(
                    f"🚀 **Broadcast Progress...**\n\n"
                    f"Total: **{total_targets}** | Completed: **{done}**\n"
                    f"✅ Success: **{success}**\n"
                    f"❌ Blocked: **{blocked}**\n"
                    f"🗑️ Deleted: **{deleted}**"
                )
            except Exception: pass
                
    time_taken = datetime.timedelta(seconds=int(time.time()-start_time))
    await sts.edit_text(
        f"🎉 **Private Broadcast पूरा हुआ!**\n"
        f"समय लगा: **{time_taken}**\n\n"
        f"Total Users: **{total_targets}**\n"
        f"सफलतापूर्वक भेजा: **{success}** ✨\n"
        f"Blocked: **{blocked}** 💔\n"
        f"Deleted/Invalid: **{deleted}** 🗑️"
    )
    await store_message(client, message)

# -----------------------------------------------------
# 2. GROUP BROADCAST (/grp_broadcast)
# -----------------------------------------------------
@app.on_message(filters.command("grp_broadcast") & filters.private & filters.user(OWNER_ID))
async def broadcast_group(client: Client, message: Message):
    b_msg = await ask_for_message(
        client,
        message.chat.id,
        "**🚀 Group Broadcast:**\nअब मुझे वह मैसेज भेजें जिसे आप सभी ग्रुप्स में भेजना चाहते हैं। (फोटो, वीडियो, टेक्स्ट कुछ भी)"
    )

    if b_msg is None:
        await message.reply_text("⏰ समय समाप्त। ब्रॉडकास्ट रद्द किया गया।")
        return

    group_chat_ids = [g["_id"] for g in group_tracking_collection.find({})]
    total_targets = len(group_chat_ids)
    
    if total_targets == 0:
        await message.reply_text("🤷‍♀️ ब्रॉडकास्ट करने के लिए कोई ग्रुप नहीं मिला।")
        return

    sts = await message.reply_text(f"🚀 **Group Broadcast Shuru!**\nमैं **{total_targets}** ग्रुप्स में मैसेज भेज रही हूँ...", parse_mode=ParseMode.MARKDOWN)
    
    start_time = time.time()
    done, success, failed = 0, 0, 0
    
    for chat_id in group_chat_ids:
        pti, sh = await send_broadcast_message(client, chat_id, b_msg)
        if pti: success += 1
        else: failed += 1
        done += 1
        
        if done % 20 == 0 or done == total_targets:
            try:
                await sts.edit_text(
                    f"🚀 **Group Broadcast Progress...**\n\n"
                    f"Total Groups: **{total_targets}** | Completed: **{done}**\n"
                    f"✅ Success: **{success}**\n"
                    f"❌ Failed: **{failed}**"
                )
            except Exception: pass
                
    time_taken = datetime.timedelta(seconds=int(time.time()-start_time))
    await sts.edit_text(
        f"🎉 **Group Broadcast पूरा हुआ!**\n"
        f"समय लगा: **{time_taken}**\n\n"
        f"Total Groups: **{total_targets}**\n"
        f"सफलतापूर्वक भेजा: **{success}** ✨\n"
        f"Failed: **{failed}** 💔"
    )
    await store_message(client, message)
