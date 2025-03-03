"""
Entry point for Vercel serverless functions.
This file is required for Vercel Python deployment.
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import sys
import os

# Add parent directory to path so we can import from app.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the FastAPI app from the main app.py file
from app import app

# This is required for Vercel serverless deployment 