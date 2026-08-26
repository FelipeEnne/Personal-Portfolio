#!/usr/bin/env python3
"""Explicitly publish approved default resume PDFs to the public portfolio."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, TextIO


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
A4_WIDTH_POINTS = 595.276
A4_HEIGHT_POINTS = 841.890
A4_TOLERANCE_POINTS = 2.0
REQUIRED_PAGE_COUNT = 2


class PublishError(RuntimeError):
    """Raised when default resumes cannot be safely published."""


@dataclass(frozen=True)
class PublicationItem:
    language: str
    source: Path
    destination: Path


@dataclass(frozen=True)
class PdfDetails:
    size: int
    pages: int
    sha256: str


def default_plan(
    repository_root: Path = REPOSITORY_ROOT,
) -> tuple[PublicationItem, ...]:
    return (
        PublicationItem(
            "EN",
            repository_root
            / "generated/resumes/default/Felipe_Enne_Default_EN.pdf",
            repository_root / "assets/doc/CV.pdf",
        ),
        PublicationItem(
            "PT",
            repository_root
            / "generated/resumes/default/Felipe_Enne_Default_PT.pdf",
            repository_root / "assets/doc/Currículo.pdf",
        ),
    )


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def validate_fixed_paths(
    plan: tuple[PublicationItem, ...], repository_root: Path = REPOSITORY_ROOT
) -> None:
    jobs_dir = repository_root / "generated/resumes/jobs"
    for item in plan:
        if _is_relative_to(item.source, jobs_dir):
            raise PublishError(
                f"job-specific resumes must never be published: {item.source}"
            )

    expected = default_plan(repository_root)
    if plan != expected:
        raise PublishError(
            "publication paths do not match the fixed default-resume plan"
        )


def find_pdfinfo() -> str:
    executable = shutil.which("pdfinfo")
    if executable is None:
        raise PublishError(
            "pdfinfo was not found in PATH; install Poppler utilities before publishing"
        )
    return executable


def run_pdfinfo(executable: str, path: Path, *arguments: str) -> str:
    completed = subprocess.run(
        [executable, *arguments, str(path)],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        details = (completed.stderr or completed.stdout).strip()
        raise PublishError(
            f"invalid PDF {path}: {details or 'pdfinfo returned an error'}"
        )
    return completed.stdout


def parse_page_count(output: str, path: Path) -> int:
    match = re.search(r"^Pages:\s+(\d+)\s*$", output, re.MULTILINE)
    if match is None:
        raise PublishError(f"could not determine page count for {path}")
    return int(match.group(1))


def parse_page_size(output: str, path: Path, page_number: int) -> tuple[float, float]:
    match = re.search(
        r"^Page(?:\s+\d+)?\s+size:\s+([0-9.]+)\s+x\s+([0-9.]+)\s+pts",
        output,
        re.MULTILINE,
    )
    if match is None:
        raise PublishError(
            f"could not determine page {page_number} size for {path}"
        )
    return float(match.group(1)), float(match.group(2))


def is_a4(width: float, height: float) -> bool:
    dimensions = sorted((width, height))
    expected = sorted((A4_WIDTH_POINTS, A4_HEIGHT_POINTS))
    return all(
        abs(actual - target) <= A4_TOLERANCE_POINTS
        for actual, target in zip(dimensions, expected)
    )


def inspect_pdf(path: Path, pdfinfo: str) -> PdfDetails:
    if not path.is_file():
        raise PublishError(f"source PDF not found: {path}")
    size = path.stat().st_size
    if size == 0:
        raise PublishError(f"source PDF is empty: {path}")
    with path.open("rb") as stream:
        if stream.read(5) != b"%PDF-":
            raise PublishError(f"source does not have a PDF signature: {path}")

    output = run_pdfinfo(pdfinfo, path)
    pages = parse_page_count(output, path)
    if pages != REQUIRED_PAGE_COUNT:
        raise PublishError(
            f"source PDF must have exactly {REQUIRED_PAGE_COUNT} pages; "
            f"found {pages}: {path}"
        )

    for page_number in range(1, pages + 1):
        page_output = run_pdfinfo(
            pdfinfo, path, "-f", str(page_number), "-l", str(page_number)
        )
        width, height = parse_page_size(page_output, path, page_number)
        if not is_a4(width, height):
            raise PublishError(
                f"page {page_number} is not A4 ({width:g} x {height:g} pts): {path}"
            )

    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return PdfDetails(size=size, pages=pages, sha256=digest)


def validate_sources(
    plan: tuple[PublicationItem, ...], pdfinfo: str
) -> dict[str, PdfDetails]:
    details = {item.language: inspect_pdf(item.source, pdfinfo) for item in plan}
    if details["EN"].sha256 == details["PT"].sha256:
        raise PublishError("EN and PT source PDFs must be different files")
    return details


def relative_display(path: Path, repository_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(repository_root.resolve()))
    except ValueError:
        return str(path)


def show_plan(
    plan: tuple[PublicationItem, ...],
    details: dict[str, PdfDetails],
    repository_root: Path,
    output: TextIO,
) -> None:
    print("Publish default public resumes?", file=output)
    for item in plan:
        pdf = details[item.language]
        print(file=output)
        source = relative_display(item.source, repository_root)
        print(f"{item.language}: {source}", file=output)
        print(f" -> {relative_display(item.destination, repository_root)}", file=output)
        print(f" size: {pdf.size} bytes", file=output)
        print(f" pages: {pdf.pages}", file=output)


def replace_with_rollback(
    plan: tuple[PublicationItem, ...],
    replace_file: Callable[[Path, Path], None] = os.replace,
) -> None:
    destination_dir = plan[0].destination.parent
    destination_dir.mkdir(parents=True, exist_ok=True)
    if any(item.destination.parent != destination_dir for item in plan):
        raise PublishError("all public resume destinations must share one directory")

    with tempfile.TemporaryDirectory(
        prefix="resume-publish-", dir=destination_dir
    ) as temp:
        temporary_dir = Path(temp)
        backups: dict[Path, Path | None] = {}
        staged: dict[Path, Path] = {}
        for item in plan:
            backup = temporary_dir / f"backup-{item.destination.name}"
            if item.destination.exists():
                shutil.copy2(item.destination, backup)
                backups[item.destination] = backup
            else:
                backups[item.destination] = None
            staged_path = temporary_dir / f"new-{item.destination.name}"
            shutil.copy2(item.source, staged_path)
            staged[item.destination] = staged_path

        try:
            for item in plan:
                replace_file(staged[item.destination], item.destination)
        except Exception as publish_error:
            rollback_errors = []
            for item in plan:
                backup = backups[item.destination]
                try:
                    if backup is None:
                        item.destination.unlink(missing_ok=True)
                    else:
                        os.replace(backup, item.destination)
                except OSError as rollback_error:
                    rollback_errors.append(f"{item.destination}: {rollback_error}")
            if rollback_errors:
                raise PublishError(
                    "publication failed and rollback was incomplete: "
                    + "; ".join(rollback_errors)
                ) from publish_error
            raise PublishError(
                f"publication failed; both public PDFs were restored: {publish_error}"
            ) from publish_error


def publish(
    *,
    repository_root: Path = REPOSITORY_ROOT,
    assume_yes: bool = False,
    input_func: Callable[[str], str] = input,
    output: TextIO = sys.stdout,
    replace_file: Callable[[Path, Path], None] = os.replace,
) -> bool:
    plan = default_plan(repository_root)
    validate_fixed_paths(plan, repository_root)
    pdfinfo = find_pdfinfo()
    details = validate_sources(plan, pdfinfo)
    show_plan(plan, details, repository_root, output)

    if not assume_yes:
        answer = input_func("\nType YES to continue: ")
        if answer != "YES":
            print("Publication cancelled; public PDFs were not changed.", file=output)
            return False

    replace_with_rollback(plan, replace_file)
    print("Default public resumes published successfully.", file=output)
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Publish approved default resume PDFs to assets/doc/."
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="explicitly approve non-interactive publication",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        published = publish(assume_yes=args.yes)
    except (PublishError, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0 if published else 1


if __name__ == "__main__":
    raise SystemExit(main())
