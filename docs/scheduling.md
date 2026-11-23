# Scheduling and approval

WorkPilot does not schedule itself. On your trusted computer, use a local scheduler such as cron or Windows Task Scheduler. Example Linux cron (machine-local time):

```cron
0 8 * * 1-5 cd /absolute/path/to/WorkPilot-AI && /usr/bin/python3 -m workpilot --mode morning --source demo
0 17 * * 5 cd /absolute/path/to/WorkPilot-AI && /usr/bin/python3 -m workpilot --mode weekly --source demo
```

Replace `demo` with `google` only after authorizing OAuth. The example task registry is synthetic; replace it with a private registry for real use. To send generated briefings by email, configure your own SMTP credentials and add `--send`. Avoid uploading private output to public CI artifacts.

## Calendar writes: separate manual step

1. Review `outputs/morning_YYYY-MM-DD_proposals.json`.
2. Create a private `approvals.json` file containing `{"approved_proposal_ids":["..."]}`.
3. From a trusted local Python session, run:

```python
from workpilot.calendar_write import apply_approved
apply_approved("outputs/morning_2026-11-24_proposals.json", "approvals.json", execute=True)
```

This action separately requests Google Calendar **events write** access, checks for duplicates, and adds only the explicitly approved proposals. It is not invoked during the automated morning or weekly run.
