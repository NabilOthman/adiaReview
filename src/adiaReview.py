import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="urllib3")

import os
import logging
import sys
from datetime import datetime, timezone
import requests
from dotenv import load_dotenv
from pydantic import BaseModel, Field
import anthropic
import json

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
SOURCE_DB_ID = os.getenv("SOURCE_DB_ID")
TRACKER_DB_ID = os.getenv("TRACKER_DB_ID")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

if not all([NOTION_TOKEN, SOURCE_DB_ID, TRACKER_DB_ID, CLAUDE_API_KEY]):
    logger.error("Error: Missing one or more environment variables in your .env file.")
    sys.exit(1)

anthropic_client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

notion_headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

# --- Pydantic Schemas ---
class QuestionItem(BaseModel):
    question: str
    reference_answer: str

class ConceptProfile(BaseModel):
    concept_name: str
    is_new: bool = Field(description="True if this is a completely new concept. False if you are updating an existing one.")
    knowledge_profile: str = Field(description="The atomic summary and depth guardrail.")
    questions: list[QuestionItem] = Field(description="1-3 questions testing this concept.")

class IngestionPayload(BaseModel):
    # FIXED: Added default_factory=list to prevent crashes if Claude returns {}
    concepts: list[ConceptProfile] = Field(default_factory=list, description="List of extracted concepts. If none found, return an empty list.")

class RetrievalPayload(BaseModel):
    questions: list[QuestionItem]


# --- Notion API: Source Database (Notes) ---
def get_triggered_review_pages():
    payload = {"filter": {"property": "Review", "select": {"equals": "Yes"}}}
    url = f"https://api.notion.com/v1/databases/{SOURCE_DB_ID}/query"
    response = requests.post(url, headers=notion_headers, json=payload)
    return response.json().get('results', []) if response.status_code == 200 else []

def finalize_source_note(page_id, existing_concepts, new_concepts):
    """Appends any new concepts to the tag list and flips Review back to No."""
    # Combine and remove duplicate string names safely
    updated_concepts_strings = list(set(existing_concepts + new_concepts)) 
    
    # Format exactly how the Notion API expects a multi-select update
    payload = {
        "properties": {
            "Review": {
                "select": {"name": "Done"}
            },
            "Concepts": {
                "multi_select": [{"name": c_name} for c_name in updated_concepts_strings]
            }
        }
    }
    
    url = f"https://api.notion.com/v1/pages/{page_id}"
    res = requests.patch(url, headers=notion_headers, json=payload)
    
    if res.status_code == 200:
        logger.info(f" -> SUCCESSFULLY synced Notion: Added {len(new_concepts)} new tags & reset Review to 'No'.")
    else:
        logger.error(f" -> FAILED to sync Notion state. Code: {res.status_code}, Error: {res.text}")

def get_page_text(page_id):
    url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    res = requests.get(url, headers=notion_headers)
    if res.status_code != 200: return ""
    
    full_text = ""
    for block in res.json().get('results', []):
        b_type = block.get('type')
        if b_type and 'rich_text' in block[b_type]:
            full_text += "".join([t.get('plain_text', '') for t in block[b_type]['rich_text']]) + "\n"
    return full_text

# --- Notion API: Tracker Database (Spaced Repetition) ---
def get_tracker_row(concept_name):
    payload = {"filter": {"property": "Concept", "title": {"equals": concept_name}}}
    url = f"https://api.notion.com/v1/databases/{TRACKER_DB_ID}/query"
    res = requests.post(url, headers=notion_headers, json=payload)
    if res.status_code == 200 and res.json().get("results"):
        return res.json()["results"][0]
    return None

def extract_knowledge_profile(tracker_row):
    props = tracker_row.get("properties", {})
    rt_array = props.get("Knowledge Profile", {}).get("rich_text", [])
    return "".join([t.get("plain_text", "") for t in rt_array])

