import json
from pathlib import Path

from date_utils import UNKNOWN_DATE


DEFAULT_PREVIEW_PATH = Path(__file__).resolve().parent.parent / "category-previews.json"


def build_category_preview_payload(category_previews: dict, category_labels: dict):
    preview_data = {}

    for category_id, items in category_previews.items():
        preview_data[category_id] = {
            "label": category_labels.get(category_id, category_id),
            "announcements": [
                {
                    "title": item.get("title", "(無標題)"),
                    "url": item.get("url", ""),
                    "date": item.get("date", UNKNOWN_DATE),
                }
                for item in items
            ],
        }

    return preview_data


def write_category_previews(category_previews: dict, category_labels: dict, output_path: Path = DEFAULT_PREVIEW_PATH):
    preview_data = build_category_preview_payload(category_previews, category_labels)

    with output_path.open("w", encoding="utf-8") as output_file:
        json.dump(preview_data, output_file, ensure_ascii=False, indent=2)

    return output_path
