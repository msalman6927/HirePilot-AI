from typing import Dict, Any, List
import logging
import json
from langchain_core.messages import HumanMessage
from langfuse.decorators import observe

from backend.agents.state import HirePilotState
from backend.tools.apify_tool import scrape_linkedin_jobs, scrape_indeed_jobs, deduplicate_jobs
from backend.agents.cv_tailoring_agent import calculate_match_score
from backend.tools.gemini_llm import get_llm, clean_json_response

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@observe(name="JobSearchAgent")
def job_search_node(state: HirePilotState) -> HirePilotState:
    """
    Executes job search on LinkedIn and Indeed using Apify.
    Deduplicates results and ranks them against the user's CV.
    """
    logger.info("AGENT: Job Search Agent Active")
    
    # Initialize "agent_logs" if not present
    if "agent_logs" not in state:
        state["agent_logs"] = []
        
    state["agent_logs"].append({
        "agent": "JobSearchAgent",
        "action": "Starting job search execution...",
        "status": "running"
    })
    
    session_id = state.get("thread_id", "default")
    
    # 1. Extract Search Parameters
    criteria = state.get("job_search_criteria")
    
    # If orchestrator didn't parse criteria perfectly, try again or use defaults
    query = "Software Engineer"
    location = "Remote"
    
    if criteria and isinstance(criteria, dict):
        query = criteria.get("query", query)
        location = criteria.get("location", location)
    else:
        # Fallback: Ask LLM to parse from user message if missing
        logger.info("AGENT: Missing criteria, extracting from user message...")
        llm, _ = get_llm(session_id, "JobSearchParamExtractor")
        user_msg = state.get("user_message", "")
        prompt = f"""Extract job search parameters from: "{user_msg}"
        Return JSON: {{"query": "job title", "location": "city or remote"}}
        If no location specified, default to "Remote".
        """
        try:
            resp = llm.invoke(prompt)
            clean = clean_json_response(resp.content)
            parsed = json.loads(clean)
            query = parsed.get("query", query)
            location = parsed.get("location", location)
            # Update state for future use
            state["job_search_criteria"] = {"query": query, "location": location}
        except Exception:
            pass

    logger.info(f"AGENT: Searching for '{query}' in '{location}'")
    state["agent_logs"].append({
        "agent": "JobSearchAgent",
        "action": f"Searching LinkedIn & Indeed for '{query}' in '{location}'",
        "status": "running"
    })

    # 2. Execute scraping (Parallel could be better, sequential for now)
    linkedin_jobs = scrape_linkedin_jobs(query, location, max_results=5)
    indeed_jobs = scrape_indeed_jobs(query, location, max_results=5)
    
    # 3. Deduplicate
    all_jobs = linkedin_jobs + indeed_jobs
    unique_jobs = deduplicate_jobs(all_jobs)
    
    logger.info(f"AGENT: Found {len(unique_jobs)} unique jobs.")

    # 4. Rank / Score using CV
    cv_data = state.get("cv_structured")
    ranked_jobs = []
    
    if cv_data:
        logger.info("AGENT: Ranking jobs against CV...")
        for job in unique_jobs:
            score = calculate_match_score(cv_data, job.get("description", "") + " " + job.get("title", ""))
            job["match_score"] = score
            ranked_jobs.append(job)
        
        # Sort desc by score
        ranked_jobs.sort(key=lambda x: x.get("match_score", 0), reverse=True)
    else:
        logger.info("AGENT: No CV found, skipping ranking.")
        ranked_jobs = unique_jobs

    # 5. Take top results
    top_jobs = ranked_jobs[:10]
    
    # Identify "best match" flag for UI
    for i, job in enumerate(top_jobs):
        if i < 3:
            job["is_best_match"] = True
        else:
            job["is_best_match"] = False

    # 6. Update State
    state["found_jobs"] = top_jobs
    
    # 7. Formulate Human-Readable Summary for "final_response"
    count = len(top_jobs)
    if count > 0:
        titles = [f"- {j['title']} at {j['company']} ({j.get('match_score', 0)}% match)" for j in top_jobs[:3]]
        summary = "\n".join(titles)
        state["final_response"] = f"I found {len(unique_jobs)} jobs matching '{query}' in '{location}'. Here are the best matches based on your CV:\n{summary}"
    else:
        state["final_response"] = f"I searched for '{query}' in '{location}' but found no matching jobs. Try broadening your location or keywords."

    state["agent_logs"].append({
        "agent": "JobSearchAgent",
        "action": f"Found {count} jobs.",
        "status": "completed"
    })
    
    return state
