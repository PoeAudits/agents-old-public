# Gene Scout JSON Examples and Uncertainty Rules

Return strict JSON only. Do not wrap in markdown fences.

## Example A: Single Exemplar -> Single Candidate

```json
{
  "schema_version": "1.1",
  "request": {
    "query": "Find local embedding deduplication pattern",
    "source_roots": ["/local/repo"],
    "search_terms": ["embedding", "cosine", "deduplication"]
  },
  "result": {
    "status": "found",
    "confidence": 0.92,
    "gene_candidate": {
      "proposed_id": "dedupe.cosine-batch",
      "title": "Batch cosine deduplication with local embeddings",
      "summary": "Embed all inputs once, compare against history and accepted in-batch items, reject near-duplicates over threshold.",
      "tags": ["dedup", "embedding", "cosine", "batch"],
      "languages": ["python"],
      "pattern_spec": [
        "Load prior records and prune by time horizon.",
        "Generate embeddings for all new items in one batch call.",
        "For each item, compute max cosine similarity against stored and accepted in-batch vectors.",
        "Reject item when max similarity is at or above threshold; otherwise accept.",
        "Persist accepted items with embedding and timestamp for future checks."
      ],
      "invariants": [
        "Embedding count must match input item count.",
        "Similarity metric remains cosine for stored and query vectors.",
        "Only accepted unique items are committed to history."
      ],
      "edge_cases": [
        "Empty input returns empty result.",
        "Embedder failure marks all items failed.",
        "Zero-norm vectors produce similarity 0.0."
      ],
      "pitfalls": [
        "Model mismatch across stored embeddings and query embeddings can corrupt scores.",
        "Threshold too low causes false positives."
      ],
      "provenance": [
        {
          "origin_note": "Extracted from a local Python deduplication implementation",
          "symbols": ["DeduplicationEngine.check_batch"],
          "search_terms": ["check_batch", "cosine"]
        }
      ],
      "snippets_by_language": {
        "python": [
          {
            "symbol": "DeduplicationEngine.check_batch",
            "code": "for text, emb, item_id in zip(items, embeddings, ids):\n    ...",
            "source_note": "Representative loop and threshold branch",
            "why_relevant": "Core scoring and threshold branching logic."
          }
        ]
      },
      "dedupe_fingerprint": "dedupe.cosine-batch|python|check_batch"
    }
  }
}
```

## Example B: Multiple Exemplars -> Merged Candidate

```json
{
  "schema_version": "1.1",
  "request": {
    "query": "Find retry with exponential backoff pattern",
    "source_roots": ["/repo-a", "/repo-b"],
    "search_terms": ["retry", "backoff", "jitter"]
  },
  "result": {
    "status": "found",
    "confidence": 0.81,
    "gene_candidate": {
      "proposed_id": "http.retry.exponential-backoff",
      "title": "Retry with bounded exponential backoff",
      "summary": "Retry transient errors with capped exponential delay and optional jitter.",
      "tags": ["retry", "backoff", "resilience"],
      "languages": ["python", "typescript"],
      "pattern_spec": [
        "Classify retryable failures.",
        "Use bounded exponential delay for each attempt.",
        "Stop after max attempts and surface terminal error."
      ],
      "invariants": [
        "Backoff cap must be enforced.",
        "Attempt count must be finite."
      ],
      "edge_cases": [
        "Timeout cancellation in async contexts.",
        "Clock skew when delay scheduling is externalized."
      ],
      "pitfalls": [
        "Retrying non-idempotent operations without safeguards."
      ],
      "provenance": [
        {
          "origin_note": "Merged from two local exemplars with equivalent semantics",
          "symbols": ["retry_call", "retryRequest"],
          "search_terms": ["retry", "backoff", "jitter"]
        }
      ],
      "snippets_by_language": {
        "python": [
          {
            "symbol": "retry_call",
            "code": "delay = min(cap_s, base_s * (2 ** attempt))",
            "why_relevant": "Shows capped exponential growth."
          }
        ],
        "typescript": [
          {
            "symbol": "retryRequest",
            "code": "const sleepMs = Math.min(capMs, baseMs * 2 ** attempt)",
            "why_relevant": "Equivalent implementation in TS."
          }
        ]
      },
      "dedupe_fingerprint": "http.retry.exponential-backoff|python,typescript"
    }
  }
}
```

## Example C: Not Found Shape

```json
{
  "schema_version": "1.1",
  "request": {
    "query": "Find CRDT merge pattern in local repos",
    "source_roots": ["/repo-a"],
    "search_terms": ["CRDT", "merge", "lamport"]
  },
  "result": {
    "status": "not_found",
    "reason": "No implementation with concrete merge logic and source-backed snippets was found.",
    "confidence": 0.64,
    "searched_locations": ["src", "lib"]
  }
}
```

## Uncertainty Handling Rules

- Partial confidence: return `status: "found"` only when pattern steps are backed by at least one snippet and one provenance note.
- Missing context: populate `gaps` inside `gene_candidate` and reduce `confidence`.
- Weak evidence across many files: prefer `status: "not_found"` over speculative synthesis.
- Keep output portable: do not require absolute paths or fixed line ranges in stored artifacts.
