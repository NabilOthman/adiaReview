#!/bin/bash

#morning_wrapper.sh

PROJECT_DIR=$(cd "$(dirname "$0")/.." && pwd)
cd "$PROJECT_DIR"

TODAY=$(date +%Y-%m-%d)
LOCK_FILE="$PROJECT_DIR/state/.morning_completed_${TODAY}"
LOG_FILE="$PROJECT_DIR/logs/morning_system.log"

# Function to match Python's exact log format
log_info() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] $1" >> "$LOG_FILE"
}
log_error() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [ERROR] $1" >> "$LOG_FILE"
}

if [ -f "$LOCK_FILE" ]; then
    exit 0
fi

for i in {1..12}; do
    if ping -q -c 1 -W 1 8.8.8.8 >/dev/null; then
        log_info "Network found. Triggering Python morning sequence."
        
        "$PROJECT_DIR/.venv/bin/python" src/activeRecall.py
        "$PROJECT_DIR/.venv/bin/python" src/adiaReview.py
        
        touch "$LOCK_FILE"
        find "$PROJECT_DIR/state" -name ".morning_completed_*" ! -name ".morning_completed_${TODAY}" -delete
        exit 0
    fi
    sleep 5
done

osascript -e 'display notification "No internet. AdiaReview will retry in 1 hour." with title "AdiaReview System"'
log_error "Skipped morning sequence: No internet connection. Awaiting next hour."
exit 1