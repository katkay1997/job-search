import os, pandas as pd
from jobspy import scrape_jobs

df = scrape_jobs(site_name=["indeed", "zip_recruiter"],
                 search_term="junior software engineer",
                 location="New York, NY", results_wanted=40,
                 hours_old=24, country_indeed="USA")
df = df.rename(columns={"job_url": "url", "site": "source"})
df["description"] = df["description"].fillna("").str[:1500]
os.makedirs("data", exist_ok=True)
df[["title", "company", "location", "url", "description", "source"]].to_csv(
    "data/jobspy_jobs.csv", index=False)
print(f"Saved {len(df)} JobSpy jobs")