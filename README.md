# Monash Particle Physics website

The group website for particle physics in the School of Physics and Astronomy,
Monash University. It is a static site built from Markdown files by a short
Python script (`build.py`). It can be published with **GitHub Pages** or
**GitLab Pages**; both CI configurations are included.

**Want to add yourself? See [CONTRIBUTING.md](CONTRIBUTING.md).**

## How it is organised

```
config.yml                 site title, contact, people categories, project levels
content/                   intro text for the Home, People, Seminars and Projects pages
research/
  experimental/            one page per area: comet.md, lhcb.md, hyper-k.md, detector-development.md
  theoretical/             qcd.md, flavour.md, cosmology.md
people/                    one business card per person (firstname-lastname.md)
  photos/                  card photos
  _TEMPLATE.md             copy this to add yourself
projects/                  one file per PhD / Honours / other project
  _TEMPLATE.md
templates/                 Jinja2 HTML templates
static/                    CSS, JavaScript, fonts, favicon
build.py                   validates content and writes the site to public/
seminars.py                reads the School talks page and builds the seminar list
tests/                     tests for the seminar reader (with a sample talks page)
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
python build.py --no-fetch # offline build: skip reading the seminar list from monash.edu
python tests/test_seminars.py   # test the seminar reader
```

The site uses relative links throughout, so it works at any URL, including
a GitLab Pages sub-path, and even opened straight from disk.

## Seminars page

The Seminars page lists every talk labelled **PARTICLE PHYSICS SEMINAR** (or the
older **HEP SEMINAR**) on the School's
[Seminars and Colloquia page](https://www.monash.edu/science/schools/physics/Physics-and-Astronomy-news-and-events/talks).

- Browsers can't read monash.edu from another website (cross-origin rules), so
  the list is read by `seminars.py` **when the site is built**. It is saved as
  `data/seminars.json`, plus a calendar feed, `seminars.ics`.
- CI rebuilds the site **every 6 hours** (GitHub: built into the workflow;
  GitLab: add a pipeline schedule). To refresh straight away, use **Run workflow**
  on GitHub's Actions tab, or **Run pipeline** on GitLab.
- When someone opens the page, it loads `data/seminars.json` and sorts the talks
  into **Upcoming** and **Past** using the current time, so a talk moves to
  Past as soon as it finishes, even between rebuilds. Times are shown in Melbourne time.
- **If monash.edu can't be read** (it's down, or its layout changed), the build
  doesn't fail. It keeps the list from the live site (set `site.url` in
  `config.yml`) and the page says the list may be out of date. The build log
  shows a `warning: seminars:` line.
- Which series are included, and which pages are read, are set under
  `seminars:` in `config.yml`. Add a past-year page (e.g. `.../talks/seminars-2025`)
  to `sources` to show more history.
- On GitHub, scheduled workflows pause after 60 days without any commits to the
  repository; GitHub emails the repository owner first, and one click re-enables them.

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

- After the first deploy, set `site.url` in `config.yml` to the published address, so the
  seminar list is kept if monash.edu is ever unreachable during a rebuild.
- Check the first live build log for a `seminars:` line. The reader was written from the
  talks page's visible layout and tested on a sample; if it reports "no talks recognised",
  save the page (File → Save as…, HTML only) and test with `python build.py --seminars-html page.html`.
- Delete `people/example-former-member.md` once a real previous member has a card.
  (While no one has `former: true`, the Previous members section is hidden.)
- Ask members to check their own cards. Research descriptions were drafted from
  public Monash pages, and most students' cards still need a description and photo.
- Ask supervisors to check the project descriptions in `projects/`. They are
  drafts based on the School's public project listings.
- Add `leads:` to the experimental research-area pages.

## Design notes

- The site follows the [Monash brand guidelines](https://www.monash.edu/brandbook/brand-elements/colours).
  Monash blue `#006DAE` is the primary colour, supported by black, white and the
  greys `#5A5A5A`, `#969696` and `#E6E6E6`. The tertiary blues (heritage
  `#ABF5F9`, electric `#285AFF`, blueberry `#121256`) are used sparingly.
- Typeface: Roboto, the Monash web font (SIL Open Font License), self-hosted in `static/fonts/`.
- **Logo:** download the official Monash University logo (SVG) from the Monash
  brand portal, save it as `static/img/monash-logo.svg`, and set
  `logo: monash-logo.svg` in `config.yml`. Until then, the header shows
  "Monash University" as text next to the school and group name.
- Card sizes: categories marked `compact: true` in `config.yml` (PhD and Honours
  by default) and previous members (`former_compact: true`) get half-height
  cards, with the bio cut to two lines and a "More" button.
- Category colours: academic Monash blue, postdoc electric blue, PhD
  blueberry, Honours heritage blue, former grey. They are defined once at the
  top of `static/site.css`.
- The home-page hero is a generated "event display": particle tracks curling
  in a solenoid field, drawn on Monash blue, with a new event on every visit.
  It respects `prefers-reduced-motion`.
