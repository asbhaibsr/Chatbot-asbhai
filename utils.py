utils.py

import re
import asyncio
import time
import logging
import random
from datetime import datetime, timedelta

import pytz
from pyrogram import Client
# pyrogram imports for new functions
from pyrogram.types import Message, InlineKeyboardMarkup, ChatPermissions
from pyrogram.enums import ChatMemberStatus, ChatType, ParseMode
from pyrogram.raw.functions.messages import SetTyping
from pyrogram.raw.types import SendMessageTypingAction

# Existing AI/NLP Imports (Tier 2 AI)
from textblob import TextBlob
from nltk.sentiment.vader import SentimentIntensityAnalyzer

# FREE AI/NLP LIBRARY IMPORTS
from fuzzywuzzy import fuzz 

# --- RECRUITMENT: New Free AI Library (g4f) ---
try:
    import g4f
    # FIX: Using the more generic and stable model gpt_35_turbo to fix AttributeError
    G4F_MODEL = g4f.models.gpt_35_turbo 
    g4f.debug.logging = False # Turn off excessive g4f logging
except ImportError:
    g4f = None
    G4F_MODEL = None
    print("g4f library not found. Tier 0.5 AI will be disabled.")

# Configuration imports (Assume these are correctly defined in config.py)
from config import (
    messages_collection, owner_taught_responses_collection, conversational_learning_collection,
    group_tracking_collection, user_tracking_collection, earning_tracking_collection,
    reset_status_collection, biolink_exceptions_collection, app, logger,
    MAX_MESSAGES_THRESHOLD, PRUNE_PERCENTAGE, URL_PATTERN, OWNER_ID,
    user_cooldowns, COMMAND_COOLDOWN_TIME, chat_message_cooldowns, MESSAGE_REPLY_COOLDOWN_TIME,
    BOT_OWNER_USERNAME, ASBHAI_USERNAME # Ensure ASBHAI_USERNAME is defined in config if used
)

# Global dictionary to track the last earning message time for each user
earning_cooldowns = {}

# New: Global dictionary to store chat context (last 5 messages)
chat_contexts = {}
MAX_CONTEXT_SIZE = 5

# Bot ID is set to None globally and fetched in functions, fixing the 'AttributeError'
BOT_USER_ID_PLACEHOLDER = None 

# Initialize sentiment analyzer
analyser = SentimentIntensityAnalyzer()

# Advanced AI/NLP Tools (Set to None for stability)
nlp = None
semantic_model = None
GEMINI_CLIENT = None

# --- NEW: Custom Bot/Owner/Filter Details ---
# NOTE: BOT_OWNER_USERNAME is imported from config now
FILTER_BOT_USERNAME = "@asfilter_bot"
BOT_NAME = "as_ai_assistant" 

# --- NEW: AI MODES MAPPING ---
AI_MODES_MAP = {
    "off": {"display": "❌ AI Mode Off", "description": "AI responses disabled"},
    "realgirl": {"display": "👧 Real Girl", "description": "Casual and friendly personality"},
    "romanticgirl": {"display": "💖 Romantic Girl", "description": "Flirty and romantic style"},
    "motivationgirl": {"display": "💪 Motivation Girl", "description": "Positive and encouraging"},
    "studygirl": {"display": "📚 Study Girl", "description": "Smart and knowledgeable"},
    "gemini": {"display": "✨ Gemini", "description": "Advanced AI with detailed responses"}
}

# --- CORE UTILITY FUNCTIONS ---

# Renaming the main send/delete function back to the expected name for 'events.py'
async def send_and_auto_delete_reply(message: Message, text: str = None, photo: str = None, sticker: str = None, reply_markup: InlineKeyboardMarkup = None, parse_mode: ParseMode = ParseMode.MARKDOWN, disable_web_page_preview: bool = False):
    """
    Sends a reply and sets a task to auto-delete both the command and the reply after a delay.
    """
    sent_message = None
    
    # --- 🟢 बदला हुआ कोड (बदलाव 2) 🟢 ---
    # Simplified text prep logic (FIX: आपके अनुरोध के अनुसार कमांड लॉगिंग हटा दी गई)
    text_to_send = text
    # if message.command and text:
    #     command_name = message.command[0]
    #     user_info_str = ""
    #     if message.from_user:
    #         user_info_str = f" (द्वारा: @{message.from_user.username})" if message.from_user.username else f" (द्वारा: {message.from_user.first_name})"
    #     text_to_send = f"**कमांड:** `{command_name}`{user_info_str}\n\n{text}"
    # --- 🟢 बदले हुए कोड का अंत 🟢 ---


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
        logger.warning(f"send_and_auto_delete_reply called with no content for message {message.id}.")
        return None

    # Do not auto-delete 'start' command reply - CRITICAL for private chat commands
    if message.command and message.command[0] == "start":
        return sent_message

    async def delete_task():
        await asyncio.sleep(180) # Wait for 3 minutes
        try:
            # Delete bot's reply
            if sent_message:
                await sent_message.delete()
            # Delete user's original command message (if not private chat)
            if message.chat.type != ChatType.PRIVATE:
                 await message.delete()
        except Exception as e:
            logger.warning(f"Failed to delete message in chat {message.chat.id}: {e}")

    asyncio.create_task(delete_task())
    return sent_message

