import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="urllib3")


import os
import logging
import sys
from datetime import datetime, timedelta, timezone
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
        logging.FileHandler(os.path.join(LOG_DIR, "evening_system.log")),
        logging.StreamHandler(sys.stdout) # Keeps terminal output alive for manual testing
    ]
)
logger = logging.getLogger(__name__)


load_dotenv()

# Verify tokens and Database ID
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
TRACKER_DB_ID = os.getenv("TRACKER_DB_ID")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

if not all([NOTION_TOKEN, TRACKER_DB_ID, CLAUDE_API_KEY]):
    logger.error("Error: Missing one or more environment variables in your .env file.")
    sys.exit(1)

anthropic_client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

notion_headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

# --- Strict Grading Schema ---
class GradingResult(BaseModel):
    score: int
    feedback: str

def grade_answer(question, reference_answer, user_answer):
    """Uses Claude 4.5 Haiku to critically evaluate the student's answer."""
    prompt = f"""
    You are an expert engineering professor grading a conceptual exam.
    
    Question: {question}
    Reference Answer: {reference_answer}
    Student's Answer: {user_answer}
    
    Evaluate the student's answer strictly against the reference. 
    1. Assign an integer score from 1 to 5:
       1 = Completely incorrect, blank, or contains severe structural hallucinations.
       3 = Partial conceptual understanding but missed a core mechanical step or coupling phase.
       5 = Flawless conceptual grasp of the underlying engineering physics.
    2. Provide a sharp, 1-sentence feedback note correcting any technical flaws or validating the logic.
    """
    
    response = anthropic_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1000,
        temperature=0.0,
        tools=[
            {
                "name": "record_grade",
                "description": "Log the evaluation score and feedback.",
                "input_schema": GradingResult.model_json_schema()
            }
        ],
        tool_choice={"type": "tool", "name": "record_grade"},
        messages=[{"role": "user", "content": prompt}]
    )
    
    for block in response.content:
        if block.type == "tool_use":
            return GradingResult(**block.input)
            
    raise ValueError("Grading failed.")

def calculate_sm2(score, repetitions, ease_factor, interval, priority="Standard"):
    """Computes the SuperMemo-2 intervals with Priority-weighted multipliers."""
    if score < 3:
        repetitions = 0
        base_interval = 1
    else:
        if repetitions == 0:
            base_interval = 1
        elif repetitions == 1:
            base_interval = 6
        else:
            base_interval = max(1, round(interval * ease_factor))
        repetitions += 1

    ease_factor = ease_factor + (0.1 - (5 - score) * (0.08 + (5 - score) * 0.02))
    if ease_factor < 1.3:
        ease_factor = 1.3

    # Apply Priority Multiplier Fan-out
    multiplier = 1.0
    if priority == "High":
        multiplier = 0.5
    elif priority == "Low":
        multiplier = 1.5

    final_interval = max(1, round(base_interval * multiplier))
    return repetitions, ease_factor, final_interval

# --- Notion API Connection Layer ---
def get_tracker_entry(concept_name):
    url = f"https://api.notion.com/v1/databases/{TRACKER_DB_ID}/query"
    payload = {"filter": {"property": "Concept", "title": {"equals": concept_name}}}
    response = requests.post(url, headers=notion_headers, json=payload)
    if response.status_code == 200:
        results = response.json().get("results", [])
        if results:
            return results[0]
    return None

def extract_current_metrics(tracker_page):
    props = tracker_page.get("properties", {})
    reps = props.get("Repetitions", {}).get("number") or 0
    ef = props.get("Ease Factor", {}).get("number") or 2.5
    interval = props.get("Interval", {}).get("number") or 1
    
    priority_data = props.get("Priority", {}).get("select")
    priority = priority_data.get("name") if priority_data else "Standard"
    return reps, ef, interval, priority

def update_tracker_entry(page_id, score, reps, ef, interval, next_review_date):
    url = f"https://api.notion.com/v1/pages/{page_id}"
    payload = {
        "properties": {
            "Repetitions": {"number": reps},
            "Ease Factor": {"number": round(ef, 2)},
            "Interval": {"number": interval},
            "Next Review": {"date": {"start": next_review_date}},
            "Last Score": {"number": score}
        }
    }
    requests.patch(url, headers=notion_headers, json=payload)

