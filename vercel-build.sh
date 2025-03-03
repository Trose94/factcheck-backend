#!/bin/bash
# Install dependencies with specific flags to avoid build issues
pip install --upgrade pip
pip install wheel setuptools
pip install -r requirements.txt
echo "Build completed" 