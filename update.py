"""Refresh the Montréal internship table from the public SimplifyJobs feed."""
import json
import re
import unicodedata
import time
from urllib.error import URLError
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlsplit
from urllib.request import urlopen

SOURCE = "https://github.com/SimplifyJobs/Summer2027-Internships"
FEED = SOURCE.replace("github.com", "raw.githubusercontent.com") + "/dev/.github/scripts/listings.json"
YEAR = "2027"


def target_terms(terms):
    return [term for term in terms if term.endswith(" " + YEAR)]


def in_montreal(location):
    normalized = unicodedata.normalize("NFKD", location.casefold())
    return re.search(r"\bmontreal\b", "".join(c for c in normalized if not unicodedata.combining(c)))


def cell(value):
    return " ".join(value.split()).replace("<", "&lt;").replace("|", "&#124;")


def render(records):
    required = {"terms", "active", "locations", "url", "date_posted", "company_name", "title"}
    if not isinstance(records, list) or not records:
        raise ValueError("Expected a populated source feed")
    for job in records:
        if not isinstance(job, dict) or not required.issubset(job):
            raise ValueError("Source feed has missing required fields")
        if not isinstance(job["terms"], list) or not isinstance(job["locations"], list):
            raise ValueError("Source terms and locations must be lists")
        if not all(isinstance(place, str) for place in job["locations"]):
            raise ValueError("Source locations must be strings")
        if not all(isinstance(term, str) for term in job["terms"]):
            raise ValueError("Source terms must be strings")
        if not isinstance(job["active"], bool):
            raise ValueError("Source active status must be boolean")
    if not any(target_terms(job["terms"]) for job in records):
        raise ValueError("Expected a populated feed containing the target year")
    rows = {}
    for job in records:
        if not job["active"] or not job.get("is_visible", True) or not target_terms(job["terms"]):
            continue
        if not any(in_montreal(place) for place in job["locations"]):
            continue
        url = job["url"]
        if urlsplit(url).scheme not in {"http", "https"}:
            continue
        date = datetime.fromtimestamp(job["date_posted"], timezone.utc).date()
        link = quote(url, safe=":/?&=#%+;,@!~$")
        rows[url] = (str(date), cell(job["company_name"]), cell(job["title"]), cell(", ".join(target_terms(job["terms"]))), cell(job.get("category", "Other")), cell(", ".join(job["locations"])), link)
    lines = [
        f"# Montréal internships · {YEAR}", "",
        f"[![Refresh status](https://github.com/Jeffrey-dai17/montreal-internships/actions/workflows/refresh.yml/badge.svg)](https://github.com/Jeffrey-dai17/montreal-internships/actions/workflows/refresh.yml)", "",
        f"Last successful check · {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}", "",
        f"**{len(rows)} open listings** · Sorted by posting date, newest first.", "",
        "Includes tech internships and co-ops that list Montréal as a work location. Multi-city roles qualify. "
        "Start terms and open status come from the source feed. All listed 2027 terms are included. Exact start dates are unspecified in this feed. Check the employer page for dates and availability.", "",
        "| Employer | Role | Start term | Category | Locations | Posted | Application |", "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for date, company, title, terms, category, locations, link in sorted(rows.values(), reverse=True):
        lines.append(f"| {company} | {title} | {terms} | {category} | {locations} | {date} | [Apply]({link}) |")
    if not rows:
        lines.append("\nNo active Montréal roles match this year.")
    lines.extend(["", f"Listings courtesy of [SimplifyJobs and Pitt CSC]({SOURCE}). "
                  "GitHub Actions checks every six hours at 00:17, 06:17, 12:17 and 18:17 UTC. Scheduled runs may be delayed by GitHub. Failed downloads or invalid feeds preserve the last successful list. The status badge links to refresh results. Coverage follows the SimplifyJobs feed. To suggest a listing, submit it to the source repository.", ""])
    return "\n".join(lines)


if __name__ == "__main__":
    for attempt in range(3):
        try:
            with urlopen(FEED, timeout=60) as response:
                content = render(json.load(response))
            break
        except (URLError, TimeoutError):
            if attempt == 2:
                raise
            time.sleep(5 * (attempt + 1))
    destination = Path(__file__).with_name("README.md")
    temporary = destination.with_suffix(".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(destination)
