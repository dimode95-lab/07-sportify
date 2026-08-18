"""liked_songs.json + artist_genres.json 으로 정적 HTML 리포트(report.html)를 생성한다.

사용법:
    python generate_report.py
"""

import html
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

import yaml

from analyze_liked_songs import load_genres, load_songs, parse_added, song_genres

OUT_FILE = "report.html"
STYLES_DIR = Path("styles")
TOP_N = 20


def esc(s: str) -> str:
    return html.escape(str(s), quote=True)


def hbar_rows(pairs: list[tuple[str, int]], max_count: int) -> str:
    """가로 막대 목록 (아티스트/장르 순위)."""
    rows = []
    for rank, (label, count) in enumerate(pairs, 1):
        pct = count / max_count * 100 if max_count else 0
        rows.append(
            f'<div class="hrow" title="{esc(label)}: {count}곡">'
            f'<span class="hrank">{rank}</span>'
            f'<span class="hlabel">{esc(label)}</span>'
            f'<span class="htrack"><span class="hfill" style="width:{pct:.1f}%"></span></span>'
            f'<span class="hval">{count}</span>'
            f"</div>"
        )
    return "\n".join(rows)


def vbar_cols(pairs: list[tuple[str, int]], max_count: int) -> str:
    """세로 막대 목록 (월별 추이). 최대값 막대만 직접 라벨."""
    cols = []
    peak = max((c for _, c in pairs), default=0)
    for label, count in pairs:
        pct = count / max_count * 100 if max_count else 0
        top_label = f'<span class="vpeak">{count}</span>' if count == peak else ""
        cols.append(
            f'<div class="vcol" data-tip="{esc(label)}: {count}곡">'
            f'{top_label}'
            f'<span class="vfill" style="height:{max(pct, 1):.1f}%"></span>'
            f'<span class="vlabel">{esc(label[2:])}</span>'  # 25-06 형태로 축약
            f"</div>"
        )
    return "\n".join(cols)


def style_cards() -> tuple[str, int]:
    """styles/*.yaml 을 카드 목록으로. (HTML, 개수) 반환."""
    cards = []
    for path in sorted(STYLES_DIR.glob("*.yaml")):
        try:
            p = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError:
            continue
        g = p.get("grounding") or {}
        inst = " · ".join(
            i.split(" (")[0] for i in (p.get("instrumentation") or {}).get("allow", [])[:5]
        )
        meta = []
        if g.get("liked_tracks"):
            meta.append(f"{g['liked_tracks']:,}곡")
        if g.get("core_era"):
            meta.append(str(g["core_era"]))
        if g.get("median_duration_min"):
            meta.append(f"중앙값 {g['median_duration_min']}분")
        cards.append(
            f'<div class="card">'
            f'<div class="cname">{esc(p.get("label", path.stem))}</div>'
            f'<div class="cid">{esc(path.stem)}</div>'
            f'<div class="cdesc">{esc(clean_yaml(p.get("identity", "")))}</div>'
            f'<div class="cinst">{esc(inst)}</div>'
            f'<div class="cmeta">{esc(" · ".join(meta))}</div>'
            f"</div>"
        )
    return "\n".join(cards), len(cards)


def clean_yaml(text: str) -> str:
    return " ".join((text or "").split())


