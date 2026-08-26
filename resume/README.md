# Resume context generator

This directory contains the format-independent first stage of the resume
generation pipeline:

```text
career/*.yaml
    -> resume/config/default.yaml (general-resume presentation policy)
    -> resume/scripts/build_context.py
    -> generated/resumes/resume-context-<language>.json
    -> resume/scripts/render_docx.py + docs/CV/template-<language>.docx
    -> generated/resumes/default/*.docx
    -> resume/scripts/render_pdf.py
    -> generated/resumes/default/*.pdf
    -> human review
    -> resume/scripts/publish_default.py
    -> assets/doc/*.pdf
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
- Poppler utilities (`pdfinfo`) for explicit PDF publication

PyYAML can be installed with:

```bash
python -m pip install PyYAML
```

## Usage

From the repository root:

```bash
python3 resume/scripts/build_context.py --lang en
python3 resume/scripts/build_context.py --lang pt
```

The default outputs are:

```text
generated/resumes/resume-context-en.json
generated/resumes/resume-context-pt.json
```

Use `--output` to choose another JSON destination:

```bash
python3 resume/scripts/build_context.py --lang en --output /tmp/resume-context.json
```

Before constructing a context, the script parses every YAML file below
`career/` and performs basic structural validation of the five canonical
files. Errors identify the affected file or field and cause a non-zero exit.

Localized canonical fields are resolved for the requested language while the
context is built. Required narrative fields do not fall back from Portuguese
to English (or vice versa); a missing requested translation is an error. The
DOCX renderer receives only the already-resolved strings and performs no
translation.

## Selection rules in this version

- `resume/config/default.yaml` controls presentation selection for the general
  resume; it is not a source of career facts.
- Experiences, education records, projects and skill groups follow the IDs and
  order declared in that configuration.
- Experience and project highlights are limited by the configured maxima while
  preserving canonical order.
- Unknown IDs, duplicate IDs and include/exclude conflicts cause clear errors.
- Certifications are selected only when `resume_eligible` is exactly `true`.
- Project evidence remains under `projects`; it is never promoted to
  professional experience.
- Missing optional values are represented consistently as JSON `null`.
- Canonical IDs are retained for experiences, education, projects and
  certifications.

The resulting JSON follows
[`schema/resume-context.schema.json`](schema/resume-context.schema.json).

## DOCX rendering

After building the contexts, render copies of the existing DOCX templates:

```bash
python3 resume/scripts/render_docx.py --lang en
python3 resume/scripts/render_docx.py --lang pt
```

The default outputs are:

```text
generated/resumes/default/Felipe_Enne_Default_EN.docx
generated/resumes/default/Felipe_Enne_Default_PT.docx
```

The renderer copies paragraph prototypes from the corresponding template and
replaces their factual content with data from `resume-context-<language>.json`.
It preserves the template package's styles, numbering definitions, section
properties, headers and footers. Hyperlinks are recreated as real external
DOCX relationships.

The renderer never writes to `docs/CV/` or `assets/doc/`.

## PDF rendering

LibreOffice Writer with headless conversion support must be installed and
available as either `libreoffice` or `soffice` in `PATH`.

Convert the generated default DOCX files with:

```bash
python3 resume/scripts/render_pdf.py --lang en
python3 resume/scripts/render_pdf.py --lang pt
```

The default outputs are:

```text
generated/resumes/default/Felipe_Enne_Default_EN.pdf
generated/resumes/default/Felipe_Enne_Default_PT.pdf
```

PDF generation does not publish anything. Replacing files under `assets/doc/`
remains a separate, explicit publication operation.

## Review and explicit publication

Review both generated PDFs before publishing them. Confirm their content,
language, layout, links, and pagination. The complete default-resume flow is:

```bash
python3 resume/scripts/build_context.py --lang en
python3 resume/scripts/build_context.py --lang pt

python3 resume/scripts/render_docx.py --lang en
python3 resume/scripts/render_docx.py --lang pt

python3 resume/scripts/render_pdf.py --lang en
python3 resume/scripts/render_pdf.py --lang pt

# revisar PDFs

python3 resume/scripts/publish_default.py
```

`publish_default.py` has fixed source and destination paths and does not accept
path arguments. Before asking for the exact confirmation `YES`, it validates
both sources as distinct, non-empty, two-page A4 PDFs. Both sources are
validated before either public file is replaced. Temporary backups restore
both previous public PDFs if replacement fails.

For a deliberately approved non-interactive publication, use:

```bash
python3 resume/scripts/publish_default.py --yes
```

Do not pass `--yes` from generation scripts. Generation, human review, and
publication remain separate operations.

**Job-specific resumes must never be published through `publish_default.py`.**
The script publishes only the fixed files under `generated/resumes/default/`
to the two general public resume paths under `assets/doc/`.
