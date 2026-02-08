#!/usr/bin/env python3

from __future__ import annotations

import argparse
import contextlib
import io
import json
import math
import re
import sys
from pathlib import Path

GENES_ROOT_DEFAULT = Path.home() / ".agents" / "genes"
REGISTRY_PATH_DEFAULT = GENES_ROOT_DEFAULT / "registry.jsonl"
UNIQUENESS_SRC_DEFAULT = (
    Path.home() / "Overlord" / "projects" / "libs" / "uniqueness" / "src"
)


def main() -> int:
    args = parse_args()
    records = load_registry(args.registry_path)
    if not records:
        print(f"No registry records found at {args.registry_path}", file=sys.stderr)
        return 1

    records_filtered = filter_records(records, args.include_staging)
    if not records_filtered:
        scope = "confirmed+staging" if args.include_staging else "confirmed"
        print(f"No {scope} records with usable metadata in registry", file=sys.stderr)
        return 1

    embedder = build_embedder(
        args.model,
        args.uniqueness_src,
        args.allow_fallback,
        suppress_logs=not args.show_model_logs,
    )
    if embedder is None:
        print("Unable to initialize local embedder", file=sys.stderr)
        return 2

    query_embedding_vector = embed_texts(
        embedder,
        [args.query],
        suppress_logs=not args.show_model_logs,
    )
    if len(query_embedding_vector) != 1:
        print("Failed to generate query embedding", file=sys.stderr)
        return 2
    query_embedding = query_embedding_vector[0]

    ranked = rank_records(query_embedding, records_filtered)
    if not ranked:
        print(
            "No records contained compatible embeddings (all skipped)", file=sys.stderr
        )
        return 1

    top_matches = ranked[: args.top_k]
    print_results(args.query, top_matches, as_json=args.json)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Search local genes using embedding similarity"
    )
    parser.add_argument(
        "--query", required=True, help="Natural-language query to search"
    )
    parser.add_argument(
        "--top-k", type=int, default=5, help="Maximum number of matches to print"
    )
    parser.add_argument(
        "--registry-path",
        type=Path,
        default=REGISTRY_PATH_DEFAULT,
        help="Path to registry.jsonl",
    )
    parser.add_argument(
        "--include-staging",
        action="store_true",
        help="Include staging genes in addition to confirmed",
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
    parser.add_argument(
        "--allow-fallback",
        action="store_true",
        help="Allow deterministic token-hash fallback when model load fails",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON output",
    )
    parser.add_argument(
        "--show-model-logs",
        action="store_true",
        help="Show sentence-transformer model load logs",
    )
    return parser.parse_args()


def load_registry(registry_path: Path) -> list[dict]:
    if not registry_path.exists():
        return []

    records: list[dict] = []
    with registry_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line_stripped = line.strip()
            if not line_stripped:
                continue
            try:
                parsed = json.loads(line_stripped)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                records.append(parsed)
    return records


def filter_records(records: list[dict], include_staging: bool) -> list[dict]:
    allowed_status = {"confirmed", "staging"} if include_staging else {"confirmed"}
    records_filtered: list[dict] = []
    for record in records:
        status = str(record.get("status", "")).strip().lower()
        if status not in allowed_status:
            continue
        if not str(record.get("id", "")).strip():
            continue
        records_filtered.append(record)
    return records_filtered


def build_embedder(
    model: str,
    uniqueness_src: Path,
    allow_fallback: bool,
    suppress_logs: bool,
):
    if str(uniqueness_src) not in sys.path:
        sys.path.insert(0, str(uniqueness_src))

    try:
        with suppress_output_context(enabled=suppress_logs):
            from uniqueness import SentenceTransformerEmbedder

            return SentenceTransformerEmbedder(model)
    except Exception as exc:
        print(f"Warning: local model unavailable: {exc}", file=sys.stderr)
        if allow_fallback:
            print("Warning: using token-hash fallback embeddings", file=sys.stderr)
            return HashingFallbackEmbedder()
        return None


def embed_texts(embedder, texts: list[str], suppress_logs: bool) -> list[list[float]]:
    with suppress_output_context(enabled=suppress_logs):
        return embedder.embed(texts)


@contextlib.contextmanager
def suppress_output_context(enabled: bool):
    if not enabled:
        yield
        return
    with (
        contextlib.redirect_stdout(io.StringIO()),
        contextlib.redirect_stderr(io.StringIO()),
    ):
        yield


class HashingFallbackEmbedder:
    def __init__(self, dimension: int = 384) -> None:
        self.dimension = dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            vector = [0.0] * self.dimension
            tokens = tokenize(text)
            for token in tokens:
                index = hash(token) % self.dimension
                vector[index] += 1.0
            vectors.append(normalize_vector(vector))
        return vectors


def rank_records(query_embedding: list[float], records: list[dict]) -> list[dict]:
    ranked: list[dict] = []
    for record in records:
        vector = record_embedding_vector(record)
        if vector is None:
            print(
                f"Warning: skipping {record.get('id')} (missing embedding)",
                file=sys.stderr,
            )
            continue
        if len(vector) != len(query_embedding):
            print(
                f"Warning: skipping {record.get('id')} (dimension mismatch)",
                file=sys.stderr,
            )
            continue

        score_value = cosine_similarity(query_embedding, vector)
        reason = build_reason(record)
        ranked.append(
            {
                "id": record.get("id"),
                "title": record.get("title", ""),
                "score": score_value,
                "location": record.get("gene_path") or record.get("gene_json_path"),
                "reason": reason,
                "status": record.get("status", "unknown"),
            }
        )

    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked


def extract_embedding_vector(embedding_info: object) -> list[float] | None:
    if not isinstance(embedding_info, dict):
        return None
    vector = embedding_info.get("vector")
    if not isinstance(vector, list):
        return None

    converted: list[float] = []
    for value in vector:
        if isinstance(value, int | float):
            converted.append(float(value))
        else:
            return None
    return converted if converted else None


def record_embedding_vector(record: dict) -> list[float] | None:
    vector = extract_embedding_vector(record.get("embedding"))
    if vector is not None:
        return vector

    gene_json_path_raw = record.get("gene_json_path")
    if not isinstance(gene_json_path_raw, str) or not gene_json_path_raw:
        return None

    gene_json_path = Path(gene_json_path_raw)
    if not gene_json_path.exists():
        return None

    try:
        gene_data = json.loads(gene_json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None

    if not isinstance(gene_data, dict):
        return None
    return extract_embedding_vector(gene_data.get("embedding"))


def build_reason(record: dict) -> str:
    tags = record.get("tags")
    languages = record.get("languages")
    tags_text = ",".join(tags[:3]) if isinstance(tags, list) else ""
    languages_text = ",".join(languages[:2]) if isinstance(languages, list) else ""
    reason_parts = [part for part in [tags_text, languages_text] if part]
    return " | ".join(reason_parts) if reason_parts else "embedding similarity"


def cosine_similarity(vector_a: list[float], vector_b: list[float]) -> float:
    dot_value = sum(a * b for a, b in zip(vector_a, vector_b))
    norm_a = math.sqrt(sum(a * a for a in vector_a))
    norm_b = math.sqrt(sum(b * b for b in vector_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot_value / (norm_a * norm_b)


def tokenize(text: str) -> list[str]:
    return [token for token in re.split(r"[^a-z0-9]+", text.lower()) if token]


def normalize_vector(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0.0:
        return vector
    return [value / norm for value in vector]


def print_results(query: str, matches: list[dict], as_json: bool) -> None:
    if as_json:
        payload = {"query": query, "match_count": len(matches), "matches": matches}
        print(json.dumps(payload, ensure_ascii=True))
        return

    print(f"Query: {query}")
    print(f"Matches: {len(matches)}")
    for index, match in enumerate(matches, start=1):
        score = f"{match['score']:.4f}"
        print(
            f"{index}. {match['id']} | {match['title']} | score={score} | "
            f"status={match['status']} | location={match['location']} | reason={match['reason']}"
        )


if __name__ == "__main__":
    raise SystemExit(main())
