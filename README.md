# 🤖 **AS AI AND SELF LEARNING Assistant Bot**

An advanced self-learning AI assistant bot built on Pyrogram and MongoDB. This bot supports group management, auto-reply, conversational AI, and command system.

## 📁 **Project Structure**

```
Chatbot-asbhai/
├── main.py                 # Entry point and bot startup
├── config.py               # Configuration and database setup
├── commands.py             # All command handlers
├── events.py               # Message handling and events
├── utils.py                # Utility functions and AI logic
├── callbacks.py            # Inline button callbacks
├── broadcast_handler.py    # Broadcast system
├── web.py                  # Web server (formerly bot_commands.py)
└── requirements.txt        # Python dependencies
```

## 🚀 **Quick Start**

### 1. **Prerequisites**
- Python 3.8+
- MongoDB Atlas (3 databases)
- Telegram Bot Token
- Pyrogram API ID and Hash

### 2. **Installation**
```bash
# Clone repository
git clone https://github.com/yourusername/Chatbot-asbhai.git
cd Chatbot-asbhai

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export BOT_TOKEN="your_bot_token"
export API_ID="your_api_id" 
export API_HASH="your_api_hash"
export MONGO_URI_MESSAGES="mongodb_uri_messages"
export MONGO_URI_BUTTONS="mongodb_uri_buttons"
export MONGO_URI_TRACKING="mongodb_uri_tracking"
export OWNER_ID="your_user_id"

# Run the bot
python main.py
```

## 📋 **Features Overview**

### 🤖 **AI System**
- **5-tier AI Response** - From g4f LLM to Markov Chain
- **Self-Learning** - Auto learns from user conversations
- **Multi-Personality** - Real Girl, Romantic, Motivation, Study Girl, Gemini
- **Contextual Understanding** - Chat history based replies

### 🛡️ **Group Management**
- **Auto Moderation** - Deletes links, bio links, mentions
- **Custom Punishment** - Delete, Mute, Warn, Ban system
- **Admin Exception** - Rules not applied on admins
- **Bio Link Exception** - Special permission for selected users

### 💰 **Earning & Leaderboard**
- **Monthly Contest** - Top 5 active users
- **Cash Prizes** - ₹50, ₹30, ₹20 rewards
- **Premium Rewards** - Filter Bot premium access
- **Auto Reset** - First date of every month

### 📊 **Data Management**
- **Multiple MongoDB** - Separate databases for separate data
- **Auto Pruning** - Auto cleanup after 100,000+ messages
- **Manual Cleanup** - Percentage-based data deletion

## 🎛️ **Commands Reference**

### **User Commands**
| Command        | Description           | Example         |
|----------------|----------------------|-----------------|
| `/start`       | Start the bot        | `/start`        |
| `/topusers`    | Earning leaderboard  | `/topusers`     |
| `/stats check` | Bot statistics       | `/stats check`  |
| `/clearmydata` | Delete your data     | `/clearmydata`  |

### **Admin Commands (Group)**
| Command        | Description           | Example         |
|----------------|----------------------|-----------------|
| `/settings`    | Group settings menu  | `/settings`     |
| `/setaimode`   | Set AI personality   | `/setaimode`    |

### **Owner Commands (Private)**
| Command          | Description                  | Example                  |
|------------------|-----------------------------|--------------------------|
| `/broadcast`     | Message all users           | `/broadcast` (reply)     |
| `/grp_broadcast` | Message all groups          | `/grp_broadcast` (reply) |
| `/groups`        | List groups                 | `/groups`                |
| `/leavegroup`    | Leave group                 | `/leavegroup -1001234567890` |
| `/cleardata`     | Data cleanup                | `/cleardata 10%`         |
| `/restart`       | Restart bot                 | `/restart`               |

## ⚙️ **Configuration**

### **Environment Variables**
```env
# Required
BOT_TOKEN=your_bot_token_here
API_ID=your_api_id
API_HASH=your_api_hash

# MongoDB URLs (3 separate databases)
MONGO_URI_MESSAGES=mongodb_uri_for_messages
MONGO_URI_BUTTONS=mongodb_uri_for_buttons  
MONGO_URI_TRACKING=mongodb_uri_for_tracking

# Bot Settings
OWNER_ID=your_telegram_user_id
UPDATE_CHANNEL_USERNAME=asbhai_bsr
ASBHAI_USERNAME=asbhaibsr
ASFILTER_BOT_USERNAME=asfilter_bot
BOT_PHOTO_URL=https://jumpshare.com/s/yECHB1KD096ARRSIYT5C
```

### **Dependencies**
```txt
pyrogram>=2.0.0
tgcrypto>=1.2.0
pymongo>=4.0.0
flask>=2.0.0
textblob>=0.17.1
nltk>=3.6.0
fuzzywuzzy>=0.18.0
pytz>=2021.0
g4f>=0.1.0
```

## 🔧 **Development**

### **Local Development Setup**
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Download NLTK data
python -c "import nltk; nltk.download('vader_lexicon')"

# Run the bot
python main.py
```

### **File Description**

| File                   | Description                                      |
|------------------------|--------------------------------------------------|
| `main.py`              | Main entry point, bot initialization             |
| `config.py`            | All configuration variables and database connections |
| `commands.py`          | Handlers for all Telegram commands               |
| `events.py`            | Message events, group join/leave, message handling |
| `utils.py`             | AI logic, utility functions, data processing     |
| `callbacks.py`         | Inline button callback handlers                  |
| `broadcast_handler.py` | Broadcast messaging system                       |
| `web.py`               | Web server (formerly bot_commands.py)            |
| `requirements.txt`     | All Python dependencies                          |

## 🐛 **Troubleshooting**

### **Common Issues**

1. **MongoDB Connection Error**
   ```bash
   # Check database URLs
   # Check IP whitelisting
   # Check network connectivity
   ```

2. **g4f Installation Issue**
   ```bash
   # Install latest version
   pip install --upgrade g4f
   ```

3. **Bot not replying in group**
   - Make the bot admin
   - Check `bot_enabled` setting
   - Check AI mode

4. **Broadcast not sending**
   - Set correct OWNER_ID
   - Check users data in MongoDB

## 📞 **Support**

- **Owner:** [@asbhaibsr](https://t.me/asbhaibsr)
- **Updates Channel:** [@asbhai_bsr](https://t.me/asbhai_bsr)
- **Support Group:** [@aschat_group](https://t.me/aschat_group)

## 📄 **License**

This project is for private use only. For any commercial use, get permission from the owner.

---

**Credits:** Developed with ❤️ by [@asbhaibsr](https://t.me/asbhaibsr)

**Version:** 2.0.0  
**Last Updated:** 10/05/2025
