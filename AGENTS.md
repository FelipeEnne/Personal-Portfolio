# AGENTS.md

## Project Purpose

This repository manages Felipe Enne's professional profile, personal portfolio,
resume generation, and supporting career data.

The main goals are:

1. Maintain a canonical and structured professional history.
2. Keep the public portfolio synchronized with canonical career data.
3. Maintain general public resumes in Portuguese and English.
4. Generate separate resumes tailored to specific job opportunities.
5. Prevent inconsistencies between resume, portfolio, LinkedIn, GitHub, and
   supporting documents.
6. Use Codex to assist with maintenance and generation without inventing,
   inflating, or rewriting career history.

The `career/` directory is the canonical source of truth.

---

# Core Architecture

The project separates career facts, presentation, generated artifacts, and
job-specific customization.

```text
career/*.yaml
      │
      ├──────────────► Public Portfolio
      │
      ├──────────────► General Public Resume EN/PT
      │
      └──────────────► Job-Specific Resumes
                             │
                             └── job description affects emphasis only
```

The core principle is:

```text
career/*.yaml = what is true
docs/CV/      = how resumes look
job input     = what should be emphasized
portfolio     = general public professional profile
```

A job description must never modify canonical career facts.

---

# Repository Areas

## Canonical Career Data

Structured professional data lives under:

* `career/profile.yaml`
* `career/experience.yaml`
* `career/projects.yaml`
* `career/education.yaml`
* `career/certifications.yaml`

These files are the canonical professional records.

---

## Supporting Evidence

Supporting documents may exist under:

* `career/certifications/`

This directory may contain:

* course completion certificates;
* professional certifications;
* educational records;
* hackathon participation;
* awards;
* other supporting evidence.

These files are evidence only.

They are not automatically:

* resume entries;
* professional certifications;
* professional experience;
* proof of advanced proficiency.

Do not move, rename, publish, delete, or modify supporting evidence unless
explicitly requested.

---

## Resume Templates

Canonical resume templates live under:

* `docs/CV/template-en.docx`
* `docs/CV/template-pt.docx`

These files define the visual presentation of generated resumes.

They do NOT define canonical factual content.

Never overwrite these templates during resume generation.

---

## Public Resume Files

The portfolio currently exposes:

* `assets/doc/CV.pdf`
* `assets/doc/Currículo.pdf`

These are public, general-purpose resumes.

They must represent the candidate's overall professional profile.

They must NOT be customized for individual job applications.

Replacing these files is a publication operation and must be explicit.

---

## Generated Resume Artifacts

Generated files belong under:

`generated/resumes/`

Current default DOCX and PDF outputs are written under
`generated/resumes/default/`. Resume contexts remain directly under
`generated/resumes/`.

The job-specific workflow organizes artifacts as:

```text
generated/resumes/
├── default/
│   ├── Felipe_Enne_Default_EN.docx
│   ├── Felipe_Enne_Default_EN.pdf
│   ├── Felipe_Enne_Default_PT.docx
│   └── Felipe_Enne_Default_PT.pdf
│
└── jobs/
    ├── Company_A/
    │   └── Felipe_Enne_Backend_Engineer_EN.pdf
    │
    └── Company_B/
        └── Felipe_Enne_Data_Engineer_EN.pdf
```

Generated files are artifacts and should normally remain outside Git.

The `.gitkeep` file may remain tracked.

---

# Source of Truth

Files under `career/*.yaml` are authoritative.

External sources may include:

* LinkedIn;
* GitHub;
* existing resumes;
* certificates;
* course completion documents;
* portfolio content;
* other professional records.

External sources may be used to:

* discover information;
* verify information;
* identify inconsistencies;
* provide supporting evidence.

External sources must NOT silently overwrite canonical career data.

If an external source conflicts with canonical data:

1. identify the conflict;
2. report the conflicting values;
3. preserve the existing canonical value;
4. request human confirmation when factual interpretation is required;
5. update canonical data only after approval.