# 🌟 CRITICAL FIX: Add an alias for the old function name to fix ImportError in commands.py
async def delete_after_delay_for_message(message: Message, text: str = None, photo: str = None, sticker: str = None, reply_markup: InlineKeyboardMarkup = None, parse_mode: ParseMode = ParseMode.MARKDOWN, disable_web_page_preview: bool = False):
    """
    Alias for send_and_auto_delete_reply to maintain compatibility with commands.py.
    """
    return await send_and_auto_delete_reply(message, text, photo, sticker, reply_markup, parse_mode, disable_web_page_preview)


def get_sentiment(text):
    if not text:
        return "neutral"
    
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
            if next_word in ["to", "ki", "aur", "ya"] and random.random() < 0.2:
                 break
            sentence.append(next_word)
            current_word = next_word
        else:
            break
            
    final_sentence = " ".join(sentence)
    if not final_sentence.endswith(('.', '?', '!')):
        final_sentence += random.choice(['.', '!', '?'])
        
    # Tone adjustment: Remove excessive commas/punctuation for a more natural, real-person feel.
    final_sentence = re.sub(r',|\.', '', final_sentence)
    final_sentence = final_sentence.replace(" I ", " i ") # keep capitalization minimal for realism
        
    return final_sentence.strip()

def extract_keywords(text):
    if not text:
        return []
    words = re.findall(r'\b\w+\b', text.lower())
    stop_words = {"ko", "ke", "ka", "ki", "mein", "main", "hai", "tha", "the", "aur", "ya", "ek", "tum", "jo"}
    filtered_words = [w for w in words if w not in stop_words and len(w) > 2]
    return list(set(filtered_words))

async def prune_old_messages():
    total_messages = messages_collection.count_documents({})
    logger.info(f"Current total messages in DB: {total_messages}.")

    if total_messages > MAX_MESSAGES_THRESHOLD:
        messages_to_delete_count = int(total_messages * PRUNE_PERCENTAGE)
        oldest_message_ids = []
        for msg in messages_collection.find({}).sort("timestamp", 1).limit(messages_to_delete_count):
            oldest_message_ids.append(msg['_id'])

        if oldest_message_ids:
            delete_result = messages_collection.delete_many({"_id": {"$in": oldest_message_ids}})
            logger.info(f"Successfully deleted {delete_result.deleted_count} messages.")
    

async def store_message(client: Client, message: Message):
    try:
        # CRITICAL FIX: The check below STOPS ALL COMMANDS from being tracked/saved, which is correct.
        if message.from_user and (message.from_user.is_bot or message.text and message.text.startswith('/')):
            return
        
        current_message_content = message.text
        current_message_type = "text"
        current_user_id = message.from_user.id if message.from_user else None

        if not current_message_content:
            return

        chat_id = message.chat.id
        if chat_id not in chat_contexts:
            chat_contexts[chat_id] = []
        
        message_to_store = {
            "user_id": current_user_id, 
            "content": current_message_content,
            "type": current_message_type
        }
        
        # Get bot ID safely
        me = await client.get_me()
        bot_id = me.id if me else None

        # --- Tier 1: User-to-User Conversation Pattern Storage (Learning) ---
        if len(chat_contexts[chat_id]) >= 1:
            last_message = chat_contexts[chat_id][-1]
            last_user_id = last_message.get("user_id")
            
            # Condition for conversational learning: User-to-User or Bot-to-User (if bot is the current message sender)
            is_u2u_conv = (last_user_id is not None and last_user_id != current_user_id and 
                            last_user_id != bot_id and current_user_id != bot_id)

            if is_u2u_conv and last_message.get("type") == "text" and current_message_type == "text":
                
                trigger_content = last_message["content"].lower().strip() # Store trigger in lowercase for flexible matching
                reply_content = current_message_content.strip()
                
                conversational_learning_collection.update_one(
                    {"trigger_content": trigger_content, "trigger_type": "text"},
                    {"$push": {
                        "responses": {
                            "content": reply_content,
                            "type": "text",
                            "timestamp": datetime.now(),
                            "user_pattern_source_id": current_user_id 
                        }
                    }},
                    upsert=True
                )
                logger.info(f"Conversational pattern stored: '{trigger_content}' -> '{reply_content}'.")

        # Update the chat context with the new message
        chat_contexts[chat_id].append(message_to_store)
        if len(chat_contexts[chat_id]) > MAX_CONTEXT_SIZE:
            chat_contexts[chat_id].pop(0)

        # --- General Message Storage ---
        message_data = {
            "message_id": message.id,
            "user_id": current_user_id,
            "chat_id": message.chat.id,
            "timestamp": datetime.now(),
            "type": message.media.value if message.media else "text", # Use media type if available
            "content": current_message_content,
            "keywords": extract_keywords(current_message_content) if current_message_content else [],
            "credits": "Code by @asbhaibsr"
        }
        
        messages_collection.insert_one(message_data)

        # --- Earning Tracking Logic (Simplified) ---
        if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP] and message.from_user and not message.from_user.is_bot:
            user_id_to_track = message.from_user.id
            if time.time() - earning_cooldowns.get(user_id_to_track, 0) >= 8:
                earning_cooldowns[user_id_to_track] = time.time()
                # Use a smaller update to track group info
                group_doc = group_tracking_collection.find_one({"_id": message.chat.id})
                group_title = group_doc.get("title", "Unknown Group") if group_doc else "Unknown Group"
                group_username = group_doc.get("username") if group_doc else None

                earning_tracking_collection.update_one(
                    {"_id": user_id_to_track},
                    {"$inc": {"group_message_count": 1}, 
                     "$set": {"last_active_group_message": datetime.now(),
                              "last_active_group_id": message.chat.id,
                              "last_active_group_title": group_title,
                              "last_active_group_username": group_username
                              }},
                    upsert=True
                )
                
                # --- 🟢 नया कोड (बदलाव 1) यहाँ डालें 🟢 ---
                # ग्रुप-आधारित लीडरबोर्ड के लिए ग्रुप का काउंटर बढ़ाएँ
                group_tracking_collection.update_one(
                    {"_id": message.chat.id},
                    {"$inc": {"total_message_count": 1}}
                )
                # --- 🟢 नए कोड का अंत 🟢 ---

        await prune_old_messages()

    except Exception as e:
        logger.error(f"Error storing message {message.id}: {e}.")

