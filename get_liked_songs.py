"""Spotify에서 좋아요(♥) 표시한 곡 목록을 가져온다.

사용법:
    python get_liked_songs.py            # 콘솔 출력 + liked_songs.json 저장
    python get_liked_songs.py --csv      # liked_songs.csv 로도 저장
"""

import argparse
import csv
import json
import sys

import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth

# 좋아요 표시한 곡(라이브러리) 조회에 필요한 권한(scope)
SCOPE = "user-library-read"

PAGE_SIZE = 50  # API가 한 번에 돌려주는 최대 개수


def create_client() -> spotipy.Spotify:
    load_dotenv()
    try:
        auth = SpotifyOAuth(scope=SCOPE, open_browser=True)
    except spotipy.SpotifyOauthError as e:
        sys.exit(
            f"인증 설정 오류: {e}\n"
            ".env 파일에 SPOTIPY_CLIENT_ID / SPOTIPY_CLIENT_SECRET / "
            "SPOTIPY_REDIRECT_URI 가 있는지 확인하세요."
        )
    return spotipy.Spotify(auth_manager=auth)


def format_duration(ms: int | None) -> str:
    if ms is None:
        return "?"
    total_sec = ms // 1000
    return f"{total_sec // 60}:{total_sec % 60:02d}"


def fetch_all_liked_songs(sp: spotipy.Spotify) -> list[dict]:
    """좋아요 표시한 곡 전체를 페이지네이션으로 수집."""
    songs = []
    results = sp.current_user_saved_tracks(limit=PAGE_SIZE)
    while results:
        for item in results["items"]:
            track = (item or {}).get("track")
            if not track:  # 삭제·비공개 처리된 곡은 건너뜀
                continue
            # 응답에 따라 일부 필드가 빠질 수 있으므로 전부 .get()으로 안전하게 접근
            album = track.get("album") or {}
            artists = [a.get("name", "") for a in (track.get("artists") or [])]
            songs.append(
                {
                    "name": track.get("name", ""),
                    "artists": ", ".join(artists),
                    "album": album.get("name", ""),
                    "release_date": album.get("release_date", ""),
                    "duration_ms": track.get("duration_ms"),
                    "added_at": item.get("added_at", ""),  # 좋아요 누른 시각(UTC)
                    "id": track.get("id", ""),
                    "url": (track.get("external_urls") or {}).get("spotify", ""),
                }
            )
        results = sp.next(results) if results["next"] else None
        if results:
            print(f"  ...{len(songs)}곡 수집 중")
    return songs


def print_songs(songs: list[dict]) -> None:
    print(f"\n좋아요 표시한 곡: 총 {len(songs)}곡\n" + "=" * 60)
    for i, s in enumerate(songs, 1):
        print(f"{i:4}. {s['name']} - {s['artists']}  [{format_duration(s['duration_ms'])}]")


def save_json(songs: list[dict], path: str = "liked_songs.json") -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(songs, f, ensure_ascii=False, indent=2)
    print(f"\nJSON 저장 완료: {path}")


def save_csv(songs: list[dict], path: str = "liked_songs.csv") -> None:
    if not songs:
        return
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=songs[0].keys())
        writer.writeheader()
        writer.writerows(songs)
    print(f"CSV 저장 완료: {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="좋아요 표시한 Spotify 곡 가져오기")
    parser.add_argument("--csv", action="store_true", help="CSV 파일로도 저장")
    args = parser.parse_args()

    sp = create_client()
    me = sp.current_user()
    print(f"로그인 계정: {me['display_name']} ({me['id']})")

    songs = fetch_all_liked_songs(sp)
    print_songs(songs)
    save_json(songs)
    if args.csv:
        save_csv(songs)


if __name__ == "__main__":
    main()
