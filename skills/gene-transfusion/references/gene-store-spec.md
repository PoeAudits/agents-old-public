# Gene Store Specification (v1)

## Canonical Paths

- `~/.agents/genes/staging/`
- `~/.agents/genes/confirmed/`
- `~/.agents/genes/registry.jsonl`

`staging/` holds candidate genes pending manual review.
`confirmed/` holds approved genes used by default search.

## Gene ID Rules

Use lowercase, human-readable slugs.

- Pattern: `^[a-z][a-z0-9]*(?:-[a-z0-9]+)*(?:\.[a-z][a-z0-9]*(?:-[a-z0-9]+)*)*$`
- Recommended form: `domain.action` or `domain.action.variant`
- Examples:
  - `data.upsert`
  - `dedupe.cosine-batch`
  - `http.retry.exponential-backoff`

### Collision Strategy

If an ID already exists, append a numeric suffix using double dash:

- `dedupe.cosine-batch`
- `dedupe.cosine-batch--2`
- `dedupe.cosine-batch--3`

### Immutability and Renames

- IDs are stable once created.
- Prefer creating a new gene for materially different patterns.
- If rename is unavoidable, keep old ID as an alias in registry via `aliases`.

## Per-Gene Folder Layout

Each gene is one folder named exactly by gene ID.

```
~/.agents/genes/{staging|confirmed}/<gene-id>/
  gene.json
  notes.md
  snippets/
    python/
      ...
    typescript/
      ...
```

Required files:

- `gene.json` (machine metadata + embeddings)
- `notes.md` (pattern at top, then tradeoffs/pitfalls/adaptation notes)
- `snippets/<lang>/...` (source-backed exemplars)

Portability rule:

- Keep gene artifacts agnostic to original repositories.
- Avoid hard dependencies on source file paths and line numbers inside stored genes.
- Store reusable semantics and code, not brittle origin coordinates.

## `gene.json` Schema (authoritative)

```json
{
  "id": "dedupe.cosine-batch",
  "title": "Batch cosine deduplication with local embeddings",
  "summary": "Compare a batch against history and in-batch accepted items.",
  "tags": ["dedup", "embedding", "cosine"],
  "languages": ["python"],
  "status": "confirmed",
  "created_at": "2026-02-08T00:00:00Z",
  "updated_at": "2026-02-08T00:00:00Z",
  "aliases": [],
  "provenance": [
    {
      "origin_note": "Extracted from a local Python deduplication implementation",
      "symbols": ["DeduplicationEngine.check_batch"],
      "search_terms": ["cosine similarity", "deduplication"],
      "captured_at": "2026-02-08T00:00:00Z"
    }
  ],
  "embedding": {
    "model": "all-MiniLM-L6-v2",
    "dimension": 384,
    "metric": "cosine",
    "text": "dedupe.cosine-batch Batch cosine deduplication ...",
    "vector": [0.12, -0.02, 0.44]
  }
}
```

Embedding storage decision:

- Store full embedding vector in each `gene.json` to keep each gene self-contained.
- Keep registry entries compact, with selected metadata and a pointer to `gene.json`.

## Registry Format (`registry.jsonl`)

One JSON object per line.

Required fields per record:

```json
{
  "id": "dedupe.cosine-batch",
  "title": "Batch cosine deduplication with local embeddings",
  "summary": "Compare a batch against history and in-batch accepted items.",
  "tags": ["dedup", "embedding", "cosine"],
  "languages": ["python"],
  "status": "confirmed",
  "aliases": [],
  "gene_path": "/home/thomas/.agents/genes/confirmed/dedupe.cosine-batch",
  "gene_json_path": "/home/thomas/.agents/genes/confirmed/dedupe.cosine-batch/gene.json",
  "notes_path": "/home/thomas/.agents/genes/confirmed/dedupe.cosine-batch/notes.md",
  "embedding": {
    "model": "all-MiniLM-L6-v2",
    "dimension": 384,
    "metric": "cosine",
    "vector": [0.12, -0.02, 0.44]
  },
  "provenance_count": 1,
  "updated_at": "2026-02-08T00:00:00Z"
}
```

Registry conventions:

- Keep human-readable JSONL (no binary blobs).
- Rebuild deterministically from gene folders.
- Prefer `confirmed` records; include `staging` only when requested.
- Use `id` as primary key.

## Runtime Drift Notes

When a confirmed gene fails during use:

- Immediately report failure and probable cause to the user.
- Propose concrete fixes to snippets, explanation text, and metadata.
- Append a concise "Post-Use Notes" entry in `notes.md` describing the observed issue and suggested remediation.
- Use `scripts/append_gene_note.py` for consistent issue-note formatting.

## Retrieval Modes

- Embedding mode: `scripts/search_genes.py` for semantic similarity.
- BM25 mode: `scripts/search_genes_bm25.py` for fast lexical lookup.

Keep both available in v1 so operators can choose based on query style and latency constraints.
