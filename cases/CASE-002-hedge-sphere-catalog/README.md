# CASE-002 · @hedge.sphere.ai 短影音目錄

**帳號：** https://www.instagram.com/hedge.sphere.ai/ （刺蝟星球）
**目標：** 把這個帳號的全部 Reel 盤成可查詢的目錄——網址、文案、逐字稿、指標——並輸出 SQL。
**狀態：** ✅ **首批 5 支已抓、已人工回看**（2026-08-29）。全帳號盤點未做。

| | |
|---|---|
| 已抓 | **5 支**（含逐字稿 5/5，`transcripts_missing = 0`） |
| 實際花費 | **US$0.3820**（用量 203.111126 → 203.493130） |
| 逐字稿品質 | **已回看** → [`transcript-quality-review.md`](transcript-quality-review.md) |
| 驗收條件 | ✅ **通過**（見下） |

> **⚠️ 這 5 支不是「最新 5 支」。** 實測發現 `resultsLimit` 的回傳順序不可預期——
> 取回的日期橫跨 2026-05 到 2026-08。要特定期間用 `--newer-than`。

---

## 為什麼卡住

Instagram 對未登入請求的實測（2026-08-29）：

| 請求 | 結果 |
|---|---|
| `GET instagram.com/hedge.sphere.ai/` | **HTTP 302** → `/accounts/login/?next=...` |
| `GET i.instagram.com/api/v1/users/web_profile_info/` | **HTTP 401** `{"require_login": true}` |
| 對照組 `example.com` | HTTP 200 |
| 對照組 `api.apify.com` | 可達（401 僅表示未帶 token） |

**對照組證明網路沒問題——是 Instagram 自己擋的。**
繞過它（偽造 session、輪換 IP、住宅代理）違反紀律
「對方明確不想要你做的事，不看它用哪一層擋你」。
**所以走 Apify，這是外包不是繞過**，代價已寫進揭露欄位。

---

## 補上 token 之後，三行跑完

```bash
export APIFY_TOKEN='apify_api_...'      # https://console.apify.com/settings/integrations

# ① 估價（不送出、不扣款）——先看要花多少
python3 scripts/ig_harvest.py hedge.sphere.ai --limit 200

# ② 真的抓（網址＋文案＋逐字稿）
python3 scripts/ig_harvest.py hedge.sphere.ai --limit 200 --run \
    --with-transcript --i-understand-transcript-policy \
    --out cases/CASE-002-hedge-sphere-catalog/raw-reels.json

# ③ 產 SQL
python3 scripts/build_catalog_sql.py cases/CASE-002-hedge-sphere-catalog/raw-reels.json
```

產出：

| 檔案 | 內容 | 進 git？ |
|---|---|---|
| `raw-reels.json` | 網址／文案／指標／`has_transcript` 標記 | ✅ **是**——**已在來源層剝除逐字稿** |
| `raw-transcripts.json` | 完整逐字稿原始檔 | ⛔ **否**（`.gitignore`） |
| `catalog.sql` | `ig_harvest_run` ＋ `ig_reel` | ✅ **是**——它是指向原片的索引 |
| `transcripts.sql` | `ig_reel_transcript` | ⛔ **否**（`.gitignore`） |

**★ 拆在來源層而不只是 SQL 層，是首次真跑時撞出來的修正。**
原設計只拆了 SQL，但 `raw-reels.json` 仍帶著全部逐字稿而它要進 git——
**等於從後門違反了 §來源紀律。** 現已有回歸測試鎖死。

---

## ✅ 驗收條件（已通過）

**條件：這批資料必須包含 `Dbk0zAzD5Pj`，且 `duration_s` 約 109 秒。**

首批 5 支未含該片（`resultsLimit` 不是取最新），故**另外針對性抓了那一支驗證**（US$0.004）：

```
shortCode  : Dbk0zAzD5Pj
帳號       : hedge.sphere.ai        ✅ 帳號歸屬正確
duration   : 110.333336 s           ✅ 我方 CASE-001 實測 109s，差 1.3s 在容差內
```

