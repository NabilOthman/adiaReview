# AdiaReview: Autonomous AI Spaced-Repetition System

AdiaReview is a fully automated, offline-resilient, AI-driven spaced-repetition tutor built natively for macOS. 

Instead of manually writing flashcards, you simply take notes in Notion. Every morning, this system synthesizes your notes into core engineering concepts and generates rigorous active-recall questions right on your Desktop. Every evening, it grades your answers using Claude 4.5 Haiku, calculates your SuperMemo-2 (SM-2) memory intervals, and updates your Notion tracker automatically.

## ✨ Features
* **Zero-Click Scheduling:** Runs invisibly in the background using native macOS `launchd` automation.
* **Offline Resilient:** Smart bash wrappers poll for network connectivity. If you open your laptop in the car without Wi-Fi, it safely caches the state and retries every hour until you connect.
* **Rigorous AI Grading:** Powered by Anthropic's Claude 4.5 Haiku. It doesn't just check for keywords; it grades for structural engineering accuracy and provides 1-sentence mechanical feedback.
* **Unified Logging:** A single chronologically unified `system.log` tracks both OS-level network polling and Python-level API execution.

---
## Features In Development (soon)
* **Multi-LLM support**
* **More detailed feedback reports**



---

## 🛠 Prerequisites
* A Mac running macOS.
* Python 3.9+ installed.
* A [Notion API Integration Token](https://www.notion.so/my-integrations).
* An [Anthropic API Key](https://console.anthropic.com/).

---

## 🗄️ Notion Setup Guide

Because AdiaReview uses Notion as its database, you need to set up two specific tables and an API key. 

### Part 1: Get Your API Key
1. Go to [Notion Integrations](https://www.notion.so/my-integrations).
2. Click **New integration**.
3. Name it "AdiaReview" and select your workspace.
4. Click **Submit**, then copy the **Internal Integration Secret**. This is your `NOTION_TOKEN`.

### Part 2: Build the Source Database (Your Notes)
Create a new full-page Table in Notion. This is where you will take your class/engineering notes. You must add these exact properties (case-sensitive):
* **Name** *(Title property)*: The title of your note.
* **Review** *(Select property)*: Add three options: `Yes`, `No`, and `Done`.
* **Concepts** *(Multi-select property)*: Leave this empty. The AI will populate it.
* **Priority** *(Select property)*: Add three options: `High`, `Standard`, and `Low`.

### Part 3: Build the Tracker Database (The SM-2 Engine)
Create a second full-page Table. This is where the AI stores the spaced-repetition data. You must add these exact properties (case-sensitive):
* **Concept** *(Title property)*
* **Knowledge Profile** *(Text property)*
* **Priority** *(Select property)*
* **Repetitions** *(Number property)*
* **Ease Factor** *(Number property)*
* **Interval** *(Number property)*
* **Next Review** *(Date property)*
* **Last Score** *(Number property)*

### Part 4: Connect the Brain
By default, your API key cannot see your databases. You must explicitly invite the integration to both tables:
1. Open your Source Database in Notion.
2. Click the **`...`** menu in the top right corner.
3. Click **Add connections** and search for "AdiaReview" (or whatever you named your integration in Part 1). 
4. Repeat this exact process for your Tracker Database.

### Part 5: Get Your Database IDs
Open Notion in your web browser (not the desktop app). Navigate to your Source Database. Look at the URL:
`https://www.notion.so/workspace/YOUR_DATABASE_ID?v=...`
Copy the 32-character string between the last `/` and the `?`. This is your `SOURCE_DB_ID`. Do the same for your Tracker Database to get your `TRACKER_DB_ID`.

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

### 6. Grant macOS Permissions (Crucial)
Apple's security system (TCC) prevents background scripts from modifying files in your `Desktop` or `Documents` folders. Since `launchd` runs in the background, you must explicitly give it permission to create your Daily Review file.

1. Open **System Settings** on your Mac.
2. Navigate to **Privacy & Security** > **Full Disk Access**.
3. Click the **`+`** button at the bottom of the list (authenticate if needed).
4. Press **`Cmd + Shift + G`** to open the path search bar.
5. Type `/bin/sh` and hit Enter, then click **Open**.
6. Repeat steps 3-5, but type `/bin/bash` this time.
7. Verify that the toggles next to `sh` and `bash` are turned **ON**.


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
