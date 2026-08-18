# 이번주 한줄평 — 설치 가이드

앱 주소: **https://dimode95-lab.github.io/sportify-review/**

## 진행 상황 (2026-08-16)

| 단계 | 상태 |
|---|---|
| 0. 앱 배포 (GitHub Pages) | ✅ 완료 |
| 1. Spotify 리다이렉트 주소 등록 | ✅ 완료 |
| 2. Google Sheets 저장 서버 (버전 2 배포됨) | ✅ 완료 |
| 3. 폰에 설치 | ⬜ **남음** |

0~2단계는 검증까지 끝났다 — 저장 서버 왕복(쓰기·읽기), 잘못된 토큰 거부,
PC 수집(`fetch_reviews.py`), spotipy 인증 모두 확인. 아래 3단계만 하면 된다.

Spotify에 등록된 리다이렉트 주소는 두 개다.
`https://dimode95-lab.github.io/sportify-review/` (폰 앱)과
`http://127.0.0.1:8888/callback` (PC의 `get_liked_songs.py` 등). 둘 다 필요하니 지우지 말 것.

---

## 0단계 — 앱 웹에 올리기 (완료)

코드는 `review-app/` 에 커밋까지 끝나 있다. 저장소 생성만 직접 실행하면 된다.
(공개 저장소로 만드는 건 무료 계정에서 GitHub Pages를 쓰기 위해서다. 코드에 비밀값은 없다 —
client ID는 공개 식별자이고, Apps Script URL·비밀 토큰은 폰에서 입력하는 값이라 저장소에 없다.)

```bash
cd "/c/Users/dimod/Desktop/dev/07. Sportify/review-app" && gh repo create sportify-review --public --source=. --push
```

이어서 GitHub Pages 켜기:

```bash
gh api --method POST /repos/dimode95-lab/sportify-review/pages -f "source[branch]=main" -f "source[path]=/"
```

1~2분 뒤 위 앱 주소가 열린다.

## 1단계 — Spotify에 앱 주소 등록 (완료)

Spotify가 로그인 후 우리 앱으로 돌아오는 걸 허용하려면 주소를 등록해야 한다.

1. https://developer.spotify.com/dashboard 접속 → 기존 앱 선택
2. **Settings** → **Redirect URIs** 항목에 아래 주소를 추가하고 저장:
   ```
   https://dimode95-lab.github.io/sportify-review/
   ```
   (마지막 `/`까지 정확히 입력 — 한 글자라도 다르면 로그인이 안 된다)

## 2단계 — Google Sheets 저장 서버 만들기 (완료)

한줄평이 저장될 스프레드시트와, 앱이 거기에 쓸 수 있게 해주는 작은 서버를 만든다.

1. https://sheets.new 에서 새 스프레드시트 생성 (이름 예: `한줄평`)
2. 메뉴 **확장 프로그램 → Apps Script** 클릭
3. 편집기에 있는 기본 코드를 전부 지우고, 이 프로젝트의
   [apps_script/Code.gs](apps_script/Code.gs) 파일 내용을 통째로 붙여넣기
4. 코드 위쪽의 `CHANGE_ME` 를 아래 비밀 토큰으로 교체:
   ```
   bcG71PAmsjwORZNRL1Jsu5gWQt1QgdWtjgQGg50Zt10
   ```
   (이미 `.env` 의 `REVIEW_API_SECRET` 에도 같은 값을 넣어뒀다)
5. 오른쪽 위 **배포 → 새 배포** → 톱니바퀴에서 유형 **웹 앱** 선택:
   - 설명: 아무거나 (예: v1)
   - 실행 계정: **나**
   - 액세스 권한: **모든 사용자**  ← 중요 (비밀 토큰이 있어야만 실제로 쓸 수 있으니 안전)
6. **배포** 클릭 → "액세스 승인" → 내 구글 계정 선택
   - "확인되지 않은 앱" 경고가 나오면: **고급 → (프로젝트 이름)(안전하지 않음)으로 이동** 클릭
     (내가 방금 만든 코드라서 나오는 표준 경고다)
7. 나오는 **웹 앱 URL** (`https://script.google.com/macros/s/…/exec`)을 복사해서:
   - `.env` 의 `REVIEW_API_URL=` 뒤에 붙여넣기
   - 폰 앱의 ⚙ 설정에도 입력 (3단계에서)

> 나중에 Code.gs를 수정하면 **배포 → 배포 관리 → 연필 아이콘 → 버전: 새 버전 → 배포**
> 를 해야 반영된다 (그냥 저장만 하면 반영 안 됨).

## 3단계 — 폰에 설치 (3분) ← 여기만 남음

1. 안드로이드 폰 Chrome에서 https://dimode95-lab.github.io/sportify-review/ 열기
2. ⚙ 설정 버튼 → 아래 두 값을 입력 → **연결 테스트** → "연결 성공 ✓" 확인 후 저장

   저장 서버 주소:
   ```
   https://script.google.com/macros/s/AKfycbyT1YfUDWA_0gokn3diXN2AAfe9Wry4Sd-w_EhYXfJWMadOLrMMu5GrgQzFA3mVMnjp/exec
   ```
   비밀 토큰:
   ```
   bcG71PAmsjwORZNRL1Jsu5gWQt1QgdWtjgQGg50Zt10
   ```
3. **Spotify로 로그인** → 권한 동의 (최초 1회)
4. Chrome 메뉴(⋮) → **홈 화면에 추가** → 앱 아이콘 생성 완료

---

## 이후 매주 쓰는 법

- **폰**: 앱 열기 → 이번 주 새 좋아요 곡이 자동으로 뜸 → 한 줄씩 쓰고 저장
- **PC**: 한줄평 데이터를 분석 파이프라인으로 가져오려면:
  ```powershell
  python fetch_reviews.py    # → reviews.json
  ```
- 시트를 직접 열어 확인·수정해도 된다 (데이터는 `reviews` 탭에 쌓인다)

## 문제가 생기면

| 증상 | 확인할 것 |
|---|---|
| 로그인이 안 됨 (INVALID_CLIENT 등) | 1단계 Redirect URI가 정확한지 (끝 `/` 포함) |
| 로그인은 되는데 곡이 안 뜸 | Spotify 계정이 Premium인지, 대시보드 앱의 User Management에 내 계정이 있는지 |
| 연결 테스트 실패 (unauthorized) | Code.gs의 SECRET과 앱 설정의 비밀 토큰이 같은지 |
| 연결 테스트 실패 (기타) | 2단계 5에서 액세스 권한이 "모든 사용자"인지, 새 버전 배포를 했는지 |
