#!/bin/bash

# script to empty grading archive file
current_dir="${PWD##*/}"

# Check if the current directory is NOT "logs"
if [ "$current_dir" != "adiaReview" ]; then # assumes no git worktrees
    echo "Error: This script must be executed from project root"
    echo "You are currently in: $PWD"
    exit 1
fi


> Grading_Archive.md
echo "grading archive clear cleared."

