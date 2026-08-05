import argparse
import json
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "src"
CONFIG_PATH = ROOT / "config" / "university-config.json"
PREVIEW_PATH = ROOT / "category-previews.json"

sys.path.insert(0, str(SRC_DIR))

from config_loader import load_category_config  # noqa: E402
from scraper import fetch_university_announcements  # noqa: E402


def load_preview_counts(path=PREVIEW_PATH):
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as input_file:
        previews = json.load(input_file)
    return {
        category_id: len(preview.get("announcements", []))
        for category_id, preview in previews.items()
    }


def group_categories(category_ids, categories):
    grouped = defaultdict(list)
    for category_id in category_ids:
        host = urlparse(categories[category_id].get("url", "")).netloc.lower()
        grouped[host].append(category_id)
    return list(grouped.values())


def validate_items(items):
    problems = []
    for index, item in enumerate(items, 1):
        if not str(item.get("title", "")).strip():
            problems.append(f"item {index}: missing title")
        if not str(item.get("url", "")).startswith(("http://", "https://")):
            problems.append(f"item {index}: invalid URL")
        if not str(item.get("date", "")).strip():
            problems.append(f"item {index}: missing date")
    return problems


def classify_status(items, problems, allow_empty):
    if problems:
        return "invalid"
    if items:
        return "ok"
    return "expected_empty" if allow_empty else "unexpected_empty"


def check_category(category_id, labels, categories, preview_counts):
    meta = categories[category_id]
    url = meta.get("url", "")
    started_at = perf_counter()
    try:
        items = fetch_university_announcements(
            url,
            labels.get(category_id, category_id),
            meta.get("selectors"),
        )
        problems = validate_items(items)
        status = classify_status(items, problems, meta.get("allowEmpty", False))
        sample = None
        if items:
            first = items[0]
            sample = {
                "title": first.get("title", ""),
                "url": first.get("url", ""),
                "date": first.get("date", ""),
            }
        error = "; ".join(problems)
    except Exception as exc:  # Keep checking other sources after one unexpected failure.
        items = []
        status = "error"
        sample = None
        error = f"{type(exc).__name__}: {exc}"

    return {
        "category_id": category_id,
        "label": labels.get(category_id, category_id),
        "domain": urlparse(url).netloc.lower(),
        "url": url,
        "parser": (meta.get("selectors") or {}).get("parser", "html_cards"),
        "status": status,
        "item_count": len(items),
        "previous_preview_count": preview_counts.get(category_id, 0),
        "elapsed_seconds": round(perf_counter() - started_at, 3),
        "error": error,
        "sample": sample,
    }


def check_group(category_ids, labels, categories, preview_counts):
    return [
        check_category(category_id, labels, categories, preview_counts)
        for category_id in category_ids
    ]


def parse_args():
    parser = argparse.ArgumentParser(description="Check configured announcement sources without DB writes.")
    parser.add_argument("--category-id", action="append", dest="category_ids")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--retry-empty", type=int, default=0)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def run_checks(category_ids, labels, categories, preview_counts, workers):
    results_by_id = {}
    groups = group_categories(category_ids, categories)
    completed = 0

    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = {
            executor.submit(check_group, group, labels, categories, preview_counts): group
            for group in groups
        }
        for future in as_completed(futures):
            for result in future.result():
                results_by_id[result["category_id"]] = result
                completed += 1
                if result["status"] != "ok":
                    print(
                        f"[{result['status'].upper()}] {result['label']} "
                        f"({result['category_id']}): {result['item_count']} items"
                    )
                elif completed % 25 == 0:
                    print(f"Checked {completed}/{len(category_ids)} categories...")

    return [results_by_id[category_id] for category_id in category_ids]


def main():
    args = parse_args()
    _, labels, categories = load_category_config(CONFIG_PATH)
    category_ids = args.category_ids or list(categories)
    unknown_ids = [category_id for category_id in category_ids if category_id not in categories]
    if unknown_ids:
        raise SystemExit(f"Unknown category IDs: {', '.join(unknown_ids)}")

    preview_counts = load_preview_counts()
    results = run_checks(category_ids, labels, categories, preview_counts, args.workers)

    for _ in range(max(0, args.retry_empty)):
        retry_ids = [
            result["category_id"]
            for result in results
            if result["status"] in {"expected_empty", "unexpected_empty"}
        ]
        if not retry_ids:
            break
        print(f"Retrying {len(retry_ids)} empty categories...")
        retry_results = run_checks(retry_ids, labels, categories, preview_counts, args.workers)
        retry_by_id = {result["category_id"]: result for result in retry_results}
        results = [retry_by_id.get(result["category_id"], result) for result in results]

    counts = defaultdict(int)
    for result in results:
        counts[result["status"]] += 1
    print(
        "Summary: "
        + ", ".join(
            f"{status}={counts[status]}"
            for status in ("ok", "expected_empty", "unexpected_empty", "invalid", "error")
        )
    )

    if args.output:
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": dict(counts),
            "results": results,
        }
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Report written to {args.output}")

    return 1 if counts["unexpected_empty"] or counts["invalid"] or counts["error"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
