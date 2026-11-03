"""Data model for the generated report.

Every metadata field is optional: the report stays valid (and still looks
professional) when the user only fills in part of the identity block.  The
dataclasses keep the report layer independent of Streamlit so it can be
unit-tested and reused.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class TeamMember:
    """One member of the working group. All fields are optional."""

    name: str = ""
    nim: str = ""
    role: str = ""

    @property
    def is_empty(self) -> bool:
        return not (
            str(self.name).strip() or str(self.nim).strip() or str(self.role).strip()
        )

    def one_line(self) -> str:
        """Human readable single line, e.g. ``Budi — NIM 21.11.0001 — Ketua``."""
        parts: List[str] = []
        if str(self.name).strip():
            parts.append(str(self.name).strip())
        if str(self.nim).strip():
            parts.append(f"NIM {str(self.nim).strip()}")
        if str(self.role).strip():
            parts.append(str(self.role).strip())
        return " — ".join(parts)

    def to_dict(self) -> dict:
        return {"name": self.name, "nim": self.nim, "role": self.role}

    @classmethod
    def from_dict(cls, data: Optional[dict]) -> "TeamMember":
        data = data or {}
        return cls(
            name=str(data.get("name", "")),
            nim=str(data.get("nim", "")),
            role=str(data.get("role", "")),
        )


@dataclass
class ReportMeta:
    """User supplied report metadata. Empty strings simply hide a row."""

    title: str = "Laporan Hasil Diagnosis Gangguan Internet"
    assignment: str = ""
    course: str = ""
    group_name: str = ""
    group_number: str = ""
    members: List[TeamMember] = field(default_factory=list)
    lecturer: str = ""
    assistant: str = ""
    program_study: str = ""
    department: str = ""
    faculty: str = ""
    institution: str = ""
    city: str = ""
    date: str = ""
    logo_data_url: str = ""
    summary: str = ""
    background: str = ""
    conclusion: str = ""

    @property
    def real_members(self) -> List[TeamMember]:
        return [member for member in self.members if not member.is_empty]

    @property
    def group_label(self) -> str:
        name = str(self.group_name).strip()
        number = str(self.group_number).strip()
        if name and number:
            return f"{name} ({number})"
        if name:
            return name
        if number:
            return f"Kelompok {number}"
        return ""

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "assignment": self.assignment,
            "course": self.course,
            "group_name": self.group_name,
            "group_number": self.group_number,
            "members": [member.to_dict() for member in self.members],
            "lecturer": self.lecturer,
            "assistant": self.assistant,
            "program_study": self.program_study,
            "department": self.department,
            "faculty": self.faculty,
            "institution": self.institution,
            "city": self.city,
            "date": self.date,
            "logo_data_url": self.logo_data_url,
            "summary": self.summary,
            "background": self.background,
            "conclusion": self.conclusion,
        }

    @classmethod
    def from_dict(cls, data: Optional[dict]) -> "ReportMeta":
        data = data or {}
        members = [
            TeamMember.from_dict(item) for item in data.get("members", []) or []
        ]
        return cls(
            title=str(data.get("title", ReportMeta.title)) or ReportMeta.title,
            assignment=str(data.get("assignment", "")),
            course=str(data.get("course", "")),
            group_name=str(data.get("group_name", "")),
            group_number=str(data.get("group_number", "")),
            members=members,
            lecturer=str(data.get("lecturer", "")),
            assistant=str(data.get("assistant", "")),
            program_study=str(data.get("program_study", "")),
            department=str(data.get("department", "")),
            faculty=str(data.get("faculty", "")),
            institution=str(data.get("institution", "")),
            city=str(data.get("city", "")),
            date=str(data.get("date", "")),
            logo_data_url=str(data.get("logo_data_url", "")),
            summary=str(data.get("summary", "")),
            background=str(data.get("background", "")),
            conclusion=str(data.get("conclusion", "")),
        )
