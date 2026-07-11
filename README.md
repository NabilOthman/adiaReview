AdiaReview: Spaced-Repetition via Notion & Claude
AdiaReview is a localized, automated spaced-repetition tutor built for macOS.
Instead of manually creating flashcards, you write standard engineering notes in Notion. The system automatically parses your notes, extracts core concepts, and drops daily active-recall questions onto your Desktop. In the evening, it parses your answers, grades them using Claude 4.5 Haiku, updates your SuperMemo-2 (SM-2) intervals, and syncs everything back to your Notion tracker database.
Features
Automated Scheduling: Runs in the background using native macOS launchd jobs—no manual execution required.
Network Fault Tolerance: Uses bash wrappers to poll for connectivity. If you open your laptop without Wi-Fi, it caches state locally and retries hourly until an API connection can be established.
Semantic Grading: Powered by Anthropic's Claude 4.5 Haiku to evaluate conceptual understanding rather than simple keyword matching, returning concise structural feedback.
Unified Logging: Merges both OS-level network polling and Python API execution steps into a single chronological system.log.
Planned Updates
Multi-LLM support (local models / OpenAI)
Cross-platform support (Linux/Windows)
Prerequisites
macOS
Python 3.9+
A Notion API Integration Token
An Anthropic API Key
Notion Setup
AdiaReview relies on two specific database tables in your Notion workspace.
1. Generate an API Key
Go to Notion Integrations.
Create a new internal integration, name it AdiaReview, and select your workspace.
Save the integration and copy the Internal Integration Secret. This is your NOTION_TOKEN.
2. Configure the Source Database (Your Notes)
Create a full-page Table database where you intend to take your notes. Ensure it contains these exact, case-sensitive properties:
Name (Title): The title of your note.
Review (Select): Must contain options: Yes, No, and Done.
Concepts (Multi-select): Leave blank; the AI populates this automatically.
Priority (Select): Options: High, Standard, and Low.
3. Configure the Tracker Database (The SM-2 Engine)
Create a second full-page Table database to manage your spaced-repetition scheduling. It requires these exact properties:
Concept (Title)
Knowledge Profile (Text)
Priority (Select)
Repetitions (Number)
Ease Factor (Number)
Interval (Number)
Next Review (Date)
Last Score (Number)
4. Share Databases with the Integration
By default, integrations cannot see your databases. You must share them manually:
Open your Source Database in Notion.
Click the ... menu in the top right.
Select Add connections and choose AdiaReview.
Repeat this step for your Tracker Database.
5. Extract Database IDs
Open Notion in a web browser and navigate to your Source Database. The URL will follow this pattern:
[https://www.notion.so/workspace/YOUR_DATABASE_ID?v=](https://www.notion.so/workspace/YOUR_DATABASE_ID?v=)...
Copy the 32-character string between the last slash and the question mark. This is your SOURCE_DB_ID. Do the same for the Tracker Database to get your TRACKER_DB_ID.
Installation & Deployment
1. Clone the Repository
Bash
git clone https://github.com/YOUR_GITHUB_USERNAME/adiaReview.git
cd adiaReview
2. Set Up the Virtual Environment
Bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
3. Configure Environment Variables
Create a .env file in the project root:
Bash
nano .env
Add your keys and database IDs:
Code snippet
NOTION_TOKEN=secret_your_notion_integration_token
CLAUDE_API_KEY=sk-ant-your_claude_api_key
SOURCE_DB_ID=your_notion_notes_database_id
TRACKER_DB_ID=your_notion_spaced_repetition_database_id
4. System Configuration
Create a config.txt file to set your macOS bundle identifier:
Bash
echo "BUNDLE_ID=com.adiareview.system" > config.txt
5. Load the Background Jobs
Run the deployment script to substitute your local paths into the .plist templates, update permissions, and load them into launchd:
Bash
chmod +x automation/*.sh
./automation/deploy_jobs.sh
6. Grant Full Disk Access
Because launchd executes scripts in the background, macOS Transparency, Consent, and Control (TCC) restrictions will block it from writing files directly to your Desktop or Documents folders unless permissions are explicitly granted.
Open System Settings > Privacy & Security > Full Disk Access.
Click the + icon at the bottom of the application list.
Use Cmd + Shift + G to open the path finder.
Add /bin/sh and click Open.
Repeat the process to add /bin/bash.
Ensure the toggles next to both sh and bash are switched ON.
How It Works (Daily Cycle)
Write: Take notes in your Notion Source Database and change the Review status to Yes.
Morning Script (8:00 AM): The system parses your flagged notes, generates questions, and creates a Daily_Review.md file on your Desktop.
Review: Open the markdown file, type your answers directly underneath the questions, and save the file.
Evening Script (8:00 PM): The system reads your answers, runs them through Claude for grading, calculates new SM-2 intervals, updates Notion, and archives the review session into Grading_Archive.md before launching it so you can review feedback.
Maintenance & Diagnostics
If you need to manually trigger the workflows outside of their scheduled times:
Run Morning Generation Manually:
Bash
launchctl start com.adiareview.system.morning
Run Evening Grading Manually:
Bash
launchctl start com.adiareview.system.evening
View Runtime Logs:
To monitor real-time execution, API requests, and network status:
Bash
tail -f logs/system.log
If a background job fails silently or does not execute, check the OS-level standard error logs located at logs/launchd_morning_error.log and logs/launchd_evening_error.log.
