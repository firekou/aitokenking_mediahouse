#!/usr/bin/env python3
"""目錄管線回歸測試（schema ＋ SQL 產生器）。

這裡鎖的六件事，每一件都是「錯了不會報錯，只會安靜地給出錯誤結論」的那一類。
"""
import json
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "schemas" / "reel-catalog.sql"
FIXTURE = ROOT / "scripts" / "fixtures" / "reels-fixture.json"

_t = []
def t(name):
    def d(fn):
        _t.append((name, fn)); return fn
    return d


def build(extra=None, fixture=None):
    d = tempfile.mkdtemp()
    cmd = [sys.executable, str(ROOT / "scripts" / "build_catalog_sql.py"),
           str(fixture or FIXTURE), "--outdir", d] + (extra or [])
    r = subprocess.run(cmd, capture_output=True, text=True)
    return Path(d), r


def db(d, with_tr=True):
    c = sqlite3.connect(":memory:")
    c.executescript(SCHEMA.read_text())
    c.executescript((d / "catalog.sql").read_text())
    p = d / "transcripts.sql"
    if with_tr and p.exists():
        c.executescript(p.read_text())
    return c


@t("schema 可建立，四表兩視圖齊備")
def _():
    c = sqlite3.connect(":memory:"); c.executescript(SCHEMA.read_text())
    got = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view')")}
    need = {"ig_harvest_run", "ig_reel", "ig_reel_transcript", "v_reel_catalog", "v_pipeline_queue"}
    assert need <= got, need - got


@t("★ 逐字稿預設分檔 —— catalog.sql 內不得出現任何逐字稿")
def _():
    d, _r = build()
    assert (d / "transcripts.sql").exists(), "逐字稿檔未產生"
    cat = (d / "catalog.sql").read_text()
    assert "ig_reel_transcript" not in cat, (
        "catalog.sql 混進了逐字稿。拆兩個檔，「不發布逐字稿」才是做得到的操作而不是口號。")


@t("--publish-transcripts 才合併 —— 推翻紀律必須是顯式動作")
def _():
    d, _r = build(["--publish-transcripts"])
    assert "ig_reel_transcript" in (d / "catalog.sql").read_text()
    assert not (d / "transcripts.sql").exists()


@t("★ 計費分鐘無條件進位 —— 109 秒是 2 個計費分鐘不是 1.8 個")
def _():
    c = db(build()[0])
    got = dict(c.execute("SELECT shortcode, billed_minutes FROM ig_reel"))
    assert got["FIXTURE0001"] == 2, got   # 109s
    assert got["FIXTURE0002"] == 2, got   # 61s
    assert got["FIXTURE0003"] == 1, got   # 30s


@t("★ cost_actual_usd 必須是 NULL 不是 0 —— 0 看起來像量測結果")
def _():
    c = db(build()[0])
    est, act = c.execute("SELECT cost_estimate_usd, cost_actual_usd FROM ig_harvest_run").fetchone()
    assert est is not None and act is None, (est, act)


@t("★ 沒拿到逐字稿記為 missing，不得靜默當成「這支沒有字幕」")
def _():
    c = db(build()[0])
    miss = c.execute("SELECT transcripts_missing FROM ig_harvest_run").fetchone()[0]
    assert miss == 1, miss
    n = c.execute("SELECT COUNT(*) FROM ig_reel_transcript").fetchone()[0]
    assert n == 2, n


@t("★ 指標缺值存 NULL 不存 0 —— 「沒看到」與「是零」不可混淆")
def _():
    c = db(build()[0])
    v = c.execute("SELECT views FROM ig_reel WHERE shortcode='FIXTURE0002'").fetchone()[0]
    assert v is None, f"缺值被寫成 {v!r}"
    # 同一張表裡，「沒看到」與「真的是零」必須並存且可區分：
    # FIXTURE0002 的 views 缺值 → NULL；同一列的 comments 真的是 0 → 必須存 0。
    z = c.execute("SELECT comments FROM ig_reel WHERE shortcode='FIXTURE0002'").fetchone()[0]
    assert z == 0, f"真正的 0 被吃掉了，存成 {z!r}"


