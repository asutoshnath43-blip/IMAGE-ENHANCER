#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
echo "Starting ClearScale 1080p Image Enhancer..."
python3 start.py "$@"
