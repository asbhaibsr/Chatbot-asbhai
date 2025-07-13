# --- IMPORTANT: THIS CODE IS PROPERTY OF @asbhaibsr ---
# --- Unauthorized copying or distribution is prohibited ---
# Owner Telegram ID: @asbhaibsr
# Update Channel: @asbhai_bsr
# Support Group: @aschat_group

import asyncio
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from pyrogram.client import Client

# गेम्स डेटाबेस
games_db = {
    "yesno_game": {
        "name": "🤔 हाँ या नहीं?",
        "rules": "1. पहला यूजर सवाल पूछेगा\n2. दूसरा जवाब देगा\n3. तीसरा अनुमान लगाएगा",
        "min_players": 3,
        "players": [],
        "countdown": None,
        "active": False,
        "current_question": None,
        "current_answer": None,
        "current_guesser": None
    },
    "future_game2": {
        "name": "🎭 ड्रामा क्वीन (जल्द आ रहा)",
        "rules": "COMING SOON",
        "min_players": 3,
        "players": [],
        "countdown": None
    }
}

async def start_countdown(game_id, chat_id, client):
    game = games_db[game_id]
    
    for time_left in [60, 30, 10]:
        if time_left == 60:
            text = f"⏳ गेम शुरू होने में 1 मिनट...\nजुड़ने के लिए:\n/startgame"
        elif time_left == 30:
            text = f"⏳ केवल 30 सेकंड शेष!\nजल्दी जॉइन करो!"
        else:
            text = "⏳ आखिरी 10 सेकंड! जल्दी करो!"
        
        await client.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎮 अभी जॉइन करो", callback_data=f"join_{game_id}")]
            ])
        )
        await asyncio.sleep(30 if time_left != 10 else 10)
    
    await start_yesno_game(game_id, chat_id, client)

async def start_yesno_game(game_id, chat_id, client):
    game = games_db[game_id]
    players = game["players"]
    
    if len(players) < game["min_players"]:
        await client.send_message(
            chat_id=chat_id,
            text="😢 पर्याप्त खिलाड़ी नहीं हैं। गेम रद्द किया जा रहा है।"
        )
        game["players"] = []
        game["countdown"] = None
        return
    
    game["active"] = True
    
    # पहला यूजर सवाल पूछे
    questioner = players[0]
    await client.send_message(
        chat_id=questioner["id"],
        text=f"🎤 {questioner['name']}, कृपया एक 'हाँ/नहीं' वाला सवाल पूछो:"
    )
    game["current_question"] = None
    game["current_answer"] = None
    game["current_guesser"] = players[2]["id"] if len(players) > 2 else None
    
    # ग्रुप को सूचना
    await client.send_message(
        chat_id=chat_id,
        text=f"🎮 गेम शुरू! {questioner['name']} से एक सवाल का इंतज़ार है..."
    )

async def handle_yesno_answer(client, user_id, answer):
    for game_id, game in games_db.items():
        if game.get("active") and game.get("current_answer") is None:
            # Check if this user is the answerer
            if len(game["players"]) > 1 and game["players"][1]["id"] == user_id:
                game["current_answer"] = answer
                await client.send_message(
                    chat_id=user_id,
                    text=f"आपने {answer} चुना! अब अनुमानकर्ता का इंतज़ार है..."
                )
                
                # Notify group
                guesser_name = next((p["name"] for p in game["players"] if p["id"] == game["current_guesser"]), "कोई")
                await client.send_message(
                    chat_id=game["players"][0]["id"],  # Questioner's chat
                    text=f"{guesser_name} अब अनुमान लगाएगा कि जवाब क्या था!"
                )
                return True
    return False

