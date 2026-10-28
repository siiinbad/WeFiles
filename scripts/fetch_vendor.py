"""Refresh versioned frontend assets and their upstream licenses."""

import re
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1] / "static" / "vendor"
ASSETS = {
    "bootstrap/bootstrap.min.css": "https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css",
    "bootstrap/LICENSE": "https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/LICENSE",
    "htmx/htmx.min.js": "https://cdn.jsdelivr.net/npm/htmx.org@2.0.8/dist/htmx.min.js",
    "htmx/LICENSE": "https://cdn.jsdelivr.net/npm/htmx.org@2.0.8/LICENSE",
}
if __name__ == "__main__":
    for name, url in ASSETS.items():
        with urlopen(url, timeout=60) as response:
            content = response.read()
        if name.endswith(".css"):
            content = re.sub(rb"/\*# sourceMappingURL=.*?\*/", b"", content)
        (ROOT / name).write_bytes(content)
        print(f"Downloaded {name} ({len(content)} bytes)")
