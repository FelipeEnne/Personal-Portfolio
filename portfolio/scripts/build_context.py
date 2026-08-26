#!/usr/bin/env python3
"""Build a public portfolio context from canonical career YAML."""

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
        "Error: PyYAML is required. Install dependencies with "
        "'python3 -m pip install -r portfolio/requirements.txt'.",
        file=sys.stderr,
    )
    raise SystemExit(2)

try:
    from jsonschema import Draft202012Validator
except ImportError:  # pragma: no cover - depends on the execution environment
    print(
        "Error: jsonschema is required. Install dependencies with "
        "'python3 -m pip install -r portfolio/requirements.txt'.",
        file=sys.stderr,
    )
    raise SystemExit(2)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CAREER_DIR = REPOSITORY_ROOT / "career"
CONFIG_PATH = REPOSITORY_ROOT / "portfolio" / "config" / "default.yaml"
SCHEMA_PATH = (
    REPOSITORY_ROOT
    / "portfolio"
    / "schema"
    / "portfolio-context.schema.json"
)
DEFAULT_OUTPUT_DIR = REPOSITORY_ROOT / "generated" / "portfolio"

CANONICAL_FILES = {
    "profile": "profile.yaml",
    "education": "education.yaml",
    "projects": "projects.yaml",
}


class PortfolioDataError(ValueError):
    """Raised for invalid canonical data or presentation configuration."""


