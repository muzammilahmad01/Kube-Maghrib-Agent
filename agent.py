# agent.py
# ─────────────────────────────────────────────────────────────────
# Maghrib Wazifa Reminder Agent
# Built with LangChain — orchestrates a 3-step pipeline:
#   1. Fetch Maghrib prayer time from Aladhan API
#   2. Check if a reminder already exists on Google Calendar
#   3. Create the reminder if it doesn't exist
# ─────────────────────────────────────────────────────────────────

import os
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from langchain import hub

from tools import get_maghrib_time, check_existing_reminder, create_wazifa_reminder

# ── Load environment variables ────────────────────────────────────
load_dotenv()

# ── Logging setup ─────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Timezone ──────────────────────────────────────────────────────
PKT = ZoneInfo("Asia/Karachi")


# ─────────────────────────────────────────────────────────────────
# Agent Prompt
# ─────────────────────────────────────────────────────────────────
# We define a clear, step-by-step system prompt so the agent
# knows exactly what to do and in what order.
# ─────────────────────────────────────────────────────────────────

AGENT_PROMPT = PromptTemplate.from_template("""
You are the Maghrib Wazifa Reminder Agent. Your job is to set a Google Calendar 
reminder for a weekly Wazifa (Islamic devotional practice) that happens every 
Friday after Maghrib prayer in Karachi, Pakistan.

You must follow these steps in EXACT ORDER — do not skip any step:

STEP 1: Get today's date in DD-MM-YYYY format.
        Today's date is: {today_date}

STEP 2: Use the `get_maghrib_time` tool with today's date to fetch the 
        Maghrib prayer time for Karachi.

STEP 3: Use the `check_existing_reminder` tool with today's date to check 
        if a Wazifa reminder already exists on Google Calendar for today.

STEP 4: 
        - If the check returns "EXISTS": Do NOT create a new reminder. 
          Report that the reminder already exists.
        - If the check returns "NOT_FOUND": Use the `create_wazifa_reminder` 
          tool with the Maghrib time from Step 2 to create the reminder.

STEP 5: Report the final result clearly.

You have access to the following tools:
{tools}

Use the following format STRICTLY:

Thought: I need to think about what to do next
Action: the action to take — must be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (repeat Thought/Action/Action Input/Observation as needed)
Thought: I now know the final answer
Final Answer: A clear summary of what happened (what time Maghrib is, 
              whether the reminder was created or already existed)

Begin!

{agent_scratchpad}
""")


# ─────────────────────────────────────────────────────────────────
# Build and Run the Agent
# ─────────────────────────────────────────────────────────────────

def run_agent():
    """
    Initializes and runs the Maghrib Wazifa Reminder Agent.
    This function is the main entry point called by the CronJob.
    """

    log.info("=" * 60)
    log.info("  Maghrib Wazifa Reminder Agent — Starting")
    log.info("=" * 60)

    # ── Get today's date in PKT ───────────────────────────────────
    today = datetime.now(PKT)
    today_date_str = today.strftime("%d-%m-%Y")
    log.info(f"Today's date (PKT): {today_date_str}")

    # ── Verify it's Friday (safety check inside agent too) ────────
    # The CronJob already ensures this runs on Fridays,
    # but we double-check here as a safeguard.
    if today.strftime("%A") != "Friday":
        log.warning(f"Today is {today.strftime('%A')}, not Friday. Exiting.")
        return

    # ── Define tools available to the agent ──────────────────────
    tools = [
        get_maghrib_time,
        check_existing_reminder,
        create_wazifa_reminder,
    ]

    # ── Initialize the LLM ───────────────────────────────────────
    # Using GPT-4o-mini — lightweight, fast, and sufficient for
    # this structured tool-calling pipeline.
    # You can swap this for any other LangChain-compatible LLM.
    llm = ChatGroq(
    model="openai/gpt-oss-120b",  # or another valid Groq model
    temperature=0,
    api_key=os.getenv("GROK_API_KEY"),
)
    

    # ── Create the ReAct Agent ────────────────────────────────────
    # ReAct = Reasoning + Acting — the agent thinks step by step
    # and decides which tool to call at each step.
    agent = create_react_agent(
        llm=llm,
        tools=tools,
        prompt=AGENT_PROMPT,
    )

    # ── Wrap in AgentExecutor ────────────────────────────────────
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,           # Prints step-by-step reasoning to logs
        max_iterations=6,       # Safety limit — our pipeline is only 3 steps
        handle_parsing_errors=True,
    )

    # ── Run the agent ─────────────────────────────────────────────
    try:
        result = agent_executor.invoke({
            "today_date": today_date_str,
        })
        log.info("─" * 60)
        log.info("AGENT RESULT:")
        log.info(result.get("output", "No output returned"))
        log.info("─" * 60)

    except Exception as e:
        log.error(f"Agent encountered an error: {str(e)}", exc_info=True)
        raise


# ─────────────────────────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    run_agent()