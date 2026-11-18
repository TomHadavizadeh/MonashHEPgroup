#!/usr/bin/env python3
"""
Build the Monash Particle Physics website.

    python build.py            # build the site into ./public
    python build.py --check    # validate content only (used on merge/pull requests)
    python build.py --serve    # build, then serve on http://localhost:8000

Content lives in plain Markdown files with a YAML header ("front matter"):

    people/*.md                  one business card per person
    projects/*.md                one file per research project
    research/<branch>/*.md       one page per research area
    content/*.md                 intro text for the home, people and projects pages

Files whose names start with "_" (e.g. people/_TEMPLATE.md) are ignored.
"""
from __future__ import annotations

import argparse
import http.server
import re
import shutil
import socketserver
import sys
from dataclasses import dataclass, field
from datetime import date
from functools import partial
from pathlib import Path

import markdown
import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from markupsafe import Markup

ROOT = Path(__file__).resolve().parent
FRONT_MATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.S)
SLUG_OK = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PHOTO_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"}
BIO_SOFT_LIMIT = 600  # characters; longer bios get a warning, not an error

PERSON_FIELDS = {
    "name", "category", "role", "photo", "areas", "email", "website",
    "orcid", "inspire", "github", "former", "years", "now", "order", "draft",
    "pronouns",
}
PROJECT_FIELDS = {
    "title", "level", "areas", "supervisors", "order", "draft", "status",
    "prerequisites",
}
AREA_FIELDS = {"title", "summary", "leads", "order", "links", "draft", "short_title"}


# --------------------------------------------------------------------------- #
#  Small helpers
# --------------------------------------------------------------------------- #
class Problems:
    """Collects errors (which fail the build) and warnings (which do not)."""

    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, path: Path, msg: str) -> None:
        self.errors.append(f"{path.relative_to(ROOT)}: {msg}")

    def warn(self, path: Path, msg: str) -> None:
        self.warnings.append(f"{path.relative_to(ROOT)}: {msg}")


def md_to_html(text: str) -> Markup:
    html = markdown.markdown(
        text.strip(), extensions=["extra", "sane_lists", "smarty"], output_format="html5"
    )
    return Markup(html)


def read_md(path: Path, problems: Problems) -> tuple[dict, str] | None:
    raw = path.read_text(encoding="utf-8")
    m = FRONT_MATTER.match(raw)
    if not m:
        problems.error(path, "missing YAML header. The file must start with a line '---', "
                             "then the fields, then another '---'.")
        return None
    try:
        meta = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as exc:
        problems.error(path, f"the YAML header could not be read: {exc}")
        return None
    if not isinstance(meta, dict):
        problems.error(path, "the YAML header must be a list of 'field: value' lines.")
        return None
    return meta, m.group(2)


def as_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def initials(name: str) -> str:
    parts = [p for p in re.split(r"[\s\-]+", name) if p and p[0].isalpha()]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][0].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def surname_key(name: str) -> tuple[str, str]:
    parts = name.split()
    return (parts[-1].lower() if parts else "", name.lower())


def md_files(folder: Path) -> list[Path]:
    if not folder.exists():
        return []
    return sorted(p for p in folder.glob("*.md") if not p.name.startswith("_"))


def check_unknown(meta: dict, allowed: set[str], path: Path, problems: Problems) -> None:
    for key in meta:
        if key not in allowed:
            problems.warn(path, f"unknown field '{key}' will be ignored "
                                f"(allowed: {', '.join(sorted(allowed))}).")


# --------------------------------------------------------------------------- #
#  Content models
# --------------------------------------------------------------------------- #
@dataclass
class Area:
    slug: str
    branch: str
    title: str
    short_title: str
    summary: str
    body: Markup
    leads: list[str]
    links: list[dict]
    order: int
    people: list = field(default_factory=list)
    projects: list = field(default_factory=list)
    lead_people: list = field(default_factory=list)

    @property
    def url(self) -> str:
        return f"research/{self.slug}.html"


@dataclass
class Person:
    slug: str
    name: str
    category: str
    category_label: str
    role: str
    photo: str | None
    areas: list[str]
    email: str | None
    website: str | None
    orcid: str | None
    inspire: str | None
    github: str | None
    pronouns: str | None
    former: bool
    years: str | None
    now: str | None
    order: int
    bio: Markup
    initials: str
    area_objs: list = field(default_factory=list)


