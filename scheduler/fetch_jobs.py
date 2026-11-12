import os, requests, pandas as pd

SEARCHES = ["junior software engineer", "entry level C# developer",
            "junior application developer", "customer success"]
LOCATION = "New York, NY"
rows = []

def has(*keys):
    return all(os.environ.get(k) for k in keys)

for q in SEARCHES:
    # Adzuna (skipped until keys are added)
    if has("ADZUNA_APP_ID", "ADZUNA_APP_KEY"):
        try:
            r = requests.get("https://api.adzuna.com/v1/api/jobs/us/search/1", params={
                "app_id": os.environ["ADZUNA_APP_ID"], "app_key": os.environ["ADZUNA_APP_KEY"],
                "what": q, "where": LOCATION, "results_per_page": 50, "max_days_old": 1}, timeout=30)
            for j in r.json().get("results", []):
                rows.append({"title": j.get("title"), "company": j.get("company", {}).get("display_name"),
                             "location": j.get("location", {}).get("display_name"),
                             "url": j.get("redirect_url"), "description": j.get("description", "")[:1500],
                             "source": "adzuna"})
        except Exception as e:
            print("Adzuna error:", e)

    # Jooble
    if has("JOOBLE_KEY"):
        try:
            r = requests.post(f"https://jooble.org/api/{os.environ['JOOBLE_KEY']}",
                              json={"keywords": q, "location": LOCATION}, timeout=30)
            for j in r.json().get("jobs", []):
                rows.append({"title": j.get("title"), "company": j.get("company"),
                             "location": j.get("location"), "url": j.get("link"),
                             "description": j.get("snippet", "")[:1500], "source": "jooble"})
        except Exception as e:
            print("Jooble error:", e)

    # USAJobs
    if has("USAJOBS_KEY", "USAJOBS_EMAIL"):
        try:
            r = requests.get("https://data.usajobs.gov/api/search", headers={
                "Host": "data.usajobs.gov",
                "User-Agent": os.environ["USAJOBS_EMAIL"],
                "Authorization-Key": os.environ["USAJOBS_KEY"]},
                params={"Keyword": q, "LocationName": "New York, New York",
                        "ResultsPerPage": 50, "DatePosted": 1}, timeout=30)
            for item in r.json().get("SearchResult", {}).get("SearchResultItems", []):
                j = item.get("MatchedObjectDescriptor", {})
                rows.append({"title": j.get("PositionTitle"), "company": j.get("OrganizationName"),
                             "location": j.get("PositionLocationDisplay"), "url": j.get("PositionURI"),
                             "description": (j.get("QualificationSummary") or "")[:1500],
                             "source": "usajobs"})
        except Exception as e:
            print("USAJobs error:", e)

os.makedirs("data", exist_ok=True)
pd.DataFrame(rows).to_csv("data/api_jobs.csv", index=False)
print(f"Saved {len(rows)} API jobs")