# Personal Portfolio

Felipe Enne's static bilingual portfolio, generated from canonical career data
and published through GitHub Pages.

Live site: [felipeenne.github.io/Personal-Portfolio](https://felipeenne.github.io/Personal-Portfolio/)

## Career data and resumes

`career/*.yaml` is the source of truth for professional facts. The portfolio
is a general public presentation of that data, and the public EN/PT resumes are
generated separately from the same source. A job description may affect only a
temporary job-specific resume; it never changes the public resume or portfolio.

For the complete resume workflow, including explicit publication of approved
PDFs, see [`resume/README.md`](resume/README.md).

Generate a job-specific resume with:

```bash
python3 resume/scripts/build_job_resume.py \
  --job resume/jobs/vaga.txt \
  --lang pt
```

Job-specific outputs remain under `generated/resumes/jobs/<slug>/`.

## Local portfolio build

Install the Python dependencies and build both languages:

```bash
python3 -m pip install -r portfolio/requirements.txt
python3 portfolio/scripts/build_context.py --lang en
python3 portfolio/scripts/build_context.py --lang pt
python3 portfolio/scripts/render_site.py
```

Serve the generated site locally:

```bash
python3 -m http.server 8000 --directory _site
```

English is available at `http://localhost:8000/` and Portuguese at
`http://localhost:8000/pt/`. See `portfolio/README.md` for architecture and
data-source details.

## License

Distributed under the MIT License. See `LICENSE` for more information.
