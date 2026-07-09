#!/usr/bin/env bash

# Install compilers for the local fallback path (if Docker is unavailable)
# Render's native environments typically allow apt-get install
if command -v apt-get &> /dev/null; then
    # We use || true so that if it requires root or fails, it doesn't break the build
    apt-get update && apt-get install -y gcc g++ default-jdk || echo "Note: apt-get failed, skipping system package installation."
fi

# Install Python dependencies
pip install -r requirements.txt
