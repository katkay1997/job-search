# sources.py
# ------------------------------------------------------------------
# One function per job site. Each one:
#   - gets your search words, your location, and the keys dictionary
#   - asks that site for jobs
#   - returns a list of jobs that all look the same (see make_job)
#
# The keys only live INSIDE these functions. They are never sent
# to the web page, never printed, and never put in error messages.
# ------------------------------------------------------------------
import re

import requests

import settings

TIMEOUT = 15  # seconds to wait for a site before giving up


def make_job(title, company, location, url, source, posted="", remote=False):
    """Every source turns its jobs into this same simple shape."""
    return {
        "title": (title or "").strip(),
        "company": (company or "").strip(),
        "location": (location or "").strip(),
        "url": (url or "").strip(),
        "source": source,
        "posted": (posted or "")[:10],  # just the date part, like 2026-10-25
        "remote": bool(remote),
    }


# ---------------- Sources that need NO key ----------------

def search_freehire(q, where, keys):
    r = requests.get(
        "https://freehire.me/api/v1/jobs/search",
        params={
            "q": q,
            "countries": "US",
            "seniority": "intern,junior",
            "seniority_include_unspecified": "true",  # many jobs don't say a level
            "limit": min(settings.RESULTS_PER_SOURCE, 100),
        },
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    jobs = []
    for j in r.json().get("data", []):
        remote = j.get("work_mode") == "remote"
        jobs.append(make_job(j.get("title"), j.get("company"), j.get("location"),
                             j.get("url"), "freehire", j.get("posted_at") or "", remote))
    # freehire can't filter by city, so we do it here
    return [j for j in jobs if j["remote"] or matches_place(j["location"], where)]


def search_remotive(q, where, keys):
    r = requests.get(
        "https://remotive.com/api/remote-jobs",
        params={"search": q, "limit": settings.RESULTS_PER_SOURCE},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    jobs = []
    for j in r.json().get("jobs", []):
        allowed = (j.get("candidate_required_location") or "").lower()
        if allowed and not any(word_in(w, allowed) for w in settings.REMOTE_OK_WORDS):
            continue  # skip remote jobs only open to people in other countries
        jobs.append(make_job(j.get("title"), j.get("company_name"),
                             "Remote (" + (j.get("candidate_required_location") or "anywhere") + ")",
                             j.get("url"), "Remotive", j.get("publication_date") or "", True))
    return jobs


# ---------------- Sources that NEED a key ----------------

def search_adzuna(q, where, keys):
    r = requests.get(
        "https://api.adzuna.com/v1/api/jobs/us/search/1",
        params={
            "app_id": keys["ADZUNA_APP_ID"],
            "app_key": keys["ADZUNA_APP_KEY"],
            "what": q,
            "where": where,
            "results_per_page": settings.RESULTS_PER_SOURCE,
            "max_days_old": 30,
        },
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return [
        make_job(j.get("title"), (j.get("company") or {}).get("display_name"),
                 (j.get("location") or {}).get("display_name"),
                 j.get("redirect_url"), "Adzuna", j.get("created") or "")
        for j in r.json().get("results", [])
    ]


def search_jooble(q, where, keys):
    r = requests.post(
        "https://jooble.org/api/" + keys["JOOBLE_KEY"],
        json={"keywords": q, "location": where},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return [
        make_job(j.get("title"), j.get("company"), j.get("location"),
                 j.get("link"), "Jooble", j.get("updated") or "")
        for j in r.json().get("jobs", [])[: settings.RESULTS_PER_SOURCE]
    ]


def search_usajobs(q, where, keys):
    r = requests.get(
        "https://data.usajobs.gov/api/search",
        params={"Keyword": q, "LocationName": where,
                "ResultsPerPage": settings.RESULTS_PER_SOURCE},
        headers={
            "Host": "data.usajobs.gov",
            "User-Agent": keys["USAJOBS_EMAIL"],      # USAJobs wants your email here
            "Authorization-Key": keys["USAJOBS_KEY"],
        },
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    items = (r.json().get("SearchResult") or {}).get("SearchResultItems", [])
    jobs = []
    for item in items:
        d = item.get("MatchedObjectDescriptor") or {}
        jobs.append(make_job(d.get("PositionTitle"), d.get("OrganizationName"),
                             d.get("PositionLocationDisplay"), d.get("PositionURI"),
                             "USAJobs", d.get("PublicationStartDate") or ""))
    return jobs


def search_findwork(q, where, keys):
    r = requests.get(
        "https://findwork.dev/api/jobs/",
        params={"search": q, "location": where},
        headers={"Authorization": "Token " + keys["FINDWORK_TOKEN"]},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return [
        make_job(j.get("role"), j.get("company_name"), j.get("location"),
                 j.get("url"), "Findwork", j.get("date_posted") or "", j.get("remote"))
        for j in r.json().get("results", [])[: settings.RESULTS_PER_SOURCE]
    ]


def search_remoteok(q, where, keys):
    # RemoteOK has no search: it returns its newest ~100 remote jobs,
    # so we filter them here. Their rules: always link to the job on
    # Remote OK and name them as the source (our page does both).
    r = requests.get("https://remoteok.com/api",
                     headers={"User-Agent": "personal-job-finder"}, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    words = specific_words(q)
    jobs = []
    for j in data[1:]:  # item 0 is their legal notice, not a job
        if not isinstance(j, dict):
            continue
        title = j.get("position") or ""
        tags = " ".join(j.get("tags") or [])
        text = (title + " " + tags).lower()
        if words:
            if not any(word_in(w, text) for w in words):
                continue
        elif not any(w in text for w in ("dev", "engineer", "software", "programmer")):
            continue
        allowed = (j.get("location") or "").lower()
        if allowed and not any(word_in(w, allowed) for w in settings.REMOTE_OK_WORDS):
            continue
        jobs.append(make_job(title, j.get("company"),
                             "Remote (" + (j.get("location") or "anywhere") + ")",
                             j.get("url"), "RemoteOK", j.get("date") or "", True))
    return jobs[: settings.RESULTS_PER_SOURCE]


def search_themuse(q, where, keys):
    # The Muse can filter to ENTRY LEVEL jobs, but it doesn't do keyword
    # search. It shows entry-level jobs in the categories set in settings.py,
    # whatever words you type. A key is optional (it just raises the limit).
    params = [("page", 0), ("level", "Entry Level"), ("location", where),
              ("location", "Flexible / Remote")]
    params += [("category", c) for c in settings.MUSE_CATEGORIES]
    if keys.get("THEMUSE_KEY"):
        params.append(("api_key", keys["THEMUSE_KEY"]))
    r = requests.get("https://www.themuse.com/api/public/jobs", params=params, timeout=TIMEOUT)
    r.raise_for_status()
    jobs = []
    for j in r.json().get("results", []):
        places = ", ".join(loc.get("name", "") for loc in (j.get("locations") or []))
        jobs.append(make_job(j.get("name"), (j.get("company") or {}).get("name"), places,
                             (j.get("refs") or {}).get("landing_page"), "The Muse",
                             j.get("publication_date") or "", "remote" in places.lower()))
    return jobs[: settings.RESULTS_PER_SOURCE]


# ---------------- The list of all sources ----------------
# name, function, which keys it needs (from keys.env)
SOURCES = [
    ("freehire", search_freehire, []),
    ("Remotive", search_remotive, []),
    ("RemoteOK", search_remoteok, []),
    ("The Muse", search_themuse, []),  # key optional, see THEMUSE_KEY
    ("Adzuna", search_adzuna, ["ADZUNA_APP_ID", "ADZUNA_APP_KEY"]),
    ("Jooble", search_jooble, ["JOOBLE_KEY"]),
    ("USAJobs", search_usajobs, ["USAJOBS_KEY", "USAJOBS_EMAIL"]),
    ("Findwork", search_findwork, ["FINDWORK_TOKEN"]),
]


# ---------------- Little helpers ----------------


def word_in(word, text):
    """True if `word` appears in `text` as a whole word (so 'ny' doesn't match 'Sunnyvale')."""
    return re.search(r"(?<![a-z])" + re.escape(word.strip()) + r"(?![a-z])", text) is not None


GENERIC_WORDS = {"junior", "jr", "entry", "level", "associate", "developer", "developers",
                 "engineer", "engineering", "software", "new", "grad", "job", "jobs", "and", "the"}


def specific_words(q):
    """The search words that actually narrow things down (e.g. 'c#', 'python')."""
    return [w for w in (q or "").lower().split() if w not in GENERIC_WORDS and len(w) > 1]


def matches_place(location, where):
    location = (location or "").lower()
    city = (where or "").split(",")[0].strip().lower()
    if not city:
        return True
    words = settings.PLACE_NICKNAMES.get(city, [city])
    return any(word_in(w, location) for w in words)
