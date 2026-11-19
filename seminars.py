"""
Collect Particle Physics Seminars from the School of Physics and Astronomy talks page.

The School lists talks as rows of an HTML table. Each talk is a few rows: the speaker,
the title, then a row with the date/time, the room and a series label, e.g.

    | Prof Martin White, University of Adelaide            |                       |                          |
    | What's next for particle physics?                    |                       |                          |
    | Wednesday 5 March 1 - 2 pm                           | Room 107, 10 College… | PARTICLE PHYSICS SEMINAR |

Dates are written without a year, so the year is taken from the nearest heading
("Upcoming 2026", "Seminars 2025", ...) and checked against the weekday.

This runs at build time (the browser cannot read monash.edu directly because of
cross-origin rules). The site is rebuilt on a schedule, and the Seminars page loads
the resulting data/seminars.json each time it is opened.
"""
from __future__ import annotations

import json
import re
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

MELBOURNE = ZoneInfo("Australia/Melbourne")
USER_AGENT = "MonashParticlePhysicsSite/1.0 (seminar list; +https://www.monash.edu/science/schools/physics)"

MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august",
     "september", "october", "november", "december"], 1)}
MONTHS.update({k[:3]: v for k, v in list(MONTHS.items())})
MONTHS["sept"] = 9
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

LABEL_RE = re.compile(r"\b(seminar|colloquium|colloquia|lecture|talk|workshop|moca)\b", re.I)
DAY_MONTH_RE = re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)?\s*(?:of\s+)?([A-Za-z]{3,9})\b\.?")
MONTH_DAY_RE = re.compile(r"\b([A-Za-z]{3,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?\b")
YEAR_RE = re.compile(r"\b(20\d\d)\b")
LINK_WORDS = re.compile(r"^\(?\s*(video|abstract|slides|recording|download flyer|flyer|poster|link)\s*\)?$", re.I)


