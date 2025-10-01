import re
import asyncio
import time
import logging
import random
from datetime import datetime, timedelta

import pytz
from pyrogram import Client
from pyrogram.types import Message, InlineKeyboardMarkup, User
from pyrogram.enums import ChatMemberStatus, ChatType, ParseMode
from pyrogram.raw.functions.messages import SetTyping
from pyrogram.raw.types import SendMessageTypingAction

# Existing AI/NLP Imports (Tier 2 AI)
from textblob import TextBlob
from nltk.sentiment.vader import SentimentIntensityAnalyzer

# NEW FREE AI/NLP LIBRARY IMPORTS
from fuzzywuzzy import fuzz # For better pattern matching similarity (Tier 1)
# Note: Tier 3 AI is implemented as a function mocking a powerful free AI.

# Configuration imports (Assume these are correctly defined in config.py)
from config import (
    messages_collection, owner_taught_responses_collection, conversational_learning_collection,
    group_tracking_collection, user_tracking_collection, earning_tracking_collection,
    reset_status_collection, biolink_exceptions_collection, app, logger,
    MAX_MESSAGES_THRESHOLD, PRUNE_PERCENTAGE, URL_PATTERN, OWNER_ID,
    user_cooldowns, COMMAND_COOLDOWN_TIME, chat_message_cooldowns, MESSAGE_REPLY_COOLDOWN_TIME
)

# Global dictionary to track the last earning message time for each user
earning_cooldowns = {}

# New: Global dictionary to store chat context (last 5 messages)
chat_contexts = {}
MAX_CONTEXT_SIZE = 5

# Initialize sentiment analyzer
analyser = SentimentIntensityAnalyzer()
# You only need to initialize VADER once.

def get_sentiment(text):
    if not text:
        return "neutral"
    
    # Use TextBlob for general sentiment and VADER for nuanced sentiment
    blob_sentiment = TextBlob(text).sentiment.polarity
    vader_sentiment = analyser.polarity_scores(text)['compound']
    
    if vader_sentiment >= 0.05:
        return "positive"
    elif vader_sentiment <= -0.05:
        return "negative"
    else:
        return "neutral"

def build_markov_chain(messages):
    chain = {}
    words = []
    for msg in messages:
        if isinstance(msg, dict) and msg.get('content') and msg.get('type') == 'text':
            # Remove punctuation for better chaining
            content = re.sub(r'[^\w\s]', '', msg['content'].lower())
            words.extend(content.split())
    
    if not words or len(words) < 2:
        return {}

    for i in range(len(words) - 1):
        current_word = words[i]
        next_word = words[i+1]
        
        if current_word not in chain:
            chain[current_word] = []
        chain[current_word].append(next_word)
        
    return chain

def generate_sentence(chain, length=10):
    if not chain:
        return ""
    
    # Start with a capitalized word for better sentence structure
    start_word_candidates = [w for w in chain.keys() if w and w[0].isalpha() and w[0].isupper()]
    if not start_word_candidates:
         start_word = random.choice(list(chain.keys()))
    else:
         start_word = random.choice(start_word_candidates)

    sentence = [start_word.capitalize()]

    current_word = start_word
    for _ in range(length - 1):
        if current_word in chain and chain[current_word]:
            next_word = random.choice(chain[current_word])
            # Simple check to stop sentence
            if next_word in ["to", "ki", "aur", "ya"] and random.random() < 0.2:
                 break
            sentence.append(next_word)
            current_word = next_word
        else:
            break
            
    # Simple post-processing
    final_sentence = " ".join(sentence)
    if not final_sentence.endswith(('.', '?', '!')):
        final_sentence += random.choice(['.', '!', '?'])
        
    return final_sentence.replace(" i ", " I ") # Correcting 'i' to 'I'

def extract_keywords(text):
    if not text:
        return []
    words = re.findall(r'\b\w+\b', text.lower())
    # Simple stop word removal (extend this list in a real scenario)
    stop_words = {"ko", "ke", "ka", "ki", "mein", "main", "hai", "tha", "the", "aur", "ya", "ek"}
    filtered_words = [w for w in words if w not in stop_words and len(w) > 2]
    return list(set(filtered_words))

