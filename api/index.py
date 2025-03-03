"""
Simplified FastAPI app for Vercel deployment.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
from dotenv import load_dotenv
import openai

# Load environment variables
load_dotenv()

# Initialize OpenAI client
openai.api_key = os.getenv("OPENAI_API_KEY")

# Initialize FastAPI app
app = FastAPI()

# Setup CORS to allow requests from anywhere
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class FactCheckRequest(BaseModel):
    text: str

class Source(BaseModel):
    url: str = ""
    title: str = ""
    snippet: str = ""

class FactCheckResponse(BaseModel):
    factCheckInfo: str
    sources: List[Source]

class ResponseGenerationRequest(BaseModel):
    text: str
    tone: str = "neutral"
    customInstructions: str = ""
    stance: str = "neutral"
    character_limit: int = 1000

class ResponseGenerationResponse(BaseModel):
    response: str

@app.get("/")
async def root():
    return {"message": "Fact Checker API is running"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/api/fact-check", response_model=FactCheckResponse)
async def fact_check(request: FactCheckRequest):
    try:
        # Call OpenAI for fact checking
        response = openai.chat.completions.create(
            model=os.getenv("OPENAI_FACT_CHECK_MODEL", "o3-mini"),
            messages=[
                {
                    "role": "system",
                    "content": """You are a fact-checking assistant. Your task is to analyze the provided text, 
                    identify factual claims, and verify their accuracy using your knowledge. 
                    Provide an analysis of the factual accuracy, assign an accuracy score between 0 and 1, 
                    and list any corrections needed."""
                },
                {
                    "role": "user",
                    "content": request.text
                }
            ],
            temperature=0.3
        )
        
        analysis = response.choices[0].message.content
        
        # Return the response
        return {
            "factCheckInfo": analysis,
            "sources": [
                {"url": "", "title": "AI Analysis", "snippet": "Based on AI knowledge"}
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate-response", response_model=ResponseGenerationResponse)
async def generate_response(request: ResponseGenerationRequest):
    try:
        # Call OpenAI for response generation
        response = openai.chat.completions.create(
            model=os.getenv("OPENAI_RESPONSE_MODEL", "gpt-4o-mini"),
            messages=[
                {
                    "role": "system",
                    "content": f"""You are a helpful assistant generating responses to social media posts.
                    Your response must be EXACTLY within {request.character_limit} characters, no more and no less.
                    Stance: {request.stance.upper()}
                    Tone: {request.tone.upper()}
                    {request.customInstructions}"""
                },
                {
                    "role": "user",
                    "content": request.text
                }
            ],
            temperature=0.7,
            max_tokens=request.character_limit * 2
        )
        
        generated_response = response.choices[0].message.content
        
        # Return the response
        return {
            "response": generated_response
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 