# --------------------------------------------------------------------------- #
#  Parsing helpers
# --------------------------------------------------------------------------- #
def clean(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").replace("\xa0", " ")).strip()


def find_date(text: str):
    """Return (day, month, span) for the first 'day month' or 'month day' in text."""
    for m in DAY_MONTH_RE.finditer(text):                # "5 March", "21st of September"
        if m.group(2).lower() in MONTHS and 1 <= int(m.group(1)) <= 31:
            return int(m.group(1)), MONTHS[m.group(2).lower()], m.span()
    for m in MONTH_DAY_RE.finditer(text):                # "March 5"
        if m.group(1).lower() in MONTHS and 1 <= int(m.group(2)) <= 31:
            return int(m.group(2)), MONTHS[m.group(1).lower()], m.span()
    return None


def normalise_when(text: str) -> str:
    """'Tuesday14 July' -> 'Tuesday 14 July' (a weekday glued to the day number)."""
    return re.sub(r"([A-Za-z])(\d)", r"\1 \2", text)


def find_weekday(text: str):
    low = text.lower()
    for i, name in enumerate(WEEKDAYS):
        if re.search(r"\b" + name[:3], low):
            return i
    return None


def _hm(token: str):
    token = token.replace(".", ":")
    if ":" in token:
        h, m = token.split(":", 1)
        return int(h), int(m[:2])
    return int(token), 0


def _to24(h: int, mer: str | None) -> int:
    if mer == "pm" and h != 12:
        return h + 12
    if mer == "am" and h == 12:
        return 0
    return h


def find_times(text: str):
    """Return ((h, m), (h, m) | None) start/end in 24 h, or None if no time is given."""
    t = text.lower().replace("noon", "12 pm").replace("–", "-").replace("—", "-")
    rng = re.search(r"(\d{1,2}(?:[:.]\d{2})?)\s*(am|pm)?\s*(?:-|to)\s*(\d{1,2}(?:[:.]\d{2})?)\s*(am|pm)?", t)
    if rng:
        (sh, sm), (eh, em) = _hm(rng.group(1)), _hm(rng.group(3))
        smer, emer = rng.group(2), rng.group(4)
        if emer or smer or ":" in rng.group(1) or ":" in rng.group(3):
            if not emer and not smer and (sh > 12 or eh > 12 or ":" in rng.group(1)):
                return (sh, sm), (eh, em)                      # 24-hour clock, e.g. 14:00 - 15:00
            e24 = _to24(eh, emer or smer)
            if smer:
                s24 = _to24(sh, smer)
            else:                                              # "1 - 2 pm", "12 - 1 pm", "11 - 12 pm"
                cands = [12 if sh == 12 else sh, (sh + 12) if sh != 12 else 0]
                cands = [c for c in cands if 0 <= e24 * 60 + em - (c * 60 + sm) <= 6 * 60] or cands
                s24 = min(cands, key=lambda c: e24 * 60 + em - (c * 60 + sm))
            return (s24, sm), (e24, em)
    one = re.search(r"(\d{1,2}(?:[:.]\d{2})?)\s*(am|pm)\b", t)
    if one:
        h, m = _hm(one.group(1))
        return (_to24(h, one.group(2)), m), None
    hm24 = re.search(r"\b([01]?\d|2[0-3])[:.]([0-5]\d)\b", t)
    if hm24:
        return (int(hm24.group(1)), int(hm24.group(2))), None
    return None


def resolve_year(day: int, month: int, weekday, explicit, hint, today: date):
    if explicit:
        return explicit
    base = hint or today.year
    candidates = [base, base + 1, base - 1] if hint else [today.year, today.year + 1, today.year - 1]
    if weekday is not None:
        for y in candidates:
            try:
                if date(y, month, day).weekday() == weekday:
                    return y
            except ValueError:
                continue
    return base


def year_hint_for(node) -> int | None:
    """Nearest preceding heading or caption that names a year (e.g. 'Upcoming 2026')."""
    cap = node.find("caption")
    if cap and YEAR_RE.search(cap.get_text()):
        return int(YEAR_RE.search(cap.get_text()).group(1))
    for prev in node.find_all_previous(["h1", "h2", "h3", "h4", "h5", "p", "strong", "title"], limit=40):
        m = YEAR_RE.search(prev.get_text(" "))
        if m and len(clean(prev.get_text(" "))) < 120:
            return int(m.group(1))
    return None


def split_speaker(text: str):
    """'Prof Jane Citizen, University of X' -> ('Prof Jane Citizen', 'University of X')."""
    text = clean(text)
    for sep in (" - ", " – ", ", "):
        if sep in text:
            a, b = text.split(sep, 1)
            return a.strip(), b.strip()
    return text, ""


def describe(rows, base_url: str):
    """Speaker, affiliation, title and links from the rows that precede a date row."""
    links, seen = [], set()
    for r in rows:
        for a in r.find_all("a", href=True):
            href = urljoin(base_url, a["href"].strip())
            if not href.startswith(("http://", "https://")) or href in seen:
                continue
            seen.add(href)
            links.append({"label": clean(a.get_text(" ")) or "Link", "url": href})
    texts = []
    for r in rows:
        cell = max(r.find_all(["td", "th"]), key=lambda c: len(clean(c.get_text(" "))))
        parts = [clean(s) for s in cell.stripped_strings]
        parts = [p for p in parts if p and not LINK_WORDS.match(p)]
        texts.append(parts)
    if len(texts) >= 2:
        speaker_text, title = " ".join(texts[-2]), " ".join(texts[-1])
    elif texts and len(texts[0]) >= 2:          # older format: speaker and title in one cell
        speaker_text, title = texts[0][0], " ".join(texts[0][1:])
    elif texts and texts[0]:
        speaker_text, title = texts[0][0], ""
    else:
        speaker_text, title = "", ""
    speaker, affiliation = split_speaker(speaker_text)
    return speaker, affiliation, clean(title), links


def parse_talks(html: str, base_url: str, match: list[str], today: date | None = None):
    """Return (events, n_talk_rows). n_talk_rows counts every talk of any series found,
    which tells us whether the page structure was understood at all."""
    today = today or datetime.now(MELBOURNE).date()
    soup = BeautifulSoup(html, "html.parser")
    patterns = [m.lower() for m in match]
    events, n_rows = [], 0
    for table in soup.find_all("table"):
        hint = year_hint_for(table)
        buffer = []
        for tr in table.find_all("tr"):
            cells = tr.find_all(["td", "th"], recursive=False) or tr.find_all(["td", "th"])
            texts = [clean(c.get_text(" ")) for c in cells]
            nonempty = [t for t in texts if t]
            is_talk = (len(nonempty) >= 2 and LABEL_RE.search(nonempty[-1])
                       and len(nonempty[-1]) <= 60 and find_date(normalise_when(nonempty[0])))
            if not is_talk:
                if nonempty:
                    buffer = (buffer + [tr])[-2:]
                continue
            n_rows += 1
            series = nonempty[-1]
            if any(p in series.lower() for p in patterns):
                when_text = nonempty[0]
                when = normalise_when(when_text)
                location = nonempty[1] if len(nonempty) >= 3 else ""
                day, month, span = find_date(when)
                weekday = find_weekday(when)
                ym = YEAR_RE.search(when)
                year = resolve_year(day, month, weekday, int(ym.group(1)) if ym else None, hint, today)
                rest = when[:span[0]] + " " + when[span[1]:]
                rest = YEAR_RE.sub(" ", rest)
                times = find_times(rest)
                speaker, affiliation, title, links = describe(buffer, base_url)
                try:
                    if times:
                        (sh, sm), end = times
                        start = datetime(year, month, day, sh, sm, tzinfo=MELBOURNE)
                        end_dt = (datetime(year, month, day, end[0], end[1], tzinfo=MELBOURNE)
                                  if end else start + timedelta(hours=1))
                        if end_dt <= start:
                            end_dt = start + timedelta(hours=1)
                        all_day = False
                    else:
                        start = datetime(year, month, day, tzinfo=MELBOURNE)
                        end_dt, all_day = start + timedelta(days=1), True
                except ValueError:
                    buffer = []
                    continue
                events.append({
                    "id": f"{start:%Y%m%d}-{re.sub(r'[^a-z0-9]+', '-', speaker.lower()).strip('-')[:40]}",
                    "title": title,
                    "speaker": speaker,
                    "affiliation": affiliation,
                    "start": start.isoformat(),
                    "end": end_dt.isoformat(),
                    "all_day": all_day,
                    "when_text": when_text,
                    "location": location,
                    "series": series,
                    "links": links,
                    "source": base_url,
                })
            buffer = []
    return events, n_rows


# --------------------------------------------------------------------------- #
#  Fetching, fallback and output
# --------------------------------------------------------------------------- #
def fetch(url: str, timeout: int = 25) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, errors="replace")


