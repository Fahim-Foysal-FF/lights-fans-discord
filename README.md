# 🏢 Lights, Fans, Discord: The Boss's Big Idea

> A smart office monitoring system that tracks devices in real-time, visualizes them on a live floor plan, sends proactive AI-powered alerts to Discord, and helps reduce energy waste.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)
![Discord.py](https://img.shields.io/badge/Discord.py-2.3+-7289DA.svg)
![Gemini AI](https://img.shields.io/badge/Gemini-2.5%20Flash-orange.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [System Architecture](#-system-architecture)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Setup Instructions](#-setup-instructions)
- [Running the Project](#-running-the-project)
- [API Documentation](#-api-documentation)
- [Discord Bot Commands](#-discord-bot-commands)
- [Screenshots](#-screenshots)
- [Troubleshooting](#-troubleshooting)
- [License](#-license)

---

## 🎯 Overview

The boss has an office with **3 rooms** (1 Drawing Room + 2 Work Rooms), each containing **2 fans and 3 lights** — a total of **15 devices**. Employees often forget to turn devices off, wasting electricity and money.

This project solves that with:

- 🖥️ **Live Web Dashboard** — Top-down floor plan showing real-time device status
- 🤖 **Discord AI Bot** — Answers natural questions and sends proactive alerts
- ⚡ **FastAPI Backend** — Simulates devices, calculates power, detects anomalies
- 🧠 **Gemini AI Integration** — Turns raw data into friendly human-readable messages

---

## ✨ Features

### 🖥️ Web Dashboard
- 📊 Real-time power consumption meter (updates every 2 seconds)
- 🏢 Interactive top-view office floor plan
- 💡 Lights that glow yellow when ON with realistic ambient light spread
- 🌀 Ceiling fans that spin visually when ON
- 🚨 Live alerts panel with color-coded severity
- 📈 Per-room power breakdown with bar visualizations
- 🔌 Backend connection status indicator

### 🤖 Discord Bot
- `!status` — Overall device status across all rooms
- `!room <name>` — Detailed status of a specific room
- `!usage` — Current wattage + estimated daily kWh + cost in ₹
- `!alerts` — Manual check for anomalies
- `!ping` — System health check
- 🔔 **Proactive alerts** every minute for anomalies

### 🚨 Smart Alerts
- 🌙 **After-Hours Alert** — Detects devices left on outside 9 AM – 5 PM
- 🔴 **Continuous Usage Alert** — Warns when all devices in a room run for 2+ hours

---

## 🏗️ System Architecture
┌─────────────────┐ ┌──────────────────┐ ┌─────────────────┐
│ Web Dashboard │◄────────┤ FastAPI ├────────►│ Discord Bot │
│ (index.html) │ HTTP │ Backend │ HTTP │ (bot.py) │
│ │ JSON │ (main.py) │ JSON │ │
│ - Live Map │ │ │ │ - Commands │
│ - Power Stats │ │ - Device DB │ │ - Alerts │
│ - Alerts UI │ │ - Simulator │ │ - Gemini AI │
└─────────────────┘ │ - Alert Logic │ └────────┬────────┘
└──────────────────┘ │
▼
┌─────────────────┐
│ Gemini API │
│ (Google AI) │
└─────────────────┘

text


📐 See [`diagrams/architecture.png`](./diagrams/architecture.png) for the full system diagram.  
📐 See [`diagrams/office-layout.png`](./diagrams/office-layout.png) for the office floor plan reference.

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| **Backend** | FastAPI, Uvicorn, Python 3.10+ |
| **Frontend** | HTML5, CSS3, Vanilla JavaScript |
| **Bot** | discord.py 2.3+ |
| **AI/LLM** | Google Gemini 2.5 Flash (`google-genai` SDK) |
| **Data Store** | In-memory Python dict (no database required) |

---

## 📁 Project Structure
lights-fans-discord/
│
├── main.py # FastAPI backend + device simulator
├── bot.py # Discord bot with Gemini AI
├── index.html # Live web dashboard
├── requirements.txt # Python dependencies
├── .env.example # Template for environment variables
├── .gitignore # Prevents secrets/venv from being pushed
├── README.md # This file
│
├── diagrams/
│ ├── architecture.png # System architecture diagram
│ ├── office-layout.png # Office floor plan reference
│ └── data-flow.png # Data flow diagram
│
└── screenshots/
├── dashboard.png # Web dashboard view
├── discord-alerts.png # Bot in action
└── discord-commands.png # Bot command examples

text


---

## 🚀 Setup Instructions

### Prerequisites

- **Python 3.10+** installed ([Download here](https://www.python.org/downloads/))
- **Discord account** with a server where you can add bots
- **Google account** (for free Gemini API access)
- **Modern web browser** (Chrome, Firefox, Edge)

---

### Step 1: Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/lights-fans-discord.git
cd lights-fans-discord
Step 2: Create a Virtual Environment
Windows (PowerShell):

PowerShell

python -m venv .venv
.venv\Scripts\Activate.ps1
macOS / Linux:

Bash

python3 -m venv .venv
source .venv/bin/activate
Step 3: Install Dependencies
Bash

pip install -r requirements.txt
Step 4: Get Your API Keys
🔑 Discord Bot Token
Go to Discord Developer Portal
Click "New Application" → give it a name
Go to "Bot" in left sidebar → click "Add Bot"
Under "Token" section, click "Reset Token" → copy the token
Enable these intents: Message Content Intent, Server Members Intent
Go to "OAuth2 > URL Generator":
Scopes: bot
Bot Permissions: Send Messages, Read Message History
Copy the generated URL and paste in browser to invite the bot to your server
🔑 Gemini API Key
Go to Google AI Studio
Click "+ Create API Key" → choose "Create in new project"
Copy the key (starts with AIzaSy...)
🔑 Discord Channel ID
In Discord, enable Developer Mode (Settings → Advanced → Developer Mode)
Right-click on the channel where you want alerts → "Copy Channel ID"
Step 5: Configure Environment Variables
Create a .env file in the project root (copy from .env.example):

env

DISCORD_TOKEN=your_discord_bot_token_here
GEMINI_API_KEY=AIzaSy_your_gemini_key_here
ALERT_CHANNEL_ID=1234567890123456789
⚠️ Never commit your .env file to Git! It's already in .gitignore.

▶️ Running the Project
You'll need 3 terminal windows — one for each component.

Terminal 1 — Start the Backend API
Bash

python main.py
You should see:

text

✅ Backend API started successfully!
📡 API available at: http://127.0.0.1:8000
📖 API docs available at: http://127.0.0.1:8000/docs
Terminal 2 — Start the Discord Bot
Bash

python bot.py
You should see:

text

✅ Bot logged in as: Energy bot
✅ Backend API connection: SUCCESSFUL
🔔 Starting proactive alert monitor...
Terminal 3 — Open the Dashboard
Simply open index.html in your web browser:

Windows:

PowerShell

start index.html
macOS:

Bash

open index.html
Linux:

Bash

xdg-open index.html
Or just double-click the file in your file explorer.

📡 API Documentation
Once the backend is running, interactive API docs are available at:
http://127.0.0.1:8000/docs (Swagger UI, auto-generated by FastAPI)

Endpoints
Method	Endpoint	Description
GET	/	Health check
GET	/api/devices	Get all 15 devices with status
GET	/api/power	Get current power consumption per room
GET	/api/alerts	Get active alerts
POST	/api/devices/{id}/toggle	Manually toggle a device
Example Response — GET /api/devices
JSON

{
  "devices": [
    {
      "id": 1,
      "name": "Fan 1",
      "type": "fan",
      "room": "Drawing Room",
      "status": "on",
      "power_draw_watts": 60,
      "last_changed": "2025-01-15T14:30:22.123456"
    }
  ]
}
🤖 Discord Bot Commands
Command	Description	Example
!ping	Check bot & API health	!ping
!status	Overview of all devices	!status
!room <name>	Details of a specific room	!room Drawing Room
!usage	Power & cost report	!usage
!alerts	Manual alert check	!alerts
!help_office	Show all commands	!help_office
🔔 Automatic Alerts
The bot posts alerts to the configured channel every minute when:

Devices are ON outside 9 AM – 5 PM (after-hours)
All devices in a room have been ON for 2+ hours (continuous usage)
📸 Screenshots
Web Dashboard
Dashboard

Discord Bot in Action
Bot Commands

Proactive Alerts
Alerts

🔧 Troubleshooting
❌ "Backend offline" on dashboard
Make sure python main.py is running in a separate terminal
Check that port 8000 is not being used by another app
Verify no firewall is blocking localhost:8000
❌ Discord bot: "Improper token has been passed"
Your token was revoked (probably exposed publicly)
Reset it at Discord Developer Portal → Bot → Reset Token
Never commit tokens to Git!
❌ Gemini: "PERMISSION_DENIED"
You're using a Cloud Console key (starts with AQ.) — wrong format
Get an AI Studio key (starts with AIzaSy) from aistudio.google.com/app/apikey
❌ Bot connects but sends no alerts
Verify ALERT_CHANNEL_ID matches your Discord channel
Bot needs Send Messages permission in that channel
Alerts only trigger outside 9 AM – 5 PM, or after 2+ hours of continuous use
❌ Dashboard shows devices, but no map updates
Open browser DevTools (F12) → Check Console tab for errors
CORS errors mean backend isn't running or allow_origins is misconfigured
🎬 Demo Video
📺 Watch the demo video here

🤝 Contributing
Pull requests welcome! For major changes, please open an issue first.

📜 License
This project is licensed under the MIT License — see the LICENSE file for details.

👤 Author
Your Name

GitHub: @your-username
Discord: your-discord-tag
🙏 Acknowledgments
Built for the "Lights, Fans, Discord: The Boss's Big Idea" hackathon challenge
Powered by FastAPI, discord.py, and Google Gemini
Inspired by real-world office energy waste problems

