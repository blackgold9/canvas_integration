"""Student data container."""
from __future__ import annotations
from dataclasses import dataclass, field
from .assignment_logic import CanvasAssignment

@dataclass
class CanvasStudentData:
    """Aggregated data for a student."""
    student_id: str
    name: str
    courses: list[dict] = field(default_factory=list)
    assignments: list[CanvasAssignment] = field(default_factory=list)
