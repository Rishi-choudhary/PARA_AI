import google.generativeai as genai
import config
import json
import logging
from datetime import datetime, timedelta

# Configure the logger for this module
logger = logging.getLogger(__name__)

# --- AI Configuration ---
try:
    genai.configure(api_key=config.GEMINI_API_KEY)
    generation_config = {"temperature": 0.2, "top_p": 1, "top_k": 1, "max_output_tokens": 2048}
    model = genai.GenerativeModel(model_name="gemini-1.5-flash", generation_config=generation_config)
    logger.info("Gemini AI model configured successfully.")
except Exception as e:
    logger.error(f"Failed to configure Gemini AI: {e}")
    model = None

# --- Core AI Processing Functions ---
def process_text_with_ai(text: str) -> dict | None:
    if not model: return None
    prompt = f"""
        Analyze the following text and classify it according to the PARA method.
        Your response MUST be a JSON object with three keys: "category", "title", and "tags".
        1.  "category": Classify into "Projects", "Areas", "Resources", or "Archive".
        2.  "title": Create a concise, clear title. IMPORTANT: If the text is a simple task like "Call the plumber" or "Buy milk", the title MUST be the original text. Do not change it. For longer notes, summarize them.
        3.  "tags": Extract 1-3 relevant keywords as a list of strings.
        Text to analyze: --- {text} ---
        Provide only the JSON object in your response.
    """
    try:
        response = model.generate_content(prompt)
        cleaned_response_text = response.text.strip().replace("```json", "").replace("```", "").strip()
        ai_result = json.loads(cleaned_response_text)
        return ai_result if all(key in ai_result for key in ["category", "title", "tags"]) else None
    except Exception as e:
        logger.error(f"An unexpected error occurred during AI processing: {e}")
        return None

def extract_task_details(text: str) -> dict | None:
    """Uses AI to extract the task name and a due date from natural language."""
    if not model:
        return None

    today_date = datetime.now().strftime("%Y-%m-%d")
    prompt = f"""
        Analyze the following task description. Extract the core task and a due date if one is mentioned.
        Today's date is {today_date}.
        - If a specific date is mentioned (e.g., "August 28th", "tomorrow"), calculate the date in YYYY-MM-DD format.
        - If no date is mentioned, the "due_date" should be null.
        Your response MUST be a JSON object with two keys: "task_name" and "due_date".

        Example outputs:
        - "Call the plumber tomorrow" -> {{"task_name": "Call the plumber", "due_date": "{(datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')}"}}
        - "Finish the report by Friday" -> {{"task_name": "Finish the report", "due_date": null}}
        - "Buy groceries" -> {{"task_name": "Buy groceries", "due_date": null}}
        - "Schedule meeting for September 5th" -> {{"task_name": "Schedule meeting", "due_date": "{datetime.now().year}-09-05"}}

        Analyze this task: --- {text} ---
        Provide only the JSON object in your response.
    """

    try:
        logger.info(f"Extracting task details from: '{text}'")

        # ✅ Add timeout so it doesn’t hang forever
        response = model.generate_content(prompt, request_options={"timeout": 20})

        raw_text = response.text.strip()
        logger.debug(f"Gemini raw response: {raw_text}")

        # ✅ Clean and parse JSON safely
        cleaned = raw_text.replace("```json", "").replace("```", "").strip()
        try:
            task_details = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON from AI: {raw_text}")
            return None

        logger.info(f"Extracted task details: {task_details}")
        return task_details if "task_name" in task_details else None

    except Exception as e:
        logger.error(f"Error during task extraction: {e}")
        return None


def is_project_complex(project_title: str) -> bool:
    if not model: return False
    prompt = f"""Analyze the project title: "{project_title}". Is it a simple, single-step task or a complex, multi-step project? Respond with "simple" or "complex"."""
    try:
        response = model.generate_content(prompt)
        return "complex" in response.text.strip().lower()
    except Exception: return False

def break_down_project(project_title: str) -> list[str] | None:
    if not model: return None
    prompt = f"""Break down the project "{project_title}" into 3 to 8 actionable sub-tasks. Respond with a JSON object: {{"tasks": ["task1", "task2"]}}"""
    try:
        response = model.generate_content(prompt)
        cleaned_response_text = response.text.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned_response_text).get("tasks")
    except Exception: return None