def build() -> str:
    songs = load_songs()
    genre_map = load_genres()
    styles_html, n_styles = style_cards()

    # --- 기본 통계 ---
    dates = sorted(dt for s in songs if (dt := parse_added(s)))
    period = f"{dates[0]:%Y.%m.%d} ~ {dates[-1]:%Y.%m.%d}" if dates else "-"

    artist_counts: Counter = Counter()
    for s in songs:
        for a in (s.get("artists") or "").split(", "):
            if a.strip():
                artist_counts[a.strip()] += 1

    genre_counts: Counter = Counter()
    covered = 0
    for s in songs:
        g = song_genres(s, genre_map)
        if g:
            covered += 1
            genre_counts.update(g)
    coverage = covered / len(songs) * 100 if songs else 0

    monthly = Counter(f"{dt.year}-{dt.month:02d}" for dt in dates)
    months = sorted(monthly)
    monthly_pairs = [(m, monthly[m]) for m in months]
    max_month = max(monthly.values(), default=0)

    by_year: dict[int, Counter] = {}
    for s in songs:
        dt = parse_added(s)
        if dt:
            by_year.setdefault(dt.year, Counter()).update(song_genres(s, genre_map))
    year_rows = "\n".join(
        f"<tr><th>{y}</th><td>"
        + ", ".join(f"{esc(g)} <span class='muted'>({c})</span>" for g, c in by_year[y].most_common(5))
        + "</td></tr>"
        for y in sorted(by_year)
    )

    top_artists = artist_counts.most_common(TOP_N)
    top_genres = genre_counts.most_common(TOP_N)

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>내 Spotify 좋아요 리포트</title>
<style>
  :root {{
    color-scheme: light;
    --page: #f9f9f7; --surface: #fcfcfb;
    --ink: #0b0b0b; --ink-2: #52514e; --muted: #898781;
    --grid: #e1e0d9; --baseline: #c3c2b7; --border: rgba(11,11,11,0.10);
    --series: #2a78d6;
  }}
  @media (prefers-color-scheme: dark) {{
    :root:not([data-theme="light"]) {{
      color-scheme: dark;
      --page: #0d0d0d; --surface: #1a1a19;
      --ink: #ffffff; --ink-2: #c3c2b7; --muted: #898781;
      --grid: #2c2c2a; --baseline: #383835; --border: rgba(255,255,255,0.10);
      --series: #3987e5;
    }}
  }}
  :root[data-theme="dark"] {{
    color-scheme: dark;
    --page: #0d0d0d; --surface: #1a1a19;
    --ink: #ffffff; --ink-2: #c3c2b7; --muted: #898781;
    --grid: #2c2c2a; --baseline: #383835; --border: rgba(255,255,255,0.10);
    --series: #3987e5;
  }}
  * {{ box-sizing: border-box; margin: 0; }}
  body {{
    background: var(--page); color: var(--ink);
    font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
    line-height: 1.5; padding: 32px 16px 64px;
  }}
  main {{ max-width: 880px; margin: 0 auto; display: grid; gap: 20px; }}
  h1 {{ font-size: 1.6rem; }}
  .sub {{ color: var(--ink-2); font-size: .9rem; margin-top: 4px; }}
  section {{
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 12px; padding: 20px 24px;
  }}
  h2 {{ font-size: 1.05rem; margin-bottom: 14px; }}
  .muted {{ color: var(--muted); }}

  /* 스탯 타일 */
  .tiles {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; }}
  .tile {{ background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 16px 20px; }}
  .tile .k {{ font-size: .8rem; color: var(--ink-2); }}
  .tile .v {{ font-size: 1.7rem; font-weight: 700; margin-top: 2px; }}
  .tile .n {{ font-size: .75rem; color: var(--muted); margin-top: 2px; }}

  /* 가로 막대 */
  .hrow {{ display: grid; grid-template-columns: 2em 11em 1fr 3.5em; gap: 8px; align-items: center; padding: 3px 0; }}
  .hrow:hover .htrack {{ filter: brightness(1.08); }}
  .hrank {{ color: var(--muted); font-size: .8rem; text-align: right; }}
  .hlabel {{ font-size: .85rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
  .htrack {{ height: 14px; position: relative; }}
  .hfill {{
    position: absolute; left: 0; top: 0; bottom: 0;
    background: var(--series); border-radius: 0 4px 4px 0; min-width: 2px;
  }}
  .hval {{ font-size: .8rem; color: var(--ink-2); font-variant-numeric: tabular-nums; }}

  /* 세로 막대 (월별) */
  .vwrap {{ display: flex; align-items: flex-end; gap: 2px; height: 180px; border-bottom: 1px solid var(--baseline); overflow-x: auto; padding-top: 20px; }}
  .vcol {{ flex: 1 0 34px; display: flex; flex-direction: column; align-items: center; justify-content: flex-end; height: 100%; position: relative; }}
  .vfill {{ width: 70%; background: var(--series); border-radius: 4px 4px 0 0; min-height: 2px; }}
  .vcol:hover .vfill {{ filter: brightness(1.08); }}
  .vlabel {{ font-size: .65rem; color: var(--muted); margin-top: 4px; white-space: nowrap; }}
  .vpeak {{ font-size: .7rem; color: var(--ink-2); margin-bottom: 2px; font-variant-numeric: tabular-nums; }}
  .vcol::after {{
    content: attr(data-tip);
    position: absolute; bottom: calc(100% + 2px); left: 50%; transform: translateX(-50%);
    background: var(--ink); color: var(--page);
    font-size: .72rem; padding: 3px 8px; border-radius: 6px; white-space: nowrap;
    opacity: 0; pointer-events: none; transition: opacity .12s; z-index: 2;
  }}
  .vcol:hover::after {{ opacity: 1; }}

  /* 연도별 장르 표 */
  table {{ width: 100%; border-collapse: collapse; font-size: .88rem; }}
  th, td {{ text-align: left; padding: 8px 10px; border-top: 1px solid var(--grid); }}
  tr:first-child th, tr:first-child td {{ border-top: none; }}
  th {{ color: var(--ink-2); font-weight: 600; width: 4em; }}

  /* 스타일 프로필 카드 */
  .cards {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 12px; }}
  .card {{ border: 1px solid var(--border); border-radius: 10px; padding: 14px 16px; }}
  .cname {{ font-weight: 650; font-size: .92rem; }}
  .cid {{ font-size: .72rem; color: var(--muted); font-family: ui-monospace, monospace; margin-top: 1px; }}
  .cdesc {{ font-size: .8rem; color: var(--ink-2); margin-top: 8px; line-height: 1.45; }}
  .cinst {{ font-size: .72rem; color: var(--muted); margin-top: 8px; }}
  .cmeta {{ font-size: .72rem; color: var(--muted); margin-top: 6px; padding-top: 6px; border-top: 1px solid var(--grid); }}

  footer {{ color: var(--muted); font-size: .78rem; text-align: center; }}
</style>
</head>
<body>
<main>
  <header>
    <h1>내 Spotify 좋아요 리포트</h1>
    <div class="sub">수집 기간 {esc(period)} · 생성일 {datetime.now():%Y-%m-%d}</div>
  </header>

  <div class="tiles">
    <div class="tile"><div class="k">좋아요한 곡</div><div class="v">{len(songs):,}</div><div class="n">곡</div></div>
    <div class="tile"><div class="k">아티스트</div><div class="v">{len(artist_counts):,}</div><div class="n">명</div></div>
    <div class="tile"><div class="k">확인된 장르</div><div class="v">{len(genre_counts):,}</div><div class="n">종 (정규화 후)</div></div>
    <div class="tile"><div class="k">장르 커버리지</div><div class="v">{coverage:.0f}%</div><div class="n">{covered:,} / {len(songs):,}곡</div></div>
  </div>

  <section>
    <h2>월별 좋아요 추이</h2>
    <div class="vwrap">
{vbar_cols(monthly_pairs, max_month)}
    </div>
  </section>

  <section>
    <h2>가장 많이 좋아요한 아티스트 TOP {TOP_N}</h2>
{hbar_rows(top_artists, top_artists[0][1] if top_artists else 0)}
  </section>

  <section>
    <h2>가장 많이 좋아요한 장르 TOP {TOP_N} <span class="muted">(정규화 적용)</span></h2>
{hbar_rows(top_genres, top_genres[0][1] if top_genres else 0)}
  </section>

  <section>
    <h2>연도별 장르 취향 TOP 5</h2>
    <table>
{year_rows}
    </table>
  </section>

  <section>
    <h2>스타일 프로필 {n_styles}종 <span class="muted">— Suno 프롬프트 생성용</span></h2>
    <div class="cards">
{styles_html}
    </div>
  </section>

  <footer>
    데이터: Spotify Web API (좋아요 곡) · Last.fm / MusicBrainz (장르 태그) ·
    한 곡에 여러 장르가 있을 수 있어 장르 곡 수 합은 전체 곡 수를 넘습니다.
  </footer>
</main>
</body>
</html>
"""


def main() -> None:
    html_text = build()
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write(html_text)
    print(f"리포트 생성 완료: {OUT_FILE}")


if __name__ == "__main__":
    main()
