#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

GENES_ROOT_DEFAULT = Path.home() / ".agents" / "genes"
REGISTRY_PATH_DEFAULT = GENES_ROOT_DEFAULT / "registry.jsonl"


@dataclass
class RegistryBuildStats:
    records_written: int = 0
    genes_skipped: int = 0


def main() -> int:
    args = parse_args()
    statuses = ["confirmed", "staging"] if args.include_staging else ["confirmed"]

    records: list[dict] = []
    stats = RegistryBuildStats()
    for status in statuses:
        records_status, skipped_count = collect_records(args.genes_root, status)
        records.extend(records_status)
        stats.genes_skipped += skipped_count

    records.sort(
        key=lambda item: (str(item.get("status", "")), str(item.get("id", "")))
    )
    write_registry(args.registry_path, records)
    stats.records_written = len(records)

    print(f"Registry written: {args.registry_path}")
    print(f"Records written: {stats.records_written}")
    print(f"Genes skipped: {stats.genes_skipped}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rebuild local gene registry from gene folders"
    )
    parser.add_argument(
        "--genes-root",
        type=Path,
        default=GENES_ROOT_DEFAULT,
        help="Root directory containing staging/ and confirmed/",
    )
    parser.add_argument(
        "--registry-path",
        type=Path,
        default=REGISTRY_PATH_DEFAULT,
        help="Output JSONL registry path",
    )
    parser.add_argument(
        "--include-staging",
        action="store_true",
        help="Include staging genes in registry",
    )
    return parser.parse_args()


def collect_records(genes_root: Path, status: str) -> tuple[list[dict], int]:
    base_path = genes_root / status
    if not base_path.exists():
        return [], 0

    records: list[dict] = []
    genes_skipped = 0
    for gene_path in sorted(path for path in base_path.iterdir() if path.is_dir()):
        record = build_record(gene_path, status)
        if record is None:
            genes_skipped += 1
            continue
        records.append(record)
    return records, genes_skipped


def build_record(gene_path: Path, status: str) -> dict | None:
    gene_json_path = gene_path / "gene.json"
    notes_path = gene_path / "notes.md"

    if not gene_json_path.exists() or not notes_path.exists():
        return None

    try:
        gene_data = json.loads(gene_json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None

    gene_id = str(gene_data.get("id", "")).strip()
    if not gene_id:
        return None

    embedding = gene_data.get("embedding")
    embedding_clean = clean_embedding(embedding)

    record = {
        "id": gene_id,
        "title": gene_data.get("title", ""),
        "summary": gene_data.get("summary", ""),
        "tags": gene_data.get("tags", []),
        "languages": gene_data.get("languages", []),
        "status": status,
        "aliases": gene_data.get("aliases", []),
        "gene_path": str(gene_path),
        "gene_json_path": str(gene_json_path),
        "notes_path": str(notes_path),
        "embedding": embedding_clean,
        "provenance_count": len(gene_data.get("provenance", []))
        if isinstance(gene_data.get("provenance"), list)
        else 0,
        "updated_at": gene_data.get("updated_at", ""),
    }
    return record


def clean_embedding(embedding: object) -> dict:
    if not isinstance(embedding, dict):
        return {}

    vector_raw = embedding.get("vector")
    if not isinstance(vector_raw, list):
        return {}

    vector_clean: list[float] = []
    for value in vector_raw:
        if isinstance(value, int | float):
            vector_clean.append(float(value))
        else:
            return {}

    return {
        "model": str(embedding.get("model", "")),
        "dimension": int(embedding.get("dimension", len(vector_clean))),
        "metric": str(embedding.get("metric", "cosine")),
        "vector": vector_clean,
    }


def write_registry(registry_path: Path, records: list[dict]) -> None:
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    with registry_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=True) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