def ics_escape(s: str) -> str:
    return (s or "").replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def ics_fold(line: str) -> str:
    out, b = [], line.encode("utf-8")
    while len(b) > 74:
        cut = 74
        while (b[cut] & 0xC0) == 0x80:        # don't split a UTF-8 character
            cut -= 1
        out.append(b[:cut].decode("utf-8"))
        b = b" " + b[cut:]
    out.append(b.decode("utf-8"))
    return "\r\n".join(out)


def to_ics(events: list[dict], name: str) -> str:
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Monash Particle Physics//Seminars//EN",
             "CALSCALE:GREGORIAN", "METHOD:PUBLISH", f"X-WR-CALNAME:{ics_escape(name)}",
             "X-WR-TIMEZONE:Australia/Melbourne"]
    for e in events:
        start, end = datetime.fromisoformat(e["start"]), datetime.fromisoformat(e["end"])
        summary = e["title"] or "Particle Physics Seminar"
        if e["speaker"]:
            summary = f"{summary} ({e['speaker']})"
        desc = "\n".join(x for x in [e["speaker"] + (f", {e['affiliation']}" if e["affiliation"] else ""),
                                     e["series"]] + [f"{l['label']}: {l['url']}" for l in e["links"]] if x)
        lines += ["BEGIN:VEVENT", f"UID:{e['id']}@monash-particle-physics", f"DTSTAMP:{now}"]
        if e["all_day"]:
            lines += [f"DTSTART;VALUE=DATE:{start:%Y%m%d}", f"DTEND;VALUE=DATE:{end:%Y%m%d}"]
        else:
            lines += [f"DTSTART:{start.astimezone(timezone.utc):%Y%m%dT%H%M%SZ}",
                      f"DTEND:{end.astimezone(timezone.utc):%Y%m%dT%H%M%SZ}"]
        lines += [f"SUMMARY:{ics_escape(summary)}", f"LOCATION:{ics_escape(e['location'])}",
                  f"DESCRIPTION:{ics_escape(desc)}", f"URL:{e['source']}", "END:VEVENT"]
    lines.append("END:VCALENDAR")
    return "\r\n".join(ics_fold(l) for l in lines) + "\r\n"