async def prune_old_messages():
    total_messages = messages_collection.count_documents({})
    logger.info(f"Current total messages in DB: {total_messages}. (System by @asbhaibsr)")

    if total_messages > MAX_MESSAGES_THRESHOLD:
        messages_to_delete_count = int(total_messages * PRUNE_PERCENTAGE)
        logger.info(f"Threshold reached. Deleting {messages_to_delete_count} oldest messages. (System by @asbhaibsr)")

        oldest_message_ids = []
        for msg in messages_collection.find({}) \
                                            .sort("timestamp", 1) \
                                            .limit(messages_to_delete_count):
            oldest_message_ids.append(msg['_id'])

        if oldest_message_ids:
            delete_result = messages_collection.delete_many({"_id": {"$in": oldest_message_ids}})
            logger.info(f"Successfully deleted {delete_result.deleted_count} messages. (System by @asbhaibsr)")
        else:
            logger.warning("No oldest messages found to delete despite threshold being reached. (System by @asbhaibsr)")
    else:
        logger.info("Message threshold not reached. No pruning needed. (System by @asbhaibsr)")

async def is_admin_or_owner(client: Client, chat_id: int, user_id: int):
    if user_id == OWNER_ID:
        return True
    try:
        member = await client.get_chat_member(chat_id, user_id)
        if member.status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
            return True
    except Exception as e:
        if "CHAT_ADMIN_REQUIRED" in str(e):
            logger.warning(f"Bot is not an admin in chat {chat_id}, cannot check user {user_id} status. Assuming user is not an admin.")
            return False
        logger.error(f"Error checking admin status for user {user_id} in chat {chat_id}: {e}")
    return False

def contains_link(text: str):
    if not text:
        return False
    return bool(URL_PATTERN.search(text))

def contains_mention(text: str):
    if not text:
        return False
    mention_pattern = r"@[\w\d\._-]+"
    return bool(re.search(mention_pattern, text))

