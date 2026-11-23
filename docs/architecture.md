# Architecture and safeguards

```
Gmail API (read-only) + Calendar API (read-only) + recurring registry + explicit task status
                                   |
                                   v
                   Normalize, reconcile, deduplicate
                       /          |           \
                 Morning      Weekly review   Proposals
                 briefing                     (pending)
                                                |
                                    Separate manual approval
                                                |
                                     Calendar write adapter
```

- Stable recurring occurrence IDs: `rule_id:YYYY-MM-DD`.
- Explicit task status `done` is the only evidence of completion; lack of a reply is not.
- Structured demo invitations are checked against existing title and start time.
- Email excerpts are **untrusted input**, not instructions to the agent.
- Calendar writes require approval and a separate OAuth token with write scope.
- The LLM only summarizes a deterministic report; it cannot authorize actions.
- No production personal data, credentials or generated reports belong in source control.

**Limitations:** Demo invitation parser is deliberately narrow; production would require validated extraction, proper persistence, retries, consent/access-control review, observability and time-zone testing. Automated tests do not validate real provider connections.
