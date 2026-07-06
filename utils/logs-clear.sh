#!/bin/bash

# script to empty log files
cd logs || (echo "Error: run this script from project root." && exit 1)

current_dir="${PWD##*/}"

# Check if the current directory is NOT "logs"
if [ "$current_dir" != "logs" ]; then
    echo "Error: This script must be executed from a 'logs' directory."
    echo "You are currently in: $PWD"
    exit 1
fi


for log_file in *log; do
    > "$log_file"
done

echo "logs cleared."

