const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const Review = require("../review-app/review-model.js");

function server(initial) {
  const rows = structuredClone(initial || []);
  const clean = (v) => typeof v === "string" && v.startsWith("'") ? v.slice(1) : v;
  const sheet = {
    getLastRow: () => rows.length,
    appendRow: (row) => rows.push(row.map(clean)),
    setFrozenRows() {},
    getRange(r, c, nr = 1, nc = 1) {
      return {
        getValues: () => Array.from({ length: nr }, (_, y) => Array.from({ length: nc }, (_, x) => rows[r - 1 + y]?.[c - 1 + x] ?? "")),
        setValues(values) { values.forEach((row, y) => { rows[r - 1 + y] ||= []; row.forEach((v, x) => { rows[r - 1 + y][c - 1 + x] = clean(v); }); }); },
        setValue(value) { this.setValues([[value]]); },
      };
    },
  };
  const context = vm.createContext({
    SpreadsheetApp: { getActiveSpreadsheet: () => ({ getSheetByName: () => rows.length ? sheet : null, insertSheet: () => sheet }), flush() {} },
    LockService: { getScriptLock: () => ({ waitLock() {}, releaseLock() {} }) },
    Utilities: { formatDate: () => "2026-10-05T15:00:00+09:00" },
    ContentService: { MimeType: { JSON: "json" }, createTextOutput: (text) => ({ setMimeType: () => JSON.parse(text) }) },
  });
  const code = fs.readFileSync("apps_script/Code.gs", "utf8").replace('const SECRET = "CHANGE_ME"', 'const SECRET = "test-only-review-secret"');
  vm.runInContext(code, context);
  const call = (action, extra = {}) => context.doPost({ postData: { contents: JSON.stringify({ secret: "test-only-review-secret", action, ...extra }) } });
  return { call, rows };
}

test("별의 좌·우·중앙을 0.5~5점으로 판정한다", () => {
  for (let n = 1; n <= 5; n++) {
    assert.equal(Review.pointerRating(n, 110, 100, 48), n - 0.5);
    assert.equal(Review.pointerRating(n, 124, 100, 48), n - 0.5);
    assert.equal(Review.pointerRating(n, 125, 100, 48), n);
    assert.equal(Review.rating(n - 0.5), n - 0.5);
  }
  for (const value of [0, 5.5, 3.2, "3.5", true, Infinity, NaN]) assert.equal(Review.rating(value), null);
  assert.match(Review.stars(3.5)[3], /width:50%/);
});

test("구버전 글과 평점만 있는 임시 기록을 복원한다", () => {
  assert.deepEqual(Review.draft("쓰던 글"), { review: "쓰던 글", rating: null });
  assert.deepEqual(Review.draft({ review: "", rating: 0.5 }), { review: "", rating: 0.5 });
  assert.equal(Review.hasContent(Review.draft({ rating: 0.5 })), true);
  assert.equal(Review.hasContent(Review.draft("  ")), false);
});

test("기존 시트에 열만 추가하고 평점만 저장·조회·수정한다", () => {
  const headers = ["saved_at", "added_at", "track_id", "track_name", "artists", "album", "release_date", "review", "spotify_url"];
  const original = ["2026-08-16", "2026-08-15", "old", "곡", "가수", "앨범", "2005-11-10", "기존 글", "https://open.spotify.com/track/old"];
  const { call, rows } = server([headers, original]);
  assert.equal(call("ping").rating_step, 0.5);
  assert.deepEqual(rows[1], original);
  assert.equal(rows[0][9], "rating");
  assert.equal(call("list").reviews[0].rating, null);
  assert.equal(call("add", { reviews: [{ track_id: "old", rating: 3.5 }] }).updated, 1);
  let r = call("list").reviews[0];
  assert.equal(r.rating, 3.5); assert.equal(r.review, "기존 글"); assert.equal(r.track_name, "곡"); assert.equal(r.release_date, "2005-11-10");
  assert.equal(call("add", { reviews: [{ track_id: "old", review: "=수식이 아닌 감상" }] }).ok, true);
  r = call("list").reviews[0]; assert.equal(r.rating, 3.5); assert.equal(r.review, "=수식이 아닌 감상");
  assert.equal(call("add", { reviews: [{ track_id: "old", rating: null }] }).ok, true);
  assert.equal(call("list").reviews[0].rating, null);
  const payload = { reviews: [{ track_id: "new", name: "새 곡", rating: 0.5, review: "" }] };
  assert.deepEqual(call("add", payload).saved_ids, ["new"]);
  assert.equal(call("add", payload).updated, 1);
  assert.equal(rows.length, 3);
  assert.equal(call("list").reviews.find((x) => x.track_id === "new").rating, 0.5);
});

test("잘못된 평점이나 빈 기록이 섞인 요청은 쓰기 전에 거부한다", () => {
  const { call, rows } = server();
  call("ping");
  for (const rating of [0, 5.5, 3.2, "3.5", true]) {
    const result = call("add", { reviews: [{ track_id: "valid", rating: 4.5 }, { track_id: "invalid", rating }] });
    assert.equal(result.ok, false); assert.equal(rows.length, 1);
  }
  assert.equal(call("add", { reviews: [{ track_id: "empty", review: " ", rating: null }] }).ok, false);
  assert.equal(call("add", { reviews: [{ track_id: "long", review: "글".repeat(301) }] }).ok, false);
  assert.equal(call("add", { reviews: [{ track_id: "same", rating: 1 }, { track_id: "same", rating: 2 }] }).ok, false);
  assert.equal(rows.length, 1);
});

test("예상하지 못한 열 구성은 덮어쓰지 않는다", () => {
  const rows = [["다른 데이터"]];
  const backend = server(rows);
  assert.equal(backend.call("ping").ok, false);
  assert.deepEqual(backend.rows, rows);
});
