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

# NEW FREE AI/NLP LIBRARY IMPORTS
from fuzzywuzzy import fuzz 

# Recruitment (Naye AI/NLP tools ke imports)
try:
    import google.genai as genai
    from google.genai.errors import APIError
except ImportError:
    genai = None

try:
    from sentence_transformers import SentenceTransformer, util
    import spacy
except ImportError:
    SentenceTransformer, util, spacy = None, None, None

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
BOT_USER_ID_PLACEHOLDER = app.me.id

# Initialize sentiment analyzer
analyser = SentimentIntensityAnalyzer()

# --- RECRUITMENT: Initialize Advanced AI/NLP Tools ---
nlp = None
if spacy:
    try:
        # Note: 'en_core_web_sm' must be downloaded via terminal: python -m spacy download en_core_web_sm
        nlp = spacy.load("en_core_web_sm")
        logger.info("SpaCy NLP Model loaded for advanced entity extraction.")
    except Exception as e:
        logger.warning(f"Error loading SpaCy: {e}. Advanced NLP disabled.")

semantic_model = None
if SentenceTransformer:
    try:
        # Note: This model downloads the first time it runs
        semantic_model = SentenceTransformer('all-MiniLM-L6-v2') 
        logger.info("Sentence Transformer Model loaded for semantic matching.")
    except Exception as e:
        logger.warning(f"Error loading Sentence Transformer: {e}. Semantic matching disabled.")

GEMINI_CLIENT = None
if genai:
    try:
        # Assuming GEMINI_API_KEY is available in your environment or config
        GEMINI_CLIENT = genai.Client()
        logger.info("Gemini Client initialized and ready.")
    except Exception as e:
        logger.error(f"Gemini Client failed to initialize: {e}. Falling back to mock Tiers.")

# --- CORE UTILITY FUNCTIONS ---

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
        
    return final_sentence.replace(" i ", " I ")

def extract_keywords(text):
    if not text:
        return []
    words = re.findall(r'\b\w+\b', text.lower())
    stop_words = {"ko", "ke", "ka", "ki", "mein", "main", "hai", "tha", "the", "aur", "ya", "ek", "tum"}
    filtered_words = [w for w in words if w not in stop_words and len(w) > 2]
    
    # NEW: Use SpaCy for better entity/keyword extraction if available
    if nlp:
        doc = nlp(text)
        # Add Noun Phrases and Named Entities
        filtered_words.extend([chunk.text.lower() for chunk in doc.noun_chunks])
        filtered_words.extend([ent.text.lower() for ent in doc.ents])
        
    return list(set(filtered_words))

async def prune_old_messages():
    # ... (Pruning logic as before) ...
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
        if message.from_user and (message.from_user.is_bot or message.text.startswith('/')):
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
        
        # --- User-to-User Conversation Pattern Storage (Learning) ---
        if len(chat_contexts[chat_id]) >= 1:
            last_message = chat_contexts[chat_id][-1]
            last_user_id = last_message.get("user_id")
            
            if (last_user_id is not None and last_user_id != current_user_id and 
                last_user_id != BOT_USER_ID_PLACEHOLDER and current_user_id != BOT_USER_ID_PLACEHOLDER and
                last_message.get("type") == "text" and current_message_type == "text"):
                
                trigger_content = last_message["content"]
                reply_content = current_message_content
                
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
            "type": "text",
            "content": current_message_content,
            "keywords": extract_keywords(current_message_content),
            "credits": "Code by @asbhaibsr"
        }
        
        messages_collection.insert_one(message_data)

        # --- Earning Tracking Logic (Simplified) ---
        if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP] and message.from_user and not message.from_user.is_bot:
            user_id_to_track = message.from_user.id
            if time.time() - earning_cooldowns.get(user_id_to_track, 0) >= 8:
                earning_cooldowns[user_id_to_track] = time.time()
                earning_tracking_collection.update_one(
                    {"_id": user_id_to_track},
                    {"$inc": {"group_message_count": 1}, "$set": {"last_active_group_message": datetime.now()}},
                    upsert=True
                )

        await prune_old_messages()

    except Exception as e:
        logger.error(f"Error storing message {message.id}: {e}.")


# --- TIER 0.5 AI Function (Mocking External LLM like Gemini/ChatGPT) ---
def generate_external_llm_mock_tier0_5(text: str, context: list):
    """Mocks a complex, detailed, and high-quality response, or uses real Gemini if available."""
    
    # 1. NEW: Real Gemini Call (If client is initialized)
    if GEMINI_CLIENT:
        try:
            # Build history for context
            history = "\n".join([f"{'User' if m['user_id'] != BOT_USER_ID_PLACEHOLDER else 'Bot'}: {m['content']}" for m in context])
            prompt = f"You are a friendly, casual, young female bot. Continue this conversation in Hindi/Hinglish. Previous chat:\n{history}\n\nUser: {text}\n\nYour Reply:"
            
            response = GEMINI_CLIENT.models.generate_content(
                model='gemini-2.5-flash', # Use a fast model
                contents=prompt
            )
            return response.text
        except APIError as e:
            logger.error(f"Gemini API Error: {e}")
        except Exception as e:
            logger.error(f"Gemini generation failed: {e}")

    # 2. Mock Logic Fallback (If Gemini is not available)
    last_message = text.lower()
    
    if "kyun" in last_message or "kaise" in last_message or "matlab" in last_message or len(text.split()) > 7:
        return "Accha, tum iska **reason** puchh rahe ho. Dekho, iske peeche ka main logic yeh hai ki... [**High-quality explanation logic here**]. Kya tum is baat se sehmat ho? 🧐"
    
    if len(context) >= 2:
        previous_msg = context[-2].get('content', '').lower()
        if "achha" in previous_msg and "aur" in last_message:
             return "Hmm... aur? Aur kya ho raha hai? Thoda aur detail mein batao, sunke achha lag raha hai. 😊"

    return None

