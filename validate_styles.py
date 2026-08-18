"""스타일 프로필 YAML을 검증한다 — 필수 항목 누락, 빈 값, 프롬프트 생성 가능 여부.

사용법:
    python validate_styles.py
"""

import sys
from pathlib import Path

import yaml

from make_prompt import build_prompt

STYLES_DIR = Path("styles")

REQUIRED = [
    "name", "label", "identity", "instrumentation", "tempo_rhythm",
    "harmony", "melody_hooks", "dynamic_arc", "vocal", "production",
    "constraints", "grounding",
]


def main() -> None:
    files = sorted(STYLES_DIR.glob("*.yaml"))
    if not files:
        sys.exit("styles/ 에 프로필이 없습니다.")

    all_ok = True
    print(f"■ 스타일 프로필 검증 ({len(files)}개)\n" + "=" * 72)

    for path in files:
        problems = []
        try:
            prof = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            print(f"\n✗ {path.name}\n   YAML 파싱 실패: {str(e)[:120]}")
            all_ok = False
            continue

        for key in REQUIRED:
            if key not in prof:
                problems.append(f"필수 항목 누락: {key}")
            elif not prof[key]:
                problems.append(f"빈 값: {key}")

        inst = prof.get("instrumentation") or {}
        if not inst.get("allow"):
            problems.append("instrumentation.allow 가 비어 있음")
        if not inst.get("roles"):
            problems.append("instrumentation.roles 가 비어 있음")

        if prof.get("name") != path.stem:
            problems.append(f"name({prof.get('name')}) 과 파일명({path.stem}) 불일치")

        n_constraints = len(prof.get("constraints") or [])
        if n_constraints < 3:
            problems.append(f"constraints 가 {n_constraints}개 — 최소 3개 권장")

        # 실제로 프롬프트가 생성되는지
        prompt_len = 0
        try:
            prompt_len = len(build_prompt(prof, "A", "harmonics", "lyrics", False))
        except Exception as e:
            problems.append(f"프롬프트 생성 실패: {e}")

        if problems:
            all_ok = False
            print(f"\n✗ {path.name}")
            for p in problems:
                print(f"   - {p}")
        else:
            print(f"✓ {path.stem:<22} {prof['label'][:34]:<36} "
                  f"{n_constraints}개 제약 / {prompt_len:,}자")

    print("\n" + "=" * 72)
    print("모든 프로필 정상" if all_ok else "문제가 있는 프로필이 있습니다 (위 참조)")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
