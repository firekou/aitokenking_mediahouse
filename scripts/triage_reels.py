#!/usr/bin/env python3
"""L0.5 Step 4 · 分流器 —— 從目錄裡挑出哪幾支值得做成 skill。

★ 刻意用規則不用 LLM，三個理由（沿用本 repo 既有的 T-1 分類器設計）：
    ① 可審   —— 每個判定都印得出「是哪幾個訊號讓它過的」
    ② 免金鑰 —— clone 下來就能跑，不必先有一把 key
    ③ 可被證偽 —— 規則寫在這裡，你可以指著某一條說它錯了

★ 判準沿用 technique-extract 的入場檢查：動作句 < 3 → OPINION_ONLY，不做。
  這一題會擋掉大約一半，而那正是它的價值 ——
  一個什麼都能轉成 skill 的產線，產出的東西不會有人用。

用法：
    python3 scripts/triage_reels.py cases/CASE-002-hedge-sphere-catalog
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 動作訊號：權重反映「它有多能證明這裡有可執行步驟」
SIGNALS = {
    "step_ordinal":   (r"第[一二三四五六七八九十1-9]步", 3, "步驟序數（第N步）"),
    "sequence":       (r"首先|然後|然后|接着|接著|接下来|接下來|最后|最後", 1, "序列詞"),
    "then_pattern":   (r"先.{1,12}再", 2, "先…再"),
    "operation_verb": (r"打开|打開|点击|點擊|上传|上傳|输入|輸入|选择|選擇|导入|導入|设置|設置|勾选|勾選|拖入|保存", 1, "操作動詞"),
    "imperative":     (r"你只要|我们要|我們要|把.{1,10}(交给|交給|丢给|丟給|传给|傳給)", 1, "教學祈使"),
    "param":          (r"\d+\s*[:：比]\s*\d+|\d+\s*(秒|幀|帧|张|張|个|個|次)", 1, "具體參數"),
}
# 反向訊號：純敘事／宣傳
OPINION = (r"我觉得|我認為|我认为|未来会|未來會|梦想|夢想|人生|感受|情怀|情懷"
           r"|专注于|專注於|致力于|致力於|我们相信|我們相信|欢迎加入|歡迎加入")

ACTION_THRESHOLD = 3          # 對應 technique-extract 的「動作句 ≥ 3 句」
OPINION_VETO = 4              # 觀點詞密集且動作分低 → 直接判 OPINION_ONLY


def score(text):
    hits, total = {}, 0
    for key, (pat, w, label) in SIGNALS.items():
        n = len(re.findall(pat, text))
        if n:
            hits[label] = n
            total += min(n, 3) * w        # ★ 單一訊號封頂，避免一個詞刷滿分
    op = len(re.findall(OPINION, text))
    return total, hits, op


def triage(reel, transcript):
    if not transcript:
        return {"verdict": "INSUFFICIENT_DATA", "action_score": None, "signals": {},
                "reason": "無逐字稿 —— 這是「我們沒拿到」不是「這支沒有內容」"}
    s, hits, op = score(transcript)
    if op >= OPINION_VETO and s < ACTION_THRESHOLD * 2:
        return {"verdict": "OPINION_ONLY", "action_score": s, "signals": hits,
                "opinion_hits": op,
                "reason": f"觀點詞 {op} 次且動作分 {s} 未達 {ACTION_THRESHOLD*2} —— 敘事或宣傳，非技巧"}
    if s >= ACTION_THRESHOLD:
        return {"verdict": "WORTH_SKILL", "action_score": s, "signals": hits,
                "opinion_hits": op, "reason": f"動作分 {s} ≥ {ACTION_THRESHOLD}"}
    return {"verdict": "OPINION_ONLY", "action_score": s, "signals": hits,
            "opinion_hits": op,
            "reason": f"動作分 {s} < {ACTION_THRESHOLD} —— 找不到足夠的可執行步驟"}


def main(argv):
    if not argv:
        print("用法：python3 scripts/triage_reels.py <case 目錄>")
        return 2
    case = Path(argv[0])
    reels = json.loads((case / "raw-reels.json").read_text(encoding="utf-8"))
    tp = case / "raw-transcripts.json"
    if not tp.exists():
        print(f"🔴 找不到 {tp}")
        print("   ⚠️ 這是「逐字稿檔不在」不是「這些片沒有字幕」。分流需要逐字稿。")
        return 3
    trs = json.loads(tp.read_text(encoding="utf-8"))["transcripts"]

    out, counts = [], Counter()
    for r in reels["reels"]:
        t = trs.get(r["shortcode"])
        v = triage(r, t)
        counts[v["verdict"]] += 1
        out.append({"shortcode": r["shortcode"], "url": r["url"],
                    "posted_at": r.get("posted_at"), "views": r.get("views"),
                    "duration_s": r.get("duration_s"),
                    "transcript_chars": len(t) if t else None, **v})

    out.sort(key=lambda x: (x["verdict"] != "WORTH_SKILL", -(x["views"] or 0)))
    payload = {
        # ★ case_id 是 CASE-NNN，取自目錄名。用帳號名當 case_id 會產生斷鏈的引用路徑。
        "case_id": (re.match(r"(CASE-\d{3})", case.name).group(1)
                    if re.match(r"CASE-\d{3}", case.name) else case.name),
        "account": reels.get("account"),
        "triaged_at": reels.get("harvested_at"),
        "classifier": "rule-based v1（刻意不用 LLM：可審／免金鑰／可被證偽）",
        "action_threshold": ACTION_THRESHOLD,
        "signals": {v[2]: v[1] for v in SIGNALS.values()},
        # ★ 沒有人工標註就只有「分佈」沒有「錯誤率」。這個欄位不會因為跑過一次就自動升格。
        "classifier_error_rate": "UNMEASURED",
        "error_rate_note": ("需要人工標註 ground truth 才算得出錯誤率。"
                            "目前僅有 5 支人工回看樣本，見 §驗證。"),
        "counts": dict(counts),
        "reels": out,
    }
    (case / "triage.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"分流完成：{sum(counts.values())} 支")
    for k in ("WORTH_SKILL", "OPINION_ONLY", "INSUFFICIENT_DATA"):
        print(f"  {k:18} {counts.get(k, 0):>4}")
    print(f"\n  → {(case / 'triage.json')}")
    print(f"\n  ⚠️ classifier_error_rate = UNMEASURED。")
    print(f"     沒有人工標註就只有「分佈」沒有「錯誤率」，這兩件事不得互相代替。")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
