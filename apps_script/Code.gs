/**
 * 이번주 한줄평 — Google Sheets 백엔드 (Apps Script 웹 앱)
 *
 * 설치는 SETUP.md 참고. 요약:
 *   1) Google Sheets 새 문서 → 확장 프로그램 → Apps Script → 이 파일 내용 붙여넣기
 *   2) 아래 SECRET 값을 SETUP.md에 적힌 값으로 교체
 *   3) 배포 → 새 배포 → 웹 앱 (실행: 나, 액세스: 모든 사용자) → URL 복사
 */

const SECRET = "CHANGE_ME"; // ← SETUP.md의 비밀 토큰으로 교체
const SHEET_NAME = "reviews";
const TIMEZONE = "Asia/Seoul";
const HEADERS = ["saved_at", "added_at", "track_id", "track_name", "artists", "album", "release_date", "review", "spotify_url"];

function getSheet_() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sh = ss.getSheetByName(SHEET_NAME);
  if (!sh) sh = ss.insertSheet(SHEET_NAME);
  if (sh.getLastRow() === 0) {
    sh.appendRow(HEADERS);
    sh.setFrozenRows(1);
  }
  return sh;
}

function json_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

/** 시트는 값을 제멋대로 해석한다 — '='로 시작하면 수식으로 삼고,
 *  "2005-11-10" 같은 문자열은 날짜 객체로 바꿔버린다(읽을 때 하루 어긋난다).
 *  보낸 문자열이 그대로 돌아오도록 전부 텍스트로 못박는다.
 *  (앞에 붙인 작은따옴표는 표시용 접두사라 getValues로 읽을 땐 사라진다) */
function literal_(v) {
  return "'" + (v == null ? "" : String(v));
}

/** 저장 시각을 현지 시각(+09:00)으로 기록한다.
 *  UTC로 적으면 밤 9시 이후에 쓴 한줄평이 전날 날짜로 보인다. */
function nowLocal_() {
  return Utilities.formatDate(new Date(), TIMEZONE, "yyyy-MM-dd'T'HH:mm:ssXXX");
}

// 브라우저로 URL을 직접 열었을 때 안내
function doGet() {
  return json_({ ok: true, message: "이번주 한줄평 저장 서버입니다. 앱에서 POST로 사용하세요." });
}

function doPost(e) {
  let body;
  try {
    body = JSON.parse(e.postData.contents);
  } catch (err) {
    return json_({ ok: false, error: "invalid JSON" });
  }
  // SECRET을 아직 안 바꿨으면(짧으면) 무조건 거부한다.
  // 자리표시자 문자열을 여기서 다시 쓰지 않는 건, 토큰을 찾아 바꿀 때
  // 이 줄까지 같이 바뀌어 검사가 항상 참이 되는 사고를 막기 위해서다.
  if (!body || SECRET.length < 16 || body.secret !== SECRET) {
    return json_({ ok: false, error: "unauthorized" });
  }

  try {
    const sh = getSheet_();
    switch (body.action) {
      case "ping":
        return json_({ ok: true, message: "pong", reviews: Math.max(0, sh.getLastRow() - 1) });

      case "ids": {
        const n = sh.getLastRow() - 1;
        const ids = n > 0 ? sh.getRange(2, 3, n, 1).getValues().map(function (r) { return String(r[0]); }) : [];
        return json_({ ok: true, ids: ids });
      }

      case "list": {
        const n = sh.getLastRow() - 1;
        if (n <= 0) return json_({ ok: true, reviews: [] });
        const limit = Math.min(Number(body.limit) || 100, 5000);
        const rows = sh.getRange(2, 1, n, HEADERS.length).getValues();
        const out = rows.map(function (r) {
          const obj = {};
          HEADERS.forEach(function (h, i) {
            obj[h] = r[i] instanceof Date ? r[i].toISOString() : r[i];
          });
          return obj;
        });
        // 같은 곡을 다시 저장하면 원래 행이 갱신되므로 행 순서 ≠ 최신순.
        // 저장 시각으로 직접 정렬해야 "최근 기록"이 실제로 최근이 된다.
        out.sort(function (a, b) { return String(b.saved_at).localeCompare(String(a.saved_at)); });
        return json_({ ok: true, reviews: out.slice(0, limit) });
      }

      case "add": {
        const reviews = Array.isArray(body.reviews) ? body.reviews : [];
        // 동시에 두 번 저장돼도 시트가 꼬이지 않도록 잠금
        const lock = LockService.getScriptLock();
        lock.waitLock(10000);
        try {
          const n0 = sh.getLastRow() - 1;
          const idCol = n0 > 0 ? sh.getRange(2, 3, n0, 1).getValues().map(function (r) { return String(r[0]); }) : [];
          let added = 0, updated = 0;
          const now = nowLocal_();
          for (let k = 0; k < reviews.length; k++) {
            const rv = reviews[k];
            if (!rv || !rv.track_id || !String(rv.review || "").trim()) continue;
            const row = [
              literal_(now),
              literal_(rv.added_at),
              literal_(rv.track_id),
              literal_(rv.name),
              literal_(rv.artists),
              literal_(rv.album),
              literal_(rv.release_date),
              literal_(String(rv.review).trim()),
              literal_(rv.url),
            ];
            const idx = idCol.indexOf(String(rv.track_id));
            if (idx >= 0) {
              // 같은 곡을 다시 저장하면 새 한줄평으로 갱신
              sh.getRange(idx + 2, 1, 1, HEADERS.length).setValues([row]);
              updated++;
            } else {
              sh.appendRow(row);
              idCol.push(String(rv.track_id));
              added++;
            }
          }
          return json_({ ok: true, added: added, updated: updated });
        } finally {
          lock.releaseLock();
        }
      }

      default:
        return json_({ ok: false, error: "unknown action: " + body.action });
    }
  } catch (err) {
    return json_({ ok: false, error: String(err) });
  }
}
