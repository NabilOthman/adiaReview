#!/bin/bash

#evening_wrapper.sh

PROJECT_DIR=$(cd "$(dirname "$0")/.." && pwd)
cd "$PROJECT_DIR"

TODAY=$(date +%Y-%m-%d)
LOCK_FILE="$PROJECT_DIR/state/.evening_completed_${TODAY}"
LOG_FILE="$PROJECT_DIR/logs/evening_system.log"

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
        log_info "Network found. Triggering Python evening grader."
        
        "$PROJECT_DIR/.venv/bin/python" src/grader.py
        
        touch "$LOCK_FILE"
        find "$PROJECT_DIR/state" -name ".evening_completed_*" ! -name ".evening_completed_${TODAY}" -delete
        exit 0
    fi
    sleep 5
done

osascript -e 'display notification "No internet. Evening grading will retry in 1 hour." with title "AdiaReview System"'
log_error "Skipped evening sequence: No internet connection. Awaiting next hour."
exit 1