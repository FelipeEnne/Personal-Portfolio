#!/usr/bin/env python3
"""Build a format-independent resume context from canonical career YAML."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - depends on the execution environment
    print(
        "Error: PyYAML is required. Install it with "
        "'python -m pip install PyYAML'.",
        file=sys.stderr,
    )
    raise SystemExit(2)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CAREER_DIR = REPOSITORY_ROOT / "career"
DEFAULT_OUTPUT_DIR = REPOSITORY_ROOT / "generated" / "resumes"
DEFAULT_CONFIG_PATH = REPOSITORY_ROOT / "resume" / "config" / "default.yaml"

CANONICAL_FILES = {
    "profile": "profile.yaml",
    "experiences": "experience.yaml",
    "education": "education.yaml",
    "projects": "projects.yaml",
    "certifications": "certifications.yaml",
}


class CareerDataError(ValueError):
    """Raised when canonical career data is missing or structurally invalid."""


def require_mapping(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CareerDataError(f"{path} must be a mapping")
    return value


def require_list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise CareerDataError(f"{path} must be a list")
    return value


def require_string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CareerDataError(f"{path} must be a non-empty string")
    return value


def require_boolean(value: Any, path: str) -> bool:
    if not isinstance(value, bool):
        raise CareerDataError(f"{path} must be a boolean")
    return value


def optional_string(value: Any, path: str) -> str | None:
    if value is not None and not isinstance(value, str):
        raise CareerDataError(f"{path} must be a string or null")
    return value


def string_list(value: Any, path: str) -> list[str]:
    values = require_list(value, path)
    for index, item in enumerate(values):
        require_string(item, f"{path}[{index}]")
    return values


def localized_string(value: Any, language: str, path: str) -> str:
    translations = require_mapping(value, path)
    if language not in translations:
        raise CareerDataError(f"{path} is missing language '{language}'")
    return require_string(translations[language], f"{path}.{language}")


def localized_string_list(value: Any, language: str, path: str) -> list[str]:
    translations = require_mapping(value, path)
    if language not in translations:
        raise CareerDataError(f"{path} is missing language '{language}'")
    return string_list(translations[language], f"{path}.{language}")


def load_yaml_files(career_dir: Path) -> dict[str, dict[str, Any]]:
    if not career_dir.is_dir():
        raise CareerDataError(f"career directory not found: {career_dir}")

    parsed_by_path: dict[Path, dict[str, Any]] = {}
    yaml_paths = sorted((*career_dir.rglob("*.yaml"), *career_dir.rglob("*.yml")))
    if not yaml_paths:
        raise CareerDataError(f"no YAML files found below {career_dir}")

    for path in yaml_paths:
        try:
            with path.open(encoding="utf-8") as stream:
                parsed = yaml.safe_load(stream)
        except yaml.YAMLError as error:
            raise CareerDataError(f"invalid YAML in {path}: {error}") from error
        except OSError as error:
            raise CareerDataError(f"could not read {path}: {error}") from error
        parsed_by_path[path.resolve()] = require_mapping(parsed, str(path))

    canonical: dict[str, dict[str, Any]] = {}
    for key, filename in CANONICAL_FILES.items():
        path = (career_dir / filename).resolve()
        if path not in parsed_by_path:
            raise CareerDataError(f"required canonical file not found: {path}")
        canonical[key] = parsed_by_path[path]

    return canonical


def validate_unique_ids(records: list[Any], path: str) -> list[dict[str, Any]]:
    seen: set[str] = set()
    validated: list[dict[str, Any]] = []
    for index, value in enumerate(records):
        record_path = f"{path}[{index}]"
        record = require_mapping(value, record_path)
        canonical_id = require_string(record.get("id"), f"{record_path}.id")
        if canonical_id in seen:
            raise CareerDataError(f"duplicate id '{canonical_id}' in {path}")
        seen.add(canonical_id)
        validated.append(record)
    return validated


def id_list(value: Any, path: str) -> list[str]:
    values = require_list(value, path)
    result: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(values):
        canonical_id = require_string(item, f"{path}[{index}]")
        if canonical_id in seen:
            raise CareerDataError(f"duplicate id '{canonical_id}' in {path}")
        seen.add(canonical_id)
        result.append(canonical_id)
    return result


def select_records(
    records: list[dict[str, Any]], policy: Any, path: str
) -> list[dict[str, Any]]:
    selection = require_mapping(policy, path)
    include = id_list(selection.get("include"), f"{path}.include")
    exclude = id_list(selection.get("exclude", []), f"{path}.exclude")
    records_by_id = {record["id"]: record for record in records}
    configured_ids = set(include) | set(exclude)
    unknown = sorted(configured_ids - records_by_id.keys())
    if unknown:
        raise CareerDataError(
            f"{path} references unknown canonical IDs: {', '.join(unknown)}"
        )
    overlap = sorted(set(include) & set(exclude))
    if overlap:
        raise CareerDataError(
            f"{path} includes and excludes the same IDs: {', '.join(overlap)}"
        )
    return [records_by_id[canonical_id] for canonical_id in include]


def positive_integer(value: Any, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise CareerDataError(f"{path} must be a positive integer")
    return value


def build_experiences(
    data: Any, language: str, policy: Any
) -> list[dict[str, Any]]:
    all_records = validate_unique_ids(
        require_list(data, "experience.yaml.experiences"), "experiences"
    )
    selection = require_mapping(policy, "default_resume.experiences")
    records = select_records(all_records, selection, "default_resume.experiences")
    limits = require_mapping(
        selection.get("max_highlights"),
        "default_resume.experiences.max_highlights",
    )
    canonical_ids = {record["id"] for record in all_records}
    selected_ids = {record["id"] for record in records}
    unknown_limits = sorted(set(limits) - canonical_ids)
    if unknown_limits:
        raise CareerDataError(
            "default_resume.experiences.max_highlights references unknown "
            f"canonical IDs: {', '.join(unknown_limits)}"
        )
    unselected_limits = sorted(set(limits) - selected_ids)
    if unselected_limits:
        raise CareerDataError(
            "default_resume.experiences.max_highlights contains IDs not selected "
            f"by include: {', '.join(unselected_limits)}"
        )
    result = []
    for index, record in enumerate(records):
        path = f"experiences[{index}]"
        record_id = require_string(record.get("id"), f"{path}.id")
        if record_id not in limits:
            raise CareerDataError(
                "default_resume.experiences.max_highlights is missing selected "
                f"ID '{record_id}'"
            )
        highlight_limit = positive_integer(
            limits[record_id],
            f"default_resume.experiences.max_highlights.{record_id}",
        )
        result.append(
            {
                "id": record_id,
                "role": localized_string(
                    record.get("role"), language, f"{path}.role"
                ),
                "company": require_string(record.get("company"), f"{path}.company"),
                "employment_type": optional_string(record.get("employment_type"), f"{path}.employment_type"),
                "location": optional_string(record.get("location"), f"{path}.location"),
                "start_date": require_string(record.get("start_date"), f"{path}.start_date"),
                "end_date": optional_string(record.get("end_date"), f"{path}.end_date"),
                "current": require_boolean(record.get("current"), f"{path}.current"),
                "technologies": string_list(record.get("technologies"), f"{path}.technologies"),
                "highlights": localized_string_list(
                    record.get("highlights"), language, f"{path}.highlights"
                )[:highlight_limit],
            }
        )
    return result


def build_education(data: Any, language: str, policy: Any) -> list[dict[str, Any]]:
    all_records = validate_unique_ids(
        require_list(data, "education.yaml.education"), "education"
    )
    records = select_records(all_records, policy, "default_resume.education")
    result = []
    for index, record in enumerate(records):
        path = f"education[{index}]"
        result.append(
            {
                "id": require_string(record.get("id"), f"{path}.id"),
                "institution": require_string(record.get("institution"), f"{path}.institution"),
                "institution_short": optional_string(record.get("institution_short"), f"{path}.institution_short"),
                "degree": localized_string(record.get("degree"), language, f"{path}.degree"),
                "field": localized_string(record.get("field"), language, f"{path}.field"),
                "level": optional_string(record.get("level"), f"{path}.level"),
                "start_date": require_string(record.get("start_date"), f"{path}.start_date"),
                "end_date": optional_string(record.get("end_date"), f"{path}.end_date"),
                "location": optional_string(record.get("location"), f"{path}.location"),
                "description": localized_string(record.get("description"), language, f"{path}.description"),
                "topics": string_list(record.get("topics"), f"{path}.topics"),
            }
        )
    return result


def build_projects(data: Any, language: str, policy: Any) -> list[dict[str, Any]]:
    all_records = validate_unique_ids(
        require_list(data, "projects.yaml.projects"), "projects"
    )
    selection = require_mapping(policy, "default_resume.projects")
    records = select_records(all_records, selection, "default_resume.projects")
    highlight_limit = positive_integer(
        selection.get("max_highlights_per_project"),
        "default_resume.projects.max_highlights_per_project",
    )
    result = []
    for index, record in enumerate(records):
        path = f"projects[{index}]"
        featured = require_boolean(record.get("featured"), f"{path}.featured")
        links = require_mapping(record.get("links"), f"{path}.links")
        evidence = require_mapping(record.get("skill_evidence"), f"{path}.skill_evidence")
        result.append(
            {
                "id": require_string(record.get("id"), f"{path}.id"),
                "name": require_string(record.get("name"), f"{path}.name"),
                "type": optional_string(record.get("type"), f"{path}.type"),
                "status": optional_string(record.get("status"), f"{path}.status"),
                "featured": featured,
                "description": localized_string(record.get("description"), language, f"{path}.description"),
                "technologies": string_list(record.get("technologies"), f"{path}.technologies"),
                "concepts": string_list(record.get("concepts"), f"{path}.concepts"),
                "highlights": localized_string_list(
                    record.get("highlights"), language, f"{path}.highlights"
                )[:highlight_limit],
                "links": {
                    "github": optional_string(links.get("github"), f"{path}.links.github"),
                    "demo": optional_string(links.get("demo"), f"{path}.links.demo"),
                },
                "skill_evidence": {
                    "professional": require_boolean(evidence.get("professional"), f"{path}.skill_evidence.professional"),
                    "project_based": require_boolean(evidence.get("project_based"), f"{path}.skill_evidence.project_based"),
                },
            }
        )
    return result


def build_certifications(data: Any, policy: Any) -> list[dict[str, Any]]:
    selection = require_mapping(policy, "default_resume.certifications")
    eligible_only = require_boolean(
        selection.get("include_resume_eligible_only"),
        "default_resume.certifications.include_resume_eligible_only",
    )
    if not eligible_only:
        raise CareerDataError(
            "default_resume.certifications.include_resume_eligible_only must be "
            "true; ineligible course certificates cannot enter a resume"
        )
    records = validate_unique_ids(
        require_list(data, "certifications.yaml.certifications"), "certifications"
    )
    result = []
    for index, record in enumerate(records):
        path = f"certifications[{index}]"
        eligible = require_boolean(record.get("resume_eligible"), f"{path}.resume_eligible")
        if not eligible:
            continue
        result.append(
            {
                "id": require_string(record.get("id"), f"{path}.id"),
                "name": require_string(record.get("name"), f"{path}.name"),
                "issuer": require_string(record.get("issuer"), f"{path}.issuer"),
                "category": optional_string(record.get("category"), f"{path}.category"),
                "skills": string_list(record.get("skills"), f"{path}.skills"),
                "level": optional_string(record.get("level"), f"{path}.level"),
                "issue_date": optional_string(record.get("issue_date"), f"{path}.issue_date"),
                "expiration_date": optional_string(record.get("expiration_date"), f"{path}.expiration_date"),
                "credential_url": optional_string(record.get("credential_url"), f"{path}.credential_url"),
                "featured": require_boolean(record.get("featured"), f"{path}.featured"),
                "resume_eligible": eligible,
            }
        )
    return result


def build_context(
    canonical: dict[str, dict[str, Any]], policy: Any, language: str
) -> dict[str, Any]:
    default_policy = require_mapping(policy, "default_resume")
    profile_file = canonical["profile"]
    profile = require_mapping(profile_file.get("profile"), "profile.yaml.profile")
    contact = require_mapping(profile.get("contact"), "profile.yaml.profile.contact")
    links = require_mapping(profile.get("links"), "profile.yaml.profile.links")
    skills = require_mapping(profile_file.get("skills"), "profile.yaml.skills")

    skill_policy = require_mapping(
        default_policy.get("skills"), "default_resume.skills"
    )
    included_skill_groups = id_list(
        skill_policy.get("include_groups"), "default_resume.skills.include_groups"
    )
    excluded_skill_groups = id_list(
        skill_policy.get("exclude_groups", []),
        "default_resume.skills.exclude_groups",
    )
    unknown_skill_groups = sorted(
        (set(included_skill_groups) | set(excluded_skill_groups)) - skills.keys()
    )
    if unknown_skill_groups:
        raise CareerDataError(
            "default_resume.skills references unknown canonical groups: "
            + ", ".join(unknown_skill_groups)
        )
    overlap = sorted(set(included_skill_groups) & set(excluded_skill_groups))
    if overlap:
        raise CareerDataError(
            "default_resume.skills includes and excludes the same groups: "
            + ", ".join(overlap)
        )

    skill_groups = []
    for category in included_skill_groups:
        values = skills[category]
        skill_groups.append(
            {"id": category, "items": string_list(values, f"profile.yaml.skills.{category}")}
        )

    return {
        "language": language,
        "candidate": {
            "name": require_string(profile.get("name"), "profile.yaml.profile.name"),
            "location": optional_string(profile.get("location"), "profile.yaml.profile.location"),
        },
        "title": localized_string(profile.get("title"), language, "profile.yaml.profile.title"),
        "contact": {
            "email": optional_string(contact.get("email"), "profile.yaml.profile.contact.email"),
            "phone": optional_string(contact.get("phone"), "profile.yaml.profile.contact.phone"),
        },
        "links": {
            "github": optional_string(links.get("github"), "profile.yaml.profile.links.github"),
            "linkedin": optional_string(links.get("linkedin"), "profile.yaml.profile.links.linkedin"),
            "medium": optional_string(links.get("medium"), "profile.yaml.profile.links.medium"),
            "portfolio": optional_string(links.get("portfolio"), "profile.yaml.profile.links.portfolio"),
        },
        "summary": localized_string(profile.get("summary"), language, "profile.yaml.profile.summary"),
        "skills": skill_groups,
        "experiences": build_experiences(
            canonical["experiences"].get("experiences"),
            language,
            default_policy.get("experiences"),
        ),
        "education": build_education(
            canonical["education"].get("education"),
            language,
            default_policy.get("education"),
        ),
        "projects": build_projects(
            canonical["projects"].get("projects"),
            language,
            default_policy.get("projects"),
        ),
        "certifications": build_certifications(
            canonical["certifications"].get("certifications"),
            default_policy.get("certifications"),
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a resume context from canonical career YAML files."
    )
    parser.add_argument("--lang", required=True, choices=("en", "pt"), help="context language")
    parser.add_argument(
        "--output",
        type=Path,
        help="output JSON path (defaults to generated/resumes/resume-context-<lang>.json)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = args.output or DEFAULT_OUTPUT_DIR / f"resume-context-{args.lang}.json"
    if not output.is_absolute():
        output = Path.cwd() / output

    try:
        canonical = load_yaml_files(CAREER_DIR)
        try:
            with DEFAULT_CONFIG_PATH.open(encoding="utf-8") as stream:
                config = yaml.safe_load(stream)
        except yaml.YAMLError as error:
            raise CareerDataError(
                f"invalid YAML in {DEFAULT_CONFIG_PATH}: {error}"
            ) from error
        config_data = require_mapping(config, str(DEFAULT_CONFIG_PATH))
        context = build_context(canonical, config_data.get("default_resume"), args.lang)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(context, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except (CareerDataError, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    print(f"Resume context written to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
