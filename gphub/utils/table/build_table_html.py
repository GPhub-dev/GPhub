"""
Build Table.html at the repository root: the rendered table as one
self-contained file with style.css inlined (replaces the old wget-based
table_html_generator.py, so no dev server is needed).

Usage (from anywhere):  python3 gphub/utils/table/build_table_html.py [output]
Requires `hugo` on PATH. The build must not use --minify, because
minification rewrites the <link> tag this script replaces.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
GPHUB = HERE.parent.parent
ROOT = GPHUB.parent
LINK_TAG = '<link rel="stylesheet" href="/style.css" />'


def main():
    out = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "Table.html"
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["hugo", "--quiet", "-s", str(GPHUB), "-d", tmp], check=True)
        html = (Path(tmp) / "index.html").read_text(encoding="utf-8")
        css = (Path(tmp) / "style.css").read_text(encoding="utf-8")
    if LINK_TAG not in html:
        sys.exit(f"{LINK_TAG!r} not found in the built page; was Hugo run with --minify?")
    html = html.replace(LINK_TAG, "<style>\n" + css + "\n</style>")
    html = html.replace('href="/favicon.ico"', 'href="gphub/static/favicon.ico"')
    out.write_text(html, encoding="utf-8")
    print(f"Wrote {out} ({len(html) // 1024} KB)")


if __name__ == "__main__":
    main()
