# WorkPilot AI - Intelligent Workday Assistant

**Portfolio project | Python · AI Agent · Gmail API · Google Calendar API · Workflow Automation**

An offline-first **working prototype** that combines email, calendar, task status and recurring obligations to produce a morning agenda, suggest meetings and prepare a weekly review. The architecture extends an earlier scheduled API → logging → notification workflow with task reconciliation and optional LLM summarization.

> **Status:** synthetic offline demo and unit tests work. Real Google API, LLM and SMTP integrations are **opt-in adapters, not deployed or verified live**. Google Calendar insertion requires separate OAuth write permission and explicit human approval. No real personal data or credentials appear here.

## Capabilities

1. Collect message metadata and calendar entries from synthetic fixtures, or read-only Google APIs.
2. Reconcile daily / weekly / monthly recurring obligations with task status.
3. Identify structured demonstration invitations, check for duplicate calendar events, and prepare **approval-only** proposals.
4. Generate daily briefings (meetings, preparation, overdue tasks, unresolved items).
5. Generate weekly review (explicitly completed vs. still open; next-week plan).
6. Optionally use an LLM for summarization or SMTP for delivery. These are *off by default*.

## Architecture

```text
Gmail (optional) ─┐
Calendar (optional) ─┤
Recurring tasks ────┼─> WorkPilot reconciliation ──> Morning briefing / Weekly review
Task status ────────┘                             └─> Meeting proposals
                                                         |
                                                explicit human approval
                                                         |
                                             optional Google Calendar write
```

## What's new: persistent tasks and AI extraction

- **SQLite task ledger:** completion status persists across runs, including recurring occurrences. Historical tasks only become overdue if they were actually recorded.
- **AI task proposal workflow:** extract action items from ordinary email snippets into structured, source-linked proposals. New tasks remain **pending review**; nothing is silently added.
- **Two extraction modes:** `--extract demo` reads a fabricated, prewritten extraction (no API); `--extract ai` explicitly calls OpenAI and requires an API key. This is not a trained custom model.
- **Human confirmation:** only approved, dated suggestions enter the ledger. Meeting creation remains a separate manual operation.
- **Daily and weekly planning:** unfinished tasks carry into future reviews without falsely labelling unseen recurring occurrences as missed.

## Offline demo — no API keys or packages required

Python 3.10+:

```bash
python -m workpilot --mode morning --date 2026-11-24
python -m workpilot --mode weekly --date 2026-11-27
# Mark a recorded task as complete, then rerun the weekly report:
python -m workpilot --complete weekly-report:2026-11-27
python -m workpilot --mode weekly --date 2026-11-27
python -m unittest discover -s tests -v
```

Generated Markdown/JSON reports and the SQLite database are saved in `outputs/` (gitignored). These files stay local.

### Approving an extracted task

Review `outputs/morning_2026-11-24_task_proposals.json`. Put the proposal IDs you genuinely approve into a **local**, untracked file:

```json
{"approved_proposal_ids": ["task:mail-demo-02:1"]}
```

Save it as `outputs/approvals.json`, then run:

```bash
python -m workpilot --mode morning --date 2026-11-24 --approve-file outputs/approvals.json
```

An extracted task without a reliable due date **cannot** be approved until a date is supplied. Meeting proposals follow a separate manual approval path.

### Optional AI parsing with fabricated email data only

```bash
# Requires a locally configured OPENAI_API_KEY, and sends demo excerpts to OpenAI
python -m workpilot --mode morning --date 2026-11-24 --extract ai
```

Never use real private email or workplace content without appropriate authorization. No AI calls are made by the default demo.

## Optional live integrations (not activated or tested against personal accounts)

Install `pip install -r requirements.txt`, configure a Google Cloud **Desktop OAuth** client locally as `credentials.json` (never commit), then run:

```bash
python -m workpilot --mode morning --source google --extract off
```

The Google reader uses **Gmail read-only and Calendar read-only** scopes. The task registry remains the demonstration fixture unless you replace it privately. Email excerpts should be treated as untrusted data. The extraction example recognizes only explicitly structured `[MEETING]` demo invitations, **not arbitrary natural-language invitation emails**.

With `OPENAI_API_KEY`, add `--llm` for a summary; the generated briefing is transmitted to OpenAI, so do not use private workplace content without an appropriate privacy review. To opt in to SMTP delivery, configure `WORKPILOT_SMTP_HOST`, `WORKPILOT_SMTP_USER`, `WORKPILOT_SMTP_PASSWORD`, `WORKPILOT_RECIPIENT` and pass `--send`.

See [scheduling and manual calendar approval](docs/scheduling.md) and [architecture and safeguards](docs/architecture.md).

## Repository

- `workpilot/` — deterministic agent engine and optional integrations
- `examples/` — entirely fabricated input data
- `tests/` — offline unit tests
- `docs/` — integration and scheduling guidance
- `tests/` — optional local unit tests using fictional example data (no automatic GitHub workflows)

## Design principles

**Safe autonomy:** read-only by default; no autonomous email responses or calendar modifications. **Reliable status:** only explicitly completed tasks count as done. **Idempotency:** stable recurring task IDs and duplicate meeting checks. **Privacy:** secrets and personal reports are excluded from version control.

### Next improvements

Validated natural-language meeting extraction, stronger logging and retries, timezone policy, explicit task-history UI, and a compact dashboard. These are proposals, not completed features.

*Portfolio reconstruction: independently built demonstration; not a deployed production assistant.*
