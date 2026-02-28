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
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content("Say 'Gemini connected!' in exactly those words.")
        print(f"   ✓ Gemini OK: {response.text.strip()}")
except ImportError:
    print("   ✗ google.generativeai not installed. Run 'pip install -r requirements.txt'")
except Exception as e:
    print(f"   ✗ Gemini FAILED: {e}")

# Test 2: Langfuse
print("\n2. Testing Langfuse connection...")
try:
    from langfuse import Langfuse
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    
    if not public_key or "pk-lf-" not in public_key or "your-key" in public_key:
         print("   ✗ Langfuse keys are missing or default. Check .env")
    else:
        lf = Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            host=os.getenv("LANGFUSE_HOST")
        )
        if lf.auth_check():
             print(f"   ✓ Langfuse OK")
        else:
             print(f"   ✗ Langfuse Auth Failed")
except ImportError:
    print("   ✗ langfuse not installed. Run 'pip install -r requirements.txt'")
except Exception as e:
    print(f"   ✗ Langfuse FAILED: {e}")
