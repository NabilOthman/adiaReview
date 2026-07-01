#!/bin/bash

#deploy_jobs.sh

# Get absolute path to the project root
PROJECT_DIR=$(cd "$(dirname "$0")/.." && pwd)
PLIST_DIR="$HOME/Library/LaunchAgents"

# Read config file
source "$PROJECT_DIR/config.txt"

echo "Deploying AdiaReview automation jobs..."

for job in morning evening; do
    TEMPLATE="$PROJECT_DIR/automation/${job}.plist.template"
    PLIST_FILE="$PLIST_DIR/${BUNDLE_ID}.${job}.plist"
    
    # Unload existing job if it exists
    if [ -f "$PLIST_FILE" ]; then
        launchctl unload "$PLIST_FILE" 2>/dev/null
    fi
    
    # Inject variables and create the new plist
    sed -e "s|{{PROJECT_DIR}}|$PROJECT_DIR|g" \
        -e "s|{{BUNDLE_ID}}|$BUNDLE_ID|g" \
        "$TEMPLATE" > "$PLIST_FILE"
        
    # Load into macOS scheduler
    launchctl load "$PLIST_FILE"
    echo " -> Loaded: $job schedule"
done

echo "Deployment complete! Logs will route to $PROJECT_DIR/logs/"
