import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "src"
CONFIG_PATH = ROOT / "config" / "university-config.json"
PREVIEW_PATH = ROOT / "category-previews.json"

sys.path.insert(0, str(SRC_DIR))

from config_loader import load_category_config  # noqa: E402
from preview_writer import build_preview_item  # noqa: E402
from scraper import fetch_university_announcements  # noqa: E402


def load_previews(path):
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as input_file:
        return json.load(input_file)


def refresh_previews(category_ids, labels, categories, previews, fetcher=None, max_items=5):
    fetcher = fetcher or fetch_university_announcements
    refreshed = dict(previews)
    results = []

    for category_id in category_ids:
        meta = categories[category_id]
        try:
            items = fetcher(
                meta.get("url", ""),
                labels.get(category_id, category_id),
                meta.get("selectors"),
            )
        except Exception as exc:
            results.append((category_id, "error", f"{type(exc).__name__}: {exc}"))
            continue

        if not items and not meta.get("allowEmpty", False):
            results.append((category_id, "unexpected_empty", "source returned no announcements"))
            continue

        refreshed[category_id] = {
            "label": labels.get(category_id, category_id),
            "announcements": [build_preview_item(item) for item in items[:max_items]],
        }
        results.append((category_id, "updated", f"{min(len(items), max_items)} preview items"))

    return refreshed, results


def write_previews(previews, path):
    temporary_path = path.with_suffix(f"{path.suffix}.tmp")
    temporary_path.write_text(
        json.dumps(previews, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(path)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Refresh announcement previews without database writes or notifications."
    )
    parser.add_argument("--category-id", action="append", dest="category_ids")
    parser.add_argument("--max-items", type=int, default=5)
    parser.add_argument("--output", type=Path, default=PREVIEW_PATH)
    return parser.parse_args()


def main():
    args = parse_args()
    if args.max_items < 1:
        raise SystemExit("--max-items must be at least 1")

    _, labels, categories = load_category_config(CONFIG_PATH)
    category_ids = args.category_ids or list(categories)
    unknown_ids = [category_id for category_id in category_ids if category_id not in categories]
    if unknown_ids:
        raise SystemExit(f"Unknown category IDs: {', '.join(unknown_ids)}")

    previews = load_previews(args.output)
    refreshed, results = refresh_previews(
        category_ids,
        labels,
        categories,
        previews,
        max_items=args.max_items,
    )
    write_previews(refreshed, args.output)

    failed = 0
    for category_id, status, detail in results:
        print(f"[{status.upper()}] {category_id}: {detail}")
        if status != "updated":
            failed += 1

    print(f"Preview refresh complete: updated={len(results) - failed}, failed={failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