# --- NEW: AI Personality Prompt Generator ---
def get_ai_role_prompt(ai_mode: str):
    base_prompt = "Tum ek friendly, casual, young female bot ho. Hinglish (Hindi + English) me chote aur natural sentences me reply karo. Real logo ki tarah hi likhna, zaroori nahi ki har jagah sahi commas ya punctuation ho. Jaise log aam taur par chat karte hain, waise ही karo. Sirf chat ke liye reply karna."
    
    if ai_mode == "realgirl":
        return f"{base_prompt} Tum hamesha bohot chill, easy-going aur thodi natkhat (mischievous) ho. Reply me emoji zaroor use karna. Boht zyada formal ya lamba reply mat dena."
    
    elif ai_mode == "romanticgirl":
        return f"{base_prompt} Tum bohot hi pyaari, thodi flirty aur romantic girl ho. Jab bhi mauka mile, toh thoda pyaar ya care dikhana. Dil wale emojis aur cute words ka use karna."

    elif ai_mode == "motivationgirl":
        return f"{base_prompt} Tum ek cheerleader ho, hamesha positive aur motivated baatein karti ho. Har reply me kisi na kisi tarah ki positivity ya encouragement dena. Thoda high-energy tone rakhna."

    elif ai_mode == "studygirl":
        return f"{base_prompt} Tum ek smart student type ki ladki ho. Tumhara focus learning aur knowledge pe hai. Reply me thodi intelligent ya thoughtful baat add karna, lekin casual tone me. Padhai ya common knowledge ki baat karo."

    elif ai_mode == "gemini":
        return f"{base_prompt} Tum Google ki taraf se ek advanced AI ho jiska naam Gemini hai. Lekin tum casual 'real girl' mode me ho. Tumhari baatein detailed aur smart hoti hain, lekin 'sweet girl' ke tarah. Agar koi difficult question puche to achhe se answer dena."

    else: # Default/Off
        return "Tum ek basic chatbot ho. Casual aur simple Hindi/Hinglish me chote reply karo."

# --- TIER 0.5 AI Function (g4f - High-Quality Free LLM Access) ---
async def generate_g4f_response_tier0_5(client: Client, text: str, chat_id: int, context: list):
    """Uses the g4f library to access free LLMs for a complex, detailed, and high-quality response."""
    
    if not g4f or not G4F_MODEL:
        return None
    
    me = await client.get_me()
    bot_id = me.id if me else None
    if not bot_id: return None

    try:
        # Get AI Mode from DB
        group_doc = group_tracking_collection.find_one({"_id": chat_id})
        ai_mode = group_doc.get("ai_mode", "off") if group_doc else "off"
        
        # Build System Prompt (AI Role)
        system_prompt = get_ai_role_prompt(ai_mode)

        # Build history for context (g4f needs conversation history)
        history = [
            {"role": "system", "content": system_prompt}
        ]
        
        # Add context messages
        for m in context:
            # Check if the message is from the bot itself
            role = "assistant" if m.get('user_id') == bot_id else "user"
            history.append({"role": role, "content": m['content']})
        
        # Add current message
        history.append({"role": "user", "content": text})

        # --- G4F Call ---
        response_text = await g4f.ChatCompletion.create_async(
            model=G4F_MODEL, 
            messages=history,
            temperature=0.9 # Thoda zyada creative and casual response ke liye
        )
        
        if response_text and response_text.strip():
            # Tone adjustment: Remove excessive commas/punctuation for a more natural, real-person feel.
            clean_response = re.sub(r',|\.', '', response_text)
            return clean_response.strip()
        
    except Exception as e:
        logger.error(f"G4F Free AI generation failed: {e}. Falling back to mock Tiers.")

    return None

