# config.py
# ─────────────────────────────────────────────
# Central configuration for the Maghrib Agent
# ─────────────────────────────────────────────

# ── Location (Karachi) ───────────────────────
CITY            = "Karachi"
COUNTRY         = "Pakistan"
LATITUDE        = 24.8607
LONGITUDE       = 67.0011

# Aladhan calculation method
# 1 = University of Islamic Sciences, Karachi (most common in Pakistan)
CALC_METHOD     = 1

# ── Aladhan API ───────────────────────────────
ALADHAN_URL     = "http://api.aladhan.com/v1/timingsByCity"

# ── Google Calendar ───────────────────────────
# Path to your OAuth2 credentials file (downloaded from Google Cloud Console)
CREDENTIALS_FILE = "credentials.json"

# Path where the token will be saved after first login
TOKEN_FILE       = "token.json"

# The calendar to create events in ('primary' = your main calendar)
CALENDAR_ID      = "primary"

# OAuth2 scopes needed
SCOPES           = ["https://www.googleapis.com/auth/calendar"]

# ── Event Details ─────────────────────────────
EVENT_TITLE      = "🤲 Wazifa Reminder — After Maghrib Prayer"
EVENT_DESCRIPTION = (
    "Assalamu Alaikum! 🌙\n\n"
    "Don't forget your Wazifa after Maghrib prayer today (Friday).\n"
    "May Allah accept it from you. Ameen. 🤲"
)
EVENT_DURATION_MINUTES = 30   # How long the calendar event block is

# Reminder pop-up: how many minutes BEFORE Maghrib to notify you
REMINDER_MINUTES_BEFORE = 10

# ── Duplicate Check ───────────────────────────
# The agent searches for events with this keyword to detect duplicates
DUPLICATE_KEYWORD = "Wazifa Reminder"