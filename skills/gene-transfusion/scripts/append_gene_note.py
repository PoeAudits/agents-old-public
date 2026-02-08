#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

GENES_ROOT_DEFAULT = Path.home() / ".agents" / "genes"
REGISTRY_PATH_DEFAULT = GENES_ROOT_DEFAULT / "registry.jsonl"

ALLOWED_CATEGORIES = {
    "confusing",
    "contradiction",
    "unexpected-edge-case",
    "runtime-failure",
    "dependency-drift",
    "impediment",
    "other",
}


def main() -> int:
    args = parse_args()
    if args.category not in ALLOWED_CATEGORIES:
        print(f"Invalid category: {args.category}")
        print(f"Allowed categories: {', '.join(sorted(ALLOWED_CATEGORIES))}")
        return 1

    notes_path = resolve_notes_path(
        registry_path=args.registry_path,
        gene_id=args.gene_id,
        status=args.status,
    )
    if notes_path is None:
        print(f"Unable to find notes.md for gene id: {args.gene_id}")
        return 1

    entry = build_entry(
        category=args.category,
        note=args.note,
        command_context=args.command_context,
    )

    content = (
        notes_path.read_text(encoding="utf-8") if notes_path.exists() else "# Notes\n"
    )
    updated = append_post_use_note(content, entry)

    if args.dry_run:
        print(updated)
        return 0

    notes_path.write_text(updated, encoding="utf-8")
    print(f"Appended post-use note to {notes_path}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Append a significant post-use issue note to a gene notes.md. "
            "Use only for confusing/contradictory/unexpected behavior that impedes implementation."
        )
    )
    parser.add_argument("--gene-id", required=True, help="Gene id to update")
    parser.add_argument(
        "--note",
        required=True,
        help="Issue note to append (significant impediments only)",
    )
    parser.add_argument(
        "--category",
        default="impediment",
        help=(
            "Issue category: confusing, contradiction, unexpected-edge-case, runtime-failure, "
            "dependency-drift, impediment, other"
        ),
    )
    parser.add_argument(
        "--command-context",
        default="",
        help="Optional command or context where the issue occurred",
    )
    parser.add_argument(
        "--status",
        default="any",
        choices=["any", "staging", "confirmed"],
        help="Restrict lookup status",
    )
    parser.add_argument(
        "--registry-path",
        type=Path,
        default=REGISTRY_PATH_DEFAULT,
        help="Path to registry.jsonl",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print updated notes content without writing",
    )
    return parser.parse_args()


def resolve_notes_path(registry_path: Path, gene_id: str, status: str) -> Path | None:
    if not registry_path.exists():
        return None

    preferred_order = ["staging", "confirmed"] if status == "any" else [status]
    records = load_registry(registry_path)

    for target_status in preferred_order:
        for record in records:
            if str(record.get("id", "")).strip() != gene_id:
                continue
            if str(record.get("status", "")).strip() != target_status:
                continue
            notes_path_raw = record.get("notes_path")
            if isinstance(notes_path_raw, str) and notes_path_raw:
                return Path(notes_path_raw)
    return None


def load_registry(registry_path: Path) -> list[dict]:
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


def build_entry(category: str, note: str, command_context: str) -> str:
    timestamp = (
        datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )
    if command_context:
        return f"- {timestamp} [{category}] {note} (context: {command_context})"
    return f"- {timestamp} [{category}] {note}"


def append_post_use_note(content: str, entry: str) -> str:
    marker = "## Post-Use Notes"
    lines = content.splitlines()

    if marker not in lines:
        if lines and lines[-1].strip() != "":
            lines.append("")
        lines.append(marker)
        lines.append("")

    marker_index = lines.index(marker)
    insert_index = marker_index + 1
    while insert_index < len(lines) and lines[insert_index].strip() == "":
        insert_index += 1

    lines.insert(insert_index, entry)
    return "\n".join(lines).rstrip() + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
