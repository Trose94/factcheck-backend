"""
FastAPI application for the Fact Checker & Response Generator backend.
"""
import os
import logging
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from typing import List, Optional
import asyncio
from dotenv import load_dotenv
from datetime import datetime
from fastapi.responses import JSONResponse
import time

from services.openai_service import OpenAIService
from services.fact_checker import FactCheckerService
from services.db_service import DBService
from config import settings

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Fact Checker API",
    description="API for fact-checking and response generation",
    version="1.0.0"
)

# Setup CORS to allow requests from extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API key security
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

# Get API key from environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_FACT_CHECK_MODEL = os.getenv("OPENAI_FACT_CHECK_MODEL", "gpt-o3-mini")
OPENAI_RESPONSE_MODEL = os.getenv("OPENAI_RESPONSE_MODEL", "gpt-4o-mini")

# Valid API keys for the service
API_KEYS = os.getenv("VALID_API_KEYS", "").split(",")

# Request/Response models
class FactCheckRequest(BaseModel):
    text: str

class ResponseGenerationRequest(BaseModel):
    text: str
    tone: str
    factCheckInfo: Optional[str] = ""
    customInstructions: Optional[str] = ""

class Source(BaseModel):
    url: str
    title: str
    snippet: str

class FactCheckResponse(BaseModel):
    factCheckInfo: str
    sources: List[Source]

class ResponseGenerationResponse(BaseModel):
    generatedResponse: str

# Dependency to validate API key
async def get_api_key(api_key: str = Depends(api_key_header)):
    if not API_KEYS or api_key in API_KEYS:
        return api_key
    raise HTTPException(
        status_code=401, 
        detail="Invalid API key"
    )

# Rate limiting
class RateLimiter:
    def __init__(self, max_calls, time_period):
        self.max_calls = max_calls
        self.time_period = time_period
        self.calls = {}
    
    async def check(self, client_id):
        current_time = asyncio.get_event_loop().time()
        
        # Initialize or clean up old entries
        if client_id not in self.calls:
            self.calls[client_id] = []
        else:
            self.calls[client_id] = [
                timestamp for timestamp in self.calls[client_id] 
                if current_time - timestamp <= self.time_period
            ]
        
        # Check if rate limit exceeded
        if len(self.calls[client_id]) >= self.max_calls:
            return False
        
        # Record this call
        self.calls[client_id].append(current_time)
        return True

# Initialize rate limiter (100 calls per hour per API key)
rate_limiter = RateLimiter(max_calls=100, time_period=3600)

# Initialize services
openai_service = OpenAIService(
    api_key=OPENAI_API_KEY,
    fact_check_model=OPENAI_FACT_CHECK_MODEL,
    response_model=OPENAI_RESPONSE_MODEL
)
fact_checker_service = FactCheckerService(openai_service)
db_service = DBService()

# Middleware for API key validation
@app.middleware("http")
async def validate_api_key(request: Request, call_next):
    # Skip API key validation for health check endpoint
    if request.url.path == "/health":
        return await call_next(request)
    
    # Get API key from header
    api_key = request.headers.get(API_KEY_NAME)
    
    # Check if API key is valid
    if not api_key or not db_service.validate_api_key(api_key):
        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid or missing API key"}
        )
    
    # Check rate limit
    is_allowed, current_count = db_service.check_rate_limit(
        api_key, 
        max_requests_per_hour=100
    )
    
    if not is_allowed:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"}
        )
    
    # Add rate limit headers
    response = await call_next(request)
    response.headers["X-Rate-Limit-Limit"] = str(100)
    response.headers["X-Rate-Limit-Remaining"] = str(100 - current_count)
    
    return response

# Middleware for request logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    # Calculate response time
    process_time = int((time.time() - start_time) * 1000)
    
    # Log request to database if it's an API endpoint (not health check)
    if request.url.path != "/health":
        api_key = request.headers.get(API_KEY_NAME)
        if api_key:
            db_service.log_request(
                api_key=api_key,
                endpoint=request.url.path,
                response_time_ms=process_time,
                status_code=response.status_code
            )
    
    # Add processing time header
    response.headers["X-Process-Time"] = str(process_time)
    return response

@app.get("/")
async def root():
    return {"message": "Welcome to the Fact Checker API"}

@app.post("/api/fact-check", response_model=FactCheckResponse)
async def fact_check(request: FactCheckRequest, api_key: str = Depends(get_api_key)):
    try:
        logger.info(f"Fact-checking request received: {request.text[:50]}...")
        
        # Perform fact check using GPT-o3-mini with online search
        fact_check_info, sources = await fact_checker_service.fact_check(request.text)
        
        # Convert sources to the expected format
        formatted_sources = [
            Source(url=source["url"], title=source["title"], snippet=source["snippet"])
            for source in sources
        ]
        
        return FactCheckResponse(
            factCheckInfo=fact_check_info,
            sources=formatted_sources
        )
    except Exception as e:
        logger.error(f"Error in fact-check endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error performing fact check: {str(e)}"
        )

@app.post("/api/generate-response", response_model=ResponseGenerationResponse)
async def generate_response(request: ResponseGenerationRequest, api_key: str = Depends(get_api_key)):
    try:
        logger.info(f"Response generation request received: {request.text[:50]}...")
        
        # Generate response
        response = await fact_checker_service.generate_response(
            text=request.text,
            tone=request.tone,
            fact_check_info=request.factCheckInfo,
            custom_instructions=request.customInstructions
        )
        
        return ResponseGenerationResponse(generatedResponse=response)
    except Exception as e:
        logger.error(f"Error in generate-response endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating response: {str(e)}"
        )

# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint for monitoring the API status.
    Returns basic information about the API and its dependencies.
    """
    return {
        "status": "ok",
        "api": f"{app.title} v{app.version}",
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)