Never resolve conflicting career facts by guessing.

---

# Evidence Hierarchy

Use evidence strength when interpreting technologies, skills, and professional
claims.

## Level 1 — Professional Experience

Primary source:

`career/experience.yaml`

This is the strongest evidence.

A technology listed in a professional experience may support a claim of
professional experience with that technology.

Example:

GraphQL appears in the Kuadro professional experience.

Valid:

> Professional experience with GraphQL.

---

## Level 2 — Practical Project Experience

Primary source:

`career/projects.yaml`

Projects demonstrate practical use.

Project use must not automatically be presented as professional employment
experience.

Example:

Databricks is used in GitHub Activity Lakehouse.

Valid:

> Practical project experience with Databricks.

Invalid unless supported by `experience.yaml`:

> Professional Databricks experience.

---

## Level 3 — Education

Primary source:

`career/education.yaml`

Education demonstrates:

* academic study;
* structured learning;
* formal exposure.

Education must not be converted into professional work experience.

---

## Level 4 — Courses and Supporting Evidence

Primary supporting source:

`career/certifications/`

Course completion documents demonstrate:

* study;
* exposure;
* completion of training.

A certificate alone does NOT prove:

* professional experience;
* production experience;
* advanced proficiency;
* expert-level knowledge;
* years of experience.

Never infer proficiency level solely from a course certificate.

---

# Skill Interpretation

A skill may have different evidence strength.

Examples:

## Databricks

Current evidence may include:

* formal course material;
* practical use in GitHub Activity Lakehouse.

Interpretation:

> Practical project experience with Databricks.

Do not describe it as professional Databricks experience unless professional
evidence is added to `career/experience.yaml`.

---

## GraphQL

Evidence includes professional use in Kuadro.

Interpretation:

> Professional experience with GraphQL.

---

# profile.yaml

`career/profile.yaml` contains:

* identity;
* professional title;
* general summary;
* contact information;
* links;
* general skill inventory.

Skills listed in `profile.yaml` are not automatically evidence of professional
experience.

When determining evidence strength, inspect in this order:

1. `experience.yaml`
2. `projects.yaml`
3. `education.yaml`
4. supporting evidence

Do not automatically remove a skill because structured evidence is currently
missing.

Instead:

* preserve the skill;
* report missing evidence when relevant;
* avoid overstating its level.

---

# Resume Context Layer

Resume generation uses an intermediate structured context.

Current implemented flow:

```text
career/*.yaml
      │
      ▼
resume/scripts/build_context.py
      │
      ▼
generated/resumes/resume-context-*.json
      │
      ▼
resume/scripts/render_docx.py
      │
      ▼
generated/resumes/default/*.docx
      │
      ▼
resume/scripts/render_pdf.py
      │
      ▼
generated/resumes/default/*.pdf
```

Current schema:

`resume/schema/resume-context.schema.json`

The context layer exists to separate:

* canonical career data;
* selection logic;
* resume rendering.

The context should contain already-selected presentation data such as:

* language;
* candidate;
* title;
* contact;
* links;
* summary;
* skills;
* experiences;
* education;
* projects;
* eligible certifications.

The context is generated data.

It is NOT canonical career history.

Never edit canonical career facts by modifying generated context files.

---

# General Public Resume

The general public resume represents Felipe's overall professional profile.

It is not optimized for one company or one vacancy.

Default public resumes should remain balanced across the strongest areas of the
professional profile.

They may include:

* strongest professional experience;
* strongest technical skills;
* important recent technologies;
* selected representative projects;
* education;
* strategically relevant professional certifications.

The default resume may use:

`featured: true`

as a strong signal for default project selection.

However, final selection should remain balanced and appropriate for a general
professional profile.

---

# Public Resume Refresh Rules

The public resume should normally be refreshed when canonical career information
changes meaningfully.

Examples:

* new employment;
* substantial role change;
* important new project;
* important new skill with meaningful evidence;
* updated professional summary;
* major education update;
* recognized professional certification;
* outdated project selection.

