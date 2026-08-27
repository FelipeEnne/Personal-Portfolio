#!/usr/bin/env python3
"""Build a deterministic job-specific resume context from canonical career data."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator, RefResolver
except ImportError:  # pragma: no cover - depends on the execution environment
    print(
        "Error: jsonschema is required. Install dependencies with "
        "'python3 -m pip install -r resume/requirements.txt'.",
        file=sys.stderr,
    )
    raise SystemExit(2)

try:
    from resume.scripts import build_context as base
except ModuleNotFoundError:  # Direct script execution from resume/scripts/.
    import build_context as base  # type: ignore[no-redef]


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CAREER_DIR = REPOSITORY_ROOT / "career"
JOBS_OUTPUT_DIR = REPOSITORY_ROOT / "generated" / "resumes" / "jobs"
BASE_SCHEMA_PATH = REPOSITORY_ROOT / "resume/schema/resume-context.schema.json"
JOB_SCHEMA_PATH = REPOSITORY_ROOT / "resume/schema/job-resume-context.schema.json"

MAX_JOB_FILE_BYTES = 1_000_000
MAX_SKILLS = 14
MAX_SUPPORTING_SKILLS = 3
MAX_EXPERIENCES = 6
MAX_PROJECTS = 3
MAX_EDUCATION = 2
MAX_RELEVANT_HIGHLIGHTS = 2
MAX_GENERAL_HIGHLIGHTS = 1
MAX_PROJECT_HIGHLIGHTS = 2

# Presentation-only matching aliases. Canonical labels remain unchanged.
TECHNOLOGY_ALIASES = {
    "JavaScript": ("JS",),
    "TypeScript": ("TS",),
    "Node.js": ("Node", "NodeJS", "Node JS"),
    "PostgreSQL": ("Postgres", "Postgre SQL"),
    "Apache Spark": ("Spark",),
    "REST APIs": ("REST", "REST API", "RESTful", "RESTful API", "RESTful APIs"),
    "Databricks": ("DataBricks",),
    "HTML5": ("HTML",),
    "CSS3": ("CSS",),
    "pytest": ("automated testing", "automated tests", "testes automatizados"),
    "GitHub Actions": (
        "CI/CD", "continuous integration", "continuous delivery",
        "integração contínua", "entrega contínua",
    ),
}

KEYWORD_ALIASES = {
    "API integrations": (
        "api", "apis", "rest api", "restful", "api integration",
        "api integrations", "integrações de api",
    ),
    "automation": ("automation", "automação", "automations", "automações"),
    "backend": ("backend", "back-end"),
    "data engineering": ("data engineering", "engenharia de dados"),
    "data pipelines": ("data pipeline", "data pipelines", "pipelines de dados"),
    "frontend": ("frontend", "front-end"),
    "production support": ("production support", "suporte à produção"),
    "testing": ("testing", "tests", "testes"),
    "CI/CD": (
        "CI/CD", "continuous integration", "continuous delivery",
        "integração contínua", "entrega contínua",
    ),
}

SECTION_HEADINGS = {
    "responsibilities": {
        "responsibilities", "responsibility", "responsabilidades",
        "what you will do", "atividades",
    },
    "required": {
        "requirements", "required", "mandatory requirements", "requisitos",
        "requisitos obrigatórios", "qualifications", "habilidades",
    },
    "preferred": {
        "preferred", "nice to have", "desired", "desejável", "desejáveis",
        "diferenciais", "valorizado",
    },
}

SECTION_BOUNDARIES = {
    "about the job", "descrição", "description", "pacote de benefícios",
    "benefícios", "benefits", "informações importantes", "important information",
    "por que você deve vir pra cá", "why join us",
}

JOB_TITLE_TERMS = (
    "developer", "desenvolvedor", "engenheiro de software", "software engineer",
    "data engineer", "engenheiro de dados", "data analyst", "analista de dados",
)

GENERIC_PROJECT_SKILLS = {"Git", "GitHub"}

PROJECT_SIGNAL_BOOSTS = {
    "github-activity-lakehouse": (
        "Python", "Docker", "automated testing", "testes automatizados",
        "CI/CD", "continuous integration", "GitHub Actions",
    ),
    "audiobook-production-automation": (
        "Python", "API", "APIs", "backend", "back-end", "FastAPI",
    ),
}

STOP_WORDS = {
    "about", "after", "also", "and", "com", "como", "das", "dos", "for",
    "from", "have", "para", "that", "the", "this", "uma", "using", "with",
    "you", "your", "mais", "pela", "pelo", "ser", "will",
}


class JobContextError(ValueError):
    """Raised when a safe job-specific context cannot be built."""


def fold(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    without_marks = "".join(
        char for char in normalized if not unicodedata.combining(char)
    )
    return without_marks.lower()


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", fold(value)).strip("-")
    if not slug:
        raise JobContextError("job filename must produce a non-empty slug")
    return slug


def phrase_pattern(phrase: str) -> re.Pattern[str]:
    escaped = re.escape(fold(phrase)).replace(r"\ ", r"\s+")
    return re.compile(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])")


def phrase_position(text: str, phrase: str) -> int | None:
    match = phrase_pattern(phrase).search(fold(text))
    return match.start() if match else None


def text_tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9+#.]+", fold(text))
        if len(token) > 2 and token not in STOP_WORDS
    }


def canonical_skill_groups(profile_file: dict[str, Any]) -> dict[str, list[str]]:
    groups = base.require_mapping(profile_file.get("skills"), "profile.yaml.skills")
    return {
        group: base.string_list(values, f"profile.yaml.skills.{group}")
        for group, values in groups.items()
    }


def alias_phrases(skill: str) -> tuple[str, ...]:
    return (skill, *TECHNOLOGY_ALIASES.get(skill, ()))


def match_skills(text: str, groups: dict[str, list[str]]) -> list[str]:
    positions = []
    inventory_index = 0
    for skills in groups.values():
        for skill in skills:
            matches = [
                position
                for phrase in alias_phrases(skill)
                if (position := phrase_position(text, phrase)) is not None
            ]
            if matches:
                positions.append((min(matches), inventory_index, skill))
            inventory_index += 1
    return [skill for _, _, skill in sorted(positions)]


def canonicalize_term(term: str, inventory: list[str]) -> str | None:
    for skill in inventory:
        if fold(term) == fold(skill):
            return skill
        if any(
            fold(term) == fold(alias)
            for alias in TECHNOLOGY_ALIASES.get(skill, ())
        ):
            return skill
    return None


def record_skill_values(record: dict[str, Any], fields: tuple[str, ...]) -> list[str]:
    result = []
    for field in fields:
        values = record.get(field, [])
        if isinstance(values, list):
            result.extend(value for value in values if isinstance(value, str))
    return result


def record_ids_for_skill(
    records: list[dict[str, Any]],
    fields: tuple[str, ...],
    skill: str,
    inventory: list[str],
) -> list[str]:
    result = []
    for record in records:
        if any(
            canonicalize_term(value, inventory) == skill
            for value in record_skill_values(record, fields)
        ):
            result.append(base.require_string(record.get("id"), f"{fields}[].id"))
    return result


def skill_evidence(
    skill: str,
    canonical: dict[str, dict[str, Any]],
    inventory: list[str],
) -> dict[str, Any]:
    sources = (
        (
            "professional",
            record_ids_for_skill(
                base.require_list(
                    canonical["experiences"].get("experiences"), "experiences"
                ),
                ("technologies",),
                skill,
                inventory,
            ),
        ),
        (
            "project",
            record_ids_for_skill(
                base.require_list(canonical["projects"].get("projects"), "projects"),
                ("technologies", "concepts"),
                skill,
                inventory,
            ),
        ),
        (
            "education",
            record_ids_for_skill(
                base.require_list(
                    canonical["education"].get("education"), "education"
                ),
                ("topics",),
                skill,
                inventory,
            ),
        ),
        (
            "study",
            record_ids_for_skill(
                base.require_list(
                    canonical["certifications"].get("certifications"),
                    "certifications",
                ),
                ("skills",),
                skill,
                inventory,
            ),
        ),
    )
    for level, source_ids in sources:
        if source_ids:
            return {"skill": skill, "level": level, "source_ids": source_ids}
    return {"skill": skill, "level": "profile", "source_ids": []}


def parse_labeled_value(line: str, labels: tuple[str, ...]) -> str | None:
    for label in labels:
        match = re.match(rf"^{re.escape(label)}\s*:\s*(.+)$", line, re.IGNORECASE)
        if match:
            return match.group(1).strip() or None
    return None


def clean_list_item(line: str) -> str:
    return re.sub(r"^(?:[-*•]|\d+[.)])\s*", "", line.strip()).strip()


def normalized_heading(line: str) -> str:
    without_markup = re.sub(r"^[\s>#]+", "", line).strip()
    return fold(without_markup.rstrip(":").strip())


def inferred_leading_title(lines: list[str]) -> str | None:
    if not lines:
        return None
    candidate = clean_list_item(lines[0])
    if ":" in candidate or len(candidate) > 120:
        return None
    normalized = fold(candidate)
    if any(term in normalized for term in JOB_TITLE_TERMS):
        return candidate
    return None


def requirement_key(value: str) -> str:
    normalized = fold(value).strip()
    compact = re.sub(r"[^a-z0-9/+.-]+", " ", normalized).strip()
    if compact in {"back-end", "backend", "back end"}:
        return "backend"
    if compact in {"rest", "rest api", "rest apis", "restful", "restful api"}:
        return "rest-apis"
    return compact


def deduplicate_requirements(values: list[str]) -> list[str]:
    result = []
    seen = set()
    for value in values:
        key = requirement_key(value)
        if key and key not in seen:
            result.append(value)
            seen.add(key)
    return result


def analyze_job(
    text: str,
    source_file: str,
    slug: str,
    groups: dict[str, list[str]],
    canonical: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    nonempty_lines = [line.strip() for line in text.splitlines() if line.strip()]
    title = inferred_leading_title(nonempty_lines)
    company = None
    sections: dict[str, list[str]] = {
        "responsibilities": [], "required": [], "preferred": []
    }
    current_section = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        title = title or parse_labeled_value(line, ("Title", "Job title", "Cargo"))
        company = company or parse_labeled_value(line, ("Company", "Empresa"))
        heading_name = normalized_heading(line)
        heading = next(
            (
                name
                for name, aliases in SECTION_HEADINGS.items()
                if heading_name in {fold(alias) for alias in aliases}
            ),
            None,
        )
        if heading:
            current_section = heading
            continue
        if heading_name in {fold(value) for value in SECTION_BOUNDARIES}:
            current_section = None
            continue
        if current_section and not parse_labeled_value(
            line, ("Title", "Job title", "Cargo", "Company", "Empresa")
        ):
            item = clean_list_item(line)
            if item:
                sections[current_section].append(item)

    sections = {
        name: deduplicate_requirements(values)
        for name, values in sections.items()
    }

    matched = match_skills(text, groups)
    inventory = [skill for skills in groups.values() for skill in skills]
    evidence = [skill_evidence(skill, canonical, inventory) for skill in matched]
    evidence_order = {
        "professional": 1, "project": 2, "education": 3, "study": 4, "profile": 5
    }
    job_positions = {skill: index for index, skill in enumerate(matched)}
    evidence.sort(
        key=lambda item: (
            evidence_order[item["level"]], job_positions[item["skill"]]
        )
    )
    matched = [item["skill"] for item in evidence]

    keywords = []
    for keyword, aliases in KEYWORD_ALIASES.items():
        if any(phrase_position(text, alias) is not None for alias in aliases):
            keywords.append(keyword)

    return {
        "source_file": source_file,
        "slug": slug,
        "company": company,
        "title": title,
        "matched_skills": matched,
        "matched_skill_evidence": evidence,
        "responsibilities": sections["responsibilities"],
        "required": sections["required"],
        "preferred": sections["preferred"],
        "keywords": keywords,
    }


def localized_record_text(record: dict[str, Any]) -> str:
    values = []
    for field in ("description", "highlights"):
        value = record.get(field)
        if isinstance(value, dict):
            for localized in value.values():
                if isinstance(localized, str):
                    values.append(localized)
                elif isinstance(localized, list):
                    values.extend(item for item in localized if isinstance(item, str))
    return " ".join(values)


def relevance_score(
    record: dict[str, Any],
    matched: set[str],
    job_tokens: set[str],
    inventory: list[str],
) -> int:
    record_skills = {
        canonical
        for value in record_skill_values(record, ("technologies", "concepts"))
        if (canonical := canonicalize_term(value, inventory)) is not None
    }
    technology_matches = len(matched & record_skills)
    overlap = len(text_tokens(localized_record_text(record)) & job_tokens)
    return technology_matches * 100 + min(overlap, 20)


def select_experiences(
    records: list[dict[str, Any]],
    matched: set[str],
    job_tokens: set[str],
    inventory: list[str],
) -> list[dict[str, Any]]:
    scored = [
        (relevance_score(record, matched, job_tokens, inventory), index, record)
        for index, record in enumerate(records)
    ]
    chosen = sorted(scored, key=lambda item: (-item[0], item[1]))[:MAX_EXPERIENCES]
    return [record for _, _, record in sorted(chosen, key=lambda item: item[1])]


def select_projects(
    records: list[dict[str, Any]],
    matched: set[str],
    job_tokens: set[str],
    inventory: list[str],
    job_text: str,
) -> list[dict[str, Any]]:
    scored = []
    for index, record in enumerate(records):
        record_values = record_skill_values(record, ("technologies", "concepts"))
        record_skills = {
            canonical
            for value in record_values
            if (canonical := canonicalize_term(value, inventory)) is not None
        }
        matched_record_skills = matched & record_skills
        skill_score = sum(
            10 if skill in GENERIC_PROJECT_SKILLS else 100
            for skill in matched_record_skills
        )
        direct_score = sum(
            40
            for value in record_values
            if canonicalize_term(value, inventory) is None
            and phrase_position(job_text, value) is not None
        )
        overlap = len(text_tokens(localized_record_text(record)) & job_tokens)
        signals = PROJECT_SIGNAL_BOOSTS.get(record.get("id"), ())
        signal_score = sum(
            25 for signal in signals if phrase_position(job_text, signal) is not None
        )
        score = skill_score + direct_score + min(overlap, 20) + signal_score
        if matched_record_skills and matched_record_skills <= GENERIC_PROJECT_SKILLS:
            score = min(score, 30)
        featured = bool(record.get("featured"))
        scored.append((score, featured, index, record))
    scored.sort(key=lambda item: (-item[0], -int(item[1]), item[2]))
    selected = scored[: min(2, len(scored))]
    if len(scored) > 2:
        third = scored[2]
        highest_score = scored[0][0]
        if third[0] >= 80 and third[0] >= highest_score * 0.6:
            selected.append(third)
    return [record for _, _, _, record in selected[:MAX_PROJECTS]]


def select_education(
    records: list[dict[str, Any]], matched: set[str], job_tokens: set[str]
) -> list[dict[str, Any]]:
    scored = []
    for index, record in enumerate(records):
        topic_matches = len(
            matched.intersection(
                value for value in record.get("topics", []) if isinstance(value, str)
            )
        )
        overlap = len(text_tokens(localized_record_text(record)) & job_tokens)
        scored.append((topic_matches * 100 + overlap, index, record))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [record for _, _, record in scored[:MAX_EDUCATION]]


def highlight_score(
    highlight: str,
    matched_skills: list[str],
    analysis: dict[str, Any],
    job_tokens: set[str],
) -> int:
    """Score an existing canonical highlight against explicit job signals.

    Technology matches are intentionally dominant.  The remaining token and
    section overlap is only a tie-breaker, so generic language cannot outrank
    a highlight that demonstrates a requested technology.
    """
    score = 0
    for skill in matched_skills:
        if any(phrase_position(highlight, phrase) is not None
               for phrase in alias_phrases(skill)):
            score += 100

    for keyword in analysis.get("keywords", []):
        aliases = KEYWORD_ALIASES.get(keyword, (keyword,))
        if any(phrase_position(highlight, phrase) is not None for phrase in aliases):
            score += 30

    # Responsibilities/requirements provide useful context, but are weaker
    # evidence than an explicit technology or normalized concept.
    section_tokens = text_tokens(" ".join(
        (*analysis.get("responsibilities", []),
         *analysis.get("required", []),
         *analysis.get("preferred", []))
    ))
    score += min(len(text_tokens(highlight) & (job_tokens | section_tokens)), 10)
    return score


def rank_highlights(
    highlights: list[str],
    job_tokens: set[str],
    limit: int,
    matched_skills: list[str] | None = None,
    analysis: dict[str, Any] | None = None,
) -> list[str]:
    # Optional arguments preserve the small helper's existing call contract.
    matched_skills = matched_skills or []
    analysis = analysis or {}
    scored = [
        (highlight_score(highlight, matched_skills, analysis, job_tokens), index, highlight)
        for index, highlight in enumerate(highlights)
    ]
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [highlight for _, _, highlight in scored[:limit]]


def filter_skill_groups(
    groups: dict[str, list[str]],
    matched_skills: list[str],
    selected_experiences: list[dict[str, Any]],
    keywords: list[str],
) -> list[dict[str, Any]]:
    canonical_order = [skill for values in groups.values() for skill in values]
    allowed_support_groups = {"languages", "backend", "databases"}
    if "backend" in keywords or "API integrations" in keywords:
        allowed_support_groups.update(
            {"testing", "devops", "integrations"}
        )
    if "data engineering" in keywords or "data pipelines" in keywords:
        allowed_support_groups.update(
            {"data_engineering", "data_visualization", "testing", "devops"}
        )
    if "frontend" in keywords:
        allowed_support_groups.update({"frontend", "testing", "devops"})

    skill_groups = {
        skill: group for group, values in groups.items() for skill in values
    }
    inventory = list(canonical_order)
    frequency = {skill: 0 for skill in canonical_order}
    for experience in selected_experiences:
        for value in record_skill_values(experience, ("technologies",)):
            canonical = canonicalize_term(value, inventory)
            if canonical is not None:
                frequency[canonical] += 1
    inventory_positions = {
        skill: index for index, skill in enumerate(canonical_order)
    }
    supporting = sorted(
        (
            skill
            for skill in canonical_order
            if skill not in matched_skills
            and frequency[skill] > 0
            and skill_groups[skill] in allowed_support_groups
        ),
        key=lambda skill: (-frequency[skill], inventory_positions[skill]),
    )[:MAX_SUPPORTING_SKILLS]
    selected = list(dict.fromkeys((*matched_skills, *supporting)))[:MAX_SKILLS]
    matched_skills = [skill for skill in matched_skills if skill in selected]
    supporting = [skill for skill in supporting if skill in selected]
    result = []
    matched_positions = {skill: index for index, skill in enumerate(matched_skills)}
    ordered_groups = sorted(
        groups.items(),
        key=lambda item: min(
            (
                matched_positions[skill]
                for skill in item[1]
                if skill in matched_positions
            ),
            default=len(matched_skills) + list(groups).index(item[0]),
        ),
    )
    for group, values in ordered_groups:
        items = [skill for skill in matched_skills if skill in values]
        items.extend(skill for skill in values if skill in supporting)
        if items:
            result.append({"id": group, "items": items})
    return result


def build_job_context(
    canonical: dict[str, dict[str, Any]],
    job_text: str,
    source_file: str,
    slug: str,
    language: str,
) -> dict[str, Any]:
    groups = canonical_skill_groups(canonical["profile"])
    inventory = [skill for values in groups.values() for skill in values]
    analysis = analyze_job(job_text, source_file, slug, groups, canonical)
    matched = set(analysis["matched_skills"])
    job_tokens = text_tokens(job_text)

    experiences = base.validate_unique_ids(
        base.require_list(canonical["experiences"].get("experiences"), "experiences"),
        "experiences",
    )
    projects = base.validate_unique_ids(
        base.require_list(canonical["projects"].get("projects"), "projects"),
        "projects",
    )
    education = base.validate_unique_ids(
        base.require_list(canonical["education"].get("education"), "education"),
        "education",
    )
    selected_experiences = select_experiences(
        experiences, matched, job_tokens, inventory
    )
    selected_projects = select_projects(
        projects, matched, job_tokens, inventory, job_text
    )
    selected_education = select_education(education, matched, job_tokens)

    policy = {
        "experiences": {
            "include": [record["id"] for record in selected_experiences],
            "exclude": [],
            "max_highlights": {
                record["id"]: max(
                    1, len(record.get("highlights", {}).get(language, []))
                )
                for record in selected_experiences
            },
        },
        "education": {
            "include": [record["id"] for record in selected_education],
            "exclude": [],
        },
        "projects": {
            "include": [record["id"] for record in selected_projects],
            "max_highlights_per_project": max(
                1,
                max(
                    (
                        len(record.get("highlights", {}).get(language, []))
                        for record in selected_projects
                    ),
                    default=1,
                ),
            ),
        },
        "skills": {"include_groups": list(groups), "exclude_groups": []},
        "certifications": {"include_resume_eligible_only": True},
    }
    context = base.build_context(canonical, policy, language)
    context["skills"] = filter_skill_groups(
        groups,
        analysis["matched_skills"],
        selected_experiences,
        analysis["keywords"],
    )

    experience_scores = {
        record["id"]: relevance_score(record, matched, job_tokens, inventory)
        for record in selected_experiences
    }
    for record in context["experiences"]:
        # Only an explicit matched technology makes an experience highly
        # relevant. Generic vocabulary overlap (for example, "data") is not
        # sufficient to spend a second highlight.
        limit = (
            MAX_RELEVANT_HIGHLIGHTS
            if experience_scores[record["id"]] >= 100
            else MAX_GENERAL_HIGHLIGHTS
        )
        record["highlights"] = rank_highlights(
            record["highlights"],
            job_tokens,
            limit,
            analysis["matched_skills"],
            analysis,
        )
    for record in context["projects"]:
        record["highlights"] = rank_highlights(
            record["highlights"],
            job_tokens,
            MAX_PROJECT_HIGHLIGHTS,
            analysis["matched_skills"],
            analysis,
        )

    context["job"] = analysis
    return context


def load_schemas() -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        base_schema = json.loads(BASE_SCHEMA_PATH.read_text(encoding="utf-8"))
        job_schema = json.loads(JOB_SCHEMA_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise JobContextError(f"invalid resume JSON schema: {error}") from error
    Draft202012Validator.check_schema(base_schema)
    Draft202012Validator.check_schema(job_schema)
    return base_schema, job_schema


def validate_job_context(context: dict[str, Any]) -> None:
    base_schema, job_schema = load_schemas()
    resolver = RefResolver.from_schema(
        job_schema, store={base_schema["$id"]: base_schema}
    )
    validator = Draft202012Validator(job_schema, resolver=resolver)
    errors = sorted(validator.iter_errors(context), key=lambda error: list(error.path))
    if errors:
        details = []
        for error in errors:
            location = ".".join(str(part) for part in error.absolute_path) or "$"
            details.append(f"{location}: {error.message}")
        raise JobContextError(
            "job resume context failed schema validation: " + "; ".join(details)
        )


def ensure_jobs_output(output: Path, jobs_dir: Path = JOBS_OUTPUT_DIR) -> None:
    try:
        output.resolve().relative_to(jobs_dir.resolve())
    except ValueError as error:
        raise JobContextError(
            f"job-specific context output must stay under {jobs_dir}"
        ) from error


def write_job_context(
    context: dict[str, Any], output: Path, jobs_dir: Path = JOBS_OUTPUT_DIR
) -> None:
    ensure_jobs_output(output, jobs_dir)
    validate_job_context(context)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(context, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def source_display(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPOSITORY_ROOT.resolve()))
    except ValueError:
        return path.name


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a deterministic job-specific resume context."
    )
    parser.add_argument(
        "--job", required=True, type=Path, help="job description text file"
    )
    parser.add_argument("--lang", required=True, choices=("en", "pt"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    job_path = args.job.resolve()
    try:
        if not job_path.is_file():
            raise JobContextError(f"job description not found: {job_path}")
        if job_path.suffix.lower() != ".txt":
            raise JobContextError("job description must be a .txt file")
        if job_path.stat().st_size == 0:
            raise JobContextError("job description is empty")
        if job_path.stat().st_size > MAX_JOB_FILE_BYTES:
            raise JobContextError(
                f"job description exceeds {MAX_JOB_FILE_BYTES} bytes"
            )
        job_text = job_path.read_text(encoding="utf-8")
        slug = slugify(job_path.stem)
        canonical = base.load_yaml_files(CAREER_DIR)
        context = build_job_context(
            canonical, job_text, source_display(job_path), slug, args.lang
        )
        output = JOBS_OUTPUT_DIR / slug / f"resume-context-{args.lang}.json"
        write_job_context(context, output)
    except (base.CareerDataError, JobContextError, OSError, UnicodeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    print(f"Job-specific resume context written to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
