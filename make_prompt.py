"""스타일 프로필 → Suno 프롬프트 생성기.

성공했던 페퍼톤스 프롬프트의 문단 구조를 템플릿으로 사용한다:
  ① 정체성 → ② 편성(+데모 보존) → ③ 중심 악기·인트로·조성 → ④ 편곡 전개
  → ⑤ 기승전결·보컬 → ⑥ 화성·멜로디 성격 → ⑦ 프로덕션 → ⑧ 금지 조항

사용법:
    python make_prompt.py peppertones
    python make_prompt.py peppertones --key A --intro harmonics --vocal humming --demo
    python make_prompt.py --list
"""

import argparse
import sys
from pathlib import Path

import yaml

STYLES_DIR = Path("styles")

# --intro 옵션 → 인트로 지시문
INTRO_DEVICES = {
    "harmonics": (
        "Begin with a short two-bar guitar-harmonic motif, preferably played on "
        "clean electric guitar and subtly doubled by acoustic guitar."
    ),
    "acoustic": (
        "Begin with a short unaccompanied acoustic guitar figure, two to four bars, "
        "establishing the rhythmic feel before the band enters."
    ),
    "riff": (
        "Begin with a clean electric guitar riff as the song's main instrumental hook, "
        "stated alone before the rhythm section enters."
    ),
    "band": (
        "Begin with the full band entering together on a short instrumental statement "
        "of the chorus hook."
    ),
    "none": "",
}

# --vocal 옵션 → 보컬 지시문
VOCAL_MODES = {
    "humming": (
        "The vocal must perform only wordless humming and vowel vocalise - no lyrics, "
        "no intelligible words."
    ),
    "lyrics": "",  # 프로필의 vocal 설명만 사용
    "instrumental": "This is an instrumental track with no vocal at all.",
}


def build_structure(p: dict, vocal: str) -> str:
    """Suno 가사 칸에 넣을 구조 스켈레톤.

    Suno는 [Intro] / [Verse] 같은 대괄호 섹션 태그와 괄호 안 연주 지시를 읽는다.
    프로필에 structure: 가 있으면 그걸 쓰고, 없으면 편성에서 기본 골격을 만든다.
    """
    if p.get("structure"):
        lines = []
        for sec in p["structure"]:
            lines.append(f"[{sec['section']}]")
            if sec.get("note"):
                lines.append(f"({clean(sec['note'])})")
            lines.append("")
        return "\n".join(lines).strip()

    inst = p.get("instrumentation", {})
    allow = [strip_parens(i) for i in inst.get("allow", [])]
    lead = next((i for i in allow if "guitar" in i or "piano" in i or "Rhodes" in i),
                allow[0] if allow else "lead instrument")
    rhythm = [i for i in allow if "drum" in i or "bass" in i]
    rhythm_txt = " and ".join(rhythm) if rhythm else "rhythm section"

    voice_note = {
        "humming": "wordless humming only, no lyrics",
        "instrumental": "no vocal",
        "lyrics": "lead vocal enters",
    }.get(vocal, "lead vocal enters")

    sections = [
        ("Intro", f"{lead} alone, state the main motif"),
        ("Verse 1", f"sparse - {lead} and {voice_note}, hold back the drums"),
        ("Pre-Chorus", f"{rhythm_txt} enter, tension builds"),
        ("Chorus", "full arrangement, widest point so far"),
        ("Verse 2", "return smaller but keep the drums"),
        ("Chorus", "as before, slightly fuller"),
        ("Bridge", f"strip back to {lead} and voice, quietest point"),
        ("Instrumental Break", f"{lead} takes the melody over the full band"),
        ("Final Chorus", "peak - most layers, highest energy"),
        ("Outro", "let the opening motif return and decay"),
    ]
    if vocal == "instrumental":
        sections = [(s, n) for s, n in sections
                    if s not in ("Verse 1", "Verse 2", "Bridge")]

    return "\n\n".join(f"[{s}]\n({n})" for s, n in sections)


def load_profile(name: str) -> dict:
    path = STYLES_DIR / f"{name}.yaml"
    if not path.exists():
        available = ", ".join(p.stem for p in STYLES_DIR.glob("*.yaml"))
        sys.exit(f"'{name}' 프로필이 없습니다. 사용 가능: {available or '(없음)'}")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def clean(text: str) -> str:
    """YAML 블록 스칼라의 줄바꿈을 한 문단으로 편다."""
    return " ".join((text or "").split())


def first_sentences(text: str, n: int = 2) -> str:
    """앞 n개 문장만 추린다 (compact 모드용)."""
    parts = clean(text).replace("; ", ". ").split(". ")
    out = ". ".join(parts[:n]).rstrip(".")
    return out + "." if out else ""


def strip_parens(item: str) -> str:
    """'drums (tight, crisp, live-kit)' → 'drums'"""
    return item.split(" (")[0].strip()


def build_compact(p: dict, key: str | None, intro: str, vocal: str, demo: bool) -> str:
    """Suno 스타일 입력창의 길이 제한(보통 1000자)에 맞춘 압축 버전.

    가장 결정적인 지시만 남긴다: 정체성 / 편성 / 조성·인트로 / 템포 / 보컬 / 핵심 금지 3개.
    """
    inst = p.get("instrumentation", {})
    bits: list[str] = [clean(p.get("identity", ""))]

    allow = ", ".join(strip_parens(i) for i in inst.get("allow", []))
    line = f"Only: {allow}."
    if demo:
        line += " Preserve the uploaded demo's melody, chords, feel and structure."
    bits.append(line)

    if INTRO_DEVICES.get(intro):
        bits.append(first_sentences(INTRO_DEVICES[intro], 1))
    if key:
        bits.append(f"First complete chord must be {key} major.")

    bits.append(first_sentences(p.get("tempo_rhythm", ""), 2))
    bits.append(first_sentences(p.get("melody_hooks", ""), 1))
    bits.append(first_sentences(p.get("dynamic_arc", ""), 2))

    if vocal != "instrumental":
        bits.append(first_sentences(p.get("vocal", ""), 1))
    if VOCAL_MODES.get(vocal):
        bits.append(clean(VOCAL_MODES[vocal]))

    bits.append(first_sentences(p.get("production", ""), 1))

    constraints = list(p.get("constraints", []))[:3]
    if demo:
        constraints.append("Do not replace the uploaded melody with a new topline.")
    if constraints:
        bits.append(" ".join(clean(c) for c in constraints))

    return " ".join(b for b in bits if b.strip())