A job application by itself is NOT a reason to update the public resume.

---

# Job-Specific Resumes

Job-specific resumes are separate generated artifacts.

The implemented deterministic context builder is:

`resume/scripts/build_job_context.py`

The complete one-command job workflow is:

`resume/scripts/build_job_resume.py`

It runs the context builder, measured capacity expansion
(`resume/scripts/expand_job_context.py`), DOCX rendering, and PDF rendering in
that order. Job descriptions live under `resume/jobs/` and are private
relevance inputs; generated job contexts, DOCX files, and PDFs remain local
artifacts under `generated/resumes/jobs/<slug>/`.

It accepts a temporary plain-text job description, resolves only canonical
skills and facts, records evidence strength, and writes exclusively below
`generated/resumes/jobs/<slug>/`. Job descriptions are relevance inputs, not
career evidence or canonical data.

They must be written under:

`generated/resumes/jobs/`

They must never automatically replace:

* `assets/doc/CV.pdf`
* `assets/doc/Currículo.pdf`

They must never automatically modify the public portfolio.

---

## What a Job Description May Influence

A job description may influence:

* professional summary emphasis;
* skill ordering;
* selected skills;
* selected professional highlights;
* selected projects;
* project ordering;
* project highlights;
* wording emphasis;
* which valid evidence receives more prominence.

---

## What a Job Description Must Never Change

A job description must never create or alter:

* companies;
* job titles;
* dates;
* employment history;
* education;
* technologies actually used;
* project facts;
* certifications;
* achievements;
* metrics;
* years of experience.

The job description is a relevance signal, not a source of career facts.

---

## Job-Specific Selection

When generating a resume for a job:

1. analyze the job description;
2. identify important technologies and responsibilities;
3. compare them against canonical career data;
4. determine evidence strength;
5. rank relevant professional experience;
6. select relevant existing highlights;
7. select relevant projects;
8. prioritize relevant skills;
9. keep the result factual;
10. keep the resume concise and readable.

Prefer stronger evidence over keyword matching.

Example:

If a job requests Databricks:

* prioritize GitHub Activity Lakehouse;
* prioritize Databricks, PySpark, Spark, and Delta Lake;
* do not claim professional Databricks experience.

If a job requests GraphQL:

* Kuadro may receive additional emphasis because GraphQL has professional
  evidence there.

---

# Public Portfolio

The public portfolio represents the general professional profile.

It must not be customized for individual vacancies.

The portfolio should eventually consume canonical data from:

`career/*.yaml`

The intended architecture is:

```text
career/*.yaml
      │
      ▼
portfolio/config/default.yaml
      │
      ▼
portfolio/scripts/build_context.py
      │
      ▼
generated/portfolio/portfolio-context-*.json
      │
      ▼
general public portfolio
```

Job descriptions must never influence the public portfolio.

`portfolio/config/default.yaml` controls general portfolio presentation,
including selection, order, visibility, and visual asset mapping. It is not a
source of professional facts.

Portfolio context JSON files are generated artifacts, not canonical data.
Professional facts must continue to come from `career/*.yaml`.

Project images are visual presentation configuration. They are not canonical
professional facts and should not be inferred from career data.

`portfolio/templates/index.html` is the visual template for static portfolio
generation. It is not a source of professional facts. Generated portfolio
contexts provide professional content to `portfolio/scripts/render_site.py`,
which writes the static EN/PT site under `_site/`.

`_site/` is generated output and must not be treated as canonical data or
edited as the source site. Job descriptions must never influence context or
static site generation for the public portfolio.

---

# Portfolio Content Rules

Portfolio content may include:

* professional profile;
* general skills;
* selected professional experience;
* education;
* featured projects;
* general public resume links.

Featured projects should normally come from:

`career/projects.yaml`

using:

`featured: true`

`featured: false` does not mean a project is invalid or unimportant.

A non-featured project may still provide:

* historical information;
* skill evidence;
* job-specific resume relevance.

