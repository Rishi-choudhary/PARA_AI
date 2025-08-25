# File 4: notion_handler.py (UPDATED)
#
# The `add_item_to_database` function is now more powerful. It can
# create a to-do list inside the Notion page, which is perfect
# for our project sub-tasks.
# =================================================================

import requests
import json
import logging
import config

logger = logging.getLogger(__name__)

# --- Notion API Configuration ---
NOTION_API_URL = "https://api.notion.com/v1/pages"
HEADERS = {
    "Authorization": f"Bearer {config.NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

DATABASE_IDS = {
    "Projects": config.NOTION_PROJECTS_DB_ID,
    "Areas": config.NOTION_AREAS_DB_ID,
    "Resources": config.NOTION_RESOURCES_DB_ID,
    "Archive": config.NOTION_ARCHIVES_DB_ID,
}

def add_item_to_database(ai_data: dict, content_blocks: list = None) -> str | None:
    # ... (This function remains mostly the same, but the payload construction is more robust)
    category = ai_data.get("category")
    title = ai_data.get("title")
    tags = ai_data.get("tags", [])

    database_id = DATABASE_IDS.get(category)
    if not database_id:
        logger.error(f"Invalid or unsupported category: {category}")
        return None

    new_page_data = {
        "parent": {"database_id": database_id},
        "properties": {
            "Name": {"title": [{"text": {"content": title}}]},
            "Tags": {"multi_select": [{"name": tag} for tag in tags]}
        }
    }

    if content_blocks:
        new_page_data["children"] = content_blocks

    try:
        logger.info(f"Adding item to Notion '{category}' database: '{title}'")
        response = requests.post(NOTION_API_URL, headers=HEADERS, data=json.dumps(new_page_data))
        response.raise_for_status()
        response_json = response.json()
        page_url = response_json.get("url")
        logger.info(f"Successfully created Notion page with URL: {page_url}")
        return page_url

    except requests.exceptions.RequestException as e:
        logger.error(f"Error adding item to Notion: {e}")
        logger.error(f"Response Body: {e.response.text if e.response else 'No Response'}")
        return None

def add_project_with_tasks(ai_data: dict, tasks: list[str]) -> str | None:
    """Creates a Notion page for a project and adds a to-do list of tasks."""
    task_blocks = [
        {
            "object": "block",
            "type": "to_do",
            "to_do": {
                "rich_text": [{"type": "text", "text": {"content": task}}],
                "checked": False
            }
        } for task in tasks
    ]
    return add_item_to_database(ai_data, content_blocks=task_blocks)

# ... (The add_content_to_resources function remains unchanged)
def add_content_to_resources(title: str, content_url: str, content_type: str) -> str | None:
    ai_data = {"category": "Resources", "title": title, "tags": [content_type.capitalize()]}
    content_block = {}
    if content_type == "url":
        content_block = {"object": "block", "type": "bookmark", "bookmark": {"url": content_url}}
    else:
        content_block = {"object": "block", "type": "embed", "embed": {"url": content_url}}
    return add_item_to_database(ai_data, content_blocks=[content_block])