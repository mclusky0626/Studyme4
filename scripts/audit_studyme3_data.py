#!/usr/bin/env python3
"""Read-only Studyme3 data audit. It never prints memory text or secrets."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path


def relation_stats(path: Path) -> dict:
    if not path.exists():
        return {"available": False, "rows": 0, "distinct_users": 0}
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        rows = connection.execute("SELECT COUNT(*) FROM relations").fetchone()[0]
        users = connection.execute(
            "SELECT COUNT(DISTINCT user_id) FROM ("
            "SELECT user_a_id AS user_id FROM relations UNION SELECT user_b_id FROM relations)"
        ).fetchone()[0]
        return {"available": True, "rows": rows, "distinct_users": users}
    finally:
        connection.close()


def chroma_stats(path: Path) -> dict:
    if not path.exists():
        return {"available": False, "rows": 0, "missing_scope_rows": 0}
    try:
        import chromadb
    except ImportError:
        return {
            "available": True,
            "error": "Install chromadb in a separate migration environment to inspect rows",
        }
    collection = chromadb.PersistentClient(path=str(path)).get_or_create_collection("memories")
    count = collection.count()
    return {"available": True, "rows": count, "missing_scope_rows": count}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("data_dir", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    data_dir = args.data_dir.expanduser().resolve()
    report = {
        "source": str(data_dir),
        "read_only": True,
        "chroma": chroma_stats(data_dir / "chroma"),
        "relations": relation_stats(data_dir / "relations.db"),
        "policy": (
            "All legacy memories lack trustworthy scope and must enter user_private quarantine"
        ),
    }
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)


if __name__ == "__main__":
    main()
