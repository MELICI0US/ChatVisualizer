from __future__ import annotations

import argparse
from pathlib import Path

from chat_parser import load_common_reasons, load_reasons, save_common_reasons


def collect_reasons(annotation_paths: list[Path]) -> list[str]:
    reasons: list[str] = []
    seen: set[str] = set()
    for annotation_path in annotation_paths:
        for reason in load_reasons(annotation_path).values():
            reason = reason.strip()
            if reason and reason not in seen:
                seen.add(reason)
                reasons.append(reason)
    return reasons


def main() -> None:
    parser = argparse.ArgumentParser(description="Update common creation and stopped-use reasons.")
    parser.add_argument(
        "directory",
        nargs="?",
        type=Path,
        default=Path("."),
        help="Directory to scan recursively for *.reasons.json files (default: current directory)",
    )
    parser.add_argument(
        "--common-reasons",
        type=Path,
        default=Path(__file__).with_name("common_reasons.json"),
        help="Common reasons JSON file to update",
    )
    parser.add_argument(
        "--common-stopped-reasons",
        type=Path,
        default=Path(__file__).with_name("common_stopped_reasons.json"),
        help="Common stopped-use reasons JSON file to update",
    )
    args = parser.parse_args()

    annotation_paths = sorted(
        path
        for path in args.directory.rglob("*.reasons.json")
        if not path.name.endswith(".stopped_reasons.json")
        and path.resolve() != args.common_reasons.resolve()
        and path.resolve() != args.common_stopped_reasons.resolve()
    )
    stopped_annotation_paths = sorted(
        path
        for path in args.directory.rglob("*.stopped_reasons.json")
        if path.resolve() != args.common_reasons.resolve()
        and path.resolve() != args.common_stopped_reasons.resolve()
    )
    existing = load_common_reasons(args.common_reasons)
    merged = existing + [
        reason
        for reason in collect_reasons(annotation_paths)
        if reason not in existing
    ]
    save_common_reasons(args.common_reasons, merged)
    existing_stopped = load_common_reasons(args.common_stopped_reasons)
    merged_stopped = existing_stopped + [
        reason
        for reason in collect_reasons(stopped_annotation_paths)
        if reason not in existing_stopped
    ]
    save_common_reasons(args.common_stopped_reasons, merged_stopped)
    print(
        f"Scanned {len(annotation_paths)} creation and "
        f"{len(stopped_annotation_paths)} stopped-use annotation file(s); "
        f"common reasons: {len(merged)}, stopped-use reasons: {len(merged_stopped)}"
    )


if __name__ == "__main__":
    main()
