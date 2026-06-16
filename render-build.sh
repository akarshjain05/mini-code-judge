#!/usr/bin/env bash
# Render build script for the worker service.
# Installs g++ (not present in Render's default Python image) and Python deps.

apt-get update && apt-get install -y g++

pip install -r requirements.txt