# 🧠 AI Picks Bot for Discord

An advanced moderation and automation bot designed for a high-traffic, gambling-focused Discord server. Built with **Python** and **discord.py**, this bot streamlines moderator tools, enhances user interaction, and handles weekly community events like nominations and giveaways.

---

## 🚀 Why I Built This

This project was commissioned by a server admin looking to simplify moderation, increase engagement, and automate server functions around sports betting culture. Though not responsible for generating the AI picks itself, this bot supports the infrastructure and community that revolves around them.

Along the way, I learned a ton about integrating with the Discord API, writing modular Python code using Cogs, and managing persistent cloud data via MongoDB.

---

## ⚙️ Tech Stack

- **Python 3.11+**
- **discord.py** (Discord bot framework)
- **MongoDB Atlas** (cloud database)
- **pytz** & **datetime** (timezone-aware scheduling)
- **difflib** (name validation)

---

## 📁 Project Structure

```
ai-picks-bot/
├── DiscordBot/
│   ├── bot.py
│   ├── token.env
│   └── cogs/
│       ├── banned_players.py
│       ├── channel_messages.py
│       ├── embeds.py
│       ├── giveaway.py
│       ├── moderation.py
│       ├── reminders.py
│       ├── role_management.py
│       ├── testing.py
│       └── welcome.py
│
│       ├── channels/
│       │   └── channel_ids.py
│       ├── other/
│       │   ├── bad_words.py
│       │   ├── player_names.py
│       │   └── stream_links.py
│       └── roles/
│           ├── bettor_app_roles.py
│           ├── sport_roles.py
│           └── user_roles.py
├── README.md
├── requirements.txt
└── todo.md
```

---

## 🧍️‍⚖️ Features by Cog

### 🟢 Embeds & Channel Messages
- `!thirty`, `!welcome`, `!rules`, `!join_vip`: Custom embed commands for channel introductions and onboarding.
- `!hello`: Basic bot health check.

---

### 🔍 Streaming & Betting Tools
- `/findstream`: Returns a list of updated streaming sites for watching live games.
- `/devig`: Calculates true odds and expected value using devig math and Kelly Criterion based on user input.

---

### 🗳️ Banned Players & Nominations
- `/nominate <player>`: Submit nominations with name correction logic via `difflib.get_close_matches`.
- Automatic spelling/duplicate detection with a 5-nomination weekly cap.
- `!start_voting <days>`: Starts community-wide voting with Discord buttons.
- `!start_voting_override <days>`: Restores a vote session from MongoDB in case of a crash.
- **Update Nominations System**:
  - Sends updated nomination list every 5 minutes.
  - Deletes previous embed to reduce spam.
  - Uses modals + buttons to encourage interaction.

---

### 🛡️ Moderation Tools
- Live message scanning for spam, adult content, and Discord ad keywords.
- Sends detected content to a log channel with 3 mod buttons: **Ban**, **Timeout**, **Clear**.
- Interactive embeds that clean up after action taken.

---

### 🎟️ Giveaway System
- Automatically parses user-submitted media.
- Sends embeds with approve/deny buttons to a private giveaway mod channel.
- Supports multi-image messages.
- `/giveaway_thanks`: Queries approved entries.
- `/export_giveaway`: Outputs approved user counts to `.txt` and resets DB.

---

### 🎭 Role Management
- Real-time role enforcement: Prevents VIP + Free role overlap.
- Logs automatic role updates for transparency.
- `/approles`, `/sportroles`: Button-based reaction roles (emoji mapped).
- `/checkroles`: Scans all server members for role inconsistencies.

---

### 🗓️ Moderator Reminders
- Scheduled daily reminders sent to mod chat to keep content fresh.
- Timezone-aware using `pytz`.

---

### 👋 Welcome System
- On member join, sends a DM embed guiding new users to key channels.
- Essential due to auto-VIP onboarding from 3rd-party app (Winnable).
- Logs success/failure of DM delivery.

---

## 🧠 What I Learned

- Working with persistent cloud databases (MongoDB Atlas)
- Modular bot design with Cogs for maintainability
- UI/UX improvements through buttons, modals, and scheduled embeds
- Failover recovery using stored MongoDB state
- Building tools that boost real community engagement in niche spaces

---

## 👨‍💻 Author

**Liam Keats**  
Python Developer | Automation Enthusiast | Discord Bot Architect  
[GitHub](https://github.com/liamkeats) · [LinkedIn](https://www.linkedin.com/in/liamkeats/)

---

## 🔒 License

This project is **closed-source** and **not licensed for redistribution, modification, or commercial use**.

If you are interested in collaboration, permissions, or viewing more of my work, feel free to reach out.

> This bot doesn't make picks—but it makes managing a betting community a hell of a lot easier.
