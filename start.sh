#!/bin/bash

# Check if a username was provided as a command line argument
if [ -z "$1" ]; then
  echo "[error] usage: ./start.sh {username}"
  exit 1
fi

# Get the username from the command line argument
username=$1

# Start a new tmux session with the name "$username-fansly"
tmux new-session -d -s "$username-fansly"

# Switch to the session and run the Python script
tmux send-keys "python3 fansly-recorder.py $username" C-m
