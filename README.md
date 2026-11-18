# Monash Particle Physics website

The group website for particle physics in the School of Physics and Astronomy,
Monash University. It is a static site built from Markdown files by a short
Python script (`build.py`). It can be published with **GitHub Pages** or
**GitLab Pages**; both CI configurations are included.

**Want to add yourself? See [CONTRIBUTING.md](CONTRIBUTING.md).**

## How it is organised

```
config.yml                 site title, contact, people categories, project levels
content/                   intro text for the Home, People and Projects pages
research/
  experimental/            one page per area: comet.md, lhcb.md, detector-development.md
  theoretical/             qcd.md, flavour.md, cosmology.md
people/                    one business card per person (firstname-lastname.md)
  photos/                  card photos
  _TEMPLATE.md             copy this to add yourself
projects/                  one file per PhD / Honours / other project
  _TEMPLATE.md
templates/                 Jinja2 HTML templates
static/                    CSS, JavaScript, fonts, favicon
build.py                   validates content and writes the site to public/
.github/workflows/pages.yml  GitHub: checks pull requests, deploys main to GitHub Pages
.gitlab-ci.yml             GitLab: checks merge requests, deploys main to GitLab Pages
```

The **Research** dropdown, the People page, the project listings and the
cross-links between them (people and projects on each research-area page) are
all generated from these files. Nobody needs to edit HTML to keep the site
up to date.

## Building

```bash
pip install -r requirements.txt
python build.py            # writes public/
python build.py --serve    # builds and serves at http://localhost:8000
python build.py --check    # validation only (what CI runs on merge requests)
```

The site uses relative links throughout, so it works at any URL, including
a GitLab Pages sub-path, and even opened straight from disk.

## Setting up on GitHub

1. Push this folder to a new GitHub repository (you can delete `.gitlab-ci.yml`).
2. Edit `config.yml` and set `repo_url` (e.g. `https://github.com/your-org/monash-pp-site`)
   and `contact_email`.
3. **Settings → Pages → Build and deployment → Source: GitHub Actions.**
   Don't choose "Deploy from a branch": that would run GitHub's built-in Jekyll
   instead of `build.py`.
4. Push to `main`. The workflow builds and deploys, and the URL appears under
   **Settings → Pages** (usually `https://your-org.github.io/monash-pp-site/`).
5. Recommended: **Settings → Branches → add a rule for `main`**. Require a pull
   request before merging, and require the `build` status check to pass, so a
   broken card can never be merged.
6. Optional: add `.github/CODEOWNERS` so changes to `research/` or `config.yml`
   need approval from an academic.
7. Custom domain (e.g. a monash.edu subdomain): set it under **Settings → Pages**
   and ask Monash IT for the DNS CNAME record.

## Setting up on GitLab

1. Push this folder to a new GitLab project (Monash GitLab or gitlab.com). You
   can delete `.github/`.
2. Edit `config.yml` and set `repo_url` and `contact_email`.
3. The first pipeline on `main` publishes the site. Find the URL under
   **Deploy → Pages**.
4. Recommended: under **Settings → Repository → Protected branches**, require
   merge requests for `main`. Under **Settings → Merge requests**, tick
   "Pipelines must succeed", so a broken card can never be merged.
5. Optional: add a `CODEOWNERS` file so changes to `research/` or `config.yml`
   need approval from an academic.

## Before going live

- Delete the `people/example-*.md` files and `people/photos/example-postdoc.svg`.
- Ask supervisors to check the project descriptions in `projects/`. They are
  drafts based on the School's public project listings.
- Add `leads:` to the experimental research-area pages.

## Design notes

- Typeface: Archivo (SIL Open Font License), self-hosted in `static/fonts/`.
  Headings use its wide setting; body text uses the normal width.
- The home-page hero is a generated "event display": particle tracks curling
  in a solenoid field, with a new event on every visit. It respects
  `prefers-reduced-motion`.
- Category colours (academic blue, postdoc rose, PhD amber, Honours cyan,
  former grey) are defined once as CSS variables at the top of `static/site.css`.
