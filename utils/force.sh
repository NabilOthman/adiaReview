#!/bin/bash

# Check if equal
if [[ "$1" == "morning" || "$1" == "evening" ]]; then
    echo "Forcing $1 script"
    launchctl start com.adiareview.system.$1
else
   echo "Usage: ./force.sh <morning/evening>"
fi




