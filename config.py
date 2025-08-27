import os
from dotenv import load_dotenv

# Load environment variables from a .env file if it exists
load_dotenv()

# --- Telegram Configuration ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# --- Notion Configuration ---
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_PROJECTS_DB_ID = os.getenv("NOTION_PROJECTS_DB_ID")
NOTION_AREAS_DB_ID = os.getenv("NOTION_AREAS_DB_ID")
NOTION_RESOURCES_DB_ID = os.getenv("NOTION_RESOURCES_DB_ID")
NOTION_ARCHIVES_DB_ID = os.getenv("NOTION_ARCHIVES_DB_ID")
NOTION_TASKS_DB_ID = os.getenv("NOTION_TASKS_DB_ID")

# --- AI Engine (Google Gemini) Configuration ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
