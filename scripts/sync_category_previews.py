import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "university-config.json"
PREVIEW_PATH = ROOT / "category-previews.json"


def main():
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    previews = json.loads(PREVIEW_PATH.read_text(encoding="utf-8"))
    categories = config.get("categories", {})

    synced = {}
    for category_id, meta in categories.items():
        synced[category_id] = previews.get(
            category_id,
            {
                "label": f"{meta.get('owner', '')}-{meta.get('label', category_id)}",
                "announcements": [],
            },
        )

    PREVIEW_PATH.write_text(
        json.dumps(synced, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Synced {len(synced)} preview entries.")


if __name__ == "__main__":
    main()
