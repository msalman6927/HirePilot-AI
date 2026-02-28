from backend.agents.cv_parser_agent import cv_parser_node
from backend.agents.state import HirePilotState
import json

def test_cv_agent():
    # Mock CV text
    cv_text = """
    John Doe
    john.doe@example.com
    555-123-4567
    
    Summary:
    Experienced Python Developer with 5 years of experience in AI and Web Development.
    
    Experience:
    Software Engineer at TechCorp (2020-Present)
    - Developed AI agents using LangGraph
    - Optimized backend APIs with FastAPI
    
    Education:
    B.S. Computer Science, University of Technology (2016-2020)
    
    Skills:
    Python, FastAPI, SQL, Machine Learning
    """
    
    # Create mock state
    state: HirePilotState = {
        "user_message": "Parse my CV",
        "thread_id": "test_session_cv_1",
        "cv_text": cv_text,
        "cv_structured": None,
        "job_search_criteria": None,
        "found_jobs": [],
        "hitl_approved": False
    }
    
    # Run the node
    print("Running CV Parser Node...")
    new_state = cv_parser_node(state)
    
    # Verify output
    if new_state.get("cv_structured"):
        print("\nSUCCESS: CV Parsed Successfully!")
        print(json.dumps(new_state["cv_structured"], indent=2))
        
        # Basic checks
        data = new_state["cv_structured"]
        assert data["personal_info"]["full_name"] == "John Doe", f"Expected John Doe, got {data['personal_info']['full_name']}"
        assert "Python" in data["skills"], "Expected Python in skills"
        print("\nAssertion Checks Passed.")
    else:
        print("\nFAILURE: cv_structured is None")

if __name__ == "__main__":
    test_cv_agent()
