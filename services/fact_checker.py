"""
Fact Checker Service for verifying information.
"""
import logging
from typing import Dict, Any, List, Optional, Tuple

from .openai_service import OpenAIService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FactCheckerService:
    """Service for fact-checking text using AI with online search capabilities."""
    
    def __init__(self, openai_service: OpenAIService):
        """
        Initialize the fact checker service.
        
        Args:
            openai_service: Service for interacting with OpenAI models
        """
        self.openai_service = openai_service
    
    async def fact_check(self, text: str) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Perform a fact check on the provided text using GPT-o3-mini with online search.
        
        Args:
            text: The text to fact-check
            
        Returns:
            Tuple containing the fact-check result and the sources used
        """
        try:
            # Use GPT-o3-mini with online search to fact-check the text
            logger.info(f"Fact-checking with online search: {text[:100]}...")
            fact_check_result, sources = await self.openai_service.fact_check_with_online_search(text)
            
            if not sources:
                logger.warning("No sources found during fact-checking")
            
            return fact_check_result, sources
            
        except Exception as e:
            logger.error(f"Fact-checking error: {e}")
            raise ValueError(f"Fact-checking error: {str(e)}")
    
    async def generate_response(
        self, 
        text: str, 
        tone: str = "neutral", 
        fact_check_info: str = "", 
        custom_instructions: str = ""
    ) -> str:
        """
        Generate a response to the provided text.
        
        Args:
            text: The text to respond to
            tone: The tone to use in the response
            fact_check_info: Optional fact-check information to include
            custom_instructions: Optional custom instructions for the response
            
        Returns:
            The generated response
        """
        try:
            # Map tone to instructions
            tone_instructions = {
                "neutral": "Maintain a neutral and balanced tone.",
                "kind": "Be kind, informative, and helpful in your response.",
                "assertive": "Be assertive and direct in addressing misinformation.",
                "professional": "Maintain a professional and formal tone."
            }
            
            selected_tone = tone_instructions.get(tone, tone_instructions["neutral"])
            
            # Build prompt
            prompt = f"""
            Using a {tone} tone, create a response to the following text:
            
            "{text}"
            """
            
            # Add fact check info if provided
            if fact_check_info:
                prompt += f"""
                
                Include this fact-check information in your response:
                {fact_check_info}
                """
            
            # Add custom instructions if provided
            if custom_instructions:
                prompt += f"""
                
                Also follow these additional instructions:
                {custom_instructions}
                """
            
            # Generate response using GPT-4o-mini for quick response
            logger.info(f"Generating response with tone: {tone}")
            
            # Create messages for the API call
            messages = [
                {"role": "system", "content": f"You are a helpful assistant that combats misinformation with factual information. {selected_tone}"},
                {"role": "user", "content": prompt}
            ]
            
            # Call the OpenAI API
            response = await self.openai_service.generate_completion(
                messages=messages,
                model=self.openai_service.response_model,
                temperature=0.7,
                max_tokens=500
            )
            
            return response["choices"][0]["message"]["content"]
            
        except Exception as e:
            logger.error(f"Response generation error: {e}")
            raise ValueError(f"Response generation error: {str(e)}")
