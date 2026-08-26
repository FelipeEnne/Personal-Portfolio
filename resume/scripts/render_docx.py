#!/usr/bin/env python3
"""Render a resume context into a copy of an existing DOCX template."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
GENERATED_DIR = REPOSITORY_ROOT / "generated" / "resumes"
TEMPLATE_DIR = REPOSITORY_ROOT / "docs" / "CV"

WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
XML_NS = "http://www.w3.org/XML/1998/namespace"
HYPERLINK_REL_TYPE = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink"
)

DOCUMENT_PATH = "word/document.xml"
DOCUMENT_RELS_PATH = "word/_rels/document.xml.rels"


def qn(namespace: str, name: str) -> str:
    return f"{{{namespace}}}{name}"


W_P = qn(WORD_NS, "p")
W_PPR = qn(WORD_NS, "pPr")
W_R = qn(WORD_NS, "r")
W_RPR = qn(WORD_NS, "rPr")
W_T = qn(WORD_NS, "t")
W_NUMPR = qn(WORD_NS, "numPr")
W_HYPERLINK = qn(WORD_NS, "hyperlink")
W_SECTPR = qn(WORD_NS, "sectPr")
R_ID = qn(REL_NS, "id")


LANGUAGE_LABELS = {
    "en": {
        "skills": "Technical Skills",
        "experiences": "Experience",
        "education": "Education",
        "projects": "Project Work",
        "certifications": "Certifications",
        "present": "Present",
        "links": "Links",
        "skill_categories": {
            "languages": "Languages",
            "backend": "Backend",
            "frontend": "Frontend",
            "databases": "Databases",
            "data_engineering": "Data Engineering",
            "data_visualization": "Data Visualization",
            "testing": "Testing",
            "devops": "DevOps/Tools",
            "code_quality": "Code Quality",
            "integrations": "Integrations",
            "concepts": "Concepts",
        },
    },
    "pt": {
        "skills": "Habilidades Técnicas",
        "experiences": "Histórico Profissional",
        "education": "Formação Acadêmica",
        "projects": "Projetos",
        "certifications": "Certificações",
        "present": "Atual",
        "links": "Links",
        "skill_categories": {
            "languages": "Linguagens",
            "backend": "Backend",
            "frontend": "Frontend",
            "databases": "Bancos de Dados",
            "data_engineering": "Engenharia de Dados",
            "data_visualization": "Visualização de Dados",
            "testing": "Testes",
            "devops": "DevOps/Ferramentas",
            "code_quality": "Qualidade de Código",
            "integrations": "Integrações",
            "concepts": "Conceitos",
        },
    },
}

MONTHS = {
    "en": (
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ),
    "pt": (
        "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
        "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
    ),
}


class RenderError(ValueError):
    """Raised when a context or template cannot be rendered safely."""


def require_mapping(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RenderError(f"{path} must be an object")
    return value


def require_list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise RenderError(f"{path} must be an array")
    return value


def require_string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RenderError(f"{path} must be a non-empty string")
    return value


def optional_string(value: Any, path: str) -> str | None:
    if value is not None and not isinstance(value, str):
        raise RenderError(f"{path} must be a string or null")
    return value


def paragraph_text(paragraph: ET.Element) -> str:
    return "".join(node.text or "" for node in paragraph.iter(W_T))


def direct_runs(paragraph: ET.Element) -> list[ET.Element]:
    return [child for child in paragraph if child.tag == W_R]


def first_text_run(paragraph: ET.Element) -> ET.Element:
    for run in paragraph.iter(W_R):
        if paragraph_text(run).strip():
            return run
    for run in paragraph.iter(W_R):
        return run
    raise RenderError("template paragraph does not contain a reusable text run")


def hyperlink_run(paragraph: ET.Element) -> ET.Element:
    hyperlink = paragraph.find(W_HYPERLINK)
    if hyperlink is None:
        raise RenderError("template contact paragraph has no hyperlink prototype")
    run = hyperlink.find(W_R)
    if run is None:
        raise RenderError("template hyperlink has no reusable run")
    return run


def clear_paragraph(paragraph: ET.Element) -> None:
    for child in list(paragraph):
        if child.tag != W_PPR:
            paragraph.remove(child)


def clone_run_with_text(prototype: ET.Element, text: str) -> ET.Element:
    run = deepcopy(prototype)
    for child in list(run):
        if child.tag != W_RPR:
            run.remove(child)
    text_node = ET.SubElement(run, W_T)
    if text[:1].isspace() or text[-1:].isspace():
        text_node.set(qn(XML_NS, "space"), "preserve")
    text_node.text = text
    return run


def set_single_run_text(paragraph: ET.Element, text: str) -> ET.Element:
    prototype = first_text_run(paragraph)
    clear_paragraph(paragraph)
    paragraph.append(clone_run_with_text(prototype, text))
    return paragraph


def append_text(paragraph: ET.Element, prototype: ET.Element, text: str) -> None:
    paragraph.append(clone_run_with_text(prototype, text))


class RelationshipWriter:
    def __init__(self, relationships: ET.Element) -> None:
        self.relationships = relationships
        for relationship in list(relationships):
            if relationship.get("Type") == HYPERLINK_REL_TYPE:
                relationships.remove(relationship)
        used_ids = []
        for relationship in relationships:
            match = re.fullmatch(r"rId(\d+)", relationship.get("Id", ""))
            if match:
                used_ids.append(int(match.group(1)))
        self.next_id = max(used_ids, default=0) + 1

    def add(self, target: str) -> str:
        relationship_id = f"rId{self.next_id}"
        self.next_id += 1
        relationship = ET.SubElement(
            self.relationships, qn(PACKAGE_REL_NS, "Relationship")
        )
        relationship.set("Id", relationship_id)
        relationship.set("Type", HYPERLINK_REL_TYPE)
        relationship.set("Target", target)
        relationship.set("TargetMode", "External")
        return relationship_id


def append_hyperlink(
    paragraph: ET.Element,
    relationships: RelationshipWriter,
    run_prototype: ET.Element,
    label: str,
    target: str,
) -> None:
    hyperlink = ET.Element(W_HYPERLINK)
    hyperlink.set(R_ID, relationships.add(target))
    hyperlink.append(clone_run_with_text(run_prototype, label))
    paragraph.append(hyperlink)


def has_numbering(paragraph: ET.Element) -> bool:
    properties = paragraph.find(W_PPR)
    return properties is not None and properties.find(W_NUMPR) is not None


def make_bullet(prototype: ET.Element, text: str) -> ET.Element:
    paragraph = deepcopy(prototype)
    prefix = "" if has_numbering(paragraph) else "· "
    return set_single_run_text(paragraph, prefix + text)


def make_skill_paragraph(
    prototype: ET.Element, label: str, values: list[str]
) -> ET.Element:
    paragraph = deepcopy(prototype)
    runs = direct_runs(paragraph)
    if len(runs) < 2:
        raise RenderError("template skill paragraph must have label and value runs")
    label_run, value_run = runs[0], runs[1]
    clear_paragraph(paragraph)
    append_text(paragraph, label_run, f"{label}:")
    append_text(paragraph, value_run, f" {', '.join(values)}.")
    return paragraph


def format_date(value: str, language: str) -> str:
    match = re.fullmatch(r"(\d{4})(?:-(\d{2}))?", value)
    if not match:
        return value
    year, month = match.groups()
    if month is None:
        return year
    month_number = int(month)
    if not 1 <= month_number <= 12:
        raise RenderError(f"invalid month in canonical date: {value}")
    return f"{MONTHS[language][month_number - 1]} {year}"


def format_period(record: dict[str, Any], language: str, path: str) -> str:
    start = format_date(require_string(record.get("start_date"), f"{path}.start_date"), language)
    end_value = optional_string(record.get("end_date"), f"{path}.end_date")
    current = record.get("current", False)
    if not isinstance(current, bool):
        raise RenderError(f"{path}.current must be a boolean")
    if current:
        end = LANGUAGE_LABELS[language]["present"]
    elif end_value:
        end = format_date(end_value, language)
    else:
        end = None
    return f"{start} - {end}" if end else start


def title_case_identifier(identifier: str) -> str:
    return identifier.replace("_", " ").title()


def project_links(project: dict[str, Any], path: str) -> list[tuple[str, str]]:
    links = require_mapping(project.get("links"), f"{path}.links")
    result = []
    for key, label in (("github", "GitHub"), ("demo", "Demo")):
        target = optional_string(links.get(key), f"{path}.links.{key}")
        if target:
            result.append((label, target))
    return result


def build_contact_paragraph(
    prototype: ET.Element,
    context: dict[str, Any],
    relationships: RelationshipWriter,
) -> ET.Element:
    paragraph = deepcopy(prototype)
    regular_run = first_text_run(paragraph)
    link_run = hyperlink_run(paragraph)
    clear_paragraph(paragraph)

    candidate = require_mapping(context.get("candidate"), "candidate")
    contact = require_mapping(context.get("contact"), "contact")
    links = require_mapping(context.get("links"), "links")
    parts: list[tuple[str, str, str | None]] = []

    location = optional_string(candidate.get("location"), "candidate.location")
    phone = optional_string(contact.get("phone"), "contact.phone")
    email = optional_string(contact.get("email"), "contact.email")
    if location:
        parts.append(("text", location, None))
    if phone:
        parts.append(("text", phone, None))
    if email:
        parts.append(("link", email, f"mailto:{email}"))

    for key, label in (
        ("github", "GitHub"),
        ("linkedin", "LinkedIn"),
        ("medium", "Medium"),
        ("portfolio", "Portfolio" if context["language"] == "en" else "Portfólio"),
    ):
        target = optional_string(links.get(key), f"links.{key}")
        if target:
            parts.append(("link", label, target))

    for index, (kind, label, target) in enumerate(parts):
        if index:
            append_text(paragraph, regular_run, " • ")
        if kind == "link" and target:
            append_hyperlink(paragraph, relationships, link_run, label, target)
        else:
            append_text(paragraph, regular_run, label)
    return paragraph


def append_project_link_paragraph(
    body_items: list[ET.Element],
    bullet_prototype: ET.Element,
    links: list[tuple[str, str]],
    labels: dict[str, Any],
    relationships: RelationshipWriter,
    hyperlink_prototype: ET.Element,
) -> None:
    if not links:
        return
    paragraph = deepcopy(bullet_prototype)
    regular_run = first_text_run(paragraph)
    clear_paragraph(paragraph)
    prefix = "" if has_numbering(paragraph) else "· "
    append_text(paragraph, regular_run, f"{prefix}{labels['links']}: ")
    for index, (label, target) in enumerate(links):
        if index:
            append_text(paragraph, regular_run, " and ")
        append_hyperlink(
            paragraph, relationships, hyperlink_prototype, label, target
        )
    append_text(paragraph, regular_run, ".")
    body_items.append(paragraph)


def render_body(
    document: ET.Element,
    relationships: RelationshipWriter,
    context: dict[str, Any],
    language: str,
) -> None:
    body = document.find(qn(WORD_NS, "body"))
    if body is None:
        raise RenderError("template has no document body")
    paragraphs = [child for child in body if child.tag == W_P]
    if len(paragraphs) < 53:
        raise RenderError(
            f"template has {len(paragraphs)} paragraphs; at least 53 are required"
        )
    section_properties = body.find(W_SECTPR)
    if section_properties is None:
        raise RenderError("template has no section properties")

    prototypes = {
        "name": paragraphs[0],
        "title": paragraphs[1],
        "contact": paragraphs[2],
        "summary": paragraphs[3],
        "top_spacer": paragraphs[4],
        "skills_heading": paragraphs[5],
        "skill": paragraphs[6],
        "skills_spacer": paragraphs[15],
        "experiences_heading": paragraphs[16],
        "experience_header": paragraphs[17],
        "experience_bullet": paragraphs[18],
        "experience_spacer": paragraphs[21],
        "education_heading": paragraphs[43],
        "education_header": paragraphs[44],
        "education_bullet": paragraphs[45],
        "education_spacer": paragraphs[46],
        "projects_heading": paragraphs[50],
        "project_header": paragraphs[51],
        "project_bullet": paragraphs[52],
    }
    contact_hyperlink_run = deepcopy(hyperlink_run(prototypes["contact"]))
    labels = LANGUAGE_LABELS[language]
    items: list[ET.Element] = []

    candidate = require_mapping(context.get("candidate"), "candidate")
    items.append(
        set_single_run_text(
            deepcopy(prototypes["name"]),
            require_string(candidate.get("name"), "candidate.name"),
        )
    )
    items.append(
        set_single_run_text(
            deepcopy(prototypes["title"]),
            require_string(context.get("title"), "title"),
        )
    )
    items.append(
        build_contact_paragraph(prototypes["contact"], context, relationships)
    )
    items.append(
        set_single_run_text(
            deepcopy(prototypes["summary"]),
            require_string(context.get("summary"), "summary"),
        )
    )
    items.append(deepcopy(prototypes["top_spacer"]))

    items.append(
        set_single_run_text(deepcopy(prototypes["skills_heading"]), labels["skills"])
    )
    for index, raw_group in enumerate(require_list(context.get("skills"), "skills")):
        group = require_mapping(raw_group, f"skills[{index}]")
        identifier = require_string(group.get("id"), f"skills[{index}].id")
        values = require_list(group.get("items"), f"skills[{index}].items")
        skill_values = [
            require_string(value, f"skills[{index}].items[{value_index}]")
            for value_index, value in enumerate(values)
        ]
        if not skill_values:
            continue
        label = labels["skill_categories"].get(
            identifier, title_case_identifier(identifier)
        )
        items.append(make_skill_paragraph(prototypes["skill"], label, skill_values))
    items.append(deepcopy(prototypes["skills_spacer"]))

    items.append(
        set_single_run_text(
            deepcopy(prototypes["experiences_heading"]), labels["experiences"]
        )
    )
    experiences = require_list(context.get("experiences"), "experiences")
    for index, raw_record in enumerate(experiences):
        path = f"experiences[{index}]"
        record = require_mapping(raw_record, path)
        header = " - ".join(
            (
                require_string(record.get("role"), f"{path}.role"),
                require_string(record.get("company"), f"{path}.company"),
                format_period(record, language, path),
            )
        )
        items.append(
            set_single_run_text(deepcopy(prototypes["experience_header"]), header)
        )
        for highlight_index, highlight in enumerate(
            require_list(record.get("highlights"), f"{path}.highlights")
        ):
            items.append(
                make_bullet(
                    prototypes["experience_bullet"],
                    require_string(
                        highlight, f"{path}.highlights[{highlight_index}]"
                    ),
                )
            )
        if index < len(experiences) - 1:
            items.append(deepcopy(prototypes["experience_spacer"]))

    items.append(deepcopy(prototypes["skills_spacer"]))
    items.append(
        set_single_run_text(
            deepcopy(prototypes["education_heading"]), labels["education"]
        )
    )
    education = require_list(context.get("education"), "education")
    for index, raw_record in enumerate(education):
        path = f"education[{index}]"
        record = require_mapping(raw_record, path)
        header = " - ".join(
            (
                require_string(record.get("degree"), f"{path}.degree"),
                require_string(record.get("institution"), f"{path}.institution"),
                format_period(record, language, path),
            )
        )
        items.append(
            set_single_run_text(deepcopy(prototypes["education_header"]), header)
        )
        description = optional_string(record.get("description"), f"{path}.description")
        if description:
            items.append(make_bullet(prototypes["education_bullet"], description))
        if index < len(education) - 1:
            items.append(deepcopy(prototypes["education_spacer"]))

    items.append(deepcopy(prototypes["skills_spacer"]))
    items.append(
        set_single_run_text(
            deepcopy(prototypes["projects_heading"]), labels["projects"]
        )
    )
    projects = require_list(context.get("projects"), "projects")
    for index, raw_project in enumerate(projects):
        path = f"projects[{index}]"
        project = require_mapping(raw_project, path)
        items.append(
            set_single_run_text(
                deepcopy(prototypes["project_header"]),
                require_string(project.get("name"), f"{path}.name"),
            )
        )
        description = optional_string(project.get("description"), f"{path}.description")
        if description:
            items.append(make_bullet(prototypes["project_bullet"], description))
        for highlight_index, highlight in enumerate(
            require_list(project.get("highlights"), f"{path}.highlights")
        ):
            items.append(
                make_bullet(
                    prototypes["project_bullet"],
                    require_string(
                        highlight, f"{path}.highlights[{highlight_index}]"
                    ),
                )
            )
        append_project_link_paragraph(
            items,
            prototypes["project_bullet"],
            project_links(project, path),
            labels,
            relationships,
            contact_hyperlink_run,
        )
        if index < len(projects) - 1:
            items.append(deepcopy(prototypes["education_spacer"]))

    certifications = require_list(context.get("certifications"), "certifications")
    if certifications:
        items.append(deepcopy(prototypes["skills_spacer"]))
        items.append(
            set_single_run_text(
                deepcopy(prototypes["projects_heading"]), labels["certifications"]
            )
        )
        for index, raw_certification in enumerate(certifications):
            path = f"certifications[{index}]"
            certification = require_mapping(raw_certification, path)
            name = require_string(certification.get("name"), f"{path}.name")
            issuer = require_string(certification.get("issuer"), f"{path}.issuer")
            items.append(
                set_single_run_text(
                    deepcopy(prototypes["education_header"]), f"{name} - {issuer}"
                )
            )

    for child in list(body):
        body.remove(child)
    for item in items:
        body.append(item)
    body.append(deepcopy(section_properties))


def register_document_namespaces(xml_bytes: bytes) -> None:
    import io

    for _, namespace in ET.iterparse(io.BytesIO(xml_bytes), events=("start-ns",)):
        prefix, uri = namespace
        ET.register_namespace(prefix, uri)
    ET.register_namespace("", PACKAGE_REL_NS)


def render_docx(
    template_path: Path,
    context_path: Path,
    output_path: Path,
    language: str,
) -> None:
    if template_path.resolve() == output_path.resolve():
        raise RenderError("output path must not overwrite the DOCX template")
    if not template_path.is_file():
        raise RenderError(f"template not found: {template_path}")
    if not context_path.is_file():
        raise RenderError(f"resume context not found: {context_path}")

    try:
        context = require_mapping(
            json.loads(context_path.read_text(encoding="utf-8")), "context"
        )
    except json.JSONDecodeError as error:
        raise RenderError(f"invalid JSON in {context_path}: {error}") from error
    context_language = require_string(context.get("language"), "language")
    if context_language != language:
        raise RenderError(
            f"context language '{context_language}' does not match --lang {language}"
        )

    try:
        with ZipFile(template_path, "r") as archive:
            entries = archive.infolist()
            package = {entry.filename: archive.read(entry.filename) for entry in entries}
    except (BadZipFile, OSError) as error:
        raise RenderError(f"could not read DOCX template {template_path}: {error}") from error

    if DOCUMENT_PATH not in package or DOCUMENT_RELS_PATH not in package:
        raise RenderError("template is missing required Word document parts")

    register_document_namespaces(package[DOCUMENT_PATH])
    document = ET.fromstring(package[DOCUMENT_PATH])
    relationships = ET.fromstring(package[DOCUMENT_RELS_PATH])
    relationship_writer = RelationshipWriter(relationships)
    render_body(document, relationship_writer, context, language)
    package[DOCUMENT_PATH] = ET.tostring(
        document, encoding="utf-8", xml_declaration=True
    )
    package[DOCUMENT_RELS_PATH] = ET.tostring(
        relationships, encoding="utf-8", xml_declaration=True
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{output_path.name}.", suffix=".tmp", dir=output_path.parent, delete=False
        ) as temporary:
            temporary_path = Path(temporary.name)
        try:
            with ZipFile(temporary_path, "w", compression=ZIP_DEFLATED) as output_archive:
                for entry in entries:
                    output_archive.writestr(entry, package[entry.filename])
            temporary_path.replace(output_path)
        finally:
            if temporary_path.exists():
                temporary_path.unlink()
    except OSError as error:
        raise RenderError(f"could not write {output_path}: {error}") from error


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render a resume context into a copy of a DOCX template."
    )
    parser.add_argument("--lang", required=True, choices=("en", "pt"))
    parser.add_argument("--context", type=Path, help="input resume-context JSON")
    parser.add_argument("--template", type=Path, help="input DOCX template")
    parser.add_argument("--output", type=Path, help="output DOCX path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    suffix = args.lang.upper()
    context_path = args.context or GENERATED_DIR / f"resume-context-{args.lang}.json"
    template_path = args.template or TEMPLATE_DIR / f"template-{args.lang}.docx"
    output_path = args.output or GENERATED_DIR / f"Felipe_Enne_Default_{suffix}.docx"

    try:
        render_docx(template_path, context_path, output_path, args.lang)
    except RenderError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    print(f"Rendered DOCX written to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
