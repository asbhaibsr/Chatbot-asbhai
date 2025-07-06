# 🤖 Self-Learning Telegram AI Bot — Powered by @asbhaibsr

Welcome to the **most advanced, self-learning Telegram bot** built for chat groups, fun interactions, earning systems, and full admin control. Perfect for Telegram kings & queens who want their group chat 🔥 always on fire!

> **⚠️ Note:** Yeh bot aapke chats se *khud seekhta hai* aur har message ko smart banata hai. Use karo, sikhao, aur chat ka mazaa uthao!

---

## 👑 Developed & Managed By:

* 👨‍💻 **Owner:** [@asbhaibsr](https://t.me/asbhaibsr)
* 📢 **Update Channel:** [@asbhai\_bsr](https://t.me/asbhai_bsr)
* 💬 **Support / Chat Group:** [@aschat\_group](https://t.me/aschat_group)
* 👼 **Live Demo Bot:** [@askiangelbot](https://t.me/askiangelbot) — *Check how it works in real-time!*

---

## 🚀 Features

* 🤖 **Self-Learning AI Chatting**
* 🧠 **Smart, Contextual Replies**
* 💬 **Stores Every Chat Message (Text + Stickers)**
* 📊 **Group & User Activity Tracking**
* 💸 **Earning System for Active Members**
* 📦 **MongoDB Storage for Scale & Speed**
* 📣 **Broadcast, Stats, Cleanup, Restart & Admin Tools**
* 🩺 **24/7 Health Check via Flask (Koyeb Compatible)**

---

## 🛠 Setup Instructions

### 1. Environment Variables (.env)

```env
API_ID=your_api_id
API_HASH=your_api_hash
BOT_TOKEN=your_bot_token
OWNER_ID=your_telegram_user_id
MONGO_URI_MESSAGES=your_mongo_uri_1
MONGO_URI_BUTTONS=your_mongo_uri_2
MONGO_URI_TRACKING=your_mongo_uri_3
PORT=8000
```

### 2. Deployment (Replit / Koyeb / VPS)

* Upload this bot.
* Set env variables.
* Health check URL for uptime.
* Deploy and enjoy unlimited chat fun!

---

## 💻 Owner-Only Commands

```bash
/broadcast your message        # Send to all groups
/stats check                   # Show total stats
/topusers                      # Show earning leaderboard
/cleardata 10%                 # Delete % of old messages
/deletemessage hello bro       # Delete specific message
/clearearning                  # Reset earning counts
/groups                        # List all joined groups
/leavegroup -100xxxxxxxxx      # Force bot leave
/restart                       # Restart the bot
```

---

## 👥 For All Group Users

* Just chat normally.
* Bot will reply based on past conversations.
* Reply to bot messages to teach it.
* Use `/topusers` to see most active users & earners.

---

## 🧠 MongoDB Collections Used

| Collection              | Purpose                           |
| ----------------------- | --------------------------------- |
| `messages`              | Stores text/stickers of all users |
| `button_interactions`   | Tracks inline button clicks       |
| `groups_data`           | All groups where bot is added     |
| `users_data`            | Tracks each user info             |
| `monthly_earnings_data` | Monthly activity stats            |

---

## ✅ Health Check (Koyeb / UptimeRobot)

Used to keep the bot always awake.

```
GET /health
```

Returns:

```json
{"status": "ok", "message": "Bot is alive and healthy!"}
```

---

## 💎 Start Menu with Inline Buttons

When someone sends /start:

* ➕ **Add Me to Group**
* 📢 **Updates Channel**  → [@asbhai\_bsr](https://t.me/asbhai_bsr)
* ❓ **Support Group**    → [@aschat\_group](https://t.me/aschat_group)
* 🛒 **Buy My Code**      → Contact [@asbhaibsr](https://t.me/asbhaibsr)
* 💰 **Earning Leaderboard** → Shows top chatters

---

## 👑 Credits & Licensing

* 🔥 Bot Developer: [@asbhaibsr](https://t.me/asbhaibsr)
* ❌ Re-uploading or selling this code without permission is **strictly prohibited**.
* 📢 Stay updated: [@asbhai\_bsr](https://t.me/asbhai_bsr)
* 💬 Chat or Help: [@aschat\_group](https://t.me/aschat_group)
* 👼 Demo this bot live: [@askiangelbot](https://t.me/askiangelbot)

---

## 💬 Final Note

Use karo, enjoy karo, aur group mein bakchodi karo 😎
Ye bot aapka group bana dega ek real time entertaining adda! 🔥
