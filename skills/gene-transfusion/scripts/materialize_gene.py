#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, datetime
from pathlib import Path

GENES_ROOT_DEFAULT = Path.home() / ".agents" / "genes"
UNIQUENESS_SRC_DEFAULT = (
    Path.home() / "Overlord" / "projects" / "libs" / "uniqueness" / "src"
)


def main() -> int:
    args = parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    result = payload.get("result", {})

    if result.get("status") != "found":
        print("Input status is not 'found'; nothing materialized")
        return 1

    candidate = result.get("gene_candidate", {})
    proposed_id = str(candidate.get("proposed_id", "")).strip()
    gene_id = allocate_gene_id(args.genes_root / "staging", proposed_id)
    gene_path = args.genes_root / "staging" / gene_id

    gene_path.mkdir(parents=True, exist_ok=False)
    (gene_path / "snippets").mkdir(parents=True, exist_ok=True)

    timestamp = timestamp_iso()
    embedding = {}
    if args.with_embedding:
        embedding = build_embedding(candidate, args.model, args.uniqueness_src)

    gene_json = {
        "id": gene_id,
        "title": candidate.get("title", ""),
        "summary": candidate.get("summary", ""),
        "tags": candidate.get("tags", []),
        "languages": candidate.get("languages", []),
        "status": "staging",
        "created_at": timestamp,
        "updated_at": timestamp,
        "aliases": [],
        "provenance": sanitize_provenance(candidate.get("provenance", [])),
        "embedding": embedding,
    }

    (gene_path / "gene.json").write_text(
        json.dumps(gene_json, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )
    (gene_path / "notes.md").write_text(
        build_notes_markdown(result, candidate), encoding="utf-8"
    )
    write_snippets(gene_path, candidate)

    print(f"Materialized staged gene: {gene_path}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Materialize gene folder from gene-scout JSON output"
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to strict gene-scout JSON output",
    )
    parser.add_argument(
        "--genes-root",
        type=Path,
        default=GENES_ROOT_DEFAULT,
        help="Root directory containing staging/ and confirmed/",
    )
    parser.add_argument(
        "--with-embedding",
        action="store_true",
        help="Compute and store embedding in gene.json",
    )
    parser.add_argument(
        "--model",
        default="all-MiniLM-L6-v2",
        help="Sentence-transformers model name",
    )
    parser.add_argument(
        "--uniqueness-src",
        type=Path,
        default=UNIQUENESS_SRC_DEFAULT,
        help="Path to uniqueness/src for local embedder import",
    )
    return parser.parse_args()


def allocate_gene_id(staging_root: Path, proposed_id: str) -> str:
    base_id = sanitize_gene_id(proposed_id)
    candidate_id = base_id
    index = 2
    while (staging_root / candidate_id).exists():
        candidate_id = f"{base_id}--{index}"
        index += 1
    return candidate_id


def sanitize_gene_id(value: str) -> str:
    value_clean = value.strip().lower()
    if not value_clean:
        return "gene.untitled"

    value_clean = re.sub(r"[^a-z0-9.-]+", "-", value_clean)
    value_clean = re.sub(r"-{2,}", "-", value_clean)
    value_clean = value_clean.strip("-.")

    if "." not in value_clean:
        value_clean = f"gene.{value_clean}"
    if not re.match(
        r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*(?:\.[a-z][a-z0-9]*(?:-[a-z0-9]+)*)*$",
        value_clean,
    ):
        return "gene.untitled"
    return value_clean


def build_embedding(candidate: dict, model: str, uniqueness_src: Path) -> dict:
    import sys

    if str(uniqueness_src) not in sys.path:
        sys.path.insert(0, str(uniqueness_src))

    from uniqueness import SentenceTransformerEmbedder

    embedding_text = build_embedding_text(candidate)
    embedder = SentenceTransformerEmbedder(model)
    vector_wrapped = embedder.embed([embedding_text])
    vector = vector_wrapped[0] if vector_wrapped else []
    return {
        "model": model,
        "dimension": len(vector),
        "metric": "cosine",
        "text": embedding_text,
        "vector": vector,
    }


def build_embedding_text(candidate: dict) -> str:
    parts = [
        str(candidate.get("proposed_id", "")),
        str(candidate.get("title", "")),
        str(candidate.get("summary", "")),
    ]
    tags = candidate.get("tags")
    if isinstance(tags, list):
        parts.extend(str(tag) for tag in tags)
    return " ".join(part for part in parts if part).strip()


def build_pattern_markdown(candidate: dict) -> list[str]:
    pattern_lines = ["## Pattern", ""]
    steps = candidate.get("pattern_spec", [])
    if isinstance(steps, list) and steps:
        for index, step in enumerate(steps, start=1):
            pattern_lines.append(f"{index}. {step}")
    else:
        pattern_lines.append("1. No pattern steps were provided.")
    return pattern_lines


def build_notes_markdown(result: dict, candidate: dict) -> str:
    confidence = result.get("confidence", "")
    invariants = candidate.get("invariants", [])
    edge_cases = candidate.get("edge_cases", [])
    pitfalls = candidate.get("pitfalls", [])
    gaps = candidate.get("gaps", [])

    lines = [
        "# Notes",
        "",
        f"- Confidence: {confidence}",
        f"- Generated: {timestamp_iso()}",
        "",
    ]
    lines.extend(build_pattern_markdown(candidate))
    lines.append("")
    lines.append("## Invariants")
    lines.extend(format_list(invariants))
    lines.append("")
    lines.append("## Edge Cases")
    lines.extend(format_list(edge_cases))
    lines.append("")
    lines.append("## Pitfalls")
    lines.extend(format_list(pitfalls))
    lines.append("")
    lines.append("## Gaps")
    lines.extend(format_list(gaps))
    lines.append("")
    lines.append("## Post-Use Notes")
    lines.append("- Add runtime surprises, breakages, or confusing behavior here.")
    lines.append("- If package/API drift breaks snippets, record the fix guidance.")
    lines.append("")
    return "\n".join(lines)


def format_list(values: object) -> list[str]:
    if not isinstance(values, list) or not values:
        return ["- (none)"]
    return [f"- {value}" for value in values]


def write_snippets(gene_path: Path, candidate: dict) -> None:
    snippets_by_language = candidate.get("snippets_by_language", {})
    if not isinstance(snippets_by_language, dict):
        return

    for language, snippets in snippets_by_language.items():
        language_dir = gene_path / "snippets" / str(language).lower()
        language_dir.mkdir(parents=True, exist_ok=True)
        if not isinstance(snippets, list):
            continue
        for index, snippet in enumerate(snippets, start=1):
            if not isinstance(snippet, dict):
                continue
            symbol = str(snippet.get("symbol", f"snippet-{index}"))
            symbol_clean = re.sub(r"[^a-zA-Z0-9._-]+", "-", symbol).strip("-")
            file_name = f"{index:02d}-{symbol_clean or 'snippet'}.md"
            file_path = language_dir / file_name
            code_block = str(snippet.get("code", "")).strip()
            body = [
                f"# {symbol}",
                "",
                f"- Source Note: {snippet.get('source_note', '')}",
                f"- Why Relevant: {snippet.get('why_relevant', '')}",
                "",
                "```",
                code_block,
                "```",
                "",
            ]
            file_path.write_text("\n".join(body), encoding="utf-8")


def sanitize_provenance(provenance_raw: object) -> list[dict]:
    if not isinstance(provenance_raw, list):
        return []

    provenance_clean: list[dict] = []
    for item in provenance_raw:
        if not isinstance(item, dict):
            continue
        origin_note = str(item.get("origin_note", "")).strip()
        if not origin_note:
            origin_note = "Extracted from local source analysis"
        symbols = item.get("symbols", [])
        search_terms = item.get("search_terms", [])
        provenance_clean.append(
            {
                "origin_note": origin_note,
                "symbols": symbols if isinstance(symbols, list) else [],
                "search_terms": search_terms if isinstance(search_terms, list) else [],
                "captured_at": timestamp_iso(),
            }
        )
    return provenance_clean


def timestamp_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