Never delete a project solely because it is not featured.

---

# Public Resume Publication

Resume generation and resume publication are separate operations.

Generation:

```text
career/*.yaml
      ↓
resume context
      ↓
generated DOCX
      ↓
generated PDF
```

Publication:

```text
approved generated PDF
      ↓
assets/doc/CV.pdf
or
assets/doc/Currículo.pdf
```

Publishing must require an explicit action.

`resume/scripts/publish_default.py` is the only official operation for
publishing the approved general EN/PT resumes to `assets/doc/`. It uses fixed
default-resume paths and requires explicit confirmation (interactive `YES` or
an intentionally supplied `--yes`). Resume generation and public publication
must remain separate operations.

Job-specific resumes must never be published through `publish_default.py`.

Never automatically overwrite public resume PDFs after:

* job-specific generation;
* testing;
* context generation;
* DOCX rendering.

---

# Resume Template Rules

The existing DOCX resumes under `docs/CV/` are the canonical visual templates.

Generated resumes should preserve their visual identity as closely as
practical.

---

## Preserve Visual Characteristics

Unless explicitly requested otherwise, preserve:

* A4 page size;
* margins;
* typography;
* font sizes;
* colors;
* heading hierarchy;
* spacing;
* visual density;
* header structure;
* section styling;
* bullet styling;
* alignment;
* hyperlink styling;
* general section organization.

The resume generator should adapt content, not redesign the resume.

---

## Template Content Is Not Canonical Data

Historical text inside the DOCX templates must not be treated as career truth.

The template provides:

* formatting;
* layout;
* paragraph structure;
* visual identity.

The resume context provides:

* factual content;
* project selection;
* experience selection;
* skills;
* summary;
* links.

Example:

If the Portuguese template historically contains Wine Recommendation while the
English template contains GitHub Activity Lakehouse, that difference must not be
treated as a permanent template rule.

Current content selection must come from canonical career data.

---

# Resume Structure

The default logical resume structure is:

1. Header / Contact
2. Professional Summary
3. Technical Skills
4. Professional Experience
5. Education
6. Project Work

Do not introduce new sections automatically.

A new section should require a clear reason.

Course completion certificates must not automatically create a
"Certifications" section.

---

# Page Count

The default target is the same page count as the current canonical resume.

Prefer a maximum of 2 pages.

When content is too long:

1. prioritize relevance;
2. remove lower-value details;
3. reduce the number of selected highlights;
4. reduce the number of projects;
5. shorten wording without changing meaning.

Do not:

* invent shorter facts;
* shrink readability excessively;
* redesign the template merely to fit more information.

Content selection should solve pagination before visual degradation.

---

# Hyperlinks

Hyperlinks in generated DOCX files must remain functional hyperlinks.

This applies to:

* email;
* GitHub;
* LinkedIn;
* Medium;
* portfolio;
* project repositories;
* project demos;
* other valid project links.

Do not render a URL merely as blue text when a real DOCX hyperlink can be
created.

If a canonical URL is null or missing, do not invent one.

---

# Resume Certifications

Course completion certificates should not normally appear in resumes.

A certification should only be considered for resume display when:

1. it is professionally recognized or strategically relevant;
2. it is relevant to the resume purpose;
3. the structured entry contains:

`resume_eligible: true`

`featured` and `resume_eligible` are independent.

`featured: true` does NOT imply resume eligibility.

Potential future examples of resume-eligible professional certifications:

* AWS certifications;
* Databricks certifications;
* Microsoft Azure certifications;
* Salesforce certifications;
* Google Cloud certifications.

Course completion certificates normally remain supporting evidence.

---

# Data Normalization

Prefer canonical technology names.

Examples:

* `Databricks`
* `QlikView`
* `REST APIs`
* `GraphQL`
* `Node.js`
* `GitHub Actions`
* `Docker Compose`
* `PySpark`

Avoid introducing duplicate names for the same technology.

Before creating a new technology label:

