# [AGENTS.md](http://AGENTS.md)

## Project Purpose

This repository is Felipe Enne's personal career and portfolio repository.

Its long-term goals are:

1. Maintain a canonical structured career history.
2. Generate resumes tailored to specific job descriptions.
3. Update the personal portfolio from the same career data.
4. Prevent inconsistencies between resume, portfolio, LinkedIn and GitHub.
5. Use Codex to assist with career-data maintenance without inventing information.

The `career/` directory is the canonical source of truth.

---

# Career Data

The main structured career data lives in:

- `career/profile.yaml`
- `career/experience.yaml`
- `career/projects.yaml`
- `career/education.yaml`
- `career/certifications.yaml`

Supporting documents may exist under:

- `career/certifications/`

PDFs and other supporting documents are evidence only.

They are not automatically part of the resume or portfolio.

---



# Source of Truth

Files under `career/*.yaml` are the canonical career records.

External sources such as:

- LinkedIn
- GitHub
- existing resumes
- certificates
- course completion documents

may be used to identify new information or inconsistencies.

They must NOT silently overwrite canonical career data.

If an external source conflicts with the canonical data:

1. identify the conflict;
2. report it;
3. preserve the existing canonical value;
4. wait for human approval before changing it.

Never resolve conflicting career facts by guessing.

---



# Evidence Hierarchy

Use the following hierarchy when determining the strength of a technical skill or career claim.

## 1. Professional Experience

Source:

`career/experience.yaml`

This is the strongest evidence.

A technology listed in a professional experience may be described as professional experience.

Example:

GraphQL used at Kuadro can support a claim of professional GraphQL experience.

---



## 2. Practical Project Experience

Source:

`career/projects.yaml`

Projects demonstrate practical experience but must not automatically be described as professional experience.

Example:

Databricks used in the GitHub Activity Lakehouse demonstrates practical project experience.

Do not describe it as professional Databricks experience unless it also appears in `career/experience.yaml`.

---



## 3. Education

Source:

`career/education.yaml`

Education demonstrates formal study or academic exposure.

Do not convert academic study into professional experience.

---



## 4. Courses and Supporting Certificates

Sources may include:

`career/certifications/`

Course completion certificates demonstrate study or exposure.

A certificate alone does NOT prove:

- professional experience;
- production experience;
- advanced proficiency;
- years of experience.

Never infer proficiency level solely from a course certificate.

---



# Skill Interpretation

Examples:

## Databricks

Evidence may include:

- a Databricks course;
- practical use in the GitHub Activity Lakehouse.

Valid interpretation:

> Practical project experience with Databricks.

Invalid interpretation:

> Professional Databricks experience.

unless professional evidence is added to `experience.yaml`.

## GraphQL

Evidence includes professional use in the Kuadro experience.

Valid interpretation:

> Professional experience with GraphQL.

---



# profile.yaml

`career/profile.yaml` contains the general professional profile and skill inventory.

A skill appearing in `profile.yaml` should not by itself be treated as proof of professional experience.

When possible, determine the strength of the skill using:

1. `experience.yaml`
2. `projects.yaml`
3. `education.yaml`
4. supporting evidence

Do not remove a skill merely because it does not currently have structured evidence.

Instead, report missing evidence when relevant.

---



# Resume Generation Rules

Generated resumes must be factual.

Never invent:

- technologies;
- companies;
- responsibilities;
- projects;
- dates;
- certifications;
- achievements;
- metrics;
- years of experience.

A job description may influence:

- ordering;
- emphasis;
- selected skills;
- selected projects;
- selected highlights;
- wording.

A job description must never create new career facts.

---



## Job-Tailored Resumes

When generating a resume for a job:

1. analyze the job description;
2. identify important technologies and responsibilities;
3. compare them with canonical career data;
4. rank existing evidence by relevance;
5. select the strongest relevant experience;
6. select the strongest relevant projects;
7. prioritize relevant skills;
8. preserve factual dates, companies and responsibilities.

Prefer stronger evidence over keyword matching.

Example:

If a job asks for Databricks:

- highlight GitHub Activity Lakehouse;
- highlight PySpark, Delta Lake and Databricks;
- do not claim professional Databricks experience.

If a job asks for GraphQL:

- Kuadro may be prioritized because GraphQL has professional evidence there.

---



# Resume Certifications

Do not automatically add course-completion certificates to resumes.

A certification should only be considered for resume display when:

1. it is professionally recognized or otherwise strategically relevant;
2. it is relevant to the target job;
3. its structured entry contains:

`resume_eligible: true`

`featured` and `resume_eligible` have different meanings.

`featured` does NOT automatically make something resume-eligible.

Examples of certifications that may eventually be eligible:

- AWS certifications
- Databricks professional certifications
- Microsoft Azure certifications
- Salesforce certifications
- Google Cloud certifications

Course-completion documents normally remain supporting evidence only.

---



# Portfolio Rules

The portfolio should eventually be generated from the canonical career data.

Do not duplicate career facts manually when a structured source already exists.

The intended architecture is:

career YAML
    ↓
generation scripts
    ↓
portfolio
    ↓
resume outputs

Featured projects should normally come from:

`career/projects.yaml`

using:

`featured: true`

However, job-specific resumes may use non-featured projects when they are more relevant.

