#!/bin/bash
# Install dependencies with specific flags to avoid build issues
pip install --upgrade pip
pip install -r requirements.txt --no-build-isolation
echo "Build completed" 