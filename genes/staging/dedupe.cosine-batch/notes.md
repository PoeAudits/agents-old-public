# Notes

- Confidence: 0.92
- Generated: 2026-02-08T21:43:00Z
- Updated: 2026-02-08T22:20:00Z

## Pattern

1. Load prior records and prune by time horizon.
2. Generate embeddings for all new items in one batch call.
3. For each item, compute max cosine similarity against stored and accepted in-batch vectors.
4. Reject item when max similarity is at or above threshold; otherwise accept.
5. Persist accepted items with embedding and timestamp for future checks.

## Invariants

- Embedding count must match input item count.
- Similarity metric remains cosine for stored and query vectors.
- Only accepted unique items are committed to history.

## Edge Cases

- Empty input returns empty result.
- Embedder failure marks all items failed.
- Zero-norm vectors produce similarity 0.0.

## Pitfalls

- Model mismatch across stored embeddings and query embeddings can corrupt scores.
- Threshold too low causes false positives.

## Gaps

- Verification not completed yet; keep this gene in staging.

## Post-Use Notes

- 2026-02-08: Initial snippet was too truncated (ellipsis); replaced with full representative block.
- 2026-02-08: Model load logs can be noisy; search script now suppresses them by default.
- Add new entries here when runtime surprises or dependency drift appears.
