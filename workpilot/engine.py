"""Deterministic reconciliation; no external I/O or LLM decisions."""
import re
from datetime import date, datetime, timedelta, time
from collections import Counter


def occurrence_dates(rule, start, end):
    result = []
    current = start
    while current <= end:
        frequency = rule["frequency"]
        eligible = (
            frequency == "daily" or
            (frequency == "weekly" and current.weekday() in rule.get("weekdays", [])) or
            (frequency == "monthly" and current.day == int(rule.get("day_of_month", 1)))
        )
        if eligible:
            result.append(current)
        current += timedelta(days=1)
    return result


def planned_recurring(rules, start, end):
    result = []
    for rule in rules:
        for day in occurrence_dates(rule, start, end):
            result.append({
                "id": f'{rule["id"]}:{day.isoformat()}',
                "title": rule["title"],
                "due_date": day.isoformat(),
                "due_time": rule.get("due_time", ""),
                "preparation": rule.get("preparation", ""),
                "status": "open",
                "source": "recurring",
            })
    return sorted(result, key=lambda x: (x["due_date"], x.get("due_time", ""), x["title"]))


def merge_tasks(tasks, recurring):
    """An explicit task record may override a recurring occurrence's status."""
    merged = {t["id"]: dict(t) for t in recurring}
    for task in tasks:
        merged[task["id"]] = dict(task)
    return list(merged.values())


def extract_meeting_proposals(messages, calendar):
    """Recognize only structured demo invitations; never interpret arbitrary email."""
    proposals = []
    existing = {(e["title"].casefold().strip(), e["starts_at"]) for e in calendar}
    seen = set()
    pattern = re.compile(r"\[MEETING\]\s*([^|]+)\|\s*([^|]+)\|\s*([^|\n]+)", re.I)
    for msg in messages:
        match = pattern.search(msg.get("snippet", ""))
        if not match:
            continue
        title, start_raw, end_raw = (item.strip() for item in match.groups())
        try:
            starts, ends = datetime.fromisoformat(start_raw), datetime.fromisoformat(end_raw)
        except ValueError:
            continue
        if starts.tzinfo is None or ends.tzinfo is None or ends <= starts:
            continue
        key = (title.casefold(), starts.isoformat())
        if key in existing or key in seen:
            continue
        seen.add(key)
        proposals.append({
            "proposal_id": "proposal:" + str(msg["id"]),
            "email_id": str(msg["id"]),
            "title": title,
            "starts_at": starts.isoformat(),
            "ends_at": ends.isoformat(),
            "status": "pending_approval",
        })
    return proposals


def prepare_morning(day, messages, calendar, tasks, rules):
    recurring = planned_recurring(rules, day - timedelta(days=30), day)
    merged = merge_tasks(tasks, recurring)
    today_tasks = sorted((t for t in merged if t["due_date"] == day.isoformat() and t["status"] != "done"),
                         key=lambda t: t.get("due_time", ""))
    overdue = sorted((t for t in merged if t["due_date"] < day.isoformat() and t["status"] != "done"),
                     key=lambda t: t["due_date"])
    today_events = sorted((e for e in calendar if datetime.fromisoformat(e["starts_at"]).date() == day),
                          key=lambda e: e["starts_at"])
    proposals = extract_meeting_proposals(messages, calendar)
    return {"date": day.isoformat(), "meetings": today_events, "tasks_due": today_tasks,
            "overdue_tasks": overdue, "meeting_proposals": proposals,
            "unread_email_context": [{"subject": x.get("subject", ""), "snippet": x.get("snippet", "")}
                                     for x in messages[:10]]}


def prepare_weekly(day, calendar, tasks, rules):
    monday = day - timedelta(days=day.weekday())
    sunday = monday + timedelta(days=6)
    next_monday = monday + timedelta(days=7)
    next_sunday = next_monday + timedelta(days=6)
    all_occurrences = planned_recurring(rules, monday, next_sunday)
    merged = merge_tasks(tasks, all_occurrences)
    week = [t for t in merged if monday.isoformat() <= t["due_date"] <= sunday.isoformat()]
    completed = [t for t in week if t["status"] == "done"]
    open_tasks = [t for t in week if t["status"] != "done"]
    next_week = [t for t in merged if next_monday.isoformat() <= t["due_date"] <= next_sunday.isoformat()]
    next_events = [e for e in calendar
                   if next_monday <= datetime.fromisoformat(e["starts_at"]).date() <= next_sunday]
    return {
        "week_start": monday.isoformat(), "week_end": sunday.isoformat(),
        "completed": completed, "open": open_tasks,
        "next_week_tasks": sorted(next_week, key=lambda t: t["due_date"]),
        "next_week_meetings": sorted(next_events, key=lambda e: e["starts_at"]),
        "status_counts": dict(Counter(t["status"] for t in week)),
    }


def render_morning(plan):
    lines = [f'# WorkPilot | Morning briefing — {plan["date"]}', "",
             "## Calendar"]
    if plan["meetings"]:
        for meeting in plan["meetings"]:
            lines.append(f'- {meeting["starts_at"][11:16]} — {meeting["title"]} | Prepare: {meeting.get("description", "review agenda")}')
    else:
        lines.append("- No confirmed meetings")
    lines += ["", "## Prepare / due today"]
    lines += [f'- {task["title"]} — {task.get("preparation", "")}' for task in plan["tasks_due"]] or ["- No tasks due"]
    lines += ["", "## Overdue / still open"]
    lines += [f'- {task["due_date"]}: {task["title"]}' for task in plan["overdue_tasks"]] or ["- No overdue tasks"]
    lines += ["", "## Proposed meetings (approval required)"]
    lines += [f'- {p["starts_at"]}: {p["title"]}' for p in plan["meeting_proposals"]] or ["- No new proposals"]
    lines += ["", "## Email context (untrusted, for review)"]
    lines += [f'- {m["subject"]}' for m in plan["unread_email_context"]] or ["- No messages"]
    return "\n".join(lines) + "\n"


def render_weekly(report):
    lines = [f'# WorkPilot | Weekly review — {report["week_start"]} to {report["week_end"]}',
             "", "## Confirmed completed"]
    lines += [f'- {t["title"]}' for t in report["completed"]] or ["- No explicitly completed tasks"]
    lines += ["", "## Outstanding"]
    lines += [f'- {t["due_date"]}: {t["title"]}' for t in report["open"]] or ["- None"]
    lines += ["", "## Next week"]
    lines += [f'- {t["due_date"]}: {t["title"]} — {t.get("preparation", "")}' for t in report["next_week_tasks"]] or ["- None scheduled"]
    lines += ["", "## Upcoming meetings"]
    lines += [f'- {e["starts_at"]}: {e["title"]}' for e in report["next_week_meetings"]] or ["- None scheduled"]
    return "\n".join(lines) + "\n"
