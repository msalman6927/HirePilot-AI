from apify_client import ApifyClient
from typing import List, Dict, Any, Optional
import os
import re
import logging
from backend.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Apify Client
# Only if API Token is available to avoid crash on import
if settings.APIFY_API_TOKEN:
    client = ApifyClient(settings.APIFY_API_TOKEN)
else:
    logger.warning("APIFY_API_TOKEN is missing in settings.")
    client = None

def normalize_company_name(name: str) -> str:
    """Removes legal suffixes and whitespace."""
    if not name:
        return ""
    # Remove common suffixes like Inc., Ltd., etc.
    name = re.sub(r'\s+(Inc|Ltd|Pvt|LLC|Corp|Co|GmbH|SA)\.?$', '', name, flags=re.IGNORECASE)
    # Remove specialized chars and extra whitespace
    name = re.sub(r'[^\w\s]', '', name)
    return name.strip()

def scrape_linkedin_jobs(query: str, location: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Scrapes LinkedIn jobs using Apify actor 'curious_coder/linkedin-jobs-scraper'.
    """
    if not client:
        logger.error("Apify Client not initialized.")
        return []

    logger.info(f"Scraping LinkedIn for '{query}' in '{location}'...")
    
    # Actor Input Schema (varies by actor version, this is for curious_coder)
    run_input = {
        "keywords": query,
        "location": location,
        "limit": max_results, # Some actors use 'limit', some 'maxResults'
        "maxResults": max_results, # Providing both for safety if unsure of version
        "scrapeDescription": True # We need description for matching
    }
    
    try:
        # Run the actor
        run = client.actor("curious_coder/linkedin-jobs-scraper").call(run_input=run_input)
        
        if not run:
             logger.warning("LinkedIn scraper run failed to start.")
             return []

        # Get dataset
        dataset_id = run.get("defaultDatasetId")
        if not dataset_id:
             logger.warning("No dataset ID returned from LinkedIn scraper.")
             return []
             
        # Fetch items
        items = list(client.dataset(dataset_id).iterate_items())
        logger.info(f"LinkedIn scraper returned {len(items)} raw items.")

        normalized_jobs = []
        for item in items:
            job = {
                "title": item.get("title", "Unknown Title"),
                "company": item.get("companyName", item.get("company", "Unknown Company")),
                "location": item.get("location", location),
                "url": item.get("jobUrl", item.get("url", "")),
                "description": item.get("description", ""),
                "source": "LinkedIn",
                "posted_at": item.get("postedAt", item.get("date", ""))
            }
            # Basic validation
            if job["title"] and job["url"]:
                 normalized_jobs.append(job)
                 
        return normalized_jobs

    except Exception as e:
        logger.error(f"Error scraping LinkedIn: {e}")
        return []

def scrape_indeed_jobs(query: str, location: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Scrapes Indeed jobs using Apify actor 'misceres/indeed-scraper'.
    """
    if not client:
        return []

    logger.info(f"Scraping Indeed for '{query}' in '{location}'...")
    
    # Run Input (misceres/indeed-scraper)
    run_input = {
        "position": query,
        "country": "PK", # Defaulting to PK based on user context (Lahore)
        "location": location,
        "maxItems": max_results,
        "parseCompanyDetails": False
    }

    try:
        run = client.actor("misceres/indeed-scraper").call(run_input=run_input)
        
        if not run:
             return []

        dataset_id = run.get("defaultDatasetId")
        items = list(client.dataset(dataset_id).iterate_items())
        logger.info(f"Indeed scraper returned {len(items)} raw items.")
        
        normalized_jobs = []
        for item in items:
            job = {
                "title": item.get("positionName", item.get("title", "Unknown Title")),
                "company": item.get("company", "Unknown Company"),
                "location": item.get("location", location),
                "url": item.get("url", ""),
                "description": item.get("description", ""),
                "source": "Indeed",
                "posted_at": item.get("postedAt", "")
            }
            if job["title"] and job["url"]:
                 normalized_jobs.append(job)
                 
        return normalized_jobs
        
    except Exception as e:
        logger.error(f"Error scraping Indeed: {e}")
        return []

def deduplicate_jobs(jobs_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Removes duplicates based on normalized (company + title + location).
    """
    seen = set()
    unique_jobs = []
    
    for job in jobs_list:
        norm_company = normalize_company_name(job["company"]).lower()
        norm_title = re.sub(r'\s+', ' ', job["title"]).strip().lower()
        # Simple location normalization (e.g. "Lahore, Pakistan" -> "lahore")
        norm_location = job["location"].split(',')[0].strip().lower()
        
        key = f"{norm_company}|{norm_title}|{norm_location}"
        
        if key not in seen:
            seen.add(key)
            unique_jobs.append(job)
            
    return unique_jobs
