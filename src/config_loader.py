import json
from pathlib import Path


CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "university-config.json"


def load_category_config(config_path: Path = CONFIG_PATH):
    with config_path.open("r", encoding="utf-8") as config_file:
        config = json.load(config_file)

    categories = config.get("categories", {})
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
