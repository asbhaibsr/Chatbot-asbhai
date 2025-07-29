# utils.py

import re
import asyncio
import random
import logging
from datetime import datetime
from pyrogram import Client
from pyrogram.types import Message
from pyrogram.raw.functions.messages import SetTyping
from pyrogram.raw.types import SendMessageTypingAction

# Import necessary collections and app from config
from config import (
    messages_collection, owner_taught_responses_collection, conversational_learning_collection, app, logger, OWNER_ID
)

def extract_keywords(text):
    """Extracts unique keywords from a given text."""
    if not text:
        return []
    words = re.findall(r'\b\w+\b', text.lower())
    return list(set(words))

async def store_message(message: Message):
    """Stores user messages for learning purposes, excluding bot messages and commands."""
    try:
        # Skip messages sent by the bot itself
        if message.from_user and message.from_user.is_bot:
            logger.debug(f"Skipping storage for message from bot: {message.from_user.id}.")
            return

        # Skip command messages
        is_command = message.text and message.text.startswith('/')
        if is_command:
            logger.debug(f"Skipping storage for command: {message.text}.")
            return
        
        message_data = {
            "message_id": message.id,
            "user_id": message.from_user.id if message.from_user else None,
            "username": message.from_user.username if message.from_user else None,
            "first_name": message.from_user.first_name if message.from_user else None,
            "chat_id": message.chat.id,
            "chat_type": message.chat.type.name,
            "timestamp": datetime.now(),
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
            logger.debug(f"Unsupported message type for storage: {message.id}.")
            return # Do not store if message type is not supported
        
        messages_collection.insert_one(message_data)
        logger.info(f"Message stored: {message.id} from {message.from_user.id if message.from_user else 'None'}.")

    except Exception as e:
        logger.error(f"Error storing message {message.id}: {e}.")

async def generate_reply(message: Message):
    """Generates a reply based on learned patterns or owner-taught responses."""
    await app.invoke(
        SetTyping(
            peer=await app.resolve_peer(message.chat.id),
            action=SendMessageTypingAction()
        )
    )
    await asyncio.sleep(0.5)

    if not message.text and not message.sticker:
        return None

    query_content = message.text if message.text else (message.sticker.emoji if message.sticker else "")
    
    # Prioritize replies to the bot's own previous messages for conversational flow
    if message.reply_to_message and message.reply_to_message.from_user and message.reply_to_message.from_user.is_self:
        original_bot_message_content = message.reply_to_message.text if message.reply_to_message.text else (message.reply_to_message.sticker.emoji if message.reply_to_message.sticker else "")
        if original_bot_message_content:
            conversational_doc = conversational_learning_collection.find_one({"trigger": {"$regex": f"^{re.escape(original_bot_message_content)}$", "$options": "i"}})
            if conversational_doc and conversational_doc.get('responses'):
                chosen_response_data = random.choice(conversational_doc['responses'])
                logger.info(f"Bot-replied contextual reply found for '{original_bot_message_content}'.")
                return chosen_response_data
    
    # Prioritize owner-taught responses
    owner_taught_doc = owner_taught_responses_collection.find_one({"trigger": {"$regex": f"^{re.escape(query_content)}$", "$options": "i"}})
    if owner_taught_doc and owner_taught_doc.get('responses'):
        chosen_response_data = random.choice(owner_taught_doc['responses'])
        logger.info(f"Owner-taught reply found for '{query_content}'.")
        return chosen_response_data
    
    # Then, conversational learning responses
    conversational_doc = conversational_learning_collection.find_one({"trigger": {"$regex": f"^{re.escape(query_content)}$", "$options": "i"}})
    if conversational_doc and conversational_doc.get('responses'):
        chosen_response_data = random.choice(conversational_doc['responses'])
        logger.info(f"Conversational reply found for '{query_content}'.")
        return chosen_response_data

    logger.info(f"No specific learning pattern found for '{query_content}'. Falling back to keyword search.")

    # Fallback to keyword-based general replies
    query_keywords = extract_keywords(query_content)
    if query_keywords:
        keyword_regex = "|".join([re.escape(kw) for kw in query_keywords])
        general_replies_cursor = messages_collection.find({
            "type": {"$in": ["text", "sticker"]},
            "content": {"$regex": f".*({keyword_regex}).*", "$options": "i"},
            "user_id": {"$ne": app.me.id} # Exclude bot's own messages
        })
    else:
        general_replies_cursor = messages_collection.find({
            "type": {"$in": ["text", "sticker"]},
            "user_id": {"$ne": app.me.id} # Exclude bot's own messages
        })

    potential_replies = []
    for doc in general_replies_cursor:
        potential_replies.append(doc)

    if potential_replies:
        chosen_reply = random.choice(potential_replies)
        logger.info(f"Keyword-based fallback reply found for '{query_content}': {chosen_reply.get('content') or chosen_reply.get('sticker_id')}.")
        return chosen_reply

    logger.info(f"No suitable reply found for: '{query_content}'.")
    return None

async def send_reply(message: Message, text: str = None, photo: str = None):
    """Sends a reply to the user, either text or photo."""
    if photo:
        await message.reply_photo(photo=photo, caption=text)
    elif text:
        await message.reply_text(text)
    else:
        logger.warning(f"send_reply called with no text or photo for message {message.id}.")

