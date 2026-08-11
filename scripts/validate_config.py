import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "src"
CONFIG_PATH = ROOT / "config" / "university-config.json"
PREVIEW_PATH = ROOT / "category-previews.json"

sys.path.insert(0, str(SRC_DIR))

from config_loader import load_category_config  # noqa: E402
from scrapers.card_strategies import CARD_STRATEGIES  # noqa: E402
from scrapers.registry import SCRAPER_REGISTRY  # noqa: E402


SUPPORTED_PARSERS = set(SCRAPER_REGISTRY) | set(CARD_STRATEGIES)
SUPPORTED_ANNOUNCEMENT_STATUSES = {"unavailable"}


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as input_file:
        return json.load(input_file)


def collect_channel_refs(units, refs):
    for unit in units:
        for channel in unit.get("channels", []):
            refs.append(
                {
                    "unit_id": unit.get("id", ""),
                    "unit_name": unit.get("name", ""),
                    "value": channel.get("value", ""),
                }
            )
        for child_key in ("units", "subUnits", "children"):
            children = unit.get(child_key)
            if isinstance(children, list):
                collect_channel_refs(children, refs)


def validate_schema_statuses(units, errors):
    for unit in units:
        channels = unit.get("channels", [])
        status = unit.get("announcementStatus")
        children = []
        for child_key in ("units", "subUnits", "children"):
            child_nodes = unit.get(child_key)
            if isinstance(child_nodes, list):
                children.extend(child_nodes)

        if status and status not in SUPPORTED_ANNOUNCEMENT_STATUSES:
            errors.append(f"{unit.get('id', '')}: unsupported announcementStatus '{status}'.")
        if status and channels:
            errors.append(f"{unit.get('id', '')}: cannot have channels and announcementStatus together.")
        if status == "unavailable" and not unit.get("announcementStatusReason"):
            errors.append(f"{unit.get('id', '')}: unavailable status requires announcementStatusReason.")
        if not children and not channels and not status:
            errors.append(f"{unit.get('id', '')}: leaf unit has neither channels nor announcementStatus.")

        if children:
            validate_schema_statuses(children, errors)


def find_text_marker(path: Path, marker: str):
    text = path.read_text(encoding="utf-8")
    return marker in text


def validate_config():
    errors = []
    warnings = []

    raw_config = load_json(CONFIG_PATH)
    previews = load_json(PREVIEW_PATH) if PREVIEW_PATH.exists() else {}
    selector_presets = raw_config.get("selectorPresets", {})
    raw_categories = raw_config.get("categories", {})
    schema = raw_config.get("schema", [])

    try:
        category_urls, category_labels, resolved_categories = load_category_config(CONFIG_PATH)
    except ValueError as exc:
        errors.append(str(exc))
        category_urls, category_labels, resolved_categories = {}, {}, raw_categories

    if not isinstance(selector_presets, dict):
        errors.append("selectorPresets must be an object when present.")

    for category_id, meta in raw_categories.items():
        if not meta.get("label"):
            errors.append(f"{category_id}: missing label.")
        if not meta.get("owner"):
            errors.append(f"{category_id}: missing owner.")

        url = meta.get("url", "")
        if not url:
            errors.append(f"{category_id}: missing url.")
        elif not url.startswith(("http://", "https://")):
            errors.append(f"{category_id}: url must start with http:// or https:// ({url}).")

        preset_name = meta.get("selectorPreset")
        if preset_name and preset_name not in selector_presets:
            errors.append(f"{category_id}: unknown selectorPreset '{preset_name}'.")

        selectors = meta.get("selectors")
        if selectors is not None and not isinstance(selectors, dict):
            errors.append(f"{category_id}: selectors must be an object.")

        resolved_selectors = resolved_categories.get(category_id, {}).get("selectors")
        if preset_name and not resolved_selectors:
            errors.append(f"{category_id}: selectorPreset '{preset_name}' did not resolve selectors.")

        parser_name = (resolved_selectors or {}).get("parser")
        if parser_name and parser_name not in SUPPORTED_PARSERS:
            errors.append(f"{category_id}: unsupported parser '{parser_name}'.")

    channel_refs = []
    collect_channel_refs(schema, channel_refs)
    validate_schema_statuses(schema, errors)

    for ref in channel_refs:
        value = ref["value"]
        if not value:
            errors.append(f"{ref['unit_id']}: channel is missing value.")
        elif value not in raw_categories:
            errors.append(
                f"{ref['unit_id']} ({ref['unit_name']}): channel '{value}' has no matching category."
            )

    missing_previews = sorted(category_id for category_id in raw_categories if category_id not in previews)
    for category_id in missing_previews:
        errors.append(f"{category_id}: missing preview entry in category-previews.json.")

    extra_previews = sorted(category_id for category_id in previews if category_id not in raw_categories)
    for category_id in extra_previews:
        warnings.append(f"{category_id}: preview entry has no matching category.")

    for category_id, preview in previews.items():
        if category_id not in raw_categories:
            continue
        announcements = preview.get("announcements")
        if announcements is None:
            errors.append(f"{category_id}: preview entry is missing announcements.")
        elif not isinstance(announcements, list):
            errors.append(f"{category_id}: preview announcements must be a list.")

    for path in (CONFIG_PATH, PREVIEW_PATH):
        if path.exists() and find_text_marker(path, "????"):
            errors.append(f"{path.relative_to(ROOT)} contains ???? marker.")

    print(f"Categories: {len(raw_categories)}")
    print(f"Selector presets: {len(selector_presets)}")
    print(f"Schema channel refs: {len(channel_refs)}")
    print(f"Preview entries: {len(previews)}")
    print(f"Resolved URLs: {len(category_urls)}")
    print(f"Resolved labels: {len(category_labels)}")

    if warnings:
        print("\nWarnings:")
        for warning in warnings:
            print(f"  - {warning}")

    if errors:
        print("\nErrors:")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("\nConfig validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(validate_config())
