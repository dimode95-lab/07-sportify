"""iTunes 30초 미리듣기를 받아 곡의 음향 특성을 실측한다.

프로필의 BPM·조성·질감 수치를 AI 추측이 아니라 측정값으로 바꾸기 위한 도구.
측정 항목: BPM, 추정 조성, 밝기(spectral centroid), 에너지(RMS), 음 밀도(onset rate).

결과는 audio_features.json 에 누적 저장되며, 다시 실행하면 안 잰 곡만 이어서 잰다.

사용법:
    python measure_audio.py --artist PEPPERTONES
    python measure_audio.py --genre shoegaze --limit 60
    python measure_audio.py --artist NELL --stats-only     # 이미 잰 것만 통계
"""

import argparse
import json
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np

OUT_FILE = Path("audio_features.json")
ITUNES = "https://itunes.apple.com/search"

# Krumhansl-Schmuckler 조성 프로파일 (장조/단조)
KS_MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
KS_MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
PITCHES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def itunes_preview(artist: str, title: str) -> str | None:
    """곡명으로 iTunes 미리듣기 URL을 찾는다."""
    q = urllib.parse.urlencode(
        {"term": f"{artist} {title}", "media": "music", "entity": "song", "limit": 1}
    )
    try:
        with urllib.request.urlopen(f"{ITUNES}?{q}", timeout=15) as r:
            data = json.load(r)
    except Exception:
        return None
    results = data.get("results") or []
    return results[0].get("previewUrl") if results else None


def decode_to_wav(url: str, ffmpeg: str, dest: Path) -> bool:
    """미리듣기 m4a를 받아 모노 22.05kHz wav로 디코딩."""
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            raw = r.read()
    except Exception:
        return False
    src = dest.with_suffix(".m4a")
    src.write_bytes(raw)
    try:
        subprocess.run(
            [ffmpeg, "-y", "-loglevel", "error", "-i", str(src),
             "-ac", "1", "-ar", "22050", str(dest)],
            check=True, capture_output=True, timeout=60,
        )
        return dest.exists()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False
    finally:
        src.unlink(missing_ok=True)


def estimate_key(chroma: np.ndarray) -> str:
    """크로마 평균을 KS 프로파일과 상관시켜 조성 추정."""
    profile = chroma.mean(axis=1)
    if profile.sum() == 0:
        return "?"
    profile = profile / profile.sum()
    best, best_score = "?", -2.0
    for i in range(12):
        for name, ref in (("major", KS_MAJOR), ("minor", KS_MINOR)):
            score = np.corrcoef(np.roll(profile, -i), ref)[0, 1]
            if score > best_score:
                best_score, best = score, f"{PITCHES[i]} {name}"
    return best


def analyze(wav: Path) -> dict | None:
    import librosa

    try:
        y, sr = librosa.load(str(wav), sr=22050, mono=True)
    except Exception:
        return None
    if y.size < sr:  # 1초 미만이면 의미 없음
        return None

    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    tempo = float(np.atleast_1d(tempo)[0])
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    centroid = float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)))
    rms = float(np.mean(librosa.feature.rms(y=y)))
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    onsets = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr)
    duration = len(y) / sr

    return {
        "bpm": round(tempo, 1),
        "key": estimate_key(chroma),
        "brightness_hz": round(centroid),          # 높을수록 밝은/날카로운 음색
        "energy_rms": round(rms, 4),               # 높을수록 큰/꽉 찬 사운드
        "onset_rate": round(len(onsets) / duration, 2),  # 초당 음 시작 — 편곡 밀도
    }


def pick_songs(args) -> list[dict]:
    from analyze_liked_songs import load_genres, load_songs, song_genres

    songs = load_songs()
    if args.artist:
        key = args.artist.lower()
        hits = [s for s in songs if key in (s.get("artists") or "").lower()]
    elif args.genre:
        genre_map = load_genres()
        target = {args.genre.lower()}
        hits = [s for s in songs if song_genres(s, genre_map) & target]
    else:
        sys.exit("--artist 또는 --genre 중 하나를 지정하세요.")

    # 중복 제목 제거 (리마스터·라이브 중복)
    seen, uniq = set(), []
    for s in hits:
        k = (s.get("name", "").lower(), s.get("artists", "").lower())
        if k not in seen:
            seen.add(k)
            uniq.append(s)
    return uniq[: args.limit]