@dataclass
class Project:
    slug: str
    title: str
    levels: list[str]
    areas: list[str]
    supervisors: list
    prerequisites: str | None
    order: int
    body: Markup
    area_objs: list = field(default_factory=list)


# --------------------------------------------------------------------------- #
#  Loading
# --------------------------------------------------------------------------- #
def load_areas(cfg: dict, problems: Problems) -> dict[str, Area]:
    areas: dict[str, Area] = {}
    branch_keys = [b["key"] for b in cfg["branches"]]
    for branch in branch_keys:
        for path in md_files(ROOT / "research" / branch):
            parsed = read_md(path, problems)
            if not parsed:
                continue
            meta, body = parsed
            if meta.get("draft"):
                continue
            check_unknown(meta, AREA_FIELDS, path, problems)
            slug = path.stem
            if not SLUG_OK.match(slug):
                problems.error(path, "file name must be lower-case words joined by hyphens, "
                                     "e.g. 'detector-development.md'.")
                continue
            if slug in areas:
                problems.error(path, f"another research area is already called '{slug}'.")
                continue
            if not meta.get("title"):
                problems.error(path, "missing 'title'.")
                continue
            areas[slug] = Area(
                slug=slug,
                branch=branch,
                title=str(meta["title"]),
                short_title=str(meta.get("short_title") or meta["title"]),
                summary=str(meta.get("summary", "")).strip(),
                body=md_to_html(body),
                leads=[str(x) for x in as_list(meta.get("leads"))],
                links=as_list(meta.get("links")),
                order=int(meta.get("order", 100)),
            )
    for path in (ROOT / "research").glob("*/"):
        if path.is_dir() and path.name not in branch_keys:
            problems.warn(path, f"folder is not a branch listed in config.yml "
                                f"({', '.join(branch_keys)}) and will be ignored.")
    return areas


def load_people(cfg: dict, areas: dict[str, Area], problems: Problems) -> list[Person]:
    cats = {c["key"]: c for c in cfg["categories"]}
    people: list[Person] = []
    photo_dir = ROOT / "people" / "photos"
    for path in md_files(ROOT / "people"):
        parsed = read_md(path, problems)
        if not parsed:
            continue
        meta, body = parsed
        if meta.get("draft"):
            continue
        check_unknown(meta, PERSON_FIELDS, path, problems)
        slug = path.stem
        ok = True
        if not SLUG_OK.match(slug):
            problems.error(path, "file name must be your name in lower case with hyphens, "
                                 "e.g. 'jane-citizen.md'.")
            ok = False
        name = str(meta.get("name") or "").strip()
        if not name:
            problems.error(path, "missing 'name'.")
            ok = False
        cat = str(meta.get("category") or "").strip().lower()
        if cat not in cats:
            problems.error(path, f"'category' must be one of: {', '.join(cats)} "
                                 f"(got '{meta.get('category')}').")
            ok = False
        area_slugs = [str(a).strip().lower() for a in as_list(meta.get("areas"))]
        for a in area_slugs:
            if a not in areas:
                problems.error(path, f"unknown research area '{a}'. "
                                     f"Choose from: {', '.join(sorted(areas))}.")
                ok = False
        photo = meta.get("photo")
        if photo:
            photo = str(photo).strip()
            p = photo_dir / photo
            if "/" in photo or "\\" in photo:
                problems.error(path, "'photo' should be just the file name, e.g. 'jane-citizen.jpg', "
                                     "with the image saved in people/photos/.")
                ok = False
            elif p.suffix.lower() not in PHOTO_EXT:
                problems.error(path, f"photo must be one of {', '.join(sorted(PHOTO_EXT))}.")
                ok = False
            elif not p.exists():
                problems.error(path, f"photo 'people/photos/{photo}' was not found. "
                                     "Add the image to your merge/pull request, or remove the 'photo' line.")
                ok = False
            elif p.stat().st_size > 1_000_000:
                problems.warn(path, f"photo is {p.stat().st_size // 1024} KB; please keep it "
                                    "under 1 MB (about 600×600 px is plenty).")
        bio_text = body.strip()
        if not bio_text:
            problems.warn(path, "no research description below the header.")
        elif len(bio_text) > BIO_SOFT_LIMIT:
            problems.warn(path, f"research description is {len(bio_text)} characters; "
                                f"cards read best under {BIO_SOFT_LIMIT}.")
        former = bool(meta.get("former", False))
        if former and not meta.get("years"):
            problems.warn(path, "former members should have 'years', e.g. years: 2019–2023.")
        if not ok:
            continue
        people.append(Person(
            slug=slug,
            name=name,
            category=cat,
            category_label=cats[cat]["singular"],
            role=str(meta.get("role") or "").strip(),
            photo=photo or None,
            areas=area_slugs,
            email=meta.get("email"),
            website=meta.get("website"),
            orcid=meta.get("orcid"),
            inspire=meta.get("inspire"),
            github=meta.get("github"),
            pronouns=meta.get("pronouns"),
            former=former,
            years=str(meta["years"]) if meta.get("years") else None,
            now=meta.get("now"),
            order=int(meta.get("order", 100)),
            bio=md_to_html(bio_text),
            initials=initials(name),
        ))
    return people


