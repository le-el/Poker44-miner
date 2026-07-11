#!/usr/bin/env python3
"""Download public Poker44 training-benchmark releases into hands_generator/.

Follows the workflow documented in docs/training-benchmark.md: fetch status,
paginate /benchmark/chunks per sourceDate, and save one file per date in the
same schema training/build_dataset.py already loads (so no downstream code
changes are needed).

Usage:
    python -m scripts.fetch_benchmark_data --new              # fetch every date newer than the newest local file
    python -m scripts.fetch_benchmark_data --dates 2026-07-10,2026-07-11
    python -m scripts.fetch_benchmark_data --latest            # just today's latestSourceDate
    python -m scripts.fetch_benchmark_data --new --force       # re-download and overwrite even if the file exists
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import requests

API_BASE = "https://api.poker44.net/api/v1/benchmark"
REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = REPO_ROOT / "hands_generator" / "evaluation_datas"
MAX_LIMIT = 48  # server-enforced ceiling ("limit: Too big: expected <= 48")


def _get(path: str, **params: Any) -> dict:
    resp = requests.get(f"{API_BASE}{path}", params=params, timeout=30)
    resp.raise_for_status()
    payload = resp.json()
    if not payload.get("success", True):
        raise RuntimeError(f"API error for {path} {params}: {payload.get('error')}")
    return payload["data"]


def fetch_status() -> dict:
    return _get("")


def fetch_releases(limit: int = 60) -> list[dict]:
    return _get("/releases", limit=limit).get("releases", [])


def fetch_date(source_date: str, *, limit: int = MAX_LIMIT, sleep: float = 0.1) -> dict:
    """Paginate every chunk group for one sourceDate into one merged payload."""
    cursor = None
    groups: list[dict] = []
    meta: dict = {}
    while True:
        params = {"sourceDate": source_date, "limit": limit}
        if cursor:
            params["cursor"] = cursor
        data = _get("/chunks", **params)
        if not meta:
            meta = {k: v for k, v in data.items() if k not in ("chunks", "nextCursor")}
        groups.extend(data.get("chunks", []))
        cursor = data.get("nextCursor")
        if not cursor:
            break
        time.sleep(sleep)
    return {**meta, "chunks": groups}


def local_dates() -> set[str]:
    dates = set()
    for path in OUTPUT_DIR.glob("training_benchmark_????-??-??.txt"):
        dates.add(path.stem.rsplit("_", 1)[-1])
    return dates


def save_date(source_date: str, payload: dict, *, force: bool) -> Path:
    out_path = OUTPUT_DIR / f"training_benchmark_{source_date}.txt"
    if out_path.exists() and not force:
        raise FileExistsError(f"{out_path} exists (pass --force to overwrite)")
    out_path.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dates", type=str, default="", help="comma-separated YYYY-MM-DD list")
    parser.add_argument("--new", action="store_true", help="fetch every release date newer than the newest local file")
    parser.add_argument("--latest", action="store_true", help="fetch only today's latestSourceDate")
    parser.add_argument("--force", action="store_true", help="overwrite existing local files")
    args = parser.parse_args()

    if sum([bool(args.dates), args.new, args.latest]) != 1:
        parser.error("pass exactly one of --dates, --new, --latest")

    status = fetch_status()
    print(
        f"status: releaseVersion={status['releaseVersion']} "
        f"latestSourceDate={status['latestSourceDate']} "
        f"totalChunks={status['totalChunks']}"
    )

    if args.latest:
        target_dates = [status["latestSourceDate"]]
    elif args.dates:
        target_dates = [d.strip() for d in args.dates.split(",") if d.strip()]
    else:
        have = local_dates()
        newest_local = max(have) if have else "0000-00-00"
        releases = fetch_releases()
        target_dates = sorted(
            {
                r["sourceDate"]
                for r in releases
                if r["sourceDate"] > newest_local
            }
        )
        if not target_dates:
            print(f"nothing newer than local newest date {newest_local}; up to date.")
            return
        print(f"newest local date: {newest_local} -> fetching: {target_dates}")

    for source_date in target_dates:
        try:
            payload = fetch_date(source_date)
        except Exception as exc:
            print(f"  {source_date}: FAILED ({exc})", file=sys.stderr)
            continue
        n_groups = len(payload["chunks"])
        n_hands = sum(g.get("handCount", 0) for g in payload["chunks"])
        if n_groups == 0:
            print(f"  {source_date}: no chunk groups published yet, skipping")
            continue
        try:
            out_path = save_date(source_date, payload, force=args.force)
        except FileExistsError as exc:
            print(f"  {source_date}: SKIPPED ({exc})")
            continue
        print(f"  {source_date}: saved {n_groups} groups / {n_hands} hands -> {out_path}")


if __name__ == "__main__":
    main()