async def store_message(client: Client, message: Message):
    try:
        if message.from_user and message.from_user.is_bot:
            logger.debug(f"Skipping general storage for message from bot: {message.from_user.id}. (Code by @asbhaibsr)")
            return

        is_command = message.text and message.text.startswith('/')
        if is_command:
            logger.debug(f"Skipping general storage for command: {message.text}. (Code by @asbhaibsr)")
            return
        
        # --- Prepare the current message data ---
        current_message_content = message.text if message.text else (message.sticker.file_id if message.sticker else None)
        current_message_type = "text" if message.text else ("sticker" if message.sticker else None)
        current_user_id = message.from_user.id if message.from_user else None

        if not current_message_content or not current_message_type:
            logger.debug(f"Skipping storage for empty or unsupported message: {message.id}.")
            return

        chat_id = message.chat.id
        if chat_id not in chat_contexts:
            chat_contexts[chat_id] = []
        
        message_to_store = {
            "user_id": current_user_id, 
            "content": current_message_content,
            "type": current_message_type
        }
        
        # --- NEW: User-to-User Conversation Pattern Storage ---
        # Store pattern if the current message is from a different user than the last message in the context
        if len(chat_contexts[chat_id]) >= 1:
            last_message = chat_contexts[chat_id][-1]
            last_user_id = last_message.get("user_id")
            
            # Check if the last two messages are from different, non-bot users
            if (last_user_id is not None and last_user_id != current_user_id and 
                last_message.get("type") in ["text", "sticker"] and 
                current_message_type in ["text", "sticker"]):
                
                trigger_content = last_message["content"]
                trigger_type = last_message["type"]
                
                reply_content = current_message_content
                reply_type = current_message_type
                
                # Store the pattern
                conversational_learning_collection.update_one(
                    {"trigger_content": trigger_content, "trigger_type": trigger_type},
                    {"$push": {
                        "responses": {
                            "content": reply_content,
                            "type": reply_type,
                            "timestamp": datetime.now(),
                            "user_pattern_source_id": current_user_id # Track which user said the response
                        }
                    }},
                    upsert=True
                )
                logger.info(f"Conversational pattern (U-to-U) stored: '{trigger_content}' -> '{reply_content}'.")


        # Update the chat context with the new message
        chat_contexts[chat_id].append(message_to_store)
        if len(chat_contexts[chat_id]) > MAX_CONTEXT_SIZE:
            chat_contexts[chat_id].pop(0)


        # --- General Message Storage ---
        message_data = {
            "message_id": message.id,
            "user_id": current_user_id,
            "username": message.from_user.username if message.from_user else None,
            "first_name": message.from_user.first_name if message.from_user else None,
            "chat_id": message.chat.id,
            "chat_type": message.chat.type.name,
            "chat_title": message.chat.title if message.chat.type != ChatType.PRIVATE else None,
            "timestamp": datetime.now(),
            "credits": "Code by @asbhaibsr"
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
            logger.debug(f"Unsupported message type for general storage: {message.id}. (Code by @asbhaibsr)")
            return
        
        messages_collection.insert_one(message_data)
        logger.info(f"General message stored: {message.id} from {current_user_id}. (Storage by @asbhaibsr)")

        # --- Earning Tracking Logic (Simplified) ---
        if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP] and message.from_user and not message.from_user.is_bot:
            user_id_to_track = message.from_user.id
            if message.reply_to_message: # Simplified: earning only when replying
                replied_to_user_id = message.reply_to_message.from_user.id if message.reply_to_message.from_user else None
                if replied_to_user_id and replied_to_user_id != user_id_to_track:
                    last_earning_time = earning_cooldowns.get(user_id_to_track, 0)
                    if time.time() - last_earning_time >= 8:
                        earning_cooldowns[user_id_to_track] = time.time()
                        # Update earning_tracking_collection (logic kept simple for brevity)
                        earning_tracking_collection.update_one(
                            {"_id": user_id_to_track},
                            {"$inc": {"group_message_count": 1}, "$set": {"last_active_group_message": datetime.now()}},
                            upsert=True
                        )
                        logger.info(f"Earning message count updated for user {user_id_to_track}.")

        await prune_old_messages()

    except Exception as e:
        logger.error(f"Error storing message {message.id}: {e}. (System by @asbhaibsr)")

# --- TIER 2 AI Fallback Function (Advanced NLTK/TextBlob) ---
def generate_free_ai_response_tier2(text: str):
    """Uses TextBlob and VADER to generate a context-aware, natural, girl-like response."""
    sentiment = get_sentiment(text)
    keywords = extract_keywords(text)
    
    # Simple, free-AI-like response logic, aiming for 'girl-like' (more empathetic/casual)
    if sentiment == "positive":
        if random.random() < 0.6 and keywords:
             return f"वाह! यह सुनकर मुझे बहुत खुशी हुई। {random.choice(keywords).capitalize()} के बारे में और बताओ ना? ✨"
        else:
             positive_replies = ["हाँ, यह तो शानदार है! मैं भी बहुत खुश हूँ! 😍", "अरे वाह! बहुत बढ़िया!"]
             return random.choice(positive_replies)
             
    elif sentiment == "negative":
        negative_replies = [
            "अरे यार, सब ठीक है ना? मुझे बताओ क्या हुआ है। 🥺",
            "परेशान मत हो, मैं तुम्हारे साथ हूँ। थोड़ा ब्रेक ले लो। ❤️",
            "कोई बात नहीं, कभी-कभी ऐसा होता है। चिल! 😊"
        ]
        return random.choice(negative_replies)
        
    elif sentiment == "neutral" and keywords:
        # Try to continue the conversation based on keywords
        return f"{random.choice(keywords).capitalize()}? हाँ, मैंने भी इसके बारे में सुना है। तुम क्या सोच रहे हो इसके बारे में?"
        
    else:
        # Final generic fallback for Tier 2
        return random.choice(["अच्छा! फिर क्या हुआ?", "और बताओ, क्या चल रहा है?", "hmm... 🙄"])