---



# Project Selection

`featured: true` means a project is a strong candidate for the default portfolio.

`featured: false` means the project remains part of career history and may still be useful for:

- job-specific resumes;
- evidence of technologies;
- historical portfolio information.

Never delete a project solely because it is not featured.

---



# Data Normalization

Prefer consistent technology names.

Examples:

- `Databricks`
- `QlikView`
- `REST APIs`
- `GraphQL`
- `Node.js`
- `GitHub Actions`

Avoid creating multiple names for the same technology.

Before introducing a new technology label, check existing YAML files.

---



# Career Data Editing Rules

When modifying career data:

1. inspect the existing YAML first;
2. preserve existing IDs whenever possible;
3. preserve factual information;
4. avoid unnecessary rewriting;
5. report conflicts before resolving them;
6. do not silently add assumptions;
7. keep YAML machine-readable.

All `.yaml` files must remain valid YAML.

Do not add Markdown fences such as:

```text
```yaml
```

inside YAML files.

---

# Dates

Do not guess dates.

If different sources disagree:

- preserve the canonical value;
- record or report the conflict;
- ask for human confirmation before changing it.

Null is preferable to an invented date.

---

# External Sources

External sources can be used for comparison and discovery.

Examples:

- LinkedIn
- GitHub
- resume PDFs
- certificates

Treat external sources as evidence, not automatic truth.

GitHub is especially useful for verifying:

- project existence;
- technologies;
- architecture;
- implementation;
- tests;
- CI/CD;
- documentation.

Do not infer professional experience from a GitHub project.

---

# Supporting Documents

Files under `career/certifications/` may contain:

- course certificates;
- professional certificates;
- education records;
- hackathon participation;
- awards;
- other career evidence.

Do not assume every document in this directory is a professional certification.

Do not move, rename, publish or modify supporting files unless explicitly requested.

---

# Language

Canonical structured data may contain English and Portuguese content.

For generated resumes:

- use the language requested by the user;
- preserve proper names;
- translate descriptions naturally;
- do not translate technology names unnecessarily.

---

# Codex Workflow

For significant career-data changes:

1. inspect relevant sources;
2. describe proposed changes;
3. identify conflicts or uncertainty;
4. wait for approval when factual interpretation is required;
5. modify only the necessary files;
6. validate YAML;
7. run appropriate tests;
8. show the diff;
9. do not commit unless explicitly requested.

---

# Validation

After changing `career/*.yaml`:

- validate all YAML files;
- run `git diff --check`;
- inspect the resulting diff.

Career data changes should never leave invalid YAML.

---

# General Principle

The system should optimize presentation, not rewrite history.

It may:

- select;
- rank;
- summarize;
- reorder;
- tailor;
- format.

It must not:

- fabricate;
- inflate;
- exaggerate;
- convert study into professional experience;
- convert projects into employment;
- invent metrics or achievements.

When uncertain, preserve the source data and report the uncertainty.

```markdown

```



# Resume Template Rules

The existing resume under `docs/CV` is the canonical visual template
for generated resumes.

Generated resumes must preserve the existing resume's visual identity
and general structure.

## Preserve

Unless explicitly requested otherwise, preserve:

- page size;
- margins;
- typography;
- font sizes;
- heading hierarchy;
- spacing;
- visual density;
- header structure;
- section styling;
- bullet styling;
- general section organization.

The resume generator should adapt content, not redesign the resume.

---



## Content That May Change

For job-tailored resumes, the generator may change:

- professional summary;
- ordering of skills;
- selected skills;
- selected experience highlights;
- selected projects;
- project ordering;
- wording used to emphasize relevant existing experience.

All changes must remain grounded in `career/*.yaml`.

---



## Content That Must Not Change Without Evidence

Never change or invent:

- companies;
- job titles;
- employment dates;
- education dates;
- technologies used;
- project facts;
- certifications;
- achievements;
- metrics.

---



## Template vs Generated Files

Files under `docs/CV` that define the base resume must be treated as
templates or reference material.

Do not overwrite the canonical resume template when generating a
job-specific resume.

Generated resumes should be written to a separate output directory,
for example:

`generated/resumes/`

Example:

`generated/resumes/Felipe_Enne_Full_Stack_Developer.pdf`

`generated/resumes/Felipe_Enne_Data_Engineer.pdf`

`generated/resumes/Felipe_Enne_Company_Name.pdf`

---



## Page Count

The default target is the same page count as the canonical resume.

Prefer a maximum of 2 pages.

When tailoring content:

1. prioritize relevance;
2. remove less relevant details;
3. shorten descriptions when necessary;
4. do not reduce readability merely to fit more content.

Do not change the visual template simply to fit additional information.

---



## Resume Structure

Use the structure from the canonical resume in `docs/CV` as the default.

The current logical structure is approximately:

1. Header / Contact
2. Professional Summary
3. Technical Skills
4. Professional Experience
5. Education
6. Project Work

Do not introduce new sections automatically.

A section may only be added when there is a clear reason and the user
approves it.

Course-completion certificates should not create a Certifications
section automatically.

---



## General Principle

`career/*.yaml` controls what the resume says.

`docs/CV` controls how the resume looks.

Job descriptions control what information is emphasized.

A job description must not control or alter factual career history.