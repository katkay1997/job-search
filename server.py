# server.py
# ------------------------------------------------------------------
# The "butler". It holds your keys, asks the job sites for jobs,
# and shows Gemini (and you) a clean results page at:
#
#     http://127.0.0.1:5000
#
# Run it with:   python server.py
# Stop it with:  Ctrl + C
# ------------------------------------------------------------------
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlencode

import requests
from dotenv import dotenv_values
from flask import Flask, abort, redirect, render_template, request

import settings
import sheet
from sources import SOURCES

app = Flask(__name__)

# The secrets folder sits NEXT TO this project folder, not inside it:
#   JobHunt/
#     job-finder/          <- this code (fine to show Gemini)
#     job-finder-secrets/  <- your keys (never show anyone)
SECRETS_DIR = Path(__file__).resolve().parent.parent / "job-finder-secrets"
KEYS_FILE = SECRETS_DIR / "keys.env"

_cache = {}  # remembers recent searches so we don't waste API calls


def load_keys():
    """Read keys.env fresh every time, so you can add a key without restarting.
    dotenv_values() keeps them in this dictionary only - they are NOT copied
    into the computer's environment variables."""
    if not KEYS_FILE.exists():
        return {}
    keys = {k: v.strip() for k, v in dotenv_values(KEYS_FILE).items() if v and v.strip()}
    robot = keys.get("GOOGLE_ROBOT_FILE", "google-robot.json")
    keys["GOOGLE_ROBOT_FILE"] = str(SECRETS_DIR / robot)
    return keys


def run_source(name, func, needed, q, where, keys):
    """Ask one site for jobs. Returns (jobs, status message).
    Error messages NEVER include the real error text, because that
    text can contain the request URL - and some URLs contain your key."""
    if any(k not in keys for k in needed):
        return [], "not set up yet (no key)"
    cache_key = (name, q.lower(), where.lower())
    hit = _cache.get(cache_key)
    if hit and time.time() - hit[0] < settings.CACHE_HOURS * 3600:
        return hit[1], f"{len(hit[1])} jobs (saved from earlier)"
    try:
        jobs = func(q, where, keys)
    except requests.HTTPError as e:
        code = e.response.status_code if e.response is not None else "?"
        hint = " - check that key" if code in (401, 403) else ""
        return [], f"error {code}{hint}"
    except requests.Timeout:
        return [], "took too long, try again"
    except Exception as e:  # noqa: BLE001
        print(f"[{name}] problem: {type(e).__name__}")  # type only, never the details
        return [], "error"
    _cache[cache_key] = (time.time(), jobs)
    return jobs, f"{len(jobs)} jobs"


def keep(job):
    title = job["title"].lower()
    company = job["company"].lower()
    if not job["title"] or not job["url"].startswith(("http://", "https://")):
        return False
    if any(w in title for w in settings.EXCLUDE_TITLE_WORDS):
        return False
    if any(w.lower() in company for w in settings.EXCLUDE_COMPANY_WORDS):
        return False
    return True


def search_all(q, where, chosen):
    keys = load_keys()
    picked = [s for s in SOURCES if s[0] in chosen]
    with ThreadPoolExecutor(max_workers=len(picked) or 1) as pool:
        futures = {name: pool.submit(run_source, name, func, needed, q, where, keys)
                   for name, func, needed in picked}
    all_jobs, status = [], {}
    for name, fut in futures.items():
        jobs, status[name] = fut.result()
        all_jobs.extend(jobs)

    # remove junk + duplicates (same link, or same title at same company)
    seen, results = set(), []
    for job in filter(keep, all_jobs):
        a = job["url"].split("?")[0].rstrip("/").lower()
        b = (job["title"].lower(), job["company"].lower())
        if a in seen or b in seen:
            continue
        seen.update([a, b])
        results.append(job)
    results.sort(key=lambda j: j["posted"], reverse=True)  # newest first
    return results, status


@app.route("/")
def home():
    all_names = [s[0] for s in SOURCES]
    q = request.args.get("q", "").strip()
    where = request.args.get("where", settings.DEFAULT_WHERE).strip()
    chosen = request.args.getlist("src") or all_names
    jobs, status = ([], {})
    if q:
        jobs, status = search_all(q, where, chosen)
    return render_template(
        "index.html",
        q=q or settings.DEFAULT_SEARCH, searched=bool(q), where=where,
        jobs=jobs, status=status, all_names=all_names, chosen=chosen,
        msg=request.args.get("msg", ""),
        # where "Save" sends you back to (same search, minus the old message)
        back="/?" + urlencode([(k, v) for k, v in request.args.items(multi=True) if k != "msg"]),
    )


@app.route("/save", methods=["POST"])
def save():
    # Only accept clicks from this page itself (blocks other websites
    # from secretly sending stuff to your server).
    origin = request.headers.get("Origin")
    if origin and origin not in (f"http://127.0.0.1:{settings.PORT}",
                                 f"http://localhost:{settings.PORT}"):
        abort(403)

    f = request.form
    job = {k: f.get(k, "").strip()[:300] for k in ("title", "company", "location", "source")}
    job["url"] = f.get("url", "").strip()[:2000]
    back = f.get("back", "/")
    if not back.startswith("/"):
        back = "/"

    if not job["url"].startswith(("http://", "https://")):
        msg = "That job had a weird link, so it wasn't saved."
    else:
        keys = load_keys()
        if "SHEET_ID" not in keys or not Path(keys["GOOGLE_ROBOT_FILE"]).exists():
            msg = "Google Sheet isn't set up yet - see Part 4 of the guide."
        else:
            try:
                result = sheet.save_job(job, keys)
                msg = f'"{job["title"]}" {result} to your Sheet.'
            except Exception as e:  # noqa: BLE001
                print(f"[sheet] problem: {type(e).__name__}")
                msg = "Couldn't save to the Sheet. Did you share the Sheet with the robot email?"

    sep = "&" if "?" in back else "?"
    return redirect(back.split("#")[0] + sep + urlencode({"msg": msg}))


if __name__ == "__main__":
    print(f"\n  Job Finder is running!  Open:  http://{settings.HOST}:{settings.PORT}\n"
          "  (Press Ctrl + C to stop it.)\n")
    # debug=False on purpose: debug mode can show secrets on error pages.
    app.run(host=settings.HOST, port=settings.PORT, debug=False)
