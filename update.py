"""Refresh the Montréal internship table from the public SimplifyJobs feed."""
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlsplit
from urllib.request import urlopen

SOURCE = "https://github.com/SimplifyJobs/Summer2027-Internships"
FEED = SOURCE.replace("github.com", "raw.githubusercontent.com") + "/dev/.github/scripts/listings.json"
TERM = "Summer 2027"


def in_montreal(location):
    normalized = unicodedata.normalize("NFKD", location.casefold())
    return re.search(r"\bmontreal\b", "".join(c for c in normalized if not unicodedata.combining(c)))


def cell(value):
    return " ".join(value.split()).replace("<", "&lt;").replace("|", "&#124;")


def render(records):
    if not isinstance(records, list) or not records or not any(TERM in r["terms"] for r in records):
        raise ValueError("Expected a populated feed containing the target term")
    rows = {}
    for job in records:
        if not job["active"] or not job.get("is_visible", True) or TERM not in job["terms"]:
            continue
        if not any(in_montreal(place) for place in job["locations"]):
            continue
        url = job["url"]
        if urlsplit(url).scheme not in {"http", "https"}:
            continue
        date = datetime.fromtimestamp(job["date_posted"], timezone.utc).date()
        link = quote(url, safe=":/?&=#%+;,@!~$")
        rows[url] = (str(date), cell(job["company_name"]), cell(job["title"]), link)
    lines = [
        f"# Montréal internships · {TERM}", "",
        f"**{len(rows)} open listings** · Sorted by posting date, newest first.", "",
        "Includes tech internships and co-ops that list Montréal as a work location. Multi-city roles qualify. "
        "Open status comes from the source feed. Check the employer page for availability.", "",
        "| Employer | Role | Posted | Application |", "| --- | --- | --- | --- |",
    ]
    for date, company, title, link in sorted(rows.values(), reverse=True):
        lines.append(f"| {company} | {title} | {date} | [Apply]({link}) |")
    if not rows:
        lines.append("\nNo active Montréal roles match this term.")
    lines.extend(["", f"Listings courtesy of [SimplifyJobs and Pitt CSC]({SOURCE}). "
                  "GitHub Actions checks for changes daily at 12:17 UTC.", ""])
    return "\n".join(lines)


if __name__ == "__main__":
    with urlopen(FEED, timeout=90) as response:
        content = render(json.load(response))
    Path(__file__).with_name("README.md").write_text(content, encoding="utf-8")
