import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="urllib3")


import os
import logging
import sys
from datetime import datetime, timezone
import requests
from dotenv import load_dotenv
from pydantic import BaseModel
import anthropic

# Dynamically find the project root so it works on any computer
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# Configure the universal logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "morning_system.log")),
        logging.StreamHandler(sys.stdout) # Keeps terminal output alive for manual testing
    ]
)
logger = logging.getLogger(__name__)


load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
TRACKER_DB_ID = os.getenv("TRACKER_DB_ID")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

if not all([NOTION_TOKEN, TRACKER_DB_ID, CLAUDE_API_KEY]):
    print("Error: Missing one or more environment variables in your .env file.")
    sys.exit(1)

anthropic_client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

notion_headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

# --- Pydantic Schema ---
class QuestionItem(BaseModel):
    question: str
    reference_answer: str

class RetrievalPayload(BaseModel):
    questions: list[QuestionItem]


# --- Notion Data Layer ---
def get_due_concepts():
    """Finds concepts in the Tracker DB where 'Next Review' is on or before today."""
    # Using local date to match your timezone study habits
    today = datetime.now().date().isoformat()
    
    payload = {
        "filter": {
            "property": "Next Review",
            "date": {
                "on_or_before": today
            }
        }
    }
    
    url = f"https://api.notion.com/v1/databases/{TRACKER_DB_ID}/query"
    res = requests.post(url, headers=notion_headers, json=payload)
    
    if res.status_code != 200:
        print(f"Failed to query Tracker DB: {res.text}")
        return []
        
    return res.json().get('results', [])

def extract_knowledge_profile(tracker_row):
    """Pulls the hidden boundary fence text from the database row."""
    props = tracker_row.get("properties", {})
    rt_array = props.get("Knowledge Profile", {}).get("rich_text", [])
    return "".join([t.get("plain_text", "") for t in rt_array])


# --- Claude Generation Layer ---
def generate_dynamic_retrieval_questions(concept_name, profile_text):
    """Forces Claude to generate strictly bounded questions based on historical state."""
    prompt = f"""
    You are an active recall engine testing an engineering student.
    
    Concept: {concept_name}
    Knowledge Boundary: {profile_text}
    
    Generate 3 fresh conceptual questions testing the internal mechanics of this concept. 
    Crucial: Do not exceed the scope defined in the Knowledge Boundary. You must ensure the student is tested on the core mechanisms without repeating the exact same phrasing from previous tests.
    Provide a highly precise engineering reference answer for each.
    """
    
    res = anthropic_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1500,
        temperature=0.4, # 0.4 provides structural consistency while allowing question variation
        tools=[{"name": "record_retrieval", "description": "Save questions.", "input_schema": RetrievalPayload.model_json_schema()}],
        tool_choice={"type": "tool", "name": "record_retrieval"},
        messages=[{"role": "user", "content": prompt}]
    )
    
    for block in res.content:
        if block.type == "tool_use": 
            return RetrievalPayload(**block.input)
            
    raise ValueError("Claude Retrieval Generation Failed.")


# --- Desktop Export ---
def append_to_desktop(concept_name, questions):
    """Writes the generated questions to your daily Markdown file."""
    desktop_path = os.path.expanduser("~/Desktop/Daily_Review.md")
    content = f"\n\n## Concept: {concept_name}\n"
    
    for item in questions:
        # Using RETRIEVAL tag to signify this came from the active recall loop, not a new note
        content += f"<!-- PAGE_ID: RETRIEVAL -->\n"
        content += f"<!-- CONCEPT_NAME: {concept_name} -->\n"
        content += f"<!-- REF_ANSWER: {item.reference_answer} -->\n"
        content += f"**Q:** {item.question}\n"
        content += f"**Answer:** [Type your answer here]\n\n---\n"
        
    with open(desktop_path, "a", encoding="utf-8") as file:
        file.write(content)


# --- Core Orchestration ---
def main():
    logger.info("=== ACTIVE RECALL GENERATION ===")
    logger.info("Querying Tracker Database for due concepts...")
    
    due_concepts_rows = get_due_concepts()
    
    if not due_concepts_rows:
        logger.info("No concepts are due for review today. Enjoy your day!")
        return
        
    retrieval_count = 0
    
    for row in due_concepts_rows:
        title_array = row.get("properties", {}).get("Concept", {}).get("title", [])
        concept_name = "".join([t.get("plain_text", "") for t in title_array])
        
        if not concept_name:
            continue
            
        logger.info(f"Generating dynamic recall questions for: '{concept_name}'...")
        profile = extract_knowledge_profile(row)
        
        if not profile:
            logger.info(f" -> Skipping: No Knowledge Profile found to boundary-check.")
            continue
            
        try:
            payload = generate_dynamic_retrieval_questions(concept_name, profile)
            append_to_desktop(concept_name, payload.questions)
            retrieval_count += 1
        except Exception as e:
            logger.error(f"Error generating retrieval for '{concept_name}': {e}")

    logger.info(f"\nSuccessfully generated fresh dynamic questions for {retrieval_count} concepts.")
    logger.info("Check your ~/Desktop/Daily_Review.md file!")

if __name__ == "__main__":
    main()