def show_stats(feats: dict, songs: list[dict], title: str) -> None:
    rows = [feats[s["id"]] for s in songs if s.get("id") in feats and feats[s["id"]]]
    if not rows:
        print("측정된 곡이 없습니다.")
        return

    def q(vals, p):
        return float(np.percentile(vals, p))

    bpms = sorted(r["bpm"] for r in rows)
    print(f"\n■ {title} — 실측 {len(rows)}곡\n" + "=" * 68)
    print(f"  BPM ⚠      중앙값 {q(bpms,50):.0f}  "
          f"(25~75% 구간 {q(bpms,25):.0f}~{q(bpms,75):.0f}) — 신뢰하지 말 것, 아래 주석 참고")

    bright = [r["brightness_hz"] for r in rows]
    print(f"  밝기        중앙값 {q(bright,50):.0f} Hz  "
          f"(25~75% {q(bright,25):.0f}~{q(bright,75):.0f})")
    energy = [r["energy_rms"] for r in rows]
    print(f"  에너지      중앙값 {q(energy,50):.3f}  "
          f"(25~75% {q(energy,25):.3f}~{q(energy,75):.3f})")
    dens = [r["onset_rate"] for r in rows]
    print(f"  음 밀도     중앙값 {q(dens,50):.1f}/초  "
          f"(25~75% {q(dens,25):.1f}~{q(dens,75):.1f})")

    keys: dict[str, int] = {}
    for r in rows:
        keys[r["key"]] = keys.get(r["key"], 0) + 1
    top = sorted(keys.items(), key=lambda x: -x[1])[:6]
    print(f"  조성 분포   " + ", ".join(f"{k}({v})" for k, v in top))
    print("\n  ⚠ BPM은 신뢰하지 마세요. 검증 결과 6개 아티스트의 중앙값이 전부 118로 같았고")
    print("    (librosa 기본 사전확률이 120 BPM 중심), 아티스트 판별력이 0.00이었습니다.")
    print("    균등 사전확률로 바꿔도 옥타브 오차 방향만 바뀝니다.")
    print("  ※ 밝기·에너지·음밀도는 신호에서 직접 나오는 값이라 신뢰할 수 있습니다")
    print("    (판별력 0.25 / 0.15 / 0.21). 조성도 참고용으로는 쓸 만합니다.")
    print("  ※ 30초 구간 기준이라 곡 전체가 아니라 도입~1절 근처의 특성입니다.")


def main() -> None:
    parser = argparse.ArgumentParser(description="iTunes 미리듣기로 곡 특성 실측")
    parser.add_argument("--artist", help="아티스트명 (부분 일치)")
    parser.add_argument("--genre", help="장르명")
    parser.add_argument("--limit", type=int, default=40, help="최대 측정 곡 수")
    parser.add_argument("--stats-only", action="store_true", help="새로 측정하지 않고 통계만")
    args = parser.parse_args()

    songs = pick_songs(args)
    feats = json.loads(OUT_FILE.read_text(encoding="utf-8")) if OUT_FILE.exists() else {}
    label = args.artist or args.genre

    if not args.stats_only:
        import imageio_ffmpeg

        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        todo = [s for s in songs if s.get("id") and s["id"] not in feats]
        print(f"■ '{label}' 대상 {len(songs)}곡 / 이미 측정 {len(songs)-len(todo)}곡 "
              f"/ 새로 측정 {len(todo)}곡")

        with tempfile.TemporaryDirectory() as tmp:
            wav = Path(tmp) / "clip.wav"
            for i, s in enumerate(todo, 1):
                artist = (s.get("artists") or "").split(",")[0]
                url = itunes_preview(artist, s.get("name", ""))
                time.sleep(0.4)  # iTunes API 예의
                if not url:
                    feats[s["id"]] = None
                    print(f"  [{i}/{len(todo)}] 미리듣기 없음: {s['name'][:40]}")
                    continue
                if not decode_to_wav(url, ffmpeg, wav):
                    feats[s["id"]] = None
                    print(f"  [{i}/{len(todo)}] 디코딩 실패: {s['name'][:40]}")
                    continue
                result = analyze(wav)
                feats[s["id"]] = result
                wav.unlink(missing_ok=True)
                if result:
                    print(f"  [{i}/{len(todo)}] {s['name'][:34]:<36} "
                          f"{result['bpm']:5.1f} BPM  {result['key']}")
                if i % 10 == 0:
                    OUT_FILE.write_text(json.dumps(feats, ensure_ascii=False, indent=2),
                                        encoding="utf-8")

        OUT_FILE.write_text(json.dumps(feats, ensure_ascii=False, indent=2), encoding="utf-8")

    show_stats(feats, songs, label)


if __name__ == "__main__":
    main()
