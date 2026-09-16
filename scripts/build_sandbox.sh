#!/bin/bash
set -e

echo "Building mini-code-judge-sandbox image..."
docker build -t mini-code-judge-sandbox:latest -f Dockerfile.sandbox .

echo "Done! The sandbox image is ready to be used by the worker."
