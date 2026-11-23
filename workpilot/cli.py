"""CLI entrypoint for deterministic demo and optional integrations."""
import argparse
import json
from datetime import date
from pathlib import Path
from .engine import prepare_morning, prepare_weekly, render_morning, render_weekly


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description="WorkPilot AI: offline-first workday assistant")
    parser.add_argument("--mode", choices=["morning", "weekly"], default="morning")
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--source", choices=["demo", "google"], default="demo")
    parser.add_argument("--llm", action="store_true", help="Send composed briefing to an LLM")
    parser.add_argument("--send", action="store_true", help="Send report through configured SMTP")
    parser.add_argument("--output-dir", default="outputs")
    args = parser.parse_args()
    day = date.fromisoformat(args.date)

    calendar = read_json("examples/calendar.json")
    messages = read_json("examples/messages.json")
    tasks = read_json("examples/tasks.json")
    recurring = read_json("examples/recurring_tasks.json")
    if args.source == "google":
        from .google_reader import load_google
        messages, calendar = load_google(day)

    if args.mode == "morning":
        report = prepare_morning(day, messages, calendar, tasks, recurring)
        markdown = render_morning(report)
    else:
        report = prepare_weekly(day, calendar, tasks, recurring)
        markdown = render_weekly(report)

    if args.llm:
        from .llm_summary import summarize
        markdown += "\n## Optional AI summary\n\n" + summarize(markdown) + "\n"

    path = Path(args.output_dir)
    path.mkdir(parents=True, exist_ok=True)
    prefix = f"{args.mode}_{day.isoformat()}"
    (path / f"{prefix}.md").write_text(markdown, encoding="utf-8")
    (path / f"{prefix}.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    if args.mode == "morning":
        (path / f"{prefix}_proposals.json").write_text(
            json.dumps(report["meeting_proposals"], indent=2), encoding="utf-8")
    if args.send:
        from .mailer import send
        send(f"WorkPilot {args.mode} — {day.isoformat()}", markdown)
    print(markdown)
    print(f"Saved reports under {path}/")


if __name__ == "__main__":
    main()
