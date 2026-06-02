#!/usr/bin/env python3
"""Test script to verify the handwritten PDF generation works"""

import sys
from pathlib import Path

# Add project root to path for package imports when run directly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.generator import render_handwritten_pdf
from backend.config import OUTPUTS_DIR, ensure_folders

print("=" * 60)
print("HANDWRITTEN PDF GENERATION TEST")
print("=" * 60)

ensure_folders()

# Test data
test_questions = [
    "What is photosynthesis?",
    "Explain the water cycle.",
    "Define Newton's first law of motion.",
]

test_answers = [
    "Photosynthesis is the process by which plants convert light energy into chemical energy stored in glucose. It occurs in the chloroplasts of plant cells. The process involves two main stages: the light-dependent reactions that occur in the thylakoid membranes, and the light-independent reactions (Calvin cycle) that occur in the stroma. During photosynthesis, water and carbon dioxide are converted into glucose and oxygen, which is released as a byproduct.",
    
    "The water cycle is the continuous process of water moving between the Earth's surface and the atmosphere. It involves evaporation, where water from oceans, lakes, and rivers is heated by the sun and turns into water vapor. This vapor rises into the atmosphere and cools, forming clouds through condensation. When clouds become saturated, precipitation occurs in the form of rain, snow, or sleet. The water then flows back to oceans and lakes through surface runoff or infiltration into the groundwater.",
    
    "Newton's first law of motion states that an object at rest will remain at rest, and an object in motion will continue moving at constant velocity unless acted upon by an external force. This law is also known as the law of inertia. It means that objects have a tendency to resist changes in their state of motion. Without friction or other forces acting on an object, it would continue moving indefinitely at the same speed and direction.",
]

print("\n1. Testing PDF generation with handwriting features...")
try:
    pdf_url, num_pages = render_handwritten_pdf(
        name="John Doe",
        roll_number="2023001",
        subject="Biology",
        college="default",
        questions=test_questions,
        answers=test_answers,
    )
    print(f"   ✅ PDF Generated Successfully!")
    print(f"   📄 URL: {pdf_url}")
    print(f"   📊 Pages: {num_pages}")
    print(f"   💾 Location: {OUTPUTS_DIR}")
    
except Exception as e:
    print(f"   ❌ PDF Generation Failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("✅ TEST PASSED - Handwritten PDF generation is working!")
print("=" * 60)
