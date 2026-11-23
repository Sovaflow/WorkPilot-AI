import unittest
from datetime import date
from workpilot.engine import (planned_recurring, merge_tasks,
                              extract_meeting_proposals, prepare_morning,
                              prepare_weekly, render_morning)


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.rule = [{"id": "daily-brief", "title": "Daily briefing",
                      "frequency": "weekly", "weekdays": [0, 1, 2, 3, 4],
                      "due_time": "08:30", "preparation": "Review updates"}]
        self.event = {"id": "e1", "title": "Standup",
                      "starts_at": "2026-11-24T09:00:00+01:00",
                      "ends_at": "2026-11-24T09:15:00+01:00"}

    def test_weekdays(self):
        dates = planned_recurring(self.rule, date(2026, 11, 23), date(2026, 11, 29))
        self.assertEqual(len(dates), 5)

    def test_explicit_completion_overrides_recurring(self):
        occ = planned_recurring(self.rule, date(2026, 11, 24), date(2026, 11, 24))
        merged = merge_tasks([{"id": occ[0]["id"], "status": "done"}], occ)
        self.assertEqual(merged[0]["status"], "done")

    def test_duplicates_not_proposed(self):
        mails = [{"id": "1", "snippet": "[MEETING] Standup | 2026-11-24T09:00:00+01:00 | 2026-11-24T09:15:00+01:00"}]
        self.assertEqual(extract_meeting_proposals(mails, [self.event]), [])

    def test_new_meeting_pending_approval(self):
        mails = [{"id": "1", "snippet": "[MEETING] Review | 2026-11-24T14:00:00+01:00 | 2026-11-24T14:30:00+01:00"}]
        proposals = extract_meeting_proposals(mails, [self.event])
        self.assertEqual(proposals[0]["status"], "pending_approval")

    def test_morning_prioritizes_overdue(self):
        tasks = [{"id": "late", "title": "Late task", "due_date": "2026-11-23", "status": "open"}]
        plan = prepare_morning(date(2026, 11, 24), [], [self.event], tasks, self.rule)
        self.assertTrue(any(t["id"] == "late" for t in plan["overdue_tasks"]))
        self.assertIn("Standup", render_morning(plan))

    def test_unseen_recurring_history_not_falsely_overdue(self):
        report = prepare_morning(date(2026, 11, 24), [], [self.event], [], self.rule)
        self.assertEqual(report["overdue_tasks"], [])
        self.assertEqual(len(report["tasks_due"]), 1)

    def test_ai_proposals_are_review_only(self):
        suggestion = [{"proposal_id": "task:m1:1", "source_email_id": "m1",
                       "title": "Check KPI report", "due_date": "2026-11-27",
                       "status": "pending_review"}]
        report = prepare_morning(date(2026, 11, 24), [], [], [], [], suggestion)
        self.assertEqual(report["task_proposals"], suggestion)
        self.assertEqual(report["tasks_due"], [])
        self.assertIn("Check KPI report", render_morning(report))

    def test_weekly_requires_explicit_done(self):
        tasks = [{"id": "done", "title": "Completed", "due_date": "2026-11-24", "status": "done"},
                 {"id": "open", "title": "Unfinished", "due_date": "2026-11-25", "status": "open"}]
        report = prepare_weekly(date(2026, 11, 27), [], tasks, [])
        self.assertEqual(len(report["completed"]), 1)
        self.assertEqual(len(report["open"]), 1)


if __name__ == "__main__":
    unittest.main()