# --- Main In-Place Processing Loop ---
def process_daily_review_file():
    desktop_path = os.path.expanduser("~/Desktop/Daily_Review.md")
    # Store the archive visibly in the project folder
    archive_path = os.path.join(PROJECT_ROOT, "Grading_Archive.md")    
    if not os.path.exists(desktop_path):
        logger.warning("No Daily_Review.md found on Desktop. Aborting.")
        return

    with open(desktop_path, "r", encoding="utf-8") as file:
        content = file.read()

    blocks = [b.strip() for b in content.split("---") if b.strip()]
    
    remaining_blocks = []
    archived_blocks = []
    processed_count = 0
    local_cache = {}

    for block in blocks:
        if "**Q:**" not in block or "**Answer:**" not in block:
            remaining_blocks.append(block)
            continue
            
        try:
            if "REF_ANSWER:" not in block:
                remaining_blocks.append(block)
                continue
                
            concept_name = "Unknown Concept"
            if "CONCEPT_NAME:" in block:
                concept_name = block.split("CONCEPT_NAME:")[1].split("-->")[0].strip()
            
            ref_answer = block.split("REF_ANSWER:")[1].split("-->")[0].strip()
            question = block.split("**Q:**")[1].split("**Answer:**")[0].strip()
            user_answer = block.split("**Answer:**")[1].strip()
            
            if "<!--" in user_answer:
                user_answer = user_answer.split("<!--")[0].strip()
                
        except Exception:
            remaining_blocks.append(block)
            continue
        
        # Check if the user actually answered it
        if user_answer == "[Type your answer here]" or len(user_answer) < 5:
            remaining_blocks.append(block)
            continue
            
        logger.info(f"\nGrading Concept: {concept_name}")
        logger.info(f"Q: {question[:50]}...")
        
        try:
            # 1. Evaluate
            grade = grade_answer(question, ref_answer, user_answer)
            logger.info(f" -> Score: {grade.score}/5 | Feedback: {grade.feedback}")
            
            # 2. Get Metrics
            if concept_name in local_cache:
                current_reps = local_cache[concept_name]["reps"]
                current_ef = local_cache[concept_name]["ef"]
                current_interval = local_cache[concept_name]["interval"]
                priority = local_cache[concept_name]["priority"]
                tracker_page_id = local_cache[concept_name]["page_id"]
            else:
                tracker_page = get_tracker_entry(concept_name)
                if tracker_page:
                    current_reps, current_ef, current_interval, priority = extract_current_metrics(tracker_page)
                    tracker_page_id = tracker_page["id"]
                else:
                    current_reps, current_ef, current_interval, priority = 0, 2.5, 1, "Standard"
                    tracker_page_id = None
            
            # 3. SM-2 Calculate
            new_reps, new_ef, new_interval = calculate_sm2(
                grade.score, current_reps, current_ef, current_interval, priority
            )
            next_review_date = (datetime.now() + timedelta(days=new_interval)).date().isoformat()
            
            # 4. Update Notion Tracker
            if tracker_page_id:
                update_tracker_entry(tracker_page_id, grade.score, new_reps, new_ef, new_interval, next_review_date)
                
            local_cache[concept_name] = {
                "page_id": tracker_page_id,
                "reps": new_reps,
                "ef": new_ef,
                "interval": new_interval,
                "priority": priority
            }
            
            # Add evaluation data directly inside the archived markdown block
            graded_block = (
                f"{block}\n"
                f"<!-- GRADED_ON: {datetime.now().date().isoformat()} -->\n"
                f"<!-- ASSIGNED_SCORE: {grade.score} -->\n"
                f"**System Feedback:** *{grade.feedback}*\n"
            )
            archived_blocks.append(graded_block)
            processed_count += 1
            
        except Exception as err:
            logger.error(f" -> Error processing block: {err}")
            remaining_blocks.append(block)

    # --- Writeback and Clean up Layer ---
    if processed_count > 0:
        # Append graded questions to Archive
        with open(archive_path, "a", encoding="utf-8") as arch_file:
            arch_file.write(f"\n\n## REVIEW SESSION: {datetime.now().date().isoformat()}\n")
            arch_file.write("\n---\n".join(archived_blocks)) # FIXED TYPO HERE
            
        logger.info(f"\nSuccessfully archived {processed_count} graded items.")
        
        # Tell macOS to pop the file open on your screen!
        os.system(f"open '{archive_path}'")

    # Overwrite the Desktop file with ONLY unanswered blocks remaining
    if remaining_blocks:
        with open(desktop_path, "w", encoding="utf-8") as desk_file:
            desk_file.write("\n\n---\n\n".join(remaining_blocks) + "\n\n---\n")
        logger.warning("Unanswered questions remain in Daily_Review.md.")
    else:
        if os.path.exists(desktop_path):
            os.remove(desktop_path)
            logger.info("All questions completed. Daily_Review.md removed from Desktop.")

if __name__ == "__main__":
    process_daily_review_file()