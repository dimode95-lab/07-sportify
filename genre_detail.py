"""장르 클러스터를 들여다본다 (스타일 프로필 작성용 재료).

사용법:
    python genre_detail.py shoegaze
    python genre_detail.py "dream pop" shoegaze     # 여러 장르 합집합
"""

import argparse
from collections import Counter

from analyze_liked_songs import load_genres, load_songs, parse_added, song_genres


def main() -> None:
    parser = argparse.ArgumentParser(description="장르별 좋아요 곡 상세 보기")
    parser.add_argument("genres", nargs="+", help="장르명 (여러 개면 합집합)")
    parser.add_argument("--top", type=int, default=25, help="아티스트 표시 개수")
    args = parser.parse_args()

    songs = load_songs()
    genre_map = load_genres()
    targets = {g.lower() for g in args.genres}

    hits = [s for s in songs if song_genres(s, genre_map) & targets]
    if not hits:
        print(f"매칭되는 곡이 없습니다: {args.genres}")
        return

    print(f"■ 장르 {' + '.join(args.genres)}: {len(hits)}곡\n" + "=" * 70)

    # 이 클러스터를 대표하는 아티스트
    artists: Counter = Counter()
    for s in hits:
        for a in (s.get("artists") or "").split(", "):
            if a.strip():
                artists[a.strip()] += 1
    print(f"\n■ 대표 아티스트 TOP {args.top}\n" + "-" * 70)
    for rank, (a, c) in enumerate(artists.most_common(args.top), 1):
        print(f"{rank:3}. {a:<32} {c:3}곡")

    # 함께 붙는 장르 — 클러스터의 실제 성격
    co: Counter = Counter()
    for s in hits:
        co.update(song_genres(s, genre_map) - targets)
    print(f"\n■ 함께 나타나는 장르 TOP 15\n" + "-" * 70)
    print("  " + ", ".join(f"{g}({c})" for g, c in co.most_common(15)))

    # 곡 길이 / 발매 연도 — 편곡 밀도와 시대감
    durs = sorted((s.get("duration_ms") or 0) / 1000 for s in hits if s.get("duration_ms"))
    if durs:
        print(f"\n■ 곡 길이: 중앙값 {durs[len(durs)//2]/60:.1f}분 "
              f"(최단 {durs[0]/60:.1f} / 최장 {durs[-1]/60:.1f})")
    eras = Counter((s.get("release_date", "")[:4] or "?") for s in hits)
    top_eras = ", ".join(f"{y}({c})" for y, c in sorted(eras.items(), key=lambda x: -x[1])[:8])
    print(f"■ 주요 발매 연도: {top_eras}")

    # 대표곡 샘플 (아티스트별 최다 곡 순)
    print(f"\n■ 대표곡 샘플\n" + "-" * 70)
    shown = 0
    for artist, _ in artists.most_common(12):
        tracks = [s["name"] for s in hits if artist in (s.get("artists") or "")][:4]
        print(f"  {artist}: {', '.join(tracks)}")
        shown += 1


if __name__ == "__main__":
    main()