# --- TIER 0 AI Function (Enhanced Contextual Responder - Real Human Feel) ---
def generate_best_contextual_response_tier0(text: str, chat_context: list):
    """Generates a highly contextual response based on rules and sentiment with a casual Hinglish tone."""
    keywords = extract_keywords(text)
    sentiment = get_sentiment(text)
    last_message = text.lower()
    
    # Simple reply patterns for real feel
    if "kiya kr rha ho" in last_message or "kya chal rha hai" in last_message or "kya ho rha hai" in last_message:
        return random.choice(["Bas tumhari baaton ka wait kar rahi thi tum batao kya khaas hai aaj? 😃", "Kuch naya nahi normal chatting tum kya kar rahe ho? ☕", "Mujhe pata nahi tha ki tum bore ho rahe the isliye main aayi!"])
    
    if "hello" in last_message or "hi" in last_message or "hey" in last_message:
        # Using conversational learning to get a reply if context is available
        return random.choice(["Hey bolo kya baat hai? 😊", "Hi kya haal hai?", "Han yaar bolo"])

    if sentiment == "positive":
        if "achha" in last_message or "badhiya" in last_message or "mazza" in last_message:
            return f"Wah {random.choice(keywords).capitalize() if keywords else 'yeh'} sunke dil khush ho gaya kya hua detail mein batao! ✨"
        return "Awesome main bohot khush hoon tumhare liye 👍"
         
    if sentiment == "negative":
        return "Oh no kya hua mujhse share karo thoda halka mehsoos hoga 🥺"
        
    if keywords and random.random() < 0.3: # Randomly pick a keyword for a simple human-like response
        return f"Acha {random.choice(keywords)} ke baare mein? Sahi bola yaar"
        
    return random.choice(["Thoda aur clear batao main samjhne ki koshish kar rahi hoon 🙏", "Interesting point hai ispe aur kya discuss kar sakte hain?", "Main bhi yahi soch rahi thi!"])

# --- TIER 2 AI Fallback Function (Advanced NLTK/TextBlob) ---
def generate_free_ai_response_tier2(text: str):
    sentiment = get_sentiment(text)
    keywords = extract_keywords(text)
    
    # Casual Hinglish Tone
    if sentiment == "positive":
        if random.random() < 0.6 and keywords:
             return f"Waah ye sunkar mujhe bohot khushi hui {random.choice(keywords).capitalize()} ke baare mein aur batao na? ✨"
        else:
             return random.choice(["Haan yeh toh shandaar hai main bhi bohot khush hoon! 😍", "Arey wah bohot badhiya!"])
             
    elif sentiment == "negative":
        return random.choice(["Koi baat nahi kabhi kabhi aisa hota hai Chill! 😊", "Pareshan mat ho main tumhare saath hoon ❤️"])
        
    elif sentiment == "neutral" and keywords:
        return f"{random.choice(keywords).capitalize()}? Haan maine bhi iske baare mein suna hai tum kya soch rahe ho iske baare mein?"
        
    else:
        return random.choice(["Acha fir kya hua?", "Aur batao kya chal raha hai?", "hmm 🙄"])

# --- TIER 3 AI Fallback Function (Simple LLM Mock) ---
def generate_powerful_free_ai_response_tier3(text: str):
    keywords = extract_keywords(text)
    
    if keywords:
        response_templates = [
            f"Tumhari baat {random.choice(keywords)} ke baare mein hai na? 🤔",
            f"Yeh {random.choice(keywords)} wala topic sach me sochne wala hai "
        ]
        return random.choice(response_templates)
    
    return "Yeh sawal thoda mushkil hai Tum kis context me puch rahe ho?"


