#!/usr/bin/env python3
"""Render docs/index.html: template.html + data/bundle.json + docs/basemap.jpg, one self-contained file."""
import base64

from citations import DATA, DOCS, ROOT

page = (ROOT / "template.html").read_text()
page = page.replace("__DATA__", (DATA / "bundle.json").read_text())
page = page.replace("__BASEMAP__", "data:image/jpeg;base64," + base64.b64encode((DOCS / "basemap.jpg").read_bytes()).decode())
out = DOCS / "index.html"
out.write_text(page)
print(out, f"{len(page) // 1024} KB")
