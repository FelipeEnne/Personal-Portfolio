#!/usr/bin/env python3
"""Use measured two-page capacity to expand a job-specific context safely."""

from __future__ import annotations

import argparse
import copy
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Callable

try:
    from resume.scripts import build_context as base
    from resume.scripts import build_job_context as jobs
    from resume.scripts import render_docx, render_pdf
except ModuleNotFoundError:  # Direct execution from resume/scripts/.
    import build_context as base  # type: ignore[no-redef]
    import build_job_context as jobs  # type: ignore[no-redef]
    import render_docx  # type: ignore[no-redef]
    import render_pdf  # type: ignore[no-redef]


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CAREER_DIR = REPOSITORY_ROOT / "career"
JOBS_OUTPUT_DIR = REPOSITORY_ROOT / "generated" / "resumes" / "jobs"
MAX_PAGES = 2


class ExpansionError(ValueError):
    """Raised when a job context cannot be expanded safely."""


def project_context(
    record: dict[str, Any], language: str, analysis: dict[str, Any], job_tokens: set[str]
) -> dict[str, Any]:
    """Build one project from canonical data, then rank its full highlights."""
    raw = base.build_projects(
        [record],
        language,
        {"include": [record["id"]], "exclude": [], "max_highlights_per_project": 100},
    )[0]
    raw["highlights"] = jobs.rank_highlights(
        raw["highlights"],
        job_tokens,
        jobs.MAX_PROJECT_HIGHLIGHTS,
        analysis["matched_skills"],
        analysis,
    )
    return raw


def add_project(
    context: dict[str, Any], record: dict[str, Any], language: str,
    analysis: dict[str, Any], job_tokens: set[str],
) -> dict[str, Any]:
    candidate = copy.deepcopy(context)
    candidate["projects"].append(project_context(record, language, analysis, job_tokens))
    return candidate


def add_skill(context: dict[str, Any], group: str, skill: str) -> dict[str, Any]:
    candidate = copy.deepcopy(context)
    target = next((item for item in candidate["skills"] if item["id"] == group), None)
    if target is None:
        target = {"id": group, "items": []}
        candidate["skills"].append(target)
    if skill not in target["items"]:
        target["items"].append(skill)
    return candidate


def page_count_for_context(
    context: dict[str, Any], language: str, slug: str
) -> int:
    """Render a candidate into a temporary job directory and measure pdfinfo."""
    job_dir = JOBS_OUTPUT_DIR / f".capacity-{slug}-{language}"
    job_dir.mkdir(parents=True, exist_ok=True)
    context_path = job_dir / "resume-context.json"
    docx_path = job_dir / "candidate.docx"
    pdf_path = job_dir / "candidate.pdf"
    candidate_context = copy.deepcopy(context)
    try:
        # render_docx enforces that a job context's slug matches its directory.
        # Temporary candidates therefore use a temporary slug only while
        # rendering; the persisted context keeps the real job slug.
        candidate_context["job"]["slug"] = job_dir.name
        context_path.write_text(
            json.dumps(candidate_context, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        render_docx.render_docx(
            render_docx.TEMPLATE_DIR / f"template-{language}.docx",
            context_path,
            docx_path,
            language,
        )
        render_pdf.convert_docx_to_pdf(docx_path, pdf_path)
        pages = render_pdf.pdf_page_count(pdf_path)
        if pages is None:
            raise ExpansionError("could not determine candidate PDF page count with pdfinfo")
        return pages
    finally:
        shutil.rmtree(job_dir, ignore_errors=True)


def expand_context(
    context: dict[str, Any],
    canonical: dict[str, dict[str, Any]],
    language: str,
    analysis: dict[str, Any],
    page_counter: Callable[[dict[str, Any]], int],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Try exactly one third project, then canonical skills in inventory order."""
    result = copy.deepcopy(context)
    # Keep the two strongest directed projects as the invariant base. If the
    # directed selector already supplied a third, it is reconsidered below as
    # the single capacity candidate rather than duplicated.
    result["projects"] = result["projects"][:2]
    report: dict[str, Any] = {
        "base_pages": page_counter(result),
        "third_project": {"attempted": False, "kept": False, "pages": None},
        "additional_skills": {"kept": [], "rejected": []},
    }
    job_tokens = jobs.text_tokens(
        " ".join((*analysis.get("responsibilities", []), *analysis.get("required", []),
                  *analysis.get("preferred", [])))
    )
    project_records = base.validate_unique_ids(
        base.require_list(canonical["projects"].get("projects"), "projects"), "projects"
    )
    current_ids = [item["id"] for item in result["projects"]]
    # The directed context may already contain a third item. Re-evaluate it as
    # the sole expansion candidate while preserving the first two positions.
    primary_ids = current_ids[:2]
    inventory = [
        (jobs.relevance_score(record, set(analysis["matched_skills"]), job_tokens,
                              [skill for values in jobs.canonical_skill_groups(canonical["profile"]).values() for skill in values]),
         bool(record.get("featured")), index, record)
        for index, record in enumerate(project_records)
        if record["id"] not in primary_ids
    ]
    inventory.sort(key=lambda item: (-item[0], -int(item[1]), item[2]))
    if inventory:
        report["third_project"]["attempted"] = True
        candidate = add_project(result, inventory[0][3], language, analysis, job_tokens)
        pages = page_counter(candidate)
        report["third_project"]["pages"] = pages
        if pages <= MAX_PAGES:
            result = candidate
            report["third_project"]["kept"] = True

    groups = jobs.canonical_skill_groups(canonical["profile"])
    present = {skill for group in result["skills"] for skill in group["items"]}
    for group, values in groups.items():
        for skill in values:
            if skill in present or skill in analysis["matched_skills"]:
                continue
            candidate = add_skill(result, group, skill)
            pages = page_counter(candidate)
            if pages <= MAX_PAGES:
                result = candidate
                present.add(skill)
                report["additional_skills"]["kept"].append(skill)
            else:
                report["additional_skills"]["rejected"].append(skill)

    report["final_pages"] = page_counter(result)
    return result, report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Expand a job resume using measured page capacity.")
    parser.add_argument("--job", required=True, type=Path)
    parser.add_argument("--lang", required=True, choices=("en", "pt"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    job_path = args.job.resolve()
    try:
        if not job_path.is_file():
            raise ExpansionError(f"job description not found: {job_path}")
        canonical = base.load_yaml_files(CAREER_DIR)
        job_text = job_path.read_text(encoding="utf-8")
        slug = jobs.slugify(job_path.stem)
        context = jobs.build_job_context(
            canonical, job_text, jobs.source_display(job_path), slug, args.lang
        )
        analysis = context["job"]
        counter = lambda candidate: page_count_for_context(
            candidate, args.lang, slug
        )
        expanded, report = expand_context(
            context, canonical, args.lang, analysis, counter
        )
        output = JOBS_OUTPUT_DIR / slug / f"resume-context-{args.lang}.json"
        jobs.write_job_context(expanded, output)
    except (
        base.CareerDataError,
        jobs.JobContextError,
        ExpansionError,
        render_docx.RenderError,
        render_pdf.PdfRenderError,
        OSError,
    ) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"Expanded job-specific context written to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
