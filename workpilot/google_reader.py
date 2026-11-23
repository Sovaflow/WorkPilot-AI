"""Optional Google API read-only adapter. Local OAuth credentials are never committed."""
from datetime import datetime, timedelta, time
from pathlib import Path


SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
]


def credentials(scopes, token_file="token.json"):
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    import json
    creds = None
    if Path(token_file).exists():
        creds = Credentials.from_authorized_user_file(token_file, scopes)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    if not creds or not creds.valid:
        if not Path("credentials.json").exists():
            raise RuntimeError("Create private credentials.json from a Google Cloud OAuth desktop client")
        flow = InstalledAppFlow.from_client_secrets_file("credentials.json", scopes)
        creds = flow.run_local_server(port=0)
    Path(token_file).write_text(creds.to_json(), encoding="utf-8")
    return creds


def load_google(day):
    """Return normalized messages + events; no email bodies or personal contacts stored."""
    from googleapiclient.discovery import build
    creds = credentials(SCOPES)
    gmail = build("gmail", "v1", credentials=creds)
    gcal = build("calendar", "v3", credentials=creds)

    # Limit to the recent inbox, with subject/snippet only.
    messages = []
    for item in gmail.users().messages().list(userId="me", q="newer_than:7d", maxResults=30).execute().get("messages", []):
        msg = gmail.users().messages().get(userId="me", id=item["id"], format="metadata",
                    metadataHeaders=["Subject", "From", "Date"]).execute()
        headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
        messages.append({"id": item["id"], "subject": headers.get("subject", ""),
                         "sender": headers.get("from", ""), "received_at": headers.get("date", ""),
                         "snippet": msg.get("snippet", "")})

    # Wide enough to include next-week review, but bounded and read-only.
    start = datetime.combine(day - timedelta(days=7), time.min).astimezone()
    end = datetime.combine(day + timedelta(days=15), time.max).astimezone()
    events = []
    page_token = None
    while True:
        result = gcal.events().list(calendarId="primary", timeMin=start.isoformat(),
                  timeMax=end.isoformat(), singleEvents=True, orderBy="startTime",
                  maxResults=250, pageToken=page_token).execute()
        for ev in result.get("items", []):
            start_data, end_data = ev.get("start", {}), ev.get("end", {})
            # All-day events are represented as midnight and tagged as all-day.
            start_at = start_data.get("dateTime") or (start_data.get("date", "") + "T00:00:00+00:00")
            end_at = end_data.get("dateTime") or (end_data.get("date", "") + "T00:00:00+00:00")
            if start_at and end_at:
                events.append({"id": ev["id"], "title": ev.get("summary", "(No title)"),
                               "starts_at": start_at, "ends_at": end_at,
                               "description": ev.get("description", "")[:500],
                               "all_day": bool(start_data.get("date"))})
        page_token = result.get("nextPageToken")
        if not page_token:
            break
    return messages, events
