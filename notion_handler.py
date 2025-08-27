import requests
import json
import logging
import config
from datetime import datetime, timezone


logger = logging.getLogger(__name__)

# --- Notion API Configuration ---
NOTION_API_BASE_URL = "https://api.notion.com/v1"
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
    "Tasks": config.NOTION_TASKS_DB_ID,
}

# --- Core Functions ---
def add_item_to_database(ai_data: dict, content_blocks: list = None) -> str | None:
    category, title, tags = ai_data.get("category"), ai_data.get("title"), ai_data.get("tags", [])
    database_id = DATABASE_IDS.get(category)
    if not database_id: return None
    new_page_data = {"parent": {"database_id": database_id}, "properties": {"Name": {"title": [{"text": {"content": title}}]}, "Tags": {"multi_select": [{"name": tag} for tag in tags]}}}
    if content_blocks: new_page_data["children"] = content_blocks
    try:
        response = requests.post(f"{NOTION_API_BASE_URL}/pages", headers=HEADERS, data=json.dumps(new_page_data))
        response.raise_for_status()
        return response.json().get("url")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error adding item to Notion: {e}")
        return None

def add_task(task_details: dict) -> str | None:
    """Adds a new task to the Tasks database in Notion."""
    task_name = task_details.get("task_name")
    due_date = task_details.get("due_date")
    
    if not task_name: return None
    
    database_id = DATABASE_IDS.get("Tasks")
    if not database_id:
        logger.error("Tasks Database ID is not configured.")
        return None
        
    properties = {
        "Task Name": {"title": [{"text": {"content": task_name}}]},
        "Status": {"select": {"name": "To Do"}}
    }
    
    if due_date:
        properties["Due Date"] = {"date": {"start": due_date}}

    new_page_data = {"parent": {"database_id": database_id}, "properties": properties}

    try:
        response = requests.post(f"{NOTION_API_BASE_URL}/pages", headers=HEADERS, data=json.dumps(new_page_data))
        response.raise_for_status()
        return response.json().get("url")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error adding task to Notion: {e}")
        return None

def get_tasks_due_today() -> list[str] | None:
    """Queries the Tasks database for tasks due today."""
    db_id = DATABASE_IDS.get("Tasks")
    if not db_id:
        logger.error("Tasks Database ID is not configured.")
        return None
    
    today_iso = datetime.now(timezone.utc).date().isoformat()
    
    query_payload = {
        "filter": {
            "property": "Due Date",
            "date": {
                "equals": today_iso
            }
        }
    }
    try:
        response = requests.post(f"{NOTION_API_BASE_URL}/databases/{db_id}/query", headers=HEADERS, data=json.dumps(query_payload))
        response.raise_for_status()
        results = response.json().get("results", [])
        
        task_titles = []
        for page in results:
            title_list = page.get("properties", {}).get("Task Name", {}).get("title", [])
            if title_list:
                title = title_list[0].get("plain_text", "Untitled")
                task_titles.append(title)
        
        return task_titles
    except requests.exceptions.RequestException as e:
        logger.error(f"Error getting tasks due today: {e}")
        return None


def get_daily_summary() -> dict:
    """Counts the number of pages created today in each main database."""
    summary = {"Projects": 0, "Areas": 0, "Resources": 0, "Tasks": 0}
    today_iso = datetime.now(timezone.utc).date().isoformat()

    for db_name, db_id in DATABASE_IDS.items():
        if db_name == "Archive" or not db_id: continue

        query_payload = {
            "filter": {
                 "timestamp": "created_time",
                 "created_time": { "on_or_after": today_iso }
            }
        }
        try:
            response = requests.post(f"{NOTION_API_BASE_URL}/databases/{db_id}/query", headers=HEADERS, data=json.dumps(query_payload))
            response.raise_for_status()
            count = len(response.json().get("results", []))
            summary[db_name] = count
        except requests.exceptions.RequestException as e:
            logger.warning(f"Could not get summary for {db_name}: {e}")
            
    return summary

