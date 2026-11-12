import os, pandas as pd

files = [f for f in ["data/api_jobs.csv", "data/jobspy_jobs.csv"] if os.path.exists(f)]
df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
df = df.drop_duplicates(subset=["title", "company"])
df.to_csv("data/jobs_today.csv", index=False)
print(f"{len(df)} unique jobs")
