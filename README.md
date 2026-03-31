# 🎌 Anime News Bot

A production-ready Telegram bot that automatically fetches anime news from RSS feeds and publishes them to your channels.

Built with **PyroFork** + **Motor (MongoDB)** + **aiohttp**.

---

## ✦ Features

- 📡 Multi-RSS feed support with auto-dedup (never reposts)
- 📢 Multi-channel publishing
- ⚙️ Full admin settings panel — configure everything live via commands
- 👑 Owner/Admin permission tiers
- 💾 All settings persist in MongoDB — survive restarts
- 🌐 Webhook/health-check mode for Render, Koyeb, Railway
- 🐳 Docker-ready, Heroku/Render/VPS compatible

---

## 🚀 Quick Start

### 1. Clone & configure

```bash
git clone <your-repo>
cd anime_news_bot
cp .env.example .env
# Fill in your values in .env
```

### 2. Install & run

```bash
pip install -r requirements.txt
python bot.py
```

### 3. Or use Docker

```bash
docker build -t anime-news-bot .
docker run --env-file .env anime-news-bot
```

---

## ⚙️ Environment Variables

| Variable       | Required | Default          | Description                          |
|----------------|----------|------------------|--------------------------------------|
| `BOT_TOKEN`    | ✅        | —                | From @BotFather                      |
| `API_ID`       | ✅        | —                | From my.telegram.org                 |
| `API_HASH`     | ✅        | —                | From my.telegram.org                 |
| `MONGO_URI`    | ✅        | —                | MongoDB connection string            |
| `OWNER_ID`     | ✅        | —                | Your Telegram user ID (becomes Admin[0]) |
| `DB_NAME`      | ❌        | `anime_news_bot` | MongoDB database name                |
| `POLL_INTERVAL`| ❌        | `300`            | Seconds between RSS polls (min 30)   |
| `MAX_RSS`      | ❌        | `25`             | Max RSS feeds                        |
| `MAX_CHANNELS` | ❌        | `10`             | Max publish channels                 |
| `EXTRA_ADMINS` | ❌        | —                | Comma-separated extra admin IDs      |
| `WEBHOOK`      | ❌        | `false`          | Enable health-check HTTP server      |
| `PORT`         | ❌        | `8080`           | Port for health-check server         |

---

## 📋 Command Reference

### RSS Management _(admin)_
| Command | Description |
|---------|-------------|
| `/add_rss <url> [name]` | Add an RSS feed |
| `/rem_rss <url>` | Remove a feed |
| `/view_rss` | List all feeds |

### Channel Management _(admin)_
| Command | Description |
|---------|-------------|
| `/add_chnl <@username or id>` | Add a publish channel |
| `/rem_chnl <@username or id>` | Remove a channel |
| `/view_chnl` | List all channels |

### Tools _(admin)_
| Command | Description |
|---------|-------------|
| `/force_poll` | Manually trigger a news fetch |
| `/status` | Bot health & live stats |
| `/help` | Command reference |

### Settings Panel _(owner only)_
| Command | Description |
|---------|-------------|
| `/settings` | View all current settings |
| `/set_interval <s>` | Set poll interval in seconds |
| `/set_max_rss <n>` | Set RSS feed limit |
| `/set_max_channels <n>` | Set channel limit |
| `/toggle_preview` | Toggle web link preview on/off |
| `/set_footer <text>` | Set a footer on all posts |
| `/clear_footer` | Remove footer |
| `/add_admin <user_id>` | Add an admin (persisted) |
| `/rem_admin <user_id>` | Remove an admin |
| `/list_admins` | List all admins |
| `/clear_seen` | Clear dedup cache |
| `/reset_stats` | Reset publish counter |

---

## 🏗 Project Structure

```
anime_news_bot/
├── bot.py                    # Entry point — startup, settings sync, poller launch
├── config.py                 # Config dataclass — env vars + ADMINS list
├── database.py               # MongoDB layer — all DB operations
├── requirements.txt
├── Dockerfile
├── Procfile
├── render.yaml
├── .env.example
├── .gitignore
├── handlers/
│   ├── __init__.py
│   ├── start.py              # /start  /help
│   ├── rss.py                # /add_rss  /rem_rss  /view_rss
│   ├── channels.py           # /add_chnl  /rem_chnl  /view_chnl
│   ├── admin.py              # /force_poll
│   ├── settings.py           # Full settings panel (owner-only)
│   └── status.py             # /status
├── services/
│   ├── __init__.py
│   └── rss_poller.py         # Background RSS polling task
├── utils/
│   ├── __init__.py
│   ├── auth.py               # @admin_only  @owner_only decorators
│   └── formatting.py         # Shared text helpers
└── middlewares/
    └── __init__.py           # Reserved for future middleware
```

---

## 🔒 Permission Tiers

| Tier | Who | Can do |
|------|-----|--------|
| **Owner** | `ADMINS[0]` (set via `OWNER_ID`) | Everything — settings, admin management, destructive ops |
| **Admin** | Owner + `EXTRA_ADMINS` | RSS management, channel management, force poll, status |
| **User** | Everyone else | `/start` and `/help` only |

---

## 🌐 Deploying to Render

1. Push code to GitHub
2. Create a new **Worker** service on Render
3. Set environment variables in the Render dashboard
4. Set `WEBHOOK=false` (worker services don't need an HTTP port)
5. Deploy — done!

Or use the included `render.yaml` for one-click deploy.

---

## 🌐 Deploying to Koyeb / Railway / Heroku

All platforms work the same way:
- Set the env vars from `.env.example`
- Use `python bot.py` as the start command
- For platforms that require an open port: set `WEBHOOK=true`
