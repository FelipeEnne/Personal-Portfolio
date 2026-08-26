#!/usr/bin/env python3
"""Render validated portfolio contexts as a static bilingual website."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
except ImportError:  # pragma: no cover - depends on the execution environment
    print(
        "Error: Jinja2 is required. Install dependencies with "
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
CONTEXT_DIR = REPOSITORY_ROOT / "generated" / "portfolio"
TEMPLATE_DIR = REPOSITORY_ROOT / "portfolio" / "templates"
SCHEMA_PATH = REPOSITORY_ROOT / "portfolio" / "schema" / "portfolio-context.schema.json"
OUTPUT_DIR = REPOSITORY_ROOT / "_site"
ASSETS_DIR = REPOSITORY_ROOT / "assets"
FAVICON_PATH = REPOSITORY_ROOT / "favicon.ico"

UI = {
    "en": {
        "projects": "Projects",
        "contact": "Contact",
        "contact_me": "Contact me!",
        "language": "Language",
        "projects_cta": "Check out my",
        "projects_link": "side-projects",
        "below": "below",
        "resume_label": "felipeenne.pdf",
        "github_link": "GitHub link",
        "demo": "Demo",
        "youtube": "YouTube",
        "screenshot_of": "Screenshot of",
        "made_by": "Made by",
    },
    "pt": {
        "projects": "Projetos",
        "contact": "Contato",
        "contact_me": "Fale comigo!",
        "language": "Idioma",
        "projects_cta": "Confira meus",
        "projects_link": "projetos",
        "below": "abaixo",
        "resume_label": "felipeenne.pdf",
        "github_link": "Link no GitHub",
        "demo": "Demo",
        "youtube": "YouTube",
        "screenshot_of": "Captura de tela de",
        "made_by": "Feito por",
    },
}


class SiteRenderError(ValueError):
    """Raised when a portfolio context or rendered site is invalid."""


class LocalReferenceParser(HTMLParser):
    """Collect local resource references from generated HTML."""

    def __init__(self) -> None:
        super().__init__()
        self.references: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        attribute_name = "src" if tag in {"img", "script"} else "href"
        if tag not in {"a", "img", "link", "script"}:
            return
        for name, value in attrs:
            if name == attribute_name and value:
                self.references.append(value)


def require_mapping(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SiteRenderError(f"{path} must be an object")
    return value


def require_list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise SiteRenderError(f"{path} must be an array")
    return value


def require_string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SiteRenderError(f"{path} must be a non-empty string")
    return value


def load_json(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise SiteRenderError(
            f"{label} not found: {path}. Run build_context.py for both languages first."
        )
    try:
        return require_mapping(
            json.loads(path.read_text(encoding="utf-8")), label
        )
    except json.JSONDecodeError as error:
        raise SiteRenderError(f"invalid JSON in {path}: {error}") from error


def load_schema() -> dict[str, Any]:
    return load_json(SCHEMA_PATH, "portfolio context schema")


def validate_context(
    context: dict[str, Any], schema: dict[str, Any], language: str
) -> None:
    if context.get("language") != language:
        raise SiteRenderError(
            f"portfolio context for {language} declares language "
            f"'{context.get('language')}'"
        )
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(context), key=lambda error: list(error.path))
    if errors:
        details = []
        for error in errors:
            location = ".".join(str(part) for part in error.absolute_path) or "$"
            details.append(f"{location}: {error.message}")
        raise SiteRenderError(
            f"portfolio context for {language} failed schema validation: "
            + "; ".join(details)
        )


def contact_items(profile: dict[str, Any]) -> list[dict[str, Any]]:
    contact = require_mapping(profile.get("contact"), "profile.contact")
    links = require_mapping(profile.get("links"), "profile.links")
    show = require_mapping(profile.get("show"), "profile.show")
    result = []
    email = contact.get("email")
    if email:
        result.append(
            {"label": email, "href": f"mailto:{email}", "external": False}
        )
    phone = contact.get("phone")
    if phone and show.get("phone"):
        result.append({"label": phone, "href": None, "external": False})
    for key, label in (("linkedin", "LinkedIn"), ("github", "GitHub")):
        if links.get(key):
            result.append({"label": label, "href": links[key], "external": True})
    if links.get("medium") and show.get("medium"):
        result.append(
            {"label": "Medium", "href": links["medium"], "external": True}
        )
    if links.get("portfolio") and show.get("portfolio_link"):
        result.append(
            {
                "label": "Portfolio",
                "href": links["portfolio"],
                "external": True,
            }
        )
    return result


def project_link_items(
    project: dict[str, Any], ui: dict[str, str]
) -> list[dict[str, str]]:
    links = require_mapping(project.get("links"), f"projects.{project.get('id')}.links")
    result = []
    github = links.get("github")
    if github:
        result.append({"label": ui["github_link"], "href": github})
    demo = links.get("demo")
    if demo:
        hostname = (urlparse(demo).hostname or "").lower()
        label = ui["youtube"] if hostname in {"youtube.com", "www.youtube.com", "youtu.be"} else ui["demo"]
        result.append({"label": label, "href": demo})
    return result


def page_model(context: dict[str, Any], language: str) -> dict[str, Any]:
    profile = require_mapping(context.get("profile"), "profile")
    projects = []
    asset_prefix = "" if language == "en" else "../"
    for index, raw_project in enumerate(require_list(context.get("projects"), "projects")):
        project = dict(require_mapping(raw_project, f"projects[{index}]"))
        image = project.get("image")
        project["image_href"] = f"{asset_prefix}{image}" if image else None
        project["link_items"] = project_link_items(project, UI[language])
        projects.append(project)

    items = contact_items(profile)
    email = require_mapping(profile.get("contact"), "profile.contact").get("email")
    footer_items = [item for item in items if item.get("href")]
    if email and not any(item["label"] == email for item in footer_items):
        footer_items.insert(
            0, {"label": email, "href": f"mailto:{email}", "external": False}
        )

    display_name = require_string(profile.get("display_name"), "profile.display_name")
    return {
        "language": language,
        "html_lang": "en" if language == "en" else "pt-BR",
        "asset_prefix": asset_prefix,
        "language_links": (
            {"en": "./", "pt": "pt/"}
            if language == "en"
            else {"en": "../", "pt": "./"}
        ),
        "ui": UI[language],
        "profile": profile,
        "terminal_identifier": display_name.split()[0],
        "page_title": f"{display_name} — {require_string(profile.get('title'), 'profile.title')}",
        "contact_items": items,
        "footer_contact_items": footer_items,
        "resume_href": f"{asset_prefix}{require_string(context.get('public_resume'), 'public_resume')}",
        "skills": require_list(context.get("skills"), "skills"),
        "education": require_list(context.get("education"), "education"),
        "projects": projects,
        "build_year": datetime.now().year,
    }


def render_page(
    environment: Environment, context: dict[str, Any], language: str
) -> str:
    template = environment.get_template("index.html")
    rendered = template.render(**page_model(context, language))
    if "{{" in rendered or "{%" in rendered or "{#" in rendered:
        raise SiteRenderError(f"unresolved template marker in {language} HTML")
    return rendered


def validate_local_references(page_path: Path, site_root: Path) -> None:
    parser = LocalReferenceParser()
    parser.feed(page_path.read_text(encoding="utf-8"))
    site_root_resolved = site_root.resolve()
    for reference in parser.references:
        parsed = urlparse(reference)
        if parsed.scheme or parsed.netloc or reference.startswith(("#", "mailto:")):
            continue
        relative_reference = parsed.path
        if not relative_reference:
            continue
        resolved = (page_path.parent / relative_reference).resolve()
        try:
            resolved.relative_to(site_root_resolved)
        except ValueError as error:
            raise SiteRenderError(
                f"local reference escapes _site in {page_path}: {reference}"
            ) from error
        if not resolved.exists():
            raise SiteRenderError(
                f"broken local reference in {page_path}: {reference}"
            )


def build_site() -> None:
    schema = load_schema()
    Draft202012Validator.check_schema(schema)
    contexts = {}
    for language in ("en", "pt"):
        path = CONTEXT_DIR / f"portfolio-context-{language}.json"
        context = load_json(path, f"portfolio context for {language}")
        validate_context(context, schema, language)
        contexts[language] = context

    if not ASSETS_DIR.is_dir():
        raise SiteRenderError(f"assets directory not found: {ASSETS_DIR}")
    if not FAVICON_PATH.is_file():
        raise SiteRenderError(f"favicon not found: {FAVICON_PATH}")

    environment = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(enabled_extensions=("html",)),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
    )

    staging_path = Path(tempfile.mkdtemp(prefix=".site-build-", dir=REPOSITORY_ROOT))
    try:
        shutil.copytree(ASSETS_DIR, staging_path / "assets")
        shutil.copy2(FAVICON_PATH, staging_path / "favicon.ico")
        (staging_path / "pt").mkdir()
        (staging_path / "index.html").write_text(
            render_page(environment, contexts["en"], "en"), encoding="utf-8"
        )
        (staging_path / "pt" / "index.html").write_text(
            render_page(environment, contexts["pt"], "pt"), encoding="utf-8"
        )
        validate_local_references(staging_path / "index.html", staging_path)
        validate_local_references(staging_path / "pt" / "index.html", staging_path)

        if OUTPUT_DIR.exists():
            shutil.rmtree(OUTPUT_DIR)
        staging_path.rename(OUTPUT_DIR)
    except Exception:
        if staging_path.exists():
            shutil.rmtree(staging_path)
        raise


def main() -> int:
    try:
        build_site()
    except (SiteRenderError, OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    print(f"Static portfolio written to {OUTPUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