def get_due_concepts():
    """Finds concepts where 'Next Review' is on or before today."""
    today = datetime.now(timezone.utc).date().isoformat()
    payload = {"filter": {"property": "Next Review", "date": {"on_or_before": today}}}
    url = f"https://api.notion.com/v1/databases/{TRACKER_DB_ID}/query"
    res = requests.post(url, headers=notion_headers, json=payload)
    return res.json().get('results', []) if res.status_code == 200 else []

def upsert_tracker_concept(concept_name, profile_text, is_new, priority_level):
    tracker_row = get_tracker_row(concept_name)
    safe_profile = profile_text[:1999] 
    
    if tracker_row:
        payload = {"properties": {"Knowledge Profile": {"rich_text": [{"text": {"content": safe_profile}}]}}}
        requests.patch(f"https://api.notion.com/v1/pages/{tracker_row['id']}", headers=notion_headers, json=payload)
    else:
        today = datetime.now(timezone.utc).date().isoformat()
        payload = {
            "parent": {"database_id": TRACKER_DB_ID},
            "properties": {
                "Concept": {"title": [{"text": {"content": concept_name}}]},
                "Knowledge Profile": {"rich_text": [{"text": {"content": safe_profile}}]},
                "Priority": {"select": {"name": priority_level}}, # <--- Added Priority Fan-out
                "Repetitions": {"number": 0},
                "Ease Factor": {"number": 2.5},
                "Interval": {"number": 1},
                "Next Review": {"date": {"start": today}},
                "Last Score": {"number": 0}
            }
        }
        requests.post("https://api.notion.com/v1/pages", headers=notion_headers, json=payload)


# --- Claude Intelligence Layer ---
def process_incremental_ingestion(text, existing_context):
    prompt = f"""
    You are an expert engineering and applied mathematics professor. Analyze the technical notes below.
    
    Existing Concepts & Their Current Knowledge Profiles (Boundary Fences):
    {existing_context if existing_context else "None yet."}
    
    CRITICAL INGESTION RULES:
    1. SYNTHESIS OVER FRAGMENTATION: Do not create highly fragmented, redundant concepts. Group deeply coupled ideas, algorithms, equations, or mechanisms into singular, comprehensive conceptual pillars. (For example, do not separate a mathematical theorem, its geometric interpretation, and its programmatic implementation into three different concepts—they belong to one unified concept).
    2. BUDGET CONSTRAINT: To prevent API token truncation, select and extract ONLY the TOP 3 most important, highest-priority synthesized concepts from the text below. Do not attempt to output more than 3 concepts.
    
    Tasks:
    1. SCRATCHPAD REASONING: Output a brief plain-text summary identifying the core themes present. Explicitly state how you are aggressively grouping related ideas to avoid redundancy, and list the final 3 prioritized concepts you will extract.
    2. STRUCTURED EXTRACTION: Immediately use the 'record_ingestion' tool to formally save those 3 synthesized concept profiles.
    3. QUESTION RIGOR: For each concept, generate 2-3 high-quality, rigorous active recall questions. DO NOT ask the exact same fundamental question in three different ways. Each question MUST test a completely different facet of the concept (e.g., Q1 tests mathematical intuition, Q2 tests physical/system tradeoffs, Q3 tests algorithmic edge cases). Do not give away the answer or equation in the text of the question.
    
    Documentation Text to Process:
    {text}
    """
    
    res = anthropic_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=3500, 
        temperature=0.2, 
        tools=[{"name": "record_ingestion", "description": "Save concepts.", "input_schema": IngestionPayload.model_json_schema()}],
        messages=[{"role": "user", "content": prompt}]
    )
    
    tool_use_block = None
    for content_block in res.content:
        if content_block.type == "tool_use":
            tool_use_block = content_block
            break
    
    if tool_use_block:
        input_data = tool_use_block.input
        if "concepts" not in input_data:
            input_data = {"concepts": []}
        return IngestionPayload(**input_data)
        
    raise ValueError("Claude completed its scratchpad but failed to invoke the structured tool call.")
