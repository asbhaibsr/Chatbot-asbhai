# music_bot_module.py

import os
import asyncio
import logging
import yt_dlp
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.raw.functions.messages import SetTyping
from pyrogram.raw.types import SendMessageTypingAction
from pyrogram.enums import ChatType, ChatMemberStatus, ParseMode

# For streaming audio
from pyrogram.errors import FloodWait

# A simple in-memory queue for each chat
# {chat_id: [{"title": "song title", "file_path": "path/to/file", "url": "youtube_url"}]}
music_queues = {}
# To keep track of the current playing task for each chat
# {chat_id: asyncio.Task | None}
current_playing_tasks = {}

# Logger for music module
music_logger = logging.getLogger("music_bot_module")
music_logger.setLevel(logging.INFO)

# --- Utility Functions for Music Bot ---

async def send_and_auto_delete_music_reply(message: Message, text: str = None, reply_markup: InlineKeyboardMarkup = None, parse_mode: ParseMode = ParseMode.MARKDOWN):
    """Sends a reply and schedules it for deletion after 2 minutes."""
    sent_message = None
    if text:
        sent_message = await message.reply_text(
            text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
            disable_web_page_preview=True
        )
    else:
        music_logger.warning(f"send_and_auto_delete_music_reply called with no text for message {message.id}.")
        return None

    async def delete_after_delay_task():
        await asyncio.sleep(120)  # Delete after 2 minutes (120 seconds)
        try:
            if sent_message:
                await sent_message.delete()
        except Exception as e:
            music_logger.warning(f"Failed to delete music reply message {sent_message.id if sent_message else 'N/A'} in chat {message.chat.id}: {e}")

    asyncio.create_task(delete_after_delay_task())
    return sent_message

def get_ytdl_options(output_path="downloads/"):
    """Returns yt-dlp options for downloading audio."""
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    return {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'logger': music_logger,
        'progress_hooks': [lambda d: music_logger.info(f"YTDL Progress: {d['status']} - {d.get('filename', '')}")],
        'verbose': False,
        'noplaylist': True,
        'nocheckcertificate': True,
        'ignoreerrors': True,
        'no_warnings': True,
        'default_search': 'ytsearch', # Search YouTube by default
    }

async def download_audio(query: str):
    """Downloads audio from YouTube based on a search query or URL."""
    try:
        ydl_opts = get_ytdl_options()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=False)
            if 'entries' in info:
                info = info['entries'][0] # Take the first result if it's a search
            
            # Ensure the file path uses the actual downloaded filename
            filepath_without_ext = ydl.prepare_filename(info)
            final_filepath = f"{filepath_without_ext}.mp3" # Assuming mp3 post-processing

            # Check if file already exists to avoid re-downloading
            if os.path.exists(final_filepath):
                music_logger.info(f"File already exists, skipping download: {final_filepath}")
                return {
                    "title": info.get('title', 'Unknown Title'),
                    "file_path": final_filepath,
                    "url": info.get('webpage_url', 'N/A')
                }

            # Download the file
            ydl.download([query])
            music_logger.info(f"Downloaded: {final_filepath}")

            return {
                "title": info.get('title', 'Unknown Title'),
                "file_path": final_filepath,
                "url": info.get('webpage_url', 'N/A')
            }
    except yt_dlp.utils.DownloadError as e:
        music_logger.error(f"Download Error: {e}")
        return None
    except Exception as e:
        music_logger.error(f"An unexpected error occurred during download: {e}")
        return None

async def play_next_song(client: Client, message: Message):
    chat_id = message.chat.id
    if chat_id not in music_queues or not music_queues[chat_id]:
        music_logger.info(f"Queue empty for chat {chat_id}.")
        current_playing_tasks[chat_id] = None # Clear the task if queue is empty
        await send_and_auto_delete_music_reply(message, "संगीत की कतार खाली है! और गाने जोड़ो! 🎵")
        return

    song = music_queues[chat_id].pop(0)
    title = song["title"]
    file_path = song["file_path"]

    try:
        await send_and_auto_delete_music_reply(message, f"🔊 अब चल रहा है: **{title}** 🎶\n\n_अगला गाना 2 मिनट में चलेगा।_", parse_mode=ParseMode.MARKDOWN)
        await client.send_audio(
            chat_id=chat_id,
            audio=file_path,
            title=title,
            caption=f"🎵 **{title}**\n[Source]({song['url']}) | Powered by @asbhaibsr Music",
            parse_mode=ParseMode.MARKDOWN
        )
        music_logger.info(f"Started playing: {title} in chat {chat_id}")
    except FloodWait as e:
        music_logger.warning(f"FloodWait encountered: {e.value} seconds. Retrying after delay.")
        await asyncio.sleep(e.value)
        # Recursively call to try playing again after floodwait
        await play_next_song(client, message)
        return
    except Exception as e:
        music_logger.error(f"Error playing song {title} in chat {chat_id}: {e}")
        await send_and_auto_delete_music_reply(message, f"गाना बजाने में कोई दिक्कत हुई: {title}. 🤔 अगला गाना ट्राई कर रही हूँ...")
        
    finally:
        # Clean up the downloaded file after playing
        if os.path.exists(file_path):
            os.remove(file_path)
            music_logger.info(f"Deleted downloaded file: {file_path}")

        # Schedule the next song only if there are more songs in the queue
        if music_queues[chat_id]:
            # This ensures next song plays after current one finishes (or after a fixed delay if audio length is unknown)
            # For simplicity, we'll use a fixed delay here. In a real bot, you'd monitor audio stream end.
            await asyncio.sleep(10) # Small delay before playing next song
            current_playing_tasks[chat_id] = asyncio.create_task(play_next_song(client, message))
        else:
            current_playing_tasks[chat_id] = None
            music_logger.info(f"Music queue finished for chat {chat_id}.")
            await send_and_auto_delete_music_reply(message, "सभी गाने बज चुके हैं! आशा है आपको पसंद आए होंगे! 😊")