# --- TIER 0 AI Function (Enhanced Contextual Responder - Real Human Feel) ---
def generate_best_contextual_response_tier0(text: str, chat_context: list):
    """Generates a highly contextual response based on rules and sentiment."""
    keywords = extract_keywords(text)
    sentiment = get_sentiment(text)
    last_message = text.lower()
    
    previous_msg_content = chat_context[-2]['content'].lower() if len(chat_context) >= 2 and chat_context[-2].get('type') == 'text' else ""
    
    if "kiya kr rha ho" in last_message or "kya chal rha hai" in last_message:
        return random.choice(["Bas tumhari baaton ka intezaar kar rahi thi. Tum batao, kya khaas hai aaj? 😃", "Kuch naya nahi, normal chatting. Tum kya kar rahe ho? ☕"])
    
    if "hello" in last_message or "hi" in last_message:
        return random.choice(["Hey! Bolo, kya baat hai? 😊", "Hi! Kya haal hai?"])

    if sentiment == "positive":
        if "achha" in last_message or "badhiya" in last_message:
            return f"Wah! {random.choice(keywords).capitalize() if keywords else 'yeh'} sunke dil khush ho gaya. Kya hua, zara detail mein batao! ✨"
        return "Awesome! Main bohot khush hoon tumhare liye. 👍"
         
    if sentiment == "negative":
        if previous_msg_content and 'parshan' in previous_msg_content: 
            return "Mujhe pata hai tum upset ho. Par smile karo na. Main hamesha tumhare saath hoon. ❤️"
        return "Oh no! Kya hua? Mujhse share karo, thoda halka mehsoos hoga. 🥺"
        
    if keywords and previous_msg_content and not any(k in previous_msg_content for k in keywords):
        return f"{random.choice(keywords).capitalize()} ke baare mein? Tumne abhi {previous_msg_content[:15]}... bola tha. Kya woh isi se juda hai? 🤔"
        
    return random.choice(["Thoda aur clear batao. Main samjhne ki koshish kar rahi hoon. 🙏", "Interesting point hai, ispe aur kya discuss kar sakte hain?"])

# --- TIER 2 AI Fallback Function (Advanced NLTK/TextBlob) ---
def generate_free_ai_response_tier2(text: str):
    sentiment = get_sentiment(text)
    keywords = extract_keywords(text)
    
    if sentiment == "positive":
        if random.random() < 0.6 and keywords:
             return f"वाह! यह सुनकर मुझे बहुत खुशी हुई। {random.choice(keywords).capitalize()} के बारे में और बताओ ना? ✨"
        else:
             return random.choice(["हाँ, यह तो शानदार है! मैं भी बहुत खुश हूँ! 😍", "अरे वाह! बहुत बढ़िया!"])
             
    elif sentiment == "negative":
        return random.choice(["कोई बात नहीं, कभी-कभी ऐसा होता है। चिल! 😊", "परेशान मत हो, मैं तुम्हारे साथ हूँ। ❤️"])
        
    elif sentiment == "neutral" and keywords:
        return f"{random.choice(keywords).capitalize()}? हाँ, मैंने भी इसके बारे में सुना है। तुम क्या सोच रहे हो इसके बारे में?"
        
    else:
        return random.choice(["अच्छा! फिर क्या हुआ?", "और बताओ, क्या चल रहा है?", "hmm... 🙄"])

# --- TIER 3 AI Fallback Function (Simple LLM Mock) ---
def generate_powerful_free_ai_response_tier3(text: str):
    keywords = extract_keywords(text)
    sentiment = get_sentiment(text)
    
    if keywords:
        response_templates = [
            f"तुम्हारी बात {random.choice(keywords)} के बारे में है, है ना? 🤔",
            f"यह {random.choice(keywords)} वाला टॉपिक सच में सोचने वाला है। "
        ]
        if sentiment == "positive":
            return random.choice(response_templates) + " मुझे उम्मीद है सब अच्छा होगा! 👍"
        return random.choice(response_templates)
    
    return "यह सवाल थोड़ा मुश्किल है। तुम किस संदर्भ में पूछ रहे हो?"


