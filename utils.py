# utils.py

import re
import asyncio
import time
import logging
import random
from datetime import datetime, timedelta

import pytz
from pyrogram import Client
from pyrogram.types import Message, InlineKeyboardMarkup
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
    logger.warning("g4f library not found. Tier 0.5 AI will be disabled.")
# google.genai has been REMOVED.

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

# Bot ID is set to None globally and fetched in functions, fixing the 'AttributeError'
BOT_USER_ID_PLACEHOLDER = None 

# Initialize sentiment analyzer
analyser = SentimentIntensityAnalyzer()

# Advanced AI/NLP Tools (Set to None for stability)
nlp = None
semantic_model = None
GEMINI_CLIENT = None

# --- CORE UTILITY FUNCTIONS ---

# Renaming the main send/delete function back to the expected name for 'events.py'
async def delete_after_delay_for_message(message: Message, text: str = None, photo: str = None, sticker: str = None, reply_markup: InlineKeyboardMarkup = None, parse_mode: ParseMode = ParseMode.MARKDOWN, disable_web_page_preview: bool = False):
    """
    Sends a reply and sets a task to auto-delete both the command and the reply after a delay.
    This function name is kept for compatibility with events.py
    NOTE: In events.py, the wrapper 'send_and_auto_delete_reply' is now using this utility function.
    """
    sent_message = None
    user_info_str = ""
    
    # Simplified text prep logic (keeping the core functionality intact)
    text_to_send = text
    if message.command and text:
        command_name = message.command[0]
        user_info_str = ""
        if message.from_user:
            user_info_str = f" (द्वारा: @{message.from_user.username})" if message.from_user.username else f" (द्वारा: {message.from_user.first_name})"
        text_to_send = f"**कमांड:** `{command_name}`{user_info_str}\n\n{text}"

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
        logger.warning(f"delete_after_delay_for_message called with no content for message {message.id}.")
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

# Renaming the new function for use in the rest of the code for clarity
# Removed the duplicate function definition here to avoid issues, relying on the single definition above.


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
        # However, calling this function in commands.py caused issues.
        # We rely on the commands.py to remove the call to this, or if needed,
        # manually call update_user_info/update_group_info in commands.py
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
            # You requested bot's response pattern also to be saved, but typically that's saved by the AI response flow.
            # Keeping the U2U logic as it's the core of organic learning.

            if is_u2u_conv and last_message.get("type") == "text" and current_message_type == "text":
                
                trigger_content = last_message["content"].lower().strip() # Store trigger in lowercase for flexible matching
                reply_content = current_message_content.strip()
                
                # Check with AI (MongoDB not necessary, local check is sufficient for now)
                # You requested AI check on save, but for learning patterns, direct save is standard.
                # The AI check will happen during the response generation (TIER 0.5/0).

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

        await prune_old_messages()

    except Exception as e:
        logger.error(f"Error storing message {message.id}: {e}.")

# --- NEW: AI Personality Prompt Generator ---
def get_ai_role_prompt(ai_mode: str):
    base_prompt = "Tum ek friendly, casual, young female bot ho. Hinglish (Hindi + English) me chote aur natural sentences me reply karo. Real logo ki tarah hi likhna, zaroori nahi ki har jagah sahi commas ya punctuation ho. Jaise log aam taur par chat karte hain, waise hi karo. Sirf chat ke liye reply karna."
    
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
    
    await app.invoke(SetTyping(peer=await app.resolve_peer(message.chat.id), action=SendMessageTypingAction()))
    await asyncio.sleep(0.5)

    query_content = message.text.strip().lower() # Use lower case for matching
    query_type = "text"
    user_id = message.from_user.id if message.from_user else None
    chat_id = message.chat.id
    current_context = chat_contexts.get(chat_id, []) 
    
    # Check if bot is enabled in the group
    group_doc = group_tracking_collection.find_one({"_id": chat_id})
    bot_enabled = group_doc.get("bot_enabled", True) if group_doc else True
    if not bot_enabled:
        return {"type": None}
    
    # Check if a reply is on cooldown
    if not await can_reply_to_chat(chat_id):
        logger.info(f"Reply suppressed for chat {chat_id} due to cooldown.")
        return {"type": None}
        
    # --- TIER 1: Pattern Matching (Learned Conversations - HIGHEST PRIORITY) ---
    docs = list(conversational_learning_collection.find({"trigger_type": query_type, "trigger_content": query_content})) # Exact match first
    
    # If no exact match, try fuzzy match on keywords for a more random reply (as requested)
    if not docs:
        query_keywords = extract_keywords(query_content)
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
            score = fuzz.token_set_ratio(query_content, doc.get("trigger_content", "").lower())
            
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
    ai_reply_text_tier0_5 = await generate_g4f_response_tier0_5(app, message.text.strip(), chat_id, current_context)
    if ai_reply_text_tier0_5 and random.random() < 0.9: # High chance to use g4f
        logger.info(f"TIER 0.5: Using g4f Free LLM: {ai_reply_text_tier0_5}")
        update_message_reply_cooldown(chat_id)
        return {"type": "text", "content": ai_reply_text_tier0_5}
            
    # --- TIER 0: Enhanced Contextual Responder (Rule-Based Human Feel) ---
    ai_reply_text_tier0 = generate_best_contextual_response_tier0(message.text.strip(), current_context)
    if ai_reply_text_tier0: 
        logger.info(f"TIER 0: Falling back to Enhanced Contextual AI: {ai_reply_text_tier0}")
        update_message_reply_cooldown(chat_id)
        return {"type": "text", "content": ai_reply_text_tier0}
            
    
    # --- TIER 2: NLTK/TextBlob Advanced Fallback (Free AI 1 - Sentiment) ---
    ai_reply_text_tier2 = generate_free_ai_response_tier2(message.text.strip())
    logger.info(f"TIER 2: Falling back to NLTK/TextBlob Advanced AI: {ai_reply_text_tier2}")
    update_message_reply_cooldown(chat_id)
    return {"type": "text", "content": ai_reply_text_tier2}

    # --- TIER 3: Powerful Free AI Fallback (Simple LLM Mock - Keywords) ---
    if random.random() < 0.5:
        ai_reply_text_tier3 = generate_powerful_free_ai_response_tier3(message.text.strip())
        logger.info(f"TIER 3: Falling back to MOCK Powerful Free AI: {ai_reply_text_tier3}")
        update_message_reply_cooldown(chat_id)
        return {"type": "text", "content": ai_reply_text_tier3}

    # --- TIER 4: Dynamic reply using Markov chain (Lowest Priority - Minimal Chance) ---
    if current_context and random.random() < 0.05:
        chain = build_markov_chain(current_context)
        if chain:
            dynamic_reply_text = generate_sentence(chain)
            if dynamic_reply_text and dynamic_reply_text.lower() not in query_content: 
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