def collect(cfg: dict, out_dir: Path, *, fetch_live: bool = True, html_file: Path | None = None,
            log=print) -> dict:
    """Build data/seminars.json and seminars.ics in out_dir. Never raises."""
    scfg = cfg.get("seminars") or {}
    sources = scfg.get("sources") or []
    match = scfg.get("match") or ["PARTICLE PHYSICS SEMINAR"]
    now = datetime.now(MELBOURNE)
    events, ok, problems = [], False, []

    pages = []
    if html_file:
        pages.append((sources[0] if sources else html_file.as_uri(), html_file.read_text(encoding="utf-8")))
    elif fetch_live:
        for url in sources:
            try:
                pages.append((url, fetch(url)))
            except Exception as exc:                          # network, HTTP or decoding error
                problems.append(f"could not fetch {url}: {exc}")
    for url, html in pages:
        found, n_rows = parse_talks(html, url, match, now.date())
        if n_rows == 0:
            problems.append(f"no talks recognised on {url}; the page layout may have changed")
            continue
        ok = True
        events.extend(found)

    data = None
    if ok:
        uniq = {}
        for e in events:
            uniq[(e["start"], e["title"].lower())] = e
        events = sorted(uniq.values(), key=lambda e: e["start"])
        data = {"status": "ok", "generated": now.isoformat(timespec="seconds"),
                "origin": "file" if html_file else "live",
                "sources": sources, "match": match, "events": events}
    else:
        # Fall back to the list currently published on the live site, if there is one.
        site_url = (cfg.get("site") or {}).get("url")
        if site_url and fetch_live:
            try:
                prev = json.loads(fetch(site_url.rstrip("/") + "/data/seminars.json"))
                if prev.get("events") is not None:
                    prev["status"] = "stale"
                    data = prev
                    problems.append("kept the seminar list from the live site")
            except Exception as exc:
                problems.append(f"no previous seminar list available: {exc}")
        if data is None:
            data = {"status": "unavailable", "generated": now.isoformat(timespec="seconds"),
                    "sources": sources, "match": match, "events": []}
    for p in problems:
        log(f"warning: seminars: {p}")
    log(f"seminars: {len(data['events'])} talk(s), status {data['status']}")

    (out_dir / "data").mkdir(parents=True, exist_ok=True)
    (out_dir / "data" / "seminars.json").write_text(json.dumps(data, indent=1, ensure_ascii=False),
                                                     encoding="utf-8")
    (out_dir / "seminars.ics").write_text(to_ics(data["events"], scfg.get("calendar_name",
                                          "Monash Particle Physics Seminars")), encoding="utf-8")
    return data