1. inspect existing YAML files;
2. reuse an existing canonical spelling when possible.

Do not perform broad automatic renaming without approval.

---

# Career Data Editing Rules

When modifying `career/*.yaml`:

1. inspect existing data first;
2. preserve IDs whenever possible;
3. preserve factual information;
4. avoid unnecessary rewriting;
5. report factual conflicts;
6. do not silently make assumptions;
7. keep YAML machine-readable;
8. change only the necessary files.

All `.yaml` files must remain valid YAML.

Never place Markdown fences inside YAML files.

Incorrect files contain literal Markdown fence lines such as ` ```yaml ` at
the beginning and ` ``` ` at the end.

Correct:

```text
experiences:
  - id: example
```

---

# Dates

Never guess dates.

If sources disagree:

1. preserve the canonical value;
2. record or report the conflict;
3. request human confirmation before changing it.

Use `null` rather than an invented date.

---

# Metrics and Achievements

Never invent quantitative achievements.

Examples that require evidence:

* percentage improvements;
* revenue impact;
* latency reduction;
* cost reduction;
* user growth;
* transaction volume;
* productivity improvements;
* number of users;
* project scale.

If no verified metric exists, use a factual qualitative description instead.

---

# External Sources

External sources may be used for validation and discovery.

Examples:

* LinkedIn;
* GitHub;
* resume PDFs;
* certificates;
* portfolio pages.

Treat them as evidence, not automatic truth.

---

## GitHub

GitHub is especially useful for verifying:

* project existence;
* repository structure;
* technologies;
* implementation;
* tests;
* CI/CD;
* documentation;
* architecture;
* project status.

GitHub project evidence demonstrates practical implementation.

It does not automatically demonstrate professional employment experience.

---

## LinkedIn

LinkedIn may be used to:

* compare career history;
* discover missing entries;
* confirm public descriptions;
* identify date or title inconsistencies.

LinkedIn must not silently overwrite canonical YAML values.

---

## Existing Resume PDFs

Existing resume PDFs are presentation references and historical outputs.

They may help verify how information has previously been presented.

They are not canonical structured data.

---

# Supporting Certificates

Documents under `career/certifications/` are primarily supporting evidence.

Examples:

* Databricks course completion;
* Docker course completion;
* GraphQL course completion;
* React/Redux training;
* SQL training;
* Python/Data Science training;
* Microverse modules;
* hackathon participation.

They may confirm learning or exposure.

They must never automatically become:

* professional experience;
* certification sections;
* claims of expertise.

---

# Language

Canonical structured data may contain English and Portuguese versions.

Generated resumes support:

* `en`
* `pt`

For generated content:

* use the requested language;
* preserve company names;
* preserve proper names;
* preserve technology names;
* do not translate technologies unnecessarily.

Translations should come from canonical localized fields or be prepared in the
resume context layer from canonical text. The DOCX renderer must consume the
context as provided and must not translate content independently.

Do not create facts merely to fill a missing translation. When no canonical or
approved translation exists, preserve the available source text and report the
limitation when relevant.

---

# Current Resume Generation Tools

The resume generator currently includes:

* `resume/scripts/build_context.py`
* `resume/scripts/build_job_context.py`
* `resume/scripts/expand_job_context.py`
* `resume/scripts/build_job_resume.py`
* `resume/scripts/render_docx.py`
* `resume/scripts/render_pdf.py`
* `resume/schema/resume-context.schema.json`
* `resume/schema/job-resume-context.schema.json`
* `resume/requirements.txt`

Current required Python dependencies:

* PyYAML
* jsonschema

Use `python3` for commands in this environment unless another interpreter is
explicitly configured.

Examples:

```bash
python3 resume/scripts/build_context.py --lang en
python3 resume/scripts/build_context.py --lang pt
python3 resume/scripts/render_docx.py --lang en
python3 resume/scripts/render_docx.py --lang pt
python3 resume/scripts/render_pdf.py --lang en
python3 resume/scripts/render_pdf.py --lang pt
```