def build_prompt(p: dict, key: str | None, intro: str, vocal: str, demo: bool) -> str:
    inst = p.get("instrumentation", {})
    paras: list[str] = []

    # ① 정체성
    paras.append(clean(p.get("identity", "")))

    # ② 편성 화이트리스트 (+ 데모 보존 지시)
    allow = ", ".join(inst.get("allow", []))
    para = f"Use only {allow}."
    if inst.get("optional"):
        para += f" Optionally and sparingly: {', '.join(inst['optional'])}."
    if demo:
        para += (
            " Preserve the uploaded demo's main melody, melodic phrasing, chord "
            "movement, rhythmic feel, tempo, and recognizable song structure."
        )
    paras.append(para)

    # ③ 중심 악기 역할 + 인트로 + 조성
    para = clean(inst.get("roles", ""))
    if INTRO_DEVICES.get(intro):
        para = f"{para} {INTRO_DEVICES[intro]}".strip()
    if key:
        para += (
            f" The opening motif should establish a {key} major tonal center, "
            f"and the first complete chord heard must be {key} major."
        )
    paras.append(para)

    # ④ 템포·리듬 (편곡 전개)
    paras.append(clean(p.get("tempo_rhythm", "")))

    # ⑤ 기승전결 + 보컬
    para = clean(p.get("dynamic_arc", ""))
    if vocal != "instrumental":
        para += " " + clean(p.get("vocal", ""))
    if VOCAL_MODES.get(vocal):
        para += " " + VOCAL_MODES[vocal]
    paras.append(para)

    # ⑥ 화성 + 멜로디 성격
    paras.append(clean(p.get("harmony", "")) + " " + clean(p.get("melody_hooks", "")))

    # ⑦ 프로덕션
    paras.append(clean(p.get("production", "")))

    # ⑧ 금지 조항
    constraints = list(p.get("constraints", []))
    if demo:
        constraints.append(
            "Do not replace the uploaded central melody with a completely new topline."
        )
    if constraints:
        paras.append(" ".join(constraints))

    return "\n\n".join(x for x in paras if x.strip())


def main() -> None:
    parser = argparse.ArgumentParser(description="스타일 프로필로 Suno 프롬프트 생성")
    parser.add_argument("style", nargs="?", help="프로필 이름 (styles/<이름>.yaml)")
    parser.add_argument("--list", action="store_true", help="사용 가능한 프로필 목록")
    parser.add_argument("--key", help="시작 조성 (예: A, C, G)")
    parser.add_argument(
        "--intro", default="harmonics", choices=list(INTRO_DEVICES),
        help="인트로 장치 (기본: harmonics)",
    )
    parser.add_argument(
        "--vocal", default="lyrics", choices=list(VOCAL_MODES),
        help="보컬 모드 (기본: lyrics)",
    )
    parser.add_argument("--demo", action="store_true", help="데모 파일 업로드와 함께 사용")
    parser.add_argument("--compact", action="store_true",
                        help="Suno 스타일 칸 길이 제한에 맞춘 압축 버전 (~1000자)")
    parser.add_argument("--structure", action="store_true",
                        help="Suno 가사 칸에 넣을 구조 스켈레톤도 함께 출력")
    parser.add_argument("-o", "--out", help="결과를 파일로 저장")
    args = parser.parse_args()

    if args.list or not args.style:
        print("사용 가능한 스타일 프로필:")
        for path in sorted(STYLES_DIR.glob("*.yaml")):
            prof = yaml.safe_load(path.read_text(encoding="utf-8"))
            print(f"  {path.stem:<20} {prof.get('label', '')}")
        return

    profile = load_profile(args.style)
    builder = build_compact if args.compact else build_prompt
    prompt = builder(profile, args.key, args.intro, args.vocal, args.demo)

    print("=" * 72)
    print(f"스타일: {profile.get('label', args.style)}")
    opts = [f"key={args.key or '-'}", f"intro={args.intro}", f"vocal={args.vocal}",
            f"demo={'있음' if args.demo else '없음'}",
            f"mode={'compact' if args.compact else 'full'}"]
    print(f"옵션: {' | '.join(opts)}")
    print("=" * 72 + "\n")
    print(prompt)
    print("\n" + "=" * 72)
    note = "" if args.compact else "  (--compact 로 짧은 버전 생성 가능)"
    print(f"({len(prompt)}자 — Suno의 Style/Description 칸에 붙여넣으세요){note}")

    out_text = prompt
    if args.structure:
        skeleton = build_structure(profile, args.vocal)
        print("\n" + "=" * 72)
        print("↓ 아래는 Suno의 Lyrics 칸에 붙여넣으세요 (구조 지시)")
        print("=" * 72 + "\n")
        print(skeleton)
        out_text += "\n\n--- LYRICS BOX ---\n\n" + skeleton

    if args.out:
        Path(args.out).write_text(out_text, encoding="utf-8")
        print(f"\n저장: {args.out}")


if __name__ == "__main__":
    main()
