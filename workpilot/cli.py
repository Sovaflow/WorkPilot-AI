"""CLI entrypoint for reproducible offline demo and optional live integrations."""
import argparse
import json
from datetime import date, datetime, timezone, timedelta
from pathlib import Path

from .engine import (prepare_morning, prepare_weekly, render_morning,
                     render_weekly, planned_recurring)
from .task_store import TaskStore
from .ai_extraction import extract_demo, extract_with_openai, approve_proposals


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description="WorkPilot: privacy-first workday assistant")
    parser.add_argument("--mode", choices=["morning", "weekly"], default="morning")
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--source", choices=["demo", "google"], default="demo")
    parser.add_argument("--extract", choices=["demo", "ai", "off"], default="demo",
                        help="Demo uses prewritten synthetic extraction; AI calls OpenAI explicitly")
    parser.add_argument("--llm", action="store_true", help="Send briefing for an optional LLM summary")
    parser.add_argument("--send", action="store_true", help="Send briefing through configured SMTP")
    parser.add_argument("--db", default="outputs/workpilot.db")
    parser.add_argument("--approve-file", help="Local JSON file with approved task proposal IDs")
    parser.add_argument("--complete", metavar="TASK_ID",
                        help="Mark an existing task as completed and exit")
    parser.add_argument("--output-dir", default="outputs")
    args = parser.parse_args()
    day = date.fromisoformat(args.date)
    if args.source == "google" and args.extract == "demo" and args.mode == "morning":
        parser.error("--source google requires explicit --extract off or --extract ai")

    store = TaskStore(args.db)
    try:
        if args.complete:
            store.mark_done(args.complete, datetime.now(timezone.utc).isoformat())
            print("Marked completed:", args.complete)
            return

        calendar = read_json("examples/calendar.json")
        messages = read_json("examples/messages.json")
        tasks = read_json("examples/tasks.json")
        rules = read_json("examples/recurring_tasks.json")
        if args.source == "google":
            from .google_reader import load_google
            messages, calendar = load_google(day)

        # Do not seed weeks of historic recurrences as if they were all uncompleted.
        if args.mode == "morning":
            due = planned_recurring(rules, day, day)
        else:
            monday = day - timedelta(days=day.weekday())
            due = planned_recurring(rules, monday, monday + timedelta(days=13))
        store.seed(tasks)
        store.seed(due)

        proposals = []
        if args.mode == "morning":
            if args.extract == "demo":
                proposals = extract_demo(messages)
            elif args.extract == "ai":
                proposals = extract_with_openai(messages, day)

        if args.approve_file:
            approved_ids = set(read_json(args.approve_file).get("approved_proposal_ids", []))
            accepted = approve_proposals(proposals, approved_ids)
            store.seed(accepted)

        saved_tasks = store.list_tasks()
        if args.mode == "morning":
            report = prepare_morning(day, messages, calendar, saved_tasks, rules, proposals)
            markdown = render_morning(report)
        else:
            report = prepare_weekly(day, calendar, saved_tasks, rules)
            markdown = render_weekly(report)

        if args.llm:
            from .llm_summary import summarize
            markdown += "\n## Optional AI summary\n\n" + summarize(markdown) + "\n"

        path = Path(args.output_dir)
        path.mkdir(parents=True, exist_ok=True)
        prefix = f"{args.mode}_{day.isoformat()}"
        (path / f"{prefix}.md").write_text(markdown, encoding="utf-8")
        (path / f"{prefix}.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        if args.mode == "morning":
            (path / f"{prefix}_proposals.json").write_text(
                json.dumps(report["meeting_proposals"], indent=2), encoding="utf-8")
            (path / f"{prefix}_task_proposals.json").write_text(
                json.dumps(proposals, indent=2), encoding="utf-8")
        if args.send:
            from .mailer import send
            send(f"WorkPilot {args.mode} — {day.isoformat()}", markdown)
        print(markdown)
        print(f"Saved reports under {path}/")
    finally:
        store.close()


if __name__ == "__main__":
    main()