def require_mapping(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PortfolioDataError(f"{path} must be a mapping")
    return value


def require_list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise PortfolioDataError(f"{path} must be a list")
    return value


def require_string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PortfolioDataError(f"{path} must be a non-empty string")
    return value.strip()


def optional_string(value: Any, path: str) -> str | None:
    if value is None:
        return None
    return require_string(value, path)


def require_boolean(value: Any, path: str) -> bool:
    if not isinstance(value, bool):
        raise PortfolioDataError(f"{path} must be a boolean")
    return value


def string_list(value: Any, path: str) -> list[str]:
    values = require_list(value, path)
    return [
        require_string(item, f"{path}[{index}]")
        for index, item in enumerate(values)
    ]


def unique_string_list(value: Any, path: str) -> list[str]:
    values = string_list(value, path)
    seen: set[str] = set()
    for item in values:
        if item in seen:
            raise PortfolioDataError(f"duplicate value '{item}' in {path}")
        seen.add(item)
    return values


def localized_string(value: Any, language: str, path: str) -> str:
    translations = require_mapping(value, path)
    if language not in translations:
        raise PortfolioDataError(f"{path} is missing language '{language}'")
    return require_string(translations[language], f"{path}.{language}")


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as stream:
            parsed = yaml.safe_load(stream)
    except yaml.YAMLError as error:
        raise PortfolioDataError(f"invalid YAML in {path}: {error}") from error
    except OSError as error:
        raise PortfolioDataError(f"could not read {path}: {error}") from error
    return require_mapping(parsed, str(path))


def load_canonical_data() -> dict[str, dict[str, Any]]:
    if not CAREER_DIR.is_dir():
        raise PortfolioDataError(f"career directory not found: {CAREER_DIR}")

    yaml_paths = sorted((*CAREER_DIR.rglob("*.yaml"), *CAREER_DIR.rglob("*.yml")))
    if not yaml_paths:
        raise PortfolioDataError(f"no YAML files found below {CAREER_DIR}")

    parsed_by_path = {path.resolve(): load_yaml(path) for path in yaml_paths}
    canonical: dict[str, dict[str, Any]] = {}
    for key, filename in CANONICAL_FILES.items():
        path = (CAREER_DIR / filename).resolve()
        if path not in parsed_by_path:
            raise PortfolioDataError(f"required canonical file not found: {path}")
        canonical[key] = parsed_by_path[path]
    return canonical


def records_by_id(value: Any, path: str) -> dict[str, dict[str, Any]]:
    records = require_list(value, path)
    result: dict[str, dict[str, Any]] = {}
    for index, value_record in enumerate(records):
        record_path = f"{path}[{index}]"
        record = require_mapping(value_record, record_path)
        record_id = require_string(record.get("id"), f"{record_path}.id")
        if record_id in result:
            raise PortfolioDataError(f"duplicate id '{record_id}' in {path}")
        result[record_id] = record
    return result


def select_records(
    records: dict[str, dict[str, Any]], include_value: Any, path: str
) -> list[dict[str, Any]]:
    include = unique_string_list(include_value, path)
    unknown = [record_id for record_id in include if record_id not in records]
    if unknown:
        raise PortfolioDataError(
            f"{path} references unknown canonical IDs: {', '.join(unknown)}"
        )
    return [records[record_id] for record_id in include]


def validated_repo_file(value: Any, path: str, *, nullable: bool) -> str | None:
    if value is None and nullable:
        return None
    configured_path = require_string(value, path)
    relative_path = Path(configured_path)
    if relative_path.is_absolute():
        raise PortfolioDataError(f"{path} must be relative to the repository")
    resolved = (REPOSITORY_ROOT / relative_path).resolve()
    try:
        resolved.relative_to(REPOSITORY_ROOT.resolve())
    except ValueError as error:
        raise PortfolioDataError(f"{path} must stay inside the repository") from error
    if not resolved.is_file():
        raise PortfolioDataError(
            f"{path} references a file that does not exist: {configured_path}"
        )
    return configured_path


def build_profile(
    canonical_profile: dict[str, Any], policy_value: Any, language: str
) -> dict[str, Any]:
    profile = require_mapping(
        canonical_profile.get("profile"), "profile.yaml.profile"
    )
    policy = require_mapping(policy_value, "default_portfolio.profile")
    show = require_mapping(policy.get("show"), "default_portfolio.profile.show")
    contact = require_mapping(
        profile.get("contact"), "profile.yaml.profile.contact"
    )
    links = require_mapping(profile.get("links"), "profile.yaml.profile.links")
    return {
        "name": require_string(profile.get("name"), "profile.yaml.profile.name"),
        "display_name": require_string(
            policy.get("display_name"), "default_portfolio.profile.display_name"
        ),
        "title": localized_string(
            profile.get("title"), language, "profile.yaml.profile.title"
        ),
        "summary": localized_string(
            profile.get("summary"), language, "profile.yaml.profile.summary"
        ),
        "location": optional_string(
            profile.get("location"), "profile.yaml.profile.location"
        ),
        "contact": {
            "email": optional_string(
                contact.get("email"), "profile.yaml.profile.contact.email"
            ),
            "phone": optional_string(
                contact.get("phone"), "profile.yaml.profile.contact.phone"
            ),
        },
        "links": {
            key: optional_string(
                links.get(key), f"profile.yaml.profile.links.{key}"
            )
            for key in ("github", "linkedin", "medium", "portfolio")
        },
        "show": {
            "phone": require_boolean(
                show.get("phone"), "default_portfolio.profile.show.phone"
            ),
            "medium": require_boolean(
                show.get("medium"), "default_portfolio.profile.show.medium"
            ),
            "portfolio_link": require_boolean(
                show.get("portfolio_link"),
                "default_portfolio.profile.show.portfolio_link",
            ),
        },
    }


def build_skills(canonical_profile: dict[str, Any], policy_value: Any) -> list[str]:
    groups = require_mapping(
        canonical_profile.get("skills"), "profile.yaml.skills"
    )
    inventory: set[str] = set()
    for group_name, group_value in groups.items():
        group = require_string(group_name, "profile.yaml.skills group name")
        inventory.update(string_list(group_value, f"profile.yaml.skills.{group}"))

    policy = require_mapping(policy_value, "default_portfolio.skills")
    selected = unique_string_list(
        policy.get("include"), "default_portfolio.skills.include"
    )
    unknown = [skill for skill in selected if skill not in inventory]
    if unknown:
        raise PortfolioDataError(
            "default_portfolio.skills.include references unknown canonical "
            f"skills: {', '.join(unknown)}"
        )
    return selected


def build_education(
    canonical_education: dict[str, Any], policy_value: Any, language: str
) -> list[dict[str, Any]]:
    records = records_by_id(
        canonical_education.get("education"), "education.yaml.education"
    )
    policy = require_mapping(policy_value, "default_portfolio.education")
    selected = select_records(
        records, policy.get("include"), "default_portfolio.education.include"
    )
    result = []
    for index, record in enumerate(selected):
        path = f"selected education[{index}]"
        result.append(
            {
                "id": require_string(record.get("id"), f"{path}.id"),
                "institution": require_string(
                    record.get("institution"), f"{path}.institution"
                ),
                "institution_short": optional_string(
                    record.get("institution_short"), f"{path}.institution_short"
                ),
                "degree": localized_string(
                    record.get("degree"), language, f"{path}.degree"
                ),
                "field": localized_string(
                    record.get("field"), language, f"{path}.field"
                ),
                "level": optional_string(record.get("level"), f"{path}.level"),
                "start_date": require_string(
                    record.get("start_date"), f"{path}.start_date"
                ),
                "end_date": optional_string(
                    record.get("end_date"), f"{path}.end_date"
                ),
                "location": optional_string(
                    record.get("location"), f"{path}.location"
                ),
                "description": localized_string(
                    record.get("description"), language, f"{path}.description"
                ),
                "topics": string_list(record.get("topics"), f"{path}.topics"),
            }
        )
    return result


def build_projects(
    canonical_projects: dict[str, Any],
    policy_value: Any,
    language: str,
    warnings: list[str],
) -> list[dict[str, Any]]:
    records = records_by_id(
        canonical_projects.get("projects"), "projects.yaml.projects"
    )
    policy = require_mapping(policy_value, "default_portfolio.projects")
    included_ids = unique_string_list(
        policy.get("include"), "default_portfolio.projects.include"
    )
    selected = select_records(
        records, included_ids, "default_portfolio.projects.include"
    )
    presentation = require_mapping(
        policy.get("presentation"), "default_portfolio.projects.presentation"
    )
    unknown_presentation = sorted(set(presentation) - set(records))
    if unknown_presentation:
        raise PortfolioDataError(
            "default_portfolio.projects.presentation references unknown canonical "
            f"IDs: {', '.join(unknown_presentation)}"
        )
    missing_presentation = [
        project_id for project_id in included_ids if project_id not in presentation
    ]
    if missing_presentation:
        raise PortfolioDataError(
            "default_portfolio.projects.presentation is missing selected IDs: "
            + ", ".join(missing_presentation)
        )

    result = []
    for index, record in enumerate(selected):
        path = f"selected projects[{index}]"
        project_id = require_string(record.get("id"), f"{path}.id")
        visual = require_mapping(
            presentation[project_id],
            f"default_portfolio.projects.presentation.{project_id}",
        )
        image = validated_repo_file(
            visual.get("image"),
            f"default_portfolio.projects.presentation.{project_id}.image",
            nullable=True,
        )
        if image is None:
            warnings.append(
                f"project '{project_id}' has no presentation image configured"
            )
        featured = require_boolean(record.get("featured"), f"{path}.featured")
        if not featured:
            warnings.append(
                f"selected project '{project_id}' is not marked featured"
            )
        links = require_mapping(record.get("links"), f"{path}.links")
        result.append(
            {
                "id": project_id,
                "name": require_string(record.get("name"), f"{path}.name"),
                "description": localized_string(
                    record.get("description"), language, f"{path}.description"
                ),
                "technologies": string_list(
                    record.get("technologies"), f"{path}.technologies"
                ),
                "links": {
                    "github": optional_string(
                        links.get("github"), f"{path}.links.github"
                    ),
                    "demo": optional_string(
                        links.get("demo"), f"{path}.links.demo"
                    ),
                },
                "image": image,
                "featured": featured,
            }
        )
    return result


def build_public_resume(policy_value: Any, language: str) -> str:
    policy = require_mapping(policy_value, "default_portfolio.public_resume")
    path = require_string(
        policy.get(language), f"default_portfolio.public_resume.{language}"
    )
    if not path.startswith("assets/doc/") or "/" in path[len("assets/doc/") :]:
        raise PortfolioDataError(
            f"default_portfolio.public_resume.{language} must point directly "
            "to assets/doc/"
        )
    if Path(path).suffix.lower() != ".pdf":
        raise PortfolioDataError(
            f"default_portfolio.public_resume.{language} must be a PDF"
        )
    return require_string(
        validated_repo_file(
            path,
            f"default_portfolio.public_resume.{language}",
            nullable=False,
        ),
        f"default_portfolio.public_resume.{language}",
    )


def build_context(
    canonical: dict[str, dict[str, Any]],
    config: dict[str, Any],
    language: str,
    warnings: list[str],
) -> dict[str, Any]:
    policy = require_mapping(
        config.get("default_portfolio"), "default_portfolio"
    )
    return {
        "language": language,
        "profile": build_profile(
            canonical["profile"], policy.get("profile"), language
        ),
        "skills": build_skills(canonical["profile"], policy.get("skills")),
        "education": build_education(
            canonical["education"], policy.get("education"), language
        ),
        "projects": build_projects(
            canonical["projects"], policy.get("projects"), language, warnings
        ),
        "public_resume": build_public_resume(
            policy.get("public_resume"), language
        ),
    }


def load_schema() -> dict[str, Any]:
    try:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise PortfolioDataError(
            f"invalid JSON schema in {SCHEMA_PATH}: {error}"
        ) from error
    except OSError as error:
        raise PortfolioDataError(f"could not read {SCHEMA_PATH}: {error}") from error
    return require_mapping(schema, str(SCHEMA_PATH))


def validate_context(context: dict[str, Any], schema: dict[str, Any]) -> None:
    try:
        Draft202012Validator.check_schema(schema)
    except Exception as error:
        raise PortfolioDataError(f"invalid portfolio context schema: {error}") from error
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(context), key=lambda error: list(error.path))
    if errors:
        details = []
        for error in errors:
            location = ".".join(str(part) for part in error.absolute_path) or "$"
            details.append(f"{location}: {error.message}")
        raise PortfolioDataError(
            "portfolio context failed schema validation: " + "; ".join(details)
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a public portfolio context from canonical career YAML."
    )
    parser.add_argument(
        "--lang", required=True, choices=("en", "pt"), help="context language"
    )
    parser.add_argument(
        "--output",
        type=Path,
        help=(
            "output JSON path (defaults to generated/portfolio/"
            "portfolio-context-<lang>.json)"
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = args.output or (
        DEFAULT_OUTPUT_DIR / f"portfolio-context-{args.lang}.json"
    )
    if not output.is_absolute():
        output = Path.cwd() / output

    try:
        canonical = load_canonical_data()
        config = load_yaml(CONFIG_PATH)
        warnings: list[str] = []
        context = build_context(canonical, config, args.lang, warnings)
        schema = load_schema()
        validate_context(context, schema)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(context, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except (PortfolioDataError, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    for warning in warnings:
        print(f"Warning: {warning}", file=sys.stderr)
    print(f"Portfolio context written to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
