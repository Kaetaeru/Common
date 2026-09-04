"""Build the static APU Schedule Builder site.

The published app runs entirely in the browser, so there is nothing for a
student to install and it works the same on macOS, Windows and phones. This
script is the only part that still needs Python, and only the person updating
the data runs it:

    py -3 build_site.py           # Windows
    python3 build_site.py         # macOS / Linux

It downloads the official APU spreadsheets, parses them with the same code the
tests cover, folds in the verified syllabus links, the language-ladder metadata
and the A+ course ratings, then writes a self-contained site to
../docs/apu-schedule-builder/ for GitHub Pages.

A+ ratings are baked in here because api.apluscoursereview.com sends no CORS
headers, so the published page cannot fetch them itself. They are a snapshot as
of the build; re-run this script to refresh them.

Useful flags:

    --colleges APM ST     build only these colleges
    --offline             reuse data/source/*.xlsx instead of downloading
    --output DIR          write somewhere else
    --serve               preview the built site on http://127.0.0.1:8000/
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import app  # noqa: F401 - installs the Windows certificate + mapping behaviour
import app_backend as backend

ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT = ROOT.parent / "docs" / "apu-schedule-builder"
COLLEGES = ("APS", "APM", "ST")
WEB_ASSETS = (
    "index.html",
    "style.css",
    "aplus.css",
    "filters.css",
    "solver.js",
    "app-i18n.js",
    "app-core.js",
    "app-ui.js",
    "app-profile.js",
    "app-filters.js",
    "app-events.js",
)


def build_college(college: str, offline: bool) -> dict:
    print(f"  {college}: ", end="", flush=True)
    backend.invalidate_college(college)
    data = app.load_or_build_data(college, allow_download=not offline)
    linked = sum(1 for s in data.get("sections", []) if s.get("syllabusUrl"))
    total = len(data.get("sections", []))
    aplus = data.get("aplusReviewStatus") or {}
    if aplus.get("available"):
        rated = f"{aplus.get('matchedSections', 0)} A+ rated"
    else:
        rated = "A+ unavailable"
    print(f"{data['stats']['subjects']} subjects, {total} classes, {linked} syllabus links, {rated}")
    return data


def clear_output(output: Path) -> None:
    """Empty the directory without removing it.

    A preview server may be running with the output as its working directory,
    and Windows refuses to remove a directory another process is sitting in.
    """
    for child in output.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def write_site(output: Path, datasets: dict[str, dict]) -> None:
    output.mkdir(parents=True, exist_ok=True)
    clear_output(output)
    (output / "data").mkdir()

    for college, data in datasets.items():
        target = output / "data" / f"{college}.json"
        target.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    for name in WEB_ASSETS:
        shutil.copy2(ROOT / "web" / name, output / name)

    any_data = next(iter(datasets.values()))
    manifest = {
        "builtAt": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "sourceVersion": any_data.get("sourceVersion", backend.DATA_VERSION),
        "term": any_data.get("term"),
        "aplusAvailable": bool((any_data.get("aplusReviewStatus") or {}).get("available")),
        "colleges": {
            college: {
                "subjects": data["stats"]["subjects"],
                "sections": data["stats"]["sections"],
                "syllabusLinks": sum(1 for s in data.get("sections", []) if s.get("syllabusUrl")),
                "aplusRatedSections": (data.get("aplusReviewStatus") or {}).get("matchedSections", 0),
            }
            for college, data in datasets.items()
        },
    }
    (output / "data" / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # GitHub Pages runs Jekyll by default, which skips files it does not expect.
    (output.parent / ".nojekyll").write_text("", encoding="utf-8")


def report(output: Path) -> None:
    total = 0
    print("\nBuilt site:")
    for path in sorted(output.rglob("*")):
        if path.is_file():
            size = path.stat().st_size
            total += size
            print(f"  {path.relative_to(output).as_posix():<28} {size / 1024:8.1f} KB")
    print(f"  {'total':<28} {total / 1024:8.1f} KB")


def serve(output: Path) -> None:
    import functools
    import webbrowser
    from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

    handler = functools.partial(SimpleHTTPRequestHandler, directory=str(output))
    server = ThreadingHTTPServer(("127.0.0.1", 8000), handler)
    url = "http://127.0.0.1:8000/"
    print(f"\nPreviewing at {url} (Ctrl+C to stop)")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--colleges", nargs="+", choices=COLLEGES, default=list(COLLEGES))
    parser.add_argument("--offline", action="store_true", help="reuse data/source/*.xlsx instead of downloading")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--serve", action="store_true", help="preview the built site after building")
    args = parser.parse_args()

    print(f"Building {', '.join(args.colleges)} ({'offline' if args.offline else 'downloading official data'})")
    datasets: dict[str, dict] = {}
    for college in args.colleges:
        try:
            datasets[college] = build_college(college, args.offline)
        except Exception as exc:
            print(f"failed - {exc}")
            return 1

    output = args.output.resolve()
    write_site(output, datasets)
    report(output)
    print(f"\nOutput: {output}")
    print("Commit it and enable GitHub Pages (Settings -> Pages -> Deploy from branch, /docs).")

    if args.serve:
        serve(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
