"""스타일 프로필이 내 좋아요 곡을 얼마나 커버하는지 본다.

각 프로필의 grounding.genre_tags 로 곡을 매칭한다. 아직 어떤 프로필에도
안 걸리는 곡이 많다면 그게 다음에 만들 프로필 후보다.

사용법:
    python style_coverage.py
    python style_coverage.py --gaps 30    # 미커버 아티스트 30명까지
"""

import argparse
from collections import Counter
from pathlib import Path

import yaml

from analyze_liked_songs import load_genres, load_songs, song_genres

STYLES_DIR = Path("styles")


def load_profiles() -> dict[str, dict]:
    out = {}
    for path in sorted(STYLES_DIR.glob("*.yaml")):
        prof = yaml.safe_load(path.read_text(encoding="utf-8"))
        tags = {t.lower() for t in (prof.get("grounding") or {}).get("genre_tags", [])}
        out[path.stem] = {"label": prof.get("label", path.stem), "tags": tags}
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="스타일 프로필 커버리지")
    parser.add_argument("--gaps", type=int, default=20, help="미커버 아티스트 표시 수")
    args = parser.parse_args()

    songs = load_songs()
    genre_map = load_genres()
    profiles = load_profiles()
    if not profiles:
        print("styles/ 에 프로필이 없습니다.")
        return

    hits: Counter = Counter()       # 느슨한 매칭 (태그 하나만 걸려도 카운트)
    exclusive: Counter = Counter()  # 이 프로필에만 걸리는 곡 — 프로필의 고유 영역
    uncovered: list[dict] = []
    no_genre = 0

    for s in songs:
        genres = song_genres(s, genre_map)
        if not genres:
            no_genre += 1
            continue
        matched = [name for name, p in profiles.items() if genres & p["tags"]]
        if matched:
            for m in matched:
                hits[m] += 1
            if len(matched) == 1:
                exclusive[matched[0]] += 1
        else:
            uncovered.append(s)

    covered = len(songs) - len(uncovered) - no_genre
    print(f"■ 스타일 프로필 커버리지 ({len(profiles)}개 프로필 / 전체 {len(songs):,}곡)\n" + "=" * 72)
    print(f"  프로필에 매칭됨 : {covered:,}곡 ({covered/len(songs)*100:.0f}%)")
    print(f"  매칭 안 됨      : {len(uncovered):,}곡 ({len(uncovered)/len(songs)*100:.0f}%)")
    print(f"  장르 정보 없음   : {no_genre:,}곡 ({no_genre/len(songs)*100:.0f}%)")

    print(f"\n■ 프로필별 매칭\n" + "-" * 72)
    print("  느슨: genre_tags 중 하나라도 겹치는 곡 (indie·rock 같은 넓은 태그 탓에 과다 계상됨)")
    print("  고유: 이 프로필에만 걸리는 곡 — 프로필의 실제 고유 영역\n")
    max_ex = max(exclusive.values(), default=1)
    for name in sorted(profiles, key=lambda n: -exclusive[n]):
        ex, loose = exclusive[name], hits[name]
        bar = "█" * max(1, round(ex / max_ex * 28)) if ex else ""
        tail = "  ← genre_tags 확인 필요" if not loose else ""
        print(f"  {name:<24} 고유 {ex:4}곡 / 느슨 {loose:5}곡  {bar}{tail}")

    # 미커버 영역 — 다음 프로필 후보
    if uncovered:
        artists: Counter = Counter()
        tags: Counter = Counter()
        for s in uncovered:
            for a in (s.get("artists") or "").split(", "):
                if a.strip():
                    artists[a.strip()] += 1
            tags.update(song_genres(s, genre_map))
        print(f"\n■ 아직 프로필이 없는 영역 — 다음 후보\n" + "-" * 72)
        print("  많이 나오는 장르: " + ", ".join(f"{g}({c})" for g, c in tags.most_common(12)))
        print(f"\n  대표 아티스트 TOP {args.gaps}:")
        for rank, (a, c) in enumerate(artists.most_common(args.gaps), 1):
            print(f"   {rank:3}. {a:<32} {c:3}곡")


if __name__ == "__main__":
    main()