Do not assume that the `python` alias exists.

---

# Current DOCX and PDF Rendering

The implemented rendering flow is:

```text
resume-context.json
      │
      ▼
docs/CV/template-*.docx
      │
      ▼
generated/resumes/default/*.docx
      │
      ▼
resume/scripts/render_pdf.py
      │
      ▼
generated/resumes/default/*.pdf
```

Job-specific contexts reuse the same DOCX templates and renderers, but every
context, DOCX, and PDF must remain under `generated/resumes/jobs/<slug>/`.
`render_docx.py` may infer language and output from `--context`, and
`render_pdf.py` may infer output from `--input`. A PDF over two pages must be
reported; fonts and margins must not be reduced automatically.

Prefer modifying/filling the existing DOCX templates rather than recreating
resume layout from scratch.

The original templates must remain unchanged. PDF conversion must operate only
on generated DOCX files and must not publish to `assets/doc/` automatically.

---

# Generated Files

Generated artifacts should normally be ignored by Git.

This includes:

* `generated/resumes/*.json`
* `generated/resumes/*.docx`
* `generated/resumes/*.pdf`

The current `.gitignore` rules cover generated artifacts recursively, including
the `default/` and `jobs/` output directories, while preserving
`generated/resumes/.gitkeep`.

Source code, templates, schemas, configuration, and `.gitkeep` files may be
tracked.

---

# Codex Workflow

For significant changes:

1. inspect relevant files;
2. understand the requested scope;
3. identify factual uncertainty;
4. describe proposed changes when appropriate;
5. request approval when factual interpretation is required;
6. modify only necessary files;
7. validate structured data;
8. run relevant tests;
9. run `git diff --check`;
10. inspect `git status`;
11. summarize what changed;
12. do not commit unless explicitly requested.

Never modify unrelated files merely because they were already dirty.

Preserve existing user changes.

---

# Protected Files

Unless explicitly requested, do not overwrite or modify:

* `docs/CV/template-en.docx`
* `docs/CV/template-pt.docx`
* `assets/doc/CV.pdf`
* `assets/doc/Currículo.pdf`

Templates may be read and copied.

Public PDFs may only be replaced during an explicit publication step.

---

# Validation

After changing `career/*.yaml`:

* validate all YAML files with PyYAML;
* verify expected top-level structure;
* detect duplicate IDs when practical;
* run `git diff --check`;
* inspect the resulting diff.

After generating resume contexts:

* validate JSON syntax;
* validate against `resume-context.schema.json`;
* verify IDs and selection invariants.

After rendering DOCX:

* confirm templates remain unchanged;
* verify page dimensions and margins;
* verify hyperlinks;
* verify section structure;
* inspect for stale template content;
* verify that generated content originated from the resume context.

---

# Commit Policy

Do not create Git commits unless explicitly requested.

When asked to commit:

* include only relevant files;
* do not accidentally stage generated artifacts;
* do not stage unrelated pre-existing modifications.

Prefer focused commits.

Example categories:

```text
feat: add resume generation foundation
feat: add DOCX resume renderer
feat: add job-specific resume generation
feat: generate portfolio from career data
docs: update Codex career rules
chore: normalize career data
```

---

# General Principle

The system should optimize presentation, not rewrite history.

It may:

* select;
* prioritize;
* rank;
* summarize;
* reorder;
* tailor;
* translate;
* format.

It must not:

* fabricate;
* inflate;
* exaggerate;
* invent metrics;
* invent experience;
* convert study into professional experience;
* convert projects into employment;
* convert course completion into professional certification;
* silently resolve factual conflicts.

When uncertain:

1. preserve canonical data;
2. state the uncertainty;
3. request human confirmation when needed.

Accuracy has priority over keyword matching.

Career truth has priority over job-description optimization.

The public portfolio and public resume represent the general professional
profile.

Job-specific resumes are temporary tailored views of the same canonical career
history and must remain separate from public portfolio publication.
