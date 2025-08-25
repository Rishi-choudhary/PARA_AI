import google.generativeai as genai
import config
import json
import logging

# Configure the logger for this module
logger = logging.getLogger(__name__)

# --- AI Configuration ---
try:
    genai.configure(api_key=config.GEMINI_API_KEY)
    generation_config = {"temperature": 0.5, "top_p": 1, "top_k": 1, "max_output_tokens": 2048}
    model = genai.GenerativeModel(model_name="gemini-1.5-flash", generation_config=generation_config)
    logger.info("Gemini AI model configured successfully.")
except Exception as e:
    logger.error(f"Failed to configure Gemini AI: {e}")
    model = None

# --- Core AI Processing Functions ---
def process_text_with_ai(text: str) -> dict | None:
    # ... (This function remains unchanged)
    if not model:
        logger.error("AI model is not available. Cannot process text.")
        return None
    prompt = f"""
        Analyze the following text and classify it according to the PARA method.
        Your response MUST be a JSON object with three keys: "category", "title", and "tags".
        1.  "category": Classify into "Projects", "Areas", "Resources", or "Archive".
        2.  "title": Create a concise, clear title.
        3.  "tags": Extract 1-3 relevant keywords as a list of strings.
        Text to analyze: --- {text} ---
        Provide only the JSON object in your response.
    """
    try:
        logger.info(f"Sending text to AI for processing: '{text[:50]}...'")
        response = model.generate_content(prompt)
        cleaned_response_text = response.text.strip().replace("```json", "").replace("```", "").strip()
        logger.info(f"AI Response received: {cleaned_response_text}")
        ai_result = json.loads(cleaned_response_text)
        if all(key in ai_result for key in ["category", "title", "tags"]):
            return ai_result
        else:
            logger.error(f"AI response was missing required keys: {ai_result}")
            return None
    except Exception as e:
        logger.error(f"An unexpected error occurred during AI processing: {e}")
        return None

def break_down_project(project_title: str) -> list[str] | None:
    """
    Uses the AI to break down a project title into a list of sub-tasks.
    """
    if not model:
        logger.error("AI model is not available. Cannot break down project.")
        return None

    prompt = f"""
        You are a project manager. Break down the following project into a series of actionable sub-tasks.
        Generate between 3 and 8 sub-tasks.
        Your response MUST be a JSON object with a single key "tasks", which contains a list of strings.
        
        Project: "{project_title}"

        Provide only the JSON object in your response. Example format:
        {{"tasks": ["First task to do", "Second task to do", "Third task to do"]}}
    """
    try:
        logger.info(f"Sending project to AI for breakdown: '{project_title}'")
        response = model.generate_content(prompt)
        cleaned_response_text = response.text.strip().replace("```json", "").replace("```", "").strip()
        logger.info(f"AI sub-task response received: {cleaned_response_text}")
        
        result = json.loads(cleaned_response_text)
        if "tasks" in result and isinstance(result["tasks"], list):
            return result["tasks"]
        else:
            logger.error(f"AI sub-task response was in an invalid format: {result}")
            return None
            
    except Exception as e:
        logger.error(f"An unexpected error occurred during project breakdown: {e}")
        return None