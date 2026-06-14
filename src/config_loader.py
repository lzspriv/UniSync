import json
from pathlib import Path
from copy import deepcopy


CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "university-config.json"


def resolve_category_selectors(categories: dict, selector_presets: dict):
    resolved_categories = deepcopy(categories)

    for category_id, meta in resolved_categories.items():
        preset_name = meta.get("selectorPreset")
        inline_selectors = meta.get("selectors")
        if not preset_name:
            continue

        if preset_name not in selector_presets:
            raise ValueError(f"Unknown selectorPreset '{preset_name}' for category '{category_id}'")

        resolved_selectors = deepcopy(selector_presets[preset_name])
        if inline_selectors:
            resolved_selectors.update(inline_selectors)
        meta["selectors"] = resolved_selectors

    return resolved_categories


def load_category_config(config_path: Path = CONFIG_PATH):
    with config_path.open("r", encoding="utf-8") as config_file:
        config = json.load(config_file)

    categories = resolve_category_selectors(
        config.get("categories", {}),
        config.get("selectorPresets", {}),
    )
    category_urls = {category_id: meta.get("url", "") for category_id, meta in categories.items()}
    category_labels = {
        category_id: (
            f"{meta.get('owner', '')}-{meta.get('label', category_id)}"
            if meta.get("owner")
            else meta.get("label", category_id)
        )
        for category_id, meta in categories.items()
    }
    return category_urls, category_labels, categories
