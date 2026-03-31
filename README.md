# 🌙 Maghrib Wazifa Reminder Agent

A LangChain-powered agent that automatically sets a Google Calendar reminder 
for your weekly Friday Wazifa at the exact Maghrib prayer time in Karachi.

---

## 📁 Project Structure

```
maghrib_agent/
├── agent.py          # Main agent — orchestrates the workflow
├── tools.py          # LangChain tools (Aladhan API + Google Calendar)
├── config.py         # All constants and configuration
├── requirements.txt  # Python dependencies
├── .env.example      # Environment variable template
├── .env              # Your actual secrets (never commit this)
├── .gitignore
└── README.md
```

---

## 🔄 Agent Workflow

```
Agent starts (triggered by K8s CronJob every hour on Fridays)
        ↓
Step 1: Get today's date in PKT
        ↓
Step 2: Fetch Maghrib time from Aladhan API (Karachi)
        ↓
Step 3: Check Google Calendar — does a Wazifa reminder already exist today?
        ↓
    EXISTS → Skip, log "Reminder already set"
    NOT_FOUND → Create event at Maghrib time with 10-min popup alert
        ↓
Step 5: Log final result
```

---

## ⚙️ Setup Instructions

### Step 1 — Clone & Install Dependencies

```bash
git clone <your-repo>
cd maghrib_agent

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
```

### Step 2 — Set Up OpenAI API Key

```bash
cp .env.example .env
# Edit .env and add your OpenAI API key
```

### Step 3 — Set Up Google Calendar API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (e.g., "Maghrib Agent")
3. Enable the **Google Calendar API**
4. Go to **Credentials** → Create **OAuth 2.0 Client ID**
5. Choose **Desktop App** as the application type
6. Download the credentials JSON file
7. Rename it to `credentials.json` and place it in this folder

### Step 4 — First Run (OAuth Login)

```bash
python agent.py
```

On the **first run only**, a browser window will open asking you to log in 
to your Google account. After login, a `token.json` file is saved automatically.
All future runs (including inside Docker/Kubernetes) will use this token silently.

⚠️ **Important:** Do this first run on your local machine BEFORE building the 
Docker image. The `token.json` file needs to be mounted into the K8s Pod as 
a Kubernetes Secret.

---

## 🐳 Docker & Kubernetes (DevOps Part)

See the Dockerfile and K8s manifests in the `/k8s` folder.

Key notes:
- Mount `token.json` as a Kubernetes Secret
- Mount `.env` (or set env vars directly in the K8s manifest)
- CronJob schedule: `0 9-17 * * 5` (every hour 9AM–5PM on Fridays)
- Set `startingDeadlineSeconds: 172800` for reliability

---

## 🔧 Configuration

All settings are in `config.py`:

| Setting | Default | Description |
|---|---|---|
| `CITY` | Karachi | City for prayer time |
| `CALC_METHOD` | 1 | University of Islamic Sciences, Karachi |
| `EVENT_DURATION_MINUTES` | 30 | Length of calendar event block |
| `REMINDER_MINUTES_BEFORE` | 10 | Popup alert before Maghrib |
| `DUPLICATE_KEYWORD` | "Wazifa Reminder" | Used to detect existing events |

---

## 📅 Google Calendar Event

The agent creates an event like this:

```
Title:       🤲 Wazifa Reminder — After Maghrib Prayer
Time:        Maghrib time (changes weekly) → +30 min
Reminders:   10-min popup + 10-min email
Color:       Blueberry (dark blue)
Description: Assalamu Alaikum! Don't forget your Wazifa after Maghrib...
```

---

## 🛡️ Error Handling

| Scenario | Behavior |
|---|---|
| Aladhan API down | Tool returns `ERROR:` message, agent logs and exits |
| Google Auth expired | Token auto-refreshes silently |
| Reminder already exists | Agent skips creation, logs "already set" |
| Not Friday | Agent exits immediately (safety check) |
| Max iterations hit | AgentExecutor stops after 6 steps |

---

## JazakAllah Khair 🤲