# --- Music Bot Commands ---

@Client.on_message(filters.command("play") & (filters.group | filters.private))
async def play_command(client: Client, message: Message):
    await client.invoke(
        SetTyping(
            peer=await client.resolve_peer(message.chat.id),
            action=SendMessageTypingAction()
        )
    )
    await asyncio.sleep(0.5)

    if len(message.command) < 2:
        await send_and_auto_delete_music_reply(message, "कोई गाना बताओ तो सही! 🎵 `/play <गाना या YouTube लिंक>` (जैसे: `/play Despacito` या `/play https://youtu.be/kJQP7kiw5Fk`)")
        return

    query = " ".join(message.command[1:])
    chat_id = message.chat.id

    await send_and_auto_delete_music_reply(message, f"आपका गाना ढूंढ रही हूँ: **{query}**... थोड़ा इंतजार करो, डार्लिंग! ⏳", parse_mode=ParseMode.MARKDOWN)
    
    song_info = await download_audio(query)

    if not song_info:
        await send_and_auto_delete_music_reply(message, f"अरे नहीं! 😟 मुझे **'{query}'** के लिए कोई गाना नहीं मिला या डाउनलोड नहीं कर पाई. कुछ और ट्राई करो, प्लीज़!")
        return

    if chat_id not in music_queues:
        music_queues[chat_id] = []

    music_queues[chat_id].append(song_info)
    
    if current_playing_tasks.get(chat_id) and not current_playing_tasks[chat_id].done():
        await send_and_auto_delete_music_reply(message, f"🎶 गाना **'{song_info['title']}'** कतार में जोड़ दिया गया है! कतार में कुल {len(music_queues[chat_id])} गाने हैं।")
    else:
        await send_and_auto_delete_music_reply(message, f"🎶 गाना **'{song_info['title']}'** कतार में जोड़ दिया गया है! अब बजा रही हूँ! ✨")
        current_playing_tasks[chat_id] = asyncio.create_task(play_next_song(client, message))

@Client.on_message(filters.command("queue") & (filters.group | filters.private))
async def queue_command(client: Client, message: Message):
    chat_id = message.chat.id
    if chat_id not in music_queues or not music_queues[chat_id]:
        await send_and_auto_delete_music_reply(message, "म्यूजिक कतार खाली है! कुछ गाने `/play` करो!")
        return

    queue_list = "\n".join([f"{i+1}. {s['title']}" for i, s in enumerate(music_queues[chat_id])])
    await send_and_auto_delete_music_reply(message, f"🎵 **म्यूजिक कतार:**\n{queue_list}\n\n_कुल {len(music_queues[chat_id])} गाने कतार में हैं।_", parse_mode=ParseMode.MARKDOWN)

@Client.on_message(filters.command("skip") & (filters.group | filters.private))
async def skip_command(client: Client, message: Message):
    chat_id = message.chat.id
    if current_playing_tasks.get(chat_id) and not current_playing_tasks[chat_id].done():
        current_playing_tasks[chat_id].cancel()
        music_logger.info(f"Skipped current song in chat {chat_id}.")
        await send_and_auto_delete_music_reply(message, "अगला गाना बजा रही हूँ! ⏭️")
        current_playing_tasks[chat_id] = asyncio.create_task(play_next_song(client, message)) # Play next immediately
    else:
        await send_and_auto_delete_music_reply(message, "कोई गाना नहीं चल रहा है जिसे स्किप किया जा सके! 🤷‍♀️")

@Client.on_message(filters.command("stopmusic") & (filters.group | filters.private))
async def stop_music_command(client: Client, message: Message):
    chat_id = message.chat.id
    if chat_id in music_queues:
        music_queues[chat_id].clear()
        music_logger.info(f"Cleared music queue for chat {chat_id}.")
    
    if current_playing_tasks.get(chat_id) and not current_playing_tasks[chat_id].done():
        current_playing_tasks[chat_id].cancel()
        music_logger.info(f"Stopped current song in chat {chat_id}.")
        current_playing_tasks[chat_id] = None
        await send_and_auto_delete_music_reply(message, "म्यूजिक बंद कर दिया गया है और कतार खाली कर दी गई है! 🔇")
    else:
        await send_and_auto_delete_music_reply(message, "कोई म्यूजिक नहीं चल रहा है जिसे बंद किया जा सके! 😴")

@Client.on_message(filters.command("musichelp") & (filters.group | filters.private))
async def music_help_command(client: Client, message: Message):
    help_text = (
        "🎶 **म्यूजिक बॉट सहायता!** 🎶\n\n"
        "आप इन कमांड्स का उपयोग करके म्यूजिक चला सकते हैं:\n\n"
        "• `/play <गाना का नाम या YouTube लिंक>`: गाना चलाने के लिए या कतार में जोड़ने के लिए।\n"
        "• `/queue`: मौजूदा म्यूजिक कतार देखने के लिए।\n"
        "• `/skip`: मौजूदा गाना स्किप करके अगले गाने पर जाने के लिए।\n"
        "• `/stopmusic`: म्यूजिक बजाना बंद करने और कतार को खाली करने के लिए।\n\n"
        "बस इतना ही! अब म्यूजिक का आनंद लो! 🥳\n\n"
        "**Powered By:** @asbhaibsr Music"
    )
    await send_and_auto_delete_music_reply(message, text=help_text, parse_mode=ParseMode.MARKDOWN)

