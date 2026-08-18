"""특정 아티스트의 좋아요 곡을 상세히 들여다본다 (스타일 프로필 작성용 재료).

사용법:
    python artist_detail.py PEPPERTONES
    python artist_detail.py "Band Nah" --json   # JSON으로도 출력
"""

import argparse
import json
from collections import Counter

from analyze_liked_songs import load_genres, load_songs, parse_added, song_genres


def main() -> None:
    parser = argparse.ArgumentParser(description="아티스트별 좋아요 곡 상세 보기")
    parser.add_argument("artist", help="아티스트명 (부분 일치, 대소문자 무시)")
    parser.add_argument("--json", action="store_true", help="JSON 형태로도 출력")
    args = parser.parse_args()

    songs = load_songs()
    key = args.artist.lower()
    hits = [s for s in songs if key in (s.get("artists") or "").lower()]
    if not hits:
        print(f"'{args.artist}' 로 매칭되는 곡이 없습니다.")
        return

    # 앨범별로 묶고, 앨범 내에서는 발매일순
    by_album: dict[str, list[dict]] = {}
    for s in hits:
        by_album.setdefault(s.get("album", "?"), []).append(s)

    print(f"■ '{args.artist}' 좋아요 곡: {len(hits)}곡 / {len(by_album)}개 앨범\n" + "=" * 70)
    for album in sorted(by_album, key=lambda a: by_album[a][0].get("release_date", "")):
        tracks = by_album[album]
        rel = tracks[0].get("release_date", "?")
        print(f"\n【{album}】 ({rel}) — {len(tracks)}곡")
        for t in tracks:
            ms = t.get("duration_ms") or 0
            dur = f"{ms // 60000}:{ms // 1000 % 60:02d}"
            others = [
                a for a in (t.get("artists") or "").split(", ")
                if key not in a.lower()
            ]
            feat = f"  (with {', '.join(others)})" if others else ""
            print(f"    · {t['name']} [{dur}]{feat}")

    # 발매 연대 분포 — 어느 시기 사운드를 좋아하는지
    eras = Counter((s.get("release_date", "")[:4] or "?") for s in hits)
    print(f"\n■ 발매 연도 분포\n" + "-" * 70)
    for year in sorted(eras):
        print(f"  {year}: {'●' * eras[year]} ({eras[year]}곡)")

    # 좋아요 누른 시기 — 언제 이 아티스트에 빠졌는지
    added = Counter(f"{dt:%Y-%m}" for s in hits if (dt := parse_added(s)))
    print(f"\n■ 좋아요 누른 시기\n" + "-" * 70)
    for m in sorted(added):
        print(f"  {m}: {'●' * added[m]} ({added[m]}곡)")

    # 장르 태그
    genre_map = load_genres()
    tags: Counter = Counter()
    for s in hits:
        tags.update(song_genres(s, genre_map))
    if tags:
        print(f"\n■ 장르 태그: {', '.join(g for g, _ in tags.most_common(10))}")

    # 곡 길이 통계 — 편곡 밀도의 힌트
    durs = sorted((s.get("duration_ms") or 0) / 1000 for s in hits)
    if durs:
        mid = durs[len(durs) // 2]
        print(f"■ 곡 길이: 최단 {durs[0]/60:.1f}분 / 중앙값 {mid/60:.1f}분 / 최장 {durs[-1]/60:.1f}분")

    if args.json:
        print("\n" + json.dumps(hits, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
