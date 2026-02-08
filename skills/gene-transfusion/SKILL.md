---
name: gene-transfusion
description: This skill should be used when the user asks to "extract reusable patterns from local repos", "create a gene from code", "search genes by description", "run gene scout", or "reuse an implementation pattern in another language".
version: 0.1.0
---

# Gene Transfusion

Capture reusable implementation patterns ("genes") from local repositories, store them in a local gene library, and retrieve them with local embedding similarity search.

Use two retrieval paths:
- Embedding search for semantic matching (`search_genes.py`)
- BM25 lexical search for fast keyword matching (`search_genes_bm25.py`)

## When to Use

Use this skill when:
- A pattern should be reused across projects or languages
- The user asks to preserve an implementation approach with provenance
- A natural-language query should find prior implementation artifacts

## Scope

- Extract candidate genes using `@gene-scout` (read-only)
- Orchestrate multi-scout extraction with `@gene-orchestrator`
- Stage artifacts in `~/.agents/genes/staging/`
- Promote vetted genes to `~/.agents/genes/confirmed/` (manual v1)
- Rebuild registry metadata used by search
- Search confirmed genes (default) with local embeddings

## Fast Workflow

1. Use `@gene-orchestrator` for end-to-end coordination (recommended), or run `@gene-scout` directly.
2. Run parallel `@gene-scout` investigations (2-6 based on project scope).
3. Synthesize results in an analysis document and decide which candidates to keep.
4. Materialize approved JSON output into staged gene folders.
5. Review and edit `notes.md` as needed (pattern section is at the top).
6. Promote selected genes from `staging/` to `confirmed/`.
7. Rebuild registry.
8. Search by natural-language description.

## Commands

Use the scripts in `scripts/`.

Rebuild registry from confirmed genes:

```bash
python ~/.agents/skills/gene-transfusion/scripts/rebuild_registry.py
```

Include staging in registry rebuild:

```bash
python ~/.agents/skills/gene-transfusion/scripts/rebuild_registry.py --include-staging
```

Search genes by description:

```bash
python ~/.agents/skills/gene-transfusion/scripts/search_genes.py \
  --query "idempotent upsert with conflict retry" \
  --json \
  --top-k 5
```

Search confirmed plus staging:

```bash
python ~/.agents/skills/gene-transfusion/scripts/search_genes.py \
  --query "batch deduplication with cosine similarity" \
  --include-staging \
  --json \
  --top-k 8
```

Search with BM25 (keywords, no embeddings):

```bash
python ~/.agents/skills/gene-transfusion/scripts/search_genes_bm25.py \
  --query "dedup cosine threshold batch" \
  --include-staging \
  --json \
  --top-k 8
```

Enable verbose model logs only when debugging:

```bash
python ~/.agents/skills/gene-transfusion/scripts/search_genes.py \
  --query "batch deduplication with cosine similarity" \
  --show-model-logs
```

Materialize one gene candidate from `gene-scout` JSON:

```bash
python ~/.agents/skills/gene-transfusion/scripts/materialize_gene.py \
  --input /tmp/gene-scout-output.json
```

Append a post-use issue note when the gene impeded implementation:

```bash
python ~/.agents/skills/gene-transfusion/scripts/append_gene_note.py \
  --gene-id dedupe.cosine-batch \
  --category confusing \
  --note "Threshold behavior was unclear for near-ties at 0.70"
```

## Agent Integration

- Use `@gene-orchestrator` to run multi-scout extraction, synthesis, and staging prep.
- Use `@gene-scout` for extraction only.
- Keep `@gene-scout` read-only; writing artifacts happens in parent/orchestrator flows.
- Require strict JSON output that matches `references/gene-scout-output-schema.json`.
- Keep extraction outputs reusable and portable; avoid path+line coupling in stored gene artifacts.

## Gene Store

Canonical store paths:
- `~/.agents/genes/staging/`
- `~/.agents/genes/confirmed/`
- `~/.agents/genes/registry.jsonl`

Default search behavior:
- Search `confirmed` only
- Include `staging` with `--include-staging`

## How to Load a Gene

1. Run search and pick a top match by score.
2. Open the reported `location` directory.
3. Read `notes.md` first; it starts with the language-agnostic pattern.
4. Read `snippets/<lang>/` for language-specific implementation details.
5. Use invariants, edge cases, pitfalls, and post-use notes to adapt safely.

Use `staging/` while iterating on candidate genes. Use `confirmed/` for production reuse.

## Failure Handling Expectations

- If a confirmed gene fails due to dependency deprecation or runtime/API drift, immediately tell the user.
- Suggest specific edits in three areas: code snippet, explanation (pattern/notes), and metadata.
- After use, append any surprising behavior, confusion, or runtime issue to `notes.md` under a post-use section.

Use `append_gene_note.py` only for significant impediments:
- Confusing or contradictory guidance
- Unexpected, undocumented edge cases
- Runtime failures or dependency/API drift that blocks progress

## Additional Resources

- `references/gene-store-spec.md` - Store layout, ID rules, embedding and registry schema
- `references/gene-scout-output-schema.json` - Strict JSON schema for extraction output
- `references/gene-scout-examples.md` - Canonical JSON examples and uncertainty handling
- `references/gene-analysis-template.md` - Standard synthesis template for `@gene-orchestrator` analysis docs
