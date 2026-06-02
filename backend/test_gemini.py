#!/usr/bin/env python3
"""Test script to verify Gemini API is working"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import SETTINGS

print("=" * 60)
print("GEMINI API TEST")
print("=" * 60)

# Check 1: API Key Presence
print("\n1. Checking if GEMINI_API_KEY is set...")
if SETTINGS.gemini_api_key:
    key_masked = f"{SETTINGS.gemini_api_key[:10]}...{SETTINGS.gemini_api_key[-5:]}"
    print(f"   ✅ API Key Found: {key_masked}")
else:
    print("   ❌ API Key NOT found - Check .env file")
    exit(1)

# Check 2: Library Installation
print("\n2. Checking if google-generativeai is installed...")
try:
    import google.generativeai as genai
    print("   ✅ google-generativeai is installed")
except ImportError as e:
    print(f"   ❌ google-generativeai NOT installed: {e}")
    exit(1)

# Check 3: Configure API
print("\n3. Configuring Gemini API...")
try:
    genai.configure(api_key=SETTINGS.gemini_api_key)
    print("   ✅ API configured successfully")
except Exception as e:
    print(f"   ❌ Failed to configure API: {e}")
    exit(1)

# Check 4: Test API Call
print("\n4. Testing API with a sample question...")
test_question = "What is photosynthesis?"
target_words = 150

prompt = f"""
Write a college exam style answer in simple English.

Question: {test_question}

Requirements:
- Plain text only (no markdown symbols, no '*' or '-' bullets).
- Use headings exactly: Title, Definition, Explanation, Key Points, Conclusion.
- In Key Points, use numbering like 1) 2) 3) etc.
- Around {target_words} words (approximate is fine).
- Keep it readable and structured.
""".strip()

try:
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt)
    answer_text = response.text
    
    if answer_text:
        word_count = len(answer_text.split())
        print(f"   ✅ API Response Received!")
        print(f"   📝 Word Count: {word_count}")
        print(f"\n   Answer Preview (First 300 chars):")
        print(f"   {answer_text[:300]}...")
    else:
        print("   ❌ Empty response from API")
        exit(1)
        
except Exception as e:
    print(f"   ❌ API Call Failed: {type(e).__name__}: {e}")
    exit(1)

print("\n" + "=" * 60)
print("✅ ALL TESTS PASSED - GEMINI API IS WORKING!")
print("=" * 60)
