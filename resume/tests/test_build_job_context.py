from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from resume.scripts import build_context as base
from resume.scripts import build_job_context as jobs
from resume.scripts import render_docx, render_pdf


FIXTURES = Path(__file__).parent / "fixtures"


class BuildJobContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.canonical = base.load_yaml_files(jobs.CAREER_DIR)

    def build_fixture(self, name: str, language: str = "en") -> dict:
        path = FIXTURES / name
        return jobs.build_job_context(
            self.canonical,
            path.read_text(encoding="utf-8"),
            f"resume/tests/fixtures/{name}",
            jobs.slugify(path.stem),
            language,
        )

    @staticmethod
    def flattened_skills(context: dict) -> list[str]:
        return [item for group in context["skills"] for item in group["items"]]

    def evidence_for(self, context: dict, skill: str) -> dict:
        return next(
            item
            for item in context["job"]["matched_skill_evidence"]
            if item["skill"] == skill
        )

    def test_react_job_can_select_non_featured_project(self) -> None:
        context = self.build_fixture("react-job.txt")
        self.assertIn("React", context["job"]["matched_skills"])
        projects = {project["id"]: project for project in context["projects"]}
        self.assertTrue(
            any(not project["featured"] for project in projects.values())
        )
        self.assertTrue(
            {"info-covid19-app", "find-your-course"}.intersection(projects)
        )

    def test_graphql_uses_professional_kuadro_evidence_and_node_alias(self) -> None:
        context = self.build_fixture("graphql-job.txt")
        self.assertEqual(self.evidence_for(context, "GraphQL")["level"], "professional")
        self.assertIn("kuadro", self.evidence_for(context, "GraphQL")["source_ids"])
        self.assertIn("Node.js", context["job"]["matched_skills"])
        self.assertIn("kuadro", [item["id"] for item in context["experiences"]])

    def test_databricks_is_project_evidence_not_professional_experience(self) -> None:
        context = self.build_fixture("data-job.txt")
        evidence = self.evidence_for(context, "Databricks")
        self.assertEqual(evidence["level"], "project")
        self.assertEqual(evidence["source_ids"], ["github-activity-lakehouse"])
        self.assertEqual(context["projects"][0]["id"], "github-activity-lakehouse")
        self.assertTrue(
            all(
                "Databricks" not in experience["technologies"]
                for experience in context["experiences"]
            )
        )

    def test_unknown_technology_is_never_added(self) -> None:
        context = self.build_fixture("data-job.txt")
        self.assertNotIn("Kubernetes", context["job"]["matched_skills"])
        self.assertNotIn("Kubernetes", self.flattened_skills(context))

    def test_section_headers_are_not_requirements(self) -> None:
        context = self.build_fixture("backend-quality-job.txt")
        requirements = context["job"]["required"]
        self.assertNotIn("Requisitos", requirements)
        self.assertNotIn("Habilidades", requirements)
        self.assertNotIn("Valorizado", requirements)
        self.assertNotIn("Benefícios", requirements)
        self.assertEqual(len(context["job"]["responsibilities"]), 2)
        self.assertNotIn("Assistência médica.", context["job"]["preferred"])

    def test_rest_and_backend_labels_are_deduplicated_for_analysis(self) -> None:
        context = self.build_fixture("backend-quality-job.txt")
        requirements = context["job"]["required"]
        self.assertIn("REST API", requirements)
        self.assertNotIn("RESTful", requirements)
        self.assertIn("Back-end", requirements)
        self.assertNotIn("Backend", requirements)
        self.assertEqual(context["job"]["matched_skills"].count("REST APIs"), 1)

    def test_git_github_and_ci_cd_map_to_canonical_project_evidence(self) -> None:
        context = self.build_fixture("backend-quality-job.txt")
        matched = context["job"]["matched_skills"]
        self.assertIn("Git", matched)
        self.assertIn("GitHub", matched)
        self.assertIn("pytest", matched)
        self.assertIn("GitHub Actions", matched)
        self.assertEqual(self.evidence_for(context, "pytest")["level"], "project")
        self.assertEqual(
            self.evidence_for(context, "GitHub Actions")["level"], "project"
        )
        self.assertTrue(
            all(
                "pytest" not in experience["technologies"]
                and "GitHub Actions" not in experience["technologies"]
                for experience in context["experiences"]
            )
        )

    def test_backend_job_does_not_expand_unmatched_groups(self) -> None:
        context = self.build_fixture("backend-quality-job.txt")
        skills = self.flattened_skills(context)
        for absent in (
            "React", "Redux", "Bootstrap", "GraphQL", "Apache Spark", "PySpark"
        ):
            self.assertNotIn(absent, skills)

    def test_personal_portfolio_does_not_beat_backend_projects_for_git(self) -> None:
        context = self.build_fixture("backend-quality-job.txt")
        project_ids = [project["id"] for project in context["projects"]]
        self.assertEqual(
            project_ids,
            ["github-activity-lakehouse", "audiobook-production-automation"],
        )
        self.assertNotIn("personal-portfolio", project_ids)

    def test_absent_technology_does_not_enter_matched_skills(self) -> None:
        context = self.build_fixture("backend-quality-job.txt")
        self.assertNotIn("MongoDB", context["job"]["matched_skills"])

    def test_company_and_title_remain_null_without_clear_evidence(self) -> None:
        context = self.build_fixture("unlabeled-job.txt")
        self.assertIsNone(context["job"]["company"])
        self.assertIsNone(context["job"]["title"])

    def test_clear_leading_title_is_extracted_without_guessing_company(self) -> None:
        context = self.build_fixture("backend-quality-job.txt")
        self.assertEqual(context["job"]["title"], "Desenvolvedor Backend II (Python)")
        self.assertIsNone(context["job"]["company"])

    def test_context_uses_only_canonical_skill_inventory(self) -> None:
        context = self.build_fixture("data-job.txt")
        inventory = {
            skill
            for values in self.canonical["profile"]["skills"].values()
            for skill in values
        }
        self.assertLessEqual(set(self.flattened_skills(context)), inventory)

    def test_project_is_not_converted_into_experience(self) -> None:
        context = self.build_fixture("data-job.txt")
        canonical_experience_ids = {
            item["id"] for item in self.canonical["experiences"]["experiences"]
        }
        self.assertLessEqual(
            {item["id"] for item in context["experiences"]},
            canonical_experience_ids,
        )
        self.assertNotIn(
            "github-activity-lakehouse",
            {item["id"] for item in context["experiences"]},
        )

    def test_en_and_pt_have_the_same_selected_ids(self) -> None:
        english = self.build_fixture("data-job.txt", "en")
        portuguese = self.build_fixture("data-job.txt", "pt")
        for collection in ("experiences", "education", "projects"):
            self.assertEqual(
                [item["id"] for item in english[collection]],
                [item["id"] for item in portuguese[collection]],
            )

    def test_schema_validation_accepts_job_context(self) -> None:
        jobs.validate_job_context(self.build_fixture("react-job.txt"))

    def test_context_output_cannot_escape_jobs_directory(self) -> None:
        context = self.build_fixture("react-job.txt")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            jobs_dir = root / "generated/resumes/jobs"
            safe = jobs_dir / "react-job/resume-context-en.json"
            jobs.write_job_context(context, safe, jobs_dir)
            self.assertTrue(safe.is_file())
            with self.assertRaisesRegex(jobs.JobContextError, "must stay under"):
                jobs.write_job_context(
                    context, root / "assets/doc/context.json", jobs_dir
                )

    def test_renderers_reject_public_and_template_outputs(self) -> None:
        with self.assertRaisesRegex(render_docx.RenderError, "assets/doc"):
            render_docx.render_docx(
                Path("missing-template.docx"),
                Path("missing-context.json"),
                render_docx.PUBLIC_DOC_DIR / "resume.docx",
                "en",
            )
        with self.assertRaisesRegex(render_pdf.PdfRenderError, "assets/doc"):
            render_pdf.convert_docx_to_pdf(
                Path("missing.docx"), render_pdf.PUBLIC_DOC_DIR / "CV.pdf"
            )

    def test_job_pipeline_does_not_call_publication(self) -> None:
        source = Path(jobs.__file__).read_text(encoding="utf-8")
        self.assertNotIn("publish_default", source)


if __name__ == "__main__":
    unittest.main()