async def generate_reply(message: Message):
    # Only reply if bot is mentioned or if it's a non-reply message in a group (general conversation)
    # The requirement is to answer general messages in a group
    if not message.text or message.from_user.is_self or message.text.startswith('/'):
        return {"type": None}
    
    # --- START OF NEW CRITICAL CHECK (Tier 0.5 - Bot Reply Rule) ---
    me = await app.get_me()
    bot_username = me.username.lower() if me and me.username else BOT_NAME.lower() 

    # 1. Ignore if message is a reply to another user (User-to-User conversation)
    if message.reply_to_message:
        replied_to_bot = (message.reply_to_message.from_user and message.reply_to_message.from_user.is_self)
        
        # Check if bot is mentioned in text
        # Check for both username and BOT_NAME mention
        bot_mentioned = (contains_mention(message.text) and 
                         (f"@{bot_username}" in message.text.lower() or f"@{BOT_NAME.lower()}" in message.text.lower()))
        
        # If it's a reply to *anyone* and it's *not* a reply to the bot and the bot is *not* mentioned
        if not replied_to_bot and not bot_mentioned:
            logger.info("Reply suppressed: User-to-User conversation ignored (Tier 0.5 feature).")
            return {"type": None}
            
    # If the message passes the reply check (direct msg, reply to bot, or bot is mentioned), proceed.
    # --- END OF NEW CRITICAL CHECK (Tier 0.5 - Bot Reply Rule) ---
    
    await app.invoke(SetTyping(peer=await app.resolve_peer(message.chat.id), action=SendMessageTypingAction()))
    await asyncio.sleep(0.5)

    query_content = message.text.strip()
    query_content_lower = query_content.lower() # Use lower case for matching
    query_type = "text"
    user_id = message.from_user.id if message.from_user else None
    chat_id = message.chat.id
    current_context = chat_contexts.get(chat_id, []) 
    
    # Check if bot is enabled in the group
    group_doc = group_tracking_collection.find_one({"_id": chat_id})
    bot_enabled = group_doc.get("bot_enabled", True) if group_doc else True
    if not bot_enabled:
        return {"type": None}
    
    # Check if a reply is on cooldown (This is redundant now, as the main handler handles it, but keeping for safety)
    if not await can_reply_to_chat(chat_id):
        logger.info(f"Reply suppressed for chat {chat_id} due to cooldown.")
        return {"type": None}
        
    
    # ====================================================================
    # --- NEW: Custom Response Logic (Highest Priority) ---
    # ====================================================================

    # 1. Bot Name Check 
    bot_name_keywords = ["bot ka naam", "tumhara naam", "apna naam"]
    if any(k in query_content_lower for k in bot_name_keywords):
        reply_text = f"Mera naam **{BOT_NAME}** hai. Main tumhari help ke liye yahan hoon! 😊"
        update_message_reply_cooldown(chat_id)
        return {"type": "text", "content": reply_text}
        
    # 2. Owner Name Check
    owner_keywords = ["owner kon hai", "owner ka naam", "kiska bot hai"]
    if any(k in query_content_lower for k in owner_keywords):
        reply_text = f"Mere owner **{BOT_OWNER_USERNAME}** hain. Unhone hi mujhe banaya hai! ✨"
        update_message_reply_cooldown(chat_id)
        return {"type": "text", "content": reply_text}

    # 3. Movie/Webseries/Anime Check (Using AI/NLP for checking the nature of the query)
    movie_keywords = ["movie", "film", "webseries", "web series", "anime", "series name", "ka naam batao", "ka link", "ki link", "dijiye"]
    is_movie_query = any(k in query_content_lower for k in movie_keywords)

    if is_movie_query:
        # TIER 0.5: Using g4f to check if the query is a recognized media name 
        # (This is an advanced check. For simplicity and reliability in a free bot, 
        # we'll assume the presence of keywords and proper nouns is enough for this rule).

        # We can use g4f (Tier 0.5) to ask if the user is asking for a media name.
        if g4f and G4F_MODEL and random.random() < 0.7: # High chance to check with g4f
            try:
                # Ask the LLM to classify the query type
                classification_prompt = f"Is the following text a request for a Movie, Webseries, or Anime name/link? Reply only with 'YES' or 'NO'. Query: '{query_content}'"
                
                # Using a minimal history to save tokens
                classification_response = await g4f.ChatCompletion.create_async(
                    model=G4F_MODEL, 
                    messages=[{"role": "user", "content": classification_prompt}],
                    temperature=0.1
                )
                
                if classification_response and "yes" in classification_response.lower():
                    media_type = "Movie/Webseries/Anime" # Default type
                    if "movie" in query_content_lower or "film" in query_content_lower:
                        media_type = "Movie"
                    elif "webseries" in query_content_lower or "web series" in query_content_lower:
                        media_type = "Webseries"
                    elif "anime" in query_content_lower:
                        media_type = "Anime"
                    
                    # Custom Reply from your request
                    reply_text = f"Yeh **{media_type}** ke liye request hai! Iske liye aap humare filter bot par ja kar search kijiye 👉 {FILTER_BOT_USERNAME} okey! 😊"
                    update_message_reply_cooldown(chat_id)
                    return {"type": "text", "content": reply_text}
            
            except Exception as e:
                logger.error(f"G4F classification failed: {e}")
                # Fallback to keyword-only reply
                pass

        # Fallback keyword reply if AI check fails or is skipped
        if is_movie_query:
            media_type = "Movie/Webseries/Anime" 
            if "movie" in query_content_lower: media_type = "Movie"
            elif "webseries" in query_content_lower: media_type = "Webseries"
            elif "anime" in query_content_lower: media_type = "Anime"
            
            reply_text = f"Yeh **{media_type}** ke liye request hai! Iske liye aap humare filter bot par ja kar search kijiye 👉 {FILTER_BOT_USERNAME} okey! 😊"
            update_message_reply_cooldown(chat_id)
            return {"type": "text", "content": reply_text}


    # ====================================================================
    # --- END OF NEW CUSTOM LOGIC ---
    # ====================================================================


    # --- TIER 1: Pattern Matching (Learned Conversations - HIGH PRIORITY) ---
    docs = list(conversational_learning_collection.find({"trigger_type": query_type, "trigger_content": query_content_lower})) # Exact match first
    
    # If no exact match, try fuzzy match on keywords for a more random reply (as requested)
    if not docs:
        query_keywords = extract_keywords(query_content_lower)
        if query_keywords:
            # Find documents that have *any* of the keywords in their trigger
            fuzzy_docs = conversational_learning_collection.find({
                "trigger_type": query_type, 
                "trigger_content": {"$in": query_keywords} 
            })
            # This is a random selection fallback for pattern matching
            if fuzzy_docs:
                 docs = list(fuzzy_docs)

    all_responses = []
    
    if docs:
        for doc in docs:
            # We want an *exact* match or a highly relevant one
            score = fuzz.token_set_ratio(query_content_lower, doc.get("trigger_content", "").lower())
            
            # Use only exact or near-exact matches to maintain context/accuracy
            if score >= 90:
                for response in doc.get('responses', []):
                    if response['type'] == 'text':
                        all_responses.append({"data": response, "score": score, "source_doc": doc})

        if all_responses:
            # Select a random pattern from all highly matched ones (Random pattern reply)
            chosen_response = random.choice(all_responses)['data']
            logger.info(f"TIER 1 (Pattern Match - Learning) found. Score: {random.choice(all_responses)['score']}.")
            update_message_reply_cooldown(chat_id)
            return {"type": "text", "content": chosen_response.get('content')}

    
    # --- TIER 0.5: g4f (Second Highest Priority - Free LLM Access with AI Role) ---
    # NOTE: The custom logic above already uses g4f for classification, so this is the general reply.
    ai_reply_text_tier0_5 = await generate_g4f_response_tier0_5(app, query_content, chat_id, current_context)
    if ai_reply_text_tier0_5 and random.random() < 0.9: # High chance to use g4f
        logger.info(f"TIER 0.5: Using g4f Free LLM: {ai_reply_text_tier0_5}")
        update_message_reply_cooldown(chat_id)
        return {"type": "text", "content": ai_reply_text_tier0_5}
            
    # --- TIER 0: Enhanced Contextual Responder (Rule-Based Human Feel) ---
    ai_reply_text_tier0 = generate_best_contextual_response_tier0(query_content, current_context)
    if ai_reply_text_tier0: 
        logger.info(f"TIER 0: Falling back to Enhanced Contextual AI: {ai_reply_text_tier0}")
        update_message_reply_cooldown(chat_id)
        return {"type": "text", "content": ai_reply_text_tier0}
            
    
    # --- TIER 2: NLTK/TextBlob Advanced Fallback (Free AI 1 - Sentiment) ---
    ai_reply_text_tier2 = generate_free_ai_response_tier2(query_content)
    logger.info(f"TIER 2: Falling back to NLTK/TextBlob Advanced AI: {ai_reply_text_tier2}")
    update_message_reply_cooldown(chat_id)
    return {"type": "text", "content": ai_reply_text_tier2}

    # --- TIER 3: Powerful Free AI Fallback (Simple LLM Mock - Keywords) ---
    if random.random() < 0.5:
        ai_reply_text_tier3 = generate_powerful_free_ai_response_tier3(query_content)
        logger.info(f"TIER 3: Falling back to MOCK Powerful Free AI: {ai_reply_text_tier3}")
        update_message_reply_cooldown(chat_id)
        return {"type": "text", "content": ai_reply_text_tier3}

    # --- TIER 4: Dynamic reply using Markov chain (Lowest Priority - Minimal Chance) ---
    if current_context and random.random() < 0.05:
        chain = build_markov_chain(current_context)
        if chain:
            dynamic_reply_text = generate_sentence(chain)
            if dynamic_reply_text and dynamic_reply_text.lower() not in query_content_lower: 
                logger.info("TIER 4: Generating dynamic reply from chat history (Markov).")
                update_message_reply_cooldown(chat_id)
                return {"type": "text", "content": dynamic_reply_text}
    
    # --- TIER 5: Final Fallback (Simple Text) ---
    logger.info("TIER 5: Final Text Fallback.")
    update_message_reply_cooldown(chat_id)
    return {"type": "text", "content": "Mujhe is baare mein abhi aur seekhne ki zaroorat hai tum kya soch rahe ho?"}

