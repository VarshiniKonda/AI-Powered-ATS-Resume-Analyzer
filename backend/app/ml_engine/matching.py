"""Explainable resume-to-job scoring using structured skills and text similarity."""

import re
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.core.config import settings
from app.ml_engine.semantic import semantic_similarity
from app.ml_engine.skills import normalize_skill

EDUCATION_RANK = {
    "high_school": 1,
    "associate": 2,
    "bachelor": 3,
    "master": 4,
    "doctorate": 5,
}
RELATED_SKILLS = {
    frozenset({"SQL", "PostgreSQL"}),
    frozenset({"SQL", "MySQL"}),
    frozenset({"React", "React Native"}),
    frozenset({"JavaScript", "TypeScript"}),
    frozenset({"AWS", "Google Cloud"}),
    frozenset({"AWS", "Azure"}),
    frozenset({"Azure", "Google Cloud"}),
}
SECTION_LABELS = {
    "experience": "Experience",
    "projects": "Projects",
    "education": "Education",
    "skills": "Skills",
    "certifications": "Certifications",
}


def _tfidf(first: str, second: str) -> tuple[float, list[str]]:
    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=20_000)
    try:
        matrix = vectorizer.fit_transform([first, second])
    except ValueError:
        return 0.0, []
    score = float(cosine_similarity(matrix[0], matrix[1])[0, 0])
    features = vectorizer.get_feature_names_out()
    job_weights = matrix[0].toarray().ravel()
    top_indexes = job_weights.argsort()[::-1]
    keywords = [
        str(features[index])
        for index in top_indexes
        if job_weights[index] > 0 and len(str(features[index])) >= 3
    ][:80]
    return score, keywords