# --- TIER 3 AI Fallback Function (Mocking Powerful Free AI) ---
def generate_powerful_free_ai_response_tier3(text: str):
    """Mocks a response from a powerful open-source model (like a local GPT-2/BART)."""
    # This simulates the logic of a free, more powerful AI model like a local open-source LLM
    
    keywords = extract_keywords(text)
    sentiment = get_sentiment(text)
    
    if keywords:
        response_templates = [
            f"तुम्हारी बात {random.choice(keywords)} के बारे में है, है ना? मुझे भी लगता है कि यह बहुत महत्वपूर्ण है। 🤔",
            f"यह {random.choice(keywords)} वाला टॉपिक सच में सोचने वाला है। इसमें तुम्हारा क्या योगदान है?",
            f"Hmm... {random.choice(keywords)}! अगर ऐसा है तो आगे क्या होगा? "
        ]
        if sentiment == "positive":
            return random.choice(response_templates) + " मुझे उम्मीद है सब अच्छा होगा! 👍"
        return random.choice(response_templates)
    
    # Fallback to a complex-sounding neutral reply
    return "यह सवाल थोड़ा मुश्किल है। मैं इस पर सोच रही हूँ, लेकिन शायद मुझे और जानकारी चाहिए। तुम किस संदर्भ में पूछ रहे हो?"


async def generate_reply(message: Message):
    if message.reply_to_message and message.reply_to_message.from_user and not message.reply_to_message.from_user.is_self:
        logger.info(f"Skipping reply for message {message.id} as it's a reply to another user.")
        return {"type": None}
    
    # Typing action for a realistic feel
    await app.invoke(
        SetTyping(
            peer=await app.resolve_peer(message.chat.id),
            action=SendMessageTypingAction()
        )
    )
    await asyncio.sleep(0.5)

    if not message.text and not message.sticker:
        return {"type": None}

    query_content = message.text if message.text else (message.sticker.file_id if message.sticker else "")
    query_type = "text" if message.text else "sticker"
    user_id = message.from_user.id if message.from_user else None
    
    # --- TIER 1: Pattern Matching (Highest Priority) ---
    
    def score_response(response_doc, query):
        trigger = response_doc.get("trigger_content", "")
        if not trigger or query_type != 'text': return 0
        
        # Use token set ratio for better matching of scattered words (fuzzy matching)
        score = fuzz.token_set_ratio(query.lower(), trigger.lower())
        
        # Give a bonus for exact match
        if score == 100:
            return 101 
        return score

    # Search for documents that contain keywords or are close to the query
    docs = list(conversational_learning_collection.find({
        "trigger_type": query_type,
        "trigger_content": {"$exists": True, "$ne": None} # Only match docs with content
    }))

    all_responses = []
    
    if query_type == "text":
        for doc in docs:
            score = score_response(doc, query_content)
            if score >= 80: # Only consider matches with high similarity
                for response in doc.get('responses', []):
                    all_responses.append({"data": response, "score": score, "source_doc": doc})

        if all_responses:
            # Filter for the highest scored/most relevant responses
            highest_score = max(r['score'] for r in all_responses)
            best_responses = [r for r in all_responses if r['score'] >= highest_score]
            
            # Prioritize the pattern learned from the current user (if any)
            user_specific_responses = [r for r in best_responses if r['data'].get("user_pattern_source_id") == user_id]
            
            # Final selection: prioritize user-specific, then the overall best match
            chosen_list = user_specific_responses if user_specific_responses else best_responses
            
            chosen_response = random.choice(chosen_list)['data']
            logger.info(f"TIER 1 (Pattern Match) found. Score: {highest_score}. Type: {chosen_response['type']}.")
            return {"type": chosen_response['type'], "content": chosen_response.get('content'), "sticker_id": chosen_response.get('sticker_id')}
    
    # --- TIER 1.5: Dynamic reply using Markov chain from chat history ---
    current_context = chat_contexts.get(message.chat.id, [])
    if current_context and random.random() < 0.3:
        chain = build_markov_chain(current_context)
        if chain:
            dynamic_reply_text = generate_sentence(chain)
            if dynamic_reply_text and dynamic_reply_text not in query_content: 
                logger.info("TIER 1.5: Generating dynamic reply from chat history (Markov).")
                return {"type": "text", "content": dynamic_reply_text}
                
    # --- TIER 2: NLTK/TextBlob Advanced Fallback (Free AI 1) ---
    if message.text:
        ai_reply_text_tier2 = generate_free_ai_response_tier2(message.text)
        logger.info(f"TIER 2: Falling back to NLTK/TextBlob Advanced AI: {ai_reply_text_tier2}")
        return {"type": "text", "content": ai_reply_text_tier2}

    # --- TIER 3: Powerful Free AI Fallback (Free AI 2) ---
    # Bot will try this only if Tier 1 and 2 responses are not sufficient or if random chance permits
    if message.text and random.random() < 0.7: 
        ai_reply_text_tier3 = generate_powerful_free_ai_response_tier3(message.text)
        logger.info(f"TIER 3: Falling back to MOCK Powerful Free AI: {ai_reply_text_tier3}")
        return {"type": "text", "content": ai_reply_text_tier3}

    # --- TIER 4: Final Fallback (Random Sticker or Generic Text) ---
    logger.info("TIER 4: No suitable pattern/AI found. Falling back to random sticker.")
    
    random_sticker_doc_cursor = messages_collection.aggregate([
        {"$match": {"type": "sticker", "user_id": {"$ne": app.me.id}}},
        {"$sample": {"size": 1}}
    ])
    
    random_sticker_doc = next(random_sticker_doc_cursor, None)
    
    if random_sticker_doc:
        logger.info(f"TIER 4: Random sticker found: {random_sticker_doc.get('sticker_id')}.")
        return {"type": "sticker", "sticker_id": random_sticker_doc.get('sticker_id'), "content": random_sticker_doc.get('content')}
    else:
        logger.warning("TIER 4: No stickers found. Sending a generic text reply.")
        generic_replies = ["Han bolo.", "Kya hua?", "Main sun rahi hu.", "Ji, boliye."]
        return {"type": "text", "content": random.choice(generic_replies)}

