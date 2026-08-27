.PHONY: help test portfolio resume-default-en resume-default-pt resume-job-en resume-job-pt publish-default clean

JOB ?= resume/jobs/vaga.txt

help:
	@echo "Available targets:"
	@echo "  make portfolio"
	@echo "  make resume-default-en"
	@echo "  make resume-default-pt"
	@echo "  make resume-job-pt"
	@echo "  make resume-job-pt JOB=resume/jobs/nortal.txt"
	@echo "  make resume-job-en JOB=resume/jobs/nortal.txt"
	@echo "  make publish-default"
	@echo "  make test"

test:
	python3 -m unittest discover -s resume/tests -v

portfolio:
	python3 portfolio/scripts/build_context.py --lang en
	python3 portfolio/scripts/build_context.py --lang pt
	python3 portfolio/scripts/render_site.py

resume-default-en:
	python3 resume/scripts/build_context.py --lang en
	python3 resume/scripts/render_docx.py --lang en
	python3 resume/scripts/render_pdf.py --lang en

resume-default-pt:
	python3 resume/scripts/build_context.py --lang pt
	python3 resume/scripts/render_docx.py --lang pt
	python3 resume/scripts/render_pdf.py --lang pt

resume-job-en:
	python3 resume/scripts/build_job_resume.py \
		--job $(JOB) \
		--lang en

resume-job-pt:
	python3 resume/scripts/build_job_resume.py \
		--job $(JOB) \
		--lang pt

# Publication is intentionally separate from generation and keeps the
# interactive YES confirmation; never pass --yes here.
publish-default:
	python3 resume/scripts/publish_default.py

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