def generate_dynamic_retrieval_questions(concept_name, profile_text):
    prompt = f"""
    You are an active recall engine testing an engineering student.
    
    Concept: {concept_name}
    Knowledge Boundary: {profile_text}
    
    Generate 3 fresh conceptual questions testing the internal mechanics of this concept. 
    Crucial: Do not exceed the scope defined in the Knowledge Boundary. 
    Provide a highly precise reference answer for each.
    """
    
    res = anthropic_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1500,
        temperature=0.4,
        tools=[{"name": "record_retrieval", "description": "Save questions.", "input_schema": RetrievalPayload.model_json_schema()}],
        tool_choice={"type": "tool", "name": "record_retrieval"},
        messages=[{"role": "user", "content": prompt}]
    )
    for block in res.content:
        if block.type == "tool_use": return RetrievalPayload(**block.input)
    raise ValueError("Claude Retrieval Failed.")


# --- Desktop Export ---
def append_to_desktop(concept_name, questions, source_page_id="RETRIEVAL"):
    desktop_path = os.path.expanduser("~/Desktop/Daily_Review.md")
    content = f"\n\n## Concept: {concept_name}\n"
    
    for item in questions:
        content += f"<!-- PAGE_ID: {source_page_id} -->\n"
        content += f"<!-- CONCEPT_NAME: {concept_name} -->\n"
        content += f"<!-- REF_ANSWER: {item.reference_answer} -->\n"
        content += f"**Q:** {item.question}\n"
        content += f"**Answer:** [Type your answer here]\n\n---\n"
        
    with open(desktop_path, "a", encoding="utf-8") as file:
        file.write(content)


# --- Core Orchestration ---
def main():
    processed_concepts_today = set()
    
    logger.info("=== PHASE 1: INGESTION (Notes marked Review: Yes) ===")
    triggered_pages = get_triggered_review_pages()
    
    if not triggered_pages:
        logger.info("No new updates found.")
    
    for page in triggered_pages:
        page_id = page['id']
        props = page.get("properties", {})
        
        # 1. Pull Name
        title_array = props.get("Name", {}).get("title", []) 
        page_title = "".join([t.get("plain_text", "") for t in title_array]) if title_array else "Untitled"
        
        # 2. Pull the Priority from the Source Note (High, Standard, Low)
        priority_data = props.get("Priority", {}).get("select")
        note_priority = priority_data.get("name") if priority_data else "Standard"
        
        existing_concept_names = [c.get("name") for c in props.get("Concepts", {}).get("multi_select", [])]
        
        # --- ADD/VERIFY THIS BLOCK HERE ---
        existing_context = ""
        for c_name in existing_concept_names:
            tracker_row = get_tracker_row(c_name)
            if tracker_row:
                profile = extract_knowledge_profile(tracker_row)
                existing_context += f"- **{c_name}**: {profile}\n"
        # ----------------------------------
        
        logger.info(f"\nProcessing Note: '{page_title}' [Priority: {note_priority}]...")
        note_text = get_page_text(page_id)
        if not note_text.strip(): continue
        
        try:
            payload = process_incremental_ingestion(note_text, existing_context)
            
            if not payload.concepts:
                logger.info(f" -> No core technical concepts identified. Skipping.")
                finalize_source_note(page_id, existing_concept_names, [])
                continue
                
            new_concept_names_to_tag = []
            for concept in payload.concepts:
                clean_name = concept.concept_name.replace(",", "")
                concept.concept_name = clean_name
                
                logger.info(f" -> Processed Concept: {concept.concept_name}")
                
                # FIX: We must pass the 'note_priority' string we grabbed above!
                upsert_tracker_concept(
                    concept_name=concept.concept_name, 
                    profile_text=concept.knowledge_profile, 
                    is_new=concept.is_new, 
                    priority_level=note_priority # <--- This handles the fan-out
                )
                
                append_to_desktop(concept.concept_name, concept.questions, source_page_id=page_id)
                new_concept_names_to_tag.append(concept.concept_name)
                processed_concepts_today.add(concept.concept_name)
                
            finalize_source_note(page_id, existing_concept_names, new_concept_names_to_tag)
            
        except Exception as e:
            logger.error(f"Error processing '{page_title}': {e}")

if __name__ == "__main__":
    main()