#!/usr/bin/env python3
"""Small local, read-only extraction browser for audio.rpf and levels.rpf.

Archive -> bounded range pages -> range detail -> back.  audio.rpf ranges are
joined to the verified extraction manifest; levels.rpf is index-only.  No
payload is copied and no archive is re-indexed or re-extracted.
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import os
from collections import Counter, defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INDEX = ROOT / "output" / "index"
DEFAULT_MANIFEST = ROOT / "output" / "extracted" / "audio" / "manifest.tsv"
DEFAULT_VERIFICATION = ROOT / "output" / "verification.tsv"
ARCHIVES = ("audio", "levels")


def read_tsv(path: Path):
    with path.open(newline="", encoding="utf-8") as handle:
        yield from csv.DictReader(handle, delimiter="\t")


class Index:
    def __init__(self, path: Path):
        self.path = path
        self.offsets: list[int] = []
        self.summary = defaultdict(lambda: [0, 0, 0])
        self.total_stored = 0
        self.total_decoded = 0
        with path.open("rb") as handle:
            header = handle.readline()
            if not header.startswith(b"kind\tstart\tend\t"):
                raise ValueError(f"unexpected index header: {path}")
            while True:
                offset = handle.tell()
                line = handle.readline()
                if not line:
                    break
                fields = line.decode("utf-8").rstrip("\n").split("\t")
                kind, start, end, stored, decoded = fields[:5]
                stored_i, decoded_i = int(stored), int(decoded or 0)
                self.offsets.append(offset)
                self.summary[kind][0] += 1
                self.summary[kind][1] += stored_i
                self.summary[kind][2] += decoded_i
                self.total_stored += stored_i
                self.total_decoded += decoded_i
        self.rows = len(self.offsets)

    def row(self, index: int):
        with self.path.open("rb") as handle:
            handle.seek(self.offsets[index])
            line = handle.readline().decode("utf-8").rstrip("\n")
        fields = line.split("\t")
        return {
            "row": index,
            "kind": fields[0],
            "start": int(fields[1], 16),
            "end": int(fields[2], 16),
            "stored": int(fields[3]),
            "decoded": int(fields[4] or 0),
            "chain_start": fields[5] if len(fields) > 5 else "",
        }

    def page(self, page: int, size: int):
        start = max(0, page - 1) * size
        end = min(self.rows, start + size)
        return [self.row(index) for index in range(start, end)]


def load_manifest(path: Path):
    if not path.is_file():
        return {}
    return {int(row["start"], 16): row for row in read_tsv(path)}


def load_verification(path: Path):
    if not path.is_file():
        return {}
    return {Path(row["archive"]).name: row for row in read_tsv(path)}


class Pilot:
    def __init__(self, index_dir: Path, manifest: Path, verification: Path, page_size: int):
        self.indexes = {name: Index(index_dir / f"{name}.tsv") for name in ARCHIVES}
        self.manifest = load_manifest(manifest)
        self.verification = load_verification(verification)
        self.page_size = page_size

    def status(self, archive: str, row: dict):
        if row["kind"] != "zlib":
            return "unresolved"
        if archive != "audio":
            return "indexed-only"
        extracted = self.manifest.get(row["start"])
        if not extracted:
            return "indexed-only"
        verdict = self.verification.get("audio.rpf", {})
        return "verified" if verdict.get("status") == "PASS" else "extracted"

    def archive_meta(self, archive: str):
        index = self.indexes[archive]
        kinds = {kind: values[0] for kind, values in index.summary.items()}
        if archive == "audio":
            status = "verified" if self.verification.get("audio.rpf", {}).get("status") == "PASS" else "extracted"
            note = "verified zlib extraction; AWC/XMA2/Opus/ACE1 decoded separately"
        else:
            status = "indexed-only"
            note = "no payload extraction; bounded range index only"
        return {
            "name": archive,
            "rows": index.rows,
            "stored": index.total_stored,
            "decoded": index.total_decoded,
            "kinds": kinds,
            "status": status,
            "note": note,
        }


def fmt(value: int) -> str:
    return f"{value:,}".replace(",", " ")


def esc(value) -> str:
    return html.escape(str(value))


STYLE = """
:root{color-scheme:dark;--bg:#141820;--panel:#202733;--line:#424e60;--accent:#a9e0c0;--warn:#e8c48a}
*{box-sizing:border-box}body{max-width:78rem;margin:auto;padding:clamp(1rem,4vw,3rem);font:1rem system-ui;background:var(--bg);color:#eef1f4}
a{color:var(--accent)}h1{font-size:clamp(1.5rem,5vw,2.3rem);margin:0 0 1rem}
.cards{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1rem}.card,table,pre{background:var(--panel);border:1px solid var(--line);border-radius:.6rem}
.card{padding:1rem}.card h2{margin:.2rem 0 .5rem}.status{color:var(--accent);font-size:.85rem}.muted{color:#aeb8c6}
table{border-collapse:collapse;width:100%;font-size:.9rem}th,td{padding:.45rem .6rem;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{color:var(--accent);font-weight:600}tr:last-child td{border-bottom:0}.num{text-align:right;font-variant-numeric:tabular-nums}
nav{display:flex;gap:.75rem;align-items:center;flex-wrap:wrap;margin:1rem 0}nav a{border:1px solid var(--line);padding:.35rem .7rem;border-radius:.4rem;text-decoration:none}
pre{padding:1rem;white-space:pre-wrap;overflow-wrap:anywhere}.pill{display:inline-block;padding:.1rem .45rem;border:1px solid var(--line);border-radius:999px;font-size:.8rem}
"""


def layout(title: str, body: str) -> bytes:
    return f"""<!doctype html><html lang="pt-BR"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{esc(title)}</title>
<style>{STYLE}</style><h1>{esc(title)}</h1>{body}</html>""".encode()


class Handler(BaseHTTPRequestHandler):
    pilot: Pilot

    def do_GET(self):
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        try:
            if parsed.path == "/":
                body = self.home()
            elif parsed.path == "/archive":
                body = self.archive(query)
            elif parsed.path == "/range":
                body = self.range(query)
            else:
                self.send_error(404)
                return
        except (ValueError, IndexError, KeyError) as exc:
            self.send_error(400, str(exc))
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        return

    def home(self):
        cards = []
        for name in ARCHIVES:
            meta = self.pilot.archive_meta(name)
            kinds = ", ".join(f"{kind}: {fmt(count)}" for kind, count in sorted(meta["kinds"].items()))
            cards.append(
                f'<section class="card"><span class="status">{esc(meta["status"])}</span>'
                f'<h2><a href="/archive?name={name}">{name}.rpf</a></h2>'
                f'<p>{fmt(meta["rows"])} ranges · {fmt(meta["stored"])} stored · '
                f'{fmt(meta["decoded"])} decoded</p><p class="muted">{esc(meta["note"])}</p>'
                f'<p class="muted">{esc(kinds)}</p></section>'
            )
        body = (
            '<p class="muted">Read-only pilot. Archive → bounded range pages → range detail → back. '
            'Uncertain pack membership stays at archive level.</p>'
            f'<div class="cards">{"".join(cards)}</div>'
        )
        return layout("Extraction pilot", body)

    def archive(self, query):
        name = query.get("name", ["audio"])[0]
        if name not in self.pilot.indexes:
            raise ValueError("unknown archive")
        index = self.pilot.indexes[name]
        page = max(1, int(query.get("page", ["1"])[0]))
        size = self.pilot.page_size
        rows = index.page(page, size)
        pages = max(1, (index.rows + size - 1) // size)
        if page > pages:
            page = pages
            rows = index.page(page, size)
        meta = self.pilot.archive_meta(name)
        body_rows = []
        for row in rows:
            status = self.pilot.status(name, row)
            body_rows.append(
                "<tr>"
                f'<td><a href="/range?name={name}&row={row["row"]}">{row["start"]:#x}</a></td>'
                f'<td>{row["end"]:#x}</td><td>{esc(row["kind"])}</td>'
                f'<td class="num">{fmt(row["stored"])}</td>'
                f'<td class="num">{fmt(row["decoded"])}</td>'
                f'<td>{esc(status)}</td></tr>'
            )
        nav = (
            f'<nav><a href="/">← archives</a>'
            f'<a href="/archive?name={name}&page=1">first</a>'
            f'<a href="/archive?name={name}&page={max(1, page - 1)}">previous</a>'
            f'<span>{page} / {pages}</span>'
            f'<a href="/archive?name={name}&page={min(pages, page + 1)}">next</a>'
            f'<a href="/archive?name={name}&page={pages}">last</a></nav>'
        )
        table = (
            '<table><thead><tr><th>start</th><th>end</th><th>kind</th><th>stored</th>'
            '<th>decoded</th><th>status</th></tr></thead><tbody>'
            + "".join(body_rows) + "</tbody></table>"
        )
        summary = (
            f'<p><span class="pill">{esc(meta["status"])}</span> '
            f'{fmt(meta["rows"])} ranges · {fmt(meta["stored"])} stored · '
            f'{fmt(meta["decoded"])} decoded</p><p class="muted">{esc(meta["note"])}</p>'
        )
        return layout(f"{name}.rpf", summary + nav + table + nav)

    def range(self, query):
        name = query.get("name", ["audio"])[0]
        if name not in self.pilot.indexes:
            raise ValueError("unknown archive")
        row = self.pilot.indexes[name].row(int(query.get("row", ["0"])[0]))
        status = self.pilot.status(name, row)
        lines = [
            f"Archive: {name}.rpf",
            f"Status: {status}",
            f"Source extent: {row['start']:#x} .. {row['end']:#x} (end exclusive)",
            f"Kind: {row['kind']}",
            f"Stored bytes: {fmt(row['stored'])}",
            f"Decoded bytes: {fmt(row['decoded'])}",
        ]
        if name == "audio" and row["start"] in self.pilot.manifest:
            item = self.pilot.manifest[row["start"]]
            lines += [
                f"Extracted file: {item['path']}",
                f"Extracted bytes: {fmt(int(item['decoded_bytes']))}",
                f"SHA-256: {item['sha256']}",
                f"Verification: {self.pilot.verification.get('audio.rpf', {}).get('status', 'missing')}",
            ]
        elif name == "audio":
            lines.append("No extracted file for this range; indexed-only.")
        else:
            lines.append("No extracted file: levels.rpf is indexed-only in this pilot.")
        nav = f'<nav><a href="/archive?name={name}">← {name} pages</a></nav>'
        return layout(f"{name}.rpf {row['start']:#x}", nav + "<pre>" + esc("\n".join(lines)) + "</pre>" + nav)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--index-dir", type=Path, default=DEFAULT_INDEX)
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--verification", type=Path, default=DEFAULT_VERIFICATION)
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--page-size", type=int, default=100)
    ap.add_argument("--bind", default="127.0.0.1")
    args = ap.parse_args()
    if args.page_size < 1:
        ap.error("--page-size must be positive")
    pilot = Pilot(args.index_dir, args.manifest, args.verification, args.page_size)
    Handler.pilot = pilot
    server = ThreadingHTTPServer((args.bind, args.port), Handler)
    print(f"extraction pilot: http://{args.bind}:{args.port}/", flush=True)
    print(f"audio rows={pilot.indexes['audio'].rows} levels rows={pilot.indexes['levels'].rows}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
