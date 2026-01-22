import os
import asyncio
import aiohttp
import pytest
from dotenv import load_dotenv
from custom_components.canvas.api import CanvasAPI
from custom_components.canvas.assignment_logic import filter_assignments

# Load environment variables
load_dotenv()

CANVAS_URL = os.getenv("CANVAS_URL")
CANVAS_TOKEN = os.getenv("CANVAS_TOKEN")

@pytest.mark.skipif(not CANVAS_URL or not CANVAS_TOKEN, reason="Canvas credentials not found in .env")
@pytest.mark.asyncio
async def test_live_api_flow():
    """Verify full flow against a live Canvas instance."""
    async with aiohttp.ClientSession() as session:
        api = CanvasAPI(CANVAS_URL, CANVAS_TOKEN, session)
        
        # 1. Fetch Students
        print("\nFetching students...")
        students = await api.async_get_students()
        assert students is not None
        print(f"Found {len(students)} students.")
        
        if not students:
            print("No students found. Checking user info...")
            user_info = await api.async_get_user_info()
            students = [user_info]
        for student in students:
            student_id = student["id"]
            student_name = student.get("name", "Unknown")
            print(f"\nProcessing student: {student_name} ({student_id})")
            
            # 2. Fetch Courses (optimized with total_scores and term)
            courses = await api.async_get_courses(user_id=student_id)
            print(f"Found {len(courses)} courses total.")
            
            final_context_codes = []
            for c in courses:
                term = c.get("term", {}).get("name", "N/A")
                score = c.get("enrollments", [{}])[0].get("computed_current_score")
                
                if "Archive" in term:
                    print(f"  - [SKIPPED ARCHIVE] {c.get('name')}: Term={term}")
                    continue
                
                print(f"  - [ACTIVE] {c.get('name')}: Term={term}, Grade={score}")
                final_context_codes.append(f"course_{c['id']}")
            
            # 3. Fetch Planner Items (bulk assignments/submissions)
            from datetime import datetime, timedelta
            start = (datetime.now() - timedelta(days=30)).isoformat()
            end = (datetime.now() + timedelta(days=30)).isoformat()
            
            print(f"\nFetching planner items for student {student_id}...")
            if final_context_codes:
                items = await api.async_get_planner_items(student_id, start, end, final_context_codes)
                assignments = [i for i in items if i.get("plannable_type") == "assignment"]
                print(f"Found {len(assignments)} assignments in planner.")
                
                for item in assignments[:5]:
                    plannable = item.get("plannable", {})
                    sub = item.get("submissions", {})
                    state = "Submitted" if (sub.get("submitted") or sub.get("graded")) else "Pending"
                    print(f"      - {plannable.get('title')}: {state}")

if __name__ == "__main__":
    # Allow running directly for quick testing
    asyncio.run(test_live_api_flow())
