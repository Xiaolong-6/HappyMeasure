from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web"
INDEX = WEB / "index.html"

EXPECTED_LINKS = {
    "https://xiaolong-6.github.io/HM-Map-Reconstruction/",
    "https://xiaolong-6.github.io/HM-IV-Fitter/",
    "https://github.com/Xiaolong-6/HappyMeasure/releases",
}


class LinkCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self.ids: set[str] = set()
        self.duplicate_ids: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        element_id = values.get("id")
        if element_id:
            if element_id in self.ids:
                self.duplicate_ids.add(element_id)
            self.ids.add(element_id)
        for attribute in ("href", "src"):
            value = values.get(attribute)
            if value:
                self.links.append((attribute, value))


def main() -> int:
    if not INDEX.is_file():
        raise SystemExit("web/index.html is missing")

    parser = LinkCollector()
    parser.feed(INDEX.read_text(encoding="utf-8"))

    if parser.duplicate_ids:
        raise SystemExit(f"duplicate HTML ids: {sorted(parser.duplicate_ids)}")

    seen = {value for _, value in parser.links}
    missing_expected = sorted(EXPECTED_LINKS - seen)
    if missing_expected:
        raise SystemExit(f"required project links missing: {missing_expected}")

    errors: list[str] = []
    for attribute, value in parser.links:
        if value.startswith(("mailto:", "tel:")):
            continue
        if value.startswith("#"):
            fragment = value[1:]
            if fragment and fragment not in parser.ids:
                errors.append(f"missing fragment target for {value}")
            continue

        parsed = urlparse(value)
        if parsed.scheme:
            if parsed.scheme != "https":
                errors.append(f"non-HTTPS {attribute}: {value}")
            continue

        local = value.split("#", 1)[0].split("?", 1)[0]
        if not local:
            continue
        target = WEB / local
        if local.endswith("/"):
            target = target / "index.html"
        if not target.exists():
            errors.append(f"missing local {attribute} target: {value}")

    required_files = [
        WEB / ".nojekyll",
        WEB / "styles.css",
        WEB / "assets" / "favicon.svg",
        WEB / "robots.txt",
        WEB / "sitemap.xml",
    ]
    for path in required_files:
        if not path.exists():
            errors.append(f"required static file missing: {path.relative_to(ROOT)}")

    if errors:
        raise SystemExit("\n".join(errors))

    print(f"Static site check passed: {len(parser.links)} links/references, {len(parser.ids)} ids.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