def load_projects(cfg: dict, areas: dict[str, Area], people_by_slug: dict,
                  problems: Problems) -> list[Project]:
    levels = {lvl["key"] for lvl in cfg["project_levels"]}
    projects: list[Project] = []
    for path in md_files(ROOT / "projects"):
        parsed = read_md(path, problems)
        if not parsed:
            continue
        meta, body = parsed
        if meta.get("draft") or str(meta.get("status", "open")).lower() in {"filled", "closed"}:
            continue
        check_unknown(meta, PROJECT_FIELDS, path, problems)
        ok = True
        if not meta.get("title"):
            problems.error(path, "missing 'title'.")
            ok = False
        lv = [str(x).strip().lower() for x in as_list(meta.get("level"))]
        if not lv:
            problems.error(path, f"missing 'level' (one or more of: {', '.join(levels)}).")
            ok = False
        for x in lv:
            if x not in levels:
                problems.error(path, f"unknown level '{x}' (use: {', '.join(levels)}).")
                ok = False
        area_slugs = [str(a).strip().lower() for a in as_list(meta.get("areas"))]
        for a in area_slugs:
            if a not in areas:
                problems.error(path, f"unknown research area '{a}'.")
                ok = False
        sups = []
        for s in as_list(meta.get("supervisors")):
            s = str(s).strip()
            person = people_by_slug.get(s)
            sups.append({"name": person.name, "person": person} if person else
                        {"name": s, "person": None})
        if not ok:
            continue
        projects.append(Project(
            slug=path.stem,
            title=str(meta["title"]),
            levels=lv,
            areas=area_slugs,
            supervisors=sups,
            prerequisites=meta.get("prerequisites"),
            order=int(meta.get("order", 100)),
            body=md_to_html(body),
        ))
    return projects


def load_page(name: str, problems: Problems) -> tuple[dict, Markup]:
    path = ROOT / "content" / f"{name}.md"
    if not path.exists():
        return {}, Markup("")
    parsed = read_md(path, problems)
    if not parsed:
        return {}, Markup("")
    meta, body = parsed
    return meta, md_to_html(body)


def resolve_lead(token: str, people_by_slug: dict) -> dict:
    person = people_by_slug.get(token)
    return {"name": person.name, "person": person} if person else {"name": token, "person": None}


