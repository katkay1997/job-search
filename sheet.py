# sheet.py
# ------------------------------------------------------------------
# Saves a job as a new row in your Google Sheet.
# Uses a Google "robot account" (service account). Its key file lives
# in the job-finder-secrets folder, never in this folder.
# ------------------------------------------------------------------
from datetime import date

HEADERS = ["Date Saved", "Title", "Company", "Location", "Source", "Link", "Status"]
LINK_COLUMN = 6  # "Link" is the 6th column; used to avoid saving the same job twice


def _worksheet(keys):
    import gspread  # only loaded when you actually save something
    client = gspread.service_account(filename=keys["GOOGLE_ROBOT_FILE"])
    return client.open_by_key(keys["SHEET_ID"]).sheet1


def save_job(job, keys):
    """Returns 'saved' or 'already saved'."""
    ws = _worksheet(keys)
    if not ws.row_values(1):
        ws.append_row(HEADERS)
    if job["url"] in ws.col_values(LINK_COLUMN):
        return "already saved"
    ws.append_row(
        [date.today().isoformat(), job["title"], job["company"], job["location"],
         job["source"], job["url"], "To review"],
        value_input_option="RAW",  # RAW = treat everything as plain text (safer)
    )
    return "saved"
