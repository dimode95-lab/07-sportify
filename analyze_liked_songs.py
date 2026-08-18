"""liked_songs.json을 분석한다: 연도별/월별 좋아요 추이, 아티스트 순위.

사용법:
    python analyze_liked_songs.py              # 전체 분석 출력
    python analyze_liked_songs.py --top 30     # 아티스트 순위 30위까지
"""

import argparse
import json
import sys
from collections import Counter
from datetime import datetime

from genre_normalize import normalize

DATA_FILE = "liked_songs.json"
GENRE_FILE = "artist_genres.json"  # fetch_artist_genres.py 가 생성
BAR_WIDTH = 40  # 막대그래프 최대 폭(문자 수)


def load_songs() -> list[dict]:
    try:
        with open(DATA_FILE, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        sys.exit(f"{DATA_FILE} 이 없습니다. 먼저 get_liked_songs.py 를 실행하세요.")


def parse_added(song: dict) -> datetime | None:
    raw = song.get("added_at") or ""
    try:
        return datetime.strptime(raw, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return None


def bar(count: int, max_count: int) -> str:
    if max_count == 0:
        return ""
    return "█" * max(1, round(count / max_count * BAR_WIDTH))


def show_yearly_trend(songs: list[dict]) -> None:
    counts = Counter(dt.year for s in songs if (dt := parse_added(s)))
    if not counts:
        print("added_at 정보가 없어 추이 분석을 건너뜁니다.")
        return
    max_count = max(counts.values())
    print("\n■ 연도별 좋아요 추이\n" + "-" * 60)
    for year in sorted(counts):
        c = counts[year]
        print(f"{year}  {c:5}곡  {bar(c, max_count)}")


def show_monthly_trend(songs: list[dict], recent_months: int = 24) -> None:
    counts = Counter(f"{dt.year}-{dt.month:02d}" for s in songs if (dt := parse_added(s)))
    if not counts:
        return
    months = sorted(counts)[-recent_months:]
    max_count = max(counts[m] for m in months)
    print(f"\n■ 월별 좋아요 추이 (최근 {len(months)}개월)\n" + "-" * 60)
    for m in months:
        c = counts[m]
        print(f"{m}  {c:5}곡  {bar(c, max_count)}")


def show_top_artists(songs: list[dict], top_n: int) -> None:
    counts: Counter = Counter()
    for s in songs:
        # "A, B" 형태로 저장된 참여 아티스트를 각각 1카운트
        for artist in (s.get("artists") or "").split(", "):
            if artist.strip():
                counts[artist.strip()] += 1
    print(f"\n■ 가장 많이 좋아요한 아티스트 TOP {top_n}\n" + "-" * 60)
    max_count = counts.most_common(1)[0][1] if counts else 0
    for rank, (artist, c) in enumerate(counts.most_common(top_n), 1):
        print(f"{rank:3}. {artist:<30} {c:4}곡  {bar(c, max_count)}")
    print(f"\n(전체 아티스트 수: {len(counts)}명)")


def load_genres() -> dict:
    """artist_genres.json 로드. 없으면 빈 dict (장르 분석 건너뜀)."""
    try:
        with open(GENRE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def song_genres(song: dict, genre_map: dict) -> set[str]:
    """곡의 참여 아티스트들 장르를 합쳐 정규화한 집합."""
    genres: set[str] = set()
    for artist in (song.get("artists") or "").split(", "):
        info = genre_map.get(artist.strip())
        if info:
            genres.update(info.get("genres", []))
    return normalize(genres)


def show_top_genres(songs: list[dict], genre_map: dict, top_n: int) -> None:
    counts: Counter = Counter()
    unknown = 0
    for s in songs:
        genres = song_genres(s, genre_map)
        if genres:
            counts.update(genres)
        else:
            unknown += 1
    print(f"\n■ 가장 많이 좋아요한 장르 TOP {top_n}\n" + "-" * 60)
    max_count = counts.most_common(1)[0][1] if counts else 0
    for rank, (genre, c) in enumerate(counts.most_common(top_n), 1):
        print(f"{rank:3}. {genre:<25} {c:5}곡  {bar(c, max_count)}")
    covered = len(songs) - unknown
    print(f"\n(장르 확인된 곡: {covered}/{len(songs)}곡, {covered / len(songs) * 100:.0f}%)")


def show_genre_by_year(songs: list[dict], genre_map: dict, top_n: int = 5) -> None:
    """연도별로 어떤 장르를 많이 좋아요했는지."""
    by_year: dict[int, Counter] = {}
    for s in songs:
        dt = parse_added(s)
        if not dt:
            continue
        genres = song_genres(s, genre_map)
        by_year.setdefault(dt.year, Counter()).update(genres)
    print(f"\n■ 연도별 장르 취향 TOP {top_n}\n" + "-" * 60)
    for year in sorted(by_year):
        top = ", ".join(f"{g}({c})" for g, c in by_year[year].most_common(top_n))
        print(f"{year}: {top}")


def main() -> None:
    parser = argparse.ArgumentParser(description="좋아요 곡 데이터 분석")
    parser.add_argument("--top", type=int, default=20, help="아티스트 순위 표시 개수 (기본 20)")
    args = parser.parse_args()

    songs = load_songs()
    print(f"분석 대상: {len(songs)}곡 ({DATA_FILE})")

    show_yearly_trend(songs)
    show_monthly_trend(songs)
    show_top_artists(songs, args.top)

    genre_map = load_genres()
    if genre_map:
        show_top_genres(songs, genre_map, args.top)
        show_genre_by_year(songs, genre_map)
    else:
        print(f"\n({GENRE_FILE} 이 없어 장르 분석은 건너뜁니다 — "
              "fetch_artist_genres.py 를 먼저 실행하세요)")


if __name__ == "__main__":
    main()
