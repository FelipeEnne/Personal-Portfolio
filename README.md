# Personal Portfolio

Felipe Enne's bilingual static portfolio and resume generation project.

Live site: [felipeenne.github.io/Personal-Portfolio](https://felipeenne.github.io/Personal-Portfolio/)

## Capabilities

- Canonical professional data in `career/*.yaml`.
- Static EN/PT portfolio for GitHub Pages.
- Public/default and job-specific resume generation.
- Deterministic, evidence-based matching, ranking, and two-page expansion.
- DOCX/PDF output, automated tests, and explicit public publication.

## Architecture

```text
career/*.yaml
  ├── portfolio  ──> _site/ ──> GitHub Pages
  ├── default resume ──> generated/resumes/default/
  └── job resume + description ──> generated/resumes/jobs/<slug>/
```

The public resume PDFs in `assets/doc/` are updated only by the explicit
publication step. See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the
full architecture and [`resume/README.md`](resume/README.md) for resume details.

## Quick start

Install dependencies as needed, then use the Makefile:

```bash
make test
make portfolio
make resume-job-pt JOB=resume/jobs/vaga.txt
```

## Main commands

```bash
make portfolio
make resume-job-pt
make resume-job-en
make resume-default-pt
make resume-default-en
make test
make clean
```

Job-specific outputs stay in `generated/resumes/jobs/<slug>/`. Default resume
targets generate files in `generated/resumes/default/` but never publish them.

## Documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — current system architecture.
- [`portfolio/README.md`](portfolio/README.md) — static portfolio pipeline.
- [`resume/README.md`](resume/README.md) — resume generation and publication.
- [`AGENTS.md`](AGENTS.md) — repository safety and source-of-truth rules.

## License

Distributed under the MIT License. See `LICENSE` for more information.
