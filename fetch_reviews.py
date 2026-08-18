"""Google Sheets에 쌓인 한줄평을 내려받아 reviews.json 으로 저장한다.

사용법:
    python fetch_reviews.py              # 전체 다운로드 + 최근 10건 출력
    python fetch_reviews.py --limit 50   # 최근 50건만

.env 에 필요한 값 (SETUP.md 참고):
    REVIEW_API_URL     Apps Script 웹 앱 배포 URL
    REVIEW_API_SECRET  앱과 공유하는 비밀 토큰
"""

import argparse
import json
import os
import sys

import requests
from dotenv import load_dotenv


def main() -> None:
    parser = argparse.ArgumentParser(description="한줄평 데이터 다운로드")
    parser.add_argument("--limit", type=int, default=5000, help="가져올 최대 건수 (기본: 전체)")
    args = parser.parse_args()

    load_dotenv()
    url = os.getenv("REVIEW_API_URL")
    secret = os.getenv("REVIEW_API_SECRET")
    if not url or not secret:
        sys.exit(".env 에 REVIEW_API_URL / REVIEW_API_SECRET 를 설정하세요 (SETUP.md 참고)")

    res = requests.post(
        url,
        data=json.dumps({"secret": secret, "action": "list", "limit": args.limit}).encode("utf-8"),
        headers={"Content-Type": "text/plain;charset=utf-8"},
        timeout=30,
    )
    res.raise_for_status()
    data = res.json()
    if not data.get("ok"):
        sys.exit(f"API 오류: {data.get('error')}")

    reviews = data["reviews"]
    with open("reviews.json", "w", encoding="utf-8") as f:
        json.dump(reviews, f, ensure_ascii=False, indent=2)
    print(f"한줄평 {len(reviews)}건 저장 완료: reviews.json\n")

    for r in reviews[:10]:
        print(f"  · {r['track_name']} — {r['artists']}")
        print(f"    \"{r['review']}\"  ({str(r['saved_at'])[:10]})")


if __name__ == "__main__":
    main()
