#!/usr/bin/env python3
"""Generate org-wide contribution heatmap SVGs for the scamai org profile.

Aggregates daily commit counts across ALL org repositories (public + private)
for the last 52 weeks, then renders GitHub-style contribution calendars to
profile/contribution-wall-light.svg and profile/contribution-wall-dark.svg.

Requires ORG_STATS_TOKEN (or GITHUB_TOKEN) with read access to all org repos.
Stdlib only — no pip installs needed on Actions runners.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ORG = "scamai"
API = "https://api.github.com"
OUT_DIR = Path(__file__).resolve().parent.parent / "profile"

TOKEN = os.environ.get("ORG_STATS_TOKEN") or os.environ.get("GITHUB_TOKEN")

# ─── GitHub API ──────────────────────────────────────────────────────────────


def api(path: str):
    """Return (status, parsed_json_or_None) for a GitHub API GET.

    Retries transient network errors (timeouts, resets) a few times.
    """
    req = urllib.request.Request(
        API + path,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "scamai-contribution-wall",
        },
    )
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read()
                return resp.status, (json.loads(body) if body.strip() else None)
        except urllib.error.HTTPError as e:
            return e.code, None
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            if attempt == 3:
                raise
            print(f"  network error on {path} ({e}), retrying...")
            time.sleep(3 * (attempt + 1))


def list_repos():
    repos, page = [], 1
    while True:
        status, data = api(f"/orgs/{ORG}/repos?per_page=100&type=all&page={page}")
        if status != 200 or not data:
            break
        repos.extend(r["name"] for r in data)
        if len(data) < 100:
            break
        page += 1
    return repos


def fetch_daily_counts(repos):
    """Sum per-day commit counts across repos via the commit_activity stats API.

    The stats endpoint returns 202 while GitHub computes the data server-side,
    so unfinished repos are retried with backoff.
    """
    counts = defaultdict(int)
    done = set()
    pending = list(repos)
    for attempt in range(7):
        still_pending = []
        for name in pending:
            status, data = api(f"/repos/{ORG}/{name}/stats/commit_activity")
            if status == 202:
                still_pending.append(name)
            elif status == 200 and data:
                for week in data:
                    week_start = datetime.fromtimestamp(
                        week["week"], tz=timezone.utc
                    ).date()
                    for i, n in enumerate(week["days"]):
                        if n:
                            counts[week_start + timedelta(days=i)] += n
                done.add(name)
            else:
                done.add(name)  # empty repo (204) or inaccessible — skip
        pending = still_pending
        if not pending:
            break
        wait = 4 * (attempt + 1)
        print(f"  {len(pending)} repos still computing, retrying in {wait}s...")
        time.sleep(wait)
    if pending:
        print(f"  WARNING: gave up on {len(pending)} repos: {pending[:10]}...")
    return counts, len(done)


# ─── SVG rendering ───────────────────────────────────────────────────────────

CELL, GAP = 11, 3
PITCH = CELL + GAP
COLS, ROWS = 53, 7
LEFT, TOP = 34, 22
FOOTER = 30

THEMES = {
    "light": {
        "text": "#57606a",
        "levels": ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"],
    },
    "dark": {
        "text": "#8b949e",
        "levels": ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"],
    },
}

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def level_thresholds(counts):
    nonzero = sorted(c for c in counts.values() if c > 0)
    if not nonzero:
        return 1, 2, 3
    q = lambda p: nonzero[min(len(nonzero) - 1, int(p * len(nonzero)))]
    return q(0.25), q(0.5), q(0.75)


def render_svg(counts, week0, today, theme, total, repo_count):
    t1, t2, t3 = level_thresholds(counts)
    colors = THEMES[theme]["levels"]
    text = THEMES[theme]["text"]
    width = LEFT + COLS * PITCH - GAP + 14
    height = TOP + ROWS * PITCH - GAP + FOOTER

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        f'<style>text{{font:11px -apple-system,BlinkMacSystemFont,"Segoe UI",'
        f'Helvetica,Arial,sans-serif;fill:{text}}}</style>',
    ]

    prev_month = None
    for col in range(COLS):
        sunday = week0 + timedelta(weeks=col)
        if sunday.month != prev_month:
            if prev_month is not None:
                x = LEFT + col * PITCH
                parts.append(f'<text x="{x}" y="{TOP - 8}">{MONTHS[sunday.month - 1]}</text>')
            prev_month = sunday.month

    for row, label in [(1, "Mon"), (3, "Wed"), (5, "Fri")]:
        y = TOP + row * PITCH + CELL - 2
        parts.append(f'<text x="0" y="{y}">{label}</text>')

    for col in range(COLS):
        for row in range(ROWS):
            d = week0 + timedelta(weeks=col, days=row)
            if d > today:
                continue
            n = counts.get(d, 0)
            lvl = 0 if n == 0 else 1 if n <= t1 else 2 if n <= t2 else 3 if n <= t3 else 4
            x, y = LEFT + col * PITCH, TOP + row * PITCH
            parts.append(
                f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" '
                f'fill="{colors[lvl]}"><title>{d.isoformat()}: {n} commit'
                f'{"s" if n != 1 else ""}</title></rect>'
            )

    fy = TOP + ROWS * PITCH - GAP + 20
    parts.append(
        f'<text x="{LEFT}" y="{fy}">{total:,} commits across {repo_count} '
        f'repositories in the last year</text>'
    )
    legend_x = width - 14 - 5 * PITCH - 64
    parts.append(f'<text x="{legend_x - 32}" y="{fy}">Less</text>')
    for i, c in enumerate(colors):
        parts.append(
            f'<rect x="{legend_x + i * PITCH}" y="{fy - CELL + 2}" '
            f'width="{CELL}" height="{CELL}" rx="2" fill="{c}"/>'
        )
    parts.append(f'<text x="{legend_x + 5 * PITCH + 4}" y="{fy}">More</text>')
    parts.append("</svg>")
    return "\n".join(parts)


# ─── Main ────────────────────────────────────────────────────────────────────


def main():
    if not TOKEN:
        sys.exit("ERROR: ORG_STATS_TOKEN (or GITHUB_TOKEN) is not set")

    repos = list_repos()
    if not repos:
        sys.exit("ERROR: could not list org repos — check token scopes")
    print(f"Found {len(repos)} repos in {ORG}")

    counts, fetched = fetch_daily_counts(repos)

    today = datetime.now(timezone.utc).date()
    week0 = today - timedelta(days=(today.weekday() + 1) % 7, weeks=COLS - 1)
    window = {d: n for d, n in counts.items() if week0 <= d <= today}
    total = sum(window.values())
    if total == 0:
        sys.exit("ERROR: zero commits found — refusing to overwrite the wall")
    print(f"Aggregated {total:,} commits over {len(window)} active days "
          f"from {fetched} repos")

    OUT_DIR.mkdir(exist_ok=True)
    for theme in THEMES:
        svg = render_svg(window, week0, today, theme, total, len(repos))
        out = OUT_DIR / f"contribution-wall-{theme}.svg"
        out.write_text(svg)
        print(f"Wrote {out}")


if __name__ == "__main__":
    main()
