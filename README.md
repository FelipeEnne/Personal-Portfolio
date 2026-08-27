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

## Main commands

```bash
make test
make portfolio
make resume-job-pt
make resume-job-en
make resume-default-pt
make resume-default-en
make clean
```

Use another job description with:

```bash
make resume-job-pt JOB=resume/jobs/nortal.txt
```

`resume-job-*` generates a job-specific resume under
`generated/resumes/jobs/<slug>/`; `resume-default-*` generates the public
default resume under `generated/resumes/default/` but does not publish it.
`portfolio` builds the static site, `test` runs the test suite, and `clean`
removes only temporary Python artifacts. See [`resume/README.md`](resume/README.md)
for the complete resume workflow and publication rules.

## Local portfolio build

Install the Python dependencies and build both languages:

```bash
python3 -m pip install -r portfolio/requirements.txt
make portfolio
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