@t("SQL 跳脫：單引號與換行必須完整還原")
def _():
    c = db(build()[0])
    cap = c.execute("SELECT caption FROM ig_reel WHERE shortcode='FIXTURE0001'").fetchone()[0]
    assert "it's" in cap and "\n" in cap, repr(cap)
    tr = c.execute("SELECT transcript FROM ig_reel_transcript WHERE shortcode='FIXTURE0001'").fetchone()[0]
    assert "don't" in tr and ";" in tr, repr(tr)


@t("外部不可信標記必須跟著資料走")
def _():
    c = db(build()[0])
    assert c.execute("SELECT content_trust FROM ig_reel LIMIT 1").fetchone()[0] == "untrusted_external"
    assert c.execute("SELECT content_trust FROM ig_reel_transcript LIMIT 1").fetchone()[0] == "untrusted_external"
    assert c.execute("SELECT asr_reviewed FROM ig_reel_transcript LIMIT 1").fetchone()[0] == 0


@t("揭露文字必須進 DB —— 享用資料就要印出它怎麼來的")
def _():
    c = db(build()[0])
    disc = c.execute("SELECT disclosure FROM ig_harvest_run").fetchone()[0]
    assert "Apify" in disc and "robots.txt" in disc, disc


@t("★ 空輸入不得產出看起來正常的空 SQL")
def _():
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump({"account": "x", "harvested_at": "2026-01-01T00:00:00Z", "reels": []}, f)
        p = f.name
    d, r = build(fixture=Path(p))
    assert r.returncode != 0, "空輸入竟然回 0 —— 空 SQL 看起來會跟「真的沒有影片」一樣"
    assert not (d / "catalog.sql").exists()


@t("★★ 來源層必須拆逐字稿 —— raw-reels.json 不得含任何逐字稿內容")
def _():
    # 這條漏過一次：SQL 層拆了，但 raw-reels.json 仍帶著全部逐字稿，
    # 而它是要進 git 的 —— 等於從後門違反 §來源紀律。
    sys.path.insert(0, str(ROOT / "scripts"))
    import ig_harvest
    payload = {"reels": [
        {"shortcode": "A", "transcript": "機密逐字稿內容"},
        {"shortcode": "B", "transcript": None},
    ]}
    clean, trs = ig_harvest.split_transcripts(payload)
    dumped = json.dumps(clean, ensure_ascii=False)
    assert "機密逐字稿內容" not in dumped, "逐字稿留在 raw-reels.json 裡了"
    assert trs == {"A": "機密逐字稿內容"}
    assert clean["reels"][0]["has_transcript"] is True
    assert clean["reels"][1]["has_transcript"] is False, "沒有逐字稿的也要標記，不得省略"


@t("★ 分離後的逐字稿檔必須被 .gitignore 覆蓋")
def _():
    ig = (ROOT / ".gitignore").read_text()
    for pat in ("raw-transcripts.json", "transcripts.sql"):
        assert pat in ig, f"{pat} 沒有被 .gitignore 覆蓋"


@t("★ 採集器預設不花錢：沒有 --run 一定不送出")
def _():
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "ig_harvest.py"),
                        "example.invalid", "--limit", "5"], capture_output=True, text=True)
    assert "乾跑結束" in r.stdout or "未設定 APIFY_TOKEN" in r.stdout, r.stdout[-300:]
    assert "run-sync" not in r.stdout


@t("★ 不對稱開關：--with-transcript 單獨給不足以放行")
def _():
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "ig_harvest.py"),
                        "example.invalid", "--with-transcript"], capture_output=True, text=True)
    assert r.returncode == 2 and "第二個旗標" in r.stdout, r.stdout[-300:]


def main():
    p = f_ = 0
    for name, fn in _t:
        try:
            fn(); print(f"  PASS  {name}"); p += 1
        except AssertionError as e:
            print(f"  FAIL  {name}\n        {e}"); f_ += 1
    print(f"\n{p}/{p+f_} 通過")
    return 1 if f_ else 0


if __name__ == "__main__":
    sys.exit(main())
