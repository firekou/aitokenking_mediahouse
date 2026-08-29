#!/usr/bin/env python3
"""raw-reels.json → SQL。

刻意輸出兩個檔案，而不是一個：

    catalog.sql       run 紀錄 ＋ 網址 ＋ 文案 ＋ 指標   → 可進 git
    transcripts.sql   完整逐字稿                        → 預設 .gitignore

理由與 schema 同一條：CONTRIBUTING.md §來源紀律「不整支影片逐字重製發布」。
合成一個檔，「不發布逐字稿」就只是一句口號；拆兩個檔，它才是一個做得到的操作。

用法：
    python3 scripts/build_catalog_sql.py cases/CASE-002-.../raw-reels.json
    python3 scripts/build_catalog_sql.py <json> --publish-transcripts   # 併進 catalog.sql
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "schemas" / "reel-catalog.sql"


def q(v):
    """SQL 字面值。None → NULL；字串跳脫單引號。"""
    if v is None or v == "":
        return "NULL"
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, (int, float)):
        return repr(v)
    return "'" + str(v).replace("'", "''") + "'"


def billed_minutes(dur):
    """逐字稿計費分鐘。★ 無條件進位 —— 109 秒是 2 個計費分鐘不是 1.8 個。"""
    try:
        return max(1, math.ceil(float(dur) / 60.0)) if dur else None
    except (TypeError, ValueError):
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json_path")
    ap.add_argument("--outdir", help="預設與輸入同目錄")
    ap.add_argument("--publish-transcripts", action="store_true",
                    help="★ 把逐字稿併進 catalog.sql（＝可能進 git）。需自行確認 §來源紀律")
    a = ap.parse_args()

    src = Path(a.json_path)
    if not src.exists():
        print(f"🔴 找不到 {src}")
        print("   ⚠️ 這是輸入缺漏，不是「這個帳號沒有影片」。先跑 scripts/ig_harvest.py")
        return 2

    d = json.loads(src.read_text(encoding="utf-8"))
    reels = d.get("reels", [])

    # 逐字稿在旁邊的獨立檔案（來源層就拆開了）—— 有就併回來，沒有就只出目錄
    tf = src.with_name(d.get("transcripts_file") or "raw-transcripts.json")
    if tf.exists():
        trs = json.loads(tf.read_text(encoding="utf-8")).get("transcripts", {})
        for r in reels:
            if r.get("shortcode") in trs:
                r["transcript"] = trs[r["shortcode"]]
        print(f"  併入 {len(trs)} 筆逐字稿（來源 {tf.name}）")
    elif any(r.get("has_transcript") for r in reels):
        print(f"  ⚠️ 有 {sum(1 for r in reels if r.get('has_transcript'))} 支標記有逐字稿，"
              f"但找不到 {tf.name}")
        print("     → 只產生目錄，不產生 transcripts.sql。"
              "★ 這是「檔案不在」不是「這些片沒有字幕」")
    if not reels:
        print("🔴 輸入檔內 reels 為空 —— 不產生任何 SQL。")
        print("   ⚠️ 空輸入產出空 SQL，看起來會跟「這個帳號真的沒有影片」一模一樣。")
        return 2

    outdir = Path(a.outdir) if a.outdir else src.parent
    outdir.mkdir(parents=True, exist_ok=True)
    run_id = f"{d['account']}@{d['harvested_at']}"
    cov = d.get("coverage", {})

    head = [
        "-- ══════════════════════════════════════════════════════════════",
        f"-- Media House · IG 短影音目錄 —— @{d['account']}",
        f"-- 產生於 {d['harvested_at']}｜actor: {d.get('actor')}",
        f"-- 取得方式：{d.get('collection_method')}",
        "--",
        "-- ⚠️ 揭露（享用資料就要印出它怎麼來的）：",
    ]
    for line in str(d.get("disclosure", "")).split("。"):
        if line.strip():
            head.append(f"--   {line.strip()}。")
    head += [
        "--",
        "-- 先跑 schemas/reel-catalog.sql 建表，再跑本檔。",
        "-- ══════════════════════════════════════════════════════════════",
        "",
        "BEGIN;",
        "",
    ]

    rows = [
        "-- ── 採集批次 ──",
        "INSERT OR REPLACE INTO ig_harvest_run (run_id, account, profile_url, harvested_at,"
        " actor, collection_method, requested_limit, reels_returned, transcripts_returned,"
        " transcripts_missing, cost_estimate_usd, cost_actual_usd, latency_s, disclosure)",
        "VALUES (" + ", ".join(q(x) for x in [
            run_id, d["account"], d.get("profile_url"), d["harvested_at"], d.get("actor"),
            d.get("collection_method"), d.get("requested_limit"),
            cov.get("reels_returned"), cov.get("transcripts_returned"),
            cov.get("transcripts_missing"), d.get("cost_estimate_usd"),
            d.get("cost_actual_usd"),          # ★ None → NULL，不是 0
            d.get("latency_s"), d.get("disclosure"),
        ]) + ");",
        "",
        f"-- ── {len(reels)} 支 reel ──",
    ]

    def sha(x):
        return hashlib.sha256(x.encode("utf-8")).hexdigest() if x else None

    for r in reels:
        cap, tr = r.get("caption"), r.get("transcript")
        # ★ 逐字稿狀態四態互斥：
        #   ok           拿到了
        #   unknown      要了但沒拿到 —— 我們沒看到，不代表這支沒有字幕
        #   not_requested 這次根本沒要
        # fail（這支確實沒有字幕）目前無法從 Apify 回應區分，因此不會被填 ——
        # 寧可留在 unknown，也不要宣稱一件我們分不出來的事。
        if tr:
            tstat = "ok"
        elif d.get("transcript_requested"):
            tstat = "unknown"
        else:
            tstat = "not_requested"
        rows.append(
            "INSERT OR REPLACE INTO ig_reel (shortcode, run_id, account, url, caption,"
            " posted_at, duration_s, billed_minutes, views, likes, comments, video_url,"
            " caption_sha256, caption_char_count, transcript_sha256, transcript_char_count,"
            " transcript_excerpt, transcript_status, collected_via) VALUES ("
            + ", ".join(q(x) for x in [
                r.get("shortcode"), run_id, d["account"], r.get("url"), cap,
                r.get("posted_at"), r.get("duration_s"), billed_minutes(r.get("duration_s")),
                r.get("views"), r.get("likes"), r.get("comments"), r.get("video_url"),
                sha(cap), len(cap) if cap else None,
                sha(tr), len(tr) if tr else None,
                (tr[:120] if tr else None),     # ★ ≤120 字節錄，§來源紀律允許的範圍
                tstat,
                r.get("collected_via"),
            ]) + ");"
        )

    trs = [r for r in reels if r.get("transcript")]
    tr_rows = [f"-- ── 逐字稿 {len(trs)} 支 ──"]
    for r in trs:
        t = r["transcript"]
        tr_rows.append(
            "INSERT OR REPLACE INTO ig_reel_transcript (shortcode, run_id, transcript,"
            " char_len, lang, asr_reviewed, source) VALUES ("
            + ", ".join(q(x) for x in [
                r.get("shortcode"), run_id, t, len(t),
                None,          # ★ lang 未偵測就留 NULL，不要猜
                0,             # ★ asr_reviewed=0：未經人工回看校對
                "apify_transcript_addon",
            ]) + ");"
        )

    catalog = outdir / "catalog.sql"
    if a.publish_transcripts:
        body = head + rows + [""] + tr_rows + ["", "COMMIT;", ""]
        catalog.write_text("\n".join(body), encoding="utf-8")
        print(f"✅ {catalog}（含 {len(trs)} 筆逐字稿）")
        print("   ⚠️ --publish-transcripts 已開啟。推上公開 repo 前請自行確認 §來源紀律。")
    else:
        catalog.write_text("\n".join(head + rows + ["", "COMMIT;", ""]), encoding="utf-8")
        print(f"✅ {catalog}（{len(reels)} 支 reel，不含逐字稿）")
        if trs:
            tp = outdir / "transcripts.sql"
            tp.write_text("\n".join(
                head[:1] + [f"-- 逐字稿 —— @{d['account']}｜{d['harvested_at']}",
                            "-- ⛔ 預設不進 git（見 .gitignore）。",
                            "--    CONTRIBUTING.md §來源紀律：不整支影片逐字重製發布。",
                            "--    這份檔案是我方分析的原料，不是可發布的內容。",
                            "-- ══════════════════════════════════════════════════════════════",
                            "", "BEGIN;", ""] + tr_rows + ["", "COMMIT;", ""]),
                encoding="utf-8")
            print(f"✅ {tp}（{len(trs)} 筆逐字稿 · 預設不進 git）")

    miss = cov.get("transcripts_missing")
    if miss:
        print(f"\n⚠️ 有 {miss} 支要了逐字稿但沒拿到 → 記為 unknown，"
              "不是「這支沒有字幕」。無語音／純音樂／ASR 失敗都會落在這裡。")
    if d.get("cost_actual_usd") is None:
        print("⚠️ cost_actual_usd 為 NULL（未量測），不是 0。實際扣款請查 Apify 帳單後回填。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
