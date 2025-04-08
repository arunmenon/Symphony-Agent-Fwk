"""Search tools for Taxonomy Planner."""

import os
import json
import logging
import time
import random
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import TaxonomyConfig

# Import search tracing plugin if available
try:
    from search_tracing_plugin import SearchTracingPlugin, get_traced_search_function
    # Create tracing plugin instance
    search_tracer = SearchTracingPlugin()
    TRACING_ENABLED = True
except ImportError:
    TRACING_ENABLED = False

# Configure detailed logging for search operations
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("search_calls.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class SearchRateLimiter:
    """Rate limiter for search requests."""
    
    def __init__(self, max_requests_per_minute: int = 60):
        """Initialize rate limiter.
        
        Args:
            max_requests_per_minute: Maximum requests per minute
        """
        self.max_requests_per_minute = max_requests_per_minute
        self.request_times = []
    
    def wait_if_needed(self):
        """Wait if rate limit would be exceeded."""
        now = time.time()
        
        # Remove requests older than 1 minute
        self.request_times = [t for t in self.request_times 
                              if now - t < 60]
        
        # Check if we've hit the limit
        if len(self.request_times) >= self.max_requests_per_minute:
            # Calculate how long to wait
            oldest = min(self.request_times)
            wait_time = 60 - (now - oldest) + 0.1  # Add small buffer
            
            # Wait
            if wait_time > 0:
                time.sleep(wait_time)
        
        # Add current request
        self.request_times.append(time.time())

# Create rate limiter
RATE_LIMITER = SearchRateLimiter(max_requests_per_minute=50)

def serapi_search(query: str, config: TaxonomyConfig, num_results: int = 5) -> Dict[str, Any]:
    """Perform search using SerAPI.
    
    Args:
        query: Search query
        config: Taxonomy configuration
        num_results: Number of results to return
        
    Returns:
        Search results
    """
    # Log search attempt with detailed information
    search_id = f"search_{int(time.time())}"
    logger.info(f"SEARCH_CALL_START - ID: {search_id} - Query: '{query}' - Num results: {num_results}")
    
    # Record search call details to track usage
    with open("search_calls_record.jsonl", "a") as f:
        f.write(json.dumps({
            "id": search_id,
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "num_results": num_results,
            "type": "search_call_start"
        }) + "\n")
    
    # Apply rate limiting
    RATE_LIMITER.wait_if_needed()
    
    # Use tracing plugin if available
    if TRACING_ENABLED:
        search_tracer.log_search_request(query, num_results, search_id)
    
    api_key = config.search_config.get("api_key")
    if not api_key:
        logger.warning(f"SEARCH_CALL_ERROR - ID: {search_id} - SerAPI API key not found. Using mock data.")
        
        with open("search_calls_record.jsonl", "a") as f:
            f.write(json.dumps({
                "id": search_id,
                "timestamp": datetime.now().isoformat(),
                "error": "API key not found",
                "type": "search_call_error"
            }) + "\n")
            
        return _mock_search_results(query)
    
    base_url = "https://serpapi.com/search"
    params = {
        "q": query,
        "num": num_results,
        "api_key": api_key,
        "engine": "google"
    }
    
    try:
        start_time = time.time()
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        result = response.json()
        duration = time.time() - start_time
        
        # Log successful search
        results_count = len(result.get("organic_results", []))
        logger.info(f"SEARCH_CALL_SUCCESS - ID: {search_id} - Duration: {duration:.2f}s - Results: {results_count}")
        
        # Record successful search call
        with open("search_calls_record.jsonl", "a") as f:
            f.write(json.dumps({
                "id": search_id,
                "timestamp": datetime.now().isoformat(),
                "duration": duration,
                "results_count": results_count,
                "type": "search_call_success"
            }) + "\n")
        
        # Use tracing plugin if available
        if TRACING_ENABLED:
            search_tracer.log_search_response(
                search_id=search_id,
                duration=duration,
                results_count=results_count,
                success=True
            )
        
        # Save sample of search results for compliance domains
        if any(term in query.lower() for term in ["alcohol", "weapon", "nudity", "pharmaceutical", "drug", "compliance", "regulation"]):
            clean_name = query.replace(" ", "_").replace("'", "").replace('"', "")[:50]
            results_file = f"search_result_{clean_name}.json"
            with open(results_file, "w") as f:
                json.dump(result, f, indent=2)
            logger.info(f"SEARCH_CALL_SAVED - ID: {search_id} - File: {results_file}")
            
        return result
        
    except Exception as e:
        logger.error(f"SEARCH_CALL_ERROR - ID: {search_id} - SerAPI search error: {e}")
        
        # Record error
        with open("search_calls_record.jsonl", "a") as f:
            f.write(json.dumps({
                "id": search_id,
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "type": "search_call_error"
            }) + "\n")
            
        # Use tracing plugin if available
        if TRACING_ENABLED:
            search_tracer.log_search_response(
                search_id=search_id,
                duration=time.time() - start_time,
                results_count=0,
                success=False,
                error=str(e)
            )
            
        return _mock_search_results(query)

def search_category_info(category: str, domain: str = "", config: TaxonomyConfig = None) -> Dict[str, Any]:
    """Search for information about a specific category.
    
    Args:
        category: Category name
        domain: Optional domain context
        config: Taxonomy configuration
        
    Returns:
        Category information from search
    """
    if not config or not config.search_config.get("enable_search", True):
        return {"category": category, "results": []}
    
    query = f"{category} {domain} classification"
    results = serapi_search(query, config)
    
    return {
        "category": category,
        "query": query,
        "results": results.get("organic_results", []),
        "knowledge_panel": results.get("knowledge_graph", {}),
        "related_searches": results.get("related_searches", [])
    }

def search_subcategories(category: str, config: TaxonomyConfig = None) -> List[str]:
    """Search for subcategories of a category.
    
    Args:
        category: Parent category
        config: Taxonomy configuration
        
    Returns:
        List of potential subcategories
    """
    if not config or not config.search_config.get("enable_search", True):
        return []
    
    query = f"{category} types OR subcategories OR classification"
    results = serapi_search(query, config)
    
    # Extract potential subcategories from search results
    subcategories = _extract_subcategories(results, category)
    
    # Limit number of subcategories if configured
    max_subcategories = config.search_config.get("max_subcategories_per_search", 10)
    if len(subcategories) > max_subcategories:
        subcategories = subcategories[:max_subcategories]
    
    return subcategories

def search_compliance_requirements(category: str, jurisdiction: str = "", config: TaxonomyConfig = None) -> List[str]:
    """Search for compliance requirements for a category.
    
    Args:
        category: Category name
        jurisdiction: Optional jurisdiction context
        config: Taxonomy configuration
        
    Returns:
        List of compliance requirements from search
    """
    if not config or not config.search_config.get("enable_search", True):
        return []
    
    query = f"{category} {jurisdiction} regulations OR compliance OR requirements"
    results = serapi_search(query, config)
    
    # Extract compliance requirements from search results
    requirements = _extract_compliance_info(results)
    return requirements

def search_legal_requirements(category: str, jurisdiction: str, config: TaxonomyConfig = None) -> List[Dict[str, str]]:
    """Search for laws applicable to a category in a jurisdiction.
    
    Args:
        category: Category name
        jurisdiction: Jurisdiction name
        config: Taxonomy configuration
        
    Returns:
        List of applicable laws from search
    """
    if not config or not config.search_config.get("enable_search", True):
        return []
    
    query = f"{category} {jurisdiction} law OR statute OR regulation"
    results = serapi_search(query, config)
    
    # Extract legal information from search results
    laws = _extract_legal_info(results, jurisdiction)
    return laws

def _extract_subcategories(search_results: Dict[str, Any], parent: str) -> List[str]:
    """Extract potential subcategories from search results.
    
    Args:
        search_results: SerAPI search results
        parent: Parent category
        
    Returns:
        List of potential subcategories
    """
    subcategories = set()
    
    # Extract from organic results
    for result in search_results.get("organic_results", []):
        title = result.get("title", "")
        snippet = result.get("snippet", "")
        
        # Process title and snippet to extract potential subcategories
        # This would use more sophisticated NLP in a real implementation
        for text in [title, snippet]:
            if "types of" in text.lower() or "categories of" in text.lower():
                # Extract list items after "types of" or "categories of"
                parts = text.split(":")
                if len(parts) > 1:
                    items = parts[1].split(",")
                    for item in items:
                        item = item.strip()
                        if item and item.lower() != parent.lower():
                            subcategories.add(item)
    
    # Extract from related searches
    for related in search_results.get("related_searches", []):
        query = related.get("query", "").lower()
        if query.startswith(parent.lower()) and " vs " in query:
            # Extract comparison items
            parts = query.split(" vs ")
            if len(parts) > 1:
                item = parts[1].strip()
                if item:
                    subcategories.add(item.title())
    
    return list(subcategories)

def _extract_compliance_info(search_results: Dict[str, Any]) -> List[str]:
    """Extract compliance information from search results.
    
    Args:
        search_results: SerAPI search results
        
    Returns:
        List of compliance requirements
    """
    requirements = set()
    
    # Extract from organic results
    for result in search_results.get("organic_results", []):
        title = result.get("title", "")
        snippet = result.get("snippet", "")
        
        # Process title and snippet to extract compliance info
        # This would use more sophisticated NLP in a real implementation
        for text in [title, snippet]:
            if "require" in text.lower() or "regulation" in text.lower() or "compliance" in text.lower():
                # Extract sentences containing compliance keywords
                sentences = text.split(".")
                for sentence in sentences:
                    if any(keyword in sentence.lower() for keyword in ["require", "regulation", "compliance", "license"]):
                        requirement = sentence.strip()
                        if requirement:
                            requirements.add(requirement)
    
    return list(requirements)

def _extract_legal_info(search_results: Dict[str, Any], jurisdiction: str) -> List[Dict[str, str]]:
    """Extract legal information from search results.
    
    Args:
        search_results: SerAPI search results
        jurisdiction: Jurisdiction name
        
    Returns:
        List of laws
    """
    laws = []
    
    # Extract from organic results
    for result in search_results.get("organic_results", []):
        title = result.get("title", "")
        snippet = result.get("snippet", "")
        
        # Check if title appears to be a law
        if any(keyword in title.lower() for keyword in ["act", "law", "regulation", "code", "statute"]):
            laws.append({
                "jurisdiction": jurisdiction,
                "title": title,
                "description": snippet
            })
    
    return laws

def _mock_search_results(query: str) -> Dict[str, Any]:
    """Provide mock search results when SerAPI is unavailable.
    
    Args:
        query: Search query
        
    Returns:
        Mock search results
    """
    # This would be replaced with more comprehensive mock data in a real implementation
    return {
        "organic_results": [
            {
                "title": f"Information about {query}",
                "snippet": f"This is mock information about {query} including types such as: Type1, Type2, Type3."
            }
        ],
        "related_searches": [
            {"query": f"{query} vs Alternative1"},
            {"query": f"{query} vs Alternative2"}
        ]
    }