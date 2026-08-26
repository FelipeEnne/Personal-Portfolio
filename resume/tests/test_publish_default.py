from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path

from resume.scripts import publish_default


def write_pdf(
    path: Path,
    pages: int = 2,
    marker: str = "test",
    width: float = 595.276,
    height: float = 841.890,
) -> None:
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        (
            "<< /Type /Pages /Kids "
            f"[{' '.join(f'{3 + index * 2} 0 R' for index in range(pages))}] "
            f"/Count {pages} >>"
        ).encode(),
    ]
    for index in range(pages):
        content_number = 4 + index * 2
        objects.extend(
            [
                (
                    f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {width} {height}] "
                    f"/Resources << >> /Contents {content_number} 0 R >>"
                ).encode(),
                f"<< /Length 0 >>\nstream\n\nendstream\n% {marker}-{index}".encode(),
            ]
        )

    document = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, value in enumerate(objects, start=1):
        offsets.append(len(document))
        document.extend(f"{number} 0 obj\n".encode())
        document.extend(value)
        document.extend(b"\nendobj\n")
    xref = len(document)
    document.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    document.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        document.extend(f"{offset:010d} 00000 n \n".encode())
    document.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref}\n%%EOF\n"
        ).encode()
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(document)


class PublishDefaultTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.plan = publish_default.default_plan(self.root)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def prepare_sources(self, *, en_pages: int = 2, pt_pages: int = 2) -> None:
        write_pdf(self.plan[0].source, en_pages, "english")
        write_pdf(self.plan[1].source, pt_pages, "portuguese")

    def prepare_destinations(self) -> tuple[bytes, bytes]:
        old_en = b"old public English PDF"
        old_pt = b"old public Portuguese PDF"
        self.plan[0].destination.parent.mkdir(parents=True, exist_ok=True)
        self.plan[0].destination.write_bytes(old_en)
        self.plan[1].destination.write_bytes(old_pt)
        return old_en, old_pt

    def test_missing_source_is_rejected(self) -> None:
        with self.assertRaisesRegex(publish_default.PublishError, "not found"):
            publish_default.publish(repository_root=self.root, assume_yes=True)

    def test_invalid_pdf_is_rejected(self) -> None:
        self.plan[0].source.parent.mkdir(parents=True)
        self.plan[0].source.write_bytes(b"not a PDF")
        write_pdf(self.plan[1].source, marker="portuguese")
        with self.assertRaisesRegex(publish_default.PublishError, "PDF signature"):
            publish_default.publish(repository_root=self.root, assume_yes=True)

    def test_wrong_page_count_is_rejected(self) -> None:
        self.prepare_sources(en_pages=1)
        with self.assertRaisesRegex(publish_default.PublishError, "exactly 2 pages"):
            publish_default.publish(repository_root=self.root, assume_yes=True)

    def test_empty_pdf_is_rejected(self) -> None:
        self.plan[0].source.parent.mkdir(parents=True)
        self.plan[0].source.write_bytes(b"")
        write_pdf(self.plan[1].source, marker="portuguese")
        with self.assertRaisesRegex(publish_default.PublishError, "empty"):
            publish_default.publish(repository_root=self.root, assume_yes=True)

    def test_identical_language_files_are_rejected(self) -> None:
        write_pdf(self.plan[0].source, marker="same")
        self.plan[1].source.parent.mkdir(parents=True, exist_ok=True)
        self.plan[1].source.write_bytes(self.plan[0].source.read_bytes())
        with self.assertRaisesRegex(publish_default.PublishError, "must be different"):
            publish_default.publish(repository_root=self.root, assume_yes=True)

    def test_non_a4_pdf_is_rejected(self) -> None:
        write_pdf(self.plan[0].source, marker="english", width=612, height=792)
        write_pdf(self.plan[1].source, marker="portuguese")
        with self.assertRaisesRegex(publish_default.PublishError, "not A4"):
            publish_default.publish(repository_root=self.root, assume_yes=True)

    def test_confirmation_other_than_exact_yes_cancels(self) -> None:
        self.prepare_sources()
        old_en, old_pt = self.prepare_destinations()
        result = publish_default.publish(
            repository_root=self.root,
            input_func=lambda _: "yes",
            output=io.StringIO(),
        )
        self.assertFalse(result)
        self.assertEqual(self.plan[0].destination.read_bytes(), old_en)
        self.assertEqual(self.plan[1].destination.read_bytes(), old_pt)

    def test_exact_confirmation_publishes_both_files(self) -> None:
        self.prepare_sources()
        self.prepare_destinations()
        output = io.StringIO()
        result = publish_default.publish(
            repository_root=self.root,
            input_func=lambda _: "YES",
            output=output,
        )
        self.assertTrue(result)
        report = output.getvalue()
        self.assertIn("generated/resumes/default/Felipe_Enne_Default_EN.pdf", report)
        self.assertIn("assets/doc/CV.pdf", report)
        self.assertIn("size:", report)
        self.assertIn("pages: 2", report)
        self.assertEqual(
            self.plan[0].destination.read_bytes(), self.plan[0].source.read_bytes()
        )
        self.assertEqual(
            self.plan[1].destination.read_bytes(), self.plan[1].source.read_bytes()
        )

    def test_failure_during_replace_rolls_back_both_files(self) -> None:
        self.prepare_sources()
        old_en, old_pt = self.prepare_destinations()

        def fail_on_portuguese(source: Path, destination: Path) -> None:
            if destination == self.plan[1].destination:
                raise OSError("simulated replacement failure")
            source.replace(destination)

        with self.assertRaisesRegex(publish_default.PublishError, "restored"):
            publish_default.publish(
                repository_root=self.root,
                assume_yes=True,
                output=io.StringIO(),
                replace_file=fail_on_portuguese,
            )
        self.assertEqual(self.plan[0].destination.read_bytes(), old_en)
        self.assertEqual(self.plan[1].destination.read_bytes(), old_pt)

    def test_job_specific_source_is_rejected(self) -> None:
        unsafe_plan = (
            publish_default.PublicationItem(
                "EN",
                self.root / "generated/resumes/jobs/company/resume.pdf",
                self.root / "assets/doc/CV.pdf",
            ),
            self.plan[1],
        )
        with self.assertRaisesRegex(publish_default.PublishError, "job-specific"):
            publish_default.validate_fixed_paths(unsafe_plan, self.root)


if __name__ == "__main__":
    unittest.main()
