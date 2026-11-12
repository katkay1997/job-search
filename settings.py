# settings.py
# ------------------------------------------------------------------
# Your search settings. NOTHING SECRET GOES IN THIS FILE.
# It's safe to show this file to Gemini or put it on GitHub.
# ------------------------------------------------------------------

# What the search box starts with when you open the page
DEFAULT_SEARCH = "junior developer"
DEFAULT_WHERE = "New York, NY"

# Jobs whose TITLE contains any of these words get hidden.
# (Keeps out jobs that are way above entry level.)
EXCLUDE_TITLE_WORDS = [
    "senior", "sr.", "sr ", "lead", "principal", "staff", "manager",
    "director", "architect", "head of", "vp", "vice president",
]

# Jobs whose COMPANY name contains any of these words get hidden.
# Example: ["some company i never want to see"]
EXCLUDE_COMPANY_WORDS = []

# Extra words that count as "the same place" as your search location.
# Used for sources that can't filter by location themselves.
PLACE_NICKNAMES = {
    "new york": ["new york", "nyc", "brooklyn", "manhattan", "queens", "bronx", "staten island"],
}

# For remote-only sources: keep a remote job only if its "allowed location"
# mentions one of these (or says nothing at all).
REMOTE_OK_WORDS = ["usa", "us", "united states", "america", "americas",
                   "north america", "worldwide", "anywhere", "global"]

# The Muse: which job categories to pull ENTRY LEVEL jobs from.
# (The Muse ignores your search words and uses these instead.)
# Other options include "Customer Service", "Sales", "Education", "Project Management".
MUSE_CATEGORIES = ["Software Engineering", "Data and Analytics", "IT"]

# How many jobs to ask each source for
RESULTS_PER_SOURCE = 50

# Remember search results for this many hours so you don't
# burn through your free API limits by searching the same thing twice.
CACHE_HOURS = 6

# The server only listens on YOUR computer. Don't change this.
HOST = "127.0.0.1"
PORT = 5000
