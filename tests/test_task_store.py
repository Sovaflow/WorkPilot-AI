import tempfile
import unittest
from pathlib import Path
from workpilot.task_store import TaskStore
from workpilot.ai_extraction import validate_proposals, approve_proposals


class StorageTests(unittest.TestCase):
    def test_completion_survives_reseeding(self):
        with tempfile.TemporaryDirectory() as folder:
            store = TaskStore(Path(folder) / "tasks.db")
            row = {"id": "weekly:2026-11-27", "title": "Weekly report",
                   "due_date": "2026-11-27", "status": "open"}
            store.seed([row])
            store.mark_done(row["id"], "2026-11-27T16:00:00+01:00")
            store.close()
            reopened = TaskStore(Path(folder) / "tasks.db")
            reopened.seed([row])
            self.assertEqual(reopened.list_tasks()[0]["status"], "done")
            reopened.close()

    def test_ai_proposals_need_approval(self):
        proposals = validate_proposals(
            [{"source_email_id": "m1", "title": "Prepare report", "due_date": "2026-11-27"}],
            {"m1"})
        self.assertEqual(proposals[0]["status"], "pending_review")
        self.assertEqual(approve_proposals(proposals, set()), [])
        self.assertEqual(len(approve_proposals(proposals, {proposals[0]["proposal_id"]})), 1)

    def test_reject_untraceable_proposal(self):
        with self.assertRaises(ValueError):
            validate_proposals([{"source_email_id": "unknown", "title": "Task"}], {"m1"})

    def test_missing_deadline_needs_human_input(self):
        proposals = validate_proposals(
            [{"source_email_id": "m1", "title": "Prepare report", "due_date": None}], {"m1"})
        with self.assertRaises(ValueError):
            approve_proposals(proposals, {proposals[0]["proposal_id"]})


if __name__ == "__main__":
    unittest.main()
