"""liked_songs.json의 모든 아티스트 장르를 수집한다.

1차: Last.fm 태그 (커버리지 좋음, 빠름)
2차: Last.fm에서 못 찾은 아티스트만 MusicBrainz (키 불필요, 초당 1회 제한)

결과는 artist_genres.json에 저장. 중간에 끊겨도 재실행하면 이어서 수집한다.

사용법:
    python fetch_artist_genres.py
"""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from dotenv import load_dotenv

SONGS_FILE = "liked_songs.json"
OUT_FILE = "artist_genres.json"
SAVE_EVERY = 50  # N명 처리할 때마다 중간 저장

LASTFM_URL = "https://ws.audioscrobbler.com/2.0/"
MB_URL = "https://musicbrainz.org/ws/2"
MB_HEADERS = {"User-Agent": "SportifyGenreFetcher/0.1 (dimode95@gmail.com)"}

# 장르가 아닌 Last.fm 태그(감상 방식·소장 여부 등)는 제외
NON_GENRE_TAGS = {
    "seen live", "favorites", "favourites", "favorite", "favourite",
    "albums i own", "under 2000 listeners", "spotify", "all", "beautiful",
    "check out", "love", "loved", "awesome", "amazing", "cool", "epic",
}
MIN_TAG_COUNT = 10  # Last.fm 태그 count(0~100 정규화) 최소값
MAX_GENRES = 5      # 아티스트당 최대 장르 수


def http_json(url: str, headers: dict | None = None, retries: int = 3) -> dict | None:
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers or {})
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.load(r)
        except (OSError, TimeoutError, json.JSONDecodeError):
            # OSError가 URLError·ConnectionResetError 등 네트워크 오류 전반을 포함
            if attempt < retries - 1:
                time.sleep(2 * (attempt + 1))
    return None


def lastfm_genres(artist: str, api_key: str) -> list[str] | None:
    """Last.fm 태그 조회. 실패/미발견이면 None."""
    params = urllib.parse.urlencode(
        {"method": "artist.gettoptags", "artist": artist, "autocorrect": 1,
         "api_key": api_key, "format": "json"}
    )
    data = http_json(f"{LASTFM_URL}?{params}")
    if not data or "error" in data:
        return None
    tags = data.get("toptags", {}).get("tag", [])
    genres = [
        t["name"].lower()
        for t in tags
        if t.get("count", 0) >= MIN_TAG_COUNT and t["name"].lower() not in NON_GENRE_TAGS
    ]
    return genres[:MAX_GENRES] or None


def musicbrainz_genres(artist: str) -> list[str] | None:
    """MusicBrainz 장르 조회 (초당 1회 제한 준수). 실패/미발견이면 None."""
    q = urllib.parse.quote(f'artist:"{artist}"')
    found = http_json(f"{MB_URL}/artist/?query={q}&limit=1&fmt=json", MB_HEADERS)
    time.sleep(1.1)
    if not found or not found.get("artists"):
        return None
    mbid = found["artists"][0]["id"]
    detail = http_json(f"{MB_URL}/artist/{mbid}?inc=genres&fmt=json", MB_HEADERS)
    time.sleep(1.1)
    if not detail:
        return None
    genres = [g["name"].lower() for g in detail.get("genres", [])]
    return genres[:MAX_GENRES] or None


def load_artists() -> list[str]:
    try:
        with open(SONGS_FILE, encoding="utf-8") as f:
            songs = json.load(f)
    except FileNotFoundError:
        sys.exit(f"{SONGS_FILE} 이 없습니다. 먼저 get_liked_songs.py 를 실행하세요.")
    seen: dict[str, None] = {}
    for s in songs:
        for a in (s.get("artists") or "").split(", "):
            a = a.strip()
            if a:
                seen[a] = None
    return list(seen)


def load_progress() -> dict:
    if os.path.exists(OUT_FILE):
        with open(OUT_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_progress(result: dict) -> None:
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)


def main() -> None:
    load_dotenv()
    api_key = os.getenv("LASTFM_API_KEY", "")
    if not api_key:
        sys.exit(".env 에 LASTFM_API_KEY 가 없습니다.")

    artists = load_artists()
    result = load_progress()
    todo = [a for a in artists if a not in result]
    print(f"전체 아티스트 {len(artists)}명 / 이미 수집 {len(result)}명 / 남은 작업 {len(todo)}명")

    # --- 1차: Last.fm ---
    print("\n[1차] Last.fm 태그 수집 시작")
    for i, artist in enumerate(todo, 1):
        genres = lastfm_genres(artist, api_key)
        result[artist] = {"genres": genres or [], "source": "lastfm" if genres else "none"}
        time.sleep(0.25)  # 초당 4회 정도로 예의 있게
        if i % SAVE_EVERY == 0:
            save_progress(result)
            print(f"  {i}/{len(todo)}명 처리 (Last.fm 성공률: "
                  f"{sum(1 for a in result.values() if a['source'] == 'lastfm')}/{len(result)})")
    save_progress(result)

    # --- 2차: MusicBrainz 폴백 ---
    misses = [a for a, v in result.items() if v["source"] == "none"]
    print(f"\n[2차] Last.fm 미발견 {len(misses)}명 → MusicBrainz 폴백 "
          f"(초당 1회 제한으로 약 {len(misses) * 2.2 / 60:.0f}분 예상)")
    for i, artist in enumerate(misses, 1):
        genres = musicbrainz_genres(artist)
        if genres:
            result[artist] = {"genres": genres, "source": "musicbrainz"}
        if i % 20 == 0:
            save_progress(result)
            print(f"  {i}/{len(misses)}명 처리")
    save_progress(result)

    # --- 요약 ---
    total = len(result)
    by_source = {"lastfm": 0, "musicbrainz": 0, "none": 0}
    for v in result.values():
        by_source[v["source"]] += 1
    print(f"\n완료: {OUT_FILE} 저장")
    print(f"  Last.fm 수집:     {by_source['lastfm']:5}명")
    print(f"  MusicBrainz 수집: {by_source['musicbrainz']:5}명")
    print(f"  미발견:           {by_source['none']:5}명")
    print(f"  커버리지: {(total - by_source['none']) / total * 100:.1f}%")


if __name__ == "__main__":
    main()
