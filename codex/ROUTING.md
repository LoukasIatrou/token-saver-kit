## Model routing (token-saver-kit)

Delegate work to the cheapest subagent that can do it well:

- `quick_task` (fast model): searches, reading/summarising code, renames, formatting, running tests, one-file edits.
- `builder` (balanced model): implementing features from a clear plan, bug fixes with a known cause, tests.
- `deep_reasoner` (frontier model): architecture, unknown-cause bugs after a failed attempt, security review.

Do small things yourself only when delegating would cost more than doing them.
