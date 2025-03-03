"""
Search Service for retrieving information from the web.
"""
import os
import logging
from typing import Dict, Any, List, Optional
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SearchService:
    """Service for performing web searches."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the search service.
        
        Args:
            api_key: Search API key. If not provided, will try to get from environment.
        """
        self.api_key = api_key or os.getenv("SEARCH_API_KEY")
        if not self.api_key:
            logger.warning("No search API key provided")
        
        # Using Bing Search API
        self.search_url = "https://api.bing.microsoft.com/v7.0/search"
    
    async def search(self, query: str, count: int = 5) -> List[Dict[str, Any]]:
        """
        Perform a web search for the given query.
        
        Args:
            query: The search query
            count: Number of results to return
            
        Returns:
            List of search results
        """
        if not self.api_key:
            raise ValueError("Search API key is required")
        
        try:
            headers = {"Ocp-Apim-Subscription-Key": self.api_key}
            params = {
                "q": query,
                "count": count,
                "responseFilter": "Webpages",
                "textDecorations": "true",
                "textFormat": "HTML"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.search_url,
                    headers=headers,
                    params=params,
                    timeout=10.0
                )
                
                response.raise_for_status()
                search_results = response.json()
                
                # Extract and format results
                results = []
                if "webPages" in search_results and "value" in search_results["webPages"]:
                    for result in search_results["webPages"]["value"]:
                        results.append({
                            "title": result.get("name", ""),
                            "url": result.get("url", ""),
                            "snippet": result.get("snippet", "")
                        })
                
                return results
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e}")
            raise ValueError(f"Search API error: {e.response.text}")
        
        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            raise ValueError(f"Request error: {str(e)}")
        
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise ValueError(f"Unexpected error: {str(e)}")
    
    async def search_for_fact_check(self, text: str) -> List[Dict[str, Any]]:
        """
        Perform a search specifically for fact-checking the given text.
        
        Args:
            text: The text to fact-check
            
        Returns:
            List of search results relevant for fact-checking
        """
        # Create a search query that's optimized for fact-checking
        # Extract key claims or entities from the text
        search_query = f"fact check {text}"
        
        # Limit query length
        if len(search_query) > 150:
            search_query = search_query[:150]
        
        return await self.search(search_query, count=5)
