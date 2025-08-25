import os
from dotenv import load_dotenv

# This line loads the .env file into the environment
load_dotenv()

# --- Configuration ---
# This code now safely gets the keys from the environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_PROJECTS_DB_ID = os.getenv("NOTION_PROJECTS_DB_ID")
NOTION_AREAS_DB_ID = os.getenv("NOTION_AREAS_DB_ID")
NOTION_RESOURCES_DB_ID = os.getenv("NOTION_RESOURCES_DB_ID")
NOTION_ARCHIVES_DB_ID = os.getenv("NOTION_ARCHIVES_DB_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")