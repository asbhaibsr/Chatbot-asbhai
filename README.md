# 🤖 Chatbot-asbhai — Self-Learning Telegram Bot

A smart, auto-learning Telegram bot built using **Pyrogram**, **MongoDB**, and **Flask**.  
It behaves like a human-style AI girl — remembers conversations, responds with fun or romantic chat, and supports private + group chats with complete control features.

---

## 📌 Features

- 🧠 Self-Learning Chat: Stores and reuses replies (text/sticker) from group & private chats.
- 🎯 Auto-replies based on message context or keyword.
- 💬 Sticker support, smart message memory, and fallback system.
- 📊 Group/User/message tracking system.
- 🧹 Auto message prune + manual clean commands.
- 👑 Owner-only control for broadcasts, stats, restart, leave group, etc.
- ⚙️ Flask Health Check for Koyeb/Render hosting.
- 🔘 Button Click Tracker (MongoDB-based)
- 🕒 Cooldown system to prevent spam.

---

## 🚀 Deploy Now to Koyeb

[![Deploy to Koyeb](https://www.koyeb.com/static/images/deploy/button.svg)](https://app.koyeb.com/deploy?name=chatbot-asbhai&repository=asbhaibsr%2FChatbot-asbhai&branch=main&run_command=python3+main.py&instance_type=free&regions=was&instances_min=0&autoscaling_sleep_idle_delay=300&env%5BAPI_HASH%5D=918e2aa94075a7d04717b371a21fb689&env%5BAPI_ID%5D=28762030&env%5BBOT_TOKEN%5D=8098449556%3AAAED8oT7U3lsPFwJxdxS-k0m27H3v9XC7EY&env%5BMONGO_URI_BUTTONS%5D=mongodb%2Bsrv%3A%2F%2Fed69yyr92n%3AkaY09k4z8zCjDSR3%40cluster0.6uhfmud.mongodb.net%2F%3FretryWrites%3Dtrue%26w%3Dmajority%26appName%3DCluster0&env%5BMONGO_URI_MESSAGES%5D=mongodb%2Bsrv%3A%2F%2Fjeriwo3420%3AsDz0ZevArtOnjpR0%40cluster0.yrfv26n.mongodb.net%2F%3FretryWrites%3Dtrue%26w%3Dmajority%26appName%3DCluster0&env%5BMONGO_URI_TRACKING%5D=mongodb%2Bsrv%3A%2F%2Fmockingbird07317%3ArTgIMbRuwlW7qMLq%40cluster0.4vlhect.mongodb.net%2F%3FretryWrites%3Dtrue%26w%3Dmajority%26appName%3DCluster0&env%5BOWNER_ID%5D=8019381468&ports=8080%3Bhttp%3B%2F&hc_protocol%5B8080%5D=tcp&hc_grace_period%5B8080%5D=5&hc_interval%5B8080%5D=30&hc_restart_limit%5B8080%5D=3&hc_timeout%5B8080%5D=5&hc_path%5B8080%5D=%2F&hc_method%5B8080%5D=get)

---

## 🔧 Environment Variables

Make sure to set the following variables:

| Variable              | Required | Description                          |
|----------------------|----------|--------------------------------------|
| `API_ID`             | ✅        | From https://my.telegram.org         |
| `API_HASH`           | ✅        | From https://my.telegram.org         |
| `BOT_TOKEN`          | ✅        | Get from BotFather                   |
| `OWNER_ID`           | ✅        | Your Telegram numeric ID             |
| `MONGO_URI_MESSAGES` | ✅        | MongoDB URI for storing messages     |
| `MONGO_URI_BUTTONS`  | ✅        | MongoDB URI for storing button logs  |
| `MONGO_URI_TRACKING` | ✅        | MongoDB URI for tracking groups/users|

---

## 💬 Available Commands

| Command         | Access       | Description                                      |
|-----------------|--------------|--------------------------------------------------|
| `/start`        | All Users    | Start the bot and get a welcome message.         |
| `/broadcast`    | Owner Only   | Send message to all users/groups.                |
| `/stats check`  | All Users    | View total users, groups, messages.              |
| `/groups`       | Owner Only   | List all groups the bot is in.                   |
| `/leavegroup`   | Owner Only   | Make the bot leave a specific group.             |
| `/cleardata`    | Owner Only   | Clear a percentage of stored messages.           |
| `/deletemessage`| Owner Only   | Delete message from DB by content match.         |
| `/restart`      | Owner Only   | Restart the bot.                                 |

---

## 📲 Start Now

Join our official update channel for support, help, and updates!

[🌸 Join Channel @asbhai_bsr](https://t.me/asbhai_bsr)

---

## 🧠 How It Works

- Learns from replied messages in chats (text/sticker).
- Detects message content or keyword match to auto-respond.
- Stores each chat globally (multi-group support).
- Deletes old messages automatically when limit is reached.

---

## 🛠 Developer Info

**Repo:** [Chatbot-asbhai GitHub](https://github.com/asbhaibsr/Chatbot-asbhai)  
**Author:** [@asbhaibsr on Telegram](https://t.me/asbhaibsr)

---

## 📜 License

This project is licensed for personal use. Do not sell or reupload without permission.

