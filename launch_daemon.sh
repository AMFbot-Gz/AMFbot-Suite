#!/bin/bash
# Lance Jarvis en daemon avec stdin maintenu ouvert
cd "$(dirname "$0")"
export GUI_ENABLED=false
tail -f /dev/null | venv/bin/python jarvis_main.py >> /tmp/jarvis_daemon.log 2>&1