def search_databases_for_exact_title(title: str) -> dict | None:
    searchable_db_ids = [DATABASE_IDS["Projects"], DATABASE_IDS["Areas"], DATABASE_IDS["Resources"]]
    for db_id in searchable_db_ids:
        if not db_id: continue
        query_payload = {"filter": {"property": "Name", "title": {"equals": title}}}
        try:
            search_url = f"{NOTION_API_BASE_URL}/databases/{db_id}/query"
            response = requests.post(search_url, headers=HEADERS, data=json.dumps(query_payload))
            response.raise_for_status()
            results = response.json().get("results")
            if results: return {"page_id": results[0]["id"], "url": results[0]["url"], "properties": results[0]["properties"]}
        except requests.exceptions.RequestException as e: logger.error(f"Error searching database {db_id}: {e}")
    return None

def add_note_to_page(page_id: str, note: str) -> bool:
    append_url = f"{NOTION_API_BASE_URL}/blocks/{page_id}/children"
    new_block_data = {"children": [{"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": note}}]}}]}
    try:
        requests.patch(append_url, headers=HEADERS, data=json.dumps(new_block_data)).raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Error adding note to page: {e}")
        return False

def get_active_projects() -> list[str] | None:
    db_id = DATABASE_IDS.get("Projects")
    if not db_id: return None
    query_url = f"{NOTION_API_BASE_URL}/databases/{db_id}/query"
    try:
        response = requests.post(query_url, headers=HEADERS)
        response.raise_for_status()
        results = response.json().get("results", [])
        return [page.get("properties", {}).get("Name", {}).get("title", [{}])[0].get("plain_text", "Untitled") for page in results]
    except requests.exceptions.RequestException as e:
        logger.error(f"Error getting active projects: {e}")
        return None

def search_workspace(query: str) -> list[dict] | None:
    search_payload = {"query": query, "filter": {"value": "page", "property": "object"}, "sort": {"direction": "descending", "timestamp": "last_edited_time"}}
    try:
        response = requests.post(f"{NOTION_API_BASE_URL}/search", headers=HEADERS, data=json.dumps(search_payload))
        response.raise_for_status()
        results = response.json().get("results", [])
        return [{"title": page.get("properties", {}).get("Name", {}).get("title", [{}])[0].get("plain_text", "Untitled"), "url": page.get("url")} for page in results if page.get("properties", {}).get("Name", {}).get("title")]
    except requests.exceptions.RequestException as e:
        logger.error(f"Error searching workspace: {e}")
        return None

def move_page_to_archive(page_data: dict) -> bool:
    if not page_data: return False
    original_page_id, original_properties = page_data["page_id"], page_data["properties"]
    title_content, tags_content = original_properties.get("Name", {}).get("title", []), original_properties.get("Tags", {}).get("multi_select", [])
    new_properties = {"Name": {"title": title_content}, "Tags": {"multi_select": tags_content}}
    archive_payload = {"parent": {"database_id": DATABASE_IDS["Archive"]}, "properties": new_properties}
    try:
        requests.post(f"{NOTION_API_BASE_URL}/pages", headers=HEADERS, data=json.dumps(archive_payload)).raise_for_status()
        requests.patch(f"{NOTION_API_BASE_URL}/pages/{original_page_id}", headers=HEADERS, data=json.dumps({"archived": True})).raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Error moving page to archive: {e}")
        return False

def add_project_with_tasks(ai_data: dict, tasks: list[str]) -> str | None:
    task_blocks = [{"object": "block", "type": "to_do", "to_do": {"rich_text": [{"type": "text", "text": {"content": task}}]}} for task in tasks]
    return add_item_to_database(ai_data, content_blocks=task_blocks)

def add_content_to_resources(title: str, content_url: str, content_type: str) -> str | None:
    ai_data = {"category": "Resources", "title": title, "tags": [content_type.capitalize()]}
    content_block = {"object": "block", "type": "bookmark" if content_type == "url" else "embed", "bookmark" if content_type == "url" else "embed": {"url": content_url}}
    return add_item_to_database(ai_data, content_blocks=[content_block])
