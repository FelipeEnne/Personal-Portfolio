# Resume context generator

This directory contains the format-independent first stage of the resume
generation pipeline:

```text
career/*.yaml
    -> resume/scripts/build_context.py
    -> generated/resumes/resume-context-<language>.json
    -> DOCX template (future stage)
    -> generated/resumes/*.docx (future stage)
    -> generated/resumes/*.pdf (future stage)
```

`career/*.yaml` remains the only canonical source of career facts. The
generated JSON is an intermediate representation: it does not add facts and
does not contain DOCX-specific formatting instructions. A future vacancy-aware
stage may select and order existing facts, but must not create new ones.

The templates in `docs/CV/` define presentation only. Generating files under
`generated/resumes/` must not replace anything in `assets/doc/`; publishing a
resume to the portfolio is a separate, explicit operation.

## Requirements

- Python 3.10 or newer
- PyYAML

PyYAML can be installed with:

```bash
python -m pip install PyYAML
```

## Usage

From the repository root:

```bash
python resume/scripts/build_context.py --lang en
python resume/scripts/build_context.py --lang pt
```

The default outputs are:

```text
generated/resumes/resume-context-en.json
generated/resumes/resume-context-pt.json
```

Use `--output` to choose another JSON destination:

```bash
python resume/scripts/build_context.py --lang en --output /tmp/resume-context.json
```

Before constructing a context, the script parses every YAML file below
`career/` and performs basic structural validation of the five canonical
files. Errors identify the affected file or field and cause a non-zero exit.

## Selection rules in this version

- All canonical experiences and education records are retained.
- Skills keep their canonical categories and ordering.
- Projects are selected when `featured` is exactly `true`.
- Certifications are selected only when `resume_eligible` is exactly `true`.
- Project evidence remains under `projects`; it is never promoted to
  professional experience.
- Missing optional values are represented consistently as JSON `null`.
- Canonical IDs are retained for experiences, education, projects and
  certifications.

The resulting JSON follows
[`schema/resume-context.schema.json`](schema/resume-context.schema.json).

