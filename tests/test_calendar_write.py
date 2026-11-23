import json
import tempfile
import unittest
from pathlib import Path
from workpilot.calendar_write import apply_approved


class CalendarApprovalTests(unittest.TestCase):
    def test_unapproved_is_not_created(self):
        with tempfile.TemporaryDirectory() as directory:
            proposal = Path(directory) / "proposals.json"
            approvals = Path(directory) / "approvals.json"
            proposal.write_text(json.dumps([{
                "proposal_id": "proposal:1", "status": "pending_approval", "title": "Review",
                "starts_at": "2026-11-24T14:00:00+01:00",
                "ends_at": "2026-11-24T15:00:00+01:00"}]))
            approvals.write_text(json.dumps({"approved_proposal_ids": []}))
            output = apply_approved(proposal, approvals, execute=False)
            self.assertEqual(output["created"], [])
            self.assertEqual(output["selected"], [])


if __name__ == "__main__":
    unittest.main()
