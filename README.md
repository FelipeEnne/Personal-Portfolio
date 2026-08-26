# Personal Portfolio

Felipe Enne's static bilingual portfolio, generated from canonical career data
and published through GitHub Pages.

Live site: [felipeenne.github.io/Personal-Portfolio](https://felipeenne.github.io/Personal-Portfolio/)

## Local build

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
