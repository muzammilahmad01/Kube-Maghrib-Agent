# tools.py
# ─────────────────────────────────────────────────────────────────
# LangChain Tools used by the Maghrib Agent
# Each tool is a single, focused action the agent can call.
# ─────────────────────────────────────────────────────────────────

import requests
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from langchain.tools import tool
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

import os
import json
import config

# ── Pakistan Standard Time zone ───────────────────────────────────
PKT = ZoneInfo("Asia/Karachi")


# ─────────────────────────────────────────────────────────────────
# TOOL 1 — Fetch Maghrib Prayer Time
# ─────────────────────────────────────────────────────────────────
@tool
def get_maghrib_time(date_str: str) -> str:
    """
    Fetches the Maghrib prayer time for Karachi on a given date.

    Args:
        date_str: Date in DD-MM-YYYY format (e.g. '04-04-2025')

    Returns:
        Maghrib time as a string in HH:MM format (24-hour, PKT)
        OR an error message starting with 'ERROR:'
    """
    try:
        params = {
            "city":    config.CITY,
            "country": config.COUNTRY,
            "method":  config.CALC_METHOD,
            "date":    date_str,
        }
        response = requests.get(config.ALADHAN_URL, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()

        if data.get("code") != 200:
            return f"ERROR: Aladhan API returned code {data.get('code')}"

        maghrib_time = data["data"]["timings"]["Maghrib"]
        # Aladhan returns time like "18:45 (PKT)" — strip timezone suffix
        maghrib_time = maghrib_time.split(" ")[0]

        return maghrib_time

    except requests.exceptions.RequestException as e:
        return f"ERROR: Network error fetching prayer time — {str(e)}"
    except (KeyError, ValueError) as e:
        return f"ERROR: Unexpected API response format — {str(e)}"


# ─────────────────────────────────────────────────────────────────
# Helper — Build authenticated Google Calendar service
# ─────────────────────────────────────────────────────────────────
def _get_calendar_service():
    """
    Handles OAuth2 authentication and returns an authenticated
    Google Calendar API service object.

    - First run: opens browser for login, saves token.json
    - Subsequent runs: loads token.json directly (no browser needed)
    - If token is expired: refreshes it automatically
    """
    creds = None

    # Load existing token if available
    if os.path.exists(config.TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(
            config.TOKEN_FILE, config.SCOPES
        )

    # If no valid credentials, authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Token expired but refresh token exists — silently refresh
            creds.refresh(Request())
        else:
            # First time — open browser for OAuth2 login
            flow = InstalledAppFlow.from_client_secrets_file(
                config.CREDENTIALS_FILE, config.SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Save the token for future runs
        with open(config.TOKEN_FILE, "w") as token_file:
            token_file.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


# ─────────────────────────────────────────────────────────────────
# TOOL 2 — Check if Wazifa reminder already exists today
# ─────────────────────────────────────────────────────────────────
@tool
def check_existing_reminder(date_str: str) -> str:
    """
    Checks Google Calendar to see if a Wazifa reminder already
    exists for the given date. Prevents creating duplicates.

    Args:
        date_str: Date in DD-MM-YYYY format (e.g. '04-04-2025')

    Returns:
        'EXISTS' if a reminder was found for today
        'NOT_FOUND' if no reminder exists
        'ERROR: <message>' if something went wrong
    """
    try:
        service = _get_calendar_service()

        # Parse the date
        date_obj = datetime.strptime(date_str, "%d-%m-%Y").replace(tzinfo=PKT)

        # Define the search window: start of day to end of day (PKT)
        time_min = date_obj.replace(hour=0,  minute=0,  second=0).isoformat()
        time_max = date_obj.replace(hour=23, minute=59, second=59).isoformat()

        # Search calendar for events today containing our keyword
        events_result = service.events().list(
            calendarId=config.CALENDAR_ID,
            timeMin=time_min,
            timeMax=time_max,
            q=config.DUPLICATE_KEYWORD,       # keyword search
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        events = events_result.get("items", [])

        if events:
            return "EXISTS"
        else:
            return "NOT_FOUND"

    except Exception as e:
        return f"ERROR: Could not check calendar — {str(e)}"


# ─────────────────────────────────────────────────────────────────
# TOOL 3 — Create the Wazifa Reminder on Google Calendar
# ─────────────────────────────────────────────────────────────────
@tool
def create_wazifa_reminder(maghrib_time_str: str) -> str:
    """
    Creates a Google Calendar event for the Wazifa reminder
    at Maghrib time on today's date.

    Args:
        maghrib_time_str: Maghrib time in HH:MM format (e.g. '18:45')

    Returns:
        'SUCCESS: <event_link>' if the event was created
        'ERROR: <message>' if something went wrong
    """
    try:
        service = _get_calendar_service()

        # Get today's date in PKT
        today = datetime.now(PKT)

        # Parse maghrib time and combine with today's date
        maghrib_hour, maghrib_minute = map(int, maghrib_time_str.split(":"))
        maghrib_dt = today.replace(
            hour=maghrib_hour,
            minute=maghrib_minute,
            second=0,
            microsecond=0
        )

        # Event ends DURATION minutes after Maghrib
        end_dt = maghrib_dt + timedelta(minutes=config.EVENT_DURATION_MINUTES)

        # Build the event payload
        event = {
            "summary": config.EVENT_TITLE,
            "description": config.EVENT_DESCRIPTION,
            "start": {
                "dateTime": maghrib_dt.isoformat(),
                "timeZone": "Asia/Karachi",
            },
            "end": {
                "dateTime": end_dt.isoformat(),
                "timeZone": "Asia/Karachi",
            },
            "reminders": {
                "useDefault": False,
                "overrides": [
                    # Pop-up notification before Maghrib
                    {
                        "method": "popup",
                        "minutes": config.REMINDER_MINUTES_BEFORE
                    },
                    # Also send an email reminder
                    {
                        "method": "email",
                        "minutes": config.REMINDER_MINUTES_BEFORE
                    },
                ],
            },
            "colorId": "9",   # Blueberry color for easy visibility
        }

        created_event = service.events().insert(
            calendarId=config.CALENDAR_ID,
            body=event
        ).execute()

        event_link = created_event.get("htmlLink", "No link available")
        return f"SUCCESS: Event created → {event_link}"

    except Exception as e:
        return f"ERROR: Could not create calendar event — {str(e)}"