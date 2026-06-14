# Config Maintenance

`config/university-config.json` is still the source of truth for supported units,
announcement categories, URLs, scraper selectors, and the dashboard menu tree.

## Selector Presets

Use `selectorPreset` when a category uses one of the common scraper shapes in
`selectorPresets`.

Example:

```json
{
  "label": "最新消息",
  "owner": "Example Unit",
  "url": "https://example.ntnu.edu.tw/news/",
  "selectorPreset": "wordpress_broad"
}
```

If a site mostly matches a preset but needs a small override, keep
`selectorPreset` and add only the changed `selectors` fields:

```json
{
  "label": "最新消息",
  "owner": "Example Unit",
  "url": "https://example.ntnu.edu.tw/news/",
  "selectorPreset": "wordpress_broad",
  "selectors": {
    "pinned": ".is-sticky"
  }
}
```

The Python loader expands presets before scraping, so `src/main.py` and debug
tools always receive the final `selectors` object.

## Inline Selectors

Keep inline `selectors` only when the site has a one-off structure that is not
shared by other categories.

When the same inline selector appears in three or more categories, consider
promoting it to `selectorPresets`.

## Validation

Run this before committing config changes:

```powershell
C:\Users\lzspr\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe scripts\validate_config.py
```

The validator checks:

- `selectorPreset` references exist
- category URL, label, and owner fields are present
- schema channel values point to existing categories
- every category has a `category-previews.json` entry
- preview entries have an `announcements` list
- config and preview files do not contain `????`

GitHub Actions also runs this validator before the scraper.

## Generated Preview Cache

`category-previews.json` is generated cache. Prefer updating it through the
scraper workflow or a focused preview-generation run, not by hand.
