"""Structured extraction of role requirements from pasted job descriptions."""

import re
from typing import Any

from app.ml_engine.skills import extract_skill_occurrences, normalize_skill
from app.services.resume_parser import EXPERIENCE_PATTERN, _education_level

PREFERRED_CONTEXT = re.compile(
    r"\b(preferred|preferably|nice to have|nice-to-have|bonus|desirable|a plus)\b",
    re.IGNORECASE,
)
PROJECT_CONTEXT = re.compile(r"\b(projects?|portfolios?|case studies|work samples?)\b", re.I)


def parse_job_description(
    text: str,
    title: str | None = None,
    required_skills: list[str] | None = None,
    preferred_skills: list[str] | None = None,
) -> dict[str, Any]:
    title_guess = title.strip() if title and title.strip() else None
    if not title_guess:
        first_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
        title_guess = first_line[:255] if first_line and len(first_line) <= 255 else "Job Opportunity"

    required = {normalize_skill(skill) for skill in (required_skills or []) if skill.strip()}
    preferred = {normalize_skill(skill) for skill in (preferred_skills or []) if skill.strip()}
    skill_context: dict[str, str] = {}
    for occurrence in extract_skill_occurrences(text):
        skill_context.setdefault(occurrence.skill, occurrence.context)
        if occurrence.skill in required or occurrence.skill in preferred:
            continue
        if PREFERRED_CONTEXT.search(occurrence.context):
            preferred.add(occurrence.skill)
        else:
            required.add(occurrence.skill)

    preferred -= required
    years_match = EXPERIENCE_PATTERN.search(text)
    responsibilities = _extract_section(text, ("responsibilities", "what you will do", "what you'll do"))
    qualifications = _extract_section(text, ("qualifications", "requirements", "what you bring"))

    return {
        "title": title_guess,
        "required_skills": sorted(required, key=str.casefold),
        "preferred_skills": sorted(preferred, key=str.casefold),
        "skill_context": skill_context,
        "experience_years": float(years_match.group(1)) if years_match else None,
        "education_level": _education_level(text),
        "responsibilities": responsibilities,
        "qualifications": qualifications,
        "projects_expected": bool(PROJECT_CONTEXT.search(text)),
    }


def _extract_section(text: str, headings: tuple[str, ...]) -> str | None:
    lines = text.splitlines()
    capture = False
    collected: list[str] = []
    other_headings = {
        "responsibilities",
        "what you will do",
        "what you'll do",
        "qualifications",
        "requirements",
        "what you bring",
        "about the role",
        "about us",
        "benefits",
        "preferred qualifications",
    }
    for line in lines:
        normalized = line.strip().rstrip(":").casefold()
        if any(normalized == heading for heading in headings):
            capture = True
            continue
        if capture and normalized in other_headings:
            break
        if capture and line.strip():
            collected.append(line.strip())
    return "\n".join(collected).strip() or None