async def update_group_info(chat_id: int, chat_title: str, chat_username: str = None):
    try:
        group_tracking_collection.update_one(
            {"_id": chat_id},
            {"$set": {"title": chat_title, "username": chat_username, "last_updated": datetime.now()},
             "$setOnInsert": {"added_on": datetime.now(), "member_count": 0, "bot_enabled": True, "credit": "by @asbhaibsr"}},
            upsert=True
        )
        logger.info(f"Group info updated/inserted successfully for {chat_title} ({chat_id}). (Tracking by @asbhaibsr)")
    except Exception as e:
        logger.error(f"Error updating group info for {chat_title} ({chat_id}): {e}. (Tracking by @asbhaibsr)")

async def update_user_info(user_id: int, username: str, first_name: str):
    try:
        user_tracking_collection.update_one(
            {"_id": user_id},
            {"$set": {"username": username, "first_name": first_name, "last_active": datetime.now()},
             "$setOnInsert": {"joined_on": datetime.now(), "credit": "by @asbhaibsr"}},
            upsert=True
        )
        logger.info(f"User info updated/inserted successfully for {first_name} ({user_id}). (Tracking by @asbhaibsr)")
    except Exception as e:
        logger.error(f"Error updating user info for {first_name} ({user_id}): {e}. (Tracking by @asbhaibsr)")

