# Portfolio context generator

This directory contains the format-independent context layer for Felipe Enne's
general public portfolio. It does not render or modify the website.

## Architecture

```text
career/*.yaml
      ↓
portfolio/config/default.yaml
      ↓
portfolio/scripts/build_context.py
      ↓
generated/portfolio/portfolio-context-en.json
generated/portfolio/portfolio-context-pt.json
```

Files in `career/*.yaml` remain the canonical source for professional facts.
`portfolio/config/default.yaml` contains presentation decisions only: display
name, visibility flags, selection and order, project images, and public resume
paths. Generated JSON contexts are build artifacts and must not be edited as
career data.

## Languages

The generator resolves localized canonical fields during the build. English
uses `en` and Portuguese uses `pt`. It does not translate automatically and
does not fall back from Portuguese to English when required narrative content
is missing. Technology names and proper names remain neutral strings.

Generate both contexts with:

```bash
python3 portfolio/scripts/build_context.py --lang en
python3 portfolio/scripts/build_context.py --lang pt
```

Install the required Python packages, if necessary, with:

```bash
python3 -m pip install -r portfolio/requirements.txt
```

Each generated context is validated against Draft 2020-12 schema
`portfolio/schema/portfolio-context.schema.json` before it is written.

## Default presentation policy

`portfolio/config/default.yaml` explicitly controls the general portfolio's
skill, education, and project selection and order. Project `featured` values
are checked as a coherence signal, but they do not replace explicit policy.
Unknown or duplicate configured skills and IDs cause a clear build error.

The full canonical profile contact data stays in the context even when a
`show` flag is false. Those flags are intended for a future renderer.

## Images

Project images are visual presentation configuration, not professional facts.
A non-null image must resolve to an existing repository file. A null image is
valid and produces an informational warning, allowing a project to remain in
the context until artwork is explicitly chosen.

## Public resumes

Public portfolio resume links are restricted to `assets/doc/`. They are
separate from job-specific resumes under `generated/resumes/jobs/`, and job
descriptions never influence the public portfolio.

## Future rendering

A later stage may consume these contexts to generate static HTML or render data
in the browser. That stage is intentionally outside the current generator and
must preserve the separation between localized UI strings and canonical
professional content.
