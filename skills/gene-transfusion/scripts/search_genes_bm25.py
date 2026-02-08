#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

GENES_ROOT_DEFAULT = Path.home() / ".agents" / "genes"
REGISTRY_PATH_DEFAULT = GENES_ROOT_DEFAULT / "registry.jsonl"


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

    index = BM25Index.build(records_filtered, include_notes=not args.no_notes)
    query_tokens = tokenize(args.query)
    if not query_tokens:
        print("Query contains no searchable terms", file=sys.stderr)
        return 1

    ranked = index.search(query_tokens, top_k=args.top_k)
    if not ranked:
        print("No BM25 matches", file=sys.stderr)
        return 1

    if args.json:
        payload = {
            "query": args.query,
            "engine": "bm25",
            "match_count": len(ranked),
            "matches": ranked,
        }
        print(json.dumps(payload, ensure_ascii=True))
        return 0

    print(f"Query: {args.query}")
    print("Engine: bm25")
    print(f"Matches: {len(ranked)}")
    for index_value, match in enumerate(ranked, start=1):
        score_text = f"{match['score']:.4f}"
        print(
            f"{index_value}. {match['id']} | {match['title']} | score={score_text} | "
            f"status={match['status']} | location={match['location']} | reason={match['reason']}"
        )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Search local genes using BM25 lexical ranking"
    )
    parser.add_argument("--query", required=True, help="Keyword query to search")
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
        "--no-notes",
        action="store_true",
        help="Exclude notes.md text from the lexical corpus",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON output",
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


def tokenize(text: str) -> list[str]:
    return [token for token in re.split(r"[^a-z0-9]+", text.lower()) if token]


class BM25Index:
    def __init__(
        self,
        docs: list[dict],
        term_freqs: list[Counter],
        doc_freqs: dict[str, int],
        avg_doc_len: float,
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        self.docs = docs
        self.term_freqs = term_freqs
        self.doc_freqs = doc_freqs
        self.avg_doc_len = avg_doc_len if avg_doc_len > 0.0 else 1.0
        self.k1 = k1
        self.b = b
        self.doc_count = len(docs)

    @classmethod
    def build(cls, records: list[dict], include_notes: bool) -> "BM25Index":
        docs: list[dict] = []
        term_freqs: list[Counter] = []
        doc_freqs_counter: Counter = Counter()

        for record in records:
            corpus_text = build_corpus_text(record, include_notes=include_notes)
            tokens = tokenize(corpus_text)
            if not tokens:
                continue
            token_counts = Counter(tokens)
            docs.append(record)
            term_freqs.append(token_counts)
            doc_freqs_counter.update(token_counts.keys())

        avg_doc_len = (
            sum(sum(counter.values()) for counter in term_freqs) / len(term_freqs)
            if term_freqs
            else 1.0
        )
        return cls(
            docs=docs,
            term_freqs=term_freqs,
            doc_freqs=dict(doc_freqs_counter),
            avg_doc_len=avg_doc_len,
        )

    def search(self, query_tokens: list[str], top_k: int) -> list[dict]:
        if self.doc_count == 0:
            return []

        query_counts = Counter(query_tokens)
        scored: list[tuple[float, int, list[str]]] = []

        for doc_index, term_counts in enumerate(self.term_freqs):
            score = 0.0
            matched_terms: list[str] = []
            doc_len = sum(term_counts.values())

            for term, query_weight in query_counts.items():
                tf = term_counts.get(term, 0)
                if tf <= 0:
                    continue
                matched_terms.append(term)
                idf = self._idf(term)
                denominator = tf + self.k1 * (
                    1.0 - self.b + self.b * (doc_len / self.avg_doc_len)
                )
                term_score = idf * ((tf * (self.k1 + 1.0)) / denominator)
                score += term_score * query_weight

            if score > 0.0:
                scored.append((score, doc_index, matched_terms))

        scored.sort(key=lambda item: item[0], reverse=True)
        top = scored[:top_k]

        results: list[dict] = []
        for score, doc_index, matched_terms in top:
            record = self.docs[doc_index]
            results.append(
                {
                    "id": record.get("id"),
                    "title": record.get("title", ""),
                    "score": score,
                    "location": record.get("gene_path") or record.get("gene_json_path"),
                    "reason": build_reason(record, matched_terms),
                    "status": record.get("status", "unknown"),
                }
            )
        return results

    def _idf(self, term: str) -> float:
        df = self.doc_freqs.get(term, 0)
        numerator = self.doc_count - df + 0.5
        denominator = df + 0.5
        return math.log(1.0 + (numerator / denominator))


def build_corpus_text(record: dict, include_notes: bool) -> str:
    parts: list[str] = [
        str(record.get("id", "")),
        str(record.get("title", "")),
        str(record.get("summary", "")),
    ]

    tags = record.get("tags")
    if isinstance(tags, list):
        parts.extend(str(tag) for tag in tags)

    languages = record.get("languages")
    if isinstance(languages, list):
        parts.extend(str(language) for language in languages)

    if include_notes:
        notes_path_raw = record.get("notes_path")
        if isinstance(notes_path_raw, str) and notes_path_raw:
            notes_path = Path(notes_path_raw)
            if notes_path.exists():
                try:
                    parts.append(notes_path.read_text(encoding="utf-8"))
                except OSError:
                    pass

    return "\n".join(parts)


def build_reason(record: dict, matched_terms: list[str]) -> str:
    tags = record.get("tags")
    tags_text = ",".join(tags[:3]) if isinstance(tags, list) else ""
    overlap = ",".join(matched_terms[:5]) if matched_terms else ""
    reason_parts = [
        part for part in [tags_text, f"terms:{overlap}" if overlap else ""] if part
    ]
    return " | ".join(reason_parts) if reason_parts else "lexical overlap"


if __name__ == "__main__":
    raise SystemExit(main())
