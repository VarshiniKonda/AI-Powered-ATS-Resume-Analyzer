from app.ml_engine.matching import _skill_match, _tfidf
from app.ml_engine.skills import extract_skills, normalize_skill
from app.services.job_parser import parse_job_description
from app.services.resume_parser import parse_resume_text


def test_skill_synonyms_and_overlapping_names_are_normalized() -> None:
    skills = extract_skills("Built a React Native app with Node.js, JS, and PostgreSQL.")
    assert "React Native" in skills
    assert "React" not in skills
    assert "Node.js" in skills
    assert "JavaScript" in skills
    assert normalize_skill("postgres") == "PostgreSQL"


def test_job_parser_separates_required_and_preferred_skills() -> None:
    job = parse_job_description(
        """Senior Data Engineer
        Required: Python, SQL, and AWS.
        Nice to have: Kubernetes and Tableau.
        Minimum 5 years of experience. Bachelor's degree required.
        Responsibilities: Build reliable data platforms and projects."""
    )
    assert {"Python", "SQL", "AWS"} <= set(job["required_skills"])
    assert {"Kubernetes", "Tableau"} <= set(job["preferred_skills"])
    assert job["experience_years"] == 5
    assert job["education_level"] == "bachelor"
    assert job["projects_expected"]


def test_job_parser_extracts_professional_experience_requirement() -> None:
    job = parse_job_description(
        "Python Developer. Requires 3 years of professional experience."
    )

    assert job["experience_years"] == 3


def test_partial_skill_and_tfidf_similarity_use_source_text() -> None:
    match_type, evidence = _skill_match("PostgreSQL", {"SQL"}, "SQL reports")
    assert match_type == "partial"
    assert evidence == "SQL"
    assert _skill_match("Proprietary Tool", set(), "Used Proprietary Tool in production") == (
        "matched",
        "Proprietary Tool",
    )
    score, keywords = _tfidf(
        "Build Python REST APIs and PostgreSQL services",
        "Implemented Python services and PostgreSQL REST APIs",
    )
    assert score > 0
    assert "python" in keywords


def test_resume_parser_captures_project_and_degree_sections() -> None:
    parsed = parse_resume_text(
        "EXPERIENCE\nDeveloper, 4 years experience\n"
        "EDUCATION\nMaster of Science in Analytics\n"
        "PROJECTS\nPython forecasting project"
    )
    assert parsed["experience_years"] == 4
    assert parsed["education_level"] == "master"
    assert "forecasting" in parsed["projects"]