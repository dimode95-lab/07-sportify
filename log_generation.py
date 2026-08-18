"""Suno 생성 결과를 기록한다. 프로필 개선의 근거가 되는 피드백 로그.

사용법:
    python log_generation.py peppertones --score 4 --note "베이스가 너무 얌전함. 코러스는 좋았음"
    python log_generation.py --show          # 기록 보기
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

LOG_FILE = Path("generation_log.json")


def load_log() -> list[dict]:
    if LOG_FILE.exists():
        return json.loads(LOG_FILE.read_text(encoding="utf-8"))
    return []


def show(entries: list[dict]) -> None:
    if not entries:
        print("아직 기록이 없습니다.")
        return
    print(f"■ 생성 기록 {len(entries)}건\n" + "=" * 70)
    for e in entries:
        stars = "★" * e["score"] + "☆" * (5 - e["score"]) if e.get("score") else "-"
        print(f"\n[{e['date']}] {e['style']}  {stars}")
        opts = e.get("options", {})
        if opts:
            print(f"  옵션: {', '.join(f'{k}={v}' for k, v in opts.items() if v)}")
        if e.get("url"):
            print(f"  링크: {e['url']}")
        if e.get("note"):
            print(f"  메모: {e['note']}")

    # 스타일별 평균 점수 — 어떤 프로필이 잘 동작하는지
    by_style: dict[str, list[int]] = {}
    for e in entries:
        if e.get("score"):
            by_style.setdefault(e["style"], []).append(e["score"])
    if by_style:
        print("\n" + "=" * 70 + "\n■ 스타일별 평균 점수")
        for style, scores in sorted(by_style.items(), key=lambda x: -sum(x[1]) / len(x[1])):
            print(f"  {style:<20} {sum(scores)/len(scores):.1f}점 ({len(scores)}회)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Suno 생성 결과 기록")
    parser.add_argument("style", nargs="?", help="사용한 스타일 프로필 이름")
    parser.add_argument("--show", action="store_true", help="기록 보기")
    parser.add_argument("--score", type=int, choices=range(1, 6), help="만족도 1~5")
    parser.add_argument("--note", default="", help="무엇이 좋았고 무엇이 아쉬웠는지")
    parser.add_argument("--url", default="", help="Suno 결과 링크")
    parser.add_argument("--key", default="", help="사용한 조성")
    parser.add_argument("--intro", default="", help="사용한 인트로 장치")
    parser.add_argument("--vocal", default="", help="사용한 보컬 모드")
    args = parser.parse_args()

    entries = load_log()

    if args.show or not args.style:
        show(entries)
        return

    entries.append({
        "date": f"{datetime.now():%Y-%m-%d %H:%M}",
        "style": args.style,
        "score": args.score,
        "note": args.note,
        "url": args.url,
        "options": {"key": args.key, "intro": args.intro, "vocal": args.vocal},
    })
    LOG_FILE.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"기록 완료 ({len(entries)}번째). 아쉬웠던 점은 "
          f"styles/{args.style}.yaml 을 고쳐서 다음 생성에 반영하세요.")


if __name__ == "__main__":
    main()