async def handle_yesno_guess(client, user_id, guess):
    for game_id, game in games_db.items():
        if game.get("active") and game.get("current_guesser") == user_id:
            correct = (guess.lower() == game["current_answer"].lower())
            
            # ग्रुप को रिजल्ट बताएं
            result_text = (
                f"🎉 नतीजा!\n\n"
                f"सवाल: {game['current_question']}\n"
                f"जवाब: {game['current_answer']}\n"
                f"अनुमान: {guess}\n\n"
                f"{'✅ सही अनुमान!' if correct else '❌ गलत अनुमान!'}"
            )
            
            await client.send_message(
                chat_id=game["players"][0]["id"],  # Questioner's chat
                text=result_text
            )
            
            # रीसेट गेम
            game["players"] = []
            game["countdown"] = None
            game["active"] = False
            game["current_question"] = None
            game["current_answer"] = None
            game["current_guesser"] = None
            return True
    return False

# /startgame कमांड हैंडलर
@Client.on_message(filters.command("startgame") & (filters.group | filters.private))
async def start_game_command(client: Client, message: Message):
    if message.chat.type == "private":
        await message.reply_text("🚫 यह कमांड सिर्फ ग्रुप्स में काम करता है!")
        return

    buttons = []
    for game_id, game in games_db.items():
        btn_text = f"{game['name']}"
        buttons.append([InlineKeyboardButton(btn_text, callback_data=f"join_{game_id}")])
    
    await message.reply_text(
        "🎮 चुनें गेम:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# जॉइन गेम कॉलबैक हैंडलर
@Client.on_callback_query(filters.regex("^join_"))
async def join_game_callback(client: Client, callback_query):
    query = callback_query
    game_id = query.data.replace("join_", "")
    game = games_db[game_id]
    
    if query.from_user.id in [p["id"] for p in game["players"]]:
        await query.answer("आप पहले से जुड़े हैं!")
        return
    
    game["players"].append({
        "id": query.from_user.id,
        "name": query.from_user.first_name
    })
    
    players_list = "\n".join([p["name"] for p in game["players"]])
    await query.message.reply_text(
        f"🎉 {query.from_user.first_name} गेम में शामिल हो गए!\n\nजुड़े खिलाड़ी:\n{players_list}"
    )
    
    if len(game["players"]) >= game["min_players"] and not game["countdown"]:
        game["countdown"] = asyncio.create_task(start_countdown(game_id, query.message.chat.id, client))

# उत्तर हैंडलर
@Client.on_callback_query(filters.regex("^answer_"))
async def handle_answer(client: Client, callback_query):
    answer = callback_query.data.replace("answer_", "")
    await callback_query.answer(f"आपने {answer} चुना!")
    await handle_yesno_answer(client, callback_query.from_user.id, answer)
    await callback_query.message.edit_text(f"🧠 आपका जवाब: {answer}")

# मैसेज हैंडलर (सवाल और अनुमान के लिए)
@Client.on_message(filters.group & filters.text & ~filters.command)
async def game_message_handler(client: Client, message: Message):
    for game_id, game in games_db.items():
        if game.get("active"):
            # सवाल पूछने वाला
            if len(game["players"]) > 0 and game["players"][0]["id"] == message.from_user.id and game["current_question"] is None:
                game["current_question"] = message.text
                await message.reply_text("सवाल सेव हो गया! अब जवाबदाता का इंतज़ार...")
                
                # जवाबदाता को बटन भेजें
                if len(game["players"]) > 1:
                    answerer = game["players"][1]
                    await client.send_message(
                        chat_id=answerer["id"],
                        text=f"🧠 {answerer['name']}, कृपया जवाब दें:",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("👍 हाँ", callback_data="answer_yes")],
                            [InlineKeyboardButton("👎 नहीं", callback_data="answer_no")]
                        ])
                    )
                return
            
            # अनुमान लगाने वाला
            elif game["current_guesser"] == message.from_user.id and game["current_answer"] is not None:
                await handle_yesno_guess(client, message.from_user.id, message.text)
                return

# Add this to your existing callback handler if you have one
@app.on_callback_query()
async def callback_handler(client, callback_query):
    if callback_query.data.startswith("join_"):
        await join_game_callback(client, callback_query)
    elif callback_query.data.startswith("answer_"):
        await handle_answer(client, callback_query)
    # Add your other callback handlers here
