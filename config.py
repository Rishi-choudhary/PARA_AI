import os
from dotenv import load_dotenv

# Load environment variables from a .env file if it exists
load_dotenv()

# --- Telegram Configuration ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8323842575:AAF5WXuo4qbtwJuCWwFtCwTVIp2F4wBoBeM")

# --- Notion Configuration ---
NOTION_API_KEY = os.getenv("NOTION_API_KEY", "secret_17602919602zRxYEeZrPT6kziTZvb71sY1EN6THqAox4Nc")
NOTION_PROJECTS_DB_ID = os.getenv("NOTION_PROJECTS_DB_ID", "258419373cb280b48232d4db6aa9649c")
NOTION_AREAS_DB_ID = os.getenv("NOTION_AREAS_DB_ID", "258419373cb28060990ad14608772536")
NOTION_RESOURCES_DB_ID = os.getenv("NOTION_RESOURCES_DB_ID", "258419373cb280fa8e49f7e1b15662a7")
NOTION_ARCHIVES_DB_ID = os.getenv("NOTION_ARCHIVES_DB_ID", "258419373cb280328cb9d49b8008b26e")
NOTION_TASKS_DB_ID = os.getenv("NOTION_TASKS_DB_ID", "25c419373cb280b7bc88f56343a14450") # New Tasks Database ID

# --- AI Engine (Google Gemini) Configuration ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyCttgKQTyJyj36MUHsNlFZE4_Fs4r5CzUk")