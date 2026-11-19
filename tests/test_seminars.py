"""Tests for the seminar scraper. Run with:  python tests/test_seminars.py  (or pytest)."""
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import seminars  # noqa: E402

FIXTURE = (ROOT / "tests" / "fixtures" / "talks-sample.html").read_text(encoding="utf-8")
URL = "https://www.monash.edu/science/schools/physics/Physics-and-Astronomy-news-and-events/talks"


def test_matches_only_particle_physics():
    events, n = seminars.parse_talks(FIXTURE, URL, ["PARTICLE PHYSICS SEMINAR"], date(2026, 11, 18))
    assert n == 7, n                                   # every talk row is recognised
    assert [e["speaker"] for e in events] == ["Prof Martin White", "Steve Sclafani", "Eugene Tan"]


def test_fields_current_format():
    events, _ = seminars.parse_talks(FIXTURE, URL, ["PARTICLE PHYSICS SEMINAR"], date(2026, 11, 18))
    e = events[0]
    assert e["affiliation"] == "University of Adelaide"
    assert e["title"] == "What's next for particle physics?"
    assert e["start"] == "2025-03-05T13:00:00+11:00", e["start"]   # year from heading, AEDT
    assert e["end"] == "2025-03-05T14:00:00+11:00", e["end"]
    assert e["location"] == "Room 107, 10 College Walk"


def test_fields_older_format():
    events, _ = seminars.parse_talks(FIXTURE, URL, ["PARTICLE PHYSICS SEMINAR"], date(2026, 11, 18))
    e = events[1]
    assert e["affiliation"] == "University of Wisconsin"
    assert e["title"] == "Seeing the Milky Way Galaxy in high-energy neutrinos"
    assert e["start"] == "2023-09-21T10:00:00+10:00", e["start"]   # AEST in September


def test_links_are_absolute():
    events, _ = seminars.parse_talks(FIXTURE, URL, ["ASTRO SEMINAR"], date(2026, 11, 18))
    siess = [e for e in events if e["speaker"] == "Lionel Siess"][0]
    assert siess["links"] == [{"label": "Video", "url": "https://www.youtube.com/watch?v=example"}]
    assert "Video" not in siess["title"]


def test_times():
    ft = seminars.find_times
    assert ft(" 1 - 2 pm") == ((13, 0), (14, 0))
    assert ft(" 12 - 1 pm") == ((12, 0), (13, 0))
    assert ft(" 11 - 12 pm") == ((11, 0), (12, 0))
    assert ft(" 11am - 12:30pm") == ((11, 0), (12, 30))
    assert ft(" @ 10 am") == ((10, 0), None)
    assert ft(" - 14:00") == ((14, 0), None)
    assert ft(" 2:30–3:30 pm") == ((14, 30), (15, 30))
    assert ft("") is None


def test_dates():
    fd = lambda t: seminars.find_date(seminars.normalise_when(t))[:2]
    assert fd("Wednesday 11 March 2 - 3 pm") == (11, 3)
    assert fd("Thursday 21 September @ 10 am") == (21, 9)
    assert fd("Tuesday14 July 12 - 1 pm") == (14, 7)
    assert fd("Tuesday, 3 October 2017 - 14:30") == (3, 10)
    assert fd("Monday, March 9, 2 pm") == (9, 3)


def test_colloquium_time_and_day():
    events, _ = seminars.parse_talks(FIXTURE, URL, ["SCHOOL COLLOQUIUM"], date(2026, 11, 18))
    assert events[0]["start"] == "2026-03-11T14:00:00+11:00", events[0]["start"]


def test_year_from_weekday_without_heading():
    # "Tuesday 24 March" with no year anywhere: 24 March 2026 is a Tuesday.
    html = """<table><tr><td>Dr A. Person, Somewhere</td><td></td></tr><tr><td>A title</td><td></td></tr>
              <tr><td>Tuesday 24 March 12 - 1 pm</td><td>Room 107</td><td>PARTICLE PHYSICS SEMINAR</td></tr></table>"""
    events, _ = seminars.parse_talks(html, URL, ["PARTICLE PHYSICS SEMINAR"], date(2026, 1, 10))
    assert events[0]["start"].startswith("2026-03-24T12:00"), events[0]["start"]


def test_unrecognised_page_reports_zero_rows():
    events, n = seminars.parse_talks("<html><p>No table here</p></html>", URL, ["PARTICLE"], date(2026, 1, 1))
    assert events == [] and n == 0


def test_ics_output():
    events, _ = seminars.parse_talks(FIXTURE, URL, ["PARTICLE PHYSICS SEMINAR"], date(2026, 11, 18))
    ics = seminars.to_ics(events, "Test")
    assert ics.count("BEGIN:VEVENT") == 3
    assert "DTSTART:20250305T020000Z" in ics           # 1 pm AEDT = 02:00 UTC
    assert all(len(line.encode()) <= 75 for line in ics.split("\r\n"))


if __name__ == "__main__":
    tests = [v for k, v in dict(globals()).items() if k.startswith("test_")]
    for t in tests:
        t()
        print(f"ok  {t.__name__}")
    print(f"{len(tests)} tests passed")
