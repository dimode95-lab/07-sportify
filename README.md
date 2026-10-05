# Sportify — 취향 분석에서 음악 생성까지

내가 좋아하는 음악을 데이터로 수집하고, 그 취향을 **스타일 프로필**로 언어화해서,
Suno 같은 생성 도구에 넣을 프롬프트를 만든다.

```
[수집] 좋아요 곡·장르 → [분석] 리포트 → [정의] 스타일 프로필 → [생성] Suno 프롬프트 → [검증] 로그 → 프로필 개선
```

## 설치

```powershell
pip install -r requirements.txt
# .env 에 SPOTIPY_CLIENT_ID / SPOTIPY_CLIENT_SECRET / SPOTIPY_REDIRECT_URI / LASTFM_API_KEY
```

## 1) 수집

```powershell
python get_liked_songs.py         # 좋아요 곡 → liked_songs.json  (--csv 옵션)
python fetch_artist_genres.py     # 아티스트 장르 → artist_genres.json (중단 후 재실행하면 이어서)
```

## 2) 분석

```powershell
python analyze_liked_songs.py --top 25   # 콘솔: 추이 / 아티스트 / 장르
python generate_report.py                # report.html (차트 포함)
python artist_detail.py PEPPERTONES      # 아티스트 심층 — 앨범·연대·길이 분포
python genre_detail.py "dream pop" shoegaze   # 장르 클러스터 심층
```

`artist_detail` / `genre_detail` 은 **스타일 프로필을 쓰기 위한 재료**를 뽑는 도구다.
발매 연대 분포와 곡 길이 중앙값이 특히 중요한데, "어느 시기 사운드를 좋아하는가"와
"편곡이 전개되는 긴 곡을 좋아하는가"를 알려주기 때문이다.

## 3) 정의 — 스타일 프로필

`styles/<이름>.yaml` 파일 하나가 스타일 하나. 항목 설명은 [styles/_SCHEMA.md](styles/_SCHEMA.md).

```powershell
python make_prompt.py --list      # 프로필 목록
python validate_styles.py         # 전 프로필 형식 검증
python style_coverage.py          # 프로필이 내 라이브러리를 얼마나 덮는지 + 남은 공백
```

프로필은 AI가 데이터를 근거로 초안을 쓰고, **사용자가 생성 결과를 듣고 교정한다.**
교정된 프로필이 이 프로젝트의 진짜 자산이다.

### 프로필의 음향 특성 실측

프로필의 수치는 AI가 쓰면 추측이다. iTunes 30초 미리듣기를 받아 실제로 잰다.

```powershell
python measure_audio.py --artist PEPPERTONES     # 밝기·에너지·음밀도·조성 측정
python measure_audio.py --genre shoegaze --limit 60
python check_profile_numbers.py                  # 프로필별 실측 특성 비교
```

측정은 `audio_features.json` 에 누적되고, 다시 실행하면 안 잰 곡만 이어서 잰다.

**⚠ BPM은 신뢰하지 말 것.** 226곡을 측정해 검증한 결과, 6개 아티스트의 BPM
중앙값이 전부 118로 같게 나왔다. librosa의 기본 템포 사전확률이 120 BPM 중심이라
음악이 아니라 사전확률을 출력한 것이다. 아티스트 판별력(그룹간분산÷그룹내분산)이
**0.00** 이었고, 균등 사전확률로 바꿔도 옥타브 오차 방향만 바뀌었다.
30초 클립 자동 템포 검출은 이 용도에 부적합하다. BPM은 직접 판단할 것.

**신뢰할 수 있는 항목** — 신호에서 직접 나오고 아티스트를 실제로 구분한다:

| 항목 | 뜻 | 판별력 |
|---|---|---|
| 밝기 (spectral centroid) | 음색의 날카로움 | 0.25 |
| 음 밀도 (onset rate) | 편곡의 빽빽함 | 0.21 |
| 에너지 (RMS) | 믹스의 꽉 찬 정도 | 0.15 |

실측 예 — 직관과 일치한다:

```
밝은 순   실리카겔(2319Hz) > 페퍼톤스(2243) > 넬(2151) > 드림팝(1968) > 검정치마(1669)
빽빽한 순  페퍼톤스(4.2/초) > 넬(3.9) > 드림팝(3.7) > 검정치마(3.1) > 실리카겔(2.9)
```

## 4) 생성 — Suno 프롬프트

```powershell
python make_prompt.py peppertones --key A --intro harmonics --vocal humming --demo
python make_prompt.py peppertones --compact          # 짧은 버전 (~1200자)
python make_prompt.py peppertones -o prompt.txt      # 파일로 저장
```