async def get_top_earning_users():
    pipeline = [
        {"$match": {"group_message_count": {"$gt": 0}}},
        {"$sort": {"group_message_count": -1}},
    ]
    top_users_data = list(earning_tracking_collection.aggregate(pipeline))
    logger.info(f"Fetched top earning users: {len(top_users_data)} results. (Earning system by @asbhaibsr)")
    top_users_details = []
    for user_data in top_users_data:
        top_users_details.append({
            "user_id": user_data["_id"],
            "first_name": user_data.get("first_name", "Unknown User"),
            "username": user_data.get("username"),
            "message_count": user_data["group_message_count"],
            "last_active_group_id": user_data.get("last_active_group_id"),
            "last_active_group_title": user_data.get("last_active_group_title"),
            "last_active_group_username": user_data.get("last_active_group_username")
        })
    return top_users_details

async def reset_monthly_earnings_manual():
    logger.info("Manually resetting monthly earnings...")
    now = datetime.now(pytz.timezone('Asia/Kolkata'))
    try:
        earning_tracking_collection.update_many(
            {},
            {"$set": {"group_message_count": 0}}
        )
        logger.info("Monthly earning message counts reset successfully by manual command. (Earning system by @asbhaibsr)")
        reset_status_collection.update_one(
            {"_id": "last_manual_reset_date"},
            {"$set": {"last_reset_timestamp": now}},
            upsert=True
        )
        logger.info(f"Manual reset status updated. (Earning system by @asbhaibsr)")
    except Exception as e:
        logger.error(f"Error resetting monthly earnings manually: {e}. (Earning system by @asbhaibsr)")

def is_on_command_cooldown(user_id):
    last_command_time = user_cooldowns.get(user_id)
    if last_command_time is None:
        return False
    return (time.time() - last_command_time) < COMMAND_COOLDOWN_TIME

def update_command_cooldown(user_id):
    user_cooldowns[user_id] = time.time()

async def can_reply_to_chat(chat_id):
    last_reply_time = chat_message_cooldowns.get(chat_id)
    if last_reply_time is None:
        return True
    return (time.time() - last_reply_time) >= MESSAGE_REPLY_COOLDOWN_TIME

def update_message_reply_cooldown(chat_id):
    chat_message_cooldowns[chat_id] = time.time()

async def send_and_auto_delete_reply(message: Message, text: str = None, photo: str = None, sticker: str = None, reply_markup: InlineKeyboardMarkup = None, parse_mode: ParseMode = ParseMode.MARKDOWN, disable_web_page_preview: bool = False):
    sent_message = None
    user_info_str = ""
    if message.from_user:
        if message.from_user.username:
            user_info_str = f" (द्वारा: @{message.from_user.username})"
        else:
            user_info_str = f" (द्वारा: {message.from_user.first_name})"

    text_to_send = text
    if message.command and text:
        command_name = message.command[0]
        text_to_send = f"**कमांड:** `{command_name}`{user_info_str}\n\n{text}"
    elif text and message.chat.type == ChatType.PRIVATE and message.from_user and message.from_user.id == OWNER_ID:
        pass
    elif text and message.from_user:
        pass

    if photo:
        sent_message = await message.reply_photo(
            photo=photo,
            caption=text_to_send,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )
    elif text:
        sent_message = await message.reply_text(
            text_to_send,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
            disable_web_page_preview=disable_web_page_preview
        )
    elif sticker:
        sent_message = await message.reply_sticker(
            sticker=sticker
        )
    else:
        logger.warning(f"send_and_auto_delete_reply called with no text or photo for message {message.id}.")
        return None

    if message.command and message.command[0] == "start":
        return sent_message

    async def delete_after_delay_task():
        await asyncio.sleep(180)
        try:
            if sent_message:
                await sent_message.delete()
        except Exception as e:
            logger.warning(f"Failed to delete message {sent_message.id if sent_message else 'N/A'} in chat {message.chat.id}: {e}")

    asyncio.create_task(delete_after_delay_task())
    return sent_message

async def delete_after_delay_for_message(message_obj: Message, delay: int):
    await asyncio.sleep(delay)
    try:
        await message_obj.delete()
    except Exception as e:
        logger.warning(f"Failed to delete message {message_obj.id} in chat {message_obj.chat.id}: {e}")
