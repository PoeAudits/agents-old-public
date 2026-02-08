# Gene Candidate Analysis Template

Use this template for orchestrator synthesis output at:
`~/.agents/genes/staging/_analysis/<project-slug>-<timestamp>.md`

## Header

- Project: `<project name>`
- Path: `<local path>`
- Timestamp: `<UTC ISO timestamp>`
- Orchestrator: `@gene-orchestrator`
- Scout Count: `<2-6>`

## Scope Summary

- Goal of extraction run
- Constraints (local-only, portability, no brittle coupling)
- What was explicitly out of scope

## Scout Coverage Map

List each scout with distinct angle and query terms.

1. Scout A - `<angle>`
   - Search terms: `<terms>`
   - Coverage notes: `<what it inspected>`
2. Scout B - `<angle>`
   - Search terms: `<terms>`
   - Coverage notes: `<what it inspected>`

## Candidate Synthesis

For each candidate, use this structure.

### Candidate: `<proposed_id>`

- Tier: `RECOMMEND | MAYBE | REJECT`
- Title: `<title>`
- Summary: `<one-line summary>`
- Why this tier: `<short rationale>`
- Portability check: `<pass/fail + notes>`
- Adaptation effort: `Low | Medium | High`
- Overlap/Merge notes: `<dedupe or merge guidance>`
- Risks:
  - `<risk 1>`
  - `<risk 2>`

## Cross-Candidate Dedupe Notes

- Equivalent candidates identified
- Suggested merged IDs (if any)
- Conflicts or contradictions across scout outputs

## Suggested User Choices

1. Stage `<proposed_id>` because `<reason>`.
2. Stage `<proposed_id>` only after edits: `<required edits>`.
3. Do not stage `<proposed_id>` because `<reason>`.

## Staging Plan (If User Approves)

- Candidates selected by user
- Materialization command(s) to run
- Registry rebuild command
- Expected staged paths

## Final Decision Log

- User selected: `<ids or none>`
- Actions taken: `<materialized / skipped>`
- Follow-ups: `<if any>`