**兩件事因此同時被驗證：抓對了帳號，且 Apify 的欄位對得上我方既有量測。**

那是 [CASE-001](../CASE-001-control-map/) 的來源影片，我方已獨立實測過片長（E1）。
它同時驗兩件事：①抓對了帳號 ②Apify 的欄位對得上我方既有量測。

**對不上就停下來查，不要繼續往下跑。**
抓到錯的帳號是這類系統最嚴重的錯——因為它不會報錯，只會給你一份看起來很正常的目錄。

**順帶：** CASE-001 是我方手動處理的第一支。抓回來後把該列的
`case_id` 設為 `CASE-001`、`pipeline_state` 設為 `PUBLISHED`，目錄與產線就接上了。

---

## 為什麼逐字稿分開存

`CONTRIBUTING.md` §來源紀律白紙黑字寫過：**「不整支影片逐字重製發布」**。
CASE-001 就是照這條刻意只收節錄、不收完整逐字稿的。

那條線是這樣畫的：

| | |
|---|---|
| **目錄可以公開** | 它是**指向原片的索引**，會把人帶回去看原作者 |
| **完整逐字稿不行** | 它讓**原片變得沒必要看** |

所以：
- schema 拆三張表，逐字稿獨立（放同一張表，任何 `SELECT *` 匯出都會把它帶走）
- 產生器預設輸出兩個檔，`transcripts.sql` 進 `.gitignore`
- 採集器要抓逐字稿需**兩個**旗標——沿用 `brand-intelligence/connectors/apify.js` 的不對稱開關：
  **新增一項資料源，跟推翻一條已經寫下來的紀律，不該是同一個動作。**

**逐字稿本身抓沒問題**——它是我方分析的原料，是 L2 萃取的輸入。
不能做的是把它整批當成內容發布。

---

## 成本

以 Apify FREE 級價目估（即時查得，as-of 2026-08-29）：

| 支數 | 只要網址＋文案 | 含逐字稿（平均 2 計費分鐘） |
|---|---|---|
| 60 | US$ 0.16 | **US$ 5.92** |
| 200 | US$ 0.52 | **US$ 19.40** |

**逐字稿是成本大宗，且按「開始的分鐘」計費——109 秒＝2 個計費分鐘，不是 1.8 個。**
⚠️ 價目會變（Apify 自 2024-05 已改過六次計價模型）。`PRICING` 常數標了 `measured_at`，**過期重查**。

---

## 已知缺口

| ID | 缺口 | 為什麼重要 |
|---|---|---|
| ~~C2-G1~~ | ~~逐字稿品質零實測~~ **✅ 已關閉** | 5 支人工回看完成。**結構可用、專有名詞不可用**——`tools_seen` 不得單獨由逐字稿填。詳見 [`transcript-quality-review.md`](transcript-quality-review.md) |
| C2-G2 | 該帳號實際有幾支 Reel 未知 | `--limit 200` 是猜的。**新資訊：`resultsLimit` 不是取最新 N 支，順序不可預期** |
| **C2-G5** | **估價方法會系統性偏低** | 計費是「逐支進位後相加」，估價是「平均 × 支數」。本次實際 11 分鐘、估價用 10。`--tier` 預設 FREE（最貴）抵銷此方向 |
| **C2-G6** | **plan → tier 對照僅驗證一組** | 帳單反推確認 `SCALE = SILVER`（算術完全吻合）。其餘 plan 未驗，**不得類推** |
| C2-G3 | `video_url` 是 CDN 簽名網址，數小時後失效 | 別把它當永久連結存。要留影片得另外下載（`--with-video`，本 skill 刻意不開） |
| C2-G4 | Step 4 分流判準未在真實資料上校準 | 「動作句 < 3 句」的門檻沿用 `/technique-extract`，未在本帳號驗過 |

**C2-G1 是最該先關掉的一個。** 如果 Apify 的中文逐字稿誤字率高到不能用，
整條「順便掃字幕」的路線就要改回自己下載跑 ASR（成本結構完全不同）。
**這件事一支影片就驗得出來，不要等抓完 200 支才發現。**