| 옵션 | 값 |
|---|---|
| `--key` | 시작 조성 (A, C, G …) |
| `--intro` | `harmonics` / `acoustic` / `riff` / `band` / `none` |
| `--vocal` | `lyrics` / `humming` / `instrumental` |
| `--demo` | 데모 파일을 함께 업로드할 때 (멜로디 보존 지시 추가) |
| `--compact` | Suno 입력창 길이 제한에 맞춘 압축 버전 |
| `--structure` | Suno **가사 칸**에 넣을 `[Intro]`/`[Verse]` 구조 스켈레톤도 출력 |

전체 버전은 4,000~5,700자라 Suno 스타일 칸에 안 들어갈 수 있다. 그럴 때 `--compact`.
`--structure` 는 별도로 가사 칸에 붙여넣는다 — Suno가 대괄호 섹션 태그와
괄호 안 연주 지시를 읽기 때문에, 기승전결을 산문이 아니라 구조로 전달할 수 있다.

## 5) 검증 — 생성 로그

들어보고 기록하면, 그 메모가 프로필을 고치는 근거가 된다.

```powershell
python log_generation.py peppertones --score 4 --note "베이스가 얌전함. 코러스는 좋았음"
python log_generation.py --show
```

## 6) 주간 한줄평 — 모바일 앱

한 주 동안 새로 좋아요한 곡에 폰에서 한줄평을 남긴다. 좋아한 이유를 언어화한
기록이라, 스타일 프로필을 교정할 때 데이터가 못 잡는 부분(리프·훅·공간감 같은
인상)을 채워주는 재료가 된다.

별점은 **0.5~5점, 0.5점 간격**이다. 별의 왼쪽 절반은 반 점, 오른쪽 절반은 온 점으로
선택한다. 별점과 한줄평은 각각 단독으로도 저장할 수 있으며, 지난 기록에서 수정할 수 있다.
기존 한줄평의 평점은 미평가로 유지된다.

- 앱: https://dimode95-lab.github.io/sportify-review/ (코드: `review-app/`, 설치: [SETUP.md](SETUP.md))
- 저장: Google Sheets (Apps Script 웹 앱, 코드: `apps_script/Code.gs`)

```powershell
python fetch_reviews.py      # 한줄평 데이터 → reviews.json
```

별점 입력·기존 시트 호환 검증은 저장소 루트에서 `node --test tests/review-rating.test.cjs`로 실행한다.

## 스타일 프로필 목록

| 프로필 | 스타일 | 중심 아티스트 |
|---|---|---|
| `peppertones` | 청량 기타팝 | 페퍼톤스 (70곡) |
| `korean_modern_rock` | 공간감 있는 한국 모던록 | 넬 (52곡) |
| `dreampop_shoegaze` | 한국형 드림팝/슈게이즈 | 의미있는 돌, 새소년, SURL (359곡) |
| `lofi_indie_pop` | 로파이 인디팝 | 검정치마 (37곡) |
| `singer_songwriter` | 어쿠스틱 싱어송라이터 | 적재, 백예린, John Mayer (292곡) |
| `alt_hiphop_soul` | 재지 소울 얼터너티브 힙합 | Mac Miller, 자이언티, 빈지노 (477곡) |
| `jrock_bandpop` | 현대 일본 밴드팝/록 | 히게단 (191곡) |
| `experimental_psych` | 실험적 사이키델릭 밴드 | 실리카겔 (35곡) |
| `kr_rock_2000s` | 2000년대 한국 얼터너티브/누메탈 | 서태지 (42곡) |
| `postrock_instrumental` | 포스트록 인스트루멘털 | BrokenTeeth, Sigur Rós, toe (80곡) |
| `hardcore_punk` | 멜로딕 하드코어/펑크 | SKIPJACK (33곡) |
| `jazz_funk` | 재즈펑크/그루브 | Cory Wong, DAYBREAK (45곡) |

## 참고

- 곡 특성(BPM·에너지 등) Spotify `audio-features` API는 2024년 11월 이후 신규 앱에 차단됨.
  대안은 iTunes 30초 미리듣기 + librosa 직접 분석, 또는 ReccoBeats 같은 서드파티.
- 기승전결·세션·레이어 같은 시간축 분석은 전곡 음원이 있어야 가능.
- `style_coverage.py` 의 "느슨" 수치는 `indie`·`rock` 같은 넓은 태그 때문에 과다 계상된다.
  프로필의 실제 고유 영역은 "고유" 열을 볼 것.
- `.env`, `.cache`, 수집 데이터는 `.gitignore`에 등록됨.
