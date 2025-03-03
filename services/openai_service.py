"""
OpenAI Service for handling interactions with OpenAI models.
"""
import os
import logging
from typing import Dict, Any, Optional, List, Tuple
import httpx
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OpenAIService:
    """
    Service for interacting with OpenAI API to generate responses and perform fact-checking.
    """
    
    def __init__(self, api_key: str, fact_check_model: str = "gpt-o3-mini", response_model: str = "gpt-4o-mini"):
        """
        Initialize the OpenAI service with API key and model configurations.
        
        Args:
            api_key: OpenAI API key
            fact_check_model: Model to use for fact checking (should be gpt-o3-mini for online search)
            response_model: Model to use for response generation
        """
        self.api_key = api_key
        self.fact_check_model = fact_check_model
        self.response_model = response_model
        self.base_url = "https://api.openai.com/v1/chat/completions"
        self.logger = logging.getLogger(__name__)
        
        # Validate API key
        if not api_key:
            self.logger.error("OpenAI API key is missing")
            raise ValueError("OpenAI API key is required")
    
    async def generate_completion(self, 
                                 messages: List[Dict[str, str]], 
                                 model: Optional[str] = None,
                                 temperature: float = 0.7,
                                 max_tokens: int = 1000,
                                 tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Generate a completion using the OpenAI API.
        
        Args:
            messages: List of message objects with role and content
            model: Model to use (defaults to self.response_model)
            temperature: Temperature for response generation
            max_tokens: Maximum tokens to generate
            tools: Optional list of tools to use (for models that support tools)
            
        Returns:
            Dictionary containing the API response
        """
        if not model:
            model = self.response_model
            
        self.logger.info(f"Generating completion with model: {model}")
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        # Add tools if provided
        if tools:
            payload["tools"] = tools
            
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.base_url,
                    headers=headers,
                    json=payload,
                    timeout=60.0  # Longer timeout for AI processing
                )
                
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPStatusError as e:
            self.logger.error(f"HTTP error occurred: {e}")
            raise Exception(f"OpenAI API error: {e.response.text}")
        except httpx.RequestError as e:
            self.logger.error(f"Request error occurred: {e}")
            raise Exception(f"Error communicating with OpenAI API: {str(e)}")
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            raise Exception(f"Unexpected error when calling OpenAI API: {str(e)}")
    
    async def fact_check_with_online_search(self, text: str) -> Tuple[str, List[Dict[str, str]]]:
        """
        Perform a fact check on the provided text using GPT-o3-mini's online search capabilities.
        
        Args:
            text: The text to fact check
            
        Returns:
            Tuple containing the fact-check result and the sources used
        """
        self.logger.info(f"Fact-checking with online search: {text[:50]}...")
        
        # Define the web browsing tool
        tools = [
            {
                "type": "web_search",
                "config": {
                    "provider": "bing"
                }
            }
        ]
        
        messages = [
            {"role": "system", "content": """You are a fact-checking assistant with access to online search.
            Your task is to verify the accuracy of the claim provided by the user.
            
            Follow these steps:
            1. Search for relevant information online to verify the claim
            2. Analyze the search results to determine if the claim is true, false, partially true, or if there's not enough information
            3. Provide a detailed explanation of your reasoning and cite specific sources
            4. Format your response in two parts:
               - A detailed fact-check analysis with your assessment and explanation
               - A list of sources you used, including titles, URLs, and brief descriptions
            
            Be thorough, objective, and focus on verifiable facts."""},
            {"role": "user", "content": f"Please fact-check this claim: {text}"}
        ]
        
        try:
            response = await self.generate_completion(
                messages=messages,
                model=self.fact_check_model,
                temperature=0.2,  # Lower temperature for more consistent fact checking
                tools=tools
            )
            
            # Extract the response content
            content = response["choices"][0]["message"]["content"]
            
            # Extract sources from the tool calls if available
            sources = []
            if "tool_calls" in response["choices"][0]["message"]:
                for tool_call in response["choices"][0]["message"]["tool_calls"]:
                    if tool_call["type"] == "web_search":
                        search_results = json.loads(tool_call["search_results"])
                        for result in search_results:
                            sources.append({
                                "title": result.get("title", "Unknown Source"),
                                "url": result.get("url", ""),
                                "snippet": result.get("snippet", "")
                            })
            
            return content, sources
                
        except Exception as e:
            self.logger.error(f"Error during fact check with online search: {e}")
            raise Exception(f"Failed to perform fact check: {str(e)}")
    
    async def analyze_fact_check(self, claim: str, search_results: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Analyze a claim against search results to determine its accuracy.
        
        Args:
            claim: The claim to fact check
            search_results: List of search results to use for fact checking
            
        Returns:
            Dictionary with fact check results including accuracy assessment and explanation
        """
        self.logger.info(f"Analyzing fact check for claim: {claim[:50]}...")
        
        # Prepare search results for the prompt
        search_context = ""
        for i, result in enumerate(search_results[:5]):  # Limit to top 5 results
            search_context += f"\nSource {i+1}: {result['title']}\nURL: {result['url']}\n{result['snippet']}\n"
        
        messages = [
            {"role": "system", "content": """You are a fact-checking assistant. Analyze the claim against the provided search results.
            Determine if the claim is true, false, partially true, or if there's not enough information.
            Provide a detailed explanation of your reasoning and cite specific sources from the search results.
            Format your response as a JSON object with the following structure:
            {
                "assessment": "true|false|partially_true|insufficient_info",
                "confidence": 0-100,
                "explanation": "detailed explanation with source citations",
                "relevant_sources": [list of source numbers that were most relevant]
            }"""},
            {"role": "user", "content": f"Claim to fact check: {claim}\n\nSearch Results:\n{search_context}"}
        ]
        
        try:
            response = await self.generate_completion(
                messages=messages,
                model=self.fact_check_model,
                temperature=0.2  # Lower temperature for more consistent fact checking
            )
            
            # Extract and parse the response content
            content = response["choices"][0]["message"]["content"]
            
            # Try to parse the JSON response
            try:
                result = json.loads(content)
                return result
            except json.JSONDecodeError:
                # If JSON parsing fails, try to extract structured data from the text
                self.logger.warning("Failed to parse JSON response, attempting to extract structured data")
                
                # Create a basic structure with the full response
                return {
                    "assessment": "insufficient_info",
                    "confidence": 50,
                    "explanation": content,
                    "relevant_sources": []
                }
                
        except Exception as e:
            self.logger.error(f"Error during fact check analysis: {e}")
            raise Exception(f"Failed to analyze fact check: {str(e)}")
    
    async def generate_response(self, 
                               original_text: str, 
                               fact_check_result: Dict[str, Any],
                               tone: str = "neutral",
                               custom_instructions: str = "") -> str:
        """
        Generate a response to the original text based on fact check results.
        
        Args:
            original_text: The original text being responded to
            fact_check_result: Results from the fact check analysis
            tone: Desired tone for the response (neutral, friendly, professional, etc.)
            custom_instructions: Any custom instructions for response generation
            
        Returns:
            Generated response text
        """
        self.logger.info(f"Generating response with tone: {tone}")
        
        # Map tones to specific instructions
        tone_instructions = {
            "neutral": "Respond in a balanced, objective manner.",
            "friendly": "Respond in a warm, conversational, and approachable manner.",
            "professional": "Respond in a formal, authoritative, and respectful manner.",
            "educational": "Respond in an informative, teaching-oriented manner that explains concepts clearly.",
            "diplomatic": "Respond in a tactful manner that acknowledges different perspectives."
        }
        
        tone_instruction = tone_instructions.get(tone.lower(), tone_instructions["neutral"])
        
        # Prepare the assessment information
        assessment = fact_check_result.get("assessment", "insufficient_info")
        explanation = fact_check_result.get("explanation", "")
        confidence = fact_check_result.get("confidence", 50)
        
        messages = [
            {"role": "system", "content": f"""You are a helpful assistant that generates responses to potentially misleading social media posts.
            {tone_instruction}
            
            When generating your response:
            1. Be respectful and constructive, even when correcting misinformation
            2. Include relevant facts from the fact-check results
            3. Cite sources when appropriate
            4. Keep your response concise and focused
            
            {custom_instructions}"""},
            {"role": "user", "content": f"""Original text: "{original_text}"
            
            Fact check results:
            - Assessment: {assessment}
            - Confidence: {confidence}%
            - Explanation: {explanation}
            
            Please generate a response to this text based on the fact check results and following the tone and style instructions."""}
        ]
        
        try:
            response = await self.generate_completion(
                messages=messages,
                model=self.response_model,
                temperature=0.7  # Higher temperature for more creative responses
            )
            
            # Extract the response content
            content = response["choices"][0]["message"]["content"]
            return content
                
        except Exception as e:
            self.logger.error(f"Error during response generation: {e}")
            raise Exception(f"Failed to generate response: {str(e)}")
