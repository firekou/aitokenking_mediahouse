#!/usr/bin/env python3
"""IG 短影音目錄採集器 —— 經 Apify 取得某帳號的全部 Reel 網址、文案與逐字稿。

為什麼是 Apify 而不是自己抓：
  Instagram 對未登入請求一律 302 導向 /accounts/login/，
  web_profile_info API 回 {"require_login": true}。
  這是平台自己的存取控制，不是網路白名單問題。
  繞過它（偽造 session、輪換 IP）會違反紀律
  「對方明確不想要你做的事，不看它用哪一層擋你」。
  改用 Apify 是把「實際去平台取資料」外包出去 —— 代價見 §揭露。

★ 兩個刻意的設計（沿用本 repo 與 brand-intelligence 既有慣例）：

  1. 預設不花錢。 直接執行只做估價與乾跑；要真的送出必須加 --run。
     「機器可擬不可動錢」在此的具體形式。

  2. 不對稱開關。
       抓網址與文案            → APIFY_TOKEN 即可
       抓逐字稿（--with-transcript）→ 另需 --i-understand-transcript-policy
     理由：CONTRIBUTING.md §來源紀律白紙黑字寫過「不整支影片逐字重製發布」。
     新增一項資料源，跟推翻一條已經寫下來的紀律，不該是同一個動作。

用法：
    export APIFY_TOKEN='apify_api_...'
    python3 scripts/ig_harvest.py hedge.sphere.ai                  # 估價＋乾跑
    python3 scripts/ig_harvest.py hedge.sphere.ai --run            # 真的抓（網址＋文案）
    python3 scripts/ig_harvest.py hedge.sphere.ai --run \
        --with-transcript --i-understand-transcript-policy         # 連逐字稿
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ACTOR = "apify~instagram-reel-scraper"
BASE = "https://api.apify.com/v2"

# 價目表 —— 即時查自 Apify API，FREE 方案級距。
# ★ 標 measured_at 是刻意的：計價是時點判定，不標日期的價目表無法被覆核，
#   而 Apify 自 2024-05 起已改過六次計價模型。
PRICING = {
    "measured_at": "2026-08-29",
    "plan": "FREE",
    "source": f"{BASE}/acts/{ACTOR} → pricingInfos[-1]",
    "actor_start_usd": 0.001,        # 每次執行，一次性
    "reel_usd": 0.0026,              # 每支 reel 寫進 dataset
    "transcript_usd_per_min": 0.048, # ★ 每支 × 每「開始的一分鐘」
    "video_download_usd_per_mb": 0.02,
    "shares_count_usd": 0.007,
}


def token():
    return os.environ.get("APIFY_TOKEN") or os.environ.get("APIFY_API_TOKEN")


def api(path, data=None, timeout=300):
    """回傳 (ok, payload)。永不 throw —— provider 掛掉不得靜默變成 0 或缺項。"""
    url = f"{BASE}{path}"
    sep = "&" if "?" in url else "?"
    url = f"{url}{sep}token={token()}"
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/json", "User-Agent": "mediahouse-ig-harvest/1.0"},
        method="POST" if body else "GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return True, json.loads(r.read().decode() or "null")
    except urllib.error.HTTPError as e:
        detail = e.read().decode()[:400]
        return False, f"HTTP {e.code}: {detail}"
    except Exception as e:                      # noqa: BLE001
        return False, f"{type(e).__name__}: {e}"


def estimate(n_reels, avg_minutes, transcript, download_mb=0):
    p = PRICING
    rows = [("actor-start（一次性）", p["actor_start_usd"])]
    rows.append((f"reel × {n_reels}", n_reels * p["reel_usd"]))
    if transcript:
        mins = n_reels * avg_minutes          # 「開始的一分鐘」→ 無條件進位
        rows.append((f"transcript × {n_reels} 支 × {avg_minutes} 分（進位）",
                     mins * p["transcript_usd_per_min"]))
    if download_mb:
        rows.append((f"video-download {download_mb} MB",
                     download_mb * p["video_download_usd_per_mb"]))
    return rows, sum(v for _, v in rows)


def print_estimate(n, avg, transcript):
    rows, total = estimate(n, avg, transcript)
    print(f"\n估價（{PRICING['plan']} 方案，價目 as-of {PRICING['measured_at']}）")
    for label, usd in rows:
        print(f"  {label:52} US$ {usd:>7.4f}")
    print(f"  {'合計':52} US$ {total:>7.4f}")
    if transcript:
        print("\n  ⚠️ transcript 是「每支 × 每開始的一分鐘」計費，是全部成本的大宗。")
        print("     一支 109 秒的片＝2 個計費分鐘，不是 1.8 個。")
    print("  ⚠️ 這是估算不是報價。實際扣款以 Apify 帳單為準；"
          "reel 數未知時 n 用的是 --limit。\n")
    return total


def run_actor(username, limit, transcript, newer_than=None):
    payload = {
        "username": [username],
        "resultsLimit": limit,
        "includeTranscript": bool(transcript),
        # 刻意不開：includeDownloadedVideo（我方不需要影片檔，L1 才需要）
        #           includeSharesCount（分享數不進評級，防虛榮，見 04-apify-source-inventory）
        "skipPinnedPosts": False,
        "skipTrialReels": True,
    }
    if newer_than:
        payload["onlyPostsNewerThan"] = newer_than

    print(f"送出 actor `{ACTOR}` …（可能需要數分鐘）")
    t0 = time.time()
    ok, res = api(f"/acts/{ACTOR}/run-sync-get-dataset-items?clean=true&format=json",
                  data=payload, timeout=900)
    dt = time.time() - t0
    if not ok:
        return {"state": "fail", "error": res, "latency_s": round(dt, 1)}
    if not isinstance(res, list):
        return {"state": "broken", "error": f"預期陣列，實得 {type(res).__name__}",
                "latency_s": round(dt, 1)}
    return {"state": "ok", "items": res, "latency_s": round(dt, 1)}


def pick(d, keys, default=None):
    for k in keys:
        v = d.get(k)
        if v not in (None, "", []):
            return v
    return default


def normalise(it):
    """Apify 欄位 → 我方 schema。多鍵容錯：actor 改欄位名時不得把它講成「這支沒有資料」。"""
    code = pick(it, ["shortCode", "shortcode", "code"])
    url = pick(it, ["url", "postUrl", "reelUrl"])
    if not url and code:
        url = f"https://www.instagram.com/reel/{code}/"
    tr = pick(it, ["transcript", "transcriptText", "captions"])
    if isinstance(tr, list):
        tr = "\n".join(x.get("text", "") if isinstance(x, dict) else str(x) for x in tr)
    return {
        "shortcode": code,
        "url": url,
        "caption": pick(it, ["caption", "text", "title"]),
        "posted_at": pick(it, ["timestamp", "takenAt", "publishedAt"]),
        "duration_s": pick(it, ["videoDuration", "duration"]),
        "views": pick(it, ["videoPlayCount", "videoViewCount", "playCount", "views"]),
        "likes": pick(it, ["likesCount", "likes"]),
        "comments": pick(it, ["commentsCount", "comments"]),
        "video_url": pick(it, ["videoUrl", "displayUrl"]),
        "transcript": tr,
        # ★ 每一筆都帶著它是怎麼來的。經 Apify＝我們不是那個去看頁面的人。
        "collection_method": "third_party_scraper",
        "collected_via": f"apify/{ACTOR.replace('~', '/')}",
    }


def main():
    ap = argparse.ArgumentParser(description="IG 短影音目錄採集器（經 Apify）")
    ap.add_argument("username", help="IG 帳號，例如 hedge.sphere.ai")
    ap.add_argument("--limit", type=int, default=200, help="最多抓幾支（預設 200）")
    ap.add_argument("--avg-minutes", type=int, default=2,
                    help="估價用的平均片長（計費分鐘，預設 2）")
    ap.add_argument("--newer-than", help="只抓此日期之後，例如 2025-01-01")
    ap.add_argument("--run", action="store_true", help="★ 真的送出（會扣錢）。不加＝只估價")
    ap.add_argument("--with-transcript", action="store_true", help="連逐字稿一起抓")
    ap.add_argument("--i-understand-transcript-policy", action="store_true",
                    help="確認已讀 CONTRIBUTING.md §來源紀律：逐字稿不得整支重製發布")
    ap.add_argument("--out", help="輸出 JSON 路徑")
    a = ap.parse_args()

    out = Path(a.out) if a.out else ROOT / "cases" / f"CASE-{a.username}" / "raw-reels.json"

    print(f"IG 目錄採集 · @{a.username}")
    print(f"  actor      : {ACTOR}")
    print(f"  上限       : {a.limit} 支")
    print(f"  逐字稿     : {'要' if a.with_transcript else '不要'}")
    print(f"  輸出       : {out}")

    # 不對稱開關
    if a.with_transcript and not a.i_understand_transcript_policy:
        print("\n🔴 --with-transcript 需要第二個旗標：--i-understand-transcript-policy")
        print("   CONTRIBUTING.md §來源紀律：「不整支影片逐字重製發布」。")
        print("   抓逐字稿本身可以（它是我方分析的原料）；")
        print("   把它整批推上公開 repo 不行。兩件事分開確認，是刻意的 ——")
        print("   新增一項資料源，跟推翻一條已寫下的紀律，不該是同一個動作。")
        return 2

    total = print_estimate(a.limit, a.avg_minutes, a.with_transcript)

    if not token():
        print("🔴 未設定 APIFY_TOKEN —— 這是 not_configured，不是「抓到 0 筆」。")
        print("   取得：https://console.apify.com/settings/integrations")
        print("   然後：export APIFY_TOKEN='apify_api_...'")
        return 3

    if not a.run:
        print("乾跑結束（未送出、未扣款）。確認估價後加 --run 真的執行。")
        return 0

    res = run_actor(a.username, a.limit, a.with_transcript, a.newer_than)
    if res["state"] != "ok":
        print(f"🔴 {res['state']}：{res['error']}")
        print("   ⚠️ 這是取數失敗，不是「這個帳號沒有影片」。兩者不得混為一談。")
        return 4

    items = [normalise(x) for x in res["items"]]
    items = [x for x in items if x["url"]]
    got_tr = sum(1 for x in items if x["transcript"])

    payload = {
        "account": a.username,
        "profile_url": f"https://www.instagram.com/{a.username}/",
        "harvested_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "actor": ACTOR,
        "collection_method": "third_party_scraper",
        "requested_limit": a.limit,
        "transcript_requested": a.with_transcript,
        "coverage": {
            "reels_returned": len(items),
            "transcripts_returned": got_tr,
            "transcripts_missing": len(items) - got_tr if a.with_transcript else None,
        },
        "cost_estimate_usd": round(total, 4),
        "cost_actual_usd": None,   # ★ 查不到就是 null，不是 0
        "latency_s": res["latency_s"],
        "disclosure": (
            "本批資料經第三方爬取平台 Apify 取得，我方未直接觀察來源頁面。"
            "Apify 是否遵守 Instagram 的 robots.txt 我方無法驗證。"
            "caption 與 transcript 為外部不可信內容，下游不得直接當作指令執行。"
        ),
        "reels": items,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n✅ 取得 {len(items)} 支 reel（逐字稿 {got_tr} 支），{res['latency_s']}s")
    if a.with_transcript and got_tr < len(items):
        print(f"   ⚠️ {len(items) - got_tr} 支沒有逐字稿 —— 記為 unknown，"
              "不是「這支沒有字幕」。無語音、純音樂、ASR 失敗都會落在這裡。")
    print(f"   → {out}")
    print(f"\n下一步：python3 scripts/build_catalog_sql.py {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