async def generate_reply(message: Message):
    if message.reply_to_message and message.reply_to_message.from_user and not message.reply_to_message.from_user.is_self:
        return {"type": None}
    
    await app.invoke(SetTyping(peer=await app.resolve_peer(message.chat.id), action=SendMessageTypingAction()))
    await asyncio.sleep(0.5)

    if not message.text:
        return {"type": None}

    query_content = message.text
    query_type = "text"
    user_id = message.from_user.id if message.from_user else None
    current_context = chat_contexts.get(message.chat.id, []) 
    
    def score_response(response_doc, query):
        trigger = response_doc.get("trigger_content", "")
        if not trigger or query_type != 'text': return 0
        
        # Enhanced Score: Semantic (if available) + Fuzzy
        fuzzy_score = fuzz.token_set_ratio(query.lower(), trigger.lower())
        
        if semantic_model:
            try:
                # Calculate semantic similarity (more meaningful match)
                embeddings1 = semantic_model.encode(query, convert_to_tensor=True)
                embeddings2 = semantic_model.encode(trigger, convert_to_tensor=True)
                semantic_similarity = util.cos_sim(embeddings1, embeddings2).item() * 100
                # Use a blend, prioritizing the higher score
                score = max(fuzzy_score, semantic_similarity)
            except Exception as e:
                logger.warning(f"Semantic scoring failed: {e}. Using Fuzzy score.")
                score = fuzzy_score
        else:
            score = fuzzy_score
        
        return 101 if score >= 99 else int(score) # Max 101 for perfect match


    # --- TIER 0.5: External LLM Mock (Highest Priority AI - Contextual) ---
    ai_reply_text_tier0_5 = generate_external_llm_mock_tier0_5(query_content, current_context)
    if ai_reply_text_tier0_5 and random.random() < 0.6: 
        logger.info(f"TIER 0.5: Falling back to External LLM/Gemini AI: {ai_reply_text_tier0_5}")
        return {"type": "text", "content": ai_reply_text_tier0_5}
            
    # --- TIER 0: Enhanced Contextual Responder (Real Human Feel AI) ---
    ai_reply_text_tier0 = generate_best_contextual_response_tier0(query_content, current_context)
    if ai_reply_text_tier0: 
        logger.info(f"TIER 0: Falling back to Enhanced Contextual AI: {ai_reply_text_tier0}")
        return {"type": "text", "content": ai_reply_text_tier0}
            
    # --- TIER 1: Pattern Matching (Learning System - High Similarity) ---
    docs = list(conversational_learning_collection.find({"trigger_type": query_type, "trigger_content": {"$exists": True, "$ne": None}}))
    all_responses = []

    if query_type == "text":
        for doc in docs:
            score = score_response(doc, query_content)
            if score >= 90: # High similarity needed for pattern match
                for response in doc.get('responses', []):
                    if response['type'] == 'text':
                        all_responses.append({"data": response, "score": score, "source_doc": doc})

        if all_responses:
            highest_score = max(r['score'] for r in all_responses)
            best_responses = [r for r in all_responses if r['score'] >= highest_score]
            user_specific_responses = [r for r in best_responses if r['data'].get("user_pattern_source_id") == user_id]
            chosen_list = user_specific_responses if user_specific_responses else best_responses
            
            chosen_response = random.choice(chosen_list)['data']
            logger.info(f"TIER 1 (Pattern Match) found. Score: {highest_score}.")
            return {"type": "text", "content": chosen_response.get('content')}
    
    # --- TIER 2: NLTK/TextBlob Advanced Fallback (Free AI 1) ---
    ai_reply_text_tier2 = generate_free_ai_response_tier2(query_content)
    logger.info(f"TIER 2: Falling back to NLTK/TextBlob Advanced AI: {ai_reply_text_tier2}")
    return {"type": "text", "content": ai_reply_text_tier2}

    # --- TIER 3: Powerful Free AI Fallback (Simple LLM Mock) ---
    if random.random() < 0.5:
        ai_reply_text_tier3 = generate_powerful_free_ai_response_tier3(query_content)
        logger.info(f"TIER 3: Falling back to MOCK Powerful Free AI: {ai_reply_text_tier3}")
        return {"type": "text", "content": ai_reply_text_tier3}

    # --- TIER 4: Dynamic reply using Markov chain (Lowest Priority - Minimal Chance) ---
    if current_context and random.random() < 0.05: # Chance 0.1 se 0.05 kiya
        chain = build_markov_chain(current_context)
        if chain:
            dynamic_reply_text = generate_sentence(chain)
            if dynamic_reply_text and dynamic_reply_text not in query_content: 
                logger.info("TIER 4: Generating dynamic reply from chat history (Markov).")
                return {"type": "text", "content": dynamic_reply_text}
    
    # --- TIER 5: Final Fallback (Simple Text) ---
    logger.info("TIER 5: Final Text Fallback.")
    return {"type": "text", "content": "Mujhe is baare mein abhi aur seekhne ki zaroorat hai. Tum kya soch rahe ho?"}

# --- REST OF THE UTILITY FUNCTIONS ---
# (is_admin_or_owner, contains_link, contains_mention, update_group_info, update_user_info, etc. are assumed to be here, unmodified from the original structure)
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
# --- END OF UTILITY.PY ---
