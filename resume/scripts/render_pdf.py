#!/usr/bin/env python3
"""Convert a generated default-resume DOCX to PDF with LibreOffice."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RESUME_DIR = REPOSITORY_ROOT / "generated" / "resumes" / "default"


class PdfRenderError(RuntimeError):
    """Raised when LibreOffice cannot produce the requested PDF."""


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
        conversion_dir.mkdir()

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
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
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
        description="Convert a generated default-resume DOCX to PDF."
    )
    parser.add_argument("--lang", required=True, choices=("en", "pt"))
    parser.add_argument("--input", type=Path, help="input DOCX path")
    parser.add_argument("--output", type=Path, help="output PDF path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    suffix = args.lang.upper()
    stem = f"Felipe_Enne_Default_{suffix}"
    input_path = args.input or DEFAULT_RESUME_DIR / f"{stem}.docx"
    output_path = args.output or DEFAULT_RESUME_DIR / f"{stem}.pdf"

    try:
        convert_docx_to_pdf(input_path, output_path)
    except (PdfRenderError, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    print(f"Rendered PDF written to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
