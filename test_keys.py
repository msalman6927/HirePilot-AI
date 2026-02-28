# test_keys.py — Run with: python test_keys.py
# Delete this file after keys are verified

import os
from dotenv import load_dotenv
import sys

# Add the project root to sys.path to ensure imports work if needed
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    load_dotenv()
    print("✓ Loaded .env file")
except Exception as e:
    print(f"✗ Failed to load .env: {e}")

print("=== Testing API Keys ===\n")

# Test 1: Gemini
print("1. Testing Gemini API...")
try:
    import google.generativeai as genai
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or "your_" in api_key:
        print("   ✗ Gemini API Key is missing or default. Check .env")
    else:
        genai.configure(api_key=api_key)
        print("   Checking available models...")
        try:
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    print(f"    - {m.name}")
            
            # Use the model available in this environment (verified as gemini-2.5-flash)
            print("   Using verified model: gemini-2.5-flash")
            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content("Say 'Gemini connected!'")
            print(f"   ✓ Gemini OK: {response.text.strip()}")
        except Exception as e:
            print(f"   ✗ Gemini Test Failed: {e}")
except ImportError:
    print("   ✗ google.generativeai not installed. Run 'pip install -r requirements.txt'")
except Exception as e:
    print(f"   ✗ Gemini FAILED: {e}")

# Test 2: Langfuse
def try_auth(host_url):
    try:
        lf = Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            host=host_url
        )
        if lf.auth_check():
             print(f"   ✓ Langfuse OK ({host_url})")
             return True
    except Exception:
        pass
    print(f"   ✗ Langfuse Auth Failed ({host_url})")
    return False

print("\n2. Testing Langfuse connection...")
try:
    from langfuse import Langfuse
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")


    
    # Try default host first
    try_auth(os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"))
    
    # If failed, try US host as fallback
    if "pk-lf" in public_key:
         print("   ! Retrying with US region host...")
         try_auth("https://us.cloud.langfuse.com")

except ImportError:
    print("   ✗ langfuse not installed. Run 'pip install -r requirements.txt'")
except Exception as e:
    print(f"   ✗ Langfuse FAILED: {e}")
