#!/usr/bin/env python3
"""Build a complete job-specific resume through the existing pipeline."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path
from typing import Sequence


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
JOBS_OUTPUT_DIR = REPOSITORY_ROOT / "generated" / "resumes" / "jobs"
SCRIPTS_DIR = REPOSITORY_ROOT / "resume" / "scripts"


class JobResumeError(ValueError):
    """Raised when the orchestration inputs or outputs are unsafe."""


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    plain = "".join(char for char in normalized if not unicodedata.combining(char))
    result = re.sub(r"[^A-Za-z0-9]+", "-", plain).strip("-").lower()
    if not result:
        raise JobResumeError("job title does not produce a valid filename")
    return result


def title_label(title: str | None, job_slug: str) -> str:
    # Parenthetical technology lists are not part of the display job title.
    clean = (title or job_slug.replace("-", " ")).split("(", 1)[0].strip()
    words = re.findall(r"[A-Za-zÀ-ÿ0-9]+", clean)
    if not words:
        raise JobResumeError("job title does not produce a valid filename")
    return "_".join(words)


def run_step(command: Sequence[str]) -> None:
    subprocess.run(list(command), cwd=REPOSITORY_ROOT, check=True)


def build_job_resume(job: Path, language: str) -> tuple[Path, Path, Path]:
    if not job.is_file():
        raise JobResumeError(f"job description not found: {job}")
    if job.suffix.lower() != ".txt":
        raise JobResumeError("job description must be a .txt file")

    python = sys.executable
    run_step([python, str(SCRIPTS_DIR / "build_job_context.py"), "--job", str(job), "--lang", language])
    run_step([python, str(SCRIPTS_DIR / "expand_job_context.py"), "--job", str(job), "--lang", language])

    job_slug = slugify(job.stem)
    context_path = JOBS_OUTPUT_DIR / job_slug / f"resume-context-{language}.json"
    try:
        context = json.loads(context_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise JobResumeError(f"expanded job context unavailable: {context_path}") from error
    title = context.get("job", {}).get("title")
    if title is not None and not isinstance(title, str):
        raise JobResumeError("job.title in context must be a string or null")

    label = title_label(title, job_slug)
    suffix = language.upper()
    output_dir = JOBS_OUTPUT_DIR / job_slug
    docx_path = output_dir / f"Felipe_Enne_{label}_{suffix}.docx"
    pdf_path = output_dir / f"Felipe_Enne_{label}_{suffix}.pdf"
    run_step([
        python, str(SCRIPTS_DIR / "render_docx.py"), "--context", str(context_path),
        "--output", str(docx_path),
    ])
    run_step([
        python, str(SCRIPTS_DIR / "render_pdf.py"), "--input", str(docx_path),
        "--output", str(pdf_path),
    ])
    return context_path, docx_path, pdf_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a complete job-specific resume.")
    parser.add_argument("--job", required=True, type=Path)
    parser.add_argument("--lang", required=True, choices=("en", "pt"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        paths = build_job_resume(args.job.resolve(), args.lang)
    except (JobResumeError, OSError, subprocess.CalledProcessError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    print(f"Job resume context: {paths[0]}")
    print(f"Job resume DOCX: {paths[1]}")
    print(f"Job resume PDF: {paths[2]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
