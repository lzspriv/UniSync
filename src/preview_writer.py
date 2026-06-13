import json
from pathlib import Path

from date_utils import UNKNOWN_DATE


DEFAULT_PREVIEW_PATH = Path(__file__).resolve().parent.parent / "category-previews.json"


def build_preview_item(item: dict):
    show_summary = bool(item.get("show_summary"))
    preview_item = {
        "title": item.get("title", "(無標題)"),
        "url": item.get("url", ""),
        "date": item.get("date", UNKNOWN_DATE),
        "date_label": item.get("date_label", "發布日期"),
        "summary": item.get("summary", "") if show_summary else "",
    }

    if show_summary:
        preview_item["show_summary"] = True

    return preview_item


def build_category_preview_payload(category_previews: dict, category_labels: dict):
    preview_data = {}

    for category_id, items in category_previews.items():
        preview_data[category_id] = {
            "label": category_labels.get(category_id, category_id),
            "announcements": [
                build_preview_item(item)
                for item in items
            ],
        }

    return preview_data


def write_category_previews(category_previews: dict, category_labels: dict, output_path: Path = DEFAULT_PREVIEW_PATH):
    preview_data = build_category_preview_payload(category_previews, category_labels)

    with output_path.open("w", encoding="utf-8") as output_file:
        json.dump(preview_data, output_file, ensure_ascii=False, indent=2)

    return output_path
