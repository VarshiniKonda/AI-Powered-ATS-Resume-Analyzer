"""Canonical skill vocabulary and context-aware skill extraction."""

import re
from dataclasses import dataclass


SKILL_ALIASES: dict[str, tuple[str, ...]] = {
    "Python": ("python",),
    "Java": ("java",),
    "C++": ("c++",),
    "C#": ("c#", "c sharp"),
    ".NET": (".net", "dotnet"),
    "Go": ("golang", "go language"),
    "Rust": ("rust",),
    "Ruby": ("ruby",),
    "PHP": ("php",),
    "Swift": ("swift",),
    "Kotlin": ("kotlin",),
    "JavaScript": ("javascript", "js"),
    "TypeScript": ("typescript", "ts"),
    "React": ("react",),
    "React Native": ("react native",),
    "Angular": ("angular",),
    "Vue.js": ("vue.js", "vuejs"),
    "Next.js": ("next.js", "nextjs", "next js"),
    "Express.js": ("express.js", "expressjs"),
    "Spring Boot": ("spring boot",),
    "SQLAlchemy": ("sqlalchemy",),
    "Node.js": ("node.js", "nodejs", "node"),
    "FastAPI": ("fastapi",),
    "Django": ("django",),
    "Flask": ("flask",),
    "SQL": ("sql", "structured query language"),
    "PostgreSQL": ("postgresql", "postgres"),
    "MySQL": ("mysql",),
    "SQLite": ("sqlite",),
    "MongoDB": ("mongodb", "mongo"),
    "Redis": ("redis",),
    "REST APIs": ("rest api", "rest apis", "restful api", "restful apis"),
    "GraphQL": ("graphql",),
    "AWS": ("aws", "amazon web services"),
    "Azure": ("azure", "microsoft azure"),
    "Google Cloud": ("google cloud", "gcp"),
    "Docker": ("docker",),
    "Kubernetes": ("kubernetes", "k8s"),
    "Terraform": ("terraform",),
    "Ansible": ("ansible",),
    "Jenkins": ("jenkins",),
    "GitHub Actions": ("github actions",),
    "Apache Kafka": ("apache kafka", "kafka"),
    "Apache Spark": ("apache spark", "spark"),
    "Apache Airflow": ("apache airflow", "airflow"),
    "Git": ("git", "github", "gitlab"),
    "CI/CD": ("ci/cd", "continuous integration", "continuous delivery"),
    "Linux": ("linux",),
    "HTML": ("html",),
    "CSS": ("css",),
    "Tailwind CSS": ("tailwind", "tailwind css"),
    "Machine Learning": ("machine learning", "ml"),
    "Deep Learning": ("deep learning",),
    "Natural Language Processing": ("natural language processing", "nlp"),
    "spaCy": ("spacy",),
    "NLTK": ("nltk",),
    "BERT": ("bert",),
    "Transformers": ("transformers", "transformer models"),
    "PyTorch": ("pytorch",),
    "TensorFlow": ("tensorflow",),
    "scikit-learn": ("scikit-learn", "scikit learn", "sklearn"),
    "Pandas": ("pandas",),
    "NumPy": ("numpy",),
    "Data Analysis": ("data analysis", "data analytics"),
    "Data Visualization": ("data visualization", "data visualisation"),
    "Statistics": ("statistics", "statistical analysis"),
    "Power BI": ("power bi",),
    "Tableau": ("tableau",),
    "Microsoft Excel": ("microsoft excel", "excel"),
    "Agile": ("agile",),
    "Scrum": ("scrum",),
    "Project Management": ("project management",),
    "Product Management": ("product management",),
    "Communication": ("communication", "written communication", "verbal communication"),
    "Leadership": ("leadership", "team leadership"),
    "Problem Solving": ("problem solving", "problem-solving"),
    "Customer Support": ("customer support", "customer service"),
    "Sales": ("sales",),
    "Marketing": ("marketing",),
    "SEO": ("seo", "search engine optimization", "search engine optimisation"),
    "Financial Modeling": ("financial modeling", "financial modelling"),
    "Accounting": ("accounting",),
    "Human Resources": ("human resources", "hr"),
}

_PATTERNS = {
    skill: re.compile(
        r"(?<![A-Za-z0-9])(?:"
        + "|".join(
            re.escape(alias).replace(r"\ ", r"\s+")
            for alias in sorted(aliases, key=len, reverse=True)
        )
        + r")(?![A-Za-z0-9])",
        flags=re.IGNORECASE,
    )
    for skill, aliases in SKILL_ALIASES.items()
}


@dataclass(frozen=True)
class SkillOccurrence:
    skill: str
    phrase: str
    start: int
    end: int
    context: str


def normalize_skill(value: str) -> str:
    """Map a supported alias to its canonical label; preserve user-entered skills."""
    clean = re.sub(r"\s+", " ", value.strip())
    lowered = clean.casefold()
    for canonical, aliases in SKILL_ALIASES.items():
        if lowered == canonical.casefold() or lowered in {alias.casefold() for alias in aliases}:
            return canonical
    return clean[:1].upper() + clean[1:]


def _context_for(text: str, start: int, end: int) -> str:
    left = max(text.rfind(".", 0, start), text.rfind(";", 0, start), text.rfind("\n", 0, start)) + 1
    stops = [stop for stop in (text.find(".", end), text.find(";", end), text.find("\n", end)) if stop >= 0]
    right = min(stops) + 1 if stops else min(len(text), end + 140)
    return re.sub(r"\s+", " ", text[left:right]).strip()


def extract_skill_occurrences(text: str) -> list[SkillOccurrence]:
    """Find canonical skills with their original mention and surrounding sentence."""
    candidates: list[SkillOccurrence] = []
    for skill, pattern in _PATTERNS.items():
        for match in pattern.finditer(text):
            candidates.append(
                SkillOccurrence(
                    skill=skill,
                    phrase=match.group(0),
                    start=match.start(),
                    end=match.end(),
                    context=_context_for(text, match.start(), match.end()),
                )
            )

    selected: list[SkillOccurrence] = []
    seen_skills: set[str] = set()
    for candidate in sorted(candidates, key=lambda item: (item.start, -(item.end - item.start))):
        if candidate.skill in seen_skills:
            continue
        if any(candidate.start < item.end and candidate.end > item.start for item in selected):
            continue
        selected.append(candidate)
        seen_skills.add(candidate.skill)
    return sorted(selected, key=lambda occurrence: occurrence.start)


def extract_skills(text: str) -> list[str]:
    return [occurrence.skill for occurrence in extract_skill_occurrences(text)]