# --------------------------------------------------------------------------- #
#  Build
# --------------------------------------------------------------------------- #
def build(out: Path, check_only: bool = False) -> int:
    cfg = yaml.safe_load((ROOT / "config.yml").read_text(encoding="utf-8"))
    problems = Problems()

    areas = load_areas(cfg, problems)
    people = load_people(cfg, areas, problems)
    people_by_slug = {p.slug: p for p in people}
    projects = load_projects(cfg, areas, people_by_slug, problems)

    # Cross-link everything.
    for p in people:
        p.area_objs = [areas[a] for a in p.areas]
    for pr in projects:
        pr.area_objs = [areas[a] for a in pr.areas]
    cat_rank = {c["key"]: i for i, c in enumerate(cfg["categories"])}
    for a in areas.values():
        a.people = sorted([p for p in people if a.slug in p.areas and not p.former],
                          key=lambda p: (cat_rank[p.category], p.order, surname_key(p.name)))
        a.projects = [pr for pr in projects if a.slug in pr.areas]
        a.lead_people = [resolve_lead(t, people_by_slug) for t in a.leads]

    for w in problems.warnings:
        print(f"warning: {w}")
    if problems.errors:
        print(f"\n{len(problems.errors)} problem(s) must be fixed:\n", file=sys.stderr)
        for e in problems.errors:
            print(f"  ✗ {e}", file=sys.stderr)
        return 1

    print(f"ok: {len(people)} people, {len(projects)} projects, {len(areas)} research areas")
    if check_only:
        return 0

    # Group data for templates.
    branches = []
    for b in cfg["branches"]:
        items = sorted([a for a in areas.values() if a.branch == b["key"]],
                       key=lambda a: (a.order, a.title))
        branches.append({**b, "areas": items})

    current = [p for p in people if not p.former]
    groups = []
    for c in cfg["categories"]:
        members = sorted([p for p in current if p.category == c["key"]],
                         key=lambda p: (p.order, surname_key(p.name)))
        groups.append({**c, "people": members})
    former = sorted([p for p in people if p.former],
                    key=lambda p: (cat_rank[p.category], surname_key(p.name)))

    level_groups = []
    for lvl in cfg["project_levels"]:
        items = sorted([pr for pr in projects if lvl["key"] in pr.levels],
                       key=lambda pr: (pr.order, pr.title))
        level_groups.append({**lvl, "projects": items})
    level_labels = {lvl["key"]: lvl["label"].replace(" projects", "")
                    for lvl in cfg["project_levels"]}

    env = Environment(
        loader=FileSystemLoader(ROOT / "templates"),
        autoescape=select_autoescape(["html"]),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    site = dict(cfg["site"])
    repo = str(site.get("repo_url", "")).rstrip("/")
    on_github = "github.com" in repo
    branch = site.get("default_branch", "main")
    site["repo_url"] = repo
    site["contributing_url"] = f"{repo}/blob/{branch}/CONTRIBUTING.md" if on_github \
        else f"{repo}/-/blob/{branch}/CONTRIBUTING.md"
    site["request_name"] = "pull request" if on_github else "merge request"
    common = dict(
        site=site, branches=branches, year=date.today().year,
        level_labels=level_labels, former_label=cfg["former_label"],
    )

    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    def render(template: str, dest: str, **ctx) -> None:
        depth = dest.count("/")
        html = env.get_template(template).render(root="../" * depth, page_path=dest,
                                                 **common, **ctx)
        target = out / dest
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html, encoding="utf-8")

    home_meta, home_body = load_page("index", problems)
    render("index.html", "index.html", page=home_meta, body=home_body, nav="home",
           level_groups=level_groups, people_count=len(current))

    people_meta, people_body = load_page("people", problems)
    render("people.html", "people.html", page=people_meta, body=people_body, nav="people",
           groups=groups, former=former, areas=areas)

    projects_meta, projects_body = load_page("projects", problems)
    render("projects.html", "projects.html", page=projects_meta, body=projects_body,
           nav="projects", level_groups=level_groups)

    for a in areas.values():
        branch_label = next(b["label"] for b in cfg["branches"] if b["key"] == a.branch)
        render("area.html", a.url, area=a, branch_label=branch_label, nav="research")

    shutil.copytree(ROOT / "static", out / "static")
    photos = ROOT / "people" / "photos"
    if photos.exists():
        shutil.copytree(photos, out / "photos",
                        ignore=shutil.ignore_patterns(".*", "README*"))
    (out / ".nojekyll").write_text("")
    print(f"built site into {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out}")
    return 0


def serve(out: Path, port: int) -> None:
    handler = partial(http.server.SimpleHTTPRequestHandler, directory=str(out))
    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"serving on http://localhost:{port}  (Ctrl+C to stop)")
        httpd.serve_forever()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="validate content without building")
    ap.add_argument("--out", default="public", help="output folder (default: public)")
    ap.add_argument("--serve", action="store_true", help="serve the built site locally")
    ap.add_argument("--port", type=int, default=8000)
    args = ap.parse_args()
    out = (ROOT / args.out).resolve()
    code = build(out, check_only=args.check)
    if code == 0 and args.serve and not args.check:
        serve(out, args.port)
    sys.exit(code)


if __name__ == "__main__":
    main()
