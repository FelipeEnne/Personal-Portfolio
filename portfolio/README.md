# Portfolio generator

This directory contains the context and static rendering layers for Felipe
Enne's general public portfolio. It builds an isolated `_site/` output and does
not overwrite the repository's current public `index.html`.

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
      ↓
portfolio/templates/index.html
      ↓
portfolio/scripts/render_site.py
      ↓
_site/index.html
_site/pt/index.html
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

Generate both contexts and render the static site with:

```bash
python3 portfolio/scripts/build_context.py --lang en
python3 portfolio/scripts/build_context.py --lang pt
python3 portfolio/scripts/render_site.py
```

Install the required Python packages, if necessary, with:

```bash
python3 -m pip install -r portfolio/requirements.txt
```

Each generated context is validated against Draft 2020-12 schema
`portfolio/schema/portfolio-context.schema.json` before it is written.

## Static rendering

`portfolio/templates/index.html` defines the visual HTML structure and reuses
the classes from the existing stylesheet. It is not a source of professional
facts. `portfolio/scripts/render_site.py` validates the generated EN and PT
contexts again, escapes professional text through Jinja2, and creates:

```text
_site/
├── index.html
├── pt/
│   └── index.html
├── assets/
└── favicon.ico
```

English is served at `/` and Portuguese at `/pt/`. The language selector uses
relative page links instead of replacing professional content in the browser.
The links work at a local root and under the GitHub Pages project path
`/Personal-Portfolio/`.

The renderer copies the existing public assets and favicon. It does not copy
career data, generated contexts, resume templates, or development files into
the static site. `_site/` is generated output and is ignored by Git.

## Default presentation policy

`portfolio/config/default.yaml` explicitly controls the general portfolio's
skill, education, and project selection and order. Project `featured` values
are checked as a coherence signal, but they do not replace explicit policy.
Unknown or duplicate configured skills and IDs cause a clear build error.

The full canonical profile contact data stays in the context even when a
`show` flag is false. The static renderer applies those visibility flags.

## Images

Project images are visual presentation configuration, not professional facts.
A non-null image must resolve to an existing repository file. A null image is
valid and produces an informational warning, allowing a project to remain in
the context until artwork is explicitly chosen.

## Public resumes

Public portfolio resume links are restricted to `assets/doc/`. They are
separate from job-specific resumes under `generated/resumes/jobs/`, and job
descriptions never influence the public portfolio.

## Local preview

Serve the generated site through a local HTTP server:

```bash
python3 -m http.server 8000 --directory _site
```

Open `http://localhost:8000/` for English or
`http://localhost:8000/pt/` for Portuguese. The repository's public
`index.html` remains separate from the template and is not overwritten.

## Future publication

A future GitHub Actions workflow may run the same three build commands and
publish `_site/` as a GitHub Pages artifact. Context JSON and `_site/` do not
need to be versioned. Job descriptions must never influence this general
public portfolio build.