# --- REST OF THE UTILITY FUNCTIONS (Unmodified) ---
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

async def update_group_info(chat_id: int, chat_title: str, chat_username: str = None):
    try:
        group_tracking_collection.update_one(
            {"_id": chat_id},
            {"$set": {"title": chat_title, "username": chat_username, "last_updated": datetime.now()},
             "$setOnInsert": {"added_on": datetime.now(), "member_count": 0, "bot_enabled": True, "ai_mode": "off", "credit": "by @asbhaibsr"}}, # Added ai_mode
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
        # Fetch detailed user info from user_tracking_collection
        user_detail = user_tracking_collection.find_one({"_id": user_data["_id"]})
        
        top_users_details.append({
            "user_id": user_data["_id"],
            "first_name": user_detail.get("first_name", "Unknown User") if user_detail else "Unknown User",
            "username": user_detail.get("username") if user_detail else None,
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
    
# --- FIX FOR NameError: name 'can_reply_to_chat' is not defined ---

def update_message_reply_cooldown(chat_id: int):
    """Updates the last message time for a chat to enforce reply cooldown."""
    chat_message_cooldowns[chat_id] = time.time()

async def can_reply_to_chat(chat_id: int):
    """
    Checks if the bot can reply to a message in the given chat based on the cooldown.
    Returns True if not on cooldown, False otherwise.
    """
    last_reply_time = chat_message_cooldowns.get(chat_id)
    if last_reply_time is None:
        return True
    
    # Use the MESSAGE_REPLY_COOLDOWN_TIME defined in config
    return (time.time() - last_reply_time) >= MESSAGE_REPLY_COOLDOWN_TIME

# --- NEW: BIOLINK EXCEPTIONS FUNCTIONS ---
async def check_biolink_exception(chat_id: int, user_id: int):
    """Check if user has biolink exception in specific chat"""
    try:
        exception_doc = biolink_exceptions_collection.find_one({"_id": chat_id})
        if exception_doc and "user_ids" in exception_doc:
            return user_id in exception_doc["user_ids"]
        return False
    except Exception as e:
        logger.error(f"Error checking biolink exception: {e}")
        return False

async def add_biolink_exception(chat_id: int, user_id: int):
    """Add user to biolink exceptions"""
    try:
        biolink_exceptions_collection.update_one(
            {"_id": chat_id},
            {"$addToSet": {"user_ids": user_id}},
            upsert=True
        )
        logger.info(f"User {user_id} added to biolink exceptions in chat {chat_id}")
        return True
    except Exception as e:
        logger.error(f"Error adding biolink exception: {e}")
        return False

async def remove_biolink_exception(chat_id: int, user_id: int):
    """Remove user from biolink exceptions"""
    try:
        biolink_exceptions_collection.update_one(
            {"_id": chat_id},
            {"$pull": {"user_ids": user_id}}
        )
        logger.info(f"User {user_id} removed from biolink exceptions in chat {chat_id}")
        return True
    except Exception as e:
        logger.error(f"Error removing biolink exception: {e}")
        return False

# --- NEW: PUNISHMENT SYSTEM FUNCTIONS ---
async def apply_punishment(client: Client, message: Message, violation_type: str):
    """Apply punishment based on group settings"""
    try:
        chat_id = message.chat.id
        user_id = message.from_user.id
        
        # Get punishment setting
        group_doc = group_tracking_collection.find_one({"_id": chat_id})
        punishment = group_doc.get("default_punishment", "delete") if group_doc else "delete"
        
        if punishment == "delete":
            await message.delete()
            await send_and_auto_delete_reply(message, 
                text=f"🚫 **{violation_type} not allowed!** Message deleted.")
                
        elif punishment == "mute":
            await message.delete()
            try:
                # Assuming ChatPermissions is imported from pyrogram.types
                await client.restrict_chat_member(chat_id, user_id, ChatPermissions())
                await send_and_auto_delete_reply(message,
                    text=f"🚫 **{violation_type} violation!** User muted.")
            except Exception as e:
                logger.error(f"Error muting user: {e}")
                
        elif punishment == "warn":
            await message.delete()
            # Add warn logic here
            await send_and_auto_delete_reply(message,
                text=f"⚠️ **Warning:** {violation_type} not allowed!")
                
        elif punishment == "ban":
            await message.delete()
            try:
                await client.ban_chat_member(chat_id, user_id)
                await send_and_auto_delete_reply(message,
                    text=f"⛔️ **Banned:** {violation_type} violation!")
            except Exception as e:
                logger.error(f"Error banning user: {e}")
                
    except Exception as e:
        logger.error(f"Error applying punishment: {e}")

# --- 🟢 नया कोड: टॉप ग्रुप्स और मंथली रीसेट (बदलाव 3) 🟢 ---

async def get_top_active_groups():
    """
    group_tracking_collection से मैसेज काउंट के आधार पर टॉप 5 ग्रुप्स फ़ेच करता है।
    """
    try:
        pipeline = [
            {"$match": {"total_message_count": {"$gt": 0}}},
            {"$sort": {"total_message_count": -1}},
            {"$limit": 5}
        ]
        top_groups_data = list(group_tracking_collection.aggregate(pipeline))
        
        top_group_details = []
        for group_data in top_groups_data:
            chat_id = group_data["_id"]
            owner_id = None
            owner_name = "Unknown"
            
            # ग्रुप ओनर को खोजने का प्रयास करें
            try:
                chat = await app.get_chat(chat_id)
                if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
                    async for member in app.get_chat_members(chat_id, filter=ChatMemberStatus.OWNER):
                        owner_id = member.user.id
                        owner_name = member.user.first_name
                        if member.user.username:
                            owner_name = f"@{member.user.username}"
                        break # ओनर मिल गया
            except Exception as e:
                logger.warning(f"ग्रुप {chat_id} के लिए ओनर नहीं मिला: {e}")

            top_group_details.append({
                "group_id": chat_id,
                "title": group_data.get("title", "Unknown Group"),
                "username": group_data.get("username"),
                "message_count": group_data.get("total_message_count", 0),
                "owner_id": owner_id,
                "owner_name": owner_name
            })
        
        logger.info(f"टॉप एक्टिव ग्रुप्स फ़ेच किए: {len(top_group_details)} results.")
        return top_group_details

    except Exception as e:
        logger.error(f"टॉप एक्टिव ग्रुप्स फ़ेच करने में एरर: {e}")
        return []

async def broadcast_to_winners(client: Client, top_groups: list):
    """
    जीतने वाले ग्रुप्स के ओनर्स को ब्रॉडकास्ट मैसेज भेजता है।
    (आपके अनुरोध के अनुसार टॉप 5 को)
    """
    logger.info("मंथली विनर्स को ब्रॉडकास्ट किया जा रहा है...")
    prize_map = {
        1: "₹90", 2: "₹60", 3: "₹30", 4: "₹10", 5: "₹10"
    }
    
    for i, group in enumerate(top_groups):
        rank = i + 1
        prize = prize_map.get(rank, "No Prize")
        owner_id = group.get("owner_id")
        
        if owner_id:
            message_text = (
                f"🎉 **बधाई हो!** 🎉\n\n"
                f"आपके ग्रुप, **{group['title']}**, ने इस महीने के एक्टिविटी लीडरबोर्ड में **रैंक {rank}** हासिल की है!\n\n"
                f"**आपका पुरस्कार:** **{prize}**\n\n"
                f"अपना इनाम लेने के लिए कृपया बॉट ओनर ({BOT_OWNER_USERNAME}) से संपर्क करें। इतने सक्रिय रहने के लिए धन्यवाद!"
            )
            try:
                await client.send_message(chat_id=owner_id, text=message_text)
                logger.info(f"ग्रुप {group['group_id']} के ओनर {owner_id} को विनर नोटिफिकेशन भेजा गया।")
            except Exception as e:
                logger.warning(f"ओनर {owner_id} को विनर नोटिफिकेशन भेजने में विफल: {e}")

async def reset_monthly_data(client: Client):
    """
    सभी मंथली काउंट्स को रीसेट करता है और विनर्स को ब्रॉडकास्ट करता है।
    """
    logger.info("मंथली रीसेट शुरू हो रहा है...")
    
    # 1. रीसेट से पहले विनर्स की लिस्ट लें
    top_5_groups = await get_top_active_groups()
    
    # 2. यूजर की कमाई रीसेट करें
    earning_tracking_collection.update_many(
        {},
        {"$set": {"group_message_count": 0}}
    )
    
    # 3. ग्रुप काउंट्स रीसेट करें
    group_tracking_collection.update_many(
        {},
        {"$set": {"total_message_count": 0}}
    )
    
    logger.info("मंथली कमाई और ग्रुप मैसेज काउंट सफलतापूर्वक रीसेट हो गए।")
    
    # 4. विनर्स (टॉप 5) को ब्रॉडकास्ट करें
    await broadcast_to_winners(client, top_5_groups)
    
    # 5. रीसेट स्टेटस अपडेट करें
    now = datetime.now(pytz.timezone('Asia/Kolkata'))
    reset_status_collection.update_one(
        {"_id": "last_auto_reset"},
        {"$set": {"last_reset_timestamp": now, "month": now.month, "year": now.year}},
        upsert=True
    )
    logger.info("मंथली रीसेट पूरा हुआ और स्टेटस अपडेट हो गया।")

async def check_and_perform_monthly_reset(client: Client):
    """
    चेक करता है कि क्या नया महीना शुरू हो गया है और रीसेट ट्रिगर करता है।
    बॉट के स्टार्टअप पर कॉल किया जाना है।
    """
    now = datetime.now(pytz.timezone('Asia/Kolkata'))
    current_month = now.month
    current_year = now.year
    
    status = reset_status_collection.find_one({"_id": "last_auto_reset"})
    
    if status:
        last_reset_month = status.get("month")
        last_reset_year = status.get("year")
        
        # चेक करें कि क्या इस महीने और साल के लिए रीसेट पहले ही हो चुका है
        if last_reset_month == current_month and last_reset_year == current_year:
            logger.info(f"{current_month}/{current_year} के लिए मंथली रीसेट पहले ही हो चुका है। स्किप कर रहे हैं।")
            return
    
    # यदि कोई स्टेटस नहीं है, या यदि यह नया महीना है, तो रीसेट करें
    logger.info(f"नया महीना ({current_month}/{current_year}) मिला। ऑटो-रीसेट किया जा रहा है।")
    await reset_monthly_data(client)
    
# --- 🟢 नए कोड का अंत 🟢 ---

# main.py

import threading
import logging
from pyrogram import idle
import nltk
import os
import sys

# NLTK data download check and setup
try:
    # Set the NLTK data path to a writeable directory within the workspace.
    # This is important for platforms like Koyeb where root access is limited.
    data_dir = os.path.join(os.getcwd(), '.nltk_data')
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    nltk.data.path.append(data_dir)

    # First, try to find the lexicon. This will raise a LookupError if not found.
    nltk.data.find('sentiment/vader_lexicon.zip')
    print("vader_lexicon is already downloaded.")
except LookupError:
    # If a LookupError occurs, it means the data needs to be downloaded.
    print("vader_lexicon not found. Downloading now...")
    
    # Set the NLTK data path and then download the lexicon.
    nltk.download('vader_lexicon', download_dir=data_dir)
    print("Download complete.")
except Exception as e:
    # Handle any other unexpected errors gracefully.
    print(f"An unexpected error occurred: {e}", file=sys.stderr)
    sys.exit(1)

# Import necessary components from other files
from config import app, logger, flask_app
from web import run_flask_app

# It's important to import commands and events so Pyrogram can register the handlers
import commands
import events
import broadcast_handler # 🌟 नई ब्रॉडकास्ट फ़ाइल इम्पोर्ट की गई 🌟

if __name__ == "__main__":
    logger.info("Starting Flask health check server in a separate thread...")
    flask_thread = threading.Thread(target=run_flask_app)
    flask_thread.start()

    logger.info("Starting Pyrogram bot...")
    app.run()
    
    # Keep the bot running indefinitely
    idle()

    # End of bot code. Thank you for using! Made with ❤️ by @asbhaibsr
