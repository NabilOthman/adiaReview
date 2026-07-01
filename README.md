# AdiaReview: Autonomous AI Spaced-Repetition System

AdiaReview is a fully automated, offline-resilient, AI-driven spaced-repetition tutor built natively for macOS. 

Instead of manually writing flashcards, you simply take notes in Notion. Every morning, this system synthesizes your notes into core engineering concepts and generates rigorous active-recall questions right on your Desktop. Every evening, it grades your answers using Claude 4.5 Haiku, calculates your SuperMemo-2 (SM-2) memory intervals, and updates your Notion tracker automatically.

## ✨ Features
* **Zero-Click Scheduling:** Runs invisibly in the background using native macOS `launchd` automation.
* **Offline Resilient:** Smart bash wrappers poll for network connectivity. If you open your laptop in the car without Wi-Fi, it safely caches the state and retries every hour until you connect.
* **Rigorous AI Grading:** Powered by Anthropic's Claude 4.5 Haiku. It doesn't just check for keywords; it grades for structural engineering accuracy and provides 1-sentence mechanical feedback.
* **Unified Logging:** A single chronologically unified `system.log` tracks both OS-level network polling and Python-level API execution.

---

## 🛠 Prerequisites
* A Mac running macOS.
* Python 3.9+ installed.
* A [Notion API Integration Token](https://www.notion.so/my-integrations).
* An [Anthropic API Key](https://console.anthropic.com/).

---

## 🚀 Installation Guide

### 1. Clone the Repository
Open your terminal and run:
`bash
git clone https://github.com/YOUR_GITHUB_USERNAME/adiaReview.git
cd adiaReview
`

### 2. Set Up the Python Environment
Create a virtual environment and install the required dependencies:
`bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
`

### 3. Configure the Environment Variables
You need to connect the system to your API keys and Notion databases. Create a `.env` file in the root directory:
`bash
nano .env
`
Paste the following and fill in your specific keys and Database IDs:
`env
NOTION_TOKEN=secret_your_notion_integration_token
CLAUDE_API_KEY=sk-ant-your_claude_api_key
SOURCE_DB_ID=your_notion_notes_database_id
TRACKER_DB_ID=your_notion_spaced_repetition_database_id
`
*(Note: Ensure your Notion Integration is invited/connected to both databases via the 3-dot menu in Notion!)*

### 4. System Configuration
Create a `config.txt` file in the root directory to define your macOS bundle ID:
`bash
nano config.txt
`
Paste this single line:
`text
BUNDLE_ID=com.adiareview.system
`

### 5. Deploy the Automation
Run the deployment script to inject your local file paths into the `.plist` templates, grant execution permissions, and load them into macOS's `launchd` scheduler:
`bash
chmod +x automation/*.sh
./automation/deploy_jobs.sh
`

**You are done! The system is now live.**

---

## 🧠 Daily Workflow

1. **Take Notes:** Write your technical notes in your Notion Source Database. Tag the page property `Review` to `Yes`.
2. **Morning Generation (8:00 AM):** The system will wake up, synthesize your notes, and place a `Daily_Review.md` file on your Desktop with generated questions.
3. **Study:** Open the Markdown file and type your answers in the designated slots. Save the file.
4. **Evening Grading (8:00 PM):** The system wakes up, grades your answers, updates your SM-2 intervals in Notion, moves the graded file to `Grading_Archive.md`, and automatically pops it open on your screen so you can read the feedback.

---

## 🔧 Troubleshooting & Commands

If you ever need to manually force the system to run off-schedule, use these commands:

**Force Morning Sequence:**
`bash
launchctl start com.adiareview.system.morning
`

**Force Evening Sequence:**
`bash
launchctl start com.adiareview.system.evening
`

**Where are the logs?**
Check the unified timeline to see exactly what the AI and network pollers are doing:
`bash
tail -f logs/system.log
`

If the system completely fails to execute, check the OS-level macOS safety net logs: `logs/launchd_morning_error.log` or `logs/launchd_evening_error.log`.
