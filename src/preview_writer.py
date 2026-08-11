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


def load_existing_preview_data(output_path: Path):
    if not output_path.exists():
        return {}

    try:
        with output_path.open("r", encoding="utf-8") as input_file:
            return json.load(input_file)
    except (OSError, json.JSONDecodeError):
        return {}


def preserve_existing_announcements(preview_data: dict, existing_preview_data: dict, allow_empty_category_ids=None):
    allow_empty_category_ids = set(allow_empty_category_ids or [])
    preserved_category_ids = []

    for category_id, current_preview in preview_data.items():
        if current_preview.get("announcements") or category_id in allow_empty_category_ids:
            continue

        existing_preview = existing_preview_data.get(category_id, {})
        existing_announcements = existing_preview.get("announcements", [])
        if not existing_announcements:
            continue

        current_preview["announcements"] = existing_announcements
        preserved_category_ids.append(category_id)

    return preserved_category_ids


def write_category_previews(
    category_previews: dict,
    category_labels: dict,
    output_path: Path = DEFAULT_PREVIEW_PATH,
    allow_empty_category_ids=None,
):
    preview_data = build_category_preview_payload(category_previews, category_labels)
    existing_preview_data = load_existing_preview_data(output_path)
    preserved_category_ids = preserve_existing_announcements(
        preview_data,
        existing_preview_data,
        allow_empty_category_ids,
    )

    temporary_path = output_path.with_suffix(f"{output_path.suffix}.tmp")
    with temporary_path.open("w", encoding="utf-8") as output_file:
        json.dump(preview_data, output_file, ensure_ascii=False, indent=2)
    temporary_path.replace(output_path)

    if preserved_category_ids:
        visible_ids = ", ".join(preserved_category_ids[:10])
        remaining_count = len(preserved_category_ids) - 10
        suffix = f"，另有 {remaining_count} 個" if remaining_count > 0 else ""
        print(
            f"⚠️ 預覽保護：{len(preserved_category_ids)} 個分類本次沒有資料，"
            f"已保留上一版（{visible_ids}{suffix}）。"
        )

    return output_path