def _contains_phrase(text: str, phrase: str) -> bool:
    return bool(re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", text, re.I))


def _skill_match(
    required: str,
    resume_skills: set[str],
    resume_text: str,
) -> tuple[str | None, str | None]:
    canonical = normalize_skill(required)
    if canonical in resume_skills:
        return "matched", canonical
    if _contains_phrase(resume_text, required):
        return "matched", canonical
    related = next(
        (skill for skill in resume_skills if frozenset({canonical, skill}) in RELATED_SKILLS),
        None,
    )
    if related:
        return "partial", related
    target_tokens = set(re.findall(r"[a-z0-9]+", canonical.casefold()))
    for skill in resume_skills:
        candidate_tokens = set(re.findall(r"[a-z0-9]+", skill.casefold()))
        if len(target_tokens) > 1 and len(candidate_tokens) > 1:
            overlap = len(target_tokens & candidate_tokens) / max(len(target_tokens), len(candidate_tokens))
            if overlap >= 0.5:
                return "partial", skill
    return None, None


def _skill_results(
    job_data: dict[str, Any],
    resume_data: dict[str, Any],
    job_text: str,
    resume_text: str,
) -> tuple[list[dict[str, str]], list[dict[str, str]], float | None]:
    resume_skills = {normalize_skill(skill) for skill in resume_data.get("skills", [])}
    evidence = {
        normalize_skill(item.get("skill", "")): item.get("evidence", "")
        for item in resume_data.get("skill_evidence", [])
    }
    matches: list[dict[str, str]] = []
    missing: list[dict[str, str]] = []
    required_scores: list[float] = []

    for category, key in (("required", "required_skills"), ("preferred", "preferred_skills")):
        for skill in job_data.get(key, []):
            match_type, matched_name = _skill_match(skill, resume_skills, resume_text)
            if match_type:
                matches.append(
                    {
                        "skill": skill,
                        "category": category,
                        "match_type": match_type,
                        "evidence": evidence.get(
                            matched_name or "",
                            next(
                                (
                                    line.strip()[:200]
                                    for line in resume_text.splitlines()
                                    if _contains_phrase(line, skill)
                                ),
                                "",
                            ),
                        ),
                    }
                )
                if category == "required":
                    required_scores.append(1.0 if match_type == "matched" else 0.5)
            else:
                context = job_data.get("skill_context", {}).get(skill, "")
                if not context:
                    context = next(
                        (
                            line.strip()
                            for line in job_text.splitlines()
                            if _contains_phrase(line, skill)
                        ),
                        "",
                    )
                explanation = (
                    f"The job description identifies {skill} as {category}; it is not evidenced "
                    "in the extracted resume text. Add it only if you can support the claim "
                    "with genuine experience."
                )
                if context:
                    explanation += f" Job context: “{context[:180]}”"
                missing.append(
                    {"skill": skill, "category": category, "explanation": explanation}
                )
                if category == "required":
                    required_scores.append(0.0)

    score = sum(required_scores) / len(required_scores) if required_scores else None
    return matches, missing, score


def _education_score(required: str | None, candidate: str | None) -> float | None:
    if not required or not candidate or required not in EDUCATION_RANK or candidate not in EDUCATION_RANK:
        return None
    return 1.0 if EDUCATION_RANK[candidate] >= EDUCATION_RANK[required] else 0.0


def _suggestions(
    missing: list[dict[str, str]],
    resume_data: dict[str, Any],
    relevant_sections: list[dict[str, Any]],
) -> tuple[list[str], list[str], dict[str, str]]:
    improvements: list[str] = []
    learn: list[str] = []
    for item in missing:
        skill = item["skill"]
        if item["category"] == "required":
            improvements.append(
                f"If you have verifiable experience with {skill}, add one concise example showing "
                "where and how you used it; otherwise consider learning it before claiming it."
            )
            learn.append(f"Build genuine, demonstrable proficiency in {skill} before listing it.")
        else:
            improvements.append(
                f"Consider addressing preferred skill {skill} only if it reflects your real experience."
            )

    sections = resume_data.get("sections", {})
    bullet = next(
        (
            line.strip().lstrip("•*- ").strip()
            for line in resume_data.get("experience", "").splitlines()
            if line.strip() and len(line.strip()) > 35
        ),
        None,
    )
    if bullet:
        improvements.append(
            "Strengthen an existing experience bullet with scope or a measurable result only "
            f"when accurate. Current example: “{bullet[:220]}”"
        )
    if not sections.get("projects"):
        improvements.append(
            "If you have relevant projects, add a clearly labeled Projects section describing "
            "your role, approach, tools, and verifiable outcome."
        )
    if not resume_data.get("education"):
        improvements.append(
            "Add an Education section if relevant; the analyzer could not reliably extract one."
        )
    if not resume_data.get("certifications"):
        improvements.append(
            "List relevant certifications only if earned and current; do not imply credentials you do not hold."
        )

    section_feedback = {
        "experience": (
            "Experience text was extracted. Prioritize job-relevant examples and state measurable "
            "impact only where you can substantiate it."
            if sections.get("experience")
            else "No clearly labeled experience section was detected; verify extraction and use clear section headings."
        ),
        "projects": (
            "Describe your contribution, methods, and verified outcomes for each relevant project."
            if sections.get("projects")
            else "No clearly labeled projects section was detected."
        ),
        "formatting": (
            "Use standard headings, consistent dates, readable bullets, and a text-selectable PDF or DOCX. "
            "Avoid columns or graphics that can disrupt document extraction."
        ),
        "relevance": (
            f"Most relevant extracted section: {relevant_sections[0]['section']}."
            if relevant_sections
            else "No resume section had a strong text match; review the extracted text and job requirements."
        ),
    }
    return improvements, learn, section_feedback


def analyze_match(
    resume_text: str,
    resume_data: dict[str, Any],
    job_text: str,
    job_data: dict[str, Any],
) -> dict[str, Any]:
    """Produce explainable matching details and a score from actual source text."""
    tfidf_score, keywords = _tfidf(job_text, resume_text)
    semantic_score = semantic_similarity(resume_text, job_text)
    matched, missing, required_score = _skill_results(
        job_data, resume_data, job_text, resume_text
    )
    resume_years = resume_data.get("experience_years")
    required_years = job_data.get("experience_years")
    experience_score: float | None = None
    experience_semantic: float | None = None
    if required_years and resume_years is not None:
        experience_text = resume_data.get("experience") or ""
        if experience_text:
            experience_semantic = semantic_similarity(experience_text, job_text)
            experience_score = 0.7 * min(float(resume_years) / float(required_years), 1.0)
            experience_score += 0.3 * experience_semantic
        else:
            experience_score = min(float(resume_years) / float(required_years), 1.0)

    project_text = resume_data.get("projects") or ""
    project_score: float | None = None
    project_semantic: float | None = None
    if project_text:
        project_semantic = semantic_similarity(project_text, job_text)
        project_score = project_semantic

    education_score = _education_score(
        job_data.get("education_level"), resume_data.get("education_level")
    )
    configured_weights = settings.scoring_weight_map
    components: dict[str, float | None] = {
        "required_skills": required_score,
        "keyword_match": tfidf_score,
        "experience": experience_score,
        "education": education_score,
        "project_relevance": project_score,
    }
    available_weight = sum(
        configured_weights[name] for name, value in components.items() if value is not None
    )
    if available_weight <= 0:
        raise ValueError("The job description does not contain enough information to score.")

    breakdown = {
        name: {
            "score": round(value * 100, 1) if value is not None else None,
            "available": value is not None,
            "configured_weight": configured_weights[name],
            "effective_weight_percent": round(configured_weights[name] / available_weight * 100, 1)
            if value is not None
            else 0.0,
        }
        for name, value in components.items()
    }
    overall_score = sum(
        configured_weights[name] * value
        for name, value in components.items()
        if value is not None
    ) / available_weight * 100

    missing_keywords = [
        keyword
        for keyword in keywords
        if not _contains_phrase(resume_text, keyword)
    ][:15]
    sections = resume_data.get("sections", {})
    relevant_sections = []
    for section_name, content in sections.items():
        if not content:
            continue
        section_tfidf, _ = _tfidf(job_text, content)
        section_semantic = semantic_similarity(content, job_text)
        relevant_sections.append(
            {
                "section": SECTION_LABELS.get(section_name, section_name.title()),
                "tfidf_similarity": round(section_tfidf * 100, 1),
                "semantic_similarity": round(section_semantic * 100, 1),
            }
        )
    relevant_sections.sort(
        key=lambda item: (item["semantic_similarity"], item["tfidf_similarity"]), reverse=True
    )
    improvements, learn, section_feedback = _suggestions(missing, resume_data, relevant_sections)
    matched_keywords = [
        keyword for keyword in keywords if _contains_phrase(resume_text, keyword)
    ][:15]
    required_total = len(job_data.get("required_skills", []))
    required_percent = (
        sum(1 if item["match_type"] == "matched" else 0.5 for item in matched if item["category"] == "required")
        / required_total
        * 100
        if required_total
        else None
    )
    preferred_missing = [item for item in missing if item["category"] == "preferred"]
    required_missing = [item for item in missing if item["category"] == "required"]
    fully_matched_required = [
        item["skill"]
        for item in matched
        if item["category"] == "required" and item["match_type"] == "matched"
    ]
    partial_required = [
        item["skill"]
        for item in matched
        if item["category"] == "required" and item["match_type"] == "partial"
    ]
    resume_strengths: list[str] = []
    areas_to_improve: list[str] = []
    if fully_matched_required:
        resume_strengths.append(
            "Resume text directly evidences required skills: "
            + ", ".join(fully_matched_required)
            + "."
        )
    if experience_score is not None and experience_score >= 0.7:
        resume_strengths.append(
            f"Extracted experience evidence aligns at {round(experience_score * 100, 1)}%."
        )
    if education_score == 1:
        resume_strengths.append("The extracted education meets or exceeds the stated requirement.")
    if project_score is not None and project_score >= 0.6:
        resume_strengths.append(
            f"Extracted project content is relevant at {round(project_score * 100, 1)}%."
        )
    if relevant_sections:
        strongest_section = relevant_sections[0]
        if strongest_section["semantic_similarity"] >= 50:
            resume_strengths.append(
                f"{strongest_section['section']} is the strongest semantically relevant section."
            )

    if required_missing:
        areas_to_improve.append(
            "Required skills not evidenced in the resume: "
            + ", ".join(item["skill"] for item in required_missing)
            + ". Include them only when supported by real experience."
        )
    if partial_required:
        areas_to_improve.append(
            "Clarify the context and depth of experience for partially matched required skills: "
            + ", ".join(partial_required)
            + "."
        )
    if experience_score is not None and experience_score < 0.6:
        areas_to_improve.append(
            f"Experience evidence aligns at {round(experience_score * 100, 1)}%; clarify relevant responsibilities and scope."
        )
    if education_score == 0:
        areas_to_improve.append(
            "The extracted education does not meet the stated level; verify the extraction and list relevant completed education accurately."
        )
    if project_score is not None and project_score < 0.5:
        areas_to_improve.append(
            "Project content has limited relevance to this role; clarify your contribution and methods where accurate."
        )
    if not areas_to_improve and preferred_missing:
        areas_to_improve.append(
            "Preferred skills not evidenced in the resume: "
            + ", ".join(item["skill"] for item in preferred_missing)
            + ". Address them only if they reflect genuine experience."
        )

    details = {
        "required_skills_match_percentage": round(required_percent, 1)
        if required_percent is not None
        else None,
        "keyword_match_percentage": round(tfidf_score * 100, 1),
        "experience_relevance_percentage": round(experience_score * 100, 1)
        if experience_score is not None
        else None,
        "education_relevance_percentage": round(education_score * 100, 1)
        if education_score is not None
        else None,
        "project_relevance_percentage": round(project_score * 100, 1)
        if project_score is not None
        else None,
        "semantic_similarity_percentage": round(semantic_score * 100, 1),
        "experience_semantic_similarity_percentage": round(experience_semantic * 100, 1)
        if experience_semantic is not None
        else None,
        "project_semantic_similarity_percentage": round(project_semantic * 100, 1)
        if project_semantic is not None
        else None,
        "matched_skills": matched,
        "partially_matched_skills": [item for item in matched if item["match_type"] == "partial"],
        "matched_keywords": matched_keywords,
        "missing_required_skills": required_missing,
        "missing_preferred_skills": preferred_missing,
        "missing_skills": missing,
        "important_missing_keywords": missing_keywords,
        "resume_strengths": resume_strengths,
        "areas_to_improve": areas_to_improve,
        "relevant_sections": relevant_sections,
        "improvement_suggestions": improvements,
        "skills_to_learn": learn,
        "section_feedback": section_feedback,
        "experience_years_detected": resume_years,
        "experience_years_required": required_years,
        "education_detected": resume_data.get("education_level"),
        "education_required": job_data.get("education_level"),
        "scoring_note": (
            "Unavailable or unreliable evidence is excluded and remaining configured weights "
            "are normalized. Keyword match uses TF-IDF cosine similarity; semantic similarity "
            "is reported separately and used for section relevance."
        ),
    }
    return {
        "overall_score": round(max(0.0, min(overall_score, 100.0)), 1),
        "breakdown": breakdown,
        "details": details,
    }