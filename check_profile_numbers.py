"""프로필별 음향 특성을 실측값과 대조한다.

⚠ BPM은 신뢰할 수 없어 제외한다. 30초 클립 자동 템포 검출은 옥타브 모호성이 크고,
librosa 기본 사전확률(120 BPM 중심)에 끌려간다. 실제로 검증한 결과 6개 아티스트의
BPM 중앙값이 전부 118로 같게 나왔고, 판별력(그룹간분산÷그룹내분산)이 0.00이었다.
균등 사전확률로 바꿔도 오차 방향만 바뀔 뿐 해결되지 않았다.

신뢰할 수 있는 항목 — 신호에서 직접 나오고 아티스트를 실제로 구분함:
  밝기(spectral centroid)  판별력 0.25
  에너지(RMS)              판별력 0.15
  음 밀도(onset rate)       판별력 0.21

사용법:
    python check_profile_numbers.py
"""

import argparse
import json
from pathlib import Path

import numpy as np
import yaml

from analyze_liked_songs import load_genres, load_songs, song_genres

STYLES_DIR = Path("styles")
FEATURES_FILE = Path("audio_features.json")


def profile_rows(songs: list[dict], feats: dict, prof: dict, genre_map: dict) -> list[dict]:
    """이 프로필에 해당하는 실측 결과. match_artists 우선, 없으면 genre_tags."""
    g = prof.get("grounding") or {}
    artists = [a.lower() for a in (g.get("match_artists") or [])]
    tags = {t.lower() for t in g.get("genre_tags", [])}

    rows = []
    for s in songs:
        if artists:
            if not any(a in (s.get("artists") or "").lower() for a in artists):
                continue
        elif not (song_genres(s, genre_map) & tags):
            continue
        f = feats.get(s.get("id"))
        if f:
            rows.append(f)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="프로필별 실측 음향 특성")
    parser.add_argument("--min-samples", type=int, default=8, help="최소 표본 수 (기본 8)")
    args = parser.parse_args()

    if not FEATURES_FILE.exists():
        print("audio_features.json 이 없습니다. 먼저 measure_audio.py 를 실행하세요.")
        return

    feats = json.loads(FEATURES_FILE.read_text(encoding="utf-8"))
    songs = load_songs()
    genre_map = load_genres()
    n_measured = sum(1 for v in feats.values() if v)

    print(f"■ 프로필별 실측 음향 특성 (실측 {n_measured}곡)\n" + "=" * 74)
    print(f"{'프로필':<24} {'밝기 Hz':>10} {'에너지':>10} {'음밀도/초':>10} {'표본':>6}")
    print("-" * 74)

    measured = []
    for path in sorted(STYLES_DIR.glob("*.yaml")):
        prof = yaml.safe_load(path.read_text(encoding="utf-8"))
        rows = profile_rows(songs, feats, prof, genre_map)
        if len(rows) < args.min_samples:
            print(f"{path.stem:<24} {'-':>10} {'-':>10} {'-':>10} {len(rows):>6}  표본 부족")
            continue
        b = np.median([r["brightness_hz"] for r in rows])
        e = np.median([r["energy_rms"] for r in rows])
        o = np.median([r["onset_rate"] for r in rows])
        measured.append((path.stem, b, e, o))
        print(f"{path.stem:<24} {b:>10.0f} {e:>10.3f} {o:>10.1f} {len(rows):>6}")

    if len(measured) >= 2:
        print("\n■ 상대적 위치 — 측정된 프로필끼리 비교\n" + "-" * 74)
        for label, idx, unit in [("밝은 순", 1, "Hz"), ("강한 순", 2, ""), ("빽빽한 순", 3, "/초")]:
            order = sorted(measured, key=lambda m: -m[idx])
            val = lambda m: f"{m[idx]:.3f}" if idx == 2 else f"{m[idx]:.0f}"
            print(f"  {label:<8} " + " > ".join(f"{m[0]}({val(m)}{unit})" for m in order))

    print("\n" + "=" * 74)
    print("※ BPM은 이 도구에서 제외했습니다. 30초 클립 자동 템포 검출은 옥타브 모호성과")
    print("   사전확률 편향 탓에 아티스트를 구분하지 못했습니다(판별력 0.00).")
    print("   프로필의 BPM 값은 합주 경험으로 직접 판단하시는 게 정확합니다.")
    print("※ 밝기는 음색의 날카로움, 에너지는 믹스의 꽉 찬 정도, 음밀도는 편곡의 빽빽함.")


if __name__ == "__main__":
    main()
