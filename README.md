# Canvas LMS Integration for Home Assistant

A custom Home Assistant integration to monitor student progress, grades, and upcoming assignments from Canvas LMS.

## Features
- **Student-Centric Sensors**: Individual sensors for each student found in your account.
- **Course Grades**: Real-time tracking of current scores and grades for every enrolled course.
- **Intelligent Assignment Tracking**: Dedicated sensors for assignments due **Today**, **Tomorrow**, **Upcoming** (next 7 days), and **Missed** (last 7 days).
- **Assignment Calendar**: Dedicated calendar entities for each student showing all upcoming assignment due dates.
- **Easy Configuration**: Simple setup through the Home Assistant UI using your Canvas URL and Access Token.

## Prerequisites
1.  **Canvas URL**: Your school's Canvas address (e.g., `https://[school].instructure.com`).
2.  **Access Token**:
    - Log in to your Canvas account.
    - Go to **Settings** -> **Approved Integrations**.
    - Click **+ New Access Token**.
    - Give it a purpose (e.g., "Home Assistant") and save the generated token.

## Installation
1.  Navigate to your Home Assistant `config` directory.
2.  Copy the `custom_components/canvas` directory from this repository into your `custom_components` folder.
3.  Restart Home Assistant.

## Configuration
1.  In Home Assistant, go to **Settings** -> **Devices & Services**.
2.  Click **Add Integration** and search for **Canvas LMS**.
3.  Enter your **Canvas URL** and **Access Token** when prompted.

## Available Entities

### Sensors
For every student, the following sensors are created:
- `sensor.[student_name]_assignments_today`: Count of assignments due by midnight tonight.
- `sensor.[student_name]_assignments_tomorrow`: Count of assignments due by midnight tomorrow.
- `sensor.[student_name]_assignments_upcoming`: Count of assignments due in the next **7 days**.
- `sensor.[student_name]_assignments_missed`: Count of incomplete assignments from the last **7 days**.
- `sensor.[student_name]_[course_name]_grade`: Current score percentage or letter grade.
    - **Attributes**: `current_score`, `current_grade`, `final_score`, `final_grade`.

### Calendar
Every student will have a calendar entity:
- `calendar.canvas_[student_name]_assignments`
- **Contents**: All upcoming assignments marked on their due dates.

## Support
The integration uses the Enrollments API to ensure it works correctly for both Student and Parent (Observer) accounts.

## Testing
To run the automated mock tests:
1.  Set up a virtual environment and install dependencies:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install aiohttp async-timeout python-dotenv pytest pytest-asyncio aresponses
    ```
2.  Run the tests using `pytest`:
    ```bash
    export PYTHONPATH=$PYTHONPATH:.
    pytest tests/
    ```
