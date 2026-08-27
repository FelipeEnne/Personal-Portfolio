#!/usr/bin/env python3
"""Convert a generated default or job-specific DOCX to PDF with LibreOffice."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RESUME_DIR = REPOSITORY_ROOT / "generated" / "resumes" / "default"
JOBS_RESUME_DIR = REPOSITORY_ROOT / "generated" / "resumes" / "jobs"
PUBLIC_DOC_DIR = REPOSITORY_ROOT / "assets" / "doc"
TEMPLATE_DIR = REPOSITORY_ROOT / "docs" / "CV"


class PdfRenderError(RuntimeError):
    """Raised when LibreOffice cannot produce the requested PDF."""


def pdf_page_count(path: Path) -> int | None:
    executable = shutil.which("pdfinfo")
    if executable is None:
        return None
    completed = subprocess.run(
        [executable, str(path)], check=False, capture_output=True, text=True
    )
    if completed.returncode != 0:
        return None
    for line in completed.stdout.splitlines():
        if line.startswith("Pages:"):
            try:
                return int(line.split(":", 1)[1].strip())
            except ValueError:
                return None
    return None


def find_libreoffice() -> str:
    for command in ("libreoffice", "soffice"):
        executable = shutil.which(command)
        if executable:
            return executable
    raise PdfRenderError(
        "LibreOffice was not found in PATH; install LibreOffice Writer with "
        "headless conversion support"
    )


def convert_docx_to_pdf(input_path: Path, output_path: Path) -> None:
    if output_path.resolve().is_relative_to(PUBLIC_DOC_DIR.resolve()):
        raise PdfRenderError(
            "PDF rendering must not publish directly to assets/doc/"
        )
    if output_path.resolve().is_relative_to(TEMPLATE_DIR.resolve()):
        raise PdfRenderError("PDF output must not be written under docs/CV/")
    if not input_path.is_file():
        raise PdfRenderError(f"generated DOCX not found: {input_path}")
    if input_path.suffix.lower() != ".docx":
        raise PdfRenderError(f"input must be a DOCX file: {input_path}")
    if output_path.suffix.lower() != ".pdf":
        raise PdfRenderError(f"output must be a PDF file: {output_path}")

    office = find_libreoffice()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="resume-pdf-") as temporary_dir:
        temporary_root = Path(temporary_dir)
        conversion_dir = temporary_root / "output"
        profile_dir = temporary_root / "libreoffice-profile"
        config_dir = temporary_root / "xdg-config"
        cache_dir = temporary_root / "xdg-cache"
        runtime_dir = temporary_root / "xdg-runtime"
        conversion_dir.mkdir()
        config_dir.mkdir()
        cache_dir.mkdir()
        runtime_dir.mkdir(mode=0o700)

        command = [
            office,
            f"-env:UserInstallation={profile_dir.as_uri()}",
            "--headless",
            "--convert-to",
            "pdf:writer_pdf_Export",
            "--outdir",
            str(conversion_dir),
            str(input_path.resolve()),
        ]
        environment = os.environ.copy()
        environment.update(
            {
                "XDG_CONFIG_HOME": str(config_dir),
                "XDG_CACHE_HOME": str(cache_dir),
                "XDG_RUNTIME_DIR": str(runtime_dir),
            }
        )
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )
        if completed.returncode != 0:
            details = (completed.stderr or completed.stdout).strip()
            raise PdfRenderError(
                f"LibreOffice conversion failed with exit code "
                f"{completed.returncode}: {details or 'no diagnostic output'}"
            )

        converted_path = conversion_dir / f"{input_path.stem}.pdf"
        if not converted_path.is_file():
            details = (completed.stdout + "\n" + completed.stderr).strip()
            raise PdfRenderError(
                "LibreOffice reported success but did not create the expected "
                f"PDF {converted_path}: {details or 'no diagnostic output'}"
            )
        if not converted_path.read_bytes().startswith(b"%PDF-"):
            raise PdfRenderError(
                f"LibreOffice produced a file without a PDF signature: "
                f"{converted_path}"
            )

        converted_path.replace(output_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert a generated resume DOCX to PDF."
    )
    parser.add_argument("--lang", choices=("en", "pt"))
    parser.add_argument("--input", type=Path, help="input DOCX path")
    parser.add_argument("--output", type=Path, help="output PDF path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        if args.input:
            input_path = args.input.resolve()
            job_specific = input_path.resolve().is_relative_to(JOBS_RESUME_DIR.resolve())
            if args.output:
                output_path = args.output.resolve()
            else:
                output_path = input_path.with_suffix(".pdf")
        else:
            if not args.lang:
                raise PdfRenderError("--lang is required when --input is not provided")
            suffix = args.lang.upper()
            stem = f"Felipe_Enne_Default_{suffix}"
            input_path = DEFAULT_RESUME_DIR / f"{stem}.docx"
            output_path = args.output or DEFAULT_RESUME_DIR / f"{stem}.pdf"
            job_specific = False

        if job_specific:
            job_directory = input_path.parent
            if not output_path.resolve().is_relative_to(job_directory.resolve()):
                raise PdfRenderError(
                    "job-specific PDF output must stay with its DOCX under "
                    "generated/resumes/jobs/"
                )
        convert_docx_to_pdf(input_path, output_path)
    except (PdfRenderError, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    print(f"Rendered PDF written to {output_path}")
    pages = pdf_page_count(output_path)
    if pages is None:
        print("Warning: could not determine generated PDF page count", file=sys.stderr)
    elif pages > 2:
        print(
            f"Warning: generated PDF has {pages} pages; the target is at most 2",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
