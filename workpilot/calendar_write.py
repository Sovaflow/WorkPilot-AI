"""Separately invoked, human-approved Google Calendar event creation."""
import json
from pathlib import Path
from datetime import datetime, timedelta


WRITE_SCOPES = ["https://www.googleapis.com/auth/calendar.events"]


def apply_approved(proposal_file, approvals_file, execute=False):
    proposals = json.loads(Path(proposal_file).read_text(encoding="utf-8"))
    approved = set(json.loads(Path(approvals_file).read_text(encoding="utf-8")).get("approved_proposal_ids", []))
    selected = [p for p in proposals if p["proposal_id"] in approved and p["status"] == "pending_approval"]
    if len({p["proposal_id"] for p in selected}) != len(selected):
        raise ValueError("Duplicate proposal IDs")
    if not execute:
        return {"mode": "dry_run", "selected": selected, "created": []}
    if not selected:
        return {"mode": "execute", "selected": [], "created": []}

    # Only this explicit manual function accesses calendar write scope.
    from googleapiclient.discovery import build
    from .google_reader import credentials
    service = build("calendar", "v3", credentials=credentials(WRITE_SCOPES, "calendar_write_token.json"))
    created = []
    for proposal in selected:
        starts = datetime.fromisoformat(proposal["starts_at"])
        ends = datetime.fromisoformat(proposal["ends_at"])
        if starts.tzinfo is None or ends.tzinfo is None or ends <= starts:
            raise ValueError("Calendar proposal requires valid timezone-aware times")
        existing = service.events().list(
            calendarId="primary", timeMin=(starts - timedelta(minutes=1)).isoformat(),
            timeMax=ends.isoformat(), singleEvents=True, maxResults=100).execute().get("items", [])
        duplicate = any(
            (e.get("summary", "").casefold().strip() == proposal["title"].casefold().strip())
            and e.get("start", {}).get("dateTime") is not None
            and datetime.fromisoformat(e["start"]["dateTime"]) == starts
            for e in existing)
        if duplicate:
            continue
        event = service.events().insert(calendarId="primary", body={
            "summary": proposal["title"],
            "start": {"dateTime": starts.isoformat()},
            "end": {"dateTime": ends.isoformat()},
            "description": "Created after manual approval of WorkPilot proposal " + proposal["proposal_id"],
        }).execute()
        created.append({"proposal_id": proposal["proposal_id"], "event_id": event["id"]})
    return {"mode": "execute", "selected": selected, "created